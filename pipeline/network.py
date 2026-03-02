"""Build bipartite (reviewer–restaurant) and projected networks; save edge lists and node CSVs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd

from pipeline.config import (
    DATA_PROCESSED,
    MIN_SHARED_RESTAURANTS,
    MIN_SHARED_REVIEWERS,
    ensure_dirs,
)


def build_bipartite(
    reviews: pd.DataFrame,
    businesses: pd.DataFrame,
    users: pd.DataFrame,
) -> nx.Graph:
    """
    Build bipartite graph B: reviewer nodes, restaurant nodes.
    Edges from reviews with attributes: stars, date, review_id.
    Node attributes: restaurants get name, categories, stars, review_count;
    reviewers get review_count, friend_count, is_elite, yelping_since.
    """
    B = nx.Graph()
    # Add restaurant nodes with attributes
    for _, row in businesses.iterrows():
        B.add_node(
            row["business_id"],
            bipartite=0,
            name=row.get("name", ""),
            categories=", ".join(row["categories_list"]) if isinstance(row.get("categories_list"), list) else str(row.get("categories", "")),
            stars=float(row.get("stars", 0)),
            review_count=int(row.get("review_count", 0)),
        )
    # Add reviewer nodes with attributes
    for _, row in users.iterrows():
        B.add_node(
            row["user_id"],
            bipartite=1,
            review_count=int(row.get("review_count", 0)),
            friend_count=int(row.get("friend_count", 0)) if pd.notna(row.get("friend_count")) else 0,
            is_elite=bool(row.get("is_elite", False)) if pd.notna(row.get("is_elite")) else False,
            yelping_since=str(row.get("yelping_since", "")),
        )
    # Edges from reviews
    for _, row in reviews.iterrows():
        B.add_edge(
            row["user_id"],
            row["business_id"],
            stars=float(row.get("stars", 0)),
            date=str(row.get("date", "")),
            review_id=str(row.get("review_id", "")),
        )
    return B


def project_restaurant_restaurant(
    B: nx.Graph,
    min_shared: int = MIN_SHARED_REVIEWERS,
) -> nx.Graph:
    """Project to restaurant–restaurant graph; edge weight = shared reviewer count; threshold min_shared."""
    reviewer_nodes = {n for n, d in B.nodes(data=True) if d.get("bipartite") == 1}
    restaurant_nodes = {n for n, d in B.nodes(data=True) if d.get("bipartite") == 0}
    G = nx.Graph()
    for r in restaurant_nodes:
        G.add_node(r, **{k: v for k, v in B.nodes[r].items() if k != "bipartite"})
    # Count shared reviewers per pair
    from collections import defaultdict
    pair_count: dict[tuple[str, str], int] = defaultdict(int)
    for u, v in B.edges():
        if u in reviewer_nodes and v in restaurant_nodes:
            rev, biz = u, v
        elif v in reviewer_nodes and u in restaurant_nodes:
            rev, biz = v, u
        else:
            continue
        for u2, v2 in B.edges(rev):
            other = v2 if v2 != biz else u2
            if other in restaurant_nodes and other != biz:
                pair = (biz, other) if biz < other else (other, biz)
                pair_count[pair] += 1
    for (a, b), w in pair_count.items():
        if w >= min_shared:
            G.add_edge(a, b, weight=w, shared_reviewers=w)
    return G


def project_reviewer_reviewer(
    B: nx.Graph,
    min_shared: int = MIN_SHARED_RESTAURANTS,
) -> nx.Graph:
    """Project to reviewer–reviewer graph via shared restaurants; threshold min_shared."""
    reviewer_nodes = {n for n, d in B.nodes(data=True) if d.get("bipartite") == 1}
    restaurant_nodes = {n for n, d in B.nodes(data=True) if d.get("bipartite") == 0}
    G = nx.Graph()
    for r in reviewer_nodes:
        G.add_node(r, **{k: v for k, v in B.nodes[r].items() if k != "bipartite"})
    from collections import defaultdict
    pair_count: dict[tuple[str, str], int] = defaultdict(int)
    for u, v in B.edges():
        if u in reviewer_nodes and v in restaurant_nodes:
            rev, biz = u, v
        elif v in reviewer_nodes and u in restaurant_nodes:
            rev, biz = v, u
        else:
            continue
        for u2, v2 in B.edges(biz):
            other = u2 if u2 != rev else v2
            if other in reviewer_nodes and other != rev:
                pair = (rev, other) if rev < other else (other, rev)
                pair_count[pair] += 1
    for (a, b), w in pair_count.items():
        if w >= min_shared:
            G.add_edge(a, b, weight=w, shared_restaurants=w)
    return G


def build_friend_graph(users: pd.DataFrame, city_user_ids: set[str]) -> nx.Graph:
    """
    Social friend graph: edges between users who are friends AND both reviewed in city.
    Expects users to have 'friends_list' (list) or we parse 'friends' string.
    """
    def get_friend_list(row: pd.Series) -> list[str]:
        if "friends_list" in row and isinstance(row["friends_list"], list):
            return row["friends_list"]
        s = row.get("friends") or ""
        if isinstance(s, str) and s.strip() and s.strip() != "None":
            return [x.strip() for x in s.split(",") if x.strip()]
        return []

    G = nx.Graph()
    for _, row in users.iterrows():
        uid = row["user_id"]
        if uid not in city_user_ids:
            continue
        G.add_node(
            uid,
            review_count=int(row.get("review_count", 0)),
            friend_count=int(row.get("friend_count", 0)) if pd.notna(row.get("friend_count")) else 0,
            is_elite=bool(row.get("is_elite", False)) if pd.notna(row.get("is_elite")) else False,
        )
    for _, row in users.iterrows():
        uid = row["user_id"]
        if uid not in city_user_ids:
            continue
        for fid in get_friend_list(row):
            if fid in city_user_ids and fid != uid:
                G.add_edge(uid, fid)
    return G


def save_graphs(
    B: nx.Graph,
    G_restaurant: nx.Graph,
    G_reviewer: nx.Graph | None,
    G_friend: nx.Graph | None,
    out_dir: Path | None = None,
) -> None:
    """Save bipartite, restaurant projection, reviewer projection, and friend graph as edge lists + node CSVs."""
    out_dir = out_dir or DATA_PROCESSED
    ensure_dirs()

    def write_graph(G: nx.Graph, prefix: str) -> None:
        nodes = list(G.nodes(data=True))
        edges = list(G.edges(data=True))
        if not nodes:
            return
        node_df = pd.DataFrame(
            [{"id": n, **d} for n, d in nodes]
        )
        edge_df = pd.DataFrame(
            [{"source": u, "target": v, **d} for u, v, d in edges]
        )
        node_df.to_csv(out_dir / f"{prefix}_nodes.csv", index=False)
        edge_df.to_csv(out_dir / f"{prefix}_edges.csv", index=False)

    # Bipartite: separate node types for clarity
    rest_nodes = [(n, d) for n, d in B.nodes(data=True) if d.get("bipartite") == 0]
    rev_nodes = [(n, d) for n, d in B.nodes(data=True) if d.get("bipartite") == 1]
    if rest_nodes:
        pd.DataFrame([{"id": n, **d} for n, d in rest_nodes]).to_csv(out_dir / "bipartite_restaurant_nodes.csv", index=False)
    if rev_nodes:
        pd.DataFrame([{"id": n, **d} for n, d in rev_nodes]).to_csv(out_dir / "bipartite_reviewer_nodes.csv", index=False)
    bip_edges = [{"source": u, "target": v, **d} for u, v, d in B.edges(data=True)]
    pd.DataFrame(bip_edges).to_csv(out_dir / "bipartite_edges.csv", index=False)

    write_graph(G_restaurant, "restaurant_projection")
    if G_reviewer and G_reviewer.number_of_nodes() > 0:
        write_graph(G_reviewer, "reviewer_projection")
    if G_friend and G_friend.number_of_nodes() > 0:
        write_graph(G_friend, "friend")


def run_network(
    businesses: pd.DataFrame,
    reviews: pd.DataFrame,
    users: pd.DataFrame,
    *,
    out_dir: Path | None = None,
) -> tuple[nx.Graph, nx.Graph, nx.Graph | None, nx.Graph | None]:
    """
    Build bipartite, restaurant projection, reviewer projection, friend graph.
    Save CSVs to data/processed/. Returns (B, G_restaurant, G_reviewer, G_friend).
    """
    # Restore categories_list if we saved categories as string
    if "categories_list" not in businesses.columns and "categories" in businesses.columns:
        businesses = businesses.copy()
        businesses["categories_list"] = businesses["categories"].fillna("").str.split(", ").apply(
            lambda x: [c for c in x if c]
        )
    if "friends_list" not in users.columns and "friends" in users.columns:
        users = users.copy()
        users["friends_list"] = users["friends"].fillna("").apply(
            lambda s: [x.strip() for x in str(s).split(",") if x.strip()] if isinstance(s, str) else []
        )

    B = build_bipartite(reviews, businesses, users)
    G_restaurant = project_restaurant_restaurant(B)
    G_reviewer = project_reviewer_reviewer(B)
    city_user_ids = set(reviews["user_id"].unique())
    G_friend = build_friend_graph(users, city_user_ids)

    save_graphs(B, G_restaurant, G_reviewer, G_friend, out_dir=out_dir)
    print(f"  Bipartite: {B.number_of_nodes()} nodes, {B.number_of_edges()} edges")
    print(f"  Restaurant projection: {G_restaurant.number_of_nodes()} nodes, {G_restaurant.number_of_edges()} edges")
    print(f"  Reviewer projection: {G_reviewer.number_of_nodes() if G_reviewer else 0} nodes")
    print(f"  Friend graph: {G_friend.number_of_nodes()} nodes, {G_friend.number_of_edges()} edges")
    return B, G_restaurant, G_reviewer, G_friend
