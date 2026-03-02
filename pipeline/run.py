"""Run full Phase 1 pipeline: ingest -> network -> metrics -> temporal."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pipeline.config import DATA_PROCESSED, ensure_dirs
from pipeline.ingest import run_ingest
from pipeline.metrics import compute_all_metrics
from pipeline.network import run_network
from pipeline.temporal import run_temporal


def run_phase1(
    *,
    skip_ingest: bool = False,
    out_dir: Path | None = None,
) -> None:
    """
    Execute Phase 1: load/stream Yelp data, build graphs, compute metrics, temporal analysis.
    If skip_ingest=True, load city_*.csv from out_dir and run network + metrics + temporal only.
    """
    out_dir = out_dir or DATA_PROCESSED
    ensure_dirs()

    if skip_ingest:
        businesses = pd.read_csv(out_dir / "city_businesses.csv")
        reviews = pd.read_csv(out_dir / "city_reviews.csv")
        users = pd.read_csv(out_dir / "city_users.csv")
        if "categories_list" not in businesses.columns:
            businesses["categories_list"] = businesses["categories"].fillna("").str.split(", ")
        if "friends_list" not in users.columns:
            users["friends_list"] = users["friends"].fillna("").apply(
                lambda s: [x.strip() for x in str(s).split(",") if x.strip()] if isinstance(s, str) else []
            )
        print("Loaded city_businesses, city_reviews, city_users from CSV (skip_ingest=True).")
    else:
        businesses, reviews, users = run_ingest(out_dir=out_dir)

    print("Building networks...")
    B, G_restaurant, G_reviewer, G_friend = run_network(businesses, reviews, users, out_dir=out_dir)

    print("Computing metrics...")
    compute_all_metrics(B, G_restaurant, G_reviewer, G_friend, out_dir=out_dir)

    # Friend edges and reviewer centrality for temporal
    friend_edges = pd.read_csv(out_dir / "friend_edges.csv") if (out_dir / "friend_edges.csv").exists() else None
    reviewer_centrality = None
    if (out_dir / "reviewer_projection_nodes.csv").exists():
        rn = pd.read_csv(out_dir / "reviewer_projection_nodes.csv")
        if "id" in rn.columns and "degree" in rn.columns:
            reviewer_centrality = rn[["id", "degree"]].rename(columns={"id": "user_id"})
        elif "id" in rn.columns and "eigenvector" in rn.columns:
            reviewer_centrality = rn[["id", "eigenvector"]].rename(columns={"id": "user_id"})
    if reviewer_centrality is None and "bipartite_reviewer_nodes.csv" in [f.name for f in out_dir.iterdir()]:
        rn = pd.read_csv(out_dir / "bipartite_reviewer_nodes.csv")
        if "id" in rn.columns and "degree" in rn.columns:
            reviewer_centrality = rn[["id", "degree"]].rename(columns={"id": "user_id"})

    print("Running temporal analysis...")
    run_temporal(
        reviews,
        users,
        friend_edges,
        reviewer_centrality,
        out_dir=out_dir,
    )
    print("Phase 1 complete.")


if __name__ == "__main__":
    import sys
    skip = "--skip-ingest" in sys.argv
    run_phase1(skip_ingest=skip)
