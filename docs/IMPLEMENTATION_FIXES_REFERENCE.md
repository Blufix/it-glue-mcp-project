# Implementation Fixes Quick Reference

## Key Fixes and Code Examples

### 1. Database Field Mismatch Fix

**Problem**: Code expected `search_text` but database had `content` field.

**Fix Applied**:
```python
# Fixed in: src/data/repositories/itglue_repository.py
# Changed from:
stmt = select(ITGlueEntity).where(
    ITGlueEntity.content.ilike(f"%{query}%")  # Wrong field
)

# To:
stmt = select(ITGlueEntity).where(
    ITGlueEntity.search_text.ilike(f"%{query}%")  # Correct field
)
```

**Database Update**:
```sql
-- Add search_text column and populate from existing data
ALTER TABLE itglue_entities ADD COLUMN search_text TEXT;

UPDATE itglue_entities 
SET search_text = LOWER(
    COALESCE(name, '') || ' ' || 
    COALESCE(attributes::text, '')
);

CREATE INDEX idx_search_text ON itglue_entities USING gin(search_text);
```

### 2. Qdrant Embedding Dimension Fix

**Problem**: Collection created with 384 dimensions but nomic uses 768.

**Fix Applied**:
```python
# Fixed in: generate_embeddings_nomic.py
# Wrong:
EMBEDDING_DIM = 384  # Incorrect for nomic

# Correct:
EMBEDDING_DIM = 768  # Correct dimension for nomic-embed-text

# Recreate collection with correct dimensions
client.recreate_collection(
    collection_name="itglue_entities",
    vectors_config=VectorParams(
        size=768,  # Must match nomic output
        distance=Distance.COSINE
    )
)
```

### 3. Qdrant ID Format Fix

**Problem**: Qdrant requires numeric IDs, not strings.

**Fix Applied**:
```python
# Fixed in: generate_document_embeddings.py
# Wrong:
point = PointStruct(
    id=doc['itglue_id'],  # String ID fails
    vector=embedding,
    payload={...}
)

# Correct:
point_id = abs(hash(doc['itglue_id']) % (10**8))  # Convert to numeric
point = PointStruct(
    id=point_id,  # Numeric ID works
    vector=embedding,
    payload={
        "itglue_id": doc['itglue_id'],  # Store original in payload
        ...
    }
)
```

### 4. Neo4j Query Parameter Name Conflict

**Problem**: Using 'query' as parameter name conflicts with session.run().

**Fix Applied**:
```python
# Fixed in: src/search/unified_hybrid.py
# Wrong:
cypher_query = """
    MATCH (n) WHERE n.name CONTAINS $query
"""
result = await session.run(cypher_query, query=query)  # Conflict!

# Correct:
cypher_query = """
    MATCH (n) WHERE n.name CONTAINS $search_query
"""
result = await session.run(cypher_query, search_query=query)  # No conflict
```

### 5. Repository Create/Update Method

**Problem**: ITGlueRepository missing create_or_update method.

**Fix Applied**:
```python
# Fixed in: import_markdown_documents.py
# Wrong:
await uow.itglue.create_or_update(entity)  # Method doesn't exist

# Correct:
existing = await uow.itglue.get_by_itglue_id(doc_id)
if existing:
    for key, value in entity.__dict__.items():
        if not key.startswith('_'):
            setattr(existing, key, value)
else:
    session.add(entity)
await session.commit()
```

### 6. Unified Search Weight Normalization

**Problem**: Search weights didn't sum to 1.0.

**Fix Applied**:
```python
# Fixed in: src/search/unified_hybrid.py
def __init__(self, keyword_weight=0.3, semantic_weight=0.5, graph_weight=0.2):
    # Normalize weights to sum to 1.0
    total = keyword_weight + semantic_weight + graph_weight
    self.keyword_weight = keyword_weight / total
    self.semantic_weight = semantic_weight / total
    self.graph_weight = graph_weight / total
```

### 7. Rate Limiter Implementation

**Problem**: IT Glue API has strict rate limits (100/minute).

**Fix Applied**:
```python
# Implemented in: src/sync/itglue_sync.py
class RateLimiter:
    def __init__(self):
        self.max_requests_per_minute = 100
        self.max_requests_per_10_seconds = 10
        self.request_times = []
    
    async def wait_if_needed(self):
        now = datetime.now()
        
        # Check 10-second window
        recent_10s = [t for t in self.request_times 
                      if now - t < timedelta(seconds=10)]
        
        if len(recent_10s) >= self.max_requests_per_10_seconds:
            wait_time = 10 - (now - recent_10s[0]).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.request_times.append(now)
```

### 8. Document Import with Hash IDs

**Problem**: Need unique IDs for imported documents.

**Fix Applied**:
```python
# Implemented in: import_markdown_documents.py
import hashlib

# Generate unique ID from content
content_hash = hashlib.md5(doc_data['content'].encode()).hexdigest()
doc_id = f"doc_{content_hash[:16]}"

# This ensures same content always gets same ID (idempotent)
```

### 9. Async Context Manager for API Client

**Problem**: Need proper session management for API calls.

**Fix Applied**:
```python
# Implemented in: src/sync/itglue_sync.py
class ITGlueAPIClient:
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/vnd.api+json"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

# Usage:
async with ITGlueAPIClient() as client:
    data = await client.get('organizations')
```

### 10. Search Result Merging

**Problem**: Need to combine results from three different sources.

**Fix Applied**:
```python
# Implemented in: src/search/unified_hybrid.py
combined = {}

# Add/merge results from each source
for entity_id, score, data in keyword_results:
    combined[entity_id] = UnifiedSearchResult(
        total_score=score * self.keyword_weight,
        keyword_score=score,
        sources=["keyword"]
    )

for entity_id, score, data in semantic_results:
    if entity_id in combined:
        # Update existing result
        result = combined[entity_id]
        result.semantic_score = score
        result.total_score += score * self.semantic_weight
        result.sources.append("semantic")
    else:
        # Create new result
        combined[entity_id] = UnifiedSearchResult(
            total_score=score * self.semantic_weight,
            semantic_score=score,
            sources=["semantic"]
        )
```

## Testing Commands

### Quick Test Commands

```bash
# Check database status
python check_full_integration.py

# Test unified search
python test_unified_search.py

# Import documents
python import_markdown_documents.py

# Generate embeddings
python generate_document_embeddings.py

# Populate Neo4j
python populate_neo4j_graph.py

# Test document search
python test_document_search.py

# Run safe sync
python test_safe_sync.py

# Sync with rate limiting (test mode)
python run_full_sync.py --test
```

### Database Verification Queries

```sql
-- PostgreSQL: Check entities
SELECT entity_type, COUNT(*) 
FROM itglue_entities 
GROUP BY entity_type;

-- PostgreSQL: Check search_text
SELECT name, LENGTH(search_text) as search_len 
FROM itglue_entities 
WHERE entity_type = 'document';
```

```python
# Qdrant: Check embeddings
from qdrant_client import QdrantClient
client = QdrantClient(url="http://localhost:6333")
info = client.get_collection("itglue_entities")
print(f"Vectors: {info.points_count}, Dimensions: {info.config.params.vectors.size}")
```

```cypher
-- Neo4j: Check graph
MATCH (n) RETURN labels(n), COUNT(n) as count;
MATCH ()-[r]->() RETURN type(r), COUNT(r) as count;
```

## Environment Variables

Required in `.env`:
```bash
# IT Glue
ITGLUE_API_KEY=your_api_key
ITGLUE_API_URL=https://api.eu.itglue.com
ITGLUE_RATE_LIMIT=100

# Databases
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5434/itglue
NEO4J_URI=bolt://localhost:7688
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
QDRANT_URL=http://localhost:6333

# Ollama
OLLAMA_URL=http://localhost:11434
```

## Docker Services

Ensure these are running:
```bash
# Check services
docker ps | grep -E "postgres|neo4j|qdrant|ollama"

# Start if needed
docker-compose up -d postgres neo4j qdrant
ollama serve  # For embeddings
```

## Common Error Messages and Solutions

| Error | Solution |
|-------|----------|
| `Column search_text does not exist` | Run database migration or UPDATE query |
| `Vector dimension mismatch` | Recreate Qdrant collection with 768 dimensions |
| `Multiple values for argument 'query'` | Use different parameter name in Cypher query |
| `429 Too Many Requests` | Implement rate limiting |
| `AttributeError: 'ITGlueRepository' object has no attribute 'create_or_update'` | Use manual check and update logic |
| `Ollama connection refused` | Start Ollama with `ollama serve` |
| `Neo4j connection refused on 7687` | Use port 7688 for bolt protocol |

## Performance Tips

1. **Batch Operations**: Process entities in batches of 50-100
2. **Connection Pooling**: Reuse database connections
3. **Async Everything**: Use asyncio.gather() for parallel operations
4. **Index Properly**: Ensure indexes on search_text, itglue_id
5. **Cache Embeddings**: Store embedding_id in PostgreSQL to avoid regeneration