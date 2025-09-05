# Quick Start Guide

**Get IT Glue MCP Server running in 5 minutes**

## Prerequisites
- Python 3.12+ 
- Docker & Docker Compose
- 8GB+ RAM
- IT Glue API key

## 1. Setup (2 minutes)

```bash
# Clone and enter directory
git clone https://github.com/Blufix/it-glue-mcp-project.git
cd itglue-mcp-project

# Configure environment
cp .env.example .env
# Edit .env - ADD YOUR IT_GLUE_API_KEY

# Install dependencies
poetry install
```

## 2. Start Services (2 minutes)

```bash
# Start all 6 services (PostgreSQL, Redis, Qdrant, Neo4j, Prometheus, Grafana)
docker-compose up -d

# Check services are running
docker ps --format "table {{.Names}}\t{{.Status}}"
```

## 3. Run MCP Server (1 minute)

```bash
# Start MCP server (stdio mode)
poetry run python -m src.mcp

# OR WebSocket mode
poetry run python -m src.mcp --websocket
```

## 4. Access UI

- **Streamlit UI**: http://localhost:8501
- **Prometheus**: http://localhost:9090  
- **Grafana**: http://localhost:3000

## 5. Test Your Setup

In Streamlit UI, try:
```
@faucets list organizations
What servers does Company A have?
@[org_name] document infrastructure
```

## MCP Tools Available

Your server provides 10 specialized tools:
- `query` - Natural language queries
- `search` - Cross-company search  
- `query_organizations` - Organization operations
- `query_documents` - Document search
- `query_flexible_assets` - Assets, licenses, certificates
- `query_locations` - Location queries
- `discover_asset_types` - Asset type discovery
- `document_infrastructure` - Generate infrastructure docs
- `sync_data` - Data synchronization
- `health` - System health check

## Architecture Overview

**Current System:**
- **PostgreSQL**: Structured IT Glue data (active)
- **Redis**: Query caching (active, 5-min TTL)
- **Qdrant**: Vector embeddings (active)
- **Neo4j**: Graph relationships (provisioned, not implemented)

**See:** `docs/brownfield-architecture.md` for complete system documentation

## Troubleshooting

**Services won't start?**
- Check ports 5434, 6333, 6380, 7475, 7688, 8501, 9090 are available
- Ensure 8GB+ RAM available
- Check Docker has enough resources

**MCP server fails?**
- Verify IT_GLUE_API_KEY in .env
- Check database services are healthy: `docker-compose ps`
- Review logs: `docker-compose logs -f`

**No data returned?**
- Verify IT Glue API key has read permissions
- Check organization exists in IT Glue
- Try basic query first: `list organizations`