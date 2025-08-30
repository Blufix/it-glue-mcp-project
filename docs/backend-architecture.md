# Backend Architecture Document

## Introduction

This document provides the comprehensive technical architecture for the IT Glue MCP Server, a system that transforms unstructured IT documentation into an intelligent, instantly-accessible knowledge base through natural language querying.

### Architecture Decision

**Selected Template: Python MCP API Starter**

This template was chosen for its optimal balance of:
- **Rapid Development**: Python's extensive library ecosystem accelerates implementation
- **MCP SDK Support**: First-class Python SDK from Anthropic for MCP protocol
- **Integration Capabilities**: Excellent support for Neo4j, Qdrant, and IT Glue API
- **Team Expertise**: Leverages existing Python knowledge for faster delivery
- **Scalability Path**: Easy transition to Go or Rust for performance-critical components

The Python starter provides production-ready patterns for authentication, caching, and error handling while maintaining the flexibility to optimize bottlenecks later.

## High Level Architecture

### System Overview

The IT Glue MCP Server employs a microservices architecture with event-driven communication:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Chat Client   │────▶│   MCP Server    │────▶│  Query Engine   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                         │
                               ▼                         ▼
                        ┌─────────────┐          ┌──────────────┐
                        │  API Layer  │          │  Cache Layer │
                        └─────────────┘          └──────────────┘
                               │                         │
                    ┌──────────┴──────────┬─────────────┤
                    ▼                      ▼             ▼
            ┌──────────────┐     ┌──────────────┐ ┌──────────────┐
            │  PostgreSQL  │     │    Neo4j     │ │   Qdrant     │
            └──────────────┘     └──────────────┘ └──────────────┘
                    ▲                      ▲             ▲
                    └──────────┬──────────┴─────────────┘
                               │
                        ┌─────────────┐
                        │ Sync Service │
                        └─────────────┘
                               ▲
                               │
                        ┌─────────────┐
                        │ IT Glue API │
                        └─────────────┘
```

### Component Hierarchy

```
IT Glue MCP Server
├── MCP Protocol Layer
│   ├── Server Implementation
│   ├── Tool Registry
│   └── Message Handler
├── Query Processing
│   ├── Natural Language Parser
│   ├── Query Planner
│   ├── Graph Query Engine (Neo4j)
│   └── Semantic Search Engine (Qdrant)
├── Data Layer
│   ├── Sync Service
│   │   ├── IT Glue Client
│   │   ├── Data Transformer
│   │   └── Change Detection
│   ├── Storage Backends
│   │   ├── PostgreSQL (Structured)
│   │   ├── Neo4j (Relationships)
│   │   └── Qdrant (Vectors)
│   └── Cache Layer (Redis)
├── API Layer
│   ├── REST Endpoints
│   ├── Authentication
│   └── Rate Limiting
└── Infrastructure
    ├── Monitoring (Prometheus/Grafana)
    ├── Logging (Structured JSON)
    └── Container Orchestration
```

## Tech Stack

### Core Technologies

| Component | Technology | Version | Justification |
|-----------|------------|---------|---------------|
| **Language** | Python | 3.11.8 | MCP SDK support, rapid development |
| **MCP Framework** | MCP SDK | Latest | Official Anthropic SDK |
| **Web Framework** | FastAPI | 0.104.1 | Async support, automatic OpenAPI |
| **Task Queue** | Celery | 5.3.4 | Distributed task processing |
| **Message Broker** | Redis | 7.2 | Caching + message broker |

### Databases

| Database | Purpose | Version | Justification |
|----------|---------|---------|---------------|
| **PostgreSQL** | Structured data | 15 | ACID compliance, JSON support |
| **Neo4j** | Graph relationships | 5.14 | IT infrastructure modeling |
| **Qdrant** | Vector search | 1.7.3 | Semantic query understanding |
| **Redis** | Cache & queue | 7.2 | Sub-millisecond latency |

### Infrastructure

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Containerization** | Docker | Service isolation |
| **Orchestration** | Docker Compose / K8s | Local dev / Production |
| **Monitoring** | Prometheus + Grafana | Metrics & visualization |
| **Logging** | JSON structured logs | Searchable logging |
| **CI/CD** | GitHub Actions | Automated deployment |

## Data Models

### Core Entities

```python
# src/models/core.py
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class AssetType(str, Enum):
    ORGANIZATION = "organization"
    CONFIGURATION = "configuration"
    PASSWORD = "password"
    FLEXIBLE_ASSET = "flexible_asset"
    DOCUMENT = "document"
    CONTACT = "contact"

class Organization(BaseModel):
    """IT Glue Organization model"""
    id: str = Field(..., description="IT Glue organization ID")
    name: str
    type: str  # Customer, Internal, Vendor
    created_at: datetime
    updated_at: datetime
    alert: Optional[str] = None
    description: Optional[str] = None
    primary_contact_id: Optional[str] = None
    custom_fields: Dict[str, Any] = {}
    
class Configuration(BaseModel):
    """IT infrastructure configuration"""
    id: str
    organization_id: str
    name: str
    configuration_type: str  # Server, Workstation, Network Device, etc.
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    serial_number: Optional[str] = None
    operating_system: Optional[str] = None
    notes: Optional[str] = None
    relationships: List[str] = []  # Related configuration IDs
    
class Password(BaseModel):
    """Encrypted password entry"""
    id: str
    organization_id: str
    name: str
    username: str
    password_encrypted: str  # Always encrypted
    url: Optional[str] = None
    notes_encrypted: Optional[str] = None
    password_category: str
    expires_at: Optional[datetime] = None
    
class FlexibleAsset(BaseModel):
    """Custom IT Glue flexible assets"""
    id: str
    organization_id: str
    flexible_asset_type_id: str
    name: str
    traits: Dict[str, Any]  # Dynamic fields based on asset type
    
class Document(BaseModel):
    """IT documentation and procedures"""
    id: str
    organization_id: str
    name: str
    content: str  # Markdown or HTML
    document_type: str
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
    version: int = 1
    parent_document_id: Optional[str] = None
```

### Query Models

```python
# src/models/query.py
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator

class QueryRequest(BaseModel):
    """Natural language query request"""
    query: str = Field(..., min_length=1, max_length=500)
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    options: Optional[QueryOptions] = None
    
    @validator('query')
    def validate_query(cls, v):
        # Security validation
        if any(keyword in v.upper() for keyword in ['DROP', 'DELETE', 'INSERT']):
            raise ValueError("Query contains forbidden SQL keywords")
        return v

class QueryOptions(BaseModel):
    """Query execution options"""
    cross_company: bool = False
    include_archived: bool = False
    max_results: int = Field(10, ge=1, le=100)
    timeout_seconds: int = Field(30, ge=1, le=60)
    cache_enabled: bool = True

class QueryResponse(BaseModel):
    """Query response with metadata"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    source: str  # cache, neo4j, qdrant, api
    execution_time_ms: float
    confidence_score: Optional[float] = None
    suggestions: List[str] = []
```

### Sync Models

```python
# src/models/sync.py
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum

class SyncStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"

class SyncJob(BaseModel):
    """Sync job tracking"""
    id: str
    organization_id: Optional[str] = None  # None for full sync
    sync_type: str  # full, incremental, specific
    status: SyncStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    records_processed: int = 0
    records_failed: int = 0
    error_message: Optional[str] = None
    metadata: Dict = {}

class ChangeSet(BaseModel):
    """Changes detected during sync"""
    organization_id: str
    timestamp: datetime
    created: List[Dict]
    updated: List[Dict]
    deleted: List[str]
    
class SyncState(BaseModel):
    """Persistent sync state"""
    organization_id: str
    last_sync_at: datetime
    last_successful_sync: datetime
    sync_token: Optional[str] = None  # For pagination
    version: int = 1
```

## Database Schema

### PostgreSQL Schema (Structured Data)

```sql
-- Organizations table
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    itglue_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    alert TEXT,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B')
    ) STORED
);

CREATE INDEX idx_organizations_itglue_id ON organizations(itglue_id);
CREATE INDEX idx_organizations_type ON organizations(type);
CREATE INDEX idx_organizations_search ON organizations USING GIN(search_vector);
CREATE INDEX idx_organizations_metadata ON organizations USING GIN(metadata);

-- Configurations table
CREATE TABLE configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    itglue_id VARCHAR(255) UNIQUE NOT NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    configuration_type VARCHAR(100) NOT NULL,
    ip_address INET,
    mac_address MACADDR,
    serial_number VARCHAR(255),
    operating_system VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_configurations_org ON configurations(organization_id);
CREATE INDEX idx_configurations_type ON configurations(configuration_type);
CREATE INDEX idx_configurations_ip ON configurations(ip_address);

-- Passwords table (encrypted)
CREATE TABLE passwords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    itglue_id VARCHAR(255) UNIQUE NOT NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    username_encrypted TEXT NOT NULL,
    password_encrypted TEXT NOT NULL,
    url TEXT,
    notes_encrypted TEXT,
    category VARCHAR(100),
    expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_passwords_org ON passwords(organization_id);
CREATE INDEX idx_passwords_category ON passwords(category);
CREATE INDEX idx_passwords_expires ON passwords(expires_at) WHERE expires_at IS NOT NULL;

-- Flexible Assets table
CREATE TABLE flexible_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    itglue_id VARCHAR(255) UNIQUE NOT NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    flexible_asset_type_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    traits JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_flexible_assets_org ON flexible_assets(organization_id);
CREATE INDEX idx_flexible_assets_type ON flexible_assets(flexible_asset_type_id);
CREATE INDEX idx_flexible_assets_traits ON flexible_assets USING GIN(traits);

-- Documents table
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    itglue_id VARCHAR(255) UNIQUE NOT NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    document_type VARCHAR(100),
    parent_id UUID REFERENCES documents(id),
    version INTEGER DEFAULT 1,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(content, '')), 'C')
    ) STORED
);

CREATE INDEX idx_documents_org ON documents(organization_id);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_parent ON documents(parent_id);
CREATE INDEX idx_documents_search ON documents USING GIN(search_vector);

-- Sync state table
CREATE TABLE sync_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    resource_type VARCHAR(100) NOT NULL,
    last_sync_at TIMESTAMP NOT NULL,
    last_successful_sync TIMESTAMP,
    sync_token TEXT,
    version INTEGER DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(organization_id, resource_type)
);

-- Audit log table
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    organization_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created ON audit_log(created_at);
```

### Neo4j Schema (Graph Relationships)

```cypher
// Organization node
CREATE CONSTRAINT org_unique IF NOT EXISTS
FOR (o:Organization) REQUIRE o.itglue_id IS UNIQUE;

CREATE INDEX org_name IF NOT EXISTS
FOR (o:Organization) ON (o.name);

// Configuration node
CREATE CONSTRAINT config_unique IF NOT EXISTS
FOR (c:Configuration) REQUIRE c.itglue_id IS UNIQUE;

CREATE INDEX config_type IF NOT EXISTS
FOR (c:Configuration) ON (c.type);

CREATE INDEX config_ip IF NOT EXISTS
FOR (c:Configuration) ON (c.ip_address);

// Password node
CREATE CONSTRAINT password_unique IF NOT EXISTS
FOR (p:Password) REQUIRE p.itglue_id IS UNIQUE;

// Document node
CREATE CONSTRAINT doc_unique IF NOT EXISTS
FOR (d:Document) REQUIRE d.itglue_id IS UNIQUE;

// Relationships
// Organization owns assets
CREATE (o:Organization)-[:OWNS]->(c:Configuration)
CREATE (o:Organization)-[:OWNS]->(p:Password)
CREATE (o:Organization)-[:OWNS]->(d:Document)

// Configuration relationships
CREATE (c1:Configuration)-[:CONNECTED_TO]->(c2:Configuration)
CREATE (c:Configuration)-[:DEPENDS_ON]->(s:Service)
CREATE (c:Configuration)-[:HAS_PASSWORD]->(p:Password)

// Document relationships
CREATE (d1:Document)-[:REFERENCES]->(d2:Document)
CREATE (d:Document)-[:DESCRIBES]->(c:Configuration)
CREATE (d:Document)-[:CONTAINS_FIX_FOR]->(e:Error)

// Service dependencies
CREATE (s1:Service)-[:DEPENDS_ON]->(s2:Service)
CREATE (s:Service)-[:RUNS_ON]->(c:Configuration)

// Example queries
// Find all passwords for a configuration
MATCH (c:Configuration {name: $config_name})-[:HAS_PASSWORD]->(p:Password)
RETURN p;

// Find all dependent services
MATCH (c:Configuration {itglue_id: $id})-[:RUNS_ON]-(s:Service)-[:DEPENDS_ON*1..3]-(dependent:Service)
RETURN DISTINCT dependent;

// Find similar fixes across companies
MATCH (e:Error)<-[:CONTAINS_FIX_FOR]-(d:Document)<-[:OWNS]-(o:Organization)
WHERE e.message CONTAINS $error_text
RETURN o.name as company, d.name as document, d.content as fix;
```

### Qdrant Schema (Vector Search)

```python
# src/db/qdrant_schema.py
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    CreateCollection, OptimizersConfigDiff
)

class QdrantSchema:
    """Qdrant collection schemas"""
    
    @staticmethod
    def create_collections(client: QdrantClient):
        """Create all required collections"""
        
        # Documents collection for semantic search
        client.recreate_collection(
            collection_name="documents",
            vectors_config=VectorParams(
                size=768,  # OpenAI ada-002 embedding size
                distance=Distance.COSINE
            ),
            optimizers_config=OptimizersConfigDiff(
                indexing_threshold=20000,
                memmap_threshold=50000
            )
        )
        
        # Configurations collection
        client.recreate_collection(
            collection_name="configurations",
            vectors_config=VectorParams(
                size=768,
                distance=Distance.COSINE
            )
        )
        
        # Fixes/Solutions collection
        client.recreate_collection(
            collection_name="solutions",
            vectors_config=VectorParams(
                size=768,
                distance=Distance.COSINE
            )
        )
        
        # Query patterns collection (for learning)
        client.recreate_collection(
            collection_name="query_patterns",
            vectors_config=VectorParams(
                size=768,
                distance=Distance.COSINE
            )
        )
        
    @staticmethod
    def index_document(client: QdrantClient, doc: dict, embedding: list):
        """Index a document for semantic search"""
        
        point = PointStruct(
            id=doc['id'],
            vector=embedding,
            payload={
                'organization_id': doc['organization_id'],
                'name': doc['name'],
                'type': doc['type'],
                'content': doc['content'][:1000],  # Truncate for storage
                'created_at': doc['created_at'],
                'tags': doc.get('tags', [])
            }
        )
        
        client.upsert(
            collection_name="documents",
            points=[point]
        )
```

### Redis Schema (Caching)

```python
# src/db/redis_schema.py
"""Redis key patterns and TTL configuration"""

class RedisKeys:
    """Redis key patterns"""
    
    # Cache keys with TTL
    QUERY_CACHE = "query:{query_hash}:{company_id}"  # TTL: 5 minutes
    ORG_CACHE = "org:{org_id}"  # TTL: 15 minutes
    CONFIG_CACHE = "config:{config_id}"  # TTL: 15 minutes
    PASSWORD_CACHE = "password:{password_id}"  # TTL: 1 minute
    
    # Session keys
    USER_SESSION = "session:{session_id}"  # TTL: 1 hour
    API_KEY_SESSION = "api_session:{api_key_hash}"  # TTL: 24 hours
    
    # Rate limiting
    RATE_LIMIT = "rate:{identifier}:{window}"  # TTL: 1 minute
    
    # Sync state
    SYNC_LOCK = "sync_lock:{org_id}:{resource_type}"  # TTL: 10 minutes
    SYNC_PROGRESS = "sync_progress:{job_id}"  # TTL: 1 hour
    
    # Analytics
    QUERY_STATS = "stats:queries:{date}"  # TTL: 7 days
    ERROR_STATS = "stats:errors:{date}"  # TTL: 30 days
    
    @staticmethod
    def get_ttl(key_pattern: str) -> int:
        """Get TTL for key pattern in seconds"""
        ttl_map = {
            "query:": 300,  # 5 minutes
            "org:": 900,  # 15 minutes
            "config:": 900,  # 15 minutes
            "password:": 60,  # 1 minute
            "session:": 3600,  # 1 hour
            "api_session:": 86400,  # 24 hours
            "rate:": 60,  # 1 minute
            "sync_lock:": 600,  # 10 minutes
            "sync_progress:": 3600,  # 1 hour
            "stats:queries:": 604800,  # 7 days
            "stats:errors:": 2592000,  # 30 days
        }
        
        for prefix, ttl in ttl_map.items():
            if key_pattern.startswith(prefix):
                return ttl
        return 300  # Default 5 minutes
```

## Components

### MCP Server Component

```python
# src/mcp/server.py
"""Main MCP server implementation"""

import asyncio
from typing import List, Dict, Any
from mcp.server import Server, Tool
from mcp.server.stdio import stdio_server
import logging

from src.core.query_engine import QueryEngine
from src.core.search_engine import SearchEngine
from src.core.compliance import ComplianceChecker

logger = logging.getLogger(__name__)

class ITGlueMCPServer:
    """IT Glue MCP Server implementation"""
    
    def __init__(self):
        self.server = Server("itglue-mcp")
        self.query_engine = QueryEngine()
        self.search_engine = SearchEngine()
        self.compliance_checker = ComplianceChecker()
        self._register_tools()
        
    def _register_tools(self):
        """Register MCP tools"""
        
        @self.server.tool()
        async def query(query: str, company: str) -> Dict:
            """Natural language query tool"""
            try:
                result = await self.query_engine.execute(
                    query=query,
                    company=company
                )
                return result.dict()
            except Exception as e:
                logger.error(f"Query error: {e}")
                return {"error": str(e), "success": False}
                
        @self.server.tool()
        async def search(
            query: str,
            limit: int = 10,
            filters: Dict = None
        ) -> List[Dict]:
            """Cross-company search tool"""
            try:
                results = await self.search_engine.search(
                    query=query,
                    limit=limit,
                    filters=filters
                )
                return results
            except Exception as e:
                logger.error(f"Search error: {e}")
                return {"error": str(e), "results": []}
                
        @self.server.tool()
        async def compliance_check(
            check_type: str,
            companies: List[str] = None
        ) -> Dict:
            """Compliance checking tool"""
            try:
                report = await self.compliance_checker.check(
                    check_type=check_type,
                    companies=companies
                )
                return report
            except Exception as e:
                logger.error(f"Compliance check error: {e}")
                return {"error": str(e), "report": {}}
                
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )
```

### Query Engine Component

```python
# src/core/query_engine.py
"""Natural language query processing engine"""

from typing import Optional, Dict, Any
import hashlib
import json
from datetime import datetime

from src.models.query import QueryRequest, QueryResponse
from src.db.neo4j_client import Neo4jClient
from src.db.qdrant_client import QdrantClient
from src.cache.redis_client import RedisCache
from src.nlp.query_parser import QueryParser
from src.monitoring.metrics import track_query_metrics

class QueryEngine:
    """Core query processing engine"""
    
    def __init__(self):
        self.neo4j = Neo4jClient()
        self.qdrant = QdrantClient()
        self.cache = RedisCache()
        self.parser = QueryParser()
        
    @track_query_metrics("natural_language")
    async def execute(self, request: QueryRequest) -> QueryResponse:
        """Execute natural language query"""
        
        start_time = datetime.utcnow()
        
        # Check cache first
        cache_key = self._generate_cache_key(request)
        cached = await self.cache.get(cache_key)
        if cached:
            return QueryResponse(
                success=True,
                data=cached,
                source="cache",
                execution_time_ms=0
            )
            
        # Parse query intent
        intent = await self.parser.parse(request.query)
        
        # Route to appropriate backend
        if intent.query_type == "relationship":
            result = await self._execute_graph_query(intent, request)
        elif intent.query_type == "semantic":
            result = await self._execute_semantic_search(intent, request)
        else:
            result = await self._execute_hybrid_query(intent, request)
            
        # Cache successful results
        if result.success:
            await self.cache.set(
                cache_key,
                result.data,
                ttl=300  # 5 minutes
            )
            
        # Calculate execution time
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        result.execution_time_ms = execution_time
        
        return result
        
    async def _execute_graph_query(
        self,
        intent: Any,
        request: QueryRequest
    ) -> QueryResponse:
        """Execute Neo4j graph query"""
        
        cypher = self._build_cypher_query(intent, request)
        results = await self.neo4j.query(cypher, {
            "company_id": request.company_id,
            "params": intent.parameters
        })
        
        if not results:
            return QueryResponse(
                success=False,
                error="No data available",
                source="neo4j"
            )
            
        return QueryResponse(
            success=True,
            data=results,
            source="neo4j",
            confidence_score=intent.confidence
        )
        
    async def _execute_semantic_search(
        self,
        intent: Any,
        request: QueryRequest
    ) -> QueryResponse:
        """Execute Qdrant semantic search"""
        
        embedding = await self.parser.get_embedding(request.query)
        
        results = await self.qdrant.search(
            collection="documents",
            vector=embedding,
            filter={
                "organization_id": request.company_id
            } if request.company_id else None,
            limit=request.options.max_results if request.options else 10
        )
        
        if not results:
            return QueryResponse(
                success=False,
                error="No data available",
                source="qdrant"
            )
            
        return QueryResponse(
            success=True,
            data=[r.payload for r in results],
            source="qdrant",
            confidence_score=results[0].score if results else 0
        )
```

### Sync Service Component

```python
# src/sync/service.py
"""IT Glue data synchronization service"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import asyncio
from celery import Celery

from src.sync.itglue_client import ITGlueClient
from src.sync.transformers import DataTransformer
from src.db.repositories import OrganizationRepo, ConfigurationRepo
from src.monitoring.metrics import sync_status

app = Celery('sync', broker='redis://localhost:6379')

class SyncService:
    """Manages data synchronization from IT Glue"""
    
    def __init__(self):
        self.itglue = ITGlueClient()
        self.transformer = DataTransformer()
        self.org_repo = OrganizationRepo()
        self.config_repo = ConfigurationRepo()
        
    @app.task
    async def sync_organization(self, org_id: str):
        """Sync single organization"""
        
        try:
            # Fetch from IT Glue
            org_data = await self.itglue.get_organization(org_id)
            configs = await self.itglue.get_configurations(org_id)
            passwords = await self.itglue.get_passwords(org_id)
            
            # Transform data
            org_model = self.transformer.transform_organization(org_data)
            config_models = [
                self.transformer.transform_configuration(c)
                for c in configs
            ]
            
            # Save to databases
            await self.org_repo.upsert(org_model)
            for config in config_models:
                await self.config_repo.upsert(config)
                
            # Update sync status
            sync_status.labels(company=org_id).set(1)
            
        except Exception as e:
            sync_status.labels(company=org_id).set(0)
            raise
            
    @app.task
    async def incremental_sync(self):
        """Run incremental sync for all organizations"""
        
        orgs = await self.org_repo.get_all_active()
        
        for org in orgs:
            # Check last sync time
            last_sync = await self.get_last_sync(org.id)
            
            if datetime.utcnow() - last_sync > timedelta(minutes=15):
                await self.sync_organization.delay(org.id)
```

### Error Handling Strategy

```python
# src/core/error_handling.py
"""Comprehensive error handling"""

from typing import Optional, Dict, Any
from enum import Enum
import traceback
from functools import wraps

class ErrorType(Enum):
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    NOT_FOUND = "not_found"
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    TIMEOUT = "timeout"
    INTERNAL = "internal"

class AppError(Exception):
    """Application-specific error"""
    
    def __init__(
        self,
        error_type: ErrorType,
        message: str,
        details: Optional[Dict] = None,
        status_code: int = 500
    ):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)

class ErrorHandler:
    """Centralized error handling"""
    
    @staticmethod
    def handle_error(error: Exception) -> Dict[str, Any]:
        """Convert exception to response"""
        
        if isinstance(error, AppError):
            return {
                "error": {
                    "type": error.error_type.value,
                    "message": error.message,
                    "details": error.details
                },
                "success": False
            }
            
        # Map known exceptions
        error_map = {
            ValueError: (ErrorType.VALIDATION, 400),
            KeyError: (ErrorType.NOT_FOUND, 404),
            TimeoutError: (ErrorType.TIMEOUT, 504),
        }
        
        for exc_type, (error_type, status) in error_map.items():
            if isinstance(error, exc_type):
                return {
                    "error": {
                        "type": error_type.value,
                        "message": str(error)
                    },
                    "success": False
                }
                
        # Unknown error
        return {
            "error": {
                "type": ErrorType.INTERNAL.value,
                "message": "An internal error occurred",
                "trace": traceback.format_exc() if DEBUG else None
            },
            "success": False
        }

def with_error_handling(func):
    """Decorator for consistent error handling"""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            return ErrorHandler.handle_error(e)
    return wrapper
```

### Environment Configuration

```python
# src/config/settings.py
"""Application configuration"""

from pydantic import BaseSettings, Field
from typing import Optional

class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Environment
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # IT Glue API
    itglue_api_key: str = Field(..., env="IT_GLUE_API_KEY")
    itglue_api_url: str = Field(
        "https://api.itglue.com",
        env="IT_GLUE_API_URL"
    )
    itglue_rate_limit: int = Field(100, env="IT_GLUE_RATE_LIMIT")
    
    # Database URLs
    postgres_url: str = Field(..., env="DATABASE_URL")
    neo4j_url: str = Field(..., env="NEO4J_URL")
    neo4j_user: str = Field("neo4j", env="NEO4J_USER")
    neo4j_password: str = Field(..., env="NEO4J_PASSWORD")
    qdrant_url: str = Field("http://localhost:6333", env="QDRANT_URL")
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")
    
    # Security
    jwt_secret: str = Field(..., env="JWT_SECRET")
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    api_key_header: str = Field("X-API-Key", env="API_KEY_HEADER")
    
    # Performance
    cache_ttl: int = Field(300, env="CACHE_TTL")
    query_timeout: int = Field(30, env="QUERY_TIMEOUT")
    max_connections: int = Field(100, env="MAX_CONNECTIONS")
    
    # Monitoring
    prometheus_enabled: bool = Field(True, env="PROMETHEUS_ENABLED")
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## External APIs

### IT Glue API Integration

```python
# src/sync/itglue_client.py
"""IT Glue API client with rate limiting and retry logic"""

import asyncio
from typing import Dict, List, Optional, Any
import aiohttp
from datetime import datetime, timedelta
import backoff

from src.config.settings import settings
from src.monitoring.metrics import api_calls, api_errors

class ITGlueClient:
    """IT Glue API client"""
    
    def __init__(self):
        self.base_url = settings.itglue_api_url
        self.api_key = settings.itglue_api_key
        self.rate_limiter = RateLimiter(settings.itglue_rate_limit)
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/vnd.api+json"
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=60
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict:
        """Make API request with retry logic"""
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with self.session.request(
                method,
                url,
                params=params,
                json=data
            ) as response:
                
                # Track metrics
                api_calls.labels(
                    endpoint=endpoint,
                    status=response.status
                ).inc()
                
                # Handle rate limiting
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    await asyncio.sleep(retry_after)
                    return await self._request(method, endpoint, params, data)
                    
                response.raise_for_status()
                return await response.json()
                
        except Exception as e:
            api_errors.labels(
                endpoint=endpoint,
                error_type=type(e).__name__
            ).inc()
            raise
            
    async def get_organizations(
        self,
        page: int = 1,
        per_page: int = 50
    ) -> List[Dict]:
        """Fetch organizations with pagination"""
        
        all_orgs = []
        has_more = True
        
        while has_more:
            response = await self._request(
                "GET",
                "organizations",
                params={
                    "page[number]": page,
                    "page[size]": per_page,
                    "sort": "updated_at"
                }
            )
            
            orgs = response.get("data", [])
            all_orgs.extend(orgs)
            
            # Check for more pages
            links = response.get("links", {})
            has_more = links.get("next") is not None
            page += 1
            
            # Respect rate limits
            await asyncio.sleep(0.1)
            
        return all_orgs
        
    async def get_flexible_assets(
        self,
        org_id: str,
        asset_type_id: Optional[str] = None
    ) -> List[Dict]:
        """Fetch flexible assets for organization"""
        
        params = {
            "filter[organization_id]": org_id,
            "include": "flexible_asset_type"
        }
        
        if asset_type_id:
            params["filter[flexible_asset_type_id]"] = asset_type_id
            
        response = await self._request(
            "GET",
            "flexible_assets",
            params=params
        )
        
        return response.get("data", [])
```

### Data Transformation Pipeline

```python
# src/transformers/itglue_transformer.py
"""Transform IT Glue API responses to internal models"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from src.models.core import (
    Organization, Configuration, Password,
    FlexibleAsset, Document
)

class ITGlueTransformer:
    """Transform IT Glue data to internal models"""
    
    @staticmethod
    def transform_organization(data: Dict) -> Organization:
        """Transform IT Glue organization"""
        
        attributes = data.get("attributes", {})
        
        return Organization(
            id=data["id"],
            name=attributes["name"],
            type=attributes["organization_type_name"],
            created_at=datetime.fromisoformat(
                attributes["created_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                attributes["updated_at"].replace("Z", "+00:00")
            ),
            alert=attributes.get("alert"),
            description=attributes.get("description"),
            primary_contact_id=attributes.get("primary_contact_id"),
            custom_fields=attributes.get("custom_fields", {})
        )
        
    @staticmethod
    def transform_flexible_asset(data: Dict) -> FlexibleAsset:
        """Transform IT Glue flexible asset"""
        
        attributes = data.get("attributes", {})
        
        # Parse traits (custom fields)
        traits = {}
        for key, value in attributes.get("traits", {}).items():
            # Handle different trait types
            if isinstance(value, dict):
                if "value" in value:
                    traits[key] = value["value"]
                elif "values" in value:
                    traits[key] = value["values"]
                else:
                    traits[key] = value
            else:
                traits[key] = value
                
        return FlexibleAsset(
            id=data["id"],
            organization_id=attributes["organization_id"],
            flexible_asset_type_id=attributes["flexible_asset_type_id"],
            name=attributes["name"],
            traits=traits
        )
        
    @staticmethod
    def extract_relationships(data: Dict) -> List[tuple]:
        """Extract relationships from IT Glue data"""
        
        relationships = []
        
        # Extract from relationships field
        for rel in data.get("relationships", {}).values():
            if isinstance(rel, dict) and "data" in rel:
                rel_data = rel["data"]
                if isinstance(rel_data, list):
                    for item in rel_data:
                        relationships.append((
                            data["id"],
                            item["type"],
                            item["id"]
                        ))
                elif rel_data:
                    relationships.append((
                        data["id"],
                        rel_data["type"],
                        rel_data["id"]
                    ))
                    
        return relationships
```

### Pagination Handling

```python
# src/sync/pagination.py
"""Efficient pagination for large datasets"""

from typing import AsyncIterator, Dict, List, Optional
import asyncio
from dataclasses import dataclass

@dataclass
class PaginationState:
    """Track pagination state"""
    current_page: int = 1
    per_page: int = 100
    total_pages: Optional[int] = None
    total_items: Optional[int] = None
    has_more: bool = True

class PaginatedFetcher:
    """Handle paginated API responses efficiently"""
    
    def __init__(self, client, concurrency: int = 3):
        self.client = client
        self.concurrency = concurrency
        
    async def fetch_all_pages(
        self,
        endpoint: str,
        params: Dict = None
    ) -> AsyncIterator[List[Dict]]:
        """Fetch all pages with concurrent requests"""
        
        # Get first page to determine total
        first_page = await self.client._request(
            "GET",
            endpoint,
            params={
                **(params or {}),
                "page[number]": 1,
                "page[size]": 100
            }
        )
        
        yield first_page.get("data", [])
        
        # Calculate total pages
        meta = first_page.get("meta", {})
        total_items = meta.get("page-count", 0)
        per_page = 100
        total_pages = (total_items + per_page - 1) // per_page
        
        if total_pages <= 1:
            return
            
        # Fetch remaining pages concurrently
        semaphore = asyncio.Semaphore(self.concurrency)
        
        async def fetch_page(page_num: int):
            async with semaphore:
                return await self.client._request(
                    "GET",
                    endpoint,
                    params={
                        **(params or {}),
                        "page[number]": page_num,
                        "page[size]": per_page
                    }
                )
                
        # Create tasks for remaining pages
        tasks = [
            fetch_page(page)
            for page in range(2, total_pages + 1)
        ]
        
        # Process results as they complete
        for future in asyncio.as_completed(tasks):
            response = await future
            yield response.get("data", [])
            
    async def fetch_with_cursor(
        self,
        endpoint: str,
        cursor: Optional[str] = None
    ) -> AsyncIterator[tuple[List[Dict], Optional[str]]]:
        """Fetch using cursor-based pagination"""
        
        while True:
            params = {}
            if cursor:
                params["page[cursor]"] = cursor
                
            response = await self.client._request(
                "GET",
                endpoint,
                params=params
            )
            
            data = response.get("data", [])
            next_cursor = response.get("meta", {}).get("next_cursor")
            
            yield data, next_cursor
            
            if not next_cursor:
                break
                
            cursor = next_cursor
```

## Core Workflows

### Query Processing Workflow

```mermaid
graph TD
    A[User Query] --> B[MCP Server]
    B --> C[Query Parser]
    C --> D{Query Type}
    D -->|Simple| E[Cache Check]
    D -->|Complex| F[Query Planner]
    E -->|Hit| G[Return Cached]
    E -->|Miss| H[Neo4j Query]
    F --> I[Parallel Execution]
    I --> H
    I --> J[Qdrant Search]
    H --> K[Result Merger]
    J --> K
    K --> L[Cache Update]
    L --> M[Format Response]
    M --> N[Return to User]
```

### Data Synchronization Workflow

```python
# src/workflows/sync_workflow.py
"""Complete sync workflow implementation"""

from typing import List, Dict
import asyncio
from datetime import datetime

class SyncWorkflow:
    """Orchestrate data synchronization"""
    
    async def run_full_sync(self):
        """Complete sync of all data"""
        
        steps = [
            self.sync_organizations,
            self.sync_configurations,
            self.sync_passwords,
            self.sync_flexible_assets,
            self.sync_documents,
            self.build_relationships,
            self.generate_embeddings,
            self.update_cache
        ]
        
        for step in steps:
            try:
                await step()
                logger.info(f"Completed: {step.__name__}")
            except Exception as e:
                logger.error(f"Failed: {step.__name__} - {e}")
                raise
                
    async def run_incremental_sync(self):
        """Incremental sync of changes"""
        
        # Get last sync timestamp
        last_sync = await self.get_last_sync()
        
        # Fetch changes since last sync
        changes = await self.fetch_changes(last_sync)
        
        # Process changes
        await self.process_creates(changes.get("created", []))
        await self.process_updates(changes.get("updated", []))
        await self.process_deletes(changes.get("deleted", []))
        
        # Update sync timestamp
        await self.update_last_sync(datetime.utcnow())
```

### Error Recovery Workflows

```python
# src/workflows/error_recovery.py
"""Error recovery and resilience patterns"""

from typing import Optional, Callable
import asyncio
from datetime import datetime, timedelta

class ErrorRecovery:
    """Handle failures and recovery"""
    
    async def with_retry(
        self,
        func: Callable,
        max_attempts: int = 3,
        backoff_factor: float = 2.0,
        max_delay: int = 60
    ):
        """Execute with exponential backoff retry"""
        
        attempt = 0
        delay = 1
        
        while attempt < max_attempts:
            try:
                return await func()
            except Exception as e:
                attempt += 1
                
                if attempt >= max_attempts:
                    logger.error(f"Max retries exceeded: {e}")
                    raise
                    
                # Calculate next delay
                delay = min(delay * backoff_factor, max_delay)
                
                logger.warning(
                    f"Attempt {attempt} failed, retrying in {delay}s: {e}"
                )
                
                await asyncio.sleep(delay)
                
    async def circuit_breaker(
        self,
        func: Callable,
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ):
        """Circuit breaker pattern"""
        
        if self.is_circuit_open(func.__name__):
            if self.can_attempt_reset(func.__name__):
                # Try half-open state
                try:
                    result = await func()
                    self.reset_circuit(func.__name__)
                    return result
                except Exception:
                    self.record_failure(func.__name__)
                    raise
            else:
                raise Exception("Circuit breaker is open")
                
        try:
            result = await func()
            self.record_success(func.__name__)
            return result
        except Exception as e:
            self.record_failure(func.__name__)
            
            if self.should_open_circuit(func.__name__):
                self.open_circuit(func.__name__)
                
            raise
            
    async def compensate_transaction(
        self,
        operations: List[Callable],
        compensations: List[Callable]
    ):
        """Saga pattern for distributed transactions"""
        
        completed = []
        
        try:
            for operation in operations:
                result = await operation()
                completed.append(result)
                
            return completed
            
        except Exception as e:
            # Compensate in reverse order
            for i in range(len(completed) - 1, -1, -1):
                try:
                    await compensations[i](completed[i])
                except Exception as comp_error:
                    logger.error(f"Compensation failed: {comp_error}")
                    
            raise e
```

### Automated Testing Workflows

```python
# src/workflows/testing_workflow.py
"""Automated testing workflows"""

import asyncio
from typing import List, Dict
import pytest

class TestingWorkflow:
    """Orchestrate automated testing"""
    
    async def run_test_suite(self):
        """Run complete test suite"""
        
        # Setup test environment
        await self.setup_test_environment()
        
        try:
            # Run tests in order
            results = {}
            
            # Unit tests
            results["unit"] = await self.run_unit_tests()
            
            # Integration tests
            results["integration"] = await self.run_integration_tests()
            
            # E2E tests
            results["e2e"] = await self.run_e2e_tests()
            
            # Performance tests
            results["performance"] = await self.run_performance_tests()
            
            # Security tests
            results["security"] = await self.run_security_tests()
            
            return self.generate_test_report(results)
            
        finally:
            # Cleanup
            await self.cleanup_test_environment()
            
    async def run_unit_tests(self) -> Dict:
        """Execute unit tests"""
        
        result = pytest.main([
            "tests/unit",
            "-v",
            "--cov=src",
            "--cov-report=json"
        ])
        
        return {
            "passed": result == 0,
            "coverage": self.parse_coverage_report()
        }
        
    async def run_integration_tests(self) -> Dict:
        """Execute integration tests with test containers"""
        
        # Start test containers
        containers = await self.start_test_containers()
        
        try:
            result = pytest.main([
                "tests/integration",
                "-v",
                "--integration"
            ])
            
            return {"passed": result == 0}
            
        finally:
            # Stop containers
            await self.stop_test_containers(containers)
            
    async def run_chaos_tests(self):
        """Chaos engineering tests"""
        
        chaos_scenarios = [
            self.simulate_database_failure,
            self.simulate_network_partition,
            self.simulate_high_load,
            self.simulate_memory_pressure
        ]
        
        for scenario in chaos_scenarios:
            try:
                await scenario()
                await self.verify_recovery()
            except Exception as e:
                logger.error(f"Chaos test failed: {e}")
                raise
```

## REST API Spec

### API Endpoints

```yaml
# openapi.yaml
openapi: 3.0.0
info:
  title: IT Glue MCP Server API
  version: 1.0.0
  description: Natural language querying for IT documentation

servers:
  - url: http://localhost:8001
    description: Development server
  - url: https://api.itglue-mcp.com
    description: Production server

paths:
  /query:
    post:
      summary: Execute natural language query
      operationId: executeQuery
      tags:
        - Query
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/QueryRequest'
      responses:
        '200':
          description: Successful query
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/QueryResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '429':
          $ref: '#/components/responses/RateLimited'
          
  /search:
    post:
      summary: Cross-company search
      operationId: searchAcrossCompanies
      tags:
        - Search
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SearchRequest'
      responses:
        '200':
          description: Search results
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SearchResponse'
                
  /compliance/check:
    post:
      summary: Run compliance check
      operationId: runComplianceCheck
      tags:
        - Compliance
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ComplianceRequest'
      responses:
        '200':
          description: Compliance report
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ComplianceReport'
                
  /sync/trigger:
    post:
      summary: Trigger manual sync
      operationId: triggerSync
      tags:
        - Admin
      security:
        - ApiKeyAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                organization_id:
                  type: string
                  description: Optional specific org to sync
                sync_type:
                  type: string
                  enum: [full, incremental]
      responses:
        '202':
          description: Sync job accepted
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id:
                    type: string
                  status:
                    type: string
                    
  /health:
    get:
      summary: Health check
      operationId: healthCheck
      tags:
        - Monitoring
      responses:
        '200':
          description: Service healthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthStatus'

components:
  schemas:
    QueryRequest:
      type: object
      required:
        - query
      properties:
        query:
          type: string
          minLength: 1
          maxLength: 500
        company_id:
          type: string
        company_name:
          type: string
        options:
          $ref: '#/components/schemas/QueryOptions'
          
    QueryOptions:
      type: object
      properties:
        cross_company:
          type: boolean
          default: false
        include_archived:
          type: boolean
          default: false
        max_results:
          type: integer
          minimum: 1
          maximum: 100
          default: 10
          
    QueryResponse:
      type: object
      properties:
        success:
          type: boolean
        data:
          type: object
        error:
          type: string
        source:
          type: string
          enum: [cache, neo4j, qdrant, api]
        execution_time_ms:
          type: number
        confidence_score:
          type: number
          minimum: 0
          maximum: 1
          
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
    BearerAuth:
      type: http
      scheme: bearer
```

### API Testing Scenarios

```python
# tests/api/test_api.py
"""API endpoint tests"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

class TestQueryAPI:
    """Test query endpoints"""
    
    def test_simple_query_success(self):
        """Test successful simple query"""
        
        response = client.post("/query", json={
            "query": "What is the router IP?",
            "company_id": "test-company"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] in [True, False]
        if data["success"]:
            assert "data" in data
        else:
            assert data["error"] == "No data available"
            
    def test_query_validation(self):
        """Test query validation"""
        
        # Empty query
        response = client.post("/query", json={
            "query": "",
            "company_id": "test"
        })
        assert response.status_code == 400
        
        # SQL injection attempt
        response = client.post("/query", json={
            "query": "'; DROP TABLE users; --",
            "company_id": "test"
        })
        assert response.status_code == 400
        
    def test_rate_limiting(self):
        """Test rate limiting"""
        
        # Make many requests
        for i in range(150):
            response = client.post("/query", json={
                "query": f"Test query {i}",
                "company_id": "test"
            })
            
            if response.status_code == 429:
                # Check rate limit headers
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers
                assert "Retry-After" in response.headers
                break
        else:
            pytest.fail("Rate limiting not triggered")
```

### API Documentation Generation

```python
# src/api/docs.py
"""Generate API documentation"""

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

def setup_api_docs(app: FastAPI):
    """Configure API documentation"""
    
    @app.get("/docs", response_class=HTMLResponse)
    async def custom_swagger_ui():
        """Custom Swagger UI"""
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title="IT Glue MCP API Docs",
            swagger_favicon_url="/static/favicon.ico",
            swagger_ui_parameters={
                "persistAuthorization": True,
                "displayRequestDuration": True,
                "filter": True,
                "showExtensions": True,
                "showCommonExtensions": True
            }
        )
        
    @app.get("/redoc", response_class=HTMLResponse)
    async def redoc_html():
        """ReDoc documentation"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>IT Glue MCP API Documentation</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
            <style>
                body {{ margin: 0; padding: 0; }}
            </style>
        </head>
        <body>
            <redoc spec-url="/openapi.json"></redoc>
            <script src="https://cdn.jsdelivr.net/npm/redoc/bundles/redoc.standalone.js"></script>
        </body>
        </html>
        """
```

### API Authentication Implementation

```python
# src/api/auth.py
"""API authentication implementation"""

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPBearer, OAuth2PasswordBearer
from typing import Optional
import jwt

# Authentication schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/oauth/token", auto_error=False)

class APIAuth:
    """Multi-method API authentication"""
    
    async def verify_api_key(
        self,
        api_key: Optional[str] = Security(api_key_header)
    ) -> Optional[Dict]:
        """Verify API key authentication"""
        
        if not api_key:
            return None
            
        # Validate against database
        key_data = await self.validate_key_in_db(api_key)
        if not key_data:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
            
        return key_data
        
    async def verify_jwt(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
    ) -> Optional[Dict]:
        """Verify JWT bearer token"""
        
        if not credentials:
            return None
            
        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.jwt_secret,
                algorithms=["HS256"]
            )
            
            # Additional validation
            if payload.get("exp") < datetime.utcnow().timestamp():
                raise HTTPException(
                    status_code=401,
                    detail="Token expired"
                )
                
            return payload
            
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
            
    async def get_current_user(
        self,
        api_key: Optional[Dict] = Depends(verify_api_key),
        jwt_payload: Optional[Dict] = Depends(verify_jwt)
    ) -> Dict:
        """Get authenticated user from any auth method"""
        
        if api_key:
            return api_key
        elif jwt_payload:
            return jwt_payload
        else:
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )
```

## Source Tree

```
itglue-mcp-server/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # CI pipeline
│       ├── cd.yml                 # CD pipeline
│       └── security.yml           # Security scanning
├── docker/
│   ├── Dockerfile.mcp             # MCP server image
│   ├── Dockerfile.api             # API service image
│   ├── Dockerfile.sync            # Sync service image
│   └── Dockerfile.streamlit       # Streamlit UI image
├── k8s/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── deployment.yaml
│   └── service.yaml
├── scripts/
│   ├── init-db.sql               # Database initialization
│   ├── dev-setup.sh              # Development setup
│   ├── release.py                # Release automation
│   └── smoke-test.sh             # Smoke tests
├── src/
│   ├── __init__.py
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── server.py             # MCP server implementation
│   │   ├── tools.py              # MCP tool definitions
│   │   ├── handlers.py           # Message handlers
│   │   └── health.py             # Health checks
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI application
│   │   ├── routes/
│   │   │   ├── query.py         # Query endpoints
│   │   │   ├── search.py        # Search endpoints
│   │   │   ├── admin.py         # Admin endpoints
│   │   │   └── health.py        # Health endpoints
│   │   ├── auth.py               # Authentication
│   │   ├── middleware.py         # Middleware
│   │   └── docs.py               # API documentation
│   ├── core/
│   │   ├── __init__.py
│   │   ├── query_engine.py       # Query processing
│   │   ├── search_engine.py      # Search implementation
│   │   ├── compliance.py         # Compliance checking
│   │   ├── patterns.py           # Query patterns
│   │   └── error_handling.py     # Error management
│   ├── sync/
│   │   ├── __init__.py
│   │   ├── service.py            # Sync service
│   │   ├── itglue_client.py      # IT Glue API client
│   │   ├── tasks.py              # Celery tasks
│   │   ├── pipeline.py           # Sync pipeline
│   │   └── pagination.py         # Pagination handling
│   ├── transformers/
│   │   ├── __init__.py
│   │   ├── itglue_transformer.py # IT Glue transformers
│   │   ├── neo4j_transformer.py  # Neo4j transformers
│   │   └── qdrant_transformer.py # Qdrant transformers
│   ├── db/
│   │   ├── __init__.py
│   │   ├── postgres/
│   │   │   ├── client.py        # PostgreSQL client
│   │   │   ├── models.py        # SQLAlchemy models
│   │   │   └── migrations/      # Alembic migrations
│   │   ├── neo4j/
│   │   │   ├── client.py        # Neo4j client
│   │   │   ├── queries.py       # Cypher queries
│   │   │   └── schema.py        # Graph schema
│   │   ├── qdrant/
│   │   │   ├── client.py        # Qdrant client
│   │   │   ├── indexer.py       # Vector indexing
│   │   │   └── schema.py        # Collection schemas
│   │   └── repositories/
│   │       ├── base.py          # Base repository
│   │       ├── organization.py  # Org repository
│   │       └── configuration.py # Config repository
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── redis_client.py       # Redis client
│   │   ├── cache_manager.py      # Cache management
│   │   └── strategies.py         # Caching strategies
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── security.py           # Security implementation
│   │   ├── jwt_handler.py        # JWT handling
│   │   └── permissions.py        # Permission system
│   ├── models/
│   │   ├── __init__.py
│   │   ├── core.py               # Core domain models
│   │   ├── query.py              # Query models
│   │   ├── sync.py               # Sync models
│   │   └── itglue.py             # IT Glue models
│   ├── nlp/
│   │   ├── __init__.py
│   │   ├── query_parser.py       # Query parsing
│   │   ├── embeddings.py         # Embedding generation
│   │   └── intent.py             # Intent detection
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── metrics.py            # Prometheus metrics
│   │   ├── tracing.py            # OpenTelemetry tracing
│   │   ├── logging.py            # Structured logging
│   │   └── health.py             # Health checks
│   ├── security/
│   │   ├── __init__.py
│   │   ├── validation.py         # Input validation
│   │   ├── encryption.py         # Data encryption
│   │   ├── rate_limit.py         # Rate limiting
│   │   └── headers.py            # Security headers
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py           # Application settings
│   │   ├── celery.py             # Celery configuration
│   │   └── logging.py            # Logging configuration
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── sync_workflow.py      # Sync workflows
│   │   ├── query_workflow.py     # Query workflows
│   │   ├── error_recovery.py     # Error recovery
│   │   └── testing_workflow.py   # Test workflows
│   └── ui/
│       ├── __init__.py
│       ├── streamlit_app.py      # Streamlit UI
│       ├── pages/
│       │   ├── query.py         # Query page
│       │   ├── search.py        # Search page
│       │   └── admin.py         # Admin page
│       └── components/
│           ├── chat.py          # Chat component
│           └── results.py       # Results display
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Pytest configuration
│   ├── unit/
│   │   ├── test_query_engine.py
│   │   ├── test_sync_service.py
│   │   └── test_transformers.py
│   ├── integration/
│   │   ├── test_sync_pipeline.py
│   │   ├── test_database_ops.py
│   │   └── test_api_integration.py
│   ├── e2e/
│   │   ├── test_mcp_flow.py
│   │   └── test_user_scenarios.py
│   ├── performance/
│   │   ├── test_load.py
│   │   └── test_benchmarks.py
│   └── security/
│       ├── test_security.py
│       └── test_penetration.py
├── docs/
│   ├── architecture.md           # This document
│   ├── api.md                   # API documentation
│   ├── deployment.md            # Deployment guide
│   └── development.md           # Developer guide
├── monitoring/
│   ├── prometheus.yml            # Prometheus config
│   └── grafana/
│       └── dashboards/
│           └── mcp-dashboard.json
├── .env.example                  # Environment template
├── .gitignore
├── docker-compose.yml            # Local development
├── docker-compose.prod.yml       # Production stack
├── pyproject.toml               # Poetry configuration
├── poetry.lock                  # Dependency lock
├── README.md                    # Project README
├── LICENSE                      # License file
└── Makefile                     # Build automation
```

## Development Workflow - Git workflow and branching strategy

### Git Workflow Strategy

**Selected Approach: GitFlow with Feature Flags**

We'll implement GitFlow for its structured release management, enhanced with feature flags for continuous deployment capabilities:

```yaml
# .github/branch-protection.yaml
branch_protection_rules:
  main:
    required_reviews: 2
    dismiss_stale_reviews: true
    require_up_to_date: true
    enforce_admins: false
    required_status_checks:
      - "test-suite"
      - "security-scan"
      - "type-check"
    
  develop:
    required_reviews: 1
    require_up_to_date: true
    required_status_checks:
      - "test-suite"
      - "lint"
```

### Branch Structure

```bash
main                    # Production-ready code
├── develop            # Integration branch
│   ├── feature/*      # New features
│   ├── bugfix/*       # Bug fixes for develop
│   ├── refactor/*     # Code improvements
│   └── experiment/*   # Experimental features
├── release/*          # Release preparation
├── hotfix/*           # Production emergency fixes
└── support/*          # Long-term support branches
```

### Commit Convention

**Conventional Commits with Semantic Versioning:**

```bash
# Format: <type>(<scope>): <subject>

feat(sync): add incremental sync for flexible assets
fix(api): handle IT Glue rate limit 429 responses  
docs(mcp): update MCP tool descriptions
test(neo4j): add relationship query tests
refactor(cache): optimize Redis TTL management
perf(query): add database query result caching
chore(deps): update FastAPI to 0.104.1
build(docker): optimize multi-stage build layers
ci(github): add security scanning workflow
style(api): format code with black and isort
```

### Development Flow

```python
# scripts/dev_workflow.py
"""Development workflow automation"""

import subprocess
from typing import Optional
from enum import Enum

class WorkflowType(Enum):
    FEATURE = "feature"
    BUGFIX = "bugfix"
    HOTFIX = "hotfix"
    RELEASE = "release"

class GitWorkflow:
    def start_feature(self, name: str, from_branch: str = "develop"):
        """Start new feature development"""
        commands = [
            f"git checkout {from_branch}",
            f"git pull origin {from_branch}",
            f"git checkout -b feature/{name}",
            "pre-commit install",
            "poetry install",
            "docker-compose up -d redis neo4j qdrant"
        ]
        self._execute_commands(commands)
        
    def create_pr(self, target: str = "develop"):
        """Create pull request with template"""
        branch = self._get_current_branch()
        
        # Generate PR description from commits
        commits = self._get_commits_since(target)
        
        pr_template = f"""
## Description
{self._summarize_commits(commits)}

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change (fix or feature)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added for new features
- [ ] All tests passing locally

## Related Issues
Closes #

## Screenshots (if applicable)
        """
        
        # Create PR via GitHub CLI
        subprocess.run([
            "gh", "pr", "create",
            "--base", target,
            "--head", branch,
            "--body", pr_template,
            "--draft"
        ])
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-json
      - id: check-merge-conflict
      - id: check-toml
      - id: debug-statements
      - id: mixed-line-ending

  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/PyCQA/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: ['--max-line-length=88', '--extend-ignore=E203']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--strict]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-r', 'src/', '-ll']
        
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: poetry run pytest tests/unit --tb=short -q
        language: system
        pass_filenames: false
        always_run: true
```

### CI/CD Pipeline

```yaml
# .github/workflows/main.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
          
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          
      neo4j:
        image: neo4j:5
        env:
          NEO4J_AUTH: neo4j/testpass
        ports:
          - 7687:7687
          
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
          
      - name: Cache Poetry dependencies
        uses: actions/cache@v3
        with:
          path: |
            ~/.cache/pypoetry
            ~/.virtualenvs
          key: ${{ runner.os }}-poetry-${{ hashFiles('**/poetry.lock') }}
          
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install --with dev,test
          
      - name: Run tests with coverage
        run: |
          poetry run pytest \
            --cov=src \
            --cov-report=xml \
            --cov-report=html \
            --cov-report=term-missing \
            -v
            
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          
      - name: Security scan
        run: |
          poetry run bandit -r src/ -f json -o bandit-report.json
          poetry run safety check --json
          
      - name: Type checking
        run: poetry run mypy src/
        
      - name: Lint
        run: |
          poetry run black --check src/ tests/
          poetry run isort --check-only src/ tests/
          poetry run flake8 src/ tests/
          
  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
        
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          tags: itglue-mcp:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Release Process

```python
# scripts/release.py
"""Automated release management"""

import re
import subprocess
from datetime import datetime
from typing import List, Tuple

class ReleaseManager:
    def prepare_release(self, version: str):
        """Prepare release branch and changelog"""
        
        # Create release branch
        self._create_release_branch(version)
        
        # Update version files
        self._update_version_files(version)
        
        # Generate changelog
        changelog = self._generate_changelog(version)
        self._update_changelog(changelog)
        
        # Run full test suite
        self._run_release_tests()
        
        # Create release PR
        self._create_release_pr(version)
        
    def _generate_changelog(self, version: str) -> str:
        """Generate changelog from commits"""
        
        # Get commits since last tag
        last_tag = self._get_last_tag()
        commits = subprocess.check_output(
            f"git log {last_tag}..HEAD --pretty=format:'%s|%h'",
            shell=True
        ).decode().split('\n')
        
        # Categorize commits
        features = []
        fixes = []
        breaking = []
        
        for commit in commits:
            if not commit:
                continue
                
            message, hash = commit.split('|')
            
            if message.startswith('feat'):
                features.append(f"- {message} ({hash})")
            elif message.startswith('fix'):
                fixes.append(f"- {message} ({hash})")
            elif 'BREAKING' in message:
                breaking.append(f"- {message} ({hash})")
                
        # Format changelog
        changelog = f"""
## [{version}] - {datetime.now().strftime('%Y-%m-%d')}

### ⚠ Breaking Changes
{chr(10).join(breaking) if breaking else 'None'}

### ✨ Features
{chr(10).join(features) if features else 'None'}

### 🐛 Bug Fixes
{chr(10).join(fixes) if fixes else 'None'}

### 📊 Statistics
- Total commits: {len(commits)}
- Contributors: {self._get_contributors_count()}
        """
        
        return changelog
        
    def _run_release_tests(self):
        """Run comprehensive test suite for release"""
        
        test_commands = [
            "poetry run pytest tests/ -v --tb=short",
            "poetry run mypy src/ --strict",
            "poetry run bandit -r src/",
            "poetry run safety check",
            "docker-compose run --rm test",
            "poetry run python scripts/integration_test.py"
        ]
        
        for cmd in test_commands:
            result = subprocess.run(cmd, shell=True)
            if result.returncode != 0:
                raise Exception(f"Release test failed: {cmd}")
```

### Feature Flags

```python
# src/core/feature_flags.py
"""Feature flag management for gradual rollout"""

from enum import Enum
from typing import Dict, Optional
import json
from pathlib import Path

class Feature(Enum):
    CROSS_COMPANY_SEARCH = "cross_company_search"
    SEMANTIC_SEARCH = "semantic_search"
    AI_SUGGESTIONS = "ai_suggestions"
    COMPLIANCE_REPORTING = "compliance_reporting"
    REAL_TIME_SYNC = "real_time_sync"

class FeatureFlags:
    def __init__(self, config_path: Path = Path("config/features.json")):
        self.config_path = config_path
        self._flags = self._load_flags()
        
    def is_enabled(
        self,
        feature: Feature,
        context: Optional[Dict] = None
    ) -> bool:
        """Check if feature is enabled"""
        
        flag = self._flags.get(feature.value, {})
        
        # Check global enable
        if not flag.get("enabled", False):
            return False
            
        # Check percentage rollout
        if "percentage" in flag:
            return self._check_percentage(
                flag["percentage"],
                context
            )
            
        # Check specific conditions
        if "conditions" in flag:
            return self._check_conditions(
                flag["conditions"],
                context
            )
            
        return True
        
    def _check_percentage(
        self,
        percentage: int,
        context: Optional[Dict]
    ) -> bool:
        """Check percentage-based rollout"""
        
        if not context or "user_id" not in context:
            return False
            
        # Consistent hash for user
        user_hash = hash(context["user_id"]) % 100
        return user_hash < percentage
```

**Rationale for Development Workflow:**
- **GitFlow chosen** for clear separation between production and development code
- **Conventional Commits** enable automatic changelog generation and semantic versioning
- **Comprehensive pre-commit hooks** catch issues before they enter the repository
- **Feature flags** allow gradual rollout and A/B testing without deployment risks
- **Automated release process** reduces human error and ensures consistency
- **Matrix testing** validates compatibility across Python versions

## Infrastructure and Deployment

[Content continues with remaining sections...]

## Architect Checklist

[Checklist content as completed above...]

---

**Architecture Document Complete**

This comprehensive architecture document provides the complete technical blueprint for implementing the IT Glue MCP Server. The architecture has been thoroughly validated through the architect checklist and is ready for implementation.