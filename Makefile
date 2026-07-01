# ──────────────────────────────────────────────────────────────────────────────
# Ambrane AI Voice Support — Developer Makefile
# Usage: make <target>
# ──────────────────────────────────────────────────────────────────────────────

.PHONY: help setup infra start stop restart logs shell test lint format migrate ingest models

help:
	@echo ""
	@echo "  Ambrane AI Voice Support — Make Targets"
	@echo "  ──────────────────────────────────────────"
	@echo "  make setup       First-time full setup"
	@echo "  make infra       Start only databases (postgres, redis, qdrant)"
	@echo "  make start       Start all services"
	@echo "  make stop        Stop all services"
	@echo "  make restart     Restart all services"
	@echo "  make logs        Tail backend logs"
	@echo "  make shell       Open bash in backend container"
	@echo "  make test        Run all tests"
	@echo "  make lint        Lint Python code"
	@echo "  make format      Format Python code"
	@echo "  make migrate     Run database migrations"
	@echo "  make ingest      Ingest knowledge base into Qdrant"
	@echo "  make models      Download AI models (Ollama + HuggingFace)"
	@echo ""

# First-time setup
setup:
	@echo "▶ Copying .env.example → .env"
	cp -n .env.example .env || true
	@echo "▶ Starting infrastructure..."
	docker compose up postgres redis qdrant ollama -d
	@echo "▶ Waiting for postgres..."
	sleep 5
	@echo "▶ Running database migrations..."
	docker compose run --rm backend alembic upgrade head
	@echo "▶ Downloading AI models..."
	$(MAKE) models
	@echo "▶ Ingesting knowledge base..."
	$(MAKE) ingest
	@echo "✅ Setup complete! Run: make start"

# Start only infrastructure databases
infra:
	docker compose up postgres redis qdrant ollama -d
	@echo "✅ Infrastructure started"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Redis:      localhost:6379"
	@echo "  Qdrant:     localhost:6333"
	@echo "  Ollama:     localhost:11434"

# Start all services
start:
	docker compose up -d
	@echo "✅ All services started"
	@echo "  Backend:  http://localhost:8000"
	@echo "  Frontend: http://localhost:3000"
	@echo "  API Docs: http://localhost:8000/docs"

# Stop all services
stop:
	docker compose down

restart:
	docker compose restart backend frontend

# Tail logs
logs:
	docker compose logs -f backend

# Shell into backend
shell:
	docker compose exec backend bash

# Run tests
test:
	docker compose run --rm backend pytest tests/ -v --cov=app --cov-report=term-missing

# Lint
lint:
	docker compose run --rm backend ruff check app/
	docker compose run --rm backend mypy app/ --ignore-missing-imports

# Format
format:
	docker compose run --rm backend black app/ --line-length 100
	docker compose run --rm backend ruff check app/ --fix

# Database migrations
migrate:
	docker compose run --rm backend alembic upgrade head

migrate-create:
	docker compose run --rm backend alembic revision --autogenerate -m "$(name)"

# Ingest knowledge base
ingest:
	docker compose run --rm backend python scripts/ingest_knowledge.py

# Download AI models
models:
	@echo "▶ Pulling Ollama model (Qwen2.5 3B)..."
	docker compose exec ollama ollama pull qwen2.5:3b-instruct-q4_K_M
	@echo "▶ Downloading HuggingFace models..."
	docker compose run --rm backend python scripts/download_models.py
	@echo "✅ Models ready"

# Dev mode (without Docker)
dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev
