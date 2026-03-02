"""FastAPI app: CORS, middleware, routers for chat, graph, metrics, temporal, stats."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import chat, graph, metrics, stats, temporal

app = FastAPI(title="Restaurant Hype GraphRAG API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(temporal.router, prefix="/api/temporal", tags=["temporal"])
app.include_router(stats.router, prefix="/api", tags=["stats"])


@app.get("/")
def root():
    return {"service": "restaurant-hype-graphrag", "docs": "/docs"}
