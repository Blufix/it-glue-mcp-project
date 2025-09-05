# Test Coverage Fix Plan

## Current Situation Analysis

### Coverage Breakdown
- **Current Coverage**: 12.97% (Target: 80%)
- **Total Tests**: 499 collected
- **Test Results**: ~20 passing, majority failing
- **Critical Issues**:
  1. Recursion error in fuzzy_matcher tests
  2. Missing mock implementations for IT Glue client
  3. Query handlers have 0% coverage
  4. Integration tests failing due to missing dependencies

### Component Coverage Analysis

#### Zero Coverage Components (Critical)
1. **Query Handlers** (0% coverage each):
   - `organizations_handler.py` - 205 lines
   - `documents_handler.py` - 224 lines  
   - `flexible_assets_handler.py` - 195 lines
   - `locations_handler.py` - 165 lines
   - `asset_type_handler.py` - Not measured yet
   
2. **Infrastructure Components** (0% coverage):
   - `infrastructure/documentation_handler.py` - Core feature

3. **Query Processing** (Low coverage):
   - `intelligent_query_processor.py` - 10.06%
   - `fuzzy_matcher.py` - 14.94%
   - `phonetic_matcher.py` - 8.43%

#### Low Coverage Components
- `services/itglue/client.py` - 12.39% (Critical - all handlers depend on this)
- `search/semantic.py` - 12.50%
- `cache/redis_cache.py` - 11.44%

## Root Cause Analysis

### Primary Issues
1. **Missing IT Glue Client Mocks**: All query handlers fail because ITGlueClient isn't properly mocked
2. **Database Dependencies**: Tests expect database connections that don't exist in test environment
3. **External Service Dependencies**: Redis, Qdrant, Neo4j connections not mocked
4. **Recursion Bug**: Fuzzy matcher tests have infinite recursion
5. **Import Structure**: Some tests can't find proper implementations

## Fix Strategy

### Phase 1: Foundation Fixes (Target: 30% coverage)

#### 1.1 Fix IT Glue Client Mocking
```python
# Create comprehensive mock for ITGlueClient
# Location: tests/fixtures/mock_itglue_client.py
- Mock all client methods
- Return realistic test data
- Support async operations
```

#### 1.2 Fix Database Mocking
```python
# Create database mock fixtures
# Location: tests/fixtures/mock_database.py
- Mock db_manager
- Mock UnitOfWork
- Mock repository methods
```

#### 1.3 Fix External Services
```python
# Mock Redis, Qdrant, Neo4j
# Location: tests/fixtures/mock_services.py
- Mock cache operations
- Mock vector search
- Mock graph queries
```

### Phase 2: Query Handler Tests (Target: 60% coverage)

#### 2.1 Organizations Handler
- Test list_all_organizations
- Test find_organization with fuzzy matching
- Test search_organizations
- Test organization type filtering
- Test caching behavior

#### 2.2 Documents Handler  
- Test document search
- Test semantic search integration
- Test runbook queries
- Test knowledge base search
- Test document truncation

#### 2.3 Flexible Assets Handler
- Test asset type discovery
- Test dynamic trait handling
- Test organization filtering
- Test unknown type handling

#### 2.4 Locations Handler
- Test location listing
- Test city-based search
- Test organization filtering
- Test fuzzy location matching

#### 2.5 Asset Type Handler
- Test type listing
- Test type description
- Test common types
- Test field definitions

### Phase 3: Integration Tests (Target: 80% coverage)

#### 3.1 End-to-End Query Flow
- Test complete query pipeline
- Test caching integration
- Test error handling
- Test rate limiting

#### 3.2 Infrastructure Documentation
- Test documentation generation
- Test embedding creation
- Test progress tracking
- Test organization resolution

## Implementation Order

### Immediate Actions (Fix Blockers)

1. **Fix Recursion Error**
   - File: `tests/unit/test_fuzzy_matcher_comprehensive.py`
   - Issue: Line 105 has infinite recursion with Path()
   - Fix: Remove or correct the Path lambda

2. **Create Base Test Fixtures**
   ```bash
   tests/fixtures/
   ├── __init__.py
   ├── mock_itglue_client.py
   ├── mock_database.py
   ├── mock_services.py
   └── test_data.py
   ```

3. **Fix Import Issues**
   - Ensure all test files can import their targets
   - Add proper __init__.py files
   - Fix PYTHONPATH in pytest.ini if needed

### Step-by-Step Implementation

#### Step 1: Create Mock Infrastructure (2 hours)
- [ ] Create mock ITGlueClient with all methods
- [ ] Create mock database components
- [ ] Create mock external services
- [ ] Create realistic test data

#### Step 2: Fix Unit Tests (3 hours)
- [ ] Fix fuzzy matcher recursion
- [ ] Fix entity extractor tests
- [ ] Fix query parser tests
- [ ] Fix validator tests

#### Step 3: Implement Query Handler Tests (4 hours)
- [ ] Organizations handler tests
- [ ] Documents handler tests
- [ ] Flexible assets handler tests
- [ ] Locations handler tests
- [ ] Asset type handler tests

#### Step 4: Fix Integration Tests (2 hours)
- [ ] Fix MCP protocol tests
- [ ] Fix infrastructure documentation tests
- [ ] Fix end-to-end tests

#### Step 5: Add Missing Tests (2 hours)
- [ ] Add tests for uncovered critical paths
- [ ] Add edge case tests
- [ ] Add error handling tests

## Success Metrics

### Minimum Acceptable Coverage
- Overall: 80%
- Query handlers: 70% each
- Critical paths: 90%
- Error handling: 60%

### Test Execution Metrics
- All tests should run without errors
- No infinite recursion
- Test execution time < 30 seconds
- No flaky tests

## Risk Mitigation

### If Coverage Still Low
1. Focus on high-value paths first
2. Use coverage reports to identify gaps
3. Consider marking some tests as xfail temporarily
4. Add simple unit tests for utility functions

### If Time Constrained
1. Priority 1: Fix blockers (recursion, imports)
2. Priority 2: Mock infrastructure
3. Priority 3: Query handler tests (highest impact)
4. Priority 4: Integration tests

## Validation Approach

After each step:
1. Run `pytest --cov=src --cov-report=term-missing`
2. Check coverage increased
3. Ensure no new failures introduced
4. Commit working changes

## Expected Timeline

- Phase 1: 2-3 hours
- Phase 2: 4-5 hours  
- Phase 3: 2-3 hours
- Total: 8-11 hours

## Next Immediate Action

Start with fixing the recursion error in fuzzy_matcher tests, as this is blocking test execution.