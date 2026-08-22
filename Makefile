.PHONY: setup backend-dev web-dev openapi api-types contracts-check test lint typecheck infra-up infra-down

setup:
	uv sync
	pnpm install

backend-dev:
	uv run --package stock-research-backend uvicorn stock_research.main:app --reload

web-dev:
	pnpm --filter @stock-research/web dev

openapi:
	uv run python scripts/export_openapi.py

api-types: openapi
	pnpm --filter @stock-research/api-types generate

contracts-check: openapi api-types
	git diff --exit-code

test:
	uv run pytest
	pnpm test

lint:
	uv run ruff check .
	pnpm lint

typecheck:
	uv run mypy .
	pnpm typecheck

infra-up:
	docker compose up -d postgres redis minio etcd minio-milvus milvus neo4j

infra-down:
	docker compose down
