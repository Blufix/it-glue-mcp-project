# IT Glue MCP Server

An intelligent MCP (Model Context Protocol) server that transforms IT Glue's unstructured documentation into an instantly-accessible knowledge base through natural language querying.

## 🚀 Features

- **Natural Language Queries**: Ask questions in plain English ("What's the router IP for Company A?")
- **Zero Hallucination**: Returns accurate data or "no data available" - never guesses
- **@Organization Commands**: Target specific organizations with @faucets or @[org_name]
- **Infrastructure Documentation**: Generate comprehensive infrastructure docs with `@<org_name> document infrastructure` or `@organisations <id/name> document infrastructure`
- **Smart Search**: Type-based matching (searches for "firewall" find Sophos devices)
- **Rich Output**: Displays IP addresses, serial numbers, dates, status, and more
- **100% READ-ONLY**: Production-safe, never modifies IT Glue data
- **Security First**: Passwords never displayed, only metadata shown
- **Progress Tracking**: Real-time progress monitoring for long-running operations

## 🏗️ Architecture

### Active Components
- **PostgreSQL**: Primary database for structured IT Glue data
- **Qdrant**: Vector database for semantic search with embeddings
- **Redis**: High-speed caching for query results (5-min TTL)
- **Streamlit**: Web UI with chat interface and @organization commands

### Provisioned (Not Yet Implemented)
- **Neo4j**: Graph database ready for future relationship mapping and knowledge graph features
  - Currently provisioned in Docker but not actively used
  - Reserved for Phase 2: relationship analysis and dependency mapping

## 📋 Prerequisites

- Python 3.11+
- Docker and Docker Compose
- IT Glue API key
- 8GB RAM minimum (16GB recommended)

## 🛠️ Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Blufix/it-glue-mcp-project.git
cd it-glue-mcp-project
```

### 2. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your IT Glue API key and other settings
nano .env
```

### 3. Install Dependencies

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install Python dependencies
poetry install

# Install pre-commit hooks
poetry run pre-commit install
```

### 4. Start Services

```bash
# Start all services with Docker Compose
docker-compose up -d

# For development mode with hot reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### 5. Initialize Databases

```bash
# Run database migrations
poetry run alembic upgrade head

# Initialize Qdrant collections (for vector search)
poetry run python scripts/init_qdrant.py

# Optional: Initialize Neo4j (currently not used but available for future knowledge graph features)
# poetry run python scripts/init_neo4j.py
```

### 6. Run Initial Sync

```bash
# Sync IT Glue data (this may take a while)
poetry run python -m src.sync.initial_sync
```

### 7. Start the MCP Server

```bash
# Run the MCP server
poetry run python -m src.mcp.server

# Or use the CLI
poetry run itglue-mcp serve
```

### 8. Access the UI

Open your browser and navigate to:
- Streamlit UI: http://localhost:8501
- API Documentation: http://localhost:8002/docs
- Grafana Dashboard: http://localhost:3000 (admin/admin)

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [Frontend Architecture](docs/frontend-architecture.md)
- [API Documentation](docs/api.md)
- [Development Guide](docs/development.md)
- [Deployment Guide](docs/deployment.md)
- [Infrastructure Documentation](docs/infrastructure-documentation.md)

## 🏗️ Project Structure

```
itglue-mcp-server/
├── src/
│   ├── mcp/              # MCP server implementation
│   ├── api/              # REST API service
│   ├── core/             # Core business logic
│   ├── sync/             # IT Glue synchronization
│   ├── db/               # Database clients and models
│   ├── ui/               # Streamlit frontend
│   └── config/           # Configuration management
├── tests/                 # Test suites
├── docker/               # Docker configurations
├── scripts/              # Utility scripts
├── docs/                 # Documentation
└── monitoring/           # Prometheus & Grafana configs
```

## 🧪 Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test types
poetry run pytest -m unit
poetry run pytest -m integration
poetry run pytest -m e2e
```

## 🔧 Development

### Running Locally

```bash
# Start only the databases
docker-compose up postgres neo4j qdrant redis

# Run the MCP server locally
poetry run python -m src.mcp.server --reload

# Run the Streamlit UI locally
poetry run streamlit run src/ui/streamlit_app.py
```

### Code Quality

```bash
# Format code
poetry run black src tests
poetry run isort src tests

# Type checking
poetry run mypy src

# Linting
poetry run ruff src

# Security scan
poetry run bandit -r src
```

## 📊 Monitoring

- **Prometheus Metrics**: http://localhost:9090
- **Grafana Dashboards**: http://localhost:3000
- **Flower (Celery)**: http://localhost:5555

## 🚢 Deployment

### Docker Deployment

```bash
# Build production image
docker build -t itglue-mcp:latest .

# Run with Docker Compose
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n itglue
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 Environment Variables

Key environment variables (see `.env.example` for full list):

- `IT_GLUE_API_KEY`: Your IT Glue API key (required)
- `DATABASE_URL`: PostgreSQL connection string
- `NEO4J_URI`: Neo4j connection URI
- `REDIS_URL`: Redis connection URL
- `OPENAI_API_KEY`: OpenAI API key for embeddings (optional)

## 🔐 Security

- All passwords are encrypted at rest
- API authentication via JWT tokens or API keys
- Rate limiting on all endpoints
- Input sanitization to prevent injection attacks
- Audit logging for compliance

## 📈 Performance

- Query response time: <2 seconds (p95)
- Supports 100+ concurrent users
- Caches frequently accessed data
- Incremental sync minimizes API calls

## 🐛 Troubleshooting

### Common Issues

1. **MCP Server won't start**
   - Check that all required services are running: `docker-compose ps`
   - Verify environment variables are set correctly
   - Check logs: `docker-compose logs mcp-server`

2. **No data returned from queries**
   - Ensure initial sync has completed
   - Check IT Glue API key is valid
   - Verify database connections

3. **Slow query performance**
   - Check if Redis is running
   - Verify Neo4j indexes are created
   - Monitor with Grafana dashboards

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with the [Model Context Protocol](https://modelcontextprotocol.io)
- Powered by IT Glue API
- Uses OpenAI embeddings for semantic search

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check the [documentation](docs/)
- Contact the development team

---

**Current Version**: 0.1.0 (MVP)  
**Status**: In Development  
**Last Updated**: 2024