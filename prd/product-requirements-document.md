# Product Requirements Document (PRD)
## IT Glue MCP Server
### Version 1.0 - August 29, 2025

---

## Executive Summary

MSPs and IT departments using IT Glue face a critical problem: organic growth has created documentation chaos across silos, with technicians spending 15-30 minutes per ticket searching for information. Current IT Glue search requires exact terminology and doesn't surface related information, leaving valuable knowledge trapped in scattered documents. 

This MCP server transforms IT Glue's unstructured documentation into an intelligent knowledge base accessible through natural language queries, directly impacting customer satisfaction and technician productivity.

## Goals & Success Metrics

### Primary Goals
1. **Enable natural language querying** of IT Glue documentation to reduce search time from 15-30 minutes to under 2 seconds
2. **Provide zero-hallucination responses** ensuring 100% accuracy for IT support technicians
3. **Create an MCP server** that integrates seamlessly with chat interfaces for daily operational use
4. **Reduce support ticket escalations** by 25% through instant access to accurate documentation
5. **Save 2 hours daily per technician** by eliminating manual documentation searches

## Requirements

### Functional Requirements

| ID | Requirement | Priority |
|----|------------|----------|
| FR1 | The system shall integrate with IT Glue API using read-only access to retrieve organizations, configurations, passwords, and flexible assets | HIGH |
| FR2 | The system shall process natural language queries and return relevant documentation within 2 seconds | HIGH |
| FR3 | The system shall validate all responses against source data to ensure zero hallucination | CRITICAL |
| FR4 | The system shall provide company-scoped queries limiting results to selected organization | HIGH |
| FR5 | The system shall expose MCP tools including query_company, list_companies, get_asset, and search_fixes | HIGH |
| FR6 | The system shall cache frequently accessed data with 15-minute TTL for API responses | MEDIUM |
| FR7 | The system shall provide a Streamlit chat interface for user interactions | HIGH |
| FR8 | The system shall handle IT Glue API rate limiting with exponential backoff | HIGH |
| FR9 | The system shall log all queries to Supabase for audit and usage tracking | MEDIUM |
| FR10 | The system shall return 'No data available' when information cannot be found | CRITICAL |
| FR11 | The system shall synchronize IT Glue data to local Supabase and Qdrant stores on initial setup and periodic intervals | HIGH |
| FR12 | The system shall generate embeddings for all synchronized documentation using Ollama with all-MiniLM-L6-v2 | HIGH |
| FR13 | The system shall maintain source references for all returned information to enable validation | CRITICAL |

### Non-Functional Requirements

| ID | Requirement | Target |
|----|------------|--------|
| NFR1 | Response time must be under 2 seconds for 95% of queries | <2s |
| NFR2 | System must achieve 100% accuracy with zero false positives | 100% |
| NFR3 | System must support 100 concurrent users | 100 |
| NFR4 | API key and sensitive data must be encrypted at rest and in transit | Required |
| NFR5 | System must handle API rate limits gracefully without service interruption | Required |
| NFR6 | All user queries must be logged with proper audit trail | Required |
| NFR7 | System must be deployable via Docker Compose for local environments | Required |
| NFR8 | Python codebase must follow PEP 8 standards and include type hints | Required |
| NFR9 | System must provide clear error messages when data is unavailable | Required |
| NFR10 | MCP server must support both stdio and SSE communication protocols | Required |

## Development Epics

### Epic 1: Working MVP (2 weeks)
**Goal**: Deliver a functional IT Glue search tool within 2 weeks that provides immediate value to technicians, even with basic keyword searching. This establishes the foundation and allows early user testing while proving the IT Glue integration works correctly.

#### User Story 1.1: Project Foundation and IT Glue Client
**As a** developer  
**I want** a properly structured Python project with IT Glue API integration  
**So that** I can retrieve and search IT Glue data programmatically

**Acceptance Criteria:**
- Python 3.11+ project structure with poetry/requirements.txt for dependency management
- Environment configuration using .env file with example template
- IT Glue API client class with authentication and basic error handling
- Methods to fetch organizations, configurations, passwords, and flexible assets
- Rate limiting implementation with exponential backoff
- Unit tests for API client with mocked responses
- Docker container configuration for consistent development environment

#### User Story 1.2: Data Storage and Sync
**As a** system administrator  
**I want** IT Glue data synchronized to local Supabase storage  
**So that** queries can be served quickly without hitting API limits

**Acceptance Criteria:**
- Supabase (PostgreSQL) database schema for storing IT Glue entities
- Initial sync function that pulls all data for a specified organization
- Incremental sync capability with last-modified tracking
- Data validation to ensure completeness and integrity
- Sync status reporting (items synced, errors, duration)
- Command-line interface to trigger manual sync
- Basic logging of sync operations to Supabase audit table

#### User Story 1.3: Basic Search Functionality
**As a** support technician  
**I want** to search IT Glue data using keywords  
**So that** I can quickly find relevant documentation

**Acceptance Criteria:**
- Search function supporting multiple entity types (configs, passwords, assets)
- Keyword matching against name, description, and notes fields
- Organization-scoped search (only return results from selected org)
- Search results include entity type, name, and relevant fields
- Return 'No results found' for empty searches
- Response time under 1 second for keyword searches
- Search results limited to 20 items with most relevant first

#### User Story 1.4: Minimal Streamlit Interface
**As a** support technician  
**I want** a simple web interface for searching  
**So that** I can use the tool without command-line knowledge

**Acceptance Criteria:**
- Streamlit app with organization selector dropdown
- Search input field with search button
- Results displayed in readable format with entity types clearly marked
- Session-based IT Glue API key input (not stored)
- Basic error handling with user-friendly messages
- Docker-compose configuration to run full stack locally
- Health check endpoint showing API connection status

### Epic 2: Add Intelligence (2 weeks)
**Goal**: Transform the basic search tool into an intelligent natural language query system that understands context and intent, dramatically improving search accuracy and user experience.

#### User Story 2.1: Embedding Infrastructure
**As a** developer  
**I want** to generate and store embeddings for all IT Glue content  
**So that** semantic search becomes possible

**Acceptance Criteria:**
- Ollama integration with all-MiniLM-L6-v2 model
- Fallback to OpenAI embeddings API if Ollama unavailable
- Embedding generation for all synced documents
- Qdrant collection setup with proper indexing
- Batch processing to handle large document sets
- Progress tracking for embedding generation
- Re-embedding capability for updated documents

#### User Story 2.2: Natural Language Query Processing
**As a** support technician  
**I want** to ask questions in natural language  
**So that** I don't need to know exact terminology

**Acceptance Criteria:**
- Query parser that extracts intent and entities from natural language
- Query expansion to include synonyms and related terms
- Support for questions like 'What's the router IP for [Company]?'
- Context awareness (understanding 'printer' means configuration type)
- Query preprocessing to handle typos and variations
- Maintain backward compatibility with keyword search
- Query examples provided in UI

#### User Story 2.3: Semantic Search Implementation
**As a** support technician  
**I want** search results based on meaning not just keywords  
**So that** I find relevant information even with different terminology

**Acceptance Criteria:**
- Vector similarity search using Qdrant
- Hybrid search combining keyword and semantic matching
- Relevance scoring for search results
- Return top 10 most relevant results
- Include confidence scores with results
- Search across all text fields in documents
- Performance maintains sub-2 second response time

#### User Story 2.4: Enhanced UI with Query Intelligence
**As a** support technician  
**I want** an improved interface showing smart search capabilities  
**So that** I can leverage the full power of natural language queries

**Acceptance Criteria:**
- Autocomplete suggestions for common queries
- Query history for current session
- Example queries displayed prominently
- Results show relevance scores and source references
- Ability to refine search with follow-up questions
- Export results to clipboard/CSV
- Visual indicators for semantic vs keyword search mode

### Epic 3: Production Polish (2 weeks)
**Goal**: Add MCP protocol support, implement zero-hallucination validation, and optimize performance to create a production-ready system that can be deployed confidently.

#### User Story 3.1: MCP Server Implementation
**As an** AI assistant  
**I want** to access IT Glue data through MCP tools  
**So that** I can help users without them leaving their chat interface

**Acceptance Criteria:**
- MCP server implementation following protocol specification
- Tool definitions for query_company, list_companies, get_asset, search_fixes
- JSON-RPC message handling over stdio
- Proper error responses for invalid requests
- Tool discovery endpoint for MCP clients
- Connection handling for multiple concurrent sessions
- Integration tests using MCP test client

#### User Story 3.2: Zero-Hallucination Validation
**As a** support technician  
**I want** guaranteed accurate responses  
**So that** I can trust the system completely for critical information

**Acceptance Criteria:**
- Source tracking for all returned information
- Validation that responses only contain verified data
- Confidence threshold checking (only return high-confidence results)
- Clear 'No data available' responses when uncertain
- Audit trail showing source documents for each response
- Fact-checking against original IT Glue records
- 100% accuracy in validation tests

#### User Story 3.3: Performance Optimization
**As a** support technician  
**I want** consistently fast responses  
**So that** I can resolve tickets efficiently

**Acceptance Criteria:**
- Redis caching layer for frequent queries
- Query result caching with 15-minute TTL
- Database query optimization and indexing
- Connection pooling for all external services
- 95% of queries respond in under 2 seconds
- Load testing proving 100 concurrent user support
- Performance monitoring with Langfuse integration

#### User Story 3.4: Production Deployment Package
**As a** system administrator  
**I want** a production-ready deployment package  
**So that** I can reliably run this system in our environment

**Acceptance Criteria:**
- Comprehensive deployment documentation
- Health check endpoints for all services
- Graceful shutdown handling
- Log aggregation and error reporting
- Backup and restore procedures documented
- Security hardening checklist completed
- Runbook for common operational tasks

## Technical Architecture

### Technology Stack
- **Language**: Python 3.11+ (MCP SDK requires modern Python)
- **Primary Storage**: Supabase (PostgreSQL) for structured data, audit logs, and IT Glue entity storage
- **Vector Storage**: Qdrant for semantic search and embeddings
- **Optional Storage**: Redis for caching (if performance requires), Neo4j (if relationship queries become complex)
- **Embeddings**: Ollama with all-MiniLM-L6-v2 WITH fallback to OpenAI API if GPU unavailable
- **UI Framework**: Streamlit with basic session-based auth (IT Glue API key per session)
- **Deployment**: Single Docker container with docker-compose for dependencies (including local Supabase)
- **Configuration**: Environment variables with .env.example template including Supabase connection string

### Service Architecture
**Pattern**: Modular Monolith  
**Description**: Single Python application with clear module separation  
**Deployment**: Deploy as single container for MVP, can decompose later if needed

**Modules**:
- `mcp_handler/` - MCP protocol and tool definitions
- `itglue_client/` - API integration and rate limiting
- `query_engine/` - Natural language processing and validation
- `data_store/` - Abstracted storage layer (Supabase + Qdrant)

### Development Standards
- **Repository Structure**: Monorepo - Single repository containing the Python MCP server application with modular components
- **Development Tools**: Black for formatting, mypy for type checking, pytest for tests
- **Sync Strategy**: Initial full sync on startup, incremental syncs every 4 hours
- **Error Handling**: Graceful degradation - cached data in Supabase remains queryable if API fails
- **Database Client**: Supabase Python client library for database operations
- **Supabase Features**: Row Level Security (RLS) for multi-tenant data isolation, Realtime subscriptions for sync status

### Testing Requirements
**Approach**: Critical Path Testing Only

**Focus Areas**:
- Unit tests for zero-hallucination validation logic
- Integration tests for IT Glue API pagination and rate limiting
- Manual testing checklist for MCP protocol compliance
- Skip E2E automation for MVP

## Timeline & Milestones

| Week | Epic | Deliverables |
|------|------|-------------|
| 1-2 | Working MVP | Basic keyword search with IT Glue integration |
| 3-4 | Add Intelligence | Natural language processing and semantic search |
| 5-6 | Production Polish | MCP protocol, validation, and optimization |

## Next Steps

### For Architect
Create the technical architecture for the IT Glue MCP Server based on this PRD. Focus on a modular monolith design using Python 3.11+, Supabase for storage, Qdrant for semantic search, and MCP protocol implementation. Prioritize simplicity and the 6-week MVP timeline.

### For UX Expert
Review the IT Glue MCP Server PRD focusing on the Streamlit chat interface design. Create a simple, intuitive UI flow that allows technicians to quickly search IT documentation with natural language queries while maintaining the zero-hallucination accuracy requirement.

## Change Log

| Date | Version | Author | Description |
|------|---------|--------|-------------|
| 2025-08-29 | 1.0 | John (PM) | Initial PRD creation based on project brief |

---

*This document is maintained in the project repository at `/prd/product-requirements-document.md` and synced with Archon knowledge base for intelligent querying.*