.PHONY: up down migrate seed dev batch check fmt

up:
	docker compose up -d

down:
	docker compose down

migrate:
	uv run alembic upgrade head

seed:
	uv run python -m geointel.scripts.ingest_admin_units
	uv run python -m geointel.scripts.ingest_cropland_mask

dev:
	uv run uvicorn geointel.api.main:app --reload

batch:
	uv run python -m geointel.batch.run_daily

check:
	uv run ruff check .
	uv run mypy geointel
	uv run pytest

fmt:
	uv run ruff format .

install:
	uv pip install -e .[dev]

init-db:
	docker-compose exec -T db psql -U user -d geointel -c 'CREATE EXTENSION IF NOT EXISTS postgis;'

alembic-revision:
	uv run alembic revision --autogenerate -m "$(m)"