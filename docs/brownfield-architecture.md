# IT Glue MCP Server Brownfield Architecture Document

## Introduction

This document captures the CURRENT STATE of the IT Glue MCP Server codebase, including technical debt, workarounds, and real-world patterns. It serves as a reference for AI agents working on enhancements to this sophisticated multi-database MCP implementation.

### Document Scope

Comprehensive documentation of the entire system based on Epic 1.1 completion - Database Integration & MCP Tools Enhancement. The system now features a fully implemented multi-database architecture with specialized MCP query handlers.

### Change Log

| Date       | Version | Description                 | Author    |
| ---------- | ------- | --------------------------- | --------- |
| 2025-09-03 | 1.0     | Initial brownfield analysis | BMad Master |

## Quick Reference - Key Files and Entry Points

### Critical Files for Understanding the System

- **Main Entry**: `src/mcp/__main__.py` - MCP server entry point with stdio/WebSocket modes
- **MCP Server Core**: `src/mcp/server.py` - Main server with 10 specialized query tools
- **Configuration**: `src/config/settings.py`, `.env.example` - Pydantic settings with 100+ config options
- **IT Glue Client**: `src/services/itglue/client.py` - Rate-limited API client with retry logic
- **Database Managers**: `src/data/db_manager.py` - Multi-database connection management
- **Query Engine**: `src/query/engine.py` - Natural language query processing
- **Streamlit UI**: `src/ui/streamlit_app.py` - Web interface with @organization commands

### Enhancement Impact Areas (Based on Epic 1.1)

Recent major enhancements completed:
- Specialized MCP query handlers in `src/query/*_handler.py`
- Multi-database integration across `src/db/` subdirectories
- Enhanced Streamlit UI with organization-specific commands
- Infrastructure documentation generation in `src/infrastructure/`

## High Level Architecture

### Technical Summary

This is a sophisticated brownfield MCP server that transforms IT Glue documentation into queryable knowledge through multiple database backends and specialized query handlers. The architecture supports both programmatic access via MCP protocol and web access via Streamlit UI.

### Actual Tech Stack (from pyproject.toml)

| Category          | Technology                 | Version | Notes                               |
| ----------------- | -------------------------- | ------- | ----------------------------------- |
| Runtime           | Python                     | ^3.12   | Requires 3.11+ for async features  |
| MCP Framework     | mcp-python                 | ^0.1.0  | Comment: installed separately       |
| API Framework     | FastAPI                    | ^0.104  | Used for API endpoints              |
| WebSocket         | websockets                 | ^12.0   | MCP WebSocket transport             |
| Primary DB        | PostgreSQL (asyncpg)       | ^0.29   | Structured IT Glue data            |
| Graph DB          | Neo4j                      | ^5.14   | PROVISIONED but not implemented    |
| Vector DB         | Qdrant                     | ^1.7.0  | Semantic search embeddings        |
| Cache/Queue       | Redis (aioredis)           | ^5.0    | Query caching + Celery broker     |
| Task Queue        | Celery                     | ^5.3.4  | Background tasks                   |
| Web UI            | Streamlit                  | ^1.29   | Chat interface with @org commands  |
| NLP/Embeddings    | sentence-transformers      | ^2.2.2  | Local embeddings                   |
| Monitoring        | Prometheus/OpenTelemetry   | latest  | Full observability stack           |
| Testing           | pytest + testcontainers   | latest  | 80% coverage requirement           |
| Code Quality      | black + ruff + mypy        | latest  | Strict type checking enabled       |

### Repository Structure Reality Check

- Type: **Monorepo** with clear domain separation
- Package Manager: **Poetry** with comprehensive dependency management
- Build System: **Docker Compose** with 6 services (postgres, neo4j, qdrant, redis, prometheus, grafana)
- Notable: Heavy use of async/await throughout, sophisticated caching patterns

## Source Tree and Module Organization

### Project Structure (Actual)

```text
itglue-mcp-server/
├── src/
│   ├── mcp/                    # MCP server implementation
│   │   ├── server.py          # Main server with 10 specialized tools
│   │   ├── tools/             # Individual MCP tools (query, sync, health)
│   │   └── websocket_server.py # WebSocket transport
│   ├── query/                  # Query processing (20+ files)
│   │   ├── *_handler.py       # Specialized handlers (orgs, docs, assets, locations)
│   │   ├── engine.py          # Main query processor
│   │   ├── fuzzy_matcher*.py  # Multiple fuzzy matching implementations
│   │   ├── intelligent_query_processor*.py # NLP query analysis
│   │   └── templates/         # Query templates and patterns
│   ├── services/itglue/       # IT Glue API integration
│   │   ├── client.py          # Rate-limited HTTP client
│   │   └── models.py          # Pydantic models for IT Glue entities
│   ├── db/                    # Database connections (postgres, neo4j, qdrant)
│   ├── cache/                 # Multi-layer caching system
│   │   ├── redis_cache.py     # Primary Redis caching
│   │   ├── redis_fuzzy_cache.py # Specialized fuzzy search cache
│   │   └── strategies.py      # Cache invalidation strategies
│   ├── ui/                    # Streamlit web interface
│   │   ├── streamlit_app.py   # Main UI with @org commands
│   │   ├── components/        # Reusable UI components
│   │   └── services/          # UI-specific service layer
│   ├── infrastructure/        # Infrastructure documentation generation
│   ├── monitoring/            # Metrics, logging, tracing
│   ├── security/              # Authentication and encryption
│   ├── sync/                  # Data synchronization (initial + incremental)
│   └── transformers/          # Data transformation for different DBs
├── tests/                     # Comprehensive test suite
│   ├── unit/                  # Unit tests (80%+ coverage)
│   ├── integration/           # Database integration tests
│   ├── performance/           # Query performance benchmarks
│   └── mcp_tools/             # MCP tool-specific tests
├── docs/                      # Project documentation
│   ├── qa/gates/              # Quality gate decisions
│   └── stories/               # Epic and story documentation
├── docker-compose.yml         # Full 6-service stack
├── monitoring/                # Prometheus/Grafana configs
└── scripts/                   # Database initialization and utilities
```

### Key Modules and Their Purpose

- **MCP Server Core** (`src/mcp/server.py`): 900+ lines, implements 10 specialized tools
- **Query Handlers** (`src/query/*_handler.py`): Type-specific query processing with <500ms targets
- **IT Glue Client** (`src/services/itglue/client.py`): Production-ready with rate limiting, retries, circuit breaker
- **Cache Management** (`src/cache/`): Multi-layer caching (Redis + in-memory) with 5-min TTL
- **Database Layer** (`src/db/`): Multi-database abstraction (active: PostgreSQL, Qdrant, Redis; provisioned: Neo4j)
- **Streamlit UI** (`src/ui/streamlit_app.py`): 700+ lines with sophisticated @organization command parsing

## Data Models and APIs

### Data Models

The system uses Pydantic models throughout for type safety:

- **IT Glue Models**: See `src/services/itglue/models.py` - Organization, Configuration, Contact, Document, etc.
- **Cache Models**: See `src/cache/manager.py` - CacheKey, CacheResult structures
- **Query Models**: See `src/query/engine.py` - QueryRequest, QueryResult, QueryContext
- **Database Models**: SQLAlchemy models in `src/db/postgres/models.py`

### API Specifications

- **MCP Tools**: 10 tools registered in server.py (query, search, query_organizations, etc.)
- **REST API**: FastAPI endpoints in `src/api/app.py` for health checks and metrics
- **WebSocket API**: MCP protocol over WebSocket on port 8001
- **IT Glue API**: Full REST client with models for all major resources

## Technical Debt and Known Issues

### Critical Technical Debt

1. **Neo4j Integration**: Provisioned in Docker but NOT IMPLEMENTED in code
   - Container runs but no data population or query logic
   - Reserved for Phase 2: relationship mapping and dependency analysis
   - Impact: Missing knowledge graph capabilities mentioned in architecture

2. **Query Handler Inconsistencies**: Different patterns across handlers
   - `organizations_handler.py`: Uses in-memory cache + Redis
   - `documents_handler.py`: Uses semantic search integration
   - `flexible_assets_handler.py`: Direct IT Glue API calls
   - Should standardize caching and response patterns

3. **Configuration Complexity**: 100+ configuration options in settings.py
   - Many feature flags not fully implemented (ENABLE_AI_SUGGESTIONS, etc.)
   - Some environment variables have different naming conventions
   - Development vs production configuration not clearly separated

4. **Multiple Fuzzy Matchers**: Three different implementations
   - `fuzzy_matcher.py`, `fuzzy_matcher_optimized.py`, `fuzzy_enhancer.py`
   - Unclear which one is used where, potential performance implications
   - Should consolidate to single optimized implementation

### Workarounds and Gotchas

- **Docker Port Mapping**: Non-standard ports (PostgreSQL on 5434, Neo4j on 7475/7688) to avoid conflicts
- **Rate Limiting**: IT Glue API limited to 100 requests/minute, client implements backoff
- **Cache TTL**: Hardcoded 5-minute TTL in multiple places, not configurable per query type
- **Async Initialization**: MCP server uses lazy initialization pattern, components initialized on first use
- **Memory Usage**: In-memory organization cache can grow large with many organizations
- **Test Dependencies**: Requires Docker for integration tests (testcontainers)

## Integration Points and External Dependencies

### External Services

| Service   | Purpose          | Integration Type | Key Files                           |
| --------- | ---------------- | ---------------- | ----------------------------------- |
| IT Glue   | Primary Data     | REST API         | `src/services/itglue/client.py`     |
| OpenAI    | Embeddings       | API              | `src/embeddings/generator.py`       |
| Ollama    | Local Embeddings | HTTP API         | `src/config/settings.py` (URL only) |

### Internal Integration Points

- **MCP Protocol**: stdio and WebSocket transports for client communication
- **Multi-Database**: PostgreSQL (primary), Qdrant (vectors), Redis (cache), Neo4j (unused)
- **Background Tasks**: Celery with Redis broker for data synchronization
- **Web UI**: Streamlit on port 8501 with @organization command parsing
- **Monitoring**: Prometheus metrics on port 9090, Grafana dashboards on port 3000

## Development and Deployment

### Local Development Setup

1. **Prerequisites Check**: Python 3.12+, Docker, 8GB+ RAM
2. **Environment Setup**: `cp .env.example .env` and configure IT_GLUE_API_KEY
3. **Docker Services**: `docker-compose up -d` (starts 6 services)
4. **Python Environment**: `poetry install` (300+ dependencies)
5. **Database Initialization**: `make migrate` runs Alembic migrations

### Known Setup Issues

- **First Time Setup**: Docker image pulls can take 10+ minutes
- **Memory Requirements**: Neo4j configured with 1G heap, Qdrant needs 2GB+ for large datasets
- **Port Conflicts**: Check ports 5434, 6333, 6380, 7475, 7688, 8501, 9090 are available
- **API Key Validation**: IT Glue API key must have read permissions for all resource types

### Build and Deployment Process

- **Development**: `make dev` starts all services including Streamlit UI
- **MCP Server**: `python -m src.mcp` for stdio mode, `--websocket` for WebSocket
- **API Server**: `uvicorn src.api.app:app --port 8002`
- **Production**: `docker-compose -f docker-compose.prod.yml up` (not fully tested)
- **Monitoring**: Prometheus metrics, Grafana dashboards, structured logging

## Testing Reality

### Current Test Coverage

- **Unit Tests**: 80%+ coverage requirement (enforced by pytest-cov)
- **Integration Tests**: Database integration with testcontainers
- **Performance Tests**: Query response time benchmarks (<2s target, <500ms for orgs)
- **MCP Tool Tests**: Comprehensive tests in `tests/mcp_tools/`
- **E2E Tests**: Limited, mostly manual through Streamlit UI

### Running Tests

```bash
poetry run pytest                    # All tests
poetry run pytest -m unit           # Unit tests only  
poetry run pytest -m integration    # Integration tests (requires Docker)
poetry run pytest -m performance    # Performance benchmarks
make test                           # Full test suite with coverage
```

### Test Environment Setup

- **Test Databases**: Uses testcontainers for isolated testing
- **Mock IT Glue**: `tests/fixtures/mock_itglue_client.py` for unit tests
- **Performance Baselines**: Response time targets defined in test files
- **CI/CD**: GitHub Actions with test matrix (not fully configured)

## Architecture Constraints and Design Decisions

### Performance Constraints

- **Query Response Time**: <2s for general queries, <500ms for organization queries
- **Cache Strategy**: 5-minute TTL with LRU eviction, Redis for distributed caching
- **Rate Limiting**: IT Glue API limited to 100 req/min, backoff strategy implemented
- **Memory Management**: In-memory caches with size limits, periodic cleanup

### Security Constraints

- **Read-Only Operations**: System never modifies IT Glue data (enforced by API permissions)
- **Credential Management**: Environment variables only, no secrets management
- **Password Handling**: Passwords never displayed, only metadata shown
- **API Security**: Optional JWT authentication, API key validation

### Database Architecture Decisions

- **PostgreSQL**: Primary structured data storage, async connections via asyncpg
- **Redis**: Multi-purpose (cache + message broker), single instance with multiple DBs
- **Qdrant**: Vector storage for semantic search, configured for single-node
- **Neo4j**: Provisioned but unused, reserved for future relationship mapping

## Production Readiness Assessment

### Current Status: CONCERNS (from Quality Gate)

**Strengths:**
- Comprehensive MCP tool coverage for all major IT Glue resources
- Multi-database architecture properly implemented
- Performance targets met with sub-2s response times
- Strong test coverage for new components
- Docker containerization complete

**Critical Issues Before Production:**

1. **Security Hardening Needed** (Medium Priority):
   - Credential rotation strategy missing
   - Environment variable security insufficient for production
   - Missing secrets management integration

2. **End-to-End Testing Gaps** (Medium Priority):
   - Individual components tested but not full workflows
   - Missing integration tests for MCP client interactions
   - No load testing for concurrent users

3. **Performance Optimization** (Low Priority):
   - Neo4j queries not optimized (when implemented)
   - Multiple fuzzy matcher implementations inefficient
   - Cache invalidation strategy could be improved

4. **Production Documentation** (Low Priority):
   - Deployment procedures incomplete
   - Monitoring runbook missing
   - Scaling strategy not documented

## Appendix - Useful Commands and Scripts

### Frequently Used Commands

```bash
# Development
make setup          # Complete environment setup
make dev            # Run all services
poetry run python -m src.mcp    # Start MCP server
streamlit run src/ui/streamlit_app.py    # Start web UI

# Database
make migrate        # Run Alembic migrations
make init-neo4j     # Initialize Neo4j (script exists)
make init-qdrant    # Initialize Qdrant collections

# Testing and Quality
make test           # Full test suite
make format         # Black + isort formatting
make lint           # Ruff linting + mypy type checking
make coverage       # Generate coverage report
```

### Debugging and Troubleshooting

- **Logs**: Structured logging to stdout, configurable level via LOG_LEVEL
- **Debug Mode**: Set DEBUG=true for verbose output and auto-reload
- **Health Checks**: `/health` endpoint for all services, MCP `health` tool
- **Metrics**: Prometheus metrics at `/metrics`, Grafana dashboards
- **Common Issues**: See Quality Gate file for known production concerns

### Performance Monitoring

- **Query Performance**: Built-in timing for all query operations
- **Cache Hit Rates**: Redis metrics for cache effectiveness  
- **Database Performance**: Connection pool monitoring, slow query logging
- **Resource Usage**: Docker container metrics, memory/CPU monitoring

---

This document serves as the definitive reference for AI agents working with the IT Glue MCP Server codebase. It captures the actual implementation state including technical debt, architectural decisions, and real-world constraints that must be respected when making enhancements.