"""Temporal analysis: monthly growth curves, hype events, homophily vs influence test."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline.config import DATA_PROCESSED, ensure_dirs


def monthly_growth(reviews: pd.DataFrame) -> pd.DataFrame:
    """For each business_id, compute monthly cumulative review count (growth curve)."""
    reviews = reviews.copy()
    reviews["date"] = pd.to_datetime(reviews["date"], errors="coerce")
    reviews = reviews.dropna(subset=["date"])
    reviews["year_month"] = reviews["date"].dt.to_period("M").astype(str)
    monthly = (
        reviews.groupby(["business_id", "year_month"])
        .size()
        .reset_index(name="count")
    )
    monthly = monthly.sort_values(["business_id", "year_month"])
    monthly["cumulative"] = monthly.groupby("business_id")["count"].cumsum()
    return monthly


def hype_events(
    monthly: pd.DataFrame,
    *,
    n_sigma: float = 2.0,
    min_velocity: int = 3,
) -> pd.DataFrame:
    """
    Hype events: months where a restaurant's review velocity exceeds n_sigma above rolling mean.
    Returns rows with business_id, year_month, count, velocity, rolling_mean, is_hype.
    """
    monthly = monthly.copy()
    monthly["velocity"] = monthly["count"]
    monthly["rolling_mean"] = monthly.groupby("business_id")["count"].transform(
        lambda x: x.rolling(6, min_periods=1).mean()
    )
    monthly["rolling_std"] = monthly.groupby("business_id")["count"].transform(
        lambda x: x.rolling(6, min_periods=1).std().fillna(0)
    )
    monthly["threshold"] = monthly["rolling_mean"] + n_sigma * monthly["rolling_std"]
    monthly["is_hype"] = (monthly["count"] >= monthly["threshold"]) & (monthly["count"] >= min_velocity)
    return monthly


def hype_event_reviewer_centrality(
    hype_months: pd.DataFrame,
    reviews: pd.DataFrame,
    reviewer_centrality: pd.DataFrame,
) -> pd.DataFrame:
    """
    For each hype event (business_id, year_month), capture reviewers in that window
    and compute their average centrality. reviewer_centrality has columns [user_id, centrality_col].
    """
    reviews = reviews.copy()
    reviews["date"] = pd.to_datetime(reviews["date"], errors="coerce")
    reviews["year_month"] = reviews["date"].dt.to_period("M").astype(str)
    hype = hype_months[hype_months["is_hype"]].copy()
    rows: list[dict[str, Any]] = []
    for _, row in hype.iterrows():
        biz = row["business_id"]
        ym = row["year_month"]
        revs_in_window = reviews[(reviews["business_id"] == biz) & (reviews["year_month"] == ym)]
        user_ids = revs_in_window["user_id"].unique()
        if len(user_ids) == 0:
            continue
        cent = reviewer_centrality[reviewer_centrality["user_id"].isin(user_ids)]
        avg_cent = cent.iloc[:, 1].mean() if cent.shape[1] >= 2 else 0.0
        rows.append({
            "business_id": biz,
            "year_month": ym,
            "review_count": int(row.get("count", 0)),
            "n_reviewers": len(user_ids),
            "avg_reviewer_centrality": float(avg_cent),
        })
    return pd.DataFrame(rows)


def influence_test(
    reviews: pd.DataFrame,
    users: pd.DataFrame,
    friend_pairs: list[tuple[str, str]],
) -> dict[str, Any]:
    """
    Homophily vs influence test: P(visit at t+1 | friend visited at t) vs
    P(visit at t+1 | no friend visited). Also Jaccard similarity friends vs random pairs.
    Returns dict with friend_jaccard, random_jaccard, ratio, p_value (placeholder), etc.
    """
    reviews = reviews.copy()
    reviews["date"] = pd.to_datetime(reviews["date"], errors="coerce")
    reviews = reviews.dropna(subset=["date"])
    reviews["year_month"] = reviews["date"].dt.to_period("M").astype(str)
    # Build user -> set of (business_id, year_month) visits
    user_visits: dict[str, set[tuple[str, str]]] = {}
    for _, row in reviews.iterrows():
        uid = row["user_id"]
        biz = row["business_id"]
        ym = row["year_month"]
        user_visits.setdefault(uid, set()).add((biz, ym))
    # Jaccard for friend pairs (shared restaurants in same month)
    def jaccard(u: str, v: str) -> float:
        a = user_visits.get(u, set())
        b = user_visits.get(v, set())
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b) if (a | b) else 0.0
    friend_jaccards = [jaccard(u, v) for u, v in friend_pairs if u in user_visits and v in user_visits]
    friend_jaccard = float(pd.Series(friend_jaccards).mean()) if friend_jaccards else 0.0
    # Random pairs
    user_list = [u for u in user_visits if len(user_visits[u]) >= 2]
    import random
    random.seed(42)
    n_random = min(5000, len(user_list) * (len(user_list) - 1) // 2)
    random_jaccards: list[float] = []
    seen: set[tuple[str, str]] = set()
    while len(random_jaccards) < n_random and len(user_list) >= 2:
        u, v = random.sample(user_list, 2)
        if u > v:
            u, v = v, u
        if (u, v) in seen:
            continue
        seen.add((u, v))
        random_jaccards.append(jaccard(u, v))
    random_jaccard = float(pd.Series(random_jaccards).mean()) if random_jaccards else 0.0
    ratio = friend_jaccard / random_jaccard if random_jaccard else 0.0
    return {
        "friend_jaccard": friend_jaccard,
        "random_jaccard": random_jaccard,
        "ratio": ratio,
        "n_friend_pairs": len(friend_jaccards),
        "n_random_pairs": len(random_jaccards),
        "p_value": None,  # placeholder for statistical test
    }


def run_temporal(
    reviews: pd.DataFrame,
    users: pd.DataFrame,
    friend_edges: pd.DataFrame | None,
    reviewer_centrality: pd.DataFrame | None,
    *,
    out_dir: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """
    Compute monthly growth, hype events, and influence test. Save temporal_growth.csv,
    hype_events.csv, influence_test_results.json. Return (monthly_df, hype_events_df, influence_dict).
    """
    out_dir = out_dir or DATA_PROCESSED
    ensure_dirs()

    monthly = monthly_growth(reviews)
    monthly.to_csv(out_dir / "temporal_growth.csv", index=False)
    print(f"  Wrote {out_dir / 'temporal_growth.csv'}")

    monthly_with_hype = hype_events(monthly)
    hype_df = monthly_with_hype[monthly_with_hype["is_hype"]][
        ["business_id", "year_month", "count", "velocity", "rolling_mean", "rolling_std"]
    ].copy()
    hype_df.to_csv(out_dir / "hype_events.csv", index=False)
    print(f"  Wrote {out_dir / 'hype_events.csv'} ({len(hype_df)} hype events)")

    if reviewer_centrality is not None and not reviewer_centrality.empty and not hype_df.empty:
        reviewer_cent = reviewer_centrality.copy()
        if "user_id" not in reviewer_cent.columns and reviewer_cent.shape[1] >= 2:
            reviewer_cent = reviewer_cent.rename(columns={reviewer_cent.columns[0]: "user_id"})
        hype_reviewer_cent = hype_event_reviewer_centrality(
            monthly_with_hype, reviews, reviewer_cent
        )
        if not hype_reviewer_cent.empty:
            hype_reviewer_cent.to_csv(out_dir / "hype_event_reviewer_centrality.csv", index=False)

    friend_pairs = []
    if friend_edges is not None and not friend_edges.empty:
        for _, row in friend_edges.iterrows():
            u, v = row.get("source"), row.get("target")
            if pd.notna(u) and pd.notna(v):
                friend_pairs.append((str(u), str(v)))
    influence = influence_test(reviews, users, friend_pairs)
    with open(out_dir / "influence_test_results.json", "w") as f:
        json.dump(influence, f, indent=2)
    print(f"  Wrote {out_dir / 'influence_test_results.json'} (friend_jaccard={influence['friend_jaccard']:.4f})")

    return monthly_with_hype, hype_df, influence
