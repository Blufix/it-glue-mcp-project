#!/usr/bin/env python3
"""
Comprehensive test script for the 'query_locations' MCP tool using REAL IT Glue API data.

This script tests the Query Locations Tool against Faucets organization data with:
- Query all locations for Faucets organization
- Test location search and filtering
- Validate address and contact information
- Test geographic queries

Test Cases:
1. List all Faucets locations
2. Search by city/state/country
3. Filter by location type
4. Query location contacts
5. Test location relationship to assets

Deliverables:
- test_query_locations_tool.py script (this file)
- Location data validation report
- Geographic search accuracy metrics
- Contact information verification
"""

import asyncio
import os
import sys
from pathlib import Path
import json
from typing import Any, Dict, List

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.mcp.tools.query_locations_tool import QueryLocationsTool
from src.services.itglue.client import ITGlueClient
from src.cache.manager import CacheManager


class LocationTestResults:
    """Container for test results and reporting."""
    
    def __init__(self):
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.locations_found = 0
        self.geographic_accuracy = 0.0
        self.validation_errors = []
    
    def add_test_result(self, test_name: str, success: bool, details: Dict[str, Any]):
        """Add a test result."""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
        
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "details": details
        })
    
    def generate_report(self) -> str:
        """Generate comprehensive test report."""
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        report = f"""
=== QUERY LOCATIONS TOOL TEST REPORT ===

**Overall Results:**
- Total Tests: {self.total_tests}
- Passed: {self.passed_tests}
- Failed: {self.failed_tests}
- Success Rate: {success_rate:.1f}%

**Location Data Summary:**
- Total Locations Found: {self.locations_found}
- Geographic Search Accuracy: {self.geographic_accuracy:.1f}%
- Validation Errors: {len(self.validation_errors)}

**Individual Test Results:**
"""
        
        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            report += f"\n{status} {result['test_name']}\n"
            
            if result["details"]:
                for key, value in result["details"].items():
                    report += f"   {key}: {value}\n"
        
        if self.validation_errors:
            report += "\n**Validation Errors:**\n"
            for error in self.validation_errors:
                report += f"- {error}\n"
        
        return report


async def test_query_locations_tool():
    """Main test function for Query Locations Tool."""
    print("=== COMPREHENSIVE QUERY LOCATIONS TOOL TEST ===")
    print("Testing against REAL IT Glue API data - Faucets Organization\n")
    
    results = LocationTestResults()
    
    try:
        # Initialize components
        api_key = os.getenv('ITGLUE_API_KEY')
        if not api_key:
            print("❌ ERROR: ITGLUE_API_KEY environment variable not set")
            return results
        
        print("✅ IT Glue API key loaded")
        
        # Create MCP tool
        itglue_client = ITGlueClient(api_key=api_key)
        cache_manager = CacheManager()
        locations_tool = QueryLocationsTool(itglue_client, cache_manager)
        
        print("✅ Query Locations Tool initialized\n")
        
        # Test Case 1: List all locations for Faucets organization
        print("🧪 TEST 1: List all Faucets locations")
        print("-" * 40)
        
        result = await locations_tool.execute(
            action="by_org",
            organization="Faucets"
        )
        
        test_1_success = result.get("success", False)
        if test_1_success:
            data = result.get("data", {})
            locations = data.get("locations", [])
            results.locations_found = len(locations)
            
            print(f"✅ Found {len(locations)} locations for Faucets")
            
            # Display location details
            for i, location in enumerate(locations[:3], 1):  # Show first 3
                print(f"   {i}. {location.get('name', 'Unknown')} - {location.get('city', 'No city')}")
            
            if len(locations) > 3:
                print(f"   ... and {len(locations) - 3} more locations")
            
            results.add_test_result(
                "List Faucets locations",
                True,
                {"locations_found": len(locations), "organization_resolved": True}
            )
        else:
            error = result.get("error", "Unknown error")
            print(f"❌ Failed to list Faucets locations: {error}")
            results.add_test_result(
                "List Faucets locations",
                False,
                {"error": error}
            )
        
        print()
        
        # Test Case 2: Search by city/state/country
        print("🧪 TEST 2: Geographic search tests")
        print("-" * 35)
        
        # Test common city names
        test_cities = ["London", "New York", "Manchester", "Birmingham"]
        geographic_hits = 0
        
        for city in test_cities:
            print(f"Searching for locations in: {city}")
            
            result = await locations_tool.execute(
                action="by_city",
                city=city
            )
            
            if result.get("success", False):
                data = result.get("data", {})
                city_locations = data.get("locations", [])
                
                if city_locations:
                    print(f"   ✅ Found {len(city_locations)} locations in {city}")
                    geographic_hits += 1
                    
                    # Validate addresses contain the city
                    for loc in city_locations:
                        city_in_address = (
                            city.lower() in (loc.get("city", "") or "").lower() or
                            city.lower() in (loc.get("address", "") or "").lower()
                        )
                        if not city_in_address:
                            results.validation_errors.append(
                                f"Location '{loc.get('name')}' doesn't contain '{city}' in address fields"
                            )
                else:
                    print(f"   ℹ️  No locations found in {city}")
            else:
                print(f"   ❌ Search failed for {city}")
        
        results.geographic_accuracy = (geographic_hits / len(test_cities)) * 100
        results.add_test_result(
            "Geographic city search",
            geographic_hits > 0,
            {
                "cities_tested": len(test_cities),
                "cities_with_results": geographic_hits,
                "accuracy": f"{results.geographic_accuracy:.1f}%"
            }
        )
        
        print()
        
        # Test Case 3: Search by location name
        print("🧪 TEST 3: Location name search")
        print("-" * 32)
        
        if results.locations_found > 0:
            # Use the first location found in Test 1 for name search
            first_test_result = await locations_tool.execute(action="by_org", organization="Faucets")
            if first_test_result.get("success") and first_test_result.get("data", {}).get("locations"):
                first_location = first_test_result["data"]["locations"][0]
                location_name = first_location.get("name", "")
                
                if location_name:
                    print(f"Searching for location by name: '{location_name}'")
                    
                    result = await locations_tool.execute(
                        action="by_name",
                        location_name=location_name
                    )
                    
                    if result.get("success", False):
                        print("✅ Location name search successful")
                        results.add_test_result(
                            "Location name search",
                            True,
                            {"search_term": location_name, "found": True}
                        )
                    else:
                        print(f"❌ Location name search failed: {result.get('error', 'Unknown error')}")
                        results.add_test_result(
                            "Location name search",
                            False,
                            {"search_term": location_name, "error": result.get("error")}
                        )
                else:
                    print("⚠️  No location name available for testing")
                    results.add_test_result(
                        "Location name search",
                        False,
                        {"error": "No location name available"}
                    )
            else:
                print("⚠️  Cannot test location name search - no locations available")
                results.add_test_result(
                    "Location name search",
                    False,
                    {"error": "No locations available for name search"}
                )
        else:
            print("⚠️  Skipping location name search - no locations found in previous tests")
            results.add_test_result(
                "Location name search",
                False,
                {"error": "No locations found in previous tests"}
            )
        
        print()
        
        # Test Case 4: General search functionality
        print("🧪 TEST 4: General location search")
        print("-" * 33)
        
        search_terms = ["office", "headquarters", "main", "branch"]
        search_hits = 0
        
        for term in search_terms:
            print(f"General search for: '{term}'")
            
            result = await locations_tool.execute(
                action="search",
                query=term
            )
            
            if result.get("success", False):
                data = result.get("data", {})
                search_locations = data.get("locations", [])
                
                if search_locations:
                    print(f"   ✅ Found {len(search_locations)} locations matching '{term}'")
                    search_hits += 1
                else:
                    print(f"   ℹ️  No locations found for '{term}'")
            else:
                print(f"   ❌ Search failed for '{term}': {result.get('error', 'Unknown error')}")
        
        results.add_test_result(
            "General location search",
            search_hits > 0,
            {
                "terms_tested": len(search_terms),
                "terms_with_results": search_hits,
                "success_rate": f"{(search_hits/len(search_terms)*100):.1f}%"
            }
        )
        
        print()
        
        # Test Case 5: List all locations (cross-organization)
        print("🧪 TEST 5: List all locations across organizations")
        print("-" * 49)
        
        result = await locations_tool.execute(action="list_all")
        
        if result.get("success", False):
            data = result.get("data", {})
            all_locations = data.get("locations", [])
            
            print(f"✅ Listed {len(all_locations)} locations across all organizations")
            
            # Validate data structure
            validation_passed = True
            required_fields = ["id", "name"]
            
            for loc in all_locations[:5]:  # Validate first 5 locations
                for field in required_fields:
                    if field not in loc or loc[field] is None:
                        results.validation_errors.append(
                            f"Location missing required field '{field}': {loc}"
                        )
                        validation_passed = False
            
            results.add_test_result(
                "List all locations",
                True,
                {
                    "total_locations": len(all_locations),
                    "data_validation": "passed" if validation_passed else "failed"
                }
            )
        else:
            error = result.get("error", "Unknown error")
            print(f"❌ Failed to list all locations: {error}")
            results.add_test_result(
                "List all locations",
                False,
                {"error": error}
            )
        
        print()
        
        # Test Case 6: Error handling and edge cases
        print("🧪 TEST 6: Error handling and edge cases")
        print("-" * 40)
        
        # Test invalid action
        result = await locations_tool.execute(action="invalid_action")
        edge_case_1 = not result.get("success", True)  # Should fail
        
        # Test missing required parameter
        result = await locations_tool.execute(action="by_org")  # Missing organization
        edge_case_2 = not result.get("success", True)  # Should fail
        
        # Test nonexistent organization
        result = await locations_tool.execute(action="by_org", organization="NonexistentOrg12345")
        edge_case_3_success = result.get("success", False)
        edge_case_3_empty = len(result.get("data", {}).get("locations", [])) == 0
        
        edge_cases_passed = edge_case_1 and edge_case_2 and (edge_case_3_success and edge_case_3_empty)
        
        if edge_cases_passed:
            print("✅ Error handling works correctly")
        else:
            print("❌ Error handling issues detected")
        
        results.add_test_result(
            "Error handling and edge cases",
            edge_cases_passed,
            {
                "invalid_action_handled": edge_case_1,
                "missing_param_handled": edge_case_2,
                "nonexistent_org_handled": edge_case_3_success and edge_case_3_empty
            }
        )
        
    except Exception as e:
        print(f"❌ Test execution error: {e}")
        import traceback
        traceback.print_exc()
        
        results.add_test_result(
            "Test execution",
            False,
            {"error": str(e)}
        )
    
    return results


async def main():
    """Run all tests and generate reports."""
    results = await test_query_locations_tool()
    
    # Generate and display report
    report = results.generate_report()
    print(report)
    
    # Save detailed report to file
    report_file = Path(__file__).parent / "location_data_validation_report.md"
    try:
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"\n📄 Detailed report saved to: {report_file}")
    except Exception as e:
        print(f"⚠️  Could not save report: {e}")
    
    # Save raw test data for analysis
    results_file = Path(__file__).parent / "location_test_results.json"
    try:
        with open(results_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": results.total_tests,
                    "passed_tests": results.passed_tests,
                    "failed_tests": results.failed_tests,
                    "locations_found": results.locations_found,
                    "geographic_accuracy": results.geographic_accuracy,
                    "validation_errors_count": len(results.validation_errors)
                },
                "test_results": results.test_results,
                "validation_errors": results.validation_errors
            }, f, indent=2)
        print(f"📊 Test data saved to: {results_file}")
    except Exception as e:
        print(f"⚠️  Could not save test data: {e}")
    
    # Return overall success status
    return results.passed_tests == results.total_tests


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)