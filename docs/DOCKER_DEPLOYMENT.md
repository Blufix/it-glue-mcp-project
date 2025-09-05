# Docker Deployment Guide

**Simple, accurate deployment instructions for the 6-service architecture**

## Services Overview

The IT Glue MCP Server runs as a 6-service Docker Compose stack:

| Service | Purpose | Port | Status |
|---------|---------|------|---------|
| **itglue-postgres** | Structured IT Glue data | 5434 | ✅ Active |
| **itglue-redis** | Query caching & message broker | 6380 | ✅ Active |
| **itglue-qdrant** | Vector embeddings for semantic search | 6333 | ✅ Active |
| **itglue-neo4j** | Graph relationships | 7475/7688 | 🚧 Provisioned |
| **itglue-prometheus** | Metrics collection | 9090 | ✅ Active |
| **itglue-grafana** | Monitoring dashboards | 3000 | ✅ Active |

## Quick Deployment

```bash
# Start all services
docker-compose up -d

# Check health
docker-compose ps

# View logs
docker-compose logs -f [service_name]

# Stop all services  
docker-compose down
```

## Service Configuration

### PostgreSQL Database
```yaml
Container: itglue-postgres
Image: postgres:15-alpine
Port: 5434 (external) -> 5432 (internal)
Volume: postgres_data:/var/lib/postgresql/data
Health check: pg_isready
```

### Redis Cache
```yaml
Container: itglue-redis  
Image: redis:7-alpine
Port: 6380 (external) -> 6379 (internal)
Config: 256MB max memory, LRU eviction
Volume: redis_data:/data
```

### Qdrant Vector Database
```yaml
Container: itglue-qdrant
Image: qdrant/qdrant:v1.7.3
Ports: 6333 (REST), 6334 (gRPC)
Volume: qdrant_data:/qdrant/storage
```

### Neo4j Graph Database
```yaml
Container: itglue-neo4j
Image: neo4j:5-community
Ports: 7475 (HTTP), 7688 (Bolt)
Memory: 1G heap, 1G pagecache
Plugins: APOC, Graph Data Science
Status: Provisioned but not implemented in code
```

## Environment Configuration

**Required in .env:**
```bash
# IT Glue API (REQUIRED)
IT_GLUE_API_KEY=your_api_key_here

# Database passwords (change for production)
POSTGRES_PASSWORD=Dfgytw6745g
NEO4J_PASSWORD=Dfghtye645

# Optional: OpenAI for embeddings
OPENAI_API_KEY=your_openai_key
```

## Production Deployment

### Resource Requirements
- **Minimum**: 4 CPU cores, 8GB RAM, 50GB SSD
- **Recommended**: 8 CPU cores, 16GB RAM, 100GB SSD
- **Production**: 16+ CPU cores, 32GB+ RAM, 500GB+ SSD

### Security Checklist
- [ ] Change default passwords in .env
- [ ] Use strong IT_GLUE_API_KEY
- [ ] Configure firewall (only expose needed ports)
- [ ] Enable SSL/TLS for external access
- [ ] Regular backups of volumes
- [ ] Monitor resource usage

### Backup Strategy
```bash
# Backup all volumes
docker run --rm -v itglue-mcp-server_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
docker run --rm -v itglue-mcp-server_qdrant_data:/data -v $(pwd):/backup alpine tar czf /backup/qdrant_backup.tar.gz -C /data .
docker run --rm -v itglue-mcp-server_neo4j_data:/data -v $(pwd):/backup alpine tar czf /backup/neo4j_backup.tar.gz -C /data .
```

## Monitoring & Health Checks

### Health Endpoints
- **MCP Health**: Use `health` tool via MCP protocol
- **Prometheus**: http://localhost:9090/targets
- **Grafana**: http://localhost:3000 (admin/admin)
- **Qdrant**: http://localhost:6333/cluster
- **Neo4j**: http://localhost:7475

### Log Locations
```bash
# Application logs
docker-compose logs -f mcp-server

# Database logs  
docker-compose logs -f postgres
docker-compose logs -f neo4j
docker-compose logs -f qdrant
```

## Troubleshooting

### Common Issues

**Services won't start:**
```bash
# Check port conflicts
netstat -tulpn | grep -E '(5434|6333|6380|7475|7688|9090|3000)'

# Check Docker resources
docker system df
docker system prune  # if low on space
```

**Database connection errors:**
```bash
# Test PostgreSQL
docker exec -it itglue-postgres pg_isready -U postgres

# Test Redis
docker exec -it itglue-redis redis-cli ping

# Test Qdrant
curl http://localhost:6333/cluster
```

**Performance issues:**
- Check container resources: `docker stats`
- Monitor memory usage of Neo4j (1GB heap limit)
- Redis maxmemory policy is LRU (256MB limit)
- Check disk space: `docker system df`

### Getting Help

**View current configuration:**
```bash
# Show running services
docker-compose ps

# Check service health
docker-compose exec postgres pg_isready
docker-compose exec redis redis-cli ping

# View resource usage
docker stats --no-stream
```

This deployment guide reflects the actual implemented system as of Epic 1.1 completion.