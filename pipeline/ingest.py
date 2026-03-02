"""Ingest Yelp JSON: filter to target city restaurants, stream reviews, output CSVs.

Do NOT load all reviews into memory — stream and filter line-by-line.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline.config import (
    BUSINESS_FILE,
    DATA_PROCESSED,
    RESTAURANT_CATEGORY_PATTERN,
    REVIEW_FILE,
    TARGET_CITY,
    USER_FILE,
    YELP_DATA_PATH,
    ensure_dirs,
)


def _parse_friends(friends_field: Any) -> list[str]:
    """Parse friend list from Yelp user record (string 'a, b, c' or list)."""
    if isinstance(friends_field, list):
        return friends_field
    if isinstance(friends_field, str) and friends_field.strip() and friends_field.strip() != "None":
        return [x.strip() for x in friends_field.split(",") if x.strip()]
    return []


def _parse_categories(categories_field: Any) -> list[str]:
    """Parse categories string into list (e.g. 'Restaurant, Bar' -> ['Restaurant','Bar'])."""
    if pd.isna(categories_field) or not str(categories_field).strip():
        return []
    s = str(categories_field).strip()
    return [x.strip() for x in s.split(",") if x.strip()]


def load_city_businesses() -> pd.DataFrame:
    """Load business JSON, filter to TARGET_CITY and restaurant/food categories. Return DataFrame."""
    path = Path(YELP_DATA_PATH) / BUSINESS_FILE
    if not path.exists():
        raise FileNotFoundError(f"Business file not found: {path}")

    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("city") != TARGET_CITY:
                continue
            cats = rec.get("categories") or ""
            if not isinstance(cats, str):
                cats = str(cats) if cats else ""
            if not re.search(RESTAURANT_CATEGORY_PATTERN, cats, flags=re.IGNORECASE):
                continue
            rec["categories_list"] = _parse_categories(rec.get("categories"))
            rows.append(rec)

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df


def stream_reviews_for_businesses(
    business_ids: set[str],
    review_path: Path | None = None,
    *,
    progress_interval: int = 1_000_000,
) -> pd.DataFrame:
    """Stream review file line-by-line; keep only reviews for given business_ids. Return DataFrame."""
    path = review_path or Path(YELP_DATA_PATH) / REVIEW_FILE
    if not path.exists():
        raise FileNotFoundError(f"Review file not found: {path}")

    rows: list[dict[str, Any]] = []
    total_scanned = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            total_scanned += 1
            if total_scanned % progress_interval == 0:
                print(f"  Reviews scanned: {total_scanned:,} — kept: {len(rows):,}")
            rec = json.loads(line)
            if rec.get("business_id") in business_ids:
                rows.append(rec)
    return pd.DataFrame(rows)


def load_users_in_set(user_ids: set[str], user_path: Path | None = None) -> pd.DataFrame:
    """Stream user file line-by-line; keep only users in user_ids. Parse friend lists."""
    path = user_path or Path(YELP_DATA_PATH) / USER_FILE
    if not path.exists():
        raise FileNotFoundError(f"User file not found: {path}")

    rows: list[dict[str, Any]] = []
    total_scanned = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            total_scanned += 1
            if total_scanned % 500_000 == 0:
                print(f"  Users scanned: {total_scanned:,} — kept: {len(rows):,}")
            rec = json.loads(line)
            if rec.get("user_id") in user_ids:
                rec["friends_list"] = _parse_friends(rec.get("friends"))
                rows.append(rec)
    return pd.DataFrame(rows)


def run_ingest(
    *,
    out_dir: Path | None = None,
    progress_interval: int = 1_000_000,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Full ingest: load city businesses, stream reviews for those businesses,
    collect user IDs from reviews, stream users. Write CSVs to data/processed/.
    Returns (city_businesses, city_reviews, city_users).
    """
    ensure_dirs()
    out = out_dir or DATA_PROCESSED

    print(f"Loading businesses for {TARGET_CITY} (restaurant/food categories)...")
    businesses = load_city_businesses()
    if businesses.empty:
        raise ValueError(
            f"No businesses found for city={TARGET_CITY}. Check YELP_DATA_PATH and TARGET_CITY."
        )
    business_ids = set(businesses["business_id"].tolist())
    print(f"  Found {len(businesses):,} businesses.")

    print("Streaming reviews (do not load full file into memory)...")
    reviews = stream_reviews_for_businesses(
        business_ids,
        progress_interval=progress_interval,
    )
    if reviews.empty:
        raise ValueError("No reviews found for city businesses.")
    user_ids = set(reviews["user_id"].tolist())
    print(f"  Kept {len(reviews):,} reviews; {len(user_ids):,} unique users.")

    print("Streaming users (filter to reviewers in city)...")
    users = load_users_in_set(user_ids)
    print(f"  Kept {len(users):,} users.")

    # Write CSVs (flatten list columns for CSV: store as strings)
    businesses_out = businesses.copy()
    if "categories_list" in businesses_out.columns:
        businesses_out["categories"] = businesses_out["categories_list"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else str(x)
        )
        businesses_out = businesses_out.drop(columns=["categories_list"], errors="ignore")
    businesses_out.to_csv(out / "city_businesses.csv", index=False)
    print(f"  Wrote {out / 'city_businesses.csv'}")

    reviews.to_csv(out / "city_reviews.csv", index=False)
    print(f"  Wrote {out / 'city_reviews.csv'}")

    users_out = users.copy()
    if "friends_list" in users_out.columns:
        users_out["friends"] = users_out["friends_list"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else ""
        )
        users_out = users_out.drop(columns=["friends_list"], errors="ignore")
    users_out.to_csv(out / "city_users.csv", index=False)
    print(f"  Wrote {out / 'city_users.csv'}")

    return businesses, reviews, users


if __name__ == "__main__":
    run_ingest()
