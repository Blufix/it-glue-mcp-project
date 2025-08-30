# Architecture Decision Records (ADRs)

## Overview

This document captures key architectural decisions made for the IT Glue MCP Server project. Each decision includes context, alternatives considered, and rationale for the chosen approach.

## ADR-001: Modular Monolith Architecture

**Status**: Accepted  
**Date**: 2025-08-29  
**Decision Makers**: Architecture Team

### Context
We need to choose between microservices, monolith, or modular monolith architecture for the MVP.

### Decision
We will use a **Modular Monolith** architecture pattern.

### Rationale
- **Simplicity**: Single deployment unit reduces operational complexity for MVP
- **Performance**: No network overhead between modules
- **Future-proof**: Can extract modules to microservices later if needed
- **Cost-effective**: Single container/process reduces infrastructure costs

### Consequences
- ✅ Faster development and deployment
- ✅ Easier debugging and testing
- ✅ Lower operational overhead
- ⚠️ Must maintain clear module boundaries
- ❌ Scaling requires scaling entire application

---

## ADR-002: Database Strategy - Polyglot Persistence

**Status**: Accepted  
**Date**: 2025-08-29  
**Decision Makers**: Architecture Team

### Context
IT Glue data has various characteristics requiring different storage optimizations.

### Decision
Use **Polyglot Persistence** with specialized databases:
- **PostgreSQL** (via Supabase): Structured data, audit logs
- **Qdrant**: Vector embeddings for semantic search
- **Neo4j**: Relationship graphs (optional, for Phase 2)
- **Redis**: Caching layer

### Rationale
- Each database optimized for specific data patterns
- PostgreSQL provides ACID compliance for critical data
- Qdrant optimized for vector similarity search
- Redis provides sub-millisecond caching

### Consequences
- ✅ Optimal performance for each data type
- ✅ Can scale each database independently
- ⚠️ Increased operational complexity
- ⚠️ Need to maintain data consistency across stores

---

## ADR-003: Zero-Hallucination Strategy

**Status**: Accepted  
**Date**: 2025-08-29  
**Decision Makers**: Product & Architecture Team

### Context
IT documentation must be 100% accurate - no fabricated information is acceptable.

### Decision
Implement **Strict Source Validation** for all responses:
1. Every response must cite source documents
2. Validation service checks all claims against source data
3. Return "No data available" rather than guess
4. Maintain audit trail of sources

### Rationale
- Trust is critical for IT operations
- Incorrect information could cause outages
- Legal/compliance requirements for accuracy

### Implementation
```python
class ValidationService:
    def validate_response(self, response: str, sources: List[Document]) -> bool:
        # Check every claim in response exists in sources
        # Return False if any unverifiable claim found
```

### Consequences
- ✅ 100% accuracy guarantee
- ✅ Full auditability
- ✅ Builds user trust
- ⚠️ May return "no data" more often
- ❌ Cannot provide "helpful guesses"

---

## ADR-004: MCP Protocol Implementation

**Status**: Accepted  
**Date**: 2025-08-29  
**Decision Makers**: Technical Team

### Context
Need to choose how to implement MCP (Model Context Protocol) server.

### Decision
Implement **Native Python MCP Server** using the official SDK.

### Rationale
- Official SDK ensures protocol compliance
- Python aligns with rest of codebase
- Supports both stdio and SSE transports
- Active community support

### Implementation
- Use `mcp` Python package
- Implement tools: `query_company`, `list_companies`, `get_asset`, `search_fixes`
- Support JSON-RPC over stdio for Claude Desktop
- Add SSE support for web clients

### Consequences
- ✅ First-class Claude integration
- ✅ Standardized protocol
- ✅ Future-proof as MCP evolves
- ⚠️ Limited to MCP-compatible clients

---

## ADR-005: Embedding Strategy

**Status**: Accepted  
**Date**: 2025-08-29  
**Decision Makers**: ML Team

### Context
Need embeddings for semantic search capability.

### Decision
**Hybrid Embedding Strategy**:
1. Primary: Ollama with `all-MiniLM-L6-v2` (local)
2. Fallback: OpenAI `text-embedding-ada-002` (cloud)

### Rationale
- Local embeddings reduce cost and latency
- Cloud fallback ensures availability
- Model size (384 dimensions) balances quality and performance

### Implementation
```python
async def generate_embedding(text: str) -> List[float]:
    try:
        return await ollama_client.embed(text)
    except OllamaUnavailable:
        return await openai_client.embed(text)
```

### Consequences
- ✅ Cost-effective for high volume
- ✅ Low latency with local inference
- ✅ Fallback ensures reliability
- ⚠️ Need GPU for optimal local performance
- ⚠️ Must handle dimension mismatch if models differ

---

## ADR-006: Caching Strategy

**Status**: Accepted  
**Date**: 2025-08-30  
**Decision Makers**: Performance Team

### Context
IT Glue API has rate limits; repeated queries should be fast.

### Decision
**Multi-level Caching**:
1. Redis for query results (5-minute TTL)
2. Application-level LRU cache for embeddings
3. PostgreSQL materialized views for aggregations

### Rationale
- Redis provides distributed caching
- LRU cache reduces embedding regeneration
- Materialized views optimize complex queries

### Cache Keys
```python
# Query cache key includes org_id for isolation
cache_key = f"query:{org_id}:{hash(query_text)}"
```

### Consequences
- ✅ Sub-second response for cached queries
- ✅ Reduced API calls to IT Glue
- ✅ Lower embedding computation
- ⚠️ Cache invalidation complexity
- ⚠️ Increased memory usage

---

## ADR-007: Sync Strategy

**Status**: Accepted  
**Date**: 2025-08-30  
**Decision Makers**: Data Team

### Context
Need to keep local data synchronized with IT Glue.

### Decision
**Scheduled Incremental Sync**:
- Full sync on initial setup
- Incremental sync every 4 hours
- Manual sync trigger available
- Use modified_since timestamps

### Rationale
- 4-hour window balances freshness vs API limits
- Incremental reduces data transfer
- Manual trigger for urgent updates

### Implementation
- Celery for task scheduling
- Track last_sync_time per organization
- Parallel sync for different resource types

### Consequences
- ✅ Predictable API usage
- ✅ Eventually consistent data
- ⚠️ Up to 4-hour staleness
- ⚠️ Need conflict resolution

---

## ADR-008: Security Model

**Status**: Accepted  
**Date**: 2025-08-30  
**Decision Makers**: Security Team

### Context
Handling sensitive IT documentation requires strong security.

### Decision
**Defense in Depth**:
1. API key per session (not stored)
2. Organization-scoped access control
3. Audit logging of all queries
4. Encryption at rest and in transit
5. No sensitive data in logs

### Rationale
- Session-based keys prevent long-term storage
- Org scoping prevents data leakage
- Audit logs for compliance
- Encryption for data protection

### Consequences
- ✅ Meets compliance requirements
- ✅ Minimal attack surface
- ✅ Full audit trail
- ⚠️ Users must re-enter API key
- ⚠️ Cannot cache across sessions

---

## ADR-009: Error Handling Philosophy

**Status**: Accepted  
**Date**: 2025-08-30  
**Decision Makers**: Engineering Team

### Context
How should the system handle errors and edge cases?

### Decision
**Graceful Degradation**:
1. Never crash - always return meaningful response
2. Use cached data if API unavailable
3. Clear error messages for users
4. Detailed error logs for debugging

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "API_RATE_LIMITED",
    "message": "IT Glue API rate limit reached",
    "suggestion": "Results from cache (5 minutes old)",
    "cached_data": {...}
  }
}
```

### Consequences
- ✅ System remains usable during outages
- ✅ Users understand issues
- ✅ Easier debugging
- ⚠️ Complexity in fallback logic

---

## ADR-010: Testing Strategy

**Status**: Accepted  
**Date**: 2025-08-30  
**Decision Makers**: QA Team

### Context
Need to balance test coverage with MVP timeline.

### Decision
**Critical Path Testing**:
1. Unit tests for validation logic (100% coverage)
2. Integration tests for API and database
3. Manual MCP protocol testing
4. Skip E2E automation for MVP

### Rationale
- Focus on zero-hallucination accuracy
- API integration is critical path
- MCP protocol must work correctly
- E2E can be manual for MVP

### Consequences
- ✅ Fast test execution
- ✅ Critical paths covered
- ✅ Meets MVP timeline
- ⚠️ Manual testing overhead
- ❌ No automated E2E tests

---

## Decision Log

| Date | ADR | Decision | Status |
|------|-----|----------|--------|
| 2025-08-29 | ADR-001 | Modular Monolith Architecture | Accepted |
| 2025-08-29 | ADR-002 | Polyglot Persistence | Accepted |
| 2025-08-29 | ADR-003 | Zero-Hallucination Strategy | Accepted |
| 2025-08-29 | ADR-004 | MCP Protocol Implementation | Accepted |
| 2025-08-29 | ADR-005 | Hybrid Embedding Strategy | Accepted |
| 2025-08-30 | ADR-006 | Multi-level Caching | Accepted |
| 2025-08-30 | ADR-007 | Scheduled Incremental Sync | Accepted |
| 2025-08-30 | ADR-008 | Defense in Depth Security | Accepted |
| 2025-08-30 | ADR-009 | Graceful Degradation | Accepted |
| 2025-08-30 | ADR-010 | Critical Path Testing | Accepted |

---

## How to Propose New ADRs

1. Create new ADR with next number (ADR-011)
2. Include: Context, Decision, Rationale, Consequences
3. Submit PR for team review
4. Update Decision Log when accepted

## Templates

```markdown
## ADR-XXX: [Decision Title]

**Status**: Proposed|Accepted|Deprecated|Superseded  
**Date**: YYYY-MM-DD  
**Decision Makers**: [Team/Person]

### Context
[What is the issue we're addressing?]

### Decision
[What have we decided to do?]

### Rationale
[Why did we make this decision?]

### Consequences
- ✅ [Positive consequence]
- ⚠️ [Neutral/Warning]
- ❌ [Negative consequence]
```