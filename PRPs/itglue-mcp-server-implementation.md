name: "IT Glue MCP Server - Complete Implementation PRP"
description: |

## Purpose
Context-rich Product Requirements Prompt (PRP) for implementing the IT Glue MCP Server with semantic search, zero-hallucination validation, and production-ready features. This PRP provides comprehensive context for AI agents to achieve working code through iterative refinement.

## Core Principles
1. **Context is King**: Includes ALL necessary documentation, API examples, and implementation patterns
2. **Validation Loops**: Provides executable tests/lints for iterative refinement
3. **Information Dense**: Uses existing codebase patterns and real-world examples
4. **Progressive Success**: Starts with basic functionality, validates, then enhances
5. **Global Rules**: Follows all rules in CLAUDE.md and project conventions

---

## Goal
Build a production-ready IT Glue MCP Server that transforms unstructured IT documentation into an intelligent knowledge base with natural language querying, achieving <2 second response times with zero hallucination through source validation.

## Why
- **Business Value**: Reduces support ticket search time from 15-30 minutes to under 2 seconds
- **Integration**: Provides standardized MCP interface for AI assistants to access IT documentation
- **Problems Solved**: Eliminates manual search friction, surfaces related information automatically, ensures 100% accuracy for critical IT information

## What
A Python-based MCP server that:
- Integrates with IT Glue API for real-time data access
- Provides semantic search using vector embeddings
- Validates all responses against source data (zero hallucination)
- Supports natural language queries through MCP tools
- Caches results for performance optimization

### Success Criteria
- [ ] MCP server responds to queries in <2 seconds (95th percentile)
- [ ] 100% accuracy with source validation (zero false positives)
- [ ] Handles 100 concurrent users without degradation
- [ ] Passes all unit, integration, and MCP protocol tests
- [ ] Successfully syncs and indexes IT Glue data

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Core Documentation
Use Archon for documents and code examples. Project =  IT Glue MCP Server - Intelligent Documentation Query System

- url: https://github.com/modelcontextprotocol/python-sdk
  why: Official MCP Python SDK implementation patterns
  
- url: https://modelcontextprotocol.io/quickstart/server
  why: MCP server implementation guide
  
- url: https://qdrant.tech/documentation/beginner-tutorials/
  why: Qdrant vector database setup and usage patterns
  
- url: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
  why: Embedding model for semantic search
  
- file: /home/jamie/projects/itglue-mcp-server/docs/it-glue-api-examples.py
  why: Comprehensive IT Glue API patterns with rate limiting
  
- file: /home/jamie/projects/itglue-mcp-server/src/services/itglue/client.py
  why: Existing IT Glue client implementation with backoff
  
- file: /home/jamie/projects/itglue-mcp-server/src/mcp/server.py
  why: Current MCP server skeleton to build upon
  
- file: /home/jamie/projects/itglue-mcp-server/src/config/settings.py
  why: Configuration pattern using pydantic-settings

# Additional Resources
- url: https://github.com/confident-ai/deepeval
  why: Hallucination detection framework for validation
  
- url: https://ollama.com/blog/embedding-models
  why: Local embedding generation with Ollama fallback
  
- docfile: /home/jamie/projects/itglue-mcp-server/prd/product-requirements-document.md
  why: Complete project requirements and epic breakdowns
```

### Current Codebase Tree
```bash
.
├── src/
│   ├── __init__.py
│   ├── config/
│   │   └── settings.py              # Pydantic settings with validation
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── server.py                # MCP server skeleton
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── query_tool.py
│   │   │   └── sync_tool.py
│   │   └── websocket_server.py
│   └── services/
│       └── itglue/
│           ├── __init__.py
│           ├── models.py            # IT Glue data models
│           └── client.py            # IT Glue API client with rate limiting
├── docs/
│   └── it-glue-api-examples.py     # Comprehensive API examples
├── scripts/
│   └── test_mcp_server.py
├── PRPs/
│   └── templates/
│       └── prp_base.md
├── pyproject.toml                   # Poetry dependencies
├── Makefile                         # Development commands
└── CLAUDE.md                        # AI guidance rules
```

### Desired Codebase Tree with Files to be Added
```bash
.
├── src/
│   ├── data/
│   │   ├── __init__.py
│   │   ├── models.py               # SQLAlchemy models for PostgreSQL
│   │   ├── repositories.py         # Repository pattern for data access
│   │   └── migrations/             # Alembic migrations
│   ├── embeddings/
│   │   ├── __init__.py
│   │   ├── generator.py            # Embedding generation with Ollama/OpenAI
│   │   └── manager.py              # Embedding lifecycle management
│   ├── query/
│   │   ├── __init__.py
│   │   ├── engine.py               # Natural language query processor
│   │   ├── parser.py               # Query intent extraction
│   │   └── validator.py            # Zero-hallucination validation
│   ├── search/
│   │   ├── __init__.py
│   │   ├── semantic.py             # Semantic search with Qdrant
│   │   ├── hybrid.py               # Hybrid search (keyword + semantic)
│   │   └── ranker.py               # Result ranking and scoring
│   ├── sync/
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # Sync coordination
│   │   ├── incremental.py          # Incremental sync logic
│   │   └── tasks.py                # Celery async tasks
│   ├── cache/
│   │   ├── __init__.py
│   │   └── manager.py              # Redis cache management
│   └── api/
│       ├── __init__.py
│       └── app.py                  # FastAPI application
├── tests/
│   ├── unit/
│   │   ├── test_query_engine.py
│   │   ├── test_validator.py
│   │   └── test_embeddings.py
│   ├── integration/
│   │   ├── test_mcp_protocol.py
│   │   ├── test_search.py
│   │   └── test_sync.py
│   └── fixtures/
│       └── mock_data.py
├── alembic/
│   └── versions/                   # Database migrations
└── docker/
    └── Dockerfile                   # Production container
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: IT Glue API rate limiting
# - Max 100 requests per minute (settings.itglue_rate_limit)
# - Use exponential backoff on 429 errors
# - Pagination required for >1000 items per endpoint

# CRITICAL: MCP Protocol requirements
# - Must use mcp.server.Server class from official SDK
# - Tools must be registered with @server.tool() decorator
# - Response format must be JSON-serializable Dict
# - Stdio transport requires proper stream handling

# CRITICAL: Qdrant vector database
# - Collection must be created with proper dimension matching embeddings
# - Distance metric must be consistent (use Cosine for normalized embeddings)
# - Batch inserts limited to 100 points for optimal performance

# CRITICAL: Embedding generation
# - all-MiniLM-L6-v2 produces 384-dimensional vectors
# - Normalize embeddings for consistent cosine similarity
# - Ollama requires model to be pulled first: ollama pull all-minilm
# - OpenAI fallback uses text-embedding-ada-002 (1536 dimensions)

# CRITICAL: Zero-hallucination validation
# - Every response must track source document IDs
# - Confidence threshold: only return results >0.7 similarity
# - Return "No data available" instead of uncertain answers
```

## Implementation Blueprint

### Data Models and Structure

#### SQLAlchemy Models for PostgreSQL
```python
# src/data/models.py
from sqlalchemy import Column, String, JSON, DateTime, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

class ITGlueEntity(Base):
    """Base model for all IT Glue entities"""
    __tablename__ = 'itglue_entities'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    itglue_id = Column(String, unique=True, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)  # organization, configuration, etc.
    organization_id = Column(String, index=True)
    name = Column(String, nullable=False)
    attributes = Column(JSON)  # Store full IT Glue attributes
    relationships = Column(JSON)  # Store relationships
    
    # Search optimization fields
    search_text = Column(String)  # Concatenated searchable fields
    embedding_id = Column(String)  # Reference to Qdrant point ID
    
    # Tracking fields
    created_at = Column(DateTime, server_default='NOW()')
    updated_at = Column(DateTime, onupdate='NOW()')
    last_synced = Column(DateTime)
    
    # Add composite indexes for common queries
    __table_args__ = (
        Index('idx_org_type', 'organization_id', 'entity_type'),
        Index('idx_search', 'search_text'),
    )

class QueryLog(Base):
    """Audit log for all queries"""
    __tablename__ = 'query_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(String, nullable=False)
    company = Column(String)
    response = Column(JSON)
    confidence_score = Column(Float)
    source_ids = Column(JSON)  # List of source document IDs
    response_time_ms = Column(Float)
    created_at = Column(DateTime, server_default='NOW()')
```

### List of Tasks to Complete (In Order)

```yaml
Task 1: Setup Database Layer
MODIFY src/data/__init__.py:
  - CREATE database connection manager
  - IMPLEMENT connection pooling with SQLAlchemy
  - ADD retry logic for connection failures

CREATE src/data/repositories.py:
  - IMPLEMENT Repository pattern for data access
  - ADD methods: get_by_id, search, bulk_insert, update
  - INCLUDE transaction management

CREATE alembic.ini:
  - CONFIGURE Alembic for migrations
  - SET database URL from environment

Task 2: Implement IT Glue Sync Service
CREATE src/sync/orchestrator.py:
  - IMPLEMENT sync coordination logic
  - USE existing ITGlueClient from src/services/itglue/client.py
  - ADD progress tracking and error handling
  - RESPECT rate limiting (100 req/min)

CREATE src/sync/incremental.py:
  - IMPLEMENT incremental sync using last_synced timestamps
  - DETECT changes using updated_at fields
  - BATCH process entities for efficiency

Task 3: Build Embedding Generation Pipeline
CREATE src/embeddings/generator.py:
  - IMPLEMENT Ollama integration with all-MiniLM-L6-v2
  - ADD OpenAI fallback with text-embedding-ada-002
  - NORMALIZE embeddings for cosine similarity
  - BATCH process for efficiency (100 items per batch)

CREATE src/embeddings/manager.py:
  - MANAGE embedding lifecycle
  - TRACK which entities have embeddings
  - HANDLE re-embedding on updates

Task 4: Setup Qdrant Vector Database
CREATE src/search/semantic.py:
  - INITIALIZE Qdrant client and collections
  - IMPLEMENT vector search with metadata filtering
  - ADD similarity threshold checking (>0.7)
  - RETURN source document IDs with results

Task 5: Implement Query Engine with Validation
CREATE src/query/parser.py:
  - EXTRACT intent from natural language queries
  - IDENTIFY entity types (router, printer, password, etc.)
  - PARSE company names and filters

CREATE src/query/validator.py:
  - IMPLEMENT zero-hallucination validation
  - VERIFY responses against source documents
  - CALCULATE confidence scores
  - ENFORCE "No data available" for uncertain results

CREATE src/query/engine.py:
  - ORCHESTRATE query processing pipeline
  - COMBINE semantic and keyword search
  - APPLY validation before returning results
  - TRACK source documents for audit

Task 6: Implement Cache Layer
CREATE src/cache/manager.py:
  - IMPLEMENT Redis cache with 5-minute TTL
  - CACHE query results by hash of (query + company)
  - INVALIDATE on data sync
  - ADD cache hit/miss metrics

Task 7: Complete MCP Server Implementation
MODIFY src/mcp/server.py:
  - WIRE UP query engine to query tool
  - IMPLEMENT list_companies tool properly
  - ADD search tool with cross-company support
  - ENSURE proper error handling and logging

CREATE src/mcp/tools/company_tool.py:
  - IMPLEMENT company-specific queries
  - ADD filtering by organization
  - RETURN structured responses

Task 8: Add FastAPI for Health & Admin
CREATE src/api/app.py:
  - IMPLEMENT health check endpoints
  - ADD sync status endpoint
  - CREATE metrics endpoint for monitoring
  - INCLUDE OpenAPI documentation

Task 9: Create Comprehensive Tests
CREATE tests/unit/test_query_engine.py:
  - TEST query parsing logic
  - TEST validation thresholds
  - MOCK external dependencies

CREATE tests/unit/test_validator.py:
  - TEST zero-hallucination validation
  - TEST confidence scoring
  - TEST source tracking

CREATE tests/integration/test_mcp_protocol.py:
  - TEST MCP protocol compliance
  - TEST tool registration and execution
  - VERIFY response formats

Task 10: Production Readiness
CREATE docker/Dockerfile:
  - MULTI-STAGE build for optimization
  - INCLUDE all dependencies
  - SET proper environment variables

MODIFY Makefile:
  - ENSURE all commands work
  - ADD production deployment targets
  - INCLUDE health check commands
```

### Per-Task Pseudocode

```python
# Task 1: Database Connection Manager
# src/data/__init__.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from src.config.settings import settings
import backoff

class DatabaseManager:
    def __init__(self):
        # PATTERN: Connection pooling for concurrent access
        self.engine = create_engine(
            settings.database_url,
            pool_size=20,  # Match settings.max_connections / 5
            max_overflow=0,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600  # Recycle connections hourly
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def get_session(self):
        # PATTERN: Retry on connection failures
        return self.SessionLocal()

# Task 5: Zero-Hallucination Validator
# src/query/validator.py
class ZeroHallucinationValidator:
    def __init__(self, confidence_threshold: float = 0.7):
        self.threshold = confidence_threshold
        self.repository = ITGlueRepository()
    
    async def validate_response(
        self, 
        response: Dict,
        source_ids: List[str],
        similarity_scores: List[float]
    ) -> ValidationResult:
        # CRITICAL: Verify every claim against source
        if not source_ids:
            return ValidationResult(
                valid=False,
                message="No source documents found",
                confidence=0.0
            )
        
        # PATTERN: Check confidence threshold
        avg_similarity = sum(similarity_scores) / len(similarity_scores)
        if avg_similarity < self.threshold:
            return ValidationResult(
                valid=False,
                message="Response confidence below threshold",
                confidence=avg_similarity
            )
        
        # CRITICAL: Verify source documents exist
        sources = await self.repository.get_by_ids(source_ids)
        if len(sources) != len(source_ids):
            return ValidationResult(
                valid=False,
                message="Source documents not found",
                confidence=0.0
            )
        
        # PATTERN: Return validated response with sources
        return ValidationResult(
            valid=True,
            response=response,
            source_ids=source_ids,
            confidence=avg_similarity
        )

# Task 4: Semantic Search with Qdrant
# src/search/semantic.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class SemanticSearch:
    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection_name = "itglue_entities"
        
    async def initialize_collection(self):
        # CRITICAL: Dimension must match embedding model
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=384,  # all-MiniLM-L6-v2 dimensions
                distance=Distance.COSINE
            )
        )
    
    async def search(
        self,
        query_embedding: List[float],
        company_id: Optional[str] = None,
        limit: int = 10
    ) -> List[SearchResult]:
        # PATTERN: Apply metadata filtering
        filter_conditions = []
        if company_id:
            filter_conditions.append({
                "key": "organization_id",
                "match": {"value": company_id}
            })
        
        # CRITICAL: Search with similarity threshold
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            filter=filter_conditions,
            limit=limit,
            score_threshold=0.7  # Only high-confidence results
        )
        
        # PATTERN: Return with source tracking
        return [
            SearchResult(
                id=hit.id,
                score=hit.score,
                payload=hit.payload,
                source_id=hit.payload.get("itglue_id")
            )
            for hit in results
        ]
```

### Integration Points
```yaml
DATABASE:
  - migration: "alembic upgrade head"
  - indexes: 
    - "CREATE INDEX idx_entities_org_type ON itglue_entities(organization_id, entity_type)"
    - "CREATE INDEX idx_entities_search ON itglue_entities USING gin(to_tsvector('english', search_text))"

CONFIG:
  - add to: src/config/settings.py
  - pattern: "sync_batch_size: int = Field(100, description='Batch size for sync')"
  - pattern: "embedding_batch_size: int = Field(50, description='Batch size for embeddings')"

CELERY:
  - add to: src/workers/celery_app.py
  - tasks: ["sync_organization", "generate_embeddings", "cleanup_old_logs"]
  - schedule: {"sync_all": {"task": "sync.all", "schedule": crontab(minute="*/15")}}

REDIS:
  - pattern: "cache_key = hashlib.md5(f'{query}:{company}'.encode()).hexdigest()"
  - ttl: 300  # 5 minutes
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
poetry run black src/ tests/ --check
poetry run isort src/ tests/ --check
poetry run ruff check src/ --fix
poetry run mypy src/

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests
```python
# tests/unit/test_query_engine.py
import pytest
from src.query.engine import QueryEngine
from src.query.validator import ZeroHallucinationValidator

def test_query_parsing():
    """Test natural language query parsing"""
    engine = QueryEngine()
    result = engine.parse_query("What's the router IP for Company A?")
    assert result.entity_type == "router"
    assert result.company == "Company A"
    assert result.intent == "get_attribute"

def test_validation_threshold():
    """Test confidence threshold enforcement"""
    validator = ZeroHallucinationValidator(threshold=0.7)
    result = validator.validate_response(
        response={"ip": "192.168.1.1"},
        source_ids=["doc-123"],
        similarity_scores=[0.6]  # Below threshold
    )
    assert not result.valid
    assert "below threshold" in result.message

def test_no_hallucination():
    """Test zero-hallucination guarantee"""
    validator = ZeroHallucinationValidator()
    result = validator.validate_response(
        response={"data": "test"},
        source_ids=[],  # No sources
        similarity_scores=[]
    )
    assert not result.valid
    assert result.confidence == 0.0

@pytest.mark.asyncio
async def test_semantic_search():
    """Test semantic search with filtering"""
    from src.search.semantic import SemanticSearch
    search = SemanticSearch()
    
    # Mock embedding for "router configuration"
    query_embedding = [0.1] * 384  # all-MiniLM-L6-v2 dimension
    
    results = await search.search(
        query_embedding=query_embedding,
        company_id="org-123",
        limit=5
    )
    
    # Verify all results are from correct company
    for result in results:
        assert result.payload.get("organization_id") == "org-123"
        assert result.score >= 0.7  # Threshold enforcement
```

```bash
# Run unit tests
poetry run pytest tests/unit/ -v --cov=src --cov-report=term-missing

# Expected: All tests pass with >80% coverage
```

### Level 3: Integration Tests
```python
# tests/integration/test_mcp_protocol.py
import asyncio
import json
from src.mcp.server import ITGlueMCPServer

async def test_mcp_query_tool():
    """Test MCP query tool end-to-end"""
    server = ITGlueMCPServer()
    
    # Test query tool
    result = await server.query(
        query="What's the printer IP for Happy Frog?",
        company="Happy Frog"
    )
    
    assert result["success"] in [True, False]
    if result["success"]:
        assert "data" in result
        assert "source" in result
    else:
        assert result.get("error") == "No data available"

async def test_mcp_list_companies():
    """Test company listing tool"""
    server = ITGlueMCPServer()
    
    result = await server.list_companies()
    assert result["success"] is True
    assert "companies" in result
    assert isinstance(result["companies"], list)
```

```bash
# Run integration tests
poetry run pytest tests/integration/ -v

# Test MCP server directly
python scripts/test_mcp_server.py
```

### Level 4: End-to-End Test
```bash
# Start all services
make docker-run

# Wait for services
sleep 10

# Run initial sync
poetry run python -m src.sync.orchestrator --initial

# Test MCP server
echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' | \
  poetry run python -m src.mcp.server

# Test API health
curl http://localhost:8002/health

# Test a real query
curl -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What printers does Happy Frog have?",
    "company": "Happy Frog"
  }'

# Expected: JSON response with printer information or "No data available"
```

## Final Validation Checklist
- [ ] All tests pass: `poetry run pytest tests/ -v`
- [ ] No linting errors: `poetry run ruff check src/`
- [ ] No type errors: `poetry run mypy src/`
- [ ] MCP protocol test passes: `python scripts/test_mcp_server.py`
- [ ] Response time <2s: Check logs for response_time_ms
- [ ] Zero hallucination: All responses have source_ids
- [ ] Rate limiting works: No 429 errors in logs
- [ ] Cache functioning: Redis has keys after queries
- [ ] Documentation updated: README includes setup instructions

---

## Anti-Patterns to Avoid
- ❌ Don't skip source validation - EVERY response needs source tracking
- ❌ Don't ignore rate limits - IT Glue will block the API key
- ❌ Don't return uncertain answers - Use "No data available" instead
- ❌ Don't mix embedding dimensions - Keep consistent with model choice
- ❌ Don't cache sensitive passwords - Only cache non-sensitive queries
- ❌ Don't use synchronous operations in async context - Keep async/await consistent
- ❌ Don't hardcode IT Glue IDs - Use configuration and dynamic lookup

## Performance Optimization Notes
- Use connection pooling for all databases (PostgreSQL, Redis, Neo4j)
- Batch API requests to IT Glue (max 100 per batch)
- Generate embeddings in parallel using asyncio
- Cache frequent queries with Redis (5-minute TTL)
- Use database indexes for common query patterns
- Implement circuit breaker for external service failures

## Security Considerations
- Never log or cache actual passwords from IT Glue
- Use environment variables for all secrets
- Implement row-level security in PostgreSQL for multi-tenant scenarios
- Validate and sanitize all user inputs
- Use prepared statements to prevent SQL injection
- Implement API rate limiting on FastAPI endpoints

---

## Confidence Score: 9/10

This PRP provides comprehensive context for one-pass implementation success. The score is 9/10 because:
- ✅ All external documentation and APIs are referenced
- ✅ Existing codebase patterns are identified and reused
- ✅ Clear task breakdown with dependencies
- ✅ Validation loops at multiple levels
- ✅ Known gotchas are documented
- ✅ Production considerations included
- ⚠️ Minor uncertainty around specific Celery task scheduling patterns (can be refined during implementation)

The implementation should proceed smoothly with this level of detail and context.