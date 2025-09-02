# IT Glue MCP Server Query Coverage Enhancement PRD

## Executive Summary

This Product Requirements Document outlines the enhancement of the IT Glue MCP Server to achieve 100% API coverage for natural language querying. Currently supporting only 3 of 8+ available resource types (37.5% coverage), this enhancement will add support for Organizations, Documents, Flexible Assets, Locations, and Flexible Asset Types, enabling comprehensive access to IT documentation through the chat interface.

## 1. Intro Project Analysis and Context

### 1.1 Scope Assessment

This enhancement involves adding 5 missing resource type query implementations with an estimated 10-20 hours of work across multiple coordinated changes. This qualifies as a significant enhancement requiring comprehensive planning and multiple stories.

### 1.2 Existing Project Overview

#### Analysis Source
- Archon Analysis Document ID: 237f212a-351b-4762-975d-6878e7852edf
- IDE-based analysis: `/home/jamie/projects/itglue-mcp-server`

#### Current Project State
The IT Glue MCP Server is a production-ready system that:
- Provides natural language querying of IT Glue documentation
- Integrates with IT Glue API for data synchronization
- Uses Neo4j for relationship queries and Qdrant for semantic search
- Implements zero-hallucination responses with validation
- Currently supports only 3 of 8+ available resource types (Configurations, Passwords, Contacts)

### 1.3 Documentation Analysis

#### Available Documentation
- ✅ Tech Stack Documentation (Python, FastAPI, Neo4j, Qdrant, Redis)
- ✅ Source Tree/Architecture (Clean separation: models, client, query engine)
- ✅ API Documentation (IT Glue API examples comprehensive)
- ✅ External API Documentation (IT Glue API fully documented)
- ✅ Technical Debt Documentation (Identified in Archon analysis)
- ✅ Query Templates (Existing patterns documented)

### 1.4 Enhancement Scope Definition

#### Enhancement Type
- ✅ New Feature Addition - Adding missing query types
- ✅ Integration with Existing Systems - Extending current query infrastructure

#### Enhancement Description
Implementing query templates and intent detection for 5 missing IT Glue API resource types (Organizations, Flexible Assets, Documents, Locations, Flexible Asset Types) to enable natural language querying of all available IT Glue data through the MCP chat interface.

#### Impact Assessment
- ✅ Moderate Impact - Leveraging existing infrastructure with new query templates
- No architectural changes required
- Existing patterns will be followed
- Performance optimizations already in place

### 1.5 Goals and Background Context

#### Goals
- Enable querying of all 8+ IT Glue API resource types via natural language
- Achieve 100% API coverage (up from current 37.5%)
- Maintain sub-500ms response times with existing optimization
- Preserve zero-hallucination guarantee
- Enable cross-resource relationship queries

#### Background Context
The IT Glue MCP Server was built with robust infrastructure including Redis caching, RapidFuzz optimization, and Neo4j integration. However, only 3 resource types were initially implemented, leaving 62.5% of the API functionality inaccessible through the chat interface. This severely limits the system's utility for users who need to query organizations, documents, flexible assets, and other critical IT documentation. The infrastructure is 95% ready - only query template definitions are missing.

### 1.6 Change Log

| Change | Date | Version | Description | Author |
|--------|------|---------|-------------|--------|
| Initial | 2025-08-31 | 1.0 | Created brownfield PRD for query coverage enhancement | John (PM) |

## 2. Requirements

### 2.1 Functional Requirements

- **FR1:** The system SHALL implement natural language query support for Organizations resource type, enabling queries like "show all organizations", "find organization Acme Corp", and "list customers"
- **FR2:** The system SHALL implement natural language query support for Documents resource type, enabling queries like "find documentation for server ABC", "show runbooks for backup service", and "search knowledge base for password reset"
- **FR3:** The system SHALL implement natural language query support for Flexible Assets resource type, enabling queries like "show all SSL certificates", "find warranties expiring soon", and "list custom assets for client X"
- **FR4:** The system SHALL implement natural language query support for Locations resource type, enabling queries like "show all locations", "find New York office details", and "list sites for organization Y"
- **FR5:** The system SHALL implement natural language query support for Flexible Asset Types resource type, enabling queries like "show available asset types", "what custom fields does SSL Certificate type have"
- **FR6:** The query engine SHALL correctly detect intent for all new resource types using existing pattern matching infrastructure
- **FR7:** All new query types SHALL integrate with existing fuzzy matching system for organization name resolution and typo tolerance
- **FR8:** All new query types SHALL utilize existing Redis cache layer with same TTL and compression settings
- **FR9:** The system SHALL maintain existing response format structure for consistency across all resource types
- **FR10:** New query templates SHALL support existing filter parameters (company, limit, include_sources)

### 2.2 Non-Functional Requirements

- **NFR1:** Query response time for new resource types SHALL NOT exceed 500ms for 95% of requests (matching current performance)
- **NFR2:** The system SHALL maintain zero-hallucination guarantee by only returning data directly from IT Glue API
- **NFR3:** New implementations SHALL achieve minimum 60% cache hit rate after warm-up period
- **NFR4:** Memory usage SHALL NOT increase by more than 10% with addition of new query types
- **NFR5:** The system SHALL handle up to 1000 concurrent queries across all resource types without degradation
- **NFR6:** All new query types SHALL include comprehensive error handling with safe fallback responses
- **NFR7:** New implementations SHALL follow existing code patterns and architectural principles for maintainability
- **NFR8:** The system SHALL provide detailed logging for new query types matching current log levels and format

### 2.3 Compatibility Requirements

- **CR1:** Existing API Compatibility - All current query endpoints and response formats must remain unchanged. New resource types must use same request/response structure
- **CR2:** Database Schema Compatibility - No changes to existing database schemas. New resource types must use existing ITGlueEntity table structure
- **CR3:** UI/UX Consistency - Query syntax and natural language patterns must be consistent with existing implementations (e.g., "show", "find", "list" prefixes)
- **CR4:** Integration Compatibility - New query types must work seamlessly with existing MCP tools (search, sync_data, health checks) without modifications

## 3. Technical Constraints and Integration Requirements

### 3.1 Existing Technology Stack

- **Languages**: Python 3.11+
- **Frameworks**: FastAPI, Pydantic, SQLAlchemy, Neo4j Python Driver
- **Database**: PostgreSQL (primary), Neo4j (relationships), Qdrant (vector search)
- **Infrastructure**: Redis (caching), Docker containers
- **External Dependencies**: IT Glue API, MCP SDK, RapidFuzz, Jellyfish

### 3.2 Integration Approach

- **Database Integration Strategy**: Reuse existing ITGlueEntity model and repository patterns. New resource types will be stored in same table structure with entity_type differentiation. No schema migrations required.
- **API Integration Strategy**: Extend existing ITGlueClient methods (already implemented for all resource types). Add corresponding query tool endpoints following current pattern in src/mcp/tools/query_tool.py
- **Frontend Integration Strategy**: N/A - This is a backend service exposed through MCP protocol. Chat interface consumes via standard MCP tools.
- **Testing Integration Strategy**: Extend existing test suites in tests/query/ directory. Add fixture data for new resource types. Maintain current mock pattern for IT Glue API responses.

### 3.3 Code Organization and Standards

- **File Structure Approach**: 
  - Query templates: src/query/templates/[resource]_queries.py
  - Intent patterns: Update src/query/intelligent_query_processor.py
  - No new directories needed

- **Naming Conventions**: 
  - Query methods: get_[resource]s(), find_[resource]()
  - Template IDs: find_[resource]s, list_[resource]s
  - Cache keys: query:[company]:[resource]:[query_hash]

- **Coding Standards**: 
  - Follow existing async/await patterns
  - Maintain type hints on all methods
  - Use existing error handling decorators

- **Documentation Standards**: 
  - Docstrings following Google style (existing pattern)
  - Update MCP tool descriptions
  - Add examples to query templates

### 3.4 Deployment and Operations

- **Build Process Integration**: No changes needed - new code follows existing Python package structure
- **Deployment Strategy**: Rolling update via existing Docker deployment. No database migrations required.
- **Monitoring and Logging**: Use existing logger instances, maintain current log levels, extend Prometheus metrics
- **Configuration Management**: No new environment variables needed, reuse existing cache TTL and rate limit settings

### 3.5 Risk Assessment and Mitigation

- **Technical Risks**: 
  - Flexible Assets have dynamic schemas that may complicate query parsing
  - Document content could be large, impacting response times
  - Cross-resource queries may create N+1 query problems

- **Integration Risks**: 
  - IT Glue API rate limits may be hit with increased query variety
  - Cache key collisions if hash algorithm isn't robust enough
  - Intent detection conflicts between similar resource types

- **Deployment Risks**: 
  - Minimal - no schema changes or breaking API changes
  - Cache invalidation during rollout could cause temporary slowdowns

- **Mitigation Strategies**: 
  - Implement query result pagination for large datasets
  - Use existing RapidFuzz optimization for all new queries
  - Add circuit breakers for IT Glue API calls
  - Comprehensive testing with production-like data volumes
  - Gradual rollout with feature flags if concerns arise

## 4. Epic and Story Structure

### 4.1 Epic Approach

**Epic Structure Decision**: Single comprehensive epic titled "Complete IT Glue API Query Coverage"

**Rationale**: All work is tightly related - adding missing query types to achieve 100% API coverage. The infrastructure is shared, patterns are consistent, and testing can be coordinated. Breaking into multiple epics would create artificial boundaries and complicate integration testing.

## 5. Epic: Complete IT Glue API Query Coverage

**Epic Goal**: Enable natural language querying for all IT Glue API resource types, increasing coverage from 37.5% to 100% while maintaining current performance and reliability standards.

**Integration Requirements**: All new query types must seamlessly integrate with existing query engine, utilize current caching and fuzzy matching infrastructure, and maintain zero-hallucination response guarantee.

### Story 1.1: Implement Organizations Query Support

**As a** system administrator,
**I want** to query organizations using natural language,
**so that** I can quickly find client information and filter data by company.

#### Acceptance Criteria
1. Query patterns "show all organizations", "find organization [name]", "list customers" return correct results
2. Fuzzy matching works for organization name variations and typos
3. Results include id, name, type, and status fields
4. Response time under 500ms for 95% of queries
5. Cache integration working with 60%+ hit rate after warm-up

#### Integration Verification
- **IV1**: Existing configuration and password queries still function correctly
- **IV2**: Organization filter parameter works in other query types
- **IV3**: Memory usage increase less than 2% after implementation

### Story 1.2: Implement Documents Query Support

**As a** support technician,
**I want** to search IT Glue documents using natural language,
**so that** I can quickly find runbooks, procedures, and knowledge base articles.

#### Acceptance Criteria
1. Query patterns "find documentation for [system]", "show runbooks", "search knowledge base for [topic]" work correctly
2. Document content is searchable with relevance ranking
3. Results include document title, snippet, folder, and organization
4. Large documents are truncated appropriately in responses
5. Search integrates with existing Qdrant semantic search

#### Integration Verification
- **IV1**: Existing query types remain functional with no performance degradation
- **IV2**: Document queries respect organization filter when provided
- **IV3**: Response payload size remains under MCP limits even with document content

### Story 1.3: Implement Flexible Assets Query Support

**As an** IT asset manager,
**I want** to query flexible assets like SSL certificates and warranties,
**so that** I can track custom asset types and their expiration dates.

#### Acceptance Criteria
1. Query patterns "show all [asset type]", "find [asset type] for [org]" function correctly
2. Dynamic traits are properly extracted and searchable
3. Asset type filtering works correctly
4. Results include name, type, traits, and organization
5. Handles unknown asset types gracefully with clear error messages

#### Integration Verification
- **IV1**: Existing fixed asset queries (configurations) still work
- **IV2**: Flexible asset traits don't conflict with standard attributes
- **IV3**: Cache keys properly differentiate between asset types

### Story 1.4: Implement Locations Query Support

**As a** field technician,
**I want** to query location information through natural language,
**so that** I can find site details, addresses, and contact information.

#### Acceptance Criteria
1. Query patterns "show all locations", "find [city] office", "list sites for [org]" work
2. Location attributes (address, phone, contacts) are returned
3. Geographic filtering capabilities are documented
4. Integration with organization filter is seamless
5. Response format consistent with other resource types

#### Integration Verification
- **IV1**: No impact on existing contact queries (potential overlap)
- **IV2**: Location-organization relationships properly maintained
- **IV3**: Query intent detection correctly distinguishes locations from contacts

### Story 1.5: Add Flexible Asset Types Discovery

**As a** system integrator,
**I want** to discover available flexible asset types and their schemas,
**so that** I can understand what custom assets are configured in IT Glue.

#### Acceptance Criteria
1. Query patterns "show asset types", "what fields does [type] have" work
2. Returns asset type names, IDs, and field definitions
3. Provides human-readable field type descriptions
4. Lists which organizations use which asset types
5. Handles missing or unauthorized asset types gracefully

#### Integration Verification
- **IV1**: Asset type queries don't interfere with asset instance queries
- **IV2**: Caching strategy appropriate for slowly-changing type definitions
- **IV3**: No performance impact on other query types

### Story 1.6: Update Query Intent Detection

**As a** chat interface user,
**I want** the system to correctly understand my intent for all resource types,
**so that** I get accurate results regardless of how I phrase my query.

#### Acceptance Criteria
1. Intent patterns added for all 5 new resource types
2. Disambiguation logic when query could match multiple types
3. Helpful suggestions when intent is unclear
4. Existing intent detection for current types unchanged
5. Performance of intent detection remains under 50ms

#### Integration Verification
- **IV1**: No regression in existing intent detection accuracy
- **IV2**: New patterns don't create conflicts with existing ones
- **IV3**: Intent detection performance scales linearly with pattern count

### Story 1.7: Comprehensive Integration Testing

**As a** quality assurance engineer,
**I want** to verify all query types work together seamlessly,
**so that** we can deploy with confidence and maintain system reliability.

#### Acceptance Criteria
1. End-to-end tests cover all 8 resource types
2. Cross-resource query scenarios are tested
3. Performance benchmarks show no degradation
4. Cache hit rates meet or exceed targets
5. Error handling verified for each resource type
6. Load tests confirm system handles concurrent queries

#### Integration Verification
- **IV1**: Full regression test suite passes
- **IV2**: No memory leaks under sustained load
- **IV3**: IT Glue API rate limits are respected under all conditions

## 6. Success Metrics

### Current State
- API Coverage: 37.5%
- Query Types Supported: 3
- Total API Resources: 8

### Target State
- Phase 1 Coverage: 75% (after Organizations, Documents, Flexible Assets)
- Phase 2 Coverage: 100% (all resource types)
- Query Types Supported: 8+
- Response Time: <500ms for 95% of queries
- Cache Hit Rate: >60%

### Success Indicators
- All IT Glue API resources queryable via natural language
- Average query response time under 500ms
- Zero hallucination rate maintained
- User satisfaction with chat interface functionality

## 7. Implementation Timeline

- **Week 1**: Stories 1.1-1.3 (Organizations, Documents, Flexible Assets)
- **Week 2**: Stories 1.4-1.6 (Locations, Asset Types, Intent Detection)
- **Week 3**: Story 1.7 (Integration Testing) and deployment

Total Estimated Effort: 10-20 hours of development + testing

## 8. Conclusion

This enhancement addresses a critical gap in the IT Glue MCP Server, where 62.5% of available API functionality is inaccessible through the chat interface. With the infrastructure already 95% ready, implementing the missing query templates represents a high-value, low-risk enhancement that will provide a 2.6x increase in queryable data types. The structured approach outlined in this PRD ensures minimal disruption to the existing system while maximizing value delivery to users.