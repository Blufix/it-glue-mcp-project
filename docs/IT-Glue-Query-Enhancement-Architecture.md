# IT Glue Query Enhancement Architecture Document

## Executive Summary

This document outlines the complete architecture and implementation strategy for enhancing the IT Glue MCP system with intelligent query processing capabilities. The system addresses the critical need for engineers to quickly access IT documentation during support incidents, with tolerance for spelling errors, natural language variations, and complex relationship queries.

---

## 1. System Overview

### 1.1 Problem Statement
- Engineers struggle with exact-match query requirements
- Spelling errors and typos lead to failed searches
- Organization name variations cause missed results
- Complex configuration relationships are not easily discoverable
- Support ticket resolution is delayed by inefficient information retrieval

### 1.2 Solution Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     Query Input Layer                        │
│  Natural Language │ Templates │ Voice │ Copy-Paste Error    │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│                 Intelligence Processing Layer                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │Fuzzy Matching│ │Intent Parser │ │Entity Extract│        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│                    Query Translation Layer                    │
│     SQL Builder │ Cypher Builder │ Vector Search Builder     │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│                     Execution Layer                          │
│  PostgreSQL │ Neo4j │ Qdrant │ Redis Cache │ IT Glue API    │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│                  Result Aggregation Layer                    │
│    Ranking │ Deduplication │ Relevance Scoring │ Formatting │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Core Components

### 2.1 Fuzzy Matching Engine

**Purpose:** Resolve spelling errors and name variations

**Key Algorithms:**
- **Levenshtein Distance:** Character-level similarity
- **Double Metaphone:** Phonetic matching
- **N-gram Similarity:** Partial string matching
- **Jaro-Winkler:** Optimized for short strings

**Configuration:**
```yaml
fuzzy_config:
  min_similarity_threshold: 0.7
  max_suggestions: 5
  algorithms:
    - levenshtein: { weight: 0.4 }
    - metaphone: { weight: 0.3 }
    - ngram: { weight: 0.2 }
    - acronym: { weight: 0.1 }
```

### 2.2 Query Intelligence System

**Intent Classification Categories:**
```yaml
intents:
  troubleshooting:
    keywords: [down, broken, failed, error, not working]
    priority: critical
    cache_ttl: 60
    
  investigation:
    keywords: [why, what, who, when, changed, caused]
    priority: high
    cache_ttl: 300
    
  audit:
    keywords: [audit, compliance, expired, old, unused]
    priority: medium
    cache_ttl: 3600
    
  documentation:
    keywords: [guide, docs, how to, manual, procedure]
    priority: low
    cache_ttl: 86400
```

### 2.3 Neo4j Graph Schema

**Node Types:**
```cypher
// Primary Entities
(:Organization {id, name, type, status})
(:Configuration {id, name, type, os, ip_address, hostname})
(:Password {id, name, username, category, url})
(:Document {id, name, content, folder})
(:Asset {id, name, type, traits})
(:Ticket {id, number, description, status})
(:Change {id, description, timestamp, author})

// Relationships
(:Configuration)-[:DEPENDS_ON]->(:Configuration)
(:Configuration)-[:BELONGS_TO]->(:Organization)
(:Configuration)-[:HOSTED_ON]->(:Configuration)
(:Password)-[:AUTHENTICATES]->(:Configuration)
(:Document)-[:REFERENCES]->(:Configuration)
(:Ticket)-[:AFFECTS]->(:Configuration)
(:Change)-[:MODIFIED]->(:Configuration)
(:Configuration)-[:CONNECTS_TO]->(:Configuration)
```

---

## 3. Query Catalog Structure

### 3.1 Query Template Hierarchy

```yaml
query_catalog:
  version: "2.0"
  
  base_templates:
    infrastructure:
      list_servers:
        pattern: "show [all] {type} servers [for|at|in] {organization}"
        sql: "SELECT * FROM configurations WHERE type='server' AND org_name FUZZY_MATCH ?"
        cypher: "MATCH (c:Configuration {type:'server'})-[:BELONGS_TO]->(o:Organization) WHERE o.name =~ $org_pattern RETURN c"
        fuzzy_fields: [organization, type]
        
      find_by_ip:
        pattern: "find [device|server|system] with IP {ip_address}"
        sql: "SELECT * FROM configurations WHERE ip_address = ?"
        fuzzy_fields: []
        validation: ip_format
    
    security:
      get_password:
        pattern: "get [admin] password for {system}"
        sql: "SELECT * FROM passwords WHERE system_name FUZZY_MATCH ? AND category='admin'"
        security_check: true
        audit_log: true
        fuzzy_fields: [system]
        
      expired_passwords:
        pattern: "show expired passwords [for {organization}]"
        sql: "SELECT * FROM passwords WHERE updated_at < NOW() - INTERVAL '90 days'"
        fuzzy_fields: [organization]
    
    relationships:
      dependencies:
        pattern: "what depends on {system}"
        cypher: "MATCH (s:Configuration)-[:DEPENDS_ON*1..3]->(target:Configuration {name: $system}) RETURN s"
        fuzzy_fields: [system]
        
      impact_analysis:
        pattern: "what breaks if {system} fails"
        cypher: "MATCH path=(start:Configuration {name: $system})-[:DEPENDS_ON*1..5]-(affected) RETURN affected, length(path) as distance ORDER BY distance"
        fuzzy_fields: [system]
```

---

## 4. Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

**Objectives:**
- Implement basic fuzzy matching
- Deploy top 10 query templates
- Enable simple typo correction

**Deliverables:**

| Component | Implementation | Success Criteria |
|-----------|---------------|------------------|
| Fuzzy Matcher | Levenshtein distance for org names | 85% match accuracy |
| Query Templates | Parameterized SQL templates | 10 templates active |
| Typo Dictionary | Common IT terms corrections | 100+ terms mapped |
| Response Time | Direct query execution | <500ms p95 |

**Code Structure:**
```python
src/
  query/
    fuzzy_matcher.py       # Core fuzzy logic
    template_engine.py     # Template processing
    typo_corrector.py      # Spelling corrections
  tests/
    test_fuzzy_matcher.py
    test_templates.py
```

### Phase 2: Intelligence Layer (Weeks 3-4)

**Objectives:**
- Add intent classification
- Implement entity extraction
- Create basic Neo4j relationships

**Deliverables:**

| Component | Implementation | Success Criteria |
|-----------|---------------|------------------|
| Intent Classifier | NLP-based classification | 70% accuracy |
| Entity Extractor | Named entity recognition | Extract org, system, IP |
| Neo4j Integration | Basic relationship queries | 5 relationship types |
| Context Manager | Session-based context | Maintains last 5 queries |

**Neo4j Initialization:**
```cypher
// Create indexes
CREATE INDEX org_name IF NOT EXISTS FOR (o:Organization) ON (o.name);
CREATE INDEX config_name IF NOT EXISTS FOR (c:Configuration) ON (c.name);
CREATE INDEX config_ip IF NOT EXISTS FOR (c:Configuration) ON (c.ip_address);

// Create constraints
CREATE CONSTRAINT unique_org_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE;
CREATE CONSTRAINT unique_config_id IF NOT EXISTS FOR (c:Configuration) REQUIRE c.id IS UNIQUE;
```

### Phase 3: Advanced Features (Weeks 5-6)

**Objectives:**
- Implement context awareness
- Add smart suggestions
- Enable complex graph traversals

**Deliverables:**

| Component | Implementation | Success Criteria |
|-----------|---------------|------------------|
| Context Engine | Multi-query context tracking | Reduces input by 40% |
| Suggestion Engine | ML-based suggestions | 3-5 relevant suggestions |
| Graph Traversal | Multi-hop relationship queries | Up to 5-level depth |
| Cache Layer | Redis with smart invalidation | 90% cache hit rate |

**Context Management:**
```python
class QueryContext:
    def __init__(self):
        self.organization = None
        self.recent_systems = []
        self.current_ticket = None
        self.time_context = "last_24h"
        self.user_role = None
    
    def enhance_query(self, query):
        # Add implicit context
        if not self.has_org(query) and self.organization:
            query += f" for {self.organization}"
        return query
```

### Phase 4: Optimization & Learning (Weeks 7-8)

**Objectives:**
- Implement query learning
- Add predictive capabilities
- Optimize performance

**Deliverables:**

| Component | Implementation | Success Criteria |
|-----------|---------------|------------------|
| Query Learning | Personal query patterns | 20% faster query creation |
| Predictive Queries | Time/role-based predictions | 60% acceptance rate |
| Performance Tuning | Query optimization, indexing | <200ms p95 |
| Analytics Dashboard | Usage metrics and patterns | Real-time insights |

---

## 5. Integration Architecture

### 5.1 API Endpoints

```yaml
api_endpoints:
  /api/query/process:
    method: POST
    input:
      query: string
      context: object (optional)
      options:
        fuzzy_matching: boolean
        max_results: integer
        include_suggestions: boolean
    output:
      results: array
      corrections: object
      suggestions: array
      metadata:
        confidence: float
        execution_time: float
        cache_hit: boolean
  
  /api/query/templates:
    method: GET
    output:
      templates: array
      categories: array
  
  /api/query/suggest:
    method: POST
    input:
      partial_query: string
      context: object
    output:
      suggestions: array
```

### 5.2 MCP Tool Integration

```python
mcp_tools = {
    "query_it_glue": {
        "description": "Natural language query for IT Glue data",
        "parameters": {
            "query": "string",
            "organization": "string (optional)",
            "fuzzy": "boolean (default: true)"
        }
    },
    "find_dependencies": {
        "description": "Find system dependencies",
        "parameters": {
            "system": "string",
            "depth": "integer (default: 3)"
        }
    }
}
```

---

## 6. Security Considerations

### 6.1 Access Control
```yaml
security:
  authentication:
    method: session_based
    timeout: 8_hours
    
  authorization:
    roles:
      tier1_support:
        - read_configurations
        - read_basic_passwords
      tier2_support:
        - all_tier1_permissions
        - modify_configurations
        - read_all_passwords
      admin:
        - all_permissions
        
  audit:
    log_all_queries: true
    log_fuzzy_corrections: true
    sensitive_data_masking: true
```

### 6.2 Data Protection
- No password values in cache
- Encrypted query logs
- PII redaction in suggestions
- Rate limiting per user

---

## 7. Performance Requirements

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Query Response Time (p50) | 200ms | 500ms |
| Query Response Time (p95) | 500ms | 2000ms |
| Fuzzy Match Time | 50ms | 200ms |
| Neo4j Traversal (3 levels) | 100ms | 500ms |
| Cache Hit Rate | >80% | >60% |
| Concurrent Queries | 100/sec | 50/sec |

---

## 8. Monitoring & Metrics

```yaml
metrics:
  performance:
    - query_duration_histogram
    - fuzzy_match_duration
    - neo4j_query_time
    - cache_hit_rate
    
  usage:
    - queries_per_minute
    - unique_users_per_hour
    - most_common_queries
    - failed_queries
    
  quality:
    - fuzzy_match_accuracy
    - intent_classification_accuracy
    - suggestion_acceptance_rate
    - user_satisfaction_score
    
  alerts:
    - response_time_degradation
    - high_error_rate
    - cache_miss_spike
    - unusual_query_patterns
```

---

## 9. Testing Strategy

### 9.1 Test Coverage Requirements

| Test Type | Coverage Target | Priority |
|-----------|----------------|----------|
| Unit Tests | 80% | Critical |
| Integration Tests | 70% | High |
| Fuzzy Match Tests | 90% | Critical |
| Performance Tests | Key paths | High |
| Security Tests | All endpoints | Critical |

### 9.2 Test Scenarios

```python
test_scenarios = [
    # Fuzzy matching
    ("microsft", "Microsoft Corporation", 0.9),
    ("amazone web services", "Amazon Web Services", 0.85),
    
    # Query patterns
    ("show all windws servers for acme", "valid_query"),
    ("get pasword for mail-server", "corrected_query"),
    
    # Neo4j relationships
    ("what depends on exchange", "dependency_tree"),
    ("impact if firewall fails", "impact_analysis"),
]
```

---

## 10. Migration & Rollout Plan

### 10.1 Rollout Strategy

**Week 1-2: Soft Launch**
- Deploy to staging environment
- Test with volunteer engineers
- Gather feedback and metrics

**Week 3-4: Limited Production**
- 10% of queries use new system
- A/B testing for accuracy
- Performance monitoring

**Week 5-6: Gradual Rollout**
- Increase to 50% of queries
- Enable advanced features
- Train support team

**Week 7-8: Full Deployment**
- 100% query traffic
- Deprecate old search
- Enable learning features

### 10.2 Rollback Plan

```yaml
rollback_triggers:
  - error_rate > 5%
  - response_time > 2sec
  - accuracy < 70%
  
rollback_procedure:
  1. Switch traffic to legacy system
  2. Preserve query logs
  3. Analyze failure patterns
  4. Fix and retest
  5. Gradual re-deployment
```

---

## 11. Success Metrics

| KPI | Baseline | Target (Phase 1) | Target (Phase 4) |
|-----|----------|------------------|------------------|
| Query Success Rate | 60% | 80% | 95% |
| Avg Resolution Time | 45 sec | 30 sec | 15 sec |
| User Satisfaction | 3.2/5 | 4.0/5 | 4.5/5 |
| Support Ticket Time | 25 min | 20 min | 15 min |
| "No Results" Rate | 40% | 20% | 5% |

---

## 12. Appendices

### A. Fuzzy Matching Examples

| Input | Matched | Method | Score |
|-------|---------|--------|-------|
| "Microsft" | "Microsoft" | Levenshtein | 0.89 |
| "Jon Smith Co" | "John Smith Company" | Phonetic | 0.85 |
| "AWS" | "Amazon Web Services" | Acronym | 0.95 |
| "Acme Corp" | "Acme Corporation" | Abbreviation | 0.92 |

### B. Common Query Templates

1. `show all {type} servers for {organization}`
2. `get {credential_type} password for {system}`
3. `what changed {time_period} for {configuration}`
4. `find {asset_type} at {location}`
5. `list expired {item_type} for {organization}`

### C. Neo4j Query Examples

```cypher
// Find all dependencies
MATCH path = (c:Configuration {name: $system})-[:DEPENDS_ON*]-(dep)
RETURN path

// Impact analysis
MATCH (c:Configuration {name: $system})
CALL apoc.path.subgraphAll(c, {
    relationshipFilter: "DEPENDS_ON|CONNECTS_TO|HOSTED_ON",
    maxLevel: 5
})
YIELD nodes, relationships
RETURN nodes, relationships

// Find related passwords
MATCH (c:Configuration {name: $system})-[:BELONGS_TO]->(o:Organization)
MATCH (p:Password)-[:BELONGS_TO]->(o)
WHERE p.url CONTAINS c.hostname
RETURN p
```

---

## Document Version
- **Version:** 1.0
- **Date:** 2024
- **Status:** Architecture Proposal
- **Author:** Mary (Business Analyst)
- **Next Review:** After Phase 2 completion

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024 | Mary | Initial architecture document |

---

## Related Documents
- IT Glue Supported Queries Documentation
- IT Glue MCP Server Technical Specification
- Neo4j Graph Database Design
- Fuzzy Matching Algorithm Research