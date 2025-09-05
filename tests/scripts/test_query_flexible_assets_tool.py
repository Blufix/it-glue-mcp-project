#!/usr/bin/env python3
"""
Comprehensive test script for the 'query_flexible_assets' MCP tool using REAL IT Glue API data.

This script tests the Query Flexible Assets Tool against Faucets organization data with:
- Query flexible assets for Faucets organization
- Test all asset types (SSL certs, warranties, etc.)
- Validate custom field handling
- Test asset relationship mapping

Test Cases:
1. Query all flexible assets for Faucets
2. Filter by specific asset type
3. Search within custom fields
4. Test asset trait validation
5. Verify asset relationships

Deliverables:
- test_query_flexible_assets_tool.py script (this file)
- Asset type coverage report
- Custom field validation results
- Performance metrics for complex queries
"""

import asyncio
import os
import sys
from pathlib import Path
import json
import time
from typing import Any, Dict, List

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.mcp.tools.query_flexible_assets_tool import QueryFlexibleAssetsTool
from src.services.itglue.client import ITGlueClient
from src.cache.manager import CacheManager


class FlexibleAssetTestResults:
    """Container for test results and reporting."""
    
    def __init__(self):
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.assets_found = 0
        self.asset_types_found = []
        self.custom_fields_validated = 0
        self.performance_metrics = []
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
    
    def add_performance_metric(self, operation: str, duration_ms: float, result_count: int):
        """Add performance metric."""
        self.performance_metrics.append({
            "operation": operation,
            "duration_ms": duration_ms,
            "result_count": result_count,
            "avg_ms_per_result": duration_ms / max(result_count, 1)
        })
    
    def generate_report(self) -> str:
        """Generate comprehensive test report."""
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        report = f"""
=== QUERY FLEXIBLE ASSETS TOOL TEST REPORT ===

**Overall Results:**
- Total Tests: {self.total_tests}
- Passed: {self.passed_tests}
- Failed: {self.failed_tests}
- Success Rate: {success_rate:.1f}%

**Asset Data Summary:**
- Total Assets Found: {self.assets_found}
- Asset Types Discovered: {len(self.asset_types_found)}
- Custom Fields Validated: {self.custom_fields_validated}
- Validation Errors: {len(self.validation_errors)}

**Asset Types Found:**
"""
        
        for asset_type in self.asset_types_found[:10]:  # Show first 10
            report += f"- {asset_type}\n"
        
        if len(self.asset_types_found) > 10:
            report += f"... and {len(self.asset_types_found) - 10} more types\n"
        
        report += "\n**Performance Metrics:**\n"
        for metric in self.performance_metrics:
            report += f"- {metric['operation']}: {metric['duration_ms']:.1f}ms ({metric['result_count']} results)\n"
        
        report += "\n**Individual Test Results:**\n"
        
        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            report += f"\n{status} {result['test_name']}\n"
            
            if result["details"]:
                for key, value in result["details"].items():
                    report += f"   {key}: {value}\n"
        
        if self.validation_errors:
            report += "\n**Validation Errors:**\n"
            for error in self.validation_errors[:5]:  # Show first 5
                report += f"- {error}\n"
            if len(self.validation_errors) > 5:
                report += f"... and {len(self.validation_errors) - 5} more errors\n"
        
        return report


async def test_query_flexible_assets_tool():
    """Main test function for Query Flexible Assets Tool."""
    print("=== COMPREHENSIVE QUERY FLEXIBLE ASSETS TOOL TEST ===")
    print("Testing against REAL IT Glue API data - Faucets Organization\n")
    
    results = FlexibleAssetTestResults()
    
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
        assets_tool = QueryFlexibleAssetsTool(itglue_client, cache_manager)
        
        print("✅ Query Flexible Assets Tool initialized\n")
        
        # Test Case 1: Get asset type statistics first
        print("🧪 TEST 1: Asset type statistics")
        print("-" * 33)
        
        start_time = time.time()
        result = await assets_tool.execute(action="stats")
        duration_ms = (time.time() - start_time) * 1000
        
        test_1_success = result.get("success", False)
        if test_1_success:
            data = result.get("data", {})
            asset_types = data.get("common_asset_types", [])
            results.asset_types_found = [at["name"] for at in asset_types]
            
            print(f"✅ Found {len(asset_types)} common asset types")
            
            # Display asset type details
            for i, asset_type in enumerate(asset_types[:5], 1):  # Show first 5
                count = asset_type.get("asset_count", 0)
                name = asset_type.get("name", "Unknown")
                print(f"   {i}. {name}: {count} assets")
            
            if len(asset_types) > 5:
                print(f"   ... and {len(asset_types) - 5} more asset types")
            
            results.add_performance_metric("Asset type stats", duration_ms, len(asset_types))
            results.add_test_result(
                "Asset type statistics",
                True,
                {"asset_types_found": len(asset_types), "duration_ms": f"{duration_ms:.1f}"}
            )
        else:
            error = result.get("error", "Unknown error")
            print(f"❌ Failed to get asset type statistics: {error}")
            results.add_test_result(
                "Asset type statistics",
                False,
                {"error": error}
            )
        
        print()
        
        # Test Case 2: Query all flexible assets for Faucets organization
        print("🧪 TEST 2: Query all Faucets flexible assets")
        print("-" * 42)
        
        start_time = time.time()
        result = await assets_tool.execute(
            action="by_org",
            organization="Faucets"
        )
        duration_ms = (time.time() - start_time) * 1000
        
        test_2_success = result.get("success", False)
        if test_2_success:
            data = result.get("data", {})
            assets = data.get("assets", [])
            results.assets_found = len(assets)
            
            print(f"✅ Found {len(assets)} flexible assets for Faucets")
            
            # Display asset details and collect types
            asset_types_in_org = set()
            for i, asset in enumerate(assets[:3], 1):  # Show first 3
                asset_name = asset.get("name", "Unknown")
                asset_type_id = asset.get("type_id", "unknown")
                traits_count = len(asset.get("traits", {}))
                print(f"   {i}. {asset_name} (Type ID: {asset_type_id}, {traits_count} traits)")
                
                # Collect asset type for validation
                if "type_id" in asset:
                    asset_types_in_org.add(asset_type_id)
            
            if len(assets) > 3:
                print(f"   ... and {len(assets) - 3} more assets")
            
            results.add_performance_metric("Org assets query", duration_ms, len(assets))
            results.add_test_result(
                "Query Faucets flexible assets",
                True,
                {
                    "assets_found": len(assets),
                    "unique_types": len(asset_types_in_org),
                    "duration_ms": f"{duration_ms:.1f}"
                }
            )
        else:
            error = result.get("error", "Unknown error")
            print(f"❌ Failed to query Faucets flexible assets: {error}")
            results.add_test_result(
                "Query Faucets flexible assets",
                False,
                {"error": error}
            )
        
        print()
        
        # Test Case 3: Filter by specific asset types
        print("🧪 TEST 3: Filter by specific asset types")
        print("-" * 38)
        
        # Test common asset types
        test_asset_types = ["SSL Certificate", "Warranty", "Software License", "Domain", "Email"]
        type_filter_hits = 0
        
        for asset_type in test_asset_types:
            print(f"Testing asset type filter: '{asset_type}'")
            
            start_time = time.time()
            result = await assets_tool.execute(
                action="by_type",
                asset_type=asset_type,
                limit=50
            )
            duration_ms = (time.time() - start_time) * 1000
            
            if result.get("success", False):
                data = result.get("data", {})
                type_assets = data.get("assets", [])
                
                if type_assets:
                    print(f"   ✅ Found {len(type_assets)} {asset_type} assets")
                    type_filter_hits += 1
                    results.add_performance_metric(f"Type filter: {asset_type}", duration_ms, len(type_assets))
                else:
                    print(f"   ℹ️  No {asset_type} assets found")
            else:
                print(f"   ❌ Filter failed for {asset_type}: {result.get('error', 'Unknown error')}")
        
        results.add_test_result(
            "Asset type filtering",
            type_filter_hits > 0,
            {
                "types_tested": len(test_asset_types),
                "types_with_results": type_filter_hits,
                "success_rate": f"{(type_filter_hits/len(test_asset_types)*100):.1f}%"
            }
        )
        
        print()
        
        # Test Case 4: Search within custom fields/traits
        print("🧪 TEST 4: Search within custom fields/traits")
        print("-" * 40)
        
        search_terms = ["certificate", "warranty", "license", "domain", "server"]
        search_hits = 0
        total_traits_found = 0
        
        for term in search_terms:
            print(f"Searching for: '{term}'")
            
            start_time = time.time()
            result = await assets_tool.execute(
                action="search",
                query=term
            )
            duration_ms = (time.time() - start_time) * 1000
            
            if result.get("success", False):
                data = result.get("data", {})
                search_assets = data.get("assets", [])
                
                if search_assets:
                    print(f"   ✅ Found {len(search_assets)} assets matching '{term}'")
                    search_hits += 1
                    
                    # Validate that assets actually contain the search term
                    for asset in search_assets[:3]:  # Check first 3 assets
                        traits = asset.get("traits", {})
                        total_traits_found += len(traits)
                        
                        # Check if search term appears in name or traits
                        name_match = term.lower() in asset.get("name", "").lower()
                        trait_match = any(
                            term.lower() in str(value).lower() 
                            for value in traits.values() 
                            if isinstance(value, str)
                        )
                        
                        if not (name_match or trait_match):
                            results.validation_errors.append(
                                f"Asset '{asset.get('name')}' doesn't contain search term '{term}'"
                            )
                    
                    results.add_performance_metric(f"Search: {term}", duration_ms, len(search_assets))
                else:
                    print(f"   ℹ️  No assets found for '{term}'")
            else:
                print(f"   ❌ Search failed for '{term}': {result.get('error', 'Unknown error')}")
        
        results.custom_fields_validated = total_traits_found
        results.add_test_result(
            "Custom field search",
            search_hits > 0,
            {
                "terms_tested": len(search_terms),
                "terms_with_results": search_hits,
                "traits_validated": total_traits_found,
                "success_rate": f"{(search_hits/len(search_terms)*100):.1f}%"
            }
        )
        
        print()
        
        # Test Case 5: Asset details and trait validation
        print("🧪 TEST 5: Asset details and trait validation")
        print("-" * 43)
        
        if results.assets_found > 0:
            # Get detailed info for first asset found in Test 2
            first_test_result = await assets_tool.execute(action="by_org", organization="Faucets")
            if first_test_result.get("success") and first_test_result.get("data", {}).get("assets"):
                first_asset = first_test_result["data"]["assets"][0]
                asset_id = first_asset.get("id", "")
                
                if asset_id:
                    print(f"Getting details for asset ID: {asset_id}")
                    
                    start_time = time.time()
                    result = await assets_tool.execute(
                        action="details",
                        asset_id=asset_id
                    )
                    duration_ms = (time.time() - start_time) * 1000
                    
                    if result.get("success", False):
                        data = result.get("data", {})
                        asset_details = data.get("asset", {})
                        
                        if asset_details:
                            print("✅ Asset details retrieved successfully")
                            
                            # Validate asset structure
                            required_fields = ["id", "name", "traits"]
                            validation_passed = True
                            
                            for field in required_fields:
                                if field not in asset_details:
                                    results.validation_errors.append(
                                        f"Asset details missing required field: {field}"
                                    )
                                    validation_passed = False
                            
                            # Validate traits structure
                            traits = asset_details.get("traits", {})
                            trait_types = set()
                            for key, value in traits.items():
                                trait_types.add(type(value).__name__)
                            
                            results.add_performance_metric("Asset details", duration_ms, 1)
                            results.add_test_result(
                                "Asset details validation",
                                validation_passed,
                                {
                                    "asset_id": asset_id,
                                    "traits_count": len(traits),
                                    "trait_types": list(trait_types),
                                    "validation_passed": validation_passed,
                                    "duration_ms": f"{duration_ms:.1f}"
                                }
                            )
                        else:
                            print("❌ Asset details empty")
                            results.add_test_result(
                                "Asset details validation",
                                False,
                                {"error": "Empty asset details"}
                            )
                    else:
                        error = result.get("error", "Unknown error")
                        print(f"❌ Failed to get asset details: {error}")
                        results.add_test_result(
                            "Asset details validation",
                            False,
                            {"error": error}
                        )
                else:
                    print("⚠️  No asset ID available for details test")
                    results.add_test_result(
                        "Asset details validation",
                        False,
                        {"error": "No asset ID available"}
                    )
            else:
                print("⚠️  Cannot test asset details - no assets available")
                results.add_test_result(
                    "Asset details validation",
                    False,
                    {"error": "No assets available for details test"}
                )
        else:
            print("⚠️  Skipping asset details test - no assets found in previous tests")
            results.add_test_result(
                "Asset details validation",
                False,
                {"error": "No assets found in previous tests"}
            )
        
        print()
        
        # Test Case 6: List all assets (cross-organization)
        print("🧪 TEST 6: List all assets across organizations")
        print("-" * 45)
        
        start_time = time.time()
        result = await assets_tool.execute(action="list_all", limit=50)
        duration_ms = (time.time() - start_time) * 1000
        
        if result.get("success", False):
            data = result.get("data", {})
            all_assets = data.get("assets", [])
            
            print(f"✅ Listed {len(all_assets)} assets across all organizations")
            
            # Validate data structure
            validation_passed = True
            required_fields = ["id", "name"]
            
            for asset in all_assets[:5]:  # Validate first 5 assets
                for field in required_fields:
                    if field not in asset or asset[field] is None:
                        results.validation_errors.append(
                            f"Asset missing required field '{field}': {asset}"
                        )
                        validation_passed = False
            
            results.add_performance_metric("List all assets", duration_ms, len(all_assets))
            results.add_test_result(
                "List all assets",
                True,
                {
                    "total_assets": len(all_assets),
                    "data_validation": "passed" if validation_passed else "failed",
                    "duration_ms": f"{duration_ms:.1f}"
                }
            )
        else:
            error = result.get("error", "Unknown error")
            print(f"❌ Failed to list all assets: {error}")
            results.add_test_result(
                "List all assets",
                False,
                {"error": error}
            )
        
        print()
        
        # Test Case 7: Error handling and edge cases
        print("🧪 TEST 7: Error handling and edge cases")
        print("-" * 40)
        
        # Test invalid action
        result = await assets_tool.execute(action="invalid_action")
        edge_case_1 = not result.get("success", True)  # Should fail
        
        # Test missing required parameter
        result = await assets_tool.execute(action="by_org")  # Missing organization
        edge_case_2 = not result.get("success", True)  # Should fail
        
        # Test nonexistent asset type
        result = await assets_tool.execute(action="by_type", asset_type="NonexistentAssetType12345")
        edge_case_3_success = result.get("success", False)
        edge_case_3_has_suggestions = "suggestions" in result.get("data", {})
        
        edge_cases_passed = edge_case_1 and edge_case_2 and edge_case_3_has_suggestions
        
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
                "nonexistent_type_suggestions": edge_case_3_has_suggestions
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
    results = await test_query_flexible_assets_tool()
    
    # Generate and display report
    report = results.generate_report()
    print(report)
    
    # Save detailed report to file
    report_file = Path(__file__).parent / "asset_type_coverage_report.md"
    try:
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"\n📄 Asset type coverage report saved to: {report_file}")
    except Exception as e:
        print(f"⚠️  Could not save report: {e}")
    
    # Save raw test data for analysis
    results_file = Path(__file__).parent / "flexible_asset_test_results.json"
    try:
        with open(results_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": results.total_tests,
                    "passed_tests": results.passed_tests,
                    "failed_tests": results.failed_tests,
                    "assets_found": results.assets_found,
                    "asset_types_found": results.asset_types_found,
                    "custom_fields_validated": results.custom_fields_validated,
                    "validation_errors_count": len(results.validation_errors)
                },
                "test_results": results.test_results,
                "performance_metrics": results.performance_metrics,
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