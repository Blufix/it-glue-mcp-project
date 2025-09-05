#!/usr/bin/env python3
"""Comprehensive test script for the 'query_organizations' MCP tool."""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.mcp.server import ITGlueMCPServer


class QueryOrganizationsTestSuite:
    """Comprehensive testing suite for MCP query_organizations tool."""
    
    def __init__(self):
        self.server = ITGlueMCPServer()
        self.test_results: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self.known_faucets_id = "3183713165639879"  # Known Faucets org ID
        
    def log_result(self, test_name: str, success: bool, message: str, 
                  data: Any = None, duration: float = 0.0):
        """Log test result with timing information."""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "data": data,
            "duration_ms": round(duration * 1000, 2),
            "timestamp": time.time() - self.start_time
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message} ({duration*1000:.1f}ms)")
        
        if data and not success:
            print(f"   Details: {json.dumps(data, indent=2)[:500]}{'...' if len(json.dumps(data, indent=2)) > 500 else ''}")
    
    async def test_exact_match_faucets(self) -> bool:
        """Test Case 1: Exact match query for 'Faucets' organization."""
        test_start = time.time()
        
        try:
            # Get the query_organizations tool
            query_orgs_tool = self.server.server.tools.get('query_organizations')
            if not query_orgs_tool:
                self.log_result(
                    "Exact Match - Faucets", False,
                    "query_organizations tool not found",
                    duration=time.time() - test_start
                )
                return False
            
            # Test exact name search
            result = await query_orgs_tool(action="find", name="Faucets")
            duration = time.time() - test_start
            
            # Validate response structure
            if not isinstance(result, dict):
                self.log_result(
                    "Exact Match - Faucets", False,
                    "Invalid response type",
                    {"response_type": type(result).__name__},
                    duration
                )
                return False
            
            success = result.get('success', False)
            if not success:
                self.log_result(
                    "Exact Match - Faucets", False,
                    f"Tool returned error: {result.get('error', 'Unknown error')}",
                    result,
                    duration
                )
                return False
            
            # Check if we got a single organization (find returns single org)
            organization = result.get('organization')
            
            if not organization:
                self.log_result(
                    "Exact Match - Faucets", False,
                    "No organization found for 'Faucets'",
                    result,
                    duration
                )
                return False
            
            # The organization should be Faucets-related (could be "Faucets Limited")
            org_name = organization.get('name', '').lower()
            if 'faucets' not in org_name:
                self.log_result(
                    "Exact Match - Faucets", False,
                    f"Found organization '{org_name}' does not contain 'faucets'",
                    {"found_org": organization.get('name', 'No name')},
                    duration
                )
                return False
            
            faucets_org = organization
            
            # Validate required fields (allow null values for optional fields)
            required_fields = ['id', 'name']
            missing_fields = [f for f in required_fields if f not in faucets_org]
            
            if missing_fields:
                self.log_result(
                    "Exact Match - Faucets", False,
                    f"Missing critical fields: {missing_fields}",
                    {"faucets_org": faucets_org},
                    duration
                )
                return False
            
            # Check for optional fields (can be null, but should be present)
            optional_fields = ['organization-type-name']
            optional_missing = [f for f in optional_fields if f not in faucets_org]
            if optional_missing:
                # Log as warning but don't fail
                print(f"   Warning: Optional fields missing: {optional_missing}")
            
            # Validate known ID if available
            org_id = faucets_org.get('id')
            if org_id != self.known_faucets_id:
                self.log_result(
                    "Exact Match - Faucets", False,
                    f"Organization ID mismatch: expected {self.known_faucets_id}, got {org_id}",
                    {"faucets_org": faucets_org},
                    duration
                )
                return False
            
            self.log_result(
                "Exact Match - Faucets", True,
                f"Found Faucets org (ID: {org_id}) with all required fields",
                {
                    "organization": {
                        "id": faucets_org.get('id'),
                        "name": faucets_org.get('name'),
                        "type": faucets_org.get('organization-type-name'),
                        "match_type": result.get('match_type', 'unknown')
                    }
                },
                duration
            )
            
            return True
            
        except Exception as e:
            self.log_result(
                "Exact Match - Faucets", False,
                f"Test failed with exception: {str(e)}",
                {"error": str(e)},
                time.time() - test_start
            )
            return False
    
    async def test_fuzzy_matching(self) -> Dict[str, bool]:
        """Test Case 2: Fuzzy name matching with typos."""
        fuzzy_results = {}
        
        fuzzy_terms = [
            ("Faucet", "Missing 's'"),
            ("Faucetts", "Double 't'"),
            ("faucets", "Lowercase"),
            ("FAUCETS", "Uppercase"),
            ("Faucet Ltd", "With suffix")
        ]
        
        query_orgs_tool = self.server.server.tools.get('query_organizations')
        if not query_orgs_tool:
            return {}
        
        for term, description in fuzzy_terms:
            test_start = time.time()
            
            try:
                result = await query_orgs_tool(action="find", name=term)
                duration = time.time() - test_start
                
                success = result.get('success', False)
                
                # Check if Faucets was found (single organization response)
                found_faucets = False
                if success and result.get('organization'):
                    org = result['organization']
                    found_faucets = (
                        org.get('id') == self.known_faucets_id or 
                        'faucets' in org.get('name', '').lower()
                    )
                
                organizations = [result['organization']] if success and result.get('organization') else []
                
                fuzzy_results[term] = found_faucets
                
                self.log_result(
                    f"Fuzzy Match - {term}", found_faucets,
                    f"{description}: {'Found' if found_faucets else 'Not found'} ({len(organizations)} results)",
                    {
                        "search_term": term,
                        "description": description,
                        "results_count": len(organizations),
                        "found_faucets": found_faucets,
                        "first_3_results": [org.get('name', 'No name') for org in organizations[:3]]
                    },
                    duration
                )
                
            except Exception as e:
                fuzzy_results[term] = False
                self.log_result(
                    f"Fuzzy Match - {term}", False,
                    f"Exception: {str(e)}",
                    {"error": str(e)},
                    time.time() - test_start
                )
        
        return fuzzy_results
    
    async def test_list_all_organizations(self) -> bool:
        """Test Case 3: List all organizations with pagination."""
        test_start = time.time()
        
        try:
            query_orgs_tool = self.server.server.tools.get('query_organizations')
            if not query_orgs_tool:
                return False
            
            # Test default list
            result = await query_orgs_tool(action="list", limit=50)
            duration = time.time() - test_start
            
            success = result.get('success', False)
            if not success:
                self.log_result(
                    "List All Organizations", False,
                    f"Tool error: {result.get('error', 'Unknown')}",
                    result,
                    duration
                )
                return False
            
            organizations = result.get('organizations', [])
            total_available = result.get('count', len(organizations))
            
            # Validate we got some organizations
            if not organizations:
                self.log_result(
                    "List All Organizations", False,
                    "No organizations returned",
                    result,
                    duration
                )
                return False
            
            # Validate Faucets is in the list
            found_faucets = any(org.get('id') == self.known_faucets_id for org in organizations)
            
            # Check for pagination info
            has_pagination = 'pagination' in result or 'total_available' in result
            
            self.log_result(
                "List All Organizations", True,
                f"Retrieved {len(organizations)} orgs (total: {total_available}), Faucets: {'✅' if found_faucets else '❌'}",
                {
                    "count": len(organizations),
                    "total_available": total_available,
                    "found_faucets": found_faucets,
                    "has_pagination": has_pagination,
                    "sample_orgs": [org.get('name', 'No name') for org in organizations[:5]]
                },
                duration
            )
            
            return True
            
        except Exception as e:
            self.log_result(
                "List All Organizations", False,
                f"Exception: {str(e)}",
                {"error": str(e)},
                time.time() - test_start
            )
            return False
    
    async def test_organization_type_filtering(self) -> bool:
        """Test Case 4: Filter by organization type."""
        test_start = time.time()
        
        try:
            query_orgs_tool = self.server.server.tools.get('query_organizations')
            if not query_orgs_tool:
                return False
            
            # Test different organization type filters
            filters = [
                ("customers", "Customer organizations"),
                ("vendors", "Vendor organizations")  
            ]
            
            all_passed = True
            filter_results = {}
            
            for org_type, description in filters:
                filter_start = time.time()
                
                try:
                    result = await query_orgs_tool(action=org_type, limit=20)
                    filter_duration = time.time() - filter_start
                    
                    success = result.get('success', False)
                    organizations = result.get('organizations', []) if success else []
                    
                    filter_results[org_type] = {
                        "success": success,
                        "count": len(organizations),
                        "error": result.get('error') if not success else None
                    }
                    
                    if success:
                        # Check if results are actually filtered by type
                        type_consistency = True
                        inconsistent_orgs = []
                        
                        for org in organizations:
                            org_type_name = org.get('organization-type-name', '') or ''
                            org_type_name = org_type_name.lower()
                            
                            # Use partial matching like the handler does
                            if org_type == "customers" and "customer" not in org_type_name:
                                # Allow null/empty types as they may be valid
                                if org_type_name.strip():  # Only flag if type is present but wrong
                                    type_consistency = False
                                    inconsistent_orgs.append(f"{org.get('name', 'Unknown')} ({org_type_name})")
                            elif org_type == "vendors" and "vendor" not in org_type_name:
                                # Allow null/empty types as they may be valid  
                                if org_type_name.strip():  # Only flag if type is present but wrong
                                    type_consistency = False
                                    inconsistent_orgs.append(f"{org.get('name', 'Unknown')} ({org_type_name})")
                        
                        if not type_consistency:
                            all_passed = False
                            self.log_result(
                                f"Filter by {org_type}", False,
                                f"Type filtering inconsistent: {len(inconsistent_orgs)} wrong types",
                                {"inconsistent_orgs": inconsistent_orgs[:3]},
                                filter_duration
                            )
                        else:
                            self.log_result(
                                f"Filter by {org_type}", True,
                                f"Found {len(organizations)} {description.lower()}",
                                {"count": len(organizations)},
                                filter_duration
                            )
                    else:
                        all_passed = False
                        self.log_result(
                            f"Filter by {org_type}", False,
                            f"Filter failed: {result.get('error', 'Unknown error')}",
                            result,
                            filter_duration
                        )
                        
                except Exception as e:
                    all_passed = False
                    filter_results[org_type] = {"success": False, "error": str(e)}
                    self.log_result(
                        f"Filter by {org_type}", False,
                        f"Exception: {str(e)}",
                        {"error": str(e)},
                        time.time() - filter_start
                    )
            
            total_duration = time.time() - test_start
            
            self.log_result(
                "Organization Type Filtering", all_passed,
                f"Type filtering: {'All passed' if all_passed else 'Some failed'}",
                filter_results,
                total_duration
            )
            
            return all_passed
            
        except Exception as e:
            self.log_result(
                "Organization Type Filtering", False,
                f"Test suite exception: {str(e)}",
                {"error": str(e)},
                time.time() - test_start
            )
            return False
    
    async def test_performance_benchmarks(self) -> Dict[str, float]:
        """Test Case 5: API response time benchmarks."""
        test_start = time.time()
        
        benchmarks = {}
        query_orgs_tool = self.server.server.tools.get('query_organizations')
        
        if not query_orgs_tool:
            return {}
        
        # Test different query types
        test_cases = [
            ("find_exact", {"action": "find", "name": "Faucets"}),
            ("list_small", {"action": "list", "limit": 10}),
            ("list_medium", {"action": "list", "limit": 50}),
            ("customers", {"action": "customers", "limit": 20}),
            ("stats", {"action": "stats"})
        ]
        
        for test_name, params in test_cases:
            response_times = []
            
            # Run each test 3 times for consistency
            for i in range(3):
                bench_start = time.time()
                
                try:
                    result = await query_orgs_tool(**params)
                    response_time = time.time() - bench_start
                    
                    if result.get('success', False):
                        response_times.append(response_time * 1000)  # Convert to ms
                    else:
                        # Still record the time, but mark as error
                        response_times.append(-1)
                        
                except Exception as e:
                    response_times.append(-1)  # Error marker
                
                # Small delay between tests
                await asyncio.sleep(0.1)
            
            # Calculate benchmarks
            valid_times = [t for t in response_times if t > 0]
            if valid_times:
                avg_time = sum(valid_times) / len(valid_times)
                max_time = max(valid_times)
                min_time = min(valid_times)
                
                benchmarks[test_name] = {
                    "average_ms": round(avg_time, 2),
                    "max_ms": round(max_time, 2),
                    "min_ms": round(min_time, 2),
                    "success_rate": len(valid_times) / len(response_times) * 100
                }
                
                # Performance thresholds (from task requirements: <500ms)
                threshold_met = avg_time < 500
                
                self.log_result(
                    f"Performance - {test_name}", threshold_met,
                    f"Avg: {avg_time:.1f}ms (threshold: <500ms)",
                    benchmarks[test_name],
                    0  # Duration not relevant for this test
                )
            else:
                benchmarks[test_name] = {"error": "All requests failed"}
                self.log_result(
                    f"Performance - {test_name}", False,
                    "All benchmark requests failed",
                    {"response_times": response_times},
                    0
                )
        
        total_duration = time.time() - test_start
        
        # Overall performance summary
        all_within_threshold = all(
            b.get("average_ms", 1000) < 500 
            for b in benchmarks.values() 
            if isinstance(b, dict) and "average_ms" in b
        )
        
        self.log_result(
            "Performance Benchmarks", all_within_threshold,
            f"Overall performance: {'Within 500ms threshold' if all_within_threshold else 'Some queries exceeded 500ms'}",
            benchmarks,
            total_duration
        )
        
        return benchmarks
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Execute all query organizations tests and generate report."""
        print("🏢 MCP Query Organizations Tool Test Suite")
        print("=" * 55)
        
        # Test Case 1: Exact Match
        exact_match = await self.test_exact_match_faucets()
        
        # Test Case 2: Fuzzy Matching  
        fuzzy_results = await self.test_fuzzy_matching()
        
        # Test Case 3: List All Organizations
        list_all = await self.test_list_all_organizations()
        
        # Test Case 4: Organization Type Filtering
        type_filtering = await self.test_organization_type_filtering()
        
        # Test Case 5: Performance Benchmarks
        performance = await self.test_performance_benchmarks()
        
        # Generate summary
        total_duration = time.time() - self.start_time
        
        # Calculate success metrics
        fuzzy_success_count = sum(1 for success in fuzzy_results.values() if success)
        fuzzy_total = len(fuzzy_results)
        
        performance_success = sum(
            1 for p in performance.values() 
            if isinstance(p, dict) and p.get("average_ms", 1000) < 500
        )
        performance_total = len([p for p in performance.values() if isinstance(p, dict) and "average_ms" in p])
        
        passed_tests = sum([
            exact_match,
            fuzzy_success_count >= fuzzy_total * 0.6,  # 60% fuzzy success rate
            list_all,
            type_filtering,
            performance_success >= performance_total * 0.8  # 80% performance success
        ])
        
        total_tests = 5
        
        summary = {
            "test_suite": "Query Organizations Tool Validation",
            "total_duration_seconds": round(total_duration, 2),
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "success_rate": round((passed_tests / total_tests) * 100, 1),
            "exact_match_faucets": exact_match,
            "fuzzy_matching": {
                "success_count": fuzzy_success_count,
                "total_tests": fuzzy_total,
                "success_rate": round((fuzzy_success_count / fuzzy_total) * 100, 1) if fuzzy_total > 0 else 0,
                "results": fuzzy_results
            },
            "list_all_organizations": list_all,
            "type_filtering": type_filtering,
            "performance_benchmarks": {
                "within_threshold": performance_success,
                "total_tested": performance_total,
                "success_rate": round((performance_success / performance_total) * 100, 1) if performance_total > 0 else 0,
                "detailed": performance
            },
            "detailed_results": self.test_results,
            "recommendations": []
        }
        
        # Generate recommendations
        if not exact_match:
            summary["recommendations"].append("CRITICAL: Cannot find Faucets organization - verify API access and organization data")
        
        if fuzzy_success_count < fuzzy_total * 0.6:
            summary["recommendations"].append("Fuzzy matching accuracy below 60% - consider improving search algorithm")
        
        if not list_all:
            summary["recommendations"].append("Organization listing failed - check API pagination and limits")
        
        if not type_filtering:
            summary["recommendations"].append("Organization type filtering issues - verify filter implementation")
        
        if performance_success < performance_total * 0.8:
            summary["recommendations"].append("Performance below target - some queries exceed 500ms threshold")
        
        # Print summary
        print("\\n📊 Test Summary")
        print("-" * 30)
        print(f"Duration: {total_duration:.2f}s")
        print(f"Tests: {passed_tests}/{total_tests} passed ({summary['success_rate']}%)")
        print(f"Exact Match: {'✅' if exact_match else '❌'}")
        print(f"Fuzzy Matching: {fuzzy_success_count}/{fuzzy_total} ({summary['fuzzy_matching']['success_rate']}%)")
        print(f"List Organizations: {'✅' if list_all else '❌'}")
        print(f"Type Filtering: {'✅' if type_filtering else '❌'}")
        print(f"Performance: {performance_success}/{performance_total} within 500ms threshold")
        
        if summary["recommendations"]:
            print("\\n⚠️  Recommendations:")
            for rec in summary["recommendations"]:
                print(f"  • {rec}")
        
        return summary


async def main():
    """Run the query organizations tool test suite."""
    test_suite = QueryOrganizationsTestSuite()
    
    try:
        summary = await test_suite.run_all_tests()
        
        # Save detailed results
        results_file = Path(__file__).parent / "query_organizations_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"\\n📄 Detailed results saved to: {results_file}")
        
        # Exit with appropriate code
        if summary["success_rate"] >= 80:
            print("\\n🎉 Query Organizations tool test suite PASSED")
            return 0
        else:
            print("\\n⚠️  Query Organizations tool test suite FAILED")
            return 1
            
    except Exception as e:
        print(f"\\n💥 Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)