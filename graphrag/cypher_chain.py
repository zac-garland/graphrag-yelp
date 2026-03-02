"""NL-to-Cypher pipeline: schema injection, query validation with retry, answer + viz_hint."""

from __future__ import annotations

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from pipeline.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER

from graphrag.prompts import build_system_prompt, get_few_shot_examples
from graphrag.schema import get_schema_text


def _run_cypher(uri: str, user: str, password: str, query: str) -> list[dict[str, Any]]:
    """Execute Cypher and return list of records (dicts)."""
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            result = session.run(query)
            return [dict(record) for record in result]
    finally:
        driver.close()


def _extract_cypher(text: str) -> str | None:
    """Extract Cypher from model output (strip markdown code block if present)."""
    text = (text or "").strip()
    if "```cypher" in text:
        start = text.index("```cypher") + len("```cypher")
        end = text.index("```", start) if "```" in text[start:] else len(text)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start) if "```" in text[start:] else len(text)
        return text[start:end].strip()
    return text if text else None


def _infer_viz_hint(question: str, cypher: str) -> str:
    """Infer visualization hint from question or query (table, network_subgraph, bar_chart, timeline)."""
    q = (question + " " + cypher).lower()
    if "subgraph" in q or "network" in q or "link" in q or "connection" in q:
        return "network_subgraph"
    if "over time" in q or "timeline" in q or "hype" in q or "year_month" in q:
        return "timeline"
    if "count" in q or "how many" in q or "per community" in q or "distribution" in q:
        return "bar_chart"
    return "table"


def query_graph_rag(
    question: str,
    *,
    max_retries: int = 2,
    schema_text: str | None = None,
) -> dict[str, Any]:
    """
    Turn natural language into Cypher, run it, return answer + cypher_used + nodes_returned + visualization_hint.
    Retries up to max_retries on Cypher syntax error.
    """
    import os
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "answer": "ANTHROPIC_API_KEY not set. Cannot run GraphRAG.",
            "cypher_used": None,
            "nodes_returned": 0,
            "visualization_hint": "table",
        }
    schema_text = schema_text or get_schema_text()
    system = build_system_prompt(schema_text)
    examples = get_few_shot_examples()
    examples_block = "\n".join([f"Q: {q}\nCypher: {c}\nViz: {v}" for q, c, v in examples])
    prompt_text = f"""{system}

Few-shot examples:
{examples_block}

User question: {question}
Return only a single Cypher query (no markdown unless wrapped in ```cypher)."""
    llm = ChatAnthropic(model="claude-sonnet-4-20250514", api_key=api_key)
    cypher_used = None
    for attempt in range(max_retries + 1):
        try:
            response = llm.invoke(prompt_text)
            cypher = _extract_cypher(response.content if hasattr(response, "content") else str(response))
            cypher_used = cypher
            if not cypher:
                return {"answer": "Could not extract Cypher from model.", "cypher_used": None, "nodes_returned": 0, "visualization_hint": "table"}
            records = _run_cypher(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, cypher)
            # Second LLM call to turn records into natural language answer
            answer_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a concise assistant. Summarize the Cypher results in 1-3 sentences."),
                ("human", "Question: {question}\nCypher: {cypher}\nResults (first 20 rows): {results}\nAnswer:"),
            ])
            chain = answer_prompt | llm | StrOutputParser()
            results_preview = str(records[:20])
            answer = chain.invoke({"question": question, "cypher": cypher, "results": results_preview})
            return {
                "answer": answer,
                "cypher_used": cypher,
                "nodes_returned": len(records),
                "visualization_hint": _infer_viz_hint(question, cypher),
            }
        except Exception as e:
            if attempt < max_retries and ("SyntaxError" in str(type(e).__name__) or "syntax" in str(e).lower()):
                continue
            return {
                "answer": f"Error running query: {e}",
                "cypher_used": cypher_used,
                "nodes_returned": 0,
                "visualization_hint": "table",
            }
    return {"answer": "Max retries exceeded.", "cypher_used": None, "nodes_returned": 0, "visualization_hint": "table"}
