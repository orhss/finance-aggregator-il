.PHONY: help api web dev install test lint

# Default target
help:
	@echo "Fin - Personal Finance Dashboard"
	@echo ""
	@echo "Development:"
	@echo "  make install     Install all dependencies"
	@echo "  make dev         Run API + Web in parallel (requires tmux or runs sequentially)"
	@echo "  make api         Run FastAPI on :8002"
	@echo "  make web         Run React dev server on :3002"
	@echo "  make streamlit   Run Streamlit on :8501"
	@echo ""
	@echo "Testing:"
	@echo "  make test        Run all Python tests"
	@echo "  make test-api    Run API tests only"
	@echo "  make lint        Run ruff linter"
	@echo ""
	@echo "Build:"
	@echo "  make build-web   Build React app for production"
	@echo ""
	@echo "Docker:"
	@echo "  make up          Start all services (API + Web + Streamlit)"
	@echo "  make down        Stop all services"
	@echo "  make logs        Tail logs from all services"
	@echo ""
	@echo "CLI:"
	@echo "  make init        Initialize database"
	@echo "  make sync        Sync all financial sources"

# ── Install ──────────────────────────────────────────────────────────────────

install:
	uv sync
	cd web && npm install

# ── Development servers ───────────────────────────────────────────────────────

api:
	uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8002

web:
	cd web && npm run dev

streamlit:
	uv run streamlit run streamlit_app/main.py --server.port 8501

# Run API and Web in parallel (requires make 4.x with --jobs)
dev:
	@echo "Starting API on :8002 and Web on :3002 ..."
	@echo "Press Ctrl+C to stop both"
	@$(MAKE) -j2 api web

# ── Build ─────────────────────────────────────────────────────────────────────

build-web:
	cd web && npm run build

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	uv run pytest

test-api:
	uv run pytest tests/api/ -v

test-services:
	uv run pytest tests/services/ -v

lint:
	uv run ruff check .

# ── Docker ────────────────────────────────────────────────────────────────────

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

build-docker:
	docker compose build

# ── CLI shortcuts ─────────────────────────────────────────────────────────────

init:
	uv run fin-cli init

sync:
	uv run fin-cli sync all
