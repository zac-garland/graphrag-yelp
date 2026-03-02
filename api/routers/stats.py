"""GET /api/stats — dashboard summary (nodes, edges, communities, top metrics)."""

from neo4j import GraphDatabase

from pipeline.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER

from fastapi import APIRouter

router = APIRouter()


def _driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


@router.get("/stats")
def get_stats():
    """Dashboard summary: total nodes, edges, communities."""
    driver = _driver()
    try:
        with driver.session() as session:
            n_rest = session.run("MATCH (r:Restaurant) RETURN count(r) AS c").single()["c"]
            n_reviewers = session.run("MATCH (r:Reviewer) RETURN count(r) AS c").single()["c"]
            n_communities = session.run("MATCH (c:Community) RETURN count(c) AS c").single()["c"]
            n_edges = session.run("MATCH ()-[e:SHARED_REVIEWERS]-() RETURN count(e)/2 AS c").single()["c"]
            top_betweenness = session.run(
                "MATCH (r:Restaurant) RETURN r.name AS name, r.betweenness AS betweenness ORDER BY r.betweenness DESC LIMIT 5"
            )
            top = [dict(r) for r in top_betweenness]
            return {
                "summary": {
                    "restaurants": n_rest,
                    "reviewers": n_reviewers,
                    "communities": n_communities,
                    "shared_reviewer_edges": int(n_edges) if n_edges else 0,
                },
                "top_betweenness": top,
            }
    finally:
        driver.close()
