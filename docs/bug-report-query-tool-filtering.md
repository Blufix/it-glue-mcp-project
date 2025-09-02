# Bug Report: Query Tool Organization Filtering Issue

## Issue Summary
The Query Tool is not properly filtering results by organization when the `company` parameter is provided. Results from all organizations are returned instead of just the specified organization.

## Severity: **HIGH** 🔴

## Details

### Expected Behavior
When querying with `company="Faucets"`, the tool should only return results from the Faucets organization.

### Actual Behavior
The tool returns results from multiple organizations including:
- Sophos
- VM Ware
- IrvinGQ Ltd
- BAWSO Women's Aid
- Echa Microbiology Ltd

### Example Query
```python
result = await query(
    query="What are the network configurations for Faucets?",
    company="Faucets"
)
```

### Actual Results Received
Results included items from various organizations:
- VMWare vSphere (VM Ware org)
- Brother HL-5270DN printer (BAWSO Women's Aid)
- Network points layout (Echa Microbiology Ltd)

## Impact
- **Security Risk**: Users might see data from organizations they shouldn't have access to
- **Data Leakage**: Cross-organization data exposure
- **Compliance Issue**: Potential GDPR/privacy violations
- **User Experience**: Incorrect and confusing results

## Root Cause Analysis
The issue appears to be in the query engine's implementation. The `company` parameter is being passed to `query_engine.process_query()` but is not being used to filter the search results.

## Suggested Fix
1. Ensure the query engine properly filters results by organization ID/name
2. Add organization validation before returning results
3. Implement proper company-based access control

## Test Coverage Added
The test script has been updated to:
- Check if all returned results belong to the specified organization
- Log warnings when results from other organizations are found
- Mark tests as failed if cross-organization data is returned

## Temporary Workaround
Until fixed, users should:
1. Manually filter results client-side
2. Include organization name explicitly in the query text
3. Use the search tool with explicit filters instead

## Files Affected
- `/src/mcp/server.py` - Query tool implementation
- `/src/query/query_engine.py` - Query processing logic (needs investigation)
- `/tests/scripts/test_query_tool.py` - Test updated to catch this issue

## Priority for Fix
**IMMEDIATE** - This is a critical security and data isolation issue that needs to be fixed before production deployment.

---
*Reported: 2025-09-02*  
*Found during: MCP Tool Testing with Faucets Organization*