"""POST /api/chat — GraphRAG query. Returns answer, cypher_used, viz_hint."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from graphrag.cypher_chain import query_graph_rag

router = APIRouter()


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    cypher_used: Optional[str] = None
    nodes_returned: int = 0
    visualization_hint: str = "table"


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = query_graph_rag(request.question)
    return ChatResponse(
        answer=result["answer"],
        cypher_used=result.get("cypher_used"),
        nodes_returned=result.get("nodes_returned", 0),
        visualization_hint=result.get("visualization_hint", "table"),
    )
