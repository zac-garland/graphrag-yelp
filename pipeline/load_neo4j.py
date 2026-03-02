"""Bulk load graph from data/processed/ into Neo4j. UNWIND + MERGE only; no individual CREATEs."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

# city_users.csv can have very long 'friends' fields; raise CSV field size limit (default 128KB)
csv.field_size_limit(10 * 2**20)  # 10 MB

from neo4j import GraphDatabase

from pipeline.config import (
    DATA_PROCESSED,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
    ensure_dirs,
)

BATCH_SIZE = 1000


def get_driver():
    """Return Neo4j driver. Caller must close."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def run_constraints_and_indexes(driver: Any) -> None:
    """Create constraints (business_id, user_id) and indexes (community_id, k_core, is_elite, fulltext on name)."""
    with driver.session() as session:
        # Uniqueness constraints (create if not exist)
        session.run("CREATE CONSTRAINT restaurant_id IF NOT EXISTS FOR (r:Restaurant) REQUIRE r.business_id IS UNIQUE")
        session.run("CREATE CONSTRAINT reviewer_id IF NOT EXISTS FOR (r:Reviewer) REQUIRE r.user_id IS UNIQUE")
        session.run("CREATE CONSTRAINT category_name IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE")
        session.run("CREATE CONSTRAINT community_id IF NOT EXISTS FOR (c:Community) REQUIRE c.community_id IS UNIQUE")
        # Indexes for filters
        session.run("CREATE INDEX restaurant_community IF NOT EXISTS FOR (r:Restaurant) ON (r.community_id)")
        session.run("CREATE INDEX restaurant_k_core IF NOT EXISTS FOR (r:Restaurant) ON (r.k_core)")
        session.run("CREATE INDEX reviewer_elite IF NOT EXISTS FOR (r:Reviewer) ON (r.is_elite)")
        session.run("CREATE INDEX reviewer_community IF NOT EXISTS FOR (r:Reviewer) ON (r.community_id)")
        # Full-text index for chat search
        try:
            session.run("CREATE FULLTEXT INDEX restaurant_name IF NOT EXISTS FOR (r:Restaurant) ON EACH [r.name]")
        except Exception:
            pass  # Syntax may vary by Neo4j version; fallback is non-fulltext
    print("  Constraints and indexes created.")


def load_restaurants(driver: Any, processed_dir: Path) -> None:
    """Load Restaurant nodes from restaurant_projection_nodes.csv (id -> business_id, metrics)."""
    path = processed_dir / "restaurant_projection_nodes.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "business_id": row.get("id", "").strip(),
                "name": (row.get("name") or "").strip()[:500],
                "stars": float(row["stars"]) if row.get("stars") else 0.0,
                "review_count": int(row["review_count"]) if row.get("review_count") else 0,
                "betweenness": float(row["betweenness"]) if row.get("betweenness") else 0.0,
                "eigenvector": float(row["eigenvector"]) if row.get("eigenvector") else 0.0,
                "k_core": int(row["k_core"]) if row.get("k_core") else 0,
                "community_id": int(row["community_id"]) if row.get("community_id") else 0,
                "categories": (row.get("categories") or "").strip()[:2000],
            })
    with driver.session() as session:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            session.run(
                """
                UNWIND $batch AS row
                MERGE (r:Restaurant {business_id: row.business_id})
                SET r.name = row.name, r.stars = row.stars, r.review_count = row.review_count,
                    r.betweenness = row.betweenness, r.eigenvector = row.eigenvector,
                    r.k_core = row.k_core, r.community_id = row.community_id, r.categories = row.categories
                """,
                batch=batch,
            )
    print(f"  Loaded {len(rows)} Restaurant nodes.")


def load_reviewers(driver: Any, processed_dir: Path) -> None:
    """Load Reviewer nodes from city_users.csv (user_id, review_count, elite -> is_elite)."""
    path = processed_dir / "city_users.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            elite = row.get("elite") or row.get("is_elite") or ""
            is_elite = str(elite).strip().lower() in ("true", "1", "yes") if elite else False
            rows.append({
                "user_id": row.get("user_id", "").strip(),
                "name": (row.get("name") or "").strip()[:200],
                "review_count": int(row["review_count"]) if row.get("review_count") else 0,
                "yelping_since": (row.get("yelping_since") or "").strip()[:20],
                "is_elite": is_elite,
            })
    with driver.session() as session:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            session.run(
                """
                UNWIND $batch AS row
                MERGE (r:Reviewer {user_id: row.user_id})
                SET r.name = row.name, r.review_count = row.review_count,
                    r.yelping_since = row.yelping_since, r.is_elite = row.is_elite
                """,
                batch=batch,
            )
    print(f"  Loaded {len(rows)} Reviewer nodes.")


def load_communities(driver: Any, processed_dir: Path) -> None:
    """Create Community nodes from unique community_id in restaurant_projection_nodes."""
    path = processed_dir / "restaurant_projection_nodes.csv"
    if not path.exists():
        return
    seen: set[int] = set()
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = int(row["community_id"]) if row.get("community_id") else 0
            seen.add(cid)
    with driver.session() as session:
        for cid in seen:
            session.run("MERGE (c:Community {community_id: $cid})", cid=cid)
    print(f"  Loaded {len(seen)} Community nodes.")


def load_categories_and_in_category(driver: Any, processed_dir: Path) -> None:
    """Create Category nodes and IN_CATEGORY from restaurant categories string. UNWIND + MERGE only."""
    path = processed_dir / "restaurant_projection_nodes.csv"
    if not path.exists():
        return
    seen_pairs: set[tuple[str, str]] = set()
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            biz_id = (row.get("id") or "").strip()
            cats = (row.get("categories") or "").strip()
            for cat in [c.strip() for c in cats.split(",") if c.strip()]:
                if cat and biz_id:
                    seen_pairs.add((biz_id, cat[:200]))
    batch_list = [{"business_id": b, "category_name": c} for b, c in seen_pairs]
    with driver.session() as session:
        for i in range(0, len(batch_list), BATCH_SIZE):
            batch = batch_list[i : i + BATCH_SIZE]
            session.run(
                """
                UNWIND $batch AS row
                MERGE (c:Category {name: row.category_name})
                WITH c, row MATCH (r:Restaurant {business_id: row.business_id})
                MERGE (r)-[:IN_CATEGORY]->(c)
                """,
                batch=batch,
            )
    print(f"  IN_CATEGORY: {len(batch_list)} edges.")


def load_belongs_to(driver: Any, processed_dir: Path) -> None:
    """Create BELONGS_TO from Restaurant to Community."""
    path = processed_dir / "restaurant_projection_nodes.csv"
    if not path.exists():
        return
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "business_id": (row.get("id") or "").strip(),
                "community_id": int(row["community_id"]) if row.get("community_id") else 0,
            })
    with driver.session() as session:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            session.run(
                """
                UNWIND $batch AS row
                MATCH (r:Restaurant {business_id: row.business_id}), (c:Community {community_id: row.community_id})
                MERGE (r)-[:BELONGS_TO]->(c)
                """,
                batch=batch,
            )
    print(f"  BELONGS_TO: {len(rows)} edges.")


def load_reviewed(driver: Any, processed_dir: Path) -> None:
    """Load REVIEWED (Reviewer)-[:REVIEWED]->(Restaurant) from city_reviews.csv. Sample if huge."""
    path = processed_dir / "city_reviews.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 500_000:
                break  # Cap for initial load; remove or increase for full
            rows.append({
                "user_id": (row.get("user_id") or "").strip(),
                "business_id": (row.get("business_id") or "").strip(),
                "stars": float(row["stars"]) if row.get("stars") else 0.0,
                "date": (row.get("date") or "").strip()[:20],
                "review_id": (row.get("review_id") or "").strip()[:100],
            })
    with driver.session() as session:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            session.run(
                """
                UNWIND $batch AS row
                MATCH (u:Reviewer {user_id: row.user_id}), (r:Restaurant {business_id: row.business_id})
                MERGE (u)-[x:REVIEWED]->(r)
                SET x.stars = row.stars, x.date = row.date, x.review_id = row.review_id
                """,
                batch=batch,
            )
    print(f"  REVIEWED: {len(rows)} edges (capped at 500k for speed; increase in code for full).")


def load_friends_with(driver: Any, processed_dir: Path) -> None:
    """Load FRIENDS_WITH from friend_edges.csv."""
    path = processed_dir / "friend_edges.csv"
    if not path.exists():
        return
    rows: list[dict[str, str]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "source": (row.get("source") or "").strip(),
                "target": (row.get("target") or "").strip(),
            })
    with driver.session() as session:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            session.run(
                """
                UNWIND $batch AS row
                MATCH (a:Reviewer {user_id: row.source}), (b:Reviewer {user_id: row.target})
                MERGE (a)-[:FRIENDS_WITH]-(b)
                """,
                batch=batch,
            )
    print(f"  FRIENDS_WITH: {len(rows)} edges.")


def load_shared_reviewers(driver: Any, processed_dir: Path) -> None:
    """Load SHARED_REVIEWERS (Restaurant)-[:SHARED_REVIEWERS {weight}]-(Restaurant) from restaurant_projection_edges."""
    path = processed_dir / "restaurant_projection_edges.csv"
    if not path.exists():
        return
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 200_000:
                break  # Cap; remove for full
            rows.append({
                "source": (row.get("source") or "").strip(),
                "target": (row.get("target") or "").strip(),
                "weight": int(row["weight"]) if row.get("weight") else 0,
            })
    with driver.session() as session:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            session.run(
                """
                UNWIND $batch AS row
                MATCH (a:Restaurant {business_id: row.source}), (b:Restaurant {business_id: row.target})
                MERGE (a)-[e:SHARED_REVIEWERS]-(b)
                SET e.weight = row.weight
                """,
                batch=batch,
            )
    print(f"  SHARED_REVIEWERS: {len(rows)} edges (capped at 200k; increase for full).")


def load_hype_events(driver: Any, processed_dir: Path) -> None:
    """Create HypeEvent nodes and link to Restaurant."""
    path = processed_dir / "hype_events.csv"
    if not path.exists():
        return
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "business_id": (row.get("business_id") or "").strip(),
                "year_month": (row.get("year_month") or "").strip()[:10],
                "count": int(row["count"]) if row.get("count") else 0,
            })
    with driver.session() as session:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            session.run(
                """
                UNWIND $batch AS row
                CREATE (h:HypeEvent {year_month: row.year_month, review_count: row.count})
                WITH h, row
                MATCH (r:Restaurant {business_id: row.business_id})
                MERGE (r)-[:HAD_HYPE_EVENT]->(h)
                """,
                batch=batch,
            )
    print(f"  HypeEvent nodes and HAD_HYPE_EVENT: {len(rows)}.")


def run_load(processed_dir: Path | None = None) -> None:
    """Run full Neo4j bulk load. Requires Neo4j running and NEO4J_* env set."""
    ensure_dirs()
    proc = processed_dir or DATA_PROCESSED
    if not NEO4J_PASSWORD:
        raise ValueError("Set NEO4J_PASSWORD in .env (and NEO4J_URI, NEO4J_USER if needed).")
    driver = get_driver()
    try:
        driver.verify_connectivity()
        print("Neo4j connected. Creating schema...")
        run_constraints_and_indexes(driver)
        print("Loading nodes...")
        load_communities(driver, proc)
        load_restaurants(driver, proc)
        load_reviewers(driver, proc)
        load_categories_and_in_category(driver, proc)
        load_belongs_to(driver, proc)
        print("Loading relationships...")
        load_reviewed(driver, proc)
        load_friends_with(driver, proc)
        load_shared_reviewers(driver, proc)
        load_hype_events(driver, proc)
        print("Neo4j load complete.")
    finally:
        driver.close()


if __name__ == "__main__":
    run_load()
