#!/usr/bin/env python3
"""
Comprehensive test script for the 'search' MCP tool.

This script tests cross-company search functionality with REAL IT Glue API data,
focusing on the Faucets organization with filtering, pagination, and relevance testing.
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from collections import Counter

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.mcp.server import ITGlueMCPServer
from src.config.settings import settings
from src.services.itglue import ITGlueClient
from src.search import HybridSearch
from src.cache import CacheManager
from src.data import db_manager


class SearchToolTester:
    """Comprehensive test suite for search tool."""
    
    def __init__(self):
        """Initialize test suite."""
        self.server = ITGlueMCPServer()
        self.test_results = []
        self.performance_metrics = {}
        self.search_results_cache = {}
        
    async def run_all_tests(self):
        """Run complete test suite."""
        print("=" * 80)
        print("IT GLUE MCP SERVER - SEARCH TOOL TEST")
        print("=" * 80)
        print(f"Test Started: {datetime.now().isoformat()}\n")
        
        # Initialize server components
        print("Initializing server components...")
        await self.server._initialize_components()
        
        # Run test cases
        await self.test_basic_search()
        await self.test_filtered_search()
        await self.test_pagination()
        await self.test_relevance_ranking()
        await self.test_performance_benchmarks()
        await self.test_cross_company_search()
        
        # Generate report
        self.generate_test_report()
        
        # Cleanup
        if self.server.itglue_client:
            await self.server.itglue_client.disconnect()
    
    async def test_basic_search(self):
        """Test Case 1: Basic search for 'server' across Faucets data."""
        print("\n" + "=" * 60)
        print("TEST CASE 1: Basic Search - 'server'")
        print("=" * 60)
        
        try:
            # Direct search using the search engine
            if not self.server.search_engine:
                print("❌ Search engine not initialized")
                self.test_results.append({
                    "test": "Basic Search",
                    "status": "FAILED",
                    "error": "Search engine not initialized"
                })
                return
            
            # Test searching for "server"
            search_terms = ["server", "firewall", "switch", "printer", "network"]
            
            for term in search_terms:
                print(f"\nSearching for '{term}'...")
                start_time = time.time()
                
                # Search without filters first
                results = await self.server.search_engine.search(
                    query=term,
                    limit=10
                )
                
                elapsed = (time.time() - start_time) * 1000
                
                # Process results
                result_count = len(results)
                print(f"   Found {result_count} results ({elapsed:.2f}ms)")
                
                # Cache results for later tests
                self.search_results_cache[term] = results
                
                # Show sample results
                if results:
                    print(f"   Sample results for '{term}':")
                    for i, result in enumerate(results[:3]):
                        entity_type = result.payload.get("entity_type", "unknown")
                        name = result.payload.get("name", "unnamed")
                        company = result.payload.get("company_name", "unknown")
                        score = result.score
                        
                        print(f"      {i+1}. [{entity_type}] {name}")
                        print(f"         Company: {company}")
                        print(f"         Score: {score:.4f}")
                
                self.performance_metrics[f"search_{term}"] = elapsed
                
                # Check if Faucets results are included
                faucets_results = [
                    r for r in results 
                    if "faucets" in str(r.payload.get("company_name", "")).lower()
                ]
                
                if faucets_results:
                    print(f"   ✅ Found {len(faucets_results)} Faucets results")
                else:
                    print(f"   ⚠️ No Faucets results in top 10")
            
            self.test_results.append({
                "test": "Basic Search",
                "status": "PASSED",
                "searches": len(search_terms),
                "avg_time_ms": sum(self.performance_metrics.values()) / len(self.performance_metrics)
            })
            
        except Exception as e:
            print(f"❌ Basic search test failed: {e}")
            self.test_results.append({
                "test": "Basic Search",
                "status": "FAILED",
                "error": str(e)
            })
    
    async def test_filtered_search(self):
        """Test Case 2: Filtered search with company/type filters."""
        print("\n" + "=" * 60)
        print("TEST CASE 2: Filtered Search")
        print("=" * 60)
        
        try:
            if not self.server.search_engine:
                print("❌ Search engine not initialized")
                return
            
            # First, find Faucets organization ID
            orgs = await self.server.itglue_client.get_organizations()
            faucets_org = None
            for org in orgs:
                if "faucets" in org.name.lower():
                    faucets_org = org
                    break
            
            if not faucets_org:
                print("⚠️ Faucets organization not found")
                company_id = None
            else:
                company_id = str(faucets_org.id)
                print(f"✅ Found Faucets Limited (ID: {company_id})")
            
            # Test different filter combinations
            filter_tests = [
                {
                    "name": "Company filter (Faucets only)",
                    "query": "network",
                    "company_id": company_id,
                    "entity_type": None
                },
                {
                    "name": "Entity type filter (configurations)",
                    "query": "server",
                    "company_id": None,
                    "entity_type": "configuration"
                },
                {
                    "name": "Combined filters (Faucets + configurations)",
                    "query": "firewall",
                    "company_id": company_id,
                    "entity_type": "configuration"
                }
            ]
            
            filter_results = []
            
            for test in filter_tests:
                if test["company_id"] is None and company_id is None:
                    continue  # Skip if we don't have Faucets ID
                
                print(f"\nTesting: {test['name']}")
                start_time = time.time()
                
                results = await self.server.search_engine.search(
                    query=test["query"],
                    company_id=test["company_id"] or company_id,
                    entity_type=test["entity_type"],
                    limit=20
                )
                
                elapsed = (time.time() - start_time) * 1000
                
                print(f"   Query: '{test['query']}'")
                if test["company_id"]:
                    print(f"   Company filter: Faucets Limited")
                if test["entity_type"]:
                    print(f"   Type filter: {test['entity_type']}")
                print(f"   Results: {len(results)} items ({elapsed:.2f}ms)")
                
                # Verify filters worked
                if test["company_id"] and results:
                    # Check all results are from the filtered company
                    correct_company = all(
                        str(test["company_id"]) == str(r.payload.get("company_id", ""))
                        for r in results[:5]  # Check first 5
                    )
                    if correct_company:
                        print(f"   ✅ All results from correct company")
                    else:
                        print(f"   ❌ Mixed company results")
                
                if test["entity_type"] and results:
                    # Check all results are of correct type
                    correct_type = all(
                        test["entity_type"] == r.payload.get("entity_type", "")
                        for r in results[:5]  # Check first 5
                    )
                    if correct_type:
                        print(f"   ✅ All results of correct type")
                    else:
                        print(f"   ❌ Mixed entity types")
                
                filter_results.append({
                    "test": test["name"],
                    "results": len(results),
                    "time_ms": elapsed,
                    "success": len(results) > 0
                })
            
            self.test_results.append({
                "test": "Filtered Search",
                "status": "PASSED" if all(r["success"] for r in filter_results) else "PARTIAL",
                "filters": filter_results
            })
            
        except Exception as e:
            print(f"❌ Filtered search test failed: {e}")
            self.test_results.append({
                "test": "Filtered Search",
                "status": "FAILED",
                "error": str(e)
            })
    
    async def test_pagination(self):
        """Test Case 3: Test pagination with different limits."""
        print("\n" + "=" * 60)
        print("TEST CASE 3: Pagination")
        print("=" * 60)
        
        try:
            if not self.server.search_engine:
                print("❌ Search engine not initialized")
                return
            
            # Test different page sizes
            page_sizes = [10, 50, 100]
            query = "configuration"  # Broad query to get many results
            
            pagination_results = []
            
            for limit in page_sizes:
                print(f"\nTesting limit={limit}...")
                start_time = time.time()
                
                results = await self.server.search_engine.search(
                    query=query,
                    limit=limit
                )
                
                elapsed = (time.time() - start_time) * 1000
                
                actual_count = len(results)
                print(f"   Requested: {limit} items")
                print(f"   Returned: {actual_count} items")
                print(f"   Response time: {elapsed:.2f}ms")
                
                # Check if pagination worked correctly
                if actual_count <= limit:
                    print(f"   ✅ Pagination correct (returned ≤ limit)")
                else:
                    print(f"   ❌ Pagination error (returned > limit)")
                
                # Calculate time per result
                if actual_count > 0:
                    time_per_result = elapsed / actual_count
                    print(f"   Time per result: {time_per_result:.2f}ms")
                
                pagination_results.append({
                    "limit": limit,
                    "returned": actual_count,
                    "time_ms": elapsed,
                    "correct": actual_count <= limit
                })
                
                self.performance_metrics[f"pagination_{limit}"] = elapsed
            
            # Test offset/pagination (if supported)
            print("\nTesting result consistency...")
            first_10 = await self.server.search_engine.search(query=query, limit=10)
            second_10 = await self.server.search_engine.search(query=query, limit=20)
            
            # Check if first 10 results are same in both queries
            if len(first_10) > 0 and len(second_10) >= 10:
                first_ids = [r.entity_id for r in first_10]
                second_first_10_ids = [r.entity_id for r in second_10[:10]]
                
                if first_ids == second_first_10_ids:
                    print("   ✅ Result ordering consistent")
                else:
                    print("   ⚠️ Result ordering may vary")
            
            self.test_results.append({
                "test": "Pagination",
                "status": "PASSED" if all(r["correct"] for r in pagination_results) else "FAILED",
                "pagination": pagination_results
            })
            
        except Exception as e:
            print(f"❌ Pagination test failed: {e}")
            self.test_results.append({
                "test": "Pagination",
                "status": "FAILED",
                "error": str(e)
            })
    
    async def test_relevance_ranking(self):
        """Test Case 4: Verify result ordering and scoring."""
        print("\n" + "=" * 60)
        print("TEST CASE 4: Relevance Ranking")
        print("=" * 60)
        
        try:
            if not self.server.search_engine:
                print("❌ Search engine not initialized")
                return
            
            # Test with specific query that should have clear relevance
            query = "Faucets firewall"
            
            print(f"Searching for: '{query}'")
            results = await self.server.search_engine.search(
                query=query,
                limit=20
            )
            
            if not results:
                print("⚠️ No results found")
                self.test_results.append({
                    "test": "Relevance Ranking",
                    "status": "SKIPPED",
                    "reason": "No results to test"
                })
                return
            
            print(f"\n✅ Found {len(results)} results")
            print("\nTop 10 results by relevance score:")
            
            scores = []
            relevance_data = []
            
            for i, result in enumerate(results[:10]):
                score = result.score
                scores.append(score)
                
                entity_type = result.payload.get("entity_type", "unknown")
                name = result.payload.get("name", "unnamed")
                company = result.payload.get("company_name", "unknown")
                
                # Check if result is relevant (contains query terms)
                name_lower = name.lower()
                is_relevant = (
                    "faucets" in company.lower() or
                    "firewall" in name_lower or
                    "faucets" in name_lower
                )
                
                relevance_marker = "✅" if is_relevant else "⚠️"
                
                print(f"   {i+1}. Score: {score:.4f} {relevance_marker}")
                print(f"      [{entity_type}] {name}")
                print(f"      Company: {company}")
                
                relevance_data.append({
                    "rank": i + 1,
                    "score": score,
                    "relevant": is_relevant,
                    "name": name,
                    "type": entity_type
                })
            
            # Check if scores are descending (properly ranked)
            is_descending = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
            
            if is_descending:
                print("\n✅ Scores are properly ordered (descending)")
            else:
                print("\n❌ Scores are not properly ordered")
            
            # Calculate relevance metrics
            top_5_relevant = sum(1 for r in relevance_data[:5] if r["relevant"])
            top_10_relevant = sum(1 for r in relevance_data[:10] if r["relevant"])
            
            print(f"\nRelevance Metrics:")
            print(f"   Top 5: {top_5_relevant}/5 relevant ({top_5_relevant*20}%)")
            print(f"   Top 10: {top_10_relevant}/10 relevant ({top_10_relevant*10}%)")
            
            # Score distribution
            if scores:
                print(f"\nScore Distribution:")
                print(f"   Highest: {max(scores):.4f}")
                print(f"   Lowest: {min(scores):.4f}")
                print(f"   Range: {max(scores) - min(scores):.4f}")
                print(f"   Average: {sum(scores)/len(scores):.4f}")
            
            self.test_results.append({
                "test": "Relevance Ranking",
                "status": "PASSED" if is_descending and top_5_relevant >= 2 else "WARNING",
                "scores_ordered": is_descending,
                "top_5_relevance": f"{top_5_relevant*20}%",
                "top_10_relevance": f"{top_10_relevant*10}%"
            })
            
        except Exception as e:
            print(f"❌ Relevance ranking test failed: {e}")
            self.test_results.append({
                "test": "Relevance Ranking",
                "status": "FAILED",
                "error": str(e)
            })
    
    async def test_performance_benchmarks(self):
        """Test Case 5: Performance benchmarks for bulk searches."""
        print("\n" + "=" * 60)
        print("TEST CASE 5: Performance Benchmarks")
        print("=" * 60)
        
        try:
            if not self.server.search_engine:
                print("❌ Search engine not initialized")
                return
            
            # Test queries of varying complexity
            test_queries = [
                ("simple", "server"),
                ("two_words", "network configuration"),
                ("specific", "Faucets firewall configuration"),
                ("complex", "server configuration network switch firewall"),
                ("typo", "sever configration"),  # Intentional typos
            ]
            
            print("Running performance benchmarks (3 iterations each)...")
            
            benchmark_results = []
            
            for query_type, query in test_queries:
                times = []
                result_counts = []
                
                for iteration in range(3):
                    start_time = time.time()
                    
                    results = await self.server.search_engine.search(
                        query=query,
                        limit=50
                    )
                    
                    elapsed = (time.time() - start_time) * 1000
                    times.append(elapsed)
                    result_counts.append(len(results))
                
                avg_time = sum(times) / len(times)
                avg_results = sum(result_counts) / len(result_counts)
                
                # Performance threshold: 500ms for simple, 1000ms for complex
                threshold = 500 if "simple" in query_type else 1000
                meets_threshold = avg_time < threshold
                
                status = "✅" if meets_threshold else "⚠️"
                
                print(f"\n{status} {query_type}: '{query}'")
                print(f"   Avg time: {avg_time:.2f}ms")
                print(f"   Avg results: {avg_results:.1f}")
                print(f"   Min/Max time: {min(times):.2f}ms / {max(times):.2f}ms")
                print(f"   Threshold: <{threshold}ms")
                
                benchmark_results.append({
                    "query_type": query_type,
                    "query": query,
                    "avg_time_ms": avg_time,
                    "avg_results": avg_results,
                    "meets_threshold": meets_threshold
                })
                
                self.performance_metrics[f"benchmark_{query_type}"] = avg_time
            
            # Overall performance assessment
            all_meet_threshold = all(b["meets_threshold"] for b in benchmark_results)
            avg_response = sum(b["avg_time_ms"] for b in benchmark_results) / len(benchmark_results)
            
            print(f"\n" + "=" * 40)
            print(f"Overall Average Response: {avg_response:.2f}ms")
            
            if avg_response < 300:
                print("✅ Performance: EXCELLENT")
            elif avg_response < 500:
                print("✅ Performance: GOOD")
            elif avg_response < 1000:
                print("⚠️ Performance: ACCEPTABLE")
            else:
                print("❌ Performance: NEEDS IMPROVEMENT")
            
            self.test_results.append({
                "test": "Performance Benchmarks",
                "status": "PASSED" if all_meet_threshold else "WARNING",
                "benchmarks": benchmark_results,
                "avg_response_ms": avg_response
            })
            
        except Exception as e:
            print(f"❌ Performance benchmark test failed: {e}")
            self.test_results.append({
                "test": "Performance Benchmarks",
                "status": "FAILED",
                "error": str(e)
            })
    
    async def test_cross_company_search(self):
        """Test Case 6: Cross-company search validation."""
        print("\n" + "=" * 60)
        print("TEST CASE 6: Cross-Company Search")
        print("=" * 60)
        
        try:
            if not self.server.search_engine:
                print("❌ Search engine not initialized")
                return
            
            # Search across all companies
            print("Searching across all companies for 'server'...")
            start_time = time.time()
            
            all_results = await self.server.search_engine.search(
                query="server",
                limit=100
            )
            
            elapsed = (time.time() - start_time) * 1000
            
            # Analyze company distribution
            company_counter = Counter()
            for result in all_results:
                company = result.payload.get("company_name", "Unknown")
                company_counter[company] += 1
            
            print(f"\n✅ Found {len(all_results)} total results ({elapsed:.2f}ms)")
            print(f"   From {len(company_counter)} different companies")
            
            print("\nTop 5 companies by result count:")
            for company, count in company_counter.most_common(5):
                percentage = (count / len(all_results)) * 100
                print(f"   • {company}: {count} results ({percentage:.1f}%)")
            
            # Check if Faucets is represented
            faucets_count = company_counter.get("Faucets Limited", 0)
            if faucets_count > 0:
                print(f"\n✅ Faucets Limited: {faucets_count} results")
            else:
                print("\n⚠️ No Faucets Limited results in cross-company search")
            
            # Entity type distribution
            type_counter = Counter()
            for result in all_results:
                entity_type = result.payload.get("entity_type", "unknown")
                type_counter[entity_type] += 1
            
            print("\nEntity type distribution:")
            for entity_type, count in type_counter.most_common():
                percentage = (count / len(all_results)) * 100
                print(f"   • {entity_type}: {count} ({percentage:.1f}%)")
            
            self.test_results.append({
                "test": "Cross-Company Search",
                "status": "PASSED",
                "total_results": len(all_results),
                "companies": len(company_counter),
                "faucets_results": faucets_count,
                "response_time_ms": elapsed
            })
            
        except Exception as e:
            print(f"❌ Cross-company search test failed: {e}")
            self.test_results.append({
                "test": "Cross-Company Search",
                "status": "FAILED",
                "error": str(e)
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
            print(f"\nPerformance Summary:")
            avg_time = sum(self.performance_metrics.values()) / len(self.performance_metrics)
            print(f"  Average response time: {avg_time:.2f}ms")
            print(f"  Fastest query: {min(self.performance_metrics.values()):.2f}ms")
            print(f"  Slowest query: {max(self.performance_metrics.values()):.2f}ms")
        
        # Test details
        print(f"\nTest Details:")
        for result in self.test_results:
            status = result.get("status", "UNKNOWN")
            test_name = result.get("test", "Unknown")
            
            if status == "PASSED":
                symbol = "✅"
            elif status == "FAILED":
                symbol = "❌"
            elif status in ["WARNING", "PARTIAL"]:
                symbol = "⚠️"
            else:
                symbol = "⏭️"
            
            print(f"  {symbol} {test_name}: {status}")
            
            # Add relevant details
            if "avg_time_ms" in result:
                print(f"     Avg time: {result['avg_time_ms']:.2f}ms")
            if "total_results" in result:
                print(f"     Total results: {result['total_results']}")
            if "error" in result:
                print(f"     Error: {result['error']}")
        
        # Save report to file
        report_file = Path(__file__).parent / "search_tool_test_report.json"
        
        report_data = {
            "test_date": datetime.now().isoformat(),
            "summary": {
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "skipped": skipped
            },
            "performance_metrics": self.performance_metrics,
            "test_results": self.test_results
        }
        
        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n📄 Full report saved to: {report_file}")
        print("=" * 80)


async def main():
    """Run the search tool test suite."""
    tester = SearchToolTester()
    
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