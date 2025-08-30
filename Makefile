# IT Glue MCP Server - Makefile
# Development automation and common tasks

.PHONY: help setup install dev test lint format clean docker-build docker-run docker-stop migrate sync

# Default target - show help
help:
	@echo "IT Glue MCP Server - Development Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup          - Complete development environment setup"
	@echo "  make install        - Install Python dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev            - Run development servers (all services)"
	@echo "  make run-mcp        - Run MCP server only"
	@echo "  make run-api        - Run API server only"
	@echo "  make run-ui         - Run Streamlit UI only"
	@echo "  make run-worker     - Run Celery worker"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make lint           - Run code linters"
	@echo "  make format         - Format code with black"
	@echo "  make type-check     - Run mypy type checking"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   - Build Docker images"
	@echo "  make docker-run     - Run with Docker Compose"
	@echo "  make docker-stop    - Stop Docker containers"
	@echo "  make docker-clean   - Remove Docker volumes"
	@echo ""
	@echo "Database:"
	@echo "  make migrate        - Run database migrations"
	@echo "  make migrate-create - Create new migration"
	@echo "  make db-reset       - Reset database (WARNING: destructive)"
	@echo ""
	@echo "Data Operations:"
	@echo "  make sync           - Sync IT Glue data"
	@echo "  make embeddings     - Generate embeddings"
	@echo "  make cache-clear    - Clear Redis cache"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make logs           - Show application logs"
	@echo "  make shell          - Python shell with app context"
	@echo "  make health         - Check system health"

# Setup complete development environment
setup: install migrate
	@echo "Setting up development environment..."
	@cp -n .env.example .env || true
	@mkdir -p logs data/uploads data/exports
	@echo "Checking Docker services..."
	@docker-compose -f docker-compose.dev.yml up -d postgres redis qdrant
	@echo "Waiting for services to start..."
	@sleep 10
	@echo "✅ Development environment ready!"
	@echo "Edit .env file with your IT Glue API credentials"

# Install Python dependencies
install:
	@echo "Installing Python dependencies..."
	@if [ -f "pyproject.toml" ]; then \
		poetry install; \
	else \
		pip install -r requirements.txt; \
		pip install -r requirements-dev.txt; \
	fi
	@pre-commit install
	@echo "✅ Dependencies installed"

# Run development servers
dev:
	@echo "Starting all development services..."
	@docker-compose -f docker-compose.dev.yml up -d
	@sleep 5
	@make migrate
	@echo "Starting application servers..."
	@honcho start

# Run individual services
run-mcp:
	@echo "Starting MCP server..."
	@python -m src.main

run-api:
	@echo "Starting API server..."
	@uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

run-ui:
	@echo "Starting Streamlit UI..."
	@streamlit run streamlit/app.py --server.port 8501

run-worker:
	@echo "Starting Celery worker..."
	@celery -A src.workers.celery_app worker --loglevel=info

# Testing commands
test:
	@echo "Running all tests..."
	@pytest tests/ -v

test-unit:
	@echo "Running unit tests..."
	@pytest tests/unit/ -v

test-integration:
	@echo "Running integration tests..."
	@pytest tests/integration/ -v

test-coverage:
	@echo "Running tests with coverage..."
	@pytest tests/ --cov=src --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/"

test-mcp:
	@echo "Testing MCP protocol..."
	@python tests/test_mcp_protocol.py

# Code quality commands
lint:
	@echo "Running linters..."
	@ruff check src/ tests/
	@flake8 src/ tests/ --max-line-length=88

format:
	@echo "Formatting code..."
	@black src/ tests/ streamlit/
	@isort src/ tests/ streamlit/
	@echo "✅ Code formatted"

type-check:
	@echo "Running type checking..."
	@mypy src/ --ignore-missing-imports

# Docker commands
docker-build:
	@echo "Building Docker images..."
	@docker-compose build

docker-run:
	@echo "Starting Docker containers..."
	@docker-compose up -d
	@echo "Services running at:"
	@echo "  - API: http://localhost:8000"
	@echo "  - UI: http://localhost:8501"
	@echo "  - PostgreSQL: localhost:5432"
	@echo "  - Redis: localhost:6379"
	@echo "  - Qdrant: http://localhost:6333"

docker-stop:
	@echo "Stopping Docker containers..."
	@docker-compose down

docker-clean:
	@echo "⚠️  WARNING: This will delete all Docker volumes!"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		echo "✅ Docker volumes removed"; \
	fi

# Database commands
migrate:
	@echo "Running database migrations..."
	@alembic upgrade head
	@echo "✅ Migrations applied"

migrate-create:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

db-reset:
	@echo "⚠️  WARNING: This will delete all data!"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		alembic downgrade base; \
		alembic upgrade head; \
		python scripts/seed_data.py; \
		echo "✅ Database reset complete"; \
	fi

# Data operations
sync:
	@echo "Syncing IT Glue data..."
	@python scripts/sync_data.py

sync-org:
	@read -p "Enter organization ID: " org_id; \
	python scripts/sync_data.py --org-id $$org_id

embeddings:
	@echo "Generating embeddings..."
	@python scripts/generate_embeddings.py

cache-clear:
	@echo "Clearing Redis cache..."
	@redis-cli FLUSHDB
	@echo "✅ Cache cleared"

# Utility commands
clean:
	@echo "Cleaning build artifacts..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info
	@echo "✅ Clean complete"

logs:
	@docker-compose logs -f --tail=100

logs-app:
	@tail -f logs/app.log

shell:
	@python -c "from src.main import *; import IPython; IPython.embed()"

health:
	@echo "Checking system health..."
	@curl -s http://localhost:8000/health | python -m json.tool

# Production commands
prod-build:
	@echo "Building for production..."
	@docker build -t itglue-mcp-server:latest -f docker/Dockerfile .

prod-deploy:
	@echo "Deploying to production..."
	@kubectl apply -f deployments/kubernetes/

# Development database shortcuts
db-shell:
	@docker-compose exec postgres psql -U postgres -d itglue

redis-cli:
	@docker-compose exec redis redis-cli

# Git hooks
pre-commit:
	@pre-commit run --all-files

# Performance testing
perf-test:
	@echo "Running performance tests..."
	@locust -f tests/performance/locustfile.py --headless -u 10 -r 2 -t 60s --host=http://localhost:8000

# Security scanning
security-scan:
	@echo "Running security scan..."
	@bandit -r src/
	@safety check

# Documentation
docs-serve:
	@echo "Serving documentation..."
	@cd docs && python -m http.server 8080

# Environment validation
check-env:
	@echo "Checking environment variables..."
	@python scripts/check_env.py

# Quick start for new developers
quickstart: setup
	@echo ""
	@echo "🚀 Quick Start Complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env with your IT Glue API credentials"
	@echo "2. Run 'make dev' to start all services"
	@echo "3. Open http://localhost:8501 for the UI"
	@echo "4. Run 'make test' to verify everything works"
	@echo ""
	@echo "Happy coding! 🎉"

.DEFAULT_GOAL := help