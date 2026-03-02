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
def get_nodes(community_id: Optional[int] = Query(None), limit: int = Query(500, le=2000)):
    """Return restaurant nodes; optional filter by community_id."""
    driver = _driver()
    try:
        with driver.session() as session:
            if community_id is not None:
                result = session.run(
                    "MATCH (r:Restaurant)-[:BELONGS_TO]->(c:Community {community_id: $cid}) RETURN r LIMIT $limit",
                    cid=community_id,
                    limit=limit,
                )
            else:
                result = session.run("MATCH (r:Restaurant) RETURN r LIMIT $limit", limit=limit)
            nodes = []
            for rec in result:
                r = rec["r"]
                nodes.append({k: r[k] for k in r.keys()} if hasattr(r, "keys") else dict(r))
            return {"nodes": nodes, "total": len(nodes)}
    finally:
        driver.close()


@router.get("/edges")
def get_edges(community_id: Optional[int] = Query(None), limit: int = Query(1000, le=5000)):
    """Return SHARED_REVIEWERS edges; optional filter by community."""
    driver = _driver()
    try:
        with driver.session() as session:
            if community_id is not None:
                result = session.run(
                    """
                    MATCH (a:Restaurant)-[e:SHARED_REVIEWERS]-(b:Restaurant)
                    WHERE (a)-[:BELONGS_TO]->(:Community {community_id: $cid}) AND (b)-[:BELONGS_TO]->(:Community {community_id: $cid})
                    RETURN a.business_id AS source, b.business_id AS target, e.weight AS weight
                    LIMIT $limit
                    """,
                    cid=community_id,
                    limit=limit,
                )
            else:
                result = session.run(
                    "MATCH (a:Restaurant)-[e:SHARED_REVIEWERS]-(b:Restaurant) RETURN a.business_id AS source, b.business_id AS target, e.weight AS weight LIMIT $limit",
                    limit=limit,
                )
            edges = [dict(r) for r in result]
            return {"edges": edges}
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
