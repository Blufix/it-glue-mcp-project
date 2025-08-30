# Data Flow Diagrams

## System Overview Data Flow

```mermaid
graph TB
    subgraph "External Systems"
        ITG[IT Glue API]
        OLLAMA[Ollama LLM]
        OPENAI[OpenAI API]
        CLAUDE[Claude Desktop]
    end
    
    subgraph "Entry Points"
        MCP[MCP Server]
        API[REST API]
        UI[Streamlit UI]
    end
    
    subgraph "Core Services"
        QH[Query Handler]
        VAL[Validation Service]
        SYNC[Sync Service]
        EMB[Embedding Service]
    end
    
    subgraph "Data Stores"
        PG[(PostgreSQL)]
        QD[(Qdrant)]
        NEO[(Neo4j)]
        REDIS[(Redis)]
    end
    
    %% User interactions
    CLAUDE -->|MCP Protocol| MCP
    UI -->|HTTP| API
    
    %% Service connections
    MCP --> QH
    API --> QH
    
    %% Query processing
    QH --> VAL
    QH --> REDIS
    QH --> PG
    QH --> QD
    QH --> NEO
    
    %% Sync flow
    SYNC --> ITG
    SYNC --> PG
    SYNC --> EMB
    EMB --> OLLAMA
    EMB --> OPENAI
    EMB --> QD
    
    %% Validation
    VAL --> PG
```

## Query Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Streamlit UI
    participant API as REST API
    participant QH as Query Handler
    participant Cache as Redis Cache
    participant Val as Validation
    participant PG as PostgreSQL
    participant QD as Qdrant
    participant Neo as Neo4j

    User->>UI: Enter natural language query
    UI->>API: POST /api/query
    API->>QH: process_query(text, org_id)
    
    %% Check cache first
    QH->>Cache: get(query_hash)
    alt Cache Hit
        Cache-->>QH: cached_result
        QH-->>API: return cached_result
    else Cache Miss
        %% Parse query intent
        QH->>QH: parse_intent(query)
        
        %% Parallel searches
        par Search Databases
            QH->>PG: SQL search
            PG-->>QH: structured_results
        and
            QH->>QD: vector_search
            QD-->>QH: semantic_results
        and
            QH->>Neo: graph_query
            Neo-->>QH: relationship_results
        end
        
        %% Merge and rank
        QH->>QH: merge_results()
        QH->>QH: rank_by_relevance()
        
        %% Validate
        QH->>Val: validate(results)
        Val->>PG: verify_sources
        PG-->>Val: source_docs
        Val->>Val: check_hallucination
        Val-->>QH: validated_results
        
        %% Cache result
        QH->>Cache: set(query_hash, results, ttl=300)
        
        %% Return
        QH-->>API: validated_results
    end
    
    API-->>UI: JSON response
    UI-->>User: Display results
```

## Data Synchronization Flow

```mermaid
graph LR
    subgraph "IT Glue API"
        ORGS[Organizations]
        CONFIGS[Configurations]
        PASSWORDS[Passwords]
        ASSETS[Flexible Assets]
    end
    
    subgraph "Sync Service"
        SCHEDULER[Celery Scheduler]
        WORKER[Sync Worker]
        TRANSFORM[Data Transformer]
    end
    
    subgraph "Processing"
        EMBED[Embedding Generator]
        RELATE[Relationship Builder]
        INDEX[Index Builder]
    end
    
    subgraph "Storage"
        PG[(PostgreSQL)]
        QDRANT[(Qdrant)]
        NEO4J[(Neo4j)]
    end
    
    SCHEDULER -->|Every 4 hours| WORKER
    WORKER --> ORGS
    WORKER --> CONFIGS
    WORKER --> PASSWORDS
    WORKER --> ASSETS
    
    ORGS --> TRANSFORM
    CONFIGS --> TRANSFORM
    PASSWORDS --> TRANSFORM
    ASSETS --> TRANSFORM
    
    TRANSFORM --> PG
    TRANSFORM --> EMBED
    EMBED --> QDRANT
    
    TRANSFORM --> RELATE
    RELATE --> NEO4J
    
    TRANSFORM --> INDEX
    INDEX --> PG
```

## MCP Protocol Flow

```mermaid
sequenceDiagram
    participant Client as Claude/ChatGPT
    participant MCP as MCP Server
    participant Tools as Tool Registry
    participant QH as Query Handler
    participant DS as Data Stores

    Client->>MCP: Initialize connection (stdio/SSE)
    MCP->>Tools: Register available tools
    Tools-->>MCP: Tool definitions
    MCP-->>Client: Available tools list
    
    Client->>MCP: {"method": "query_company", "params": {...}}
    MCP->>Tools: Route to tool handler
    Tools->>QH: Execute query
    QH->>DS: Fetch data
    DS-->>QH: Results
    QH-->>Tools: Processed results
    Tools-->>MCP: Tool response
    MCP-->>Client: {"result": {...}}
```

## Embedding Generation Flow

```mermaid
graph TD
    subgraph "Input"
        DOC[Document Text]
    end
    
    subgraph "Preprocessing"
        CHUNK[Text Chunker]
        CLEAN[Text Cleaner]
    end
    
    subgraph "Embedding Generation"
        LOCAL{Local Available?}
        OLLAMA[Ollama all-MiniLM]
        OPENAI[OpenAI Ada-002]
    end
    
    subgraph "Storage"
        QDRANT[(Qdrant Vector DB)]
        CACHE[(Redis Cache)]
    end
    
    DOC --> CHUNK
    CHUNK --> CLEAN
    CLEAN --> LOCAL
    
    LOCAL -->|Yes| OLLAMA
    LOCAL -->|No| OPENAI
    
    OLLAMA --> QDRANT
    OPENAI --> QDRANT
    
    OLLAMA --> CACHE
    OPENAI --> CACHE
```

## Authentication & Authorization Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Streamlit UI
    participant Auth as Auth Service
    participant Session as Session Store
    participant API as API Gateway
    participant ITG as IT Glue

    User->>UI: Enter IT Glue API Key
    UI->>Auth: validate_api_key(key)
    Auth->>ITG: GET /organizations (test key)
    
    alt Valid Key
        ITG-->>Auth: 200 OK
        Auth->>Session: store_session(user_id, key_hash)
        Session-->>Auth: session_token
        Auth-->>UI: auth_success(token)
        UI->>UI: Set session state
        
        loop Subsequent Requests
            UI->>API: Request + session_token
            API->>Session: validate_token
            Session-->>API: user_context
            API->>API: Process with context
        end
    else Invalid Key
        ITG-->>Auth: 401 Unauthorized
        Auth-->>UI: auth_failed
        UI-->>User: Show error
    end
```

## Caching Strategy Flow

```mermaid
graph TD
    subgraph "Request"
        QUERY[User Query]
    end
    
    subgraph "Cache Layers"
        L1[L1: Application Memory<br/>TTL: 60s]
        L2[L2: Redis Query Cache<br/>TTL: 5 min]
        L3[L3: Redis Embedding Cache<br/>TTL: 1 hour]
        L4[L4: PostgreSQL Materialized Views<br/>TTL: 4 hours]
    end
    
    subgraph "Data Sources"
        LIVE[Live Query Processing]
        DB[(Databases)]
    end
    
    QUERY --> L1
    L1 -->|Miss| L2
    L2 -->|Miss| L3
    L3 -->|Miss| L4
    L4 -->|Miss| LIVE
    
    LIVE --> DB
    DB --> LIVE
    
    LIVE -->|Store| L4
    LIVE -->|Store| L3
    LIVE -->|Store| L2
    LIVE -->|Store| L1
```

## Error Handling Flow

```mermaid
graph TD
    subgraph "Error Sources"
        API_ERR[API Error]
        DB_ERR[Database Error]
        VAL_ERR[Validation Error]
        NET_ERR[Network Error]
    end
    
    subgraph "Error Handler"
        CLASSIFY[Classify Error]
        RETRY{Retryable?}
        FALLBACK{Cache Available?}
    end
    
    subgraph "Responses"
        RETRY_OP[Retry with Backoff]
        USE_CACHE[Return Cached Data]
        GRACEFUL[Graceful Error Response]
        LOG[Log Error]
    end
    
    API_ERR --> CLASSIFY
    DB_ERR --> CLASSIFY
    VAL_ERR --> CLASSIFY
    NET_ERR --> CLASSIFY
    
    CLASSIFY --> RETRY
    RETRY -->|Yes| RETRY_OP
    RETRY -->|No| FALLBACK
    
    FALLBACK -->|Yes| USE_CACHE
    FALLBACK -->|No| GRACEFUL
    
    RETRY_OP --> LOG
    USE_CACHE --> LOG
    GRACEFUL --> LOG
```

## Data Validation Flow

```mermaid
sequenceDiagram
    participant QH as Query Handler
    participant VAL as Validation Service
    participant SRC as Source Verifier
    participant PG as PostgreSQL
    participant AUDIT as Audit Logger

    QH->>VAL: validate_response(text, sources)
    
    VAL->>VAL: extract_claims(text)
    
    loop For Each Claim
        VAL->>SRC: verify_claim(claim, sources)
        SRC->>PG: get_source_document(doc_id)
        PG-->>SRC: document_content
        SRC->>SRC: check_claim_in_content()
        
        alt Claim Verified
            SRC-->>VAL: verified: true
        else Claim Not Found
            SRC-->>VAL: verified: false
            VAL->>VAL: mark_as_hallucination()
        end
    end
    
    VAL->>AUDIT: log_validation_result()
    
    alt All Claims Valid
        VAL-->>QH: validation_passed
    else Hallucination Detected
        VAL-->>QH: validation_failed
        QH->>QH: return "No data available"
    end
```

## Performance Monitoring Flow

```mermaid
graph LR
    subgraph "Application"
        APP[Application Metrics]
        API[API Metrics]
        DB[Database Metrics]
    end
    
    subgraph "Collection"
        PROM[Prometheus]
        LOKI[Loki Logs]
        TRACE[Jaeger Traces]
    end
    
    subgraph "Visualization"
        GRAF[Grafana]
        ALERT[AlertManager]
    end
    
    subgraph "Actions"
        SLACK[Slack Alerts]
        SCALE[Auto-scaling]
        PAGE[PagerDuty]
    end
    
    APP --> PROM
    API --> PROM
    DB --> PROM
    
    APP --> LOKI
    API --> TRACE
    
    PROM --> GRAF
    LOKI --> GRAF
    TRACE --> GRAF
    
    PROM --> ALERT
    ALERT --> SLACK
    ALERT --> PAGE
    ALERT --> SCALE
```

## Data Privacy & Compliance Flow

```mermaid
graph TD
    subgraph "Data Classification"
        PUBLIC[Public Data]
        INTERNAL[Internal Data]
        SENSITIVE[Sensitive Data]
        CREDENTIALS[Credentials]
    end
    
    subgraph "Processing Rules"
        ENCRYPT[Encryption Required]
        MASK[Masking Required]
        AUDIT[Audit Required]
        RESTRICT[Access Restricted]
    end
    
    subgraph "Storage"
        ENCRYPTED[(Encrypted Storage)]
        STANDARD[(Standard Storage)]
        NOSTOR[No Storage<br/>Session Only]
    end
    
    PUBLIC --> STANDARD
    INTERNAL --> AUDIT
    INTERNAL --> STANDARD
    
    SENSITIVE --> ENCRYPT
    SENSITIVE --> MASK
    SENSITIVE --> AUDIT
    SENSITIVE --> ENCRYPTED
    
    CREDENTIALS --> ENCRYPT
    CREDENTIALS --> RESTRICT
    CREDENTIALS --> NOSTOR
```

---

## Key Data Flow Principles

1. **Cache First**: Always check cache before expensive operations
2. **Parallel Processing**: Execute independent queries concurrently
3. **Fail Fast**: Validate early in the pipeline
4. **Graceful Degradation**: Use cached/stale data when services unavailable
5. **Audit Everything**: Log all data access for compliance
6. **Zero Trust**: Validate at every boundary
7. **Async Where Possible**: Use async operations for I/O bound tasks

## Performance Targets

- Query Response: < 2 seconds (95th percentile)
- Cache Hit Rate: > 60%
- Sync Completion: < 30 minutes for full org
- Embedding Generation: < 100ms per document
- Validation: < 50ms per response

## Data Retention

- Query Cache: 5 minutes
- Embedding Cache: 1 hour  
- Session Data: 24 hours
- Audit Logs: 90 days
- Sync History: 30 days
- Error Logs: 7 days