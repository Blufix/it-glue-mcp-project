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

### 2. Search Tool Test ⏳ PENDING
**Script**: `/tests/scripts/test_search_tool.py`  
**Status**: Not yet created  

### 3. Health Tool Test ⏳ PENDING
**Script**: `/tests/scripts/test_health_tool.py`  
**Status**: Not yet created  

### 4. Query Organizations Tool Test ⏳ PENDING
**Script**: `/tests/scripts/test_query_organizations_tool.py`  
**Status**: Not yet created  

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