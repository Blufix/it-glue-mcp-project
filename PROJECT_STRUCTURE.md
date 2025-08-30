# IT Glue MCP Server - Project Structure

## Directory Tree

```
itglue-mcp-server/
├── src/                           # Source code
│   ├── __init__.py
│   ├── main.py                   # Application entry point
│   │
│   ├── mcp/                      # MCP Protocol Implementation
│   │   ├── __init__.py
│   │   ├── server.py             # MCP server core
│   │   ├── handlers.py           # Request handlers
│   │   ├── tools.py              # Tool definitions
│   │   └── protocol.py           # Protocol utilities
│   │
│   ├── api/                      # REST API Layer
│   │   ├── __init__.py
│   │   ├── app.py                # FastAPI application
│   │   ├── endpoints/            # API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── query.py          # Query endpoints
│   │   │   ├── health.py         # Health checks
│   │   │   └── admin.py          # Admin endpoints
│   │   ├── middleware/           # API middleware
│   │   │   ├── __init__.py
│   │   │   ├── auth.py           # Authentication
│   │   │   ├── rate_limit.py     # Rate limiting
│   │   │   └── logging.py        # Request logging
│   │   └── dependencies.py       # Dependency injection
│   │
│   ├── services/                 # Business Logic
│   │   ├── __init__.py
│   │   ├── query_handler.py      # Query processing
│   │   ├── validation.py         # Zero-hallucination validation
│   │   ├── embedding.py          # Embedding generation
│   │   ├── cache.py              # Caching service
│   │   └── sync_service.py       # Data synchronization
│   │
│   ├── clients/                  # External Service Clients
│   │   ├── __init__.py
│   │   ├── itglue_client.py      # IT Glue API client
│   │   ├── ollama_client.py      # Ollama embeddings
│   │   └── openai_client.py      # OpenAI fallback
│   │
│   ├── models/                   # Data Models
│   │   ├── __init__.py
│   │   ├── database.py           # SQLAlchemy models
│   │   ├── schemas.py            # Pydantic schemas
│   │   ├── entities.py           # Domain entities
│   │   └── responses.py          # Response models
│   │
│   ├── repositories/             # Data Access Layer
│   │   ├── __init__.py
│   │   ├── postgres.py           # PostgreSQL operations
│   │   ├── neo4j_repo.py         # Neo4j operations
│   │   ├── qdrant_repo.py        # Qdrant operations
│   │   └── redis_repo.py         # Redis operations
│   │
│   ├── utils/                    # Utilities
│   │   ├── __init__.py
│   │   ├── config.py             # Configuration management
│   │   ├── logger.py             # Logging setup
│   │   ├── exceptions.py         # Custom exceptions
│   │   └── helpers.py            # Helper functions
│   │
│   └── workers/                  # Background Workers
│       ├── __init__.py
│       ├── celery_app.py         # Celery configuration
│       ├── sync_tasks.py         # Sync tasks
│       └── embedding_tasks.py    # Embedding tasks
│
├── streamlit/                    # Streamlit UI
│   ├── app.py                    # Main Streamlit app
│   ├── pages/                    # Multi-page structure
│   │   ├── 1_🔍_Query.py        # Query interface
│   │   ├── 2_🏢_Organizations.py # Organization management
│   │   ├── 3_📊_Analytics.py    # Analytics dashboard
│   │   └── 4_⚙️_Settings.py     # Settings page
│   ├── components/               # Reusable components
│   │   ├── __init__.py
│   │   ├── chat_interface.py    # Chat UI component
│   │   ├── result_display.py    # Result display
│   │   ├── filters.py           # Filter components
│   │   └── auth.py              # Auth components
│   └── utils/                    # UI utilities
│       ├── __init__.py
│       ├── state_manager.py     # Session state
│       └── formatters.py        # Data formatters
│
├── tests/                        # Test Suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest configuration
│   ├── unit/                    # Unit tests
│   │   ├── __init__.py
│   │   ├── test_query_handler.py
│   │   ├── test_validation.py
│   │   └── test_itglue_client.py
│   ├── integration/             # Integration tests
│   │   ├── __init__.py
│   │   ├── test_api.py
│   │   ├── test_database.py
│   │   └── test_mcp_protocol.py
│   ├── e2e/                     # End-to-end tests
│   │   ├── __init__.py
│   │   └── test_query_flow.py
│   └── fixtures/                # Test fixtures
│       ├── __init__.py
│       └── sample_data.py
│
├── scripts/                      # Utility Scripts
│   ├── setup.py                 # Initial setup script
│   ├── migrate.py               # Database migrations
│   ├── sync_data.py            # Manual sync trigger
│   ├── generate_embeddings.py  # Embedding generation
│   └── health_check.py         # System health check
│
├── configs/                      # Configuration Files
│   ├── nginx.conf               # Nginx configuration
│   ├── prometheus.yml           # Prometheus config
│   ├── grafana/                 # Grafana dashboards
│   │   └── dashboard.json
│   └── redis.conf               # Redis configuration
│
├── deployments/                  # Deployment Configurations
│   ├── docker/                  # Docker files
│   │   ├── Dockerfile           # Main application
│   │   ├── Dockerfile.streamlit # Streamlit UI
│   │   └── Dockerfile.worker    # Worker processes
│   ├── kubernetes/              # K8s manifests
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── configmap.yaml
│   │   └── secrets.yaml
│   └── terraform/               # Infrastructure as Code
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
│
├── docs/                         # Documentation
│   ├── README.md                # Documentation index
│   ├── api-integration-specification.md
│   ├── backend-architecture.md
│   ├── deployment-guide.md
│   ├── development-workflow-guide.md
│   ├── frontend-architecture.md
│   ├── fullstack-architecture.md
│   ├── implementation-guide.md
│   ├── security-compliance-documentation.md
│   ├── testing-documentation.md
│   └── user-guide.md
│
├── prd/                          # Product Requirements
│   └── product-requirements-document.md
│
├── migrations/                   # Database Migrations
│   ├── alembic.ini              # Alembic configuration
│   └── versions/                # Migration scripts
│       └── 001_initial_schema.py
│
├── .github/                      # GitHub Configuration
│   ├── workflows/               # GitHub Actions
│   │   ├── ci.yml              # CI pipeline
│   │   ├── cd.yml              # CD pipeline
│   │   └── security.yml        # Security scanning
│   ├── ISSUE_TEMPLATE/         # Issue templates
│   └── pull_request_template.md
│
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore rules
├── docker-compose.yml            # Docker Compose config
├── docker-compose.dev.yml        # Development overrides
├── docker-compose.prod.yml       # Production overrides
├── Makefile                      # Build automation
├── pyproject.toml               # Python project config
├── poetry.lock                  # Poetry lock file
├── requirements.txt             # Python dependencies
├── requirements-dev.txt         # Dev dependencies
├── README.md                    # Project README
└── LICENSE                      # License file
```

## Module Descriptions

### Core Modules

#### `/src/mcp/`
**Purpose**: MCP Protocol implementation  
**Key Files**:
- `server.py`: Core MCP server with stdio/SSE communication
- `handlers.py`: Request routing and response handling
- `tools.py`: Tool definitions (query_company, list_companies, etc.)
- `protocol.py`: JSON-RPC protocol utilities

#### `/src/services/`
**Purpose**: Business logic and core services  
**Key Files**:
- `query_handler.py`: Natural language query processing
- `validation.py`: Zero-hallucination validation logic
- `embedding.py`: Document embedding generation
- `sync_service.py`: IT Glue data synchronization

#### `/src/clients/`
**Purpose**: External service integrations  
**Key Files**:
- `itglue_client.py`: IT Glue API client with rate limiting
- `ollama_client.py`: Local embedding generation
- `openai_client.py`: Fallback cloud embeddings

#### `/src/repositories/`
**Purpose**: Data access layer  
**Key Files**:
- `postgres.py`: Structured data storage
- `neo4j_repo.py`: Graph relationships
- `qdrant_repo.py`: Vector search operations
- `redis_repo.py`: Caching layer

### Frontend Module

#### `/streamlit/`
**Purpose**: User interface  
**Key Files**:
- `app.py`: Main Streamlit application
- `pages/`: Multi-page app structure
- `components/`: Reusable UI components
- `utils/`: State management and formatting

### Supporting Modules

#### `/tests/`
**Purpose**: Comprehensive test suite  
**Structure**:
- `unit/`: Isolated component tests
- `integration/`: Component interaction tests
- `e2e/`: Full workflow tests

#### `/scripts/`
**Purpose**: Operational utilities  
**Key Scripts**:
- `setup.py`: Initial environment setup
- `sync_data.py`: Manual data synchronization
- `generate_embeddings.py`: Batch embedding generation

## File Naming Conventions

- **Python files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Test files**: `test_*.py`
- **Config files**: `*.yml` or `*.yaml`

## Import Structure

```python
# Standard library imports
import os
import sys
from typing import Optional, List, Dict

# Third-party imports
import fastapi
import streamlit as st
from sqlalchemy import create_engine

# Local application imports
from src.services import QueryHandler
from src.models import QueryRequest
from src.utils import logger
```

## Environment Variables

Key environment variables needed (see `.env.example`):

```bash
# IT Glue Configuration
IT_GLUE_API_KEY=
IT_GLUE_BASE_URL=

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost/itglue
NEO4J_URI=bolt://localhost:7687
QDRANT_HOST=localhost
REDIS_URL=redis://localhost:6379

# Service Configuration
OLLAMA_HOST=http://localhost:11434
OPENAI_API_KEY=

# Application Settings
APP_ENV=development
LOG_LEVEL=INFO
```

## Development Entry Points

1. **MCP Server**: `python -m src.main`
2. **Streamlit UI**: `streamlit run streamlit/app.py`
3. **API Server**: `uvicorn src.api.app:app --reload`
4. **Worker**: `celery -A src.workers.celery_app worker`
5. **Tests**: `pytest tests/`

## Quick Start Commands

```bash
# Setup development environment
make setup

# Run all services locally
docker-compose up

# Run tests
make test

# Format code
make format

# Lint code
make lint

# Build for production
make build
```

## Dependencies Graph

```
main.py
├── mcp/server.py
│   ├── services/query_handler.py
│   │   ├── repositories/postgres.py
│   │   ├── repositories/qdrant_repo.py
│   │   └── services/validation.py
│   └── clients/itglue_client.py
│       └── utils/config.py
└── api/app.py
    ├── api/endpoints/*
    └── api/middleware/*
```

---

**Note for AI Coding Agents**: This structure follows Python best practices with clear separation of concerns. Each module has a single responsibility. The `src/` directory contains all application code, while configuration and deployment files are at the root level. Tests mirror the source structure for easy navigation.