"""GET /api/graph/nodes, /edges, /community/{id} — graph data from Neo4j."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from neo4j import GraphDatabase
from pipeline.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER

router = APIRouter()


def _driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


@router.get("/nodes")
def get_nodes(community_id: Optional[int] = Query(None), limit: int = Query(200, le=2000)):
    """Return top-betweenness restaurants with at least one SHARED_REVIEWERS edge (no isolates). Optional filter by community_id."""
    driver = _driver()
    try:
        with driver.session() as session:
            if community_id is not None:
                result = session.run(
                    """
                    MATCH (r:Restaurant)-[:BELONGS_TO]->(c:Community {community_id: $cid})
                    WHERE (r)-[:SHARED_REVIEWERS]-()
                    RETURN r
                    ORDER BY r.betweenness DESC
                    LIMIT $limit
                    """,
                    cid=community_id,
                    limit=limit,
                )
            else:
                result = session.run(
                    """
                    MATCH (r:Restaurant)
                    WHERE (r)-[:SHARED_REVIEWERS]-()
                    RETURN r
                    ORDER BY r.betweenness DESC
                    LIMIT $limit
                    """,
                    limit=limit,
                )
            nodes = []
            for rec in result:
                r = rec["r"]
                nodes.append({k: r[k] for k in r.keys()} if hasattr(r, "keys") else dict(r))
            return {"nodes": nodes, "total": len(nodes)}
    finally:
        driver.close()


@router.get("/edges")
def get_edges(
    community_id: Optional[int] = Query(None),
    limit: int = Query(1000, le=5000),
    node_ids: Optional[str] = Query(
        None,
        description="Comma-separated business_id list; only return edges between these nodes",
    ),
    min_weight: int = Query(
        5,
        ge=1,
        description="Minimum SHARED_REVIEWERS weight for an edge to be included",
    ),
):
    """Return SHARED_REVIEWERS edges; optional filter by community or by node set (so edges match dashboard nodes).

    A default min_weight of 5 reduces visual clutter by dropping very weak ties.
    """
    ids_list = [x.strip() for x in node_ids.split(",")] if node_ids else None
    if ids_list is not None and len(ids_list) > 5000:
        ids_list = ids_list[:5000]
    driver = _driver()
    try:
        with driver.session() as session:
            if ids_list:
                result = session.run(
                    """
                    MATCH (a:Restaurant)-[e:SHARED_REVIEWERS]-(b:Restaurant)
                    WHERE a.business_id IN $ids AND b.business_id IN $ids AND e.weight >= $min_weight
                    RETURN a.business_id AS source, b.business_id AS target, e.weight AS weight
                    LIMIT $limit
                    """,
                    ids=ids_list,
                    min_weight=min_weight,
                    limit=limit,
                )
            elif community_id is not None:
                result = session.run(
                    """
                    MATCH (a:Restaurant)-[e:SHARED_REVIEWERS]-(b:Restaurant)
                    WHERE (a)-[:BELONGS_TO]->(:Community {community_id: $cid})
                      AND (b)-[:BELONGS_TO]->(:Community {community_id: $cid})
                      AND e.weight >= $min_weight
                    RETURN a.business_id AS source, b.business_id AS target, e.weight AS weight
                    LIMIT $limit
                    """,
                    cid=community_id,
                    min_weight=min_weight,
                    limit=limit,
                )
            else:
                result = session.run(
                    """
                    MATCH (a:Restaurant)-[e:SHARED_REVIEWERS]-(b:Restaurant)
                    WHERE e.weight >= $min_weight
                    RETURN a.business_id AS source, b.business_id AS target, e.weight AS weight
                    LIMIT $limit
                    """,
                    min_weight=min_weight,
                    limit=limit,
                )
            edges = [dict(r) for r in result]
            return {"edges": edges}
    finally:
        driver.close()


@router.get("/communities")
def list_communities():
    """Return list of community_id with restaurant count for the filter dropdown."""
    driver = _driver()
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (r:Restaurant)-[:BELONGS_TO]->(c:Community)
                WITH c, count(r) AS restaurant_count
                WHERE restaurant_count > 1
                RETURN c.community_id AS community_id, restaurant_count
                ORDER BY restaurant_count DESC
                """
            )
            rows = [dict(r) for r in result]
            return {"communities": rows}
    finally:
        driver.close()


@router.get("/community/{community_id}")
def get_community(community_id: int):
    """Full community detail: members, optional internal density/bridges."""
    driver = _driver()
    try:
        with driver.session() as session:
            members = session.run(
                "MATCH (r:Restaurant)-[:BELONGS_TO]->(c:Community {community_id: $cid}) RETURN r.business_id, r.name, r.stars, r.k_core",
                cid=community_id,
            )
            restaurants = [dict(r) for r in members]
            return {"community_id": community_id, "restaurants": restaurants}
    finally:
        driver.close()
