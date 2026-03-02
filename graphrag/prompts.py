"""System prompt and few-shot Cypher examples for GraphRAG (≥15 question→Cypher pairs)."""

from __future__ import annotations

SYSTEM_PROMPT_TEMPLATE = """You are a Cypher expert for a Neo4j graph of Philadelphia restaurants and reviewers.
Use only the provided schema and relationship types. Return valid Cypher only; no explanation unless asked.

Schema:
{schema}

Guidelines:
- Use MERGE/MATCH; avoid creating new nodes in query results.
- Prefer parameters for user-provided values.
- Return visualization_hint: 'table' | 'network_subgraph' | 'bar_chart' | 'timeline' when appropriate.
"""

FEW_SHOT_EXAMPLES = [
    ("Which restaurants have the highest betweenness centrality?", "MATCH (r:Restaurant) RETURN r.name AS name, r.betweenness AS betweenness ORDER BY r.betweenness DESC LIMIT 10", "table"),
    ("Top 5 elite reviewers by review count?", "MATCH (u:Reviewer) WHERE u.is_elite = true RETURN u.name, u.review_count ORDER BY u.review_count DESC LIMIT 5", "table"),
    ("Restaurants in community 0?", "MATCH (r:Restaurant)-[:BELONGS_TO]->(c:Community {community_id: 0}) RETURN r.name, r.stars, r.k_core LIMIT 20", "table"),
    ("Show me restaurants that share reviewers with Reading Terminal Market.", "MATCH (a:Restaurant {name: 'Reading Terminal Market'})-[e:SHARED_REVIEWERS]-(b:Restaurant) RETURN b.name, e.weight ORDER BY e.weight DESC LIMIT 15", "table"),
    ("Which reviewers are friends with the most elite reviewers?", "MATCH (u:Reviewer)-[:FRIENDS_WITH]-(e:Reviewer) WHERE e.is_elite = true WITH u, count(e) AS elite_friends RETURN u.name, elite_friends ORDER BY elite_friends DESC LIMIT 10", "table"),
    ("Restaurants with the most reviews?", "MATCH (r:Restaurant) RETURN r.name, r.review_count ORDER BY r.review_count DESC LIMIT 10", "table"),
    ("What categories does Restaurant X belong to?", "MATCH (r:Restaurant)-[:IN_CATEGORY]->(c:Category) WHERE r.name CONTAINS $name RETURN r.name, collect(c.name) AS categories", "table"),
    ("Reviewers who reviewed both restaurant A and B?", "MATCH (u:Reviewer)-[:REVIEWED]->(a:Restaurant), (u)-[:REVIEWED]->(b:Restaurant) WHERE a.business_id = $biz_a AND b.business_id = $biz_b RETURN u.name, u.review_count LIMIT 20", "table"),
    ("Restaurants in the highest k-core?", "MATCH (r:Restaurant) WITH max(r.k_core) AS max_core MATCH (r:Restaurant) WHERE r.k_core = max_core RETURN r.name, r.k_core LIMIT 20", "table"),
    ("Subgraph of restaurants in community 5 and links between them?", "MATCH (r:Restaurant)-[:BELONGS_TO]->(c:Community {community_id: 5}) OPTIONAL MATCH (r)-[e:SHARED_REVIEWERS]-(r2:Restaurant) WHERE r.business_id < r2.business_id RETURN r, r2, e LIMIT 100", "network_subgraph"),
    ("How many restaurants per community?", "MATCH (r:Restaurant)-[:BELONGS_TO]->(c:Community) RETURN c.community_id, count(r) AS count ORDER BY count DESC", "bar_chart"),
    ("Hype events for a restaurant?", "MATCH (r:Restaurant)-[:HAD_HYPE_EVENT]->(h:HypeEvent) WHERE r.business_id = $business_id RETURN h.year_month, h.review_count ORDER BY h.year_month", "timeline"),
    ("Restaurants with name containing 'Pizza'?", "MATCH (r:Restaurant) WHERE r.name CONTAINS 'Pizza' RETURN r.name, r.stars, r.review_count LIMIT 20", "table"),
    ("Eigenvector centrality top 10 restaurants?", "MATCH (r:Restaurant) RETURN r.name, r.eigenvector ORDER BY r.eigenvector DESC LIMIT 10", "table"),
    ("Friends of reviewer X?", "MATCH (u:Reviewer {user_id: $user_id})-[:FRIENDS_WITH]-(f:Reviewer) RETURN f.name, f.review_count LIMIT 20", "table"),
]


def build_system_prompt(schema_text: str) -> str:
    """Build full system prompt with schema injected."""
    return SYSTEM_PROMPT_TEMPLATE.format(schema=schema_text)


def get_few_shot_examples() -> list[tuple[str, str, str]]:
    """Return list of (question, cypher, viz_hint)."""
    return FEW_SHOT_EXAMPLES.copy()
