"""GET /api/temporal/growth/{biz_id}, /influence-test — from Neo4j or precomputed JSON."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from neo4j import GraphDatabase
from pipeline.config import DATA_PROCESSED, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER

router = APIRouter()


def _driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


@router.get("/growth/{business_id}")
def get_growth(business_id: str):
    """Monthly review growth for one restaurant. From Neo4j HypeEvents or fallback to CSV."""
    driver = _driver()
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (r:Restaurant {business_id: $bid})-[:HAD_HYPE_EVENT]->(h:HypeEvent) RETURN h.year_month AS year_month, h.review_count AS count ORDER BY h.year_month",
                bid=business_id,
            )
            events = [dict(r) for r in result]
            if events:
                return {"business_id": business_id, "hype_events": events}
    except Exception:
        pass
    finally:
        driver.close()
    # Fallback: temporal_growth.csv if present
    csv_path = DATA_PROCESSED / "temporal_growth.csv"
    if csv_path.exists():
        import csv as csv_mod
        months = []
        with open(csv_path, "r", encoding="utf-8") as f:
            for row in csv_mod.DictReader(f):
                if row.get("business_id") == business_id:
                    months.append({"year_month": row.get("year_month"), "count": int(row.get("count", 0)), "cumulative": int(row.get("cumulative", 0))})
        months.sort(key=lambda x: x["year_month"])
        return {"business_id": business_id, "months": months}
    raise HTTPException(status_code=404, detail="No growth data for this business.")


@router.get("/influence-test")
def get_influence_test():
    """Pre-computed homophily vs influence (Jaccard) results."""
    import json
    path = DATA_PROCESSED / "influence_test_results.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run pipeline to generate influence_test_results.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
