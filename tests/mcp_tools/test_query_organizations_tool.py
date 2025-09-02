#!/usr/bin/env python3
"""
Comprehensive test script for the 'query_organizations' MCP tool.

This script tests the query_organizations tool with REAL IT Glue API data,
focusing on the Faucets organization with fuzzy matching and validation.
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from difflib import SequenceMatcher

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.mcp.server import ITGlueMCPServer
from src.config.settings import settings
from src.services.itglue import ITGlueClient


class QueryOrganizationsToolTester:
    """Comprehensive test suite for query_organizations tool."""
    
    def __init__(self):
        """Initialize test suite."""
        self.server = ITGlueMCPServer()
        self.test_results = []
        self.performance_metrics = {}
        self.faucets_data = None
        
    async def run_all_tests(self):
        """Run complete test suite."""
        print("=" * 80)
        print("IT GLUE MCP SERVER - QUERY ORGANIZATIONS TOOL TEST")
        print("=" * 80)
        print(f"Test Started: {datetime.now().isoformat()}\n")
        
        # Initialize server
        await self.server._initialize_components()
        
        # Run test cases
        await self.test_exact_match()
        await self.test_fuzzy_matching()
        await self.test_list_all_organizations()
        await self.test_organization_filters()
        await self.test_validate_organization_data()
        await self.test_performance_benchmarks()
        
        # Generate report
        self.generate_test_report()
        
        # Cleanup
        if self.server.itglue_client:
            await self.server.itglue_client.disconnect()
    
    async def test_exact_match(self):
        """Test Case 1: Exact match query for 'Faucets' organization."""
        print("\n" + "=" * 60)
        print("TEST CASE 1: Exact Match - 'Faucets'")
        print("=" * 60)
        
        try:
            # Test exact name "Faucets"
            start_time = time.time()
            
            # Find the query_organizations tool
            org_tool = None
            for tool in self.server.server.tools:
                if tool.name == "query_organizations":
                    org_tool = tool
                    break
            
            if not org_tool:
                raise Exception("query_organizations tool not found")
            
            # Call with exact match
            result = await org_tool.handler(
                action="find",
                name="Faucets"
            )
            
            elapsed = (time.time() - start_time) * 1000
            
            if result.get("success"):
                org = result.get("organization")
                if org:
                    print(f"✅ Found organization: {org.get('name')}")
                    print(f"   ID: {org.get('id')}")
                    print(f"   Type: {org.get('organization_type')}")
                    print(f"   Response time: {elapsed:.2f}ms")
                    
                    # Store for later validation
                    self.faucets_data = org
                else:
                    print(f"❌ Organization not found")
            else:
                print(f"❌ Query failed: {result.get('error')}")
            
            self.performance_metrics["exact_match"] = elapsed
            
            self.test_results.append({
                "test": "Exact Match - 'Faucets'",
                "status": "PASSED" if result.get("success") else "FAILED",
                "response_time_ms": elapsed,
                "found": bool(result.get("organization"))
            })
            
            # Also test with full name "Faucets Limited"
            print("\nTesting with full name 'Faucets Limited'...")
            start_time = time.time()
            
            result2 = await org_tool.handler(
                action="find",
                name="Faucets Limited"
            )
            
            elapsed2 = (time.time() - start_time) * 1000
            
            if result2.get("success") and result2.get("organization"):
                print(f"✅ Found with full name: {result2['organization'].get('name')}")
                print(f"   Response time: {elapsed2:.2f}ms")
            else:
                print(f"⚠️ Not found with full name")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            self.test_results.append({
                "test": "Exact Match",
                "status": "FAILED",
                "error": str(e)
            })
    
    async def test_fuzzy_matching(self):
        """Test Case 2: Fuzzy match with typos."""
        print("\n" + "=" * 60)
        print("TEST CASE 2: Fuzzy Matching")
        print("=" * 60)
        
        # Test variations
        typo_variations = [
            "Faucet",      # Missing 's'
            "Faucetts",    # Extra 't'
            "Facets",      # Common typo
            "Faucets Ltd", # Abbreviated
            "faucets",     # Lowercase
            "FAUCETS"      # Uppercase
        ]
        
        org_tool = None
        for tool in self.server.server.tools:
            if tool.name == "query_organizations":
                org_tool = tool
                break
        
        if not org_tool:
            print("❌ Tool not found")
            return
        
        fuzzy_results = []
        
        for variant in typo_variations:
            try:
                start_time = time.time()
                
                result = await org_tool.handler(
                    action="find",
                    name=variant
                )
                
                elapsed = (time.time() - start_time) * 1000
                
                found = result.get("success") and result.get("organization")
                org_name = result.get("organization", {}).get("name") if found else None
                
                # Calculate similarity score
                similarity = 0
                if org_name:
                    similarity = SequenceMatcher(None, variant.lower(), "faucets limited".lower()).ratio()
                
                print(f"   '{variant}': {'✅ Found' if found else '❌ Not found'} ({elapsed:.2f}ms)")
                if found:
                    print(f"      Matched: {org_name} (similarity: {similarity:.2%})")
                
                fuzzy_results.append({
                    "variant": variant,
                    "found": found,
                    "matched_name": org_name,
                    "similarity": similarity,
                    "response_time_ms": elapsed
                })
                
            except Exception as e:
                print(f"   '{variant}': ❌ Error - {e}")
                fuzzy_results.append({
                    "variant": variant,
                    "found": False,
                    "error": str(e)
                })
        
        # Calculate fuzzy matching accuracy
        success_count = sum(1 for r in fuzzy_results if r.get("found"))
        accuracy = (success_count / len(typo_variations)) * 100
        
        print(f"\nFuzzy Matching Accuracy: {accuracy:.1f}% ({success_count}/{len(typo_variations)})")
        
        self.test_results.append({
            "test": "Fuzzy Matching",
            "status": "PASSED" if accuracy >= 50 else "FAILED",
            "accuracy_percent": accuracy,
            "details": fuzzy_results
        })
    
    async def test_list_all_organizations(self):
        """Test Case 3: List all organizations with pagination."""
        print("\n" + "=" * 60)
        print("TEST CASE 3: List All Organizations")
        print("=" * 60)
        
        org_tool = None
        for tool in self.server.server.tools:
            if tool.name == "query_organizations":
                org_tool = tool
                break
        
        if not org_tool:
            print("❌ Tool not found")
            return
        
        try:
            # Test different page sizes
            page_sizes = [10, 50, 100]
            
            for limit in page_sizes:
                start_time = time.time()
                
                result = await org_tool.handler(
                    action="list",
                    limit=limit
                )
                
                elapsed = (time.time() - start_time) * 1000
                
                if result.get("success"):
                    orgs = result.get("organizations", [])
                    total = result.get("total_count", len(orgs))
                    
                    print(f"\n   Limit {limit}:")
                    print(f"      Returned: {len(orgs)} organizations")
                    print(f"      Total available: {total}")
                    print(f"      Response time: {elapsed:.2f}ms")
                    
                    # Check if Faucets is in the list
                    faucets_found = any(
                        "faucets" in org.get("name", "").lower() 
                        for org in orgs
                    )
                    
                    if faucets_found:
                        print(f"      ✅ Faucets found in results")
                    
                    self.performance_metrics[f"list_{limit}"] = elapsed
                else:
                    print(f"   Limit {limit}: ❌ Failed - {result.get('error')}")
            
            self.test_results.append({
                "test": "List All Organizations",
                "status": "PASSED",
                "performance": {
                    f"limit_{k}": v 
                    for k, v in self.performance_metrics.items() 
                    if f"list_{k}" in self.performance_metrics
                }
            })
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            self.test_results.append({
                "test": "List All Organizations",
                "status": "FAILED",
                "error": str(e)
            })
    
    async def test_organization_filters(self):
        """Test Case 4: Filter by organization type/status."""
        print("\n" + "=" * 60)
        print("TEST CASE 4: Organization Filters")
        print("=" * 60)
        
        org_tool = None
        for tool in self.server.server.tools:
            if tool.name == "query_organizations":
                org_tool = tool
                break
        
        if not org_tool:
            print("❌ Tool not found")
            return
        
        filter_tests = []
        
        try:
            # Test customers filter
            print("\nTesting 'customers' action...")
            start_time = time.time()
            
            result = await org_tool.handler(
                action="customers",
                limit=50
            )
            
            elapsed = (time.time() - start_time) * 1000
            
            if result.get("success"):
                customers = result.get("organizations", [])
                print(f"   ✅ Found {len(customers)} customers ({elapsed:.2f}ms)")
                
                # Check if they're all customers
                all_customers = all(
                    org.get("organization_type", "").lower() in ["customer", "client"]
                    for org in customers[:10]  # Check first 10
                )
                
                if all_customers:
                    print(f"      ✅ All are customer type")
                
                filter_tests.append({
                    "filter": "customers",
                    "count": len(customers),
                    "success": True,
                    "response_time_ms": elapsed
                })
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                filter_tests.append({
                    "filter": "customers",
                    "success": False,
                    "error": result.get("error")
                })
            
            # Test vendors filter
            print("\nTesting 'vendors' action...")
            start_time = time.time()
            
            result = await org_tool.handler(
                action="vendors",
                limit=50
            )
            
            elapsed = (time.time() - start_time) * 1000
            
            if result.get("success"):
                vendors = result.get("organizations", [])
                print(f"   ✅ Found {len(vendors)} vendors ({elapsed:.2f}ms)")
                
                filter_tests.append({
                    "filter": "vendors",
                    "count": len(vendors),
                    "success": True,
                    "response_time_ms": elapsed
                })
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                filter_tests.append({
                    "filter": "vendors",
                    "success": False,
                    "error": result.get("error")
                })
            
            # Test stats action
            print("\nTesting 'stats' action...")
            start_time = time.time()
            
            result = await org_tool.handler(action="stats")
            
            elapsed = (time.time() - start_time) * 1000
            
            if result.get("success"):
                stats = result.get("stats", {})
                print(f"   ✅ Got statistics ({elapsed:.2f}ms)")
                print(f"      Total: {stats.get('total', 0)}")
                print(f"      Customers: {stats.get('customers', 0)}")
                print(f"      Vendors: {stats.get('vendors', 0)}")
                print(f"      Internal: {stats.get('internal', 0)}")
                
                filter_tests.append({
                    "filter": "stats",
                    "data": stats,
                    "success": True,
                    "response_time_ms": elapsed
                })
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                filter_tests.append({
                    "filter": "stats",
                    "success": False,
                    "error": result.get("error")
                })
            
            self.test_results.append({
                "test": "Organization Filters",
                "status": "PASSED" if all(t.get("success") for t in filter_tests) else "PARTIAL",
                "filters": filter_tests
            })
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            self.test_results.append({
                "test": "Organization Filters",
                "status": "FAILED",
                "error": str(e)
            })
    
    async def test_validate_organization_data(self):
        """Test Case 5: Validate organization data fields."""
        print("\n" + "=" * 60)
        print("TEST CASE 5: Validate Organization Data")
        print("=" * 60)
        
        if not self.faucets_data:
            print("⚠️ No Faucets data to validate (exact match test may have failed)")
            self.test_results.append({
                "test": "Validate Organization Data",
                "status": "SKIPPED",
                "reason": "No data available"
            })
            return
        
        # Expected fields for an organization
        required_fields = [
            "id",
            "name",
            "organization_type",
            "created_at",
            "updated_at"
        ]
        
        optional_fields = [
            "description",
            "quick_notes",
            "short_name",
            "organization_status_name",
            "primary_location_id",
            "address",
            "phone",
            "fax",
            "website",
            "logo_url"
        ]
        
        validation_results = {
            "required_fields": {},
            "optional_fields": {},
            "data_quality": {}
        }
        
        print("\nValidating required fields...")
        for field in required_fields:
            present = field in self.faucets_data
            value = self.faucets_data.get(field)
            
            if present and value is not None:
                print(f"   ✅ {field}: Present")
                validation_results["required_fields"][field] = "present"
            else:
                print(f"   ❌ {field}: Missing or null")
                validation_results["required_fields"][field] = "missing"
        
        print("\nChecking optional fields...")
        found_optional = 0
        for field in optional_fields:
            if field in self.faucets_data and self.faucets_data.get(field):
                found_optional += 1
                validation_results["optional_fields"][field] = "present"
        
        print(f"   Found {found_optional}/{len(optional_fields)} optional fields")
        
        # Validate data quality
        print("\nValidating data quality...")
        
        # Check ID format
        org_id = self.faucets_data.get("id")
        if org_id and str(org_id).isdigit():
            print(f"   ✅ ID format valid: {org_id}")
            validation_results["data_quality"]["id_format"] = "valid"
        else:
            print(f"   ❌ ID format invalid: {org_id}")
            validation_results["data_quality"]["id_format"] = "invalid"
        
        # Check name
        name = self.faucets_data.get("name", "")
        if "faucets" in name.lower():
            print(f"   ✅ Name correct: {name}")
            validation_results["data_quality"]["name_match"] = "correct"
        else:
            print(f"   ❌ Name unexpected: {name}")
            validation_results["data_quality"]["name_match"] = "incorrect"
        
        # Check timestamps
        for ts_field in ["created_at", "updated_at"]:
            ts_value = self.faucets_data.get(ts_field)
            if ts_value:
                try:
                    # Try to parse as ISO format
                    if "T" in str(ts_value):
                        print(f"   ✅ {ts_field} format valid")
                        validation_results["data_quality"][f"{ts_field}_format"] = "valid"
                    else:
                        print(f"   ⚠️ {ts_field} format non-standard")
                        validation_results["data_quality"][f"{ts_field}_format"] = "non-standard"
                except:
                    print(f"   ❌ {ts_field} format invalid")
                    validation_results["data_quality"][f"{ts_field}_format"] = "invalid"
        
        # Overall validation status
        all_required = all(
            v == "present" 
            for v in validation_results["required_fields"].values()
        )
        
        self.test_results.append({
            "test": "Validate Organization Data",
            "status": "PASSED" if all_required else "FAILED",
            "validation": validation_results,
            "organization_name": self.faucets_data.get("name"),
            "organization_id": self.faucets_data.get("id")
        })
    
    async def test_performance_benchmarks(self):
        """Test Case 6: Performance benchmarks."""
        print("\n" + "=" * 60)
        print("TEST CASE 6: Performance Benchmarks")
        print("=" * 60)
        
        org_tool = None
        for tool in self.server.server.tools:
            if tool.name == "query_organizations":
                org_tool = tool
                break
        
        if not org_tool:
            print("❌ Tool not found")
            return
        
        benchmark_results = []
        
        # Benchmark different operations
        operations = [
            ("find_exact", {"action": "find", "name": "Faucets Limited"}),
            ("list_10", {"action": "list", "limit": 10}),
            ("list_100", {"action": "list", "limit": 100}),
            ("search", {"action": "search", "query": "faucets"}),
            ("stats", {"action": "stats"})
        ]
        
        print("\nRunning performance benchmarks (3 iterations each)...")
        
        for op_name, params in operations:
            times = []
            
            for i in range(3):
                start_time = time.time()
                
                try:
                    result = await org_tool.handler(**params)
                    elapsed = (time.time() - start_time) * 1000
                    times.append(elapsed)
                    
                    if not result.get("success"):
                        print(f"   ⚠️ {op_name}: Operation failed")
                        break
                        
                except Exception as e:
                    print(f"   ❌ {op_name}: Error - {e}")
                    break
            
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                
                # Check if meets performance threshold (500ms for most, 2000ms for list_100)
                threshold = 2000 if "100" in op_name else 500
                meets_threshold = avg_time < threshold
                
                status_symbol = "✅" if meets_threshold else "⚠️"
                
                print(f"   {status_symbol} {op_name}:")
                print(f"      Avg: {avg_time:.2f}ms")
                print(f"      Min: {min_time:.2f}ms")
                print(f"      Max: {max_time:.2f}ms")
                print(f"      Threshold: <{threshold}ms")
                
                benchmark_results.append({
                    "operation": op_name,
                    "avg_ms": avg_time,
                    "min_ms": min_time,
                    "max_ms": max_time,
                    "meets_threshold": meets_threshold,
                    "threshold_ms": threshold
                })
        
        # Overall performance assessment
        all_meet_threshold = all(b.get("meets_threshold", False) for b in benchmark_results)
        
        self.test_results.append({
            "test": "Performance Benchmarks",
            "status": "PASSED" if all_meet_threshold else "WARNING",
            "benchmarks": benchmark_results
        })
    
    def generate_test_report(self):
        """Generate comprehensive test report."""
        print("\n" + "=" * 80)
        print("TEST REPORT SUMMARY")
        print("=" * 80)
        
        # Count results
        passed = sum(1 for r in self.test_results if r.get("status") == "PASSED")
        failed = sum(1 for r in self.test_results if r.get("status") == "FAILED")
        warnings = sum(1 for r in self.test_results if r.get("status") in ["WARNING", "PARTIAL"])
        skipped = sum(1 for r in self.test_results if r.get("status") == "SKIPPED")
        
        print(f"\nTest Results:")
        print(f"  ✅ Passed: {passed}")
        print(f"  ❌ Failed: {failed}")
        print(f"  ⚠️  Warnings/Partial: {warnings}")
        print(f"  ⏭️  Skipped: {skipped}")
        
        # Performance summary
        if self.performance_metrics:
            print(f"\nPerformance Highlights:")
            for metric, value in self.performance_metrics.items():
                print(f"  {metric}: {value:.2f}ms")
        
        # Fuzzy matching accuracy
        fuzzy_test = next((t for t in self.test_results if t.get("test") == "Fuzzy Matching"), None)
        if fuzzy_test:
            accuracy = fuzzy_test.get("accuracy_percent", 0)
            print(f"\nFuzzy Matching Accuracy: {accuracy:.1f}%")
        
        # Organization data validation
        validation_test = next((t for t in self.test_results if t.get("test") == "Validate Organization Data"), None)
        if validation_test and validation_test.get("status") != "SKIPPED":
            print(f"\nOrganization Data:")
            print(f"  Name: {validation_test.get('organization_name')}")
            print(f"  ID: {validation_test.get('organization_id')}")
        
        # Save report to file
        report_file = Path(__file__).parent / "query_organizations_test_report.json"
        
        report_data = {
            "test_date": datetime.now().isoformat(),
            "summary": {
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "skipped": skipped
            },
            "performance_metrics": self.performance_metrics,
            "test_results": self.test_results,
            "target_organization": "Faucets Limited"
        }
        
        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n📄 Full report saved to: {report_file}")
        print("=" * 80)


async def main():
    """Run the query_organizations tool test suite."""
    tester = QueryOrganizationsToolTester()
    
    try:
        await tester.run_all_tests()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Test suite interrupted by user")
        
    except Exception as e:
        print(f"\n\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())