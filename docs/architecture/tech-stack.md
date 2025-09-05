# Technology Stack

## Core Technologies

### Runtime & Language
- **Python 3.12+**: Primary language with modern async features
- **Poetry**: Dependency management and packaging
- **asyncio**: Asynchronous programming foundation

### MCP Framework
- **mcp-python 0.1.0**: Model Context Protocol implementation
- **WebSocket**: Real-time MCP transport
- **stdio**: Standard input/output MCP transport

## Backend Architecture

### API Framework
- **FastAPI 0.104+**: Modern async API framework
- **Uvicorn**: ASGI server with auto-reload
- **Pydantic 2.5+**: Data validation and serialization
- **aiohttp 3.9+**: HTTP client for IT Glue API integration

### Database Stack (Multi-Database Architecture)

#### Primary Database
- **PostgreSQL 15**: Structured IT Glue data storage
- **asyncpg 0.29+**: Async PostgreSQL driver
- **SQLAlchemy 2.0+**: ORM with async support
- **Alembic**: Database migrations

#### Vector Database  
- **Qdrant 1.7.3**: Vector embeddings for semantic search
- **qdrant-client 1.7+**: Python client library
- **Collections**: Organized by document types

#### Graph Database (Provisioned)
- **Neo4j 5-community**: Graph relationships (not implemented)
- **neo4j 5.14+**: Python driver
- **APOC + GDS**: Graph algorithms and procedures
- **Status**: Docker container running, code integration pending

#### Caching & Message Broker
- **Redis 7-alpine**: Multi-purpose (cache + broker)
- **aioredis 2.0+**: Async Redis client  
- **Celery 5.3+**: Background task processing
- **TTL Strategy**: 5-minute default for query results

### Natural Language Processing
- **sentence-transformers 2.2+**: Local embeddings generation
- **OpenAI API**: Optional cloud embeddings
- **tiktoken 0.5+**: Token counting and management
- **langchain 0.0.350**: NLP pipeline components

### Security
- **python-jose**: JWT token handling
- **passlib + bcrypt**: Password hashing
- **cryptography 41+**: Encryption utilities
- **Environment variables**: Secure configuration

## Frontend & UI

### Web Interface
- **Streamlit 1.29+**: Interactive web UI
- **streamlit-chat**: Chat interface components
- **plotly 5.18+**: Data visualization
- **Rich display**: IP addresses, serial numbers, status indicators

### User Experience Features
- **@organization commands**: Scoped queries (`@faucets`, `@[org_name]`)
- **Chat interface**: Natural language query input
- **Progress tracking**: Real-time operation monitoring
- **Infrastructure documentation**: Automated report generation

## Monitoring & Observability

### Metrics Collection
- **Prometheus**: Time-series metrics storage
- **prometheus-client**: Python metrics collection
- **Custom metrics**: Query response times, cache hit rates
- **Health checks**: Service availability monitoring

### Logging & Tracing
- **structlog 23.2+**: Structured logging
- **OpenTelemetry**: Distributed tracing
- **Log levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Context preservation**: Request/query correlation

### Dashboards
- **Grafana**: Monitoring dashboards
- **Pre-built dashboards**: System health, query performance
- **Alerting**: Configurable thresholds and notifications

## Development Tools

### Code Quality
- **black 23.12+**: Code formatting (88 char line length)
- **isort 5.13+**: Import organization
- **mypy 1.7+**: Static type checking
- **ruff 0.1.8+**: Fast Python linter
- **pre-commit 3.6+**: Git hooks for quality enforcement

### Testing Framework
- **pytest 7.4+**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting (80% minimum)
- **pytest-xdist**: Parallel test execution
- **testcontainers**: Database integration testing

### Development Environment
- **Docker Compose**: Multi-service development
- **Poetry**: Dependency and virtual environment management
- **IPython**: Enhanced REPL
- **ipdb**: Interactive debugging

## Infrastructure & Deployment

### Containerization
- **Docker**: Service containerization
- **Docker Compose**: Multi-service orchestration
- **6 Services**: postgres, redis, qdrant, neo4j, prometheus, grafana
- **Volume management**: Persistent data storage

### Service Configuration
```yaml
Services Architecture:
├── itglue-postgres (5434:5432)    # Structured data
├── itglue-redis (6380:6379)       # Caching + broker  
├── itglue-qdrant (6333:6333)      # Vector search
├── itglue-neo4j (7475:7474)       # Graph DB (provisioned)
├── itglue-prometheus (9090:9090)  # Metrics
└── itglue-grafana (3000:3000)     # Dashboards
```

### Resource Requirements
- **Minimum**: 4 CPU, 8GB RAM, 50GB SSD
- **Recommended**: 8 CPU, 16GB RAM, 100GB SSD  
- **Production**: 16+ CPU, 32GB+ RAM, 500GB+ SSD

## Integration Points

### External APIs
- **IT Glue REST API**: Primary data source
- **Rate limiting**: 100 requests/minute
- **Authentication**: API key based
- **Retry logic**: Exponential backoff on failures

### Data Processing Pipeline
```
IT Glue API → Rate Limiter → Transformer → Database(s) → Cache → MCP Response
```

### MCP Tools (10 Specialized)
1. **query**: Natural language processing
2. **search**: Cross-company semantic search
3. **query_organizations**: Organization operations with fuzzy matching
4. **query_documents**: Document search with semantic support
5. **query_flexible_assets**: Certificates, licenses, warranties
6. **query_locations**: Site and location management
7. **discover_asset_types**: Asset type discovery and analysis
8. **document_infrastructure**: Automated documentation generation
9. **sync_data**: Data synchronization management
10. **health**: System health and status monitoring

## Performance Characteristics

### Response Time Targets
- **Organization queries**: < 500ms
- **General queries**: < 2 seconds  
- **Infrastructure docs**: < 30 seconds
- **Cache hit ratio**: > 80%

### Scalability Patterns
- **Async/await**: Non-blocking I/O throughout
- **Connection pooling**: Database and HTTP connections
- **Horizontal scaling**: Stateless service design
- **Resource monitoring**: Prometheus metrics collection

## Version Management

### Dependency Versions (Current)
```toml
# Core (pyproject.toml)
python = "^3.12"
fastapi = "^0.104.1"
sqlalchemy = "^2.0.23"
pydantic = "^2.5.2"

# Databases
asyncpg = "^0.29.0"
qdrant-client = "^1.7.0"
neo4j = "^5.14.0"
aioredis = "^2.0.1"

# NLP & AI
openai = "^1.6.0"
sentence-transformers = "^2.2.2"
langchain = "^0.0.350"

# Frontend
streamlit = "^1.29.0"
```

### Update Strategy
- **Poetry lock file**: Ensures reproducible builds
- **Semantic versioning**: Major.minor.patch
- **Testing**: Full test suite before version updates
- **Security patches**: Applied promptly

This tech stack supports the sophisticated multi-database MCP server architecture implemented in Epic 1.1.