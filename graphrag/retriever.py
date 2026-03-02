"""Hybrid retriever: prefer Cypher; fallback to keyword + fulltext search if Cypher fails."""

from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase

from pipeline.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER


def fulltext_search_restaurants(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """
    Fallback: keyword extraction (use query as-is) + fulltext search on Restaurant(name).
    Requires fulltext index on Restaurant(name). If index missing, falls back to CONTAINS.
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            # Try fulltext first (Neo4j 5)
            try:
                result = session.run(
                    "CALL db.index.fulltext.queryNodes('restaurant_name', $q) YIELD node RETURN node.name AS name, node.business_id AS business_id LIMIT $limit",
                    q=query,
                    limit=limit,
                )
                return [dict(r) for r in result]
            except Exception:
                pass
            # Fallback: CONTAINS
            result = session.run(
                "MATCH (r:Restaurant) WHERE r.name CONTAINS $q RETURN r.name AS name, r.business_id AS business_id LIMIT $limit",
                q=query[:100],
                limit=limit,
            )
            return [dict(r) for r in result]
    finally:
        driver.close()
