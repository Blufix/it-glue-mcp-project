# Triple Database Integration Guide

## Overview

This document describes the complete integration of PostgreSQL, Qdrant, and Neo4j to create a unified search system for IT Glue data. The system combines keyword search, semantic understanding, and graph relationships for comprehensive knowledge retrieval.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Database Fixes and Setup](#database-fixes-and-setup)
3. [Embedding Generation](#embedding-generation)
4. [Neo4j Graph Population](#neo4j-graph-population)
5. [Unified Search Implementation](#unified-search-implementation)
6. [Document Import System](#document-import-system)
7. [API Sync with Rate Limiting](#api-sync-with-rate-limiting)
8. [Testing and Verification](#testing-and-verification)
9. [Troubleshooting](#troubleshooting)

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   PostgreSQL    │     │     Qdrant      │     │     Neo4j       │
│                 │     │                 │     │                 │
│  Text Search    │     │ Vector Search   │     │ Graph Search    │
│  - Keywords     │     │ - Embeddings    │     │ - Relationships │
│  - Exact Match  │     │ - Semantic      │     │ - Impact        │
│                 │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                        │
         └───────────────────────┴────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   UnifiedHybridSearch   │
                    │                         │
                    │  Weighted Scoring:      │
                    │  - Keyword: 30%         │
                    │  - Semantic: 50%        │
                    │  - Graph: 20%           │
                    └─────────────────────────┘
```

## Database Fixes and Setup

### 1. PostgreSQL Schema Fix

**Problem**: The database had a `content` field but code expected `search_text`.

**Solution**: Added migration to rename field and create proper indexes.

```python
# Migration: 002_add_search_text.py
"""Add search_text field for full-text search."""

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add search_text column if it doesn't exist
    op.add_column('itglue_entities', 
        sa.Column('search_text', sa.Text(), nullable=True)
    )
    
    # Create index for search performance
    op.create_index(
        'idx_search_text',
        'itglue_entities',
        ['search_text'],
        postgresql_using='gin',
        postgresql_ops={'search_text': 'gin_trgm_ops'}
    )
    
    # Migrate existing content
    op.execute("""
        UPDATE itglue_entities 
        SET search_text = LOWER(
            COALESCE(name, '') || ' ' || 
            COALESCE(attributes::text, '')
        )
        WHERE search_text IS NULL
    """)
```

### 2. Database Repository Pattern

```python
# src/data/repositories/itglue_repository.py
class ITGlueRepository:
    """Repository for IT Glue entity operations."""
    
    async def search(
        self,
        query: str,
        organization_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 10
    ) -> List[ITGlueEntity]:
        """Search entities using full-text search."""
        
        stmt = select(ITGlueEntity).where(
            ITGlueEntity.search_text.ilike(f"%{query}%")
        )
        
        if organization_id:
            stmt = stmt.where(
                ITGlueEntity.organization_id == organization_id
            )
        
        if entity_type:
            stmt = stmt.where(
                ITGlueEntity.entity_type == entity_type
            )
        
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

## Embedding Generation

### 1. Ollama Integration with Nomic Model

**Key Discovery**: The nomic-embed-text model uses 768 dimensions, not 384.

```python
# generate_embeddings_nomic.py
import aiohttp
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_DIM = 768  # Correct dimension for nomic

async def generate_embedding_ollama(text: str) -> list[float]:
    """Generate embedding using Ollama's nomic model."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{settings.ollama_url}/api/embeddings",
            json={
                "model": EMBEDDING_MODEL,
                "prompt": text
            },
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data["embedding"]
            return None

async def create_qdrant_collection():
    """Create collection with correct dimensions."""
    client = QdrantClient(url=settings.qdrant_url)
    
    # Recreate collection with correct dimensions
    client.recreate_collection(
        collection_name="itglue_entities",
        vectors_config=VectorParams(
            size=EMBEDDING_DIM,  # 768 for nomic
            distance=Distance.COSINE
        )
    )

async def store_embeddings(entities: List[dict], embeddings: List[List[float]]):
    """Store embeddings in Qdrant."""
    client = QdrantClient(url=settings.qdrant_url)
    
    points = []
    for entity, embedding in zip(entities, embeddings):
        # Qdrant requires numeric IDs
        point_id = abs(hash(entity['itglue_id']) % (10**8))
        
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "entity_id": entity['id'],
                "itglue_id": entity['itglue_id'],
                "name": entity['name'],
                "entity_type": entity['entity_type'],
                "organization_id": entity['organization_id']
            }
        )
        points.append(point)
    
    # Batch upsert
    client.upsert(
        collection_name="itglue_entities",
        points=points
    )
```

### 2. Batch Processing for Efficiency

```python
async def generate_embeddings_batch(entities: List[dict]) -> List[List[float]]:
    """Generate embeddings for multiple entities efficiently."""
    embeddings = []
    
    async with aiohttp.ClientSession() as session:
        for entity in entities:
            # Build comprehensive text for embedding
            text = build_embedding_text(entity)
            embedding = await generate_embedding_ollama(text, session)
            
            if embedding:
                embeddings.append(embedding)
            
            # Small delay to avoid overwhelming Ollama
            await asyncio.sleep(0.1)
    
    return embeddings

def build_embedding_text(entity: dict) -> str:
    """Build text for embedding from entity data."""
    parts = [
        entity.get('name', ''),
        entity.get('search_text', ''),
        # Include key attributes for better semantic understanding
        entity.get('attributes', {}).get('description', ''),
        entity.get('attributes', {}).get('notes', '')
    ]
    
    return ' '.join(filter(None, parts))
```

## Neo4j Graph Population

### 1. Entity Categorization and Node Creation

```python
# populate_neo4j_graph.py
async def create_configuration_nodes(session, configurations):
    """Create configuration nodes with proper categorization."""
    
    for config in configurations:
        name_lower = config['name'].lower()
        
        # Determine node type based on name patterns
        if 'server' in name_lower or 'hyperv' in name_lower:
            node_type = 'Server'
        elif 'switch' in name_lower or 'aruba' in name_lower:
            node_type = 'Switch'
        elif 'firewall' in name_lower or 'sophos' in name_lower:
            node_type = 'Firewall'
        elif 'desktop' in name_lower or 'laptop' in name_lower:
            node_type = 'Workstation'
        else:
            node_type = 'Device'
        
        # Create node with multiple labels
        query = f"""
            MERGE (c:Configuration:{node_type} {{itglue_id: $itglue_id}})
            SET c.name = $name,
                c.hostname = $hostname,
                c.primary_ip = $primary_ip,
                c.archived = $archived
            RETURN c
        """
        
        await session.run(query, 
            itglue_id=config['itglue_id'],
            name=config['name'],
            hostname=config['attributes'].get('hostname'),
            primary_ip=config['attributes'].get('primary_ip'),
            archived=config['attributes'].get('archived', False)
        )
```

### 2. Intelligent Relationship Creation

```python
async def create_infrastructure_relationships(session, servers, switches, firewalls):
    """Create meaningful infrastructure relationships."""
    
    # Connect servers to switches
    for server in servers:
        if switches:
            # In production, use IP ranges or VLANs to determine connections
            query = """
                MATCH (s:Server {itglue_id: $server_id})
                MATCH (sw:Switch {itglue_id: $switch_id})
                MERGE (s)-[:CONNECTS_TO]->(sw)
            """
            await session.run(query,
                server_id=server['itglue_id'],
                switch_id=switches[0]['itglue_id']
            )
    
    # Connect switches to firewalls
    for switch in switches:
        for firewall in firewalls:
            if 'sophos' in firewall['name'].lower():
                query = """
                    MATCH (sw:Switch {itglue_id: $switch_id})
                    MATCH (fw:Firewall {itglue_id: $firewall_id})
                    MERGE (sw)-[:ROUTES_THROUGH]->(fw)
                """
                await session.run(query,
                    switch_id=switch['itglue_id'],
                    firewall_id=firewall['itglue_id']
                )
                break

async def create_service_dependencies(session):
    """Create service-level dependencies."""
    
    dependencies = [
        # SQL depends on domain controller
        """
        MATCH (sql:Server) WHERE sql.name CONTAINS 'SQL'
        MATCH (dc:Server) WHERE dc.name CONTAINS 'DC'
        MERGE (sql)-[:DEPENDS_ON {service: 'Authentication'}]->(dc)
        """,
        
        # VMs hosted on hypervisor
        """
        MATCH (hyperv:Server) WHERE hyperv.name CONTAINS 'HYPERV'
        MATCH (vm:Server) WHERE vm.name =~ '.*VM.*'
        MERGE (vm)-[:HOSTED_ON]->(hyperv)
        """
    ]
    
    for query in dependencies:
        try:
            await session.run(query)
        except Exception as e:
            logger.debug(f"Dependency might not apply: {e}")
```

## Unified Search Implementation

### 1. UnifiedHybridSearch Class

```python
# src/search/unified_hybrid.py
class UnifiedHybridSearch:
    """Unified search across PostgreSQL, Qdrant, and Neo4j."""
    
    def __init__(
        self,
        keyword_weight: float = 0.3,
        semantic_weight: float = 0.5,
        graph_weight: float = 0.2
    ):
        """Initialize with configurable weights."""
        # Normalize weights to sum to 1.0
        total = keyword_weight + semantic_weight + graph_weight
        self.keyword_weight = keyword_weight / total
        self.semantic_weight = semantic_weight / total
        self.graph_weight = graph_weight / total
        
        self.qdrant_client = None
        self.neo4j_driver = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize all database connections."""
        if self._initialized:
            return
        
        # PostgreSQL through db_manager
        await db_manager.initialize()
        
        # Qdrant
        self.qdrant_client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key
        )
        
        # Neo4j
        self.neo4j_driver = AsyncGraphDatabase.driver(
            "bolt://localhost:7688",
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        
        self._initialized = True
```

### 2. Multi-Source Search Integration

```python
async def _hybrid_search(
    self,
    query: str,
    organization_id: Optional[str],
    entity_type: Optional[str],
    limit: int,
    min_score: float
) -> list[UnifiedSearchResult]:
    """Combine results from all three systems."""
    
    # Run searches in parallel for efficiency
    keyword_task = self._get_keyword_results(query, organization_id, entity_type, limit * 2)
    semantic_task = self._get_semantic_results(query, organization_id, entity_type, limit * 2)
    graph_task = self._get_graph_results(query, organization_id, limit * 2)
    
    keyword_results, semantic_results, graph_results = await asyncio.gather(
        keyword_task, semantic_task, graph_task
    )
    
    # Combine and score results
    combined = {}
    
    # Process keyword results
    for entity_id, score, data in keyword_results:
        combined[entity_id] = UnifiedSearchResult(
            id=entity_id,
            entity_id=entity_id,
            name=data.get("name", ""),
            entity_type=data.get("entity_type", ""),
            total_score=score * self.keyword_weight,
            keyword_score=score,
            sources=["keyword"],
            payload=data
        )
    
    # Merge semantic results
    for entity_id, score, data in semantic_results:
        if entity_id in combined:
            result = combined[entity_id]
            result.semantic_score = score
            result.total_score += score * self.semantic_weight
            result.sources.append("semantic")
        else:
            combined[entity_id] = UnifiedSearchResult(
                id=entity_id,
                entity_id=entity_id,
                name=data.get("name", ""),
                total_score=score * self.semantic_weight,
                semantic_score=score,
                sources=["semantic"],
                payload=data
            )
    
    # Merge graph results
    for entity_id, score, relationships in graph_results:
        if entity_id in combined:
            result = combined[entity_id]
            result.graph_score = score
            result.total_score += score * self.graph_weight
            result.sources.append("graph")
            result.relationships = relationships
        else:
            # Fetch entity details for graph-only results
            entity_data = await self._fetch_entity_details(entity_id)
            if entity_data:
                combined[entity_id] = UnifiedSearchResult(
                    id=entity_id,
                    entity_id=entity_id,
                    name=entity_data.get("name", ""),
                    total_score=score * self.graph_weight,
                    graph_score=score,
                    sources=["graph"],
                    relationships=relationships,
                    payload=entity_data
                )
    
    # Filter and sort
    results = [r for r in combined.values() if r.total_score >= min_score]
    results.sort(key=lambda x: x.total_score, reverse=True)
    
    return results[:limit]
```

### 3. Graph Query Integration

```python
async def _get_graph_results(
    self,
    query: str,
    organization_id: Optional[str],
    limit: int
) -> list[tuple[str, float, list]]:
    """Get graph-based results from Neo4j."""
    
    async with self.neo4j_driver.session() as session:
        # Note: Fixed parameter name conflict - use 'search_query' instead of 'query'
        cypher_query = """
            MATCH (n)
            WHERE toLower(n.name) CONTAINS toLower($search_query)
            
            // Find related nodes for context
            OPTIONAL MATCH (n)-[r]-(related)
            
            WITH n, collect(DISTINCT {
                type: type(r),
                direction: CASE 
                    WHEN startNode(r) = n THEN 'outgoing' 
                    ELSE 'incoming' 
                END,
                related_id: related.itglue_id,
                related_name: related.name
            }) as relationships
            
            RETURN 
                n.itglue_id as entity_id,
                n.name as name,
                labels(n) as labels,
                size(relationships) as relationship_count,
                relationships
            ORDER BY relationship_count DESC
            LIMIT $limit
        """
        
        result = await session.run(
            cypher_query,
            search_query=query,  # Fixed parameter name
            limit=limit
        )
        
        graph_results = []
        async for record in result:
            # Score based on relationship count
            score = min(1.0, record["relationship_count"] / 10)
            
            graph_results.append((
                record["entity_id"],
                score,
                record["relationships"]
            ))
        
        return graph_results
```

## Document Import System

### 1. Markdown Document Import

```python
# import_markdown_documents.py
import hashlib
from datetime import datetime

async def import_markdown_documents():
    """Import markdown documents with proper structure."""
    
    documents = [
        {
            "name": "IT Infrastructure Documentation",
            "content": "# IT Infrastructure...",
            "tags": ["infrastructure", "network", "documentation"]
        },
        # ... more documents
    ]
    
    async with db_manager.get_session() as session:
        for doc_data in documents:
            # Generate unique ID from content hash
            content_hash = hashlib.md5(
                doc_data['content'].encode()
            ).hexdigest()
            doc_id = f"doc_{content_hash[:16]}"
            
            # Build comprehensive search text
            search_text = f"{doc_data['name']} {doc_data['content']}".lower()
            
            # Create structured attributes
            attributes = {
                "name": doc_data['name'],
                "content": doc_data['content'],
                "content-type": "text/markdown",
                "tags": doc_data.get('tags', []),
                "word_count": len(doc_data['content'].split()),
                "character_count": len(doc_data['content']),
                "created-at": datetime.utcnow().isoformat()
            }
            
            # Create entity
            entity = ITGlueEntity(
                itglue_id=doc_id,
                entity_type='document',
                organization_id=org_id,
                name=doc_data['name'],
                attributes=attributes,
                search_text=search_text,
                last_synced=datetime.utcnow()
            )
            
            # Check if exists and update or create
            existing = await session.get(ITGlueEntity, doc_id)
            if existing:
                for key, value in entity.__dict__.items():
                    if not key.startswith('_'):
                        setattr(existing, key, value)
            else:
                session.add(entity)
        
        await session.commit()
```

### 2. Document Embedding Generation

```python
async def generate_document_embeddings():
    """Generate embeddings specifically for documents."""
    
    # Fetch documents
    async with db_manager.get_session() as session:
        result = await session.execute(text("""
            SELECT id, itglue_id, name, search_text, attributes
            FROM itglue_entities
            WHERE entity_type = 'document'
            AND organization_id = :org_id
        """), {"org_id": org_id})
        
        documents = result.fetchall()
    
    # Generate embeddings
    async with aiohttp.ClientSession() as session:
        for doc in documents:
            # Use full search_text for comprehensive embedding
            embedding = await generate_embedding_ollama(
                doc.search_text, 
                session
            )
            
            if embedding:
                # Store in Qdrant with document metadata
                point_id = abs(hash(doc.itglue_id) % (10**8))
                
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "entity_id": str(doc.id),
                        "itglue_id": doc.itglue_id,
                        "name": doc.name,
                        "entity_type": "document",
                        "tags": doc.attributes.get('tags', []),
                        "word_count": doc.attributes.get('word_count', 0)
                    }
                )
                
                client.upsert(
                    collection_name="itglue_entities",
                    points=[point]
                )
```

## API Sync with Rate Limiting

### 1. Rate Limiter Implementation

```python
# src/sync/itglue_sync.py
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class RateLimiter:
    """Rate limiter for IT Glue API compliance."""
    
    max_requests_per_minute: int = 100
    max_requests_per_10_seconds: int = 10
    request_times: List[datetime] = None
    
    def __post_init__(self):
        self.request_times = []
    
    async def wait_if_needed(self):
        """Wait if rate limits would be exceeded."""
        now = datetime.now()
        
        # Clean old requests
        self.request_times = [
            t for t in self.request_times 
            if now - t < timedelta(minutes=1)
        ]
        
        # Check 10-second window
        recent_10s = [
            t for t in self.request_times 
            if now - t < timedelta(seconds=10)
        ]
        
        if len(recent_10s) >= self.max_requests_per_10_seconds:
            wait_time = 10 - (now - recent_10s[0]).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        
        # Check 1-minute window
        if len(self.request_times) >= self.max_requests_per_minute:
            wait_time = 60 - (now - self.request_times[0]).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        
        # Record this request
        self.request_times.append(now)
```

### 2. API Client with Rate Limiting

```python
class ITGlueAPIClient:
    """IT Glue API client with automatic rate limiting."""
    
    def __init__(self):
        self.base_url = settings.itglue_api_url
        self.api_key = settings.itglue_api_key
        self.rate_limiter = RateLimiter(
            max_requests_per_minute=settings.itglue_rate_limit
        )
    
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make rate-limited GET request."""
        await self.rate_limiter.wait_if_needed()
        
        url = f"{self.base_url}/{endpoint}"
        
        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()
    
    async def get_paginated(
        self, 
        endpoint: str, 
        params: Optional[Dict] = None,
        max_pages: Optional[int] = None
    ) -> List[Dict]:
        """Get all pages with automatic rate limiting."""
        if params is None:
            params = {}
        
        params['page[size]'] = 50  # IT Glue max
        params['page[number]'] = 1
        
        all_data = []
        
        while True:
            logger.info(f"Fetching page {params['page[number]']}")
            
            response = await self.get(endpoint, params)
            data = response.get('data', [])
            all_data.extend(data)
            
            # Check for more pages
            if not response.get('links', {}).get('next'):
                break
            
            params['page[number]'] += 1
            
            if max_pages and params['page[number]'] > max_pages:
                break
        
        return all_data
```

## Testing and Verification

### 1. Integration Status Check

```python
# check_full_integration.py
async def check_integration():
    """Verify all three systems are working."""
    
    print("1️⃣ POSTGRESQL")
    async with db_manager.get_session() as session:
        result = await session.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT organization_id) as orgs,
                   COUNT(DISTINCT entity_type) as types
            FROM itglue_entities
        """))
        stats = result.first()
        print(f"✅ Entities: {stats.total}")
    
    print("\n2️⃣ QDRANT")
    client = QdrantClient(url=settings.qdrant_url)
    collection_info = client.get_collection("itglue_entities")
    print(f"✅ Vectors: {collection_info.points_count}")
    print(f"   Dimensions: {collection_info.config.params.vectors.size}")
    
    print("\n3️⃣ NEO4J")
    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7688",
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    async with driver.session() as session:
        result = await session.run("""
            MATCH (n) WITH COUNT(n) as nodes
            MATCH ()-[r]->() WITH nodes, COUNT(r) as rels
            RETURN nodes, rels
        """)
        record = await result.single()
        print(f"✅ Nodes: {record['nodes']}")
        print(f"   Relationships: {record['rels']}")
```

### 2. Search Testing

```python
# test_unified_search.py
async def test_unified_search():
    """Test all search modes."""
    
    search = UnifiedHybridSearch()
    await search.initialize()
    
    test_queries = [
        ("disaster recovery", SearchMode.KEYWORD),
        ("How to handle failures", SearchMode.SEMANTIC),
        ("network", SearchMode.GRAPH),
        ("security", SearchMode.HYBRID)
    ]
    
    for query, mode in test_queries:
        results = await search.search(
            query=query,
            mode=mode,
            limit=3
        )
        
        print(f"\nQuery: '{query}' ({mode.value})")
        for result in results:
            print(f"  - {result.name}: {result.total_score:.3f}")
            print(f"    Sources: {', '.join(result.sources)}")
```

## Troubleshooting

### Common Issues and Solutions

1. **Qdrant Dimension Mismatch**
   - Error: "Vector dimension mismatch"
   - Solution: Recreate collection with correct dimensions (768 for nomic)

2. **Neo4j Query Parameter Conflicts**
   - Error: "Multiple values for argument 'query'"
   - Solution: Use different parameter names (e.g., 'search_query')

3. **PostgreSQL Missing search_text**
   - Error: "Column search_text does not exist"
   - Solution: Run migration to add field and populate from existing data

4. **Rate Limiting Issues**
   - Error: "429 Too Many Requests"
   - Solution: Implement RateLimiter with proper wait logic

5. **Embedding Generation Failures**
   - Error: "Ollama connection refused"
   - Solution: Ensure Ollama is running on port 11434

## Performance Optimizations

1. **Batch Processing**: Process entities in batches for embeddings
2. **Connection Pooling**: Reuse database connections
3. **Async Operations**: Use asyncio for parallel processing
4. **Caching**: Cache frequently accessed data (Redis integration pending)
5. **Index Optimization**: Create proper indexes on search fields

## Next Steps

1. **Redis Integration**: Add caching layer for frequent queries
2. **Real-time Sync**: Implement webhooks for live updates
3. **Query Optimization**: Fine-tune search weights based on usage
4. **Monitoring**: Add metrics collection and alerting
5. **UI Integration**: Connect to MCP server interface