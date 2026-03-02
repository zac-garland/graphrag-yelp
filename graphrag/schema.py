"""Neo4j schema introspection for LLM context. GraphRAG needs full schema to generate valid Cypher."""

from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase

from pipeline.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER


def get_driver():
    """Return Neo4j driver. Caller must close."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def introspect_schema(driver: Any) -> str:
    """
    Introspect Neo4j labels, relationship types, and property keys.
    Returns a string description for injection into the LLM system prompt.
    """
    with driver.session() as session:
        # Node labels
        labels_result = session.run("CALL db.labels()")
        labels = [r["label"] for r in labels_result]
        # Relationship types
        rel_result = session.run("CALL db.relationshipTypes()")
        rel_types = [r["relationshipType"] for r in rel_result]
        # Sample node structure per label
        schema_parts = [
            "Node labels: " + ", ".join(labels),
            "Relationship types: " + ", ".join(rel_types),
        ]
        for label in labels:
            r = session.run(
                f"MATCH (n:{label}) RETURN n LIMIT 1"
            ).single()
            if r and r["n"]:
                props = list(r["n"].keys())
                schema_parts.append(f"  {label} properties (example): {', '.join(props)}")
        return "\n".join(schema_parts)


def get_schema_text(uri: str | None = None, user: str | None = None, password: str | None = None) -> str:
    """Connect with optional overrides and return schema string. Closes driver."""
    uri = uri or NEO4J_URI
    user = user or NEO4J_USER
    password = password or NEO4J_PASSWORD
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        return introspect_schema(driver)
    finally:
        driver.close()
