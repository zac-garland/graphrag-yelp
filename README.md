# Restaurant Hype Networks — GraphRAG

Full-stack GraphRAG application modeling **Philadelphia's** restaurant hype ecosystem using the Yelp Open Dataset. Builds bipartite and projected networks, computes graph metrics, loads into Neo4j, and exposes a conversational AI interface with interactive visualizations.

**Target city:** Philadelphia (largest restaurant footprint in the Yelp Open Dataset; Austin is not available in this dataset).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
# Optional: copy .env.example to .env and set TARGET_CITY, YELP_DATA_PATH, Neo4j, API keys
python -m pipeline.run   # Full Phase 1 pipeline (ingest → network → metrics → temporal)
```

- **Step-by-step build plan:** `ref/Restaurant_Hype_GraphRAG_Build_Plan.docx`
- **Cursor rules / phase summary:** `contex.cursorules`
- **Student guide (data + pipeline):** [docs/STUDENT_SETUP_GUIDE.md](docs/STUDENT_SETUP_GUIDE.md) — download Yelp dataset, place in repo, run pipeline to generate `data/processed/`.

## Project structure

- `data/processed/` — Output CSVs from the pipeline (city businesses, reviews, users, graphs, metrics, temporal).
- `pipeline/` — Data ingest, network construction, metrics, temporal analysis (Phase 1).
- `graphrag/` — Neo4j schema + NL-to-Cypher RAG (Phase 3).
- `api/` — FastAPI backend (Phase 4).
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
