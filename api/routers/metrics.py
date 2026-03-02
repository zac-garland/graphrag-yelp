"""GET /api/metrics/centrality, /kcore — from Neo4j."""

from fastapi import APIRouter, Query

from neo4j import GraphDatabase
from pipeline.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER

router = APIRouter()


def _driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


@router.get("/centrality")
def get_centrality(
    centrality_type: str = Query("betweenness", description="betweenness | eigenvector"),
    limit: int = Query(20, le=100),
):
    """Top-N nodes by centrality type."""
    driver = _driver()
    try:
        with driver.session() as session:
            prop = "betweenness" if centrality_type == "betweenness" else "eigenvector"
            result = session.run(
                f"MATCH (r:Restaurant) WHERE r.{prop} IS NOT NULL RETURN r.name AS name, r.{prop} AS value ORDER BY r.{prop} DESC LIMIT $limit",
                limit=limit,
            )
            rankings = [dict(r) for r in result]
            return {"rankings": rankings}
    finally:
        driver.close()


@router.get("/kcore")
def get_kcore():
    """K-core shell distribution (count per k)."""
    driver = _driver()
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (r:Restaurant) WITH r.k_core AS k, count(r) AS count RETURN k, count ORDER BY k DESC"
            )
            shells = {r["k"]: r["count"] for r in result}
            return {"shells": shells}
    finally:
        driver.close()
