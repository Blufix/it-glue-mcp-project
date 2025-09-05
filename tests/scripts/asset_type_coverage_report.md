
=== QUERY FLEXIBLE ASSETS TOOL TEST REPORT ===

**Overall Results:**
- Total Tests: 7
- Passed: 4
- Failed: 3
- Success Rate: 57.1%

**Asset Data Summary:**
- Total Assets Found: 0
- Asset Types Discovered: 0
- Custom Fields Validated: 0
- Validation Errors: 0

**Asset Types Found:**

**Performance Metrics:**
- Asset type stats: 1053.4ms (0 results)
- Org assets query: 2954.6ms (0 results)
- List all assets: 1611.5ms (0 results)

**Individual Test Results:**

✅ PASS Asset type statistics
   asset_types_found: 0
   duration_ms: 1053.4

✅ PASS Query Faucets flexible assets
   assets_found: 0
   unique_types: 0
   duration_ms: 2954.6

❌ FAIL Asset type filtering
   types_tested: 5
   types_with_results: 0
   success_rate: 0.0%

❌ FAIL Custom field search
   terms_tested: 5
   terms_with_results: 0
   traits_validated: 0
   success_rate: 0.0%

❌ FAIL Asset details validation
   error: No assets found in previous tests

✅ PASS List all assets
   total_assets: 0
   data_validation: passed
   duration_ms: 1611.5

✅ PASS Error handling and edge cases
   invalid_action_handled: True
   missing_param_handled: True
   nonexistent_type_suggestions: True
