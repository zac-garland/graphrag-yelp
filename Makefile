# Restaurant Hype GraphRAG — common commands
# Usage: make setup | pipeline | up | seed | load

.PHONY: setup pipeline up seed load api

setup:
	python -m venv .venv
	@echo "Run: source .venv/bin/activate && pip install -e ."

pipeline:
	python -m pipeline.run

up:
	docker compose up -d

seed: load

load:
	python -m pipeline.load_neo4j

api:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8081

frontend:
	cd frontend && npm run dev
