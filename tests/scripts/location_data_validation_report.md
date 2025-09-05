
=== QUERY LOCATIONS TOOL TEST REPORT ===

**Overall Results:**
- Total Tests: 6
- Passed: 6
- Failed: 0
- Success Rate: 100.0%

**Location Data Summary:**
- Total Locations Found: 3
- Geographic Search Accuracy: 50.0%
- Validation Errors: 0

**Individual Test Results:**

✅ PASS List Faucets locations
   locations_found: 3
   organization_resolved: True

✅ PASS Geographic city search
   cities_tested: 4
   cities_with_results: 2
   accuracy: 50.0%

✅ PASS Location name search
   search_term: Faucets Ltd [Pontnewynydd]
   found: True

✅ PASS General location search
   terms_tested: 4
   terms_with_results: 3
   success_rate: 75.0%

✅ PASS List all locations
   total_locations: 100
   data_validation: passed

✅ PASS Error handling and edge cases
   invalid_action_handled: True
   missing_param_handled: True
   nonexistent_org_handled: True
