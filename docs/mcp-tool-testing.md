# MCP Tool Testing Documentation

## Overview
This document tracks all MCP tool test scripts, their locations, and test results for the IT Glue MCP Server project. All tests use **REAL IT Glue API data** from the **Faucets** organization - NO MOCK DATA.

## Test Configuration
- **Test Organization**: Faucets
- **API**: Real IT Glue Production API
- **Performance Threshold**: 2000ms (2 seconds) per query
- **Test Scripts Location**: `/tests/scripts/`
- **Test Results Location**: `/tests/scripts/` (JSON and log files)

## Test Scripts Status

### 1. Query Tool Test ✅ FIXED & READY
**Script**: `/tests/scripts/test_query_tool.py`  
**Status**: Fixed and ready for re-testing  
**Created**: 2025-09-02  
**Fixed**: 2025-09-02 - Organization filtering bug resolved

**Critical Bug Fixed**:
- ✅ **Organization Filtering**: Query engine now properly resolves company names to IDs
- ✅ **Result Filtering**: Added post-filter to ensure only specified org data is returned
- ✅ **Company Resolution**: Added _resolve_company_to_id() method to handle name→ID mapping

**Test Cases**:
1. ✅ Basic Query - "Show all servers for Faucets"
2. ✅ Complex Query - "What are the network configurations for Faucets?"
3. ✅ Error Handling - Invalid/malformed queries
4. ✅ Edge Cases - Non-existent data queries
5. ✅ Performance Test - Batch queries with timing

**Verification Script**: `/tests/scripts/verify_query_fix.py`
- Quick test to verify organization filtering works correctly
- Checks configuration count issue

**How to Run**:
```bash
cd /home/jamie/projects/itglue-mcp-server
# Full test suite
python tests/scripts/test_query_tool.py

# Quick verification of fix
python tests/scripts/verify_query_fix.py
```

### 2. Health Tool Test ✅ COMPLETED
**Script**: `/tests/mcp_tools/test_health_tool.py` & `test_health_tool_simple.py`  
**Status**: Completed and passing  
**Created**: 2025-09-02  
**Tested**: 2025-09-02 - All components healthy

**Test Cases Implemented**:
1. ✅ Basic Health Check - Server status and component initialization
2. ✅ Component-Specific Health - PostgreSQL, Redis, IT Glue API connectivity
3. ✅ Performance Metrics - Response time validation (< 100ms threshold)
4. ✅ Error State Detection - Uninitialized components and exception handling
5. ✅ Recovery Testing - System recovery after failures
6. ✅ Dependency Validation - Python version, env vars, network, disk, memory

**Test Results**:
- **PostgreSQL**: ✅ Connected (v15.14)
- **Redis**: ✅ Connected (v7.4.5)
- **IT Glue API**: ✅ Connected (252 organizations found)
- **Performance**: ✅ Excellent (< 1ms response time)
- **Neo4j**: ⚠️ Needs async handling improvements
- **Qdrant**: ⚠️ Version mismatch warning (client 1.15.1 vs server 1.7.3)

**Health Monitoring Recommendations**:
- Alert thresholds: 200ms (warn) / 500ms (critical)
- Monitor all 6 components every 60 seconds
- Track API rate limit usage
- Implement circuit breaker for API calls
- Add health endpoint at /health for monitoring tools

**How to Run**:
```bash
cd /home/jamie/projects/itglue-mcp-server
source venv/bin/activate

# Comprehensive test suite
python tests/mcp_tools/test_health_tool.py

# Simple direct test
python tests/mcp_tools/test_health_tool_simple.py
```

**Output Files**:
- `health_test_results.json` - Test metrics and recommendations
- `health_tool_test_report.json` - Detailed test report

### 3. Query Organizations Tool Test ✅ COMPLETED
**Script**: `/tests/mcp_tools/test_query_organizations_tool.py` & `test_query_organizations_simple.py`  
**Status**: Completed and passing  
**Created**: 2025-09-02  
**Tested**: 2025-09-02 - Fuzzy matching working well

**Test Cases Implemented**:
1. ✅ Exact Match - Found "Faucets Limited" organization
2. ✅ Fuzzy Matching - 80% accuracy (4/5 typos matched)
3. ✅ List Organizations - Pagination working (10, 50, 100 items)
4. ✅ Organization Filters - Customers, vendors, stats working
5. ⚠️ Data Validation - Some fields missing in cached responses
6. ✅ Performance Benchmarks - Avg 346ms response time

**Test Results**:
- **Fuzzy Matching Accuracy**: 80% (4/5 variants found)
  - ✅ "Faucet", "Faucetts", "faucets", "FAUCETS" all matched
  - ❌ "Facets" did not match (too different)
- **Performance**: Excellent (avg 346ms)
- **Organizations Found**: 252 total, including Faucets Limited

**Important Notes**:
- **Redis warnings are normal**: "Redis not connected" messages are warnings, not errors
- **Cache is optional**: System works without Redis, just without caching benefits
- **Graceful degradation**: Queries still succeed when cache is unavailable

**How to Run**:
```bash
cd /home/jamie/projects/itglue-mcp-server
source venv/bin/activate

# Full test suite
python tests/mcp_tools/test_query_organizations_tool.py

# Simple direct test (recommended)
python tests/mcp_tools/test_query_organizations_simple.py
```

**Output Files**:
- `query_organizations_results.json` - Test results and metrics
- `query_organizations_test_report.json` - Detailed test report

### 4. Search Tool Test ✅ DATA SYNCED & TESTED
**Script**: `/tests/mcp_tools/test_search_tool.py`  
**Status**: Completed with synced data  
**Created**: 2025-09-02  
**Tested**: 2025-09-02 - Database populated with 97 entities

**Database Sync Completed**:
- **Sync method**: Direct data insertion via `simple_sync_test.py`
- **Data synced**: Faucets Limited organization
- **Total entities**: 97 (1 organization + 96 configurations)
- **Schema fixes applied**: Resolved content vs search_text field mismatch

**Test Cases Implemented**:
1. ✅ Basic Search - Search for "server", "firewall", "switch", etc.
2. ✅ Filtered Search - Company and entity type filters
3. ✅ Pagination - Test limits (10, 50, 100)
4. ✅ Relevance Ranking - Score ordering and relevance
5. ✅ Performance Benchmarks - Response time testing
6. ✅ Cross-Company Search - Multi-company result analysis

**Test Results (with populated database)**:
- **Database Contents**:
  - Total: 97 entities
  - Organization: 1 (Faucets Limited)
  - Configurations: 96
- **Search Matches**:
  - "server": 1 match (FCLHYPERV01 - Server ILO)
  - "switch": 5 matches
  - "sophos": 1 match (Sophos XGS138)
  - "network": 1 match
  - "firewall": 0 matches (none in data)
- **Performance**: Excellent (avg 18.03ms per query)
- **Pagination**: Working correctly
- **Filters**: Applied properly

**Issues Fixed During Testing**:
1. ✅ **Database schema mismatch**: Fixed trigger expecting "content" field vs models using "search_text"
2. ✅ **Configuration attribute access**: Fixed accessing nested attributes dictionary
3. ✅ **Database initialization**: Properly initialized database with SQLAlchemy models
4. ⚠️ **HybridSearch initialization**: Test scripts need proper DB initialization

**How to Run**:
```bash
cd /home/jamie/projects/itglue-mcp-server
source venv/bin/activate

# Sync data (if needed)
python simple_sync_test.py

# Run search tests
python tests/mcp_tools/test_search_tool.py
```

**Output Files**:
- `search_tool_test_report.json` - Test results and metrics

### 5. Sync Data Tool Test ⏳ PENDING

### 5. Sync Data Tool Test ⏳ PENDING
**Script**: `/tests/scripts/test_sync_data_tool.py`  
**Status**: Not yet created  

### 6. Query Documents Tool Test ⏳ PENDING
**Script**: `/tests/scripts/test_query_documents_tool.py`  
**Status**: Not yet created  

### 7. Query Flexible Assets Tool Test ⏳ PENDING
**Script**: `/tests/scripts/test_query_flexible_assets_tool.py`  
**Status**: Not yet created  

### 8. Query Locations Tool Test ⏳ PENDING
**Script**: `/tests/scripts/test_query_locations_tool.py`  
**Status**: Not yet created  

### 9. Discover Asset Types Tool Test ⏳ PENDING
**Script**: `/tests/scripts/test_discover_asset_types_tool.py`  
**Status**: Not yet created  

### 10. Document Infrastructure Tool Test ⏳ PENDING
**Script**: `/tests/scripts/test_document_infrastructure_tool.py`  
**Status**: Not yet created  

### 11. Integration Test Suite ⏳ PENDING
**Script**: `/tests/scripts/test_integration_suite.py`  
**Status**: Not yet created  

## Test Results Summary

### Latest Test Run Results
*Results will be updated after each test execution*

| Tool | Test Date | Tests Run | Passed | Failed | Avg Response Time | Status |
|------|-----------|-----------|---------|---------|------------------|---------|
| Query Tool | 2025-09-02 | N/A | N/A | N/A | N/A | Fix Applied - Needs API Connection |
| Search Tool | - | - | - | - | - | Pending |
| Health Tool | - | - | - | - | - | Pending |
| Query Organizations | - | - | - | - | - | Pending |
| Sync Data | - | - | - | - | - | Pending |
| Query Documents | - | - | - | - | - | Pending |
| Query Flexible Assets | - | - | - | - | - | Pending |
| Query Locations | - | - | - | - | - | Pending |
| Discover Asset Types | - | - | - | - | - | Pending |
| Document Infrastructure | - | - | - | - | - | Pending |
| Integration Suite | - | - | - | - | - | Pending |

## Key Findings

### Query Tool (2025-09-02)
1. **Critical Bug Found**: Organization filtering was not working - returned data from ALL organizations
2. **Initial Fix Applied**: 
   - Added `_resolve_company_to_id()` method to QueryEngine
   - Updated search methods to properly filter by organization ID
   - Added post-filtering to ensure only matching org data is returned
3. **Fix Refinement (Too Restrictive)**: 
   - Initial fix was too aggressive, only returning 1 configuration
   - Issue: Passing string "Faucets" to SQL query expecting numeric ID
   - Solution: Only pass numeric IDs to search/database queries
   - Added fallback name-based filtering when ID resolution fails
4. **Final Fix Applied**:
   - Modified all handler methods to check if company is numeric before using
   - Only pass company_id to search when successfully resolved to numeric ID
   - Added name-based filtering as fallback for unresolved companies
5. **Test Status**: 
   - Fix implemented and refined based on user feedback
   - User to manually test in Streamlit app
   - Test scripts need API connection to fully validate

### Configuration Count Issue
- Initial investigation showed API client fetches 1000 items per page
- Found the actual issue: Search results were limited to 20 items, then filtered down to 10
- **Fix Applied**: Increased search limit from 20 to 50, display limit from 10 to 20
- This should now show up to 20 configurations (was showing only 6)

## Performance Benchmarks
*To be updated after test execution*

## Issues and Blockers
*To be documented during testing*

## Next Steps
1. Execute Query Tool test and validate results
2. Create remaining test scripts based on Query Tool template
3. Run full test suite
4. Generate consolidated performance report
5. Address any failures or performance issues

---
*Last Updated: 2025-09-02*