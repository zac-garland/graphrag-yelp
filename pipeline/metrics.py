"""Compute graph metrics: centrality, k-core, Louvain communities; attach to nodes and save."""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import pandas as pd

from pipeline.config import DATA_PROCESSED, ensure_dirs

try:
    import community as community_louvain
except ImportError:
    community_louvain = None  # type: ignore[assignment]


def add_degree_centrality_bipartite(B: nx.Graph) -> nx.Graph:
    """Degree centrality on bipartite: reviewer degree = restaurants visited, restaurant degree = unique reviewers."""
    for n in B.nodes():
        B.nodes[n]["degree"] = B.degree(n)
    return B


def add_betweenness_centrality(G: nx.Graph, weight: str | None = "weight") -> nx.Graph:
    """Betweenness centrality on projected graph (identifies cross-cluster bridges)."""
    bc = nx.betweenness_centrality(G, weight=weight)
    for n, v in bc.items():
        G.nodes[n]["betweenness"] = v
    return G


def add_eigenvector_centrality(G: nx.Graph, weight: str | None = "weight") -> nx.Graph:
    """Eigenvector centrality on projected restaurant graph (prestige via influential reviewers)."""
    try:
        ec = nx.eigenvector_centrality(G, weight=weight or "weight", max_iter=500)
    except (nx.PowerIterationFailedConvergence, nx.NetworkXError):
        ec = {n: 0.0 for n in G.nodes()}
    for n, v in ec.items():
        G.nodes[n]["eigenvector"] = v
    return G


def add_k_core(G: nx.Graph, weight: str | None = "weight") -> nx.Graph:
    """K-core decomposition; assign k_core number to each node."""
    try:
        core = nx.core_number(G)
    except Exception:
        core = {n: 0 for n in G.nodes()}
    for n, k in core.items():
        G.nodes[n]["k_core"] = k
    return G


def add_louvain_communities(G: nx.Graph, weight: str | None = "weight") -> nx.Graph:
    """Louvain community detection; label each node with community_id. Requires python-louvain."""
    if community_louvain is None:
        for n in G.nodes():
            G.nodes[n]["community_id"] = 0
        return G
    partition = community_louvain.best_partition(G, weight=weight)
    for n, cid in partition.items():
        G.nodes[n]["community_id"] = cid
    return G


def _communities_from_node_attr(G: nx.Graph, attr: str = "community_id") -> list[set]:
    """Build list of node sets from community_id on nodes."""
    from collections import defaultdict
    by_comm: dict[int, set] = defaultdict(set)
    for n in G.nodes():
        cid = G.nodes[n].get(attr, 0)
        by_comm[cid].add(n)
    return list(by_comm.values())


def modularity(G: nx.Graph, weight: str | None = "weight") -> float:
    """Modularity of the current community assignment (community_id on nodes)."""
    if not G.nodes():
        return 0.0
    if "community_id" not in next(iter(G.nodes(data=True)), [None, {}])[1]:
        return 0.0
    try:
        communities = _communities_from_node_attr(G)
        return float(nx.community.modularity(G, communities, weight=weight))
    except Exception:
        return 0.0


def compute_all_metrics(
    B: nx.Graph,
    G_restaurant: nx.Graph,
    G_reviewer: nx.Graph | None,
    G_friend: nx.Graph | None,
    *,
    out_dir: Path | None = None,
) -> None:
    """
    Compute degree on bipartite; betweenness, eigenvector, k-core, Louvain on restaurant projection;
    k-core, Louvain on reviewer projection and friend graph. Save node CSVs with metrics.
    """
    out_dir = out_dir or DATA_PROCESSED
    ensure_dirs()

    add_degree_centrality_bipartite(B)
    add_betweenness_centrality(G_restaurant, weight="weight")
    add_eigenvector_centrality(G_restaurant, weight="weight")
    add_k_core(G_restaurant, weight="weight")
    add_louvain_communities(G_restaurant, weight="weight")
    mod_r = modularity(G_restaurant, weight="weight")
    print(f"  Restaurant graph modularity: {mod_r:.4f}")

    if G_reviewer and G_reviewer.number_of_nodes() > 0:
        for n in G_reviewer.nodes():
            G_reviewer.nodes[n]["degree"] = G_reviewer.degree(n)
        add_k_core(G_reviewer, weight="weight")
        add_louvain_communities(G_reviewer, weight="weight")

    if G_friend and G_friend.number_of_nodes() > 0:
        add_k_core(G_friend)
        add_louvain_communities(G_friend)

    # Save restaurant nodes with all metrics (for Neo4j and dashboard)
    rest_nodes = [
        dict(id=n, **{k: v for k, v in G_restaurant.nodes[n].items()})
        for n in G_restaurant.nodes()
    ]
    pd.DataFrame(rest_nodes).to_csv(out_dir / "restaurant_projection_nodes.csv", index=False)
    # Overwrite edges to keep weight
    pd.DataFrame(
        [{"source": u, "target": v, **d} for u, v, d in G_restaurant.edges(data=True)]
    ).to_csv(out_dir / "restaurant_projection_edges.csv", index=False)

    if G_reviewer and G_reviewer.number_of_nodes() > 0:
        rev_nodes = [
            dict(id=n, **{k: v for k, v in G_reviewer.nodes[n].items()})
            for n in G_reviewer.nodes()
        ]
        pd.DataFrame(rev_nodes).to_csv(out_dir / "reviewer_projection_nodes.csv", index=False)
    if G_friend and G_friend.number_of_nodes() > 0:
        friend_nodes = [
            dict(id=n, **{k: v for k, v in G_friend.nodes[n].items()})
            for n in G_friend.nodes()
        ]
        pd.DataFrame(friend_nodes).to_csv(out_dir / "friend_nodes.csv", index=False)
    print(f"  Wrote {out_dir / 'restaurant_projection_nodes.csv'} (with metrics)")
