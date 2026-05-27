.PHONY: help up down logs install dev api ui worker beat migrate fresh-db test lint format check

help:
	@echo "CliniqAI — common commands"
	@echo "  make install     install python deps with uv"
	@echo "  make up          start postgres + redis + langfuse via docker"
	@echo "  make down        stop docker services"
	@echo "  make logs        tail docker logs"
	@echo "  make migrate     apply alembic migrations"
	@echo "  make fresh-db    drop + recreate db (DESTRUCTIVE)"
	@echo "  make api         run FastAPI on :8000 with reload"
	@echo "  make ui          run Gradio UI on :7860"
	@echo "  make worker      run celery worker"
	@echo "  make beat        run celery beat (reminders)"
	@echo "  make dev         api + ui + worker in parallel (needs tmux)"
	@echo "  make test        pytest"
	@echo "  make lint        ruff check"
	@echo "  make format      ruff format"
	@echo "  make check       lint + mypy contracts + tests"

install:
	uv sync --extra dev

up:
	docker compose -f infra/docker-compose.dev.yml up -d

down:
	docker compose -f infra/docker-compose.dev.yml down

logs:
	docker compose -f infra/docker-compose.dev.yml logs -f --tail=100

migrate:
	alembic -c infra/alembic.ini upgrade head

fresh-db:
	docker compose -f infra/docker-compose.dev.yml down -v
	$(MAKE) up
	sleep 3
	$(MAKE) migrate

api:
	uvicorn app.api.main:app --reload --port 8000

ui:
	python deploy/hf_space/app.py

worker:
	celery -A app.agents.appointment.tasks worker --loglevel=info

beat:
	celery -A app.agents.appointment.tasks beat --loglevel=info

test:
	pytest

lint:
	ruff check app tests

format:
	ruff format app tests

check: lint
	mypy app/contracts.py
	pytest -q
