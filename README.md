# Restaurant Hype Networks — GraphRAG

Full-stack GraphRAG application modeling **Philadelphia's** restaurant hype ecosystem using the Yelp Open Dataset. Builds bipartite and projected networks, computes graph metrics, loads into Neo4j, and exposes a conversational AI interface with interactive visualizations.

**Target city:** Philadelphia (largest restaurant footprint in the Yelp Open Dataset; Austin is not available in this dataset).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
# Optional: copy .env.example to .env and set TARGET_CITY, YELP_DATA_PATH, Neo4j, ANTHROPIC_API_KEY
python -m pipeline.run   # Phase 1: ingest → network → metrics → temporal
```

**Phase 2–4 (Neo4j + GraphRAG + API):**
```bash
# In .env set NEO4J_PASSWORD, ANTHROPIC_API_KEY
docker compose up -d              # Start Neo4j (APOC)
python -m pipeline.load_neo4j     # Bulk load graph into Neo4j
uvicorn api.main:app --reload --port 8081   # FastAPI: /docs for Swagger
```

**Phase 5 (Frontend):**
```bash
cd frontend && npm run dev        # Next.js at http://localhost:3000
```
Then open http://localhost:3000: chat (GraphRAG), Graph tab (Cytoscape), Dashboard (KPIs + betweenness), Temporal (influence test).

**Full-stack order (for new clones):** (1) Pipeline → `data/processed/`; (2) `docker compose up -d` and `python -m pipeline.load_neo4j`; (3) API on 8081; (4) Frontend on 3000. The frontend expects the API at `http://localhost:8081`.

**Makefile (optional):** From repo root, `make up` (Neo4j), `make load` (load graph), `make api` (FastAPI on 8081), `make frontend` (Next.js on 3000).

- **Step-by-step build plan:** `ref/Restaurant_Hype_GraphRAG_Build_Plan.docx`
- **Cursor rules / phase summary:** `contex.cursorules`
- **Student guide (data + pipeline):** [docs/STUDENT_SETUP_GUIDE.md](docs/STUDENT_SETUP_GUIDE.md) — download Yelp dataset, place in repo, run pipeline to generate `data/processed/`.
- **Docker + Neo4j basics:** [docs/DOCKER_AND_NEO4J_BASICS.md](docs/DOCKER_AND_NEO4J_BASICS.md) — first-time Docker/Neo4j: install, set password, start Neo4j, load graph, open Browser.

## Project structure

- `data/processed/` — Output CSVs from the pipeline (gitignored).
- `pipeline/` — Ingest, network, metrics, temporal (Phase 1); `load_neo4j` (Phase 2).
- `graphrag/` — Schema introspection, Cypher chain, prompts, retriever (Phase 3).
- `api/` — FastAPI: `/api/chat`, `/api/graph/*`, `/api/metrics/*`, `/api/temporal/*`, `/api/stats` (Phase 4).
- `frontend/` — Next.js app (Phase 5).

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_CITY` | `Philadelphia` | City to filter businesses and reviews. |
| `YELP_DATA_PATH` | `Yelp JSON/yelp_dataset` | Path to extracted Yelp JSON files (relative to project root). |

See `.env.example` for Neo4j and API keys.

## Git hooks

A **pre-commit** hook blocks commits if any staged file is larger than 95 MB (under GitHub’s 100 MB limit). Hooks live in `.githooks/`; this repo uses `core.hooksPath` so they run automatically.

- **Limit:** default 95 MB. Override: `GIT_MAX_FILE_SIZE=<bytes> git commit ...` (bytes).
- **Disable once:** `git commit --no-verify`
- **Disable hooks path:** `git config --unset core.hooksPath`
