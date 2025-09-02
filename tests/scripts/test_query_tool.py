#!/usr/bin/env python3
"""
Comprehensive test script for the MCP Query Tool.
Tests natural language queries against REAL IT Glue API data for Faucets organization.

NO MOCK DATA - This script uses actual IT Glue API endpoints.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import settings
from src.mcp.server import ITGlueMCPServer
from src.services.itglue import ITGlueClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_query_tool_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Test configuration
FAUCETS_ORG_NAME = "Faucets"
PERFORMANCE_THRESHOLD_MS = 2000  # 2 seconds max response time


class QueryToolTester:
    """Test harness for the MCP Query Tool."""
    
    def __init__(self):
        self.server = ITGlueMCPServer()
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "organization": FAUCETS_ORG_NAME,
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "avg_response_time_ms": 0
            }
        }
        self.response_times = []
        
    async def setup(self):
        """Initialize the MCP server and verify connectivity."""
        logger.info("Initializing MCP Server and IT Glue connection...")
        try:
            # Initialize server components
            await self.server._initialize_components()
            
            # Verify IT Glue API connectivity
            client = ITGlueClient()
            orgs = await client.get_organizations(limit=1)
            if not orgs:
                raise Exception("Cannot connect to IT Glue API")
                
            logger.info("✓ Successfully connected to IT Glue API")
            return True
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            return False
    
    async def test_basic_query(self) -> Dict:
        """Test Case 1: Basic query - 'Show all servers for Faucets'"""
        test_name = "Basic Query - Show Servers"
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*60}")
        
        query = "Show all servers for Faucets"
        start_time = time.time()
        
        try:
            # Execute query through the MCP tool
            result = await self.server.server._tools["query"](
                query=query,
                company=FAUCETS_ORG_NAME
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            self.response_times.append(response_time_ms)
            
            # Validate response
            success = result.get("success", False)
            has_results = bool(result.get("results", []))
            
            # Check if results are actually filtered to Faucets org
            faucets_only = True
            if has_results and result.get("results"):
                for item in result.get("results", []):
                    # Check if organization field exists and matches
                    org_name = item.get("organization", {}).get("name", "") if isinstance(item.get("organization"), dict) else item.get("organization", "")
                    if org_name and "faucets" not in org_name.lower():
                        faucets_only = False
                        logger.warning(f"  ⚠️ Found result from different org: {org_name}")
            
            test_result = {
                "name": test_name,
                "query": query,
                "passed": success and has_results and faucets_only,
                "response_time_ms": response_time_ms,
                "performance_pass": response_time_ms < PERFORMANCE_THRESHOLD_MS,
                "result_count": len(result.get("results", [])),
                "faucets_only": faucets_only,
                "error": result.get("error") if not faucets_only else None
            }
            
            if test_result["passed"]:
                logger.info(f"✓ Test passed - Found {test_result['result_count']} servers")
                logger.info(f"  Response time: {response_time_ms:.2f}ms")
                logger.info(f"  Faucets-only filter: {'PASSED' if faucets_only else 'FAILED'}")
                # Log sample result
                if result.get("results"):
                    logger.info(f"  Sample: {result['results'][0].get('name', 'N/A')}")
            else:
                if not faucets_only:
                    logger.error(f"✗ Test failed - Results contain data from other organizations")
                else:
                    logger.error(f"✗ Test failed - {result.get('error', 'No results found')}")
                
            return test_result
            
        except Exception as e:
            logger.error(f"✗ Test exception: {e}")
            return {
                "name": test_name,
                "query": query,
                "passed": False,
                "error": str(e)
            }
    
    async def test_complex_query(self) -> Dict:
        """Test Case 2: Complex query - 'What are the network configurations for Faucets?'"""
        test_name = "Complex Query - Network Configurations"
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*60}")
        
        query = "What are the network configurations for Faucets?"
        start_time = time.time()
        
        try:
            result = await self.server.server._tools["query"](
                query=query,
                company=FAUCETS_ORG_NAME
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            self.response_times.append(response_time_ms)
            
            success = result.get("success", False)
            has_results = bool(result.get("results", []))
            
            # Check if results are actually filtered to Faucets org
            faucets_only = True
            other_orgs = []
            if has_results and result.get("results"):
                for item in result.get("results", []):
                    # Check various possible organization field formats
                    org_name = None
                    if isinstance(item, dict):
                        # Try different field names where org might be stored
                        org_name = (item.get("organization", {}).get("name", "") if isinstance(item.get("organization"), dict) 
                                   else item.get("organization", "") or item.get("company", "") 
                                   or item.get("org_name", "") or item.get("location", ""))
                    
                    if org_name and "faucets" not in org_name.lower():
                        faucets_only = False
                        if org_name not in other_orgs:
                            other_orgs.append(org_name)
                            logger.warning(f"  ⚠️ Found result from different org: {org_name}")
            
            test_result = {
                "name": test_name,
                "query": query,
                "passed": success and has_results and faucets_only,
                "response_time_ms": response_time_ms,
                "performance_pass": response_time_ms < PERFORMANCE_THRESHOLD_MS,
                "result_count": len(result.get("results", [])),
                "faucets_only": faucets_only,
                "other_orgs_found": other_orgs,
                "error": f"Results from other orgs: {', '.join(other_orgs)}" if not faucets_only else result.get("error")
            }
            
            if test_result["passed"]:
                logger.info(f"✓ Test passed - Found {test_result['result_count']} network configs")
                logger.info(f"  Response time: {response_time_ms:.2f}ms")
                logger.info(f"  Faucets-only filter: PASSED")
            else:
                if not faucets_only:
                    logger.error(f"✗ Test failed - Results contain data from {len(other_orgs)} other organization(s)")
                    logger.error(f"  Organizations found: {', '.join(other_orgs[:5])}")  # Show first 5
                else:
                    logger.error(f"✗ Test failed - {result.get('error', 'No results found')}")
                
            return test_result
            
        except Exception as e:
            logger.error(f"✗ Test exception: {e}")
            return {
                "name": test_name,
                "query": query,
                "passed": False,
                "error": str(e)
            }
    
    async def test_error_handling(self) -> Dict:
        """Test Case 3: Error handling - Invalid/malformed queries"""
        test_name = "Error Handling - Invalid Query"
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*60}")
        
        # Test with empty query
        query = ""
        start_time = time.time()
        
        try:
            result = await self.server.server._tools["query"](
                query=query,
                company=FAUCETS_ORG_NAME
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # For error handling, we expect it to handle gracefully
            handled_gracefully = result.get("success") == False and "error" in result
            
            test_result = {
                "name": test_name,
                "query": query,
                "passed": handled_gracefully,
                "response_time_ms": response_time_ms,
                "error_message": result.get("error"),
                "handled_gracefully": handled_gracefully
            }
            
            if handled_gracefully:
                logger.info(f"✓ Error handled gracefully: {result.get('error')}")
            else:
                logger.error(f"✗ Error not handled properly")
                
            return test_result
            
        except Exception as e:
            logger.error(f"✗ Unhandled exception: {e}")
            return {
                "name": test_name,
                "query": query,
                "passed": False,
                "error": str(e)
            }
    
    async def test_edge_cases(self) -> Dict:
        """Test Case 4: Edge cases - Non-existent data queries"""
        test_name = "Edge Case - Non-existent Data"
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*60}")
        
        query = "Show all quantum computers for Faucets"
        start_time = time.time()
        
        try:
            result = await self.server.server._tools["query"](
                query=query,
                company=FAUCETS_ORG_NAME
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            self.response_times.append(response_time_ms)
            
            # Should handle gracefully with empty results or appropriate message
            handled_well = result.get("success") is not None
            
            test_result = {
                "name": test_name,
                "query": query,
                "passed": handled_well,
                "response_time_ms": response_time_ms,
                "performance_pass": response_time_ms < PERFORMANCE_THRESHOLD_MS,
                "result_count": len(result.get("results", [])),
                "message": result.get("message") or result.get("error")
            }
            
            if handled_well:
                logger.info(f"✓ Edge case handled - Results: {test_result['result_count']}")
                logger.info(f"  Response time: {response_time_ms:.2f}ms")
            else:
                logger.error(f"✗ Edge case failed")
                
            return test_result
            
        except Exception as e:
            logger.error(f"✗ Test exception: {e}")
            return {
                "name": test_name,
                "query": query,
                "passed": False,
                "error": str(e)
            }
    
    async def test_performance_batch(self) -> Dict:
        """Test Case 5: Performance test - Multiple queries in succession"""
        test_name = "Performance Test - Batch Queries"
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*60}")
        
        queries = [
            "Show configurations for Faucets",
            "List all documents for Faucets",
            "What passwords are stored for Faucets?",
            "Show contacts for Faucets",
            "Display all assets for Faucets"
        ]
        
        batch_results = []
        batch_times = []
        
        for query in queries:
            start_time = time.time()
            try:
                result = await self.server.server._tools["query"](
                    query=query,
                    company=FAUCETS_ORG_NAME
                )
                response_time_ms = (time.time() - start_time) * 1000
                batch_times.append(response_time_ms)
                self.response_times.append(response_time_ms)
                
                batch_results.append({
                    "query": query,
                    "success": result.get("success", False),
                    "time_ms": response_time_ms,
                    "results": len(result.get("results", []))
                })
                
                logger.info(f"  Query: {query[:50]}... - {response_time_ms:.2f}ms")
                
            except Exception as e:
                logger.error(f"  Query failed: {query} - {e}")
                batch_results.append({
                    "query": query,
                    "success": False,
                    "error": str(e)
                })
        
        # Calculate performance metrics
        avg_time = sum(batch_times) / len(batch_times) if batch_times else 0
        max_time = max(batch_times) if batch_times else 0
        all_under_threshold = all(t < PERFORMANCE_THRESHOLD_MS for t in batch_times)
        
        test_result = {
            "name": test_name,
            "passed": all_under_threshold and len(batch_times) == len(queries),
            "total_queries": len(queries),
            "successful_queries": sum(1 for r in batch_results if r.get("success")),
            "avg_response_time_ms": avg_time,
            "max_response_time_ms": max_time,
            "performance_pass": all_under_threshold,
            "details": batch_results
        }
        
        logger.info(f"\nBatch Performance Summary:")
        logger.info(f"  Average response time: {avg_time:.2f}ms")
        logger.info(f"  Max response time: {max_time:.2f}ms")
        logger.info(f"  All under {PERFORMANCE_THRESHOLD_MS}ms: {all_under_threshold}")
        
        return test_result
    
    async def run_all_tests(self):
        """Execute all test cases and generate report."""
        logger.info("\n" + "="*80)
        logger.info("STARTING MCP QUERY TOOL TEST SUITE")
        logger.info(f"Organization: {FAUCETS_ORG_NAME}")
        logger.info(f"Performance Threshold: {PERFORMANCE_THRESHOLD_MS}ms")
        logger.info("="*80)
        
        # Setup
        if not await self.setup():
            logger.error("Setup failed - cannot proceed with tests")
            return
        
        # Run all test cases
        test_cases = [
            self.test_basic_query,
            self.test_complex_query,
            self.test_error_handling,
            self.test_edge_cases,
            self.test_performance_batch
        ]
        
        for test_case in test_cases:
            try:
                result = await test_case()
                self.test_results["tests"].append(result)
                self.test_results["summary"]["total"] += 1
                if result.get("passed"):
                    self.test_results["summary"]["passed"] += 1
                else:
                    self.test_results["summary"]["failed"] += 1
            except Exception as e:
                logger.error(f"Test case failed to execute: {e}")
                self.test_results["summary"]["total"] += 1
                self.test_results["summary"]["failed"] += 1
        
        # Calculate summary statistics
        if self.response_times:
            self.test_results["summary"]["avg_response_time_ms"] = \
                sum(self.response_times) / len(self.response_times)
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate test results report."""
        logger.info("\n" + "="*80)
        logger.info("TEST SUITE COMPLETE - SUMMARY")
        logger.info("="*80)
        
        summary = self.test_results["summary"]
        logger.info(f"Total Tests: {summary['total']}")
        logger.info(f"Passed: {summary['passed']}")
        logger.info(f"Failed: {summary['failed']}")
        logger.info(f"Pass Rate: {(summary['passed']/summary['total']*100):.1f}%")
        logger.info(f"Average Response Time: {summary['avg_response_time_ms']:.2f}ms")
        
        # Save detailed results to JSON
        results_file = Path("test_query_tool_results.json")
        with open(results_file, "w") as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        logger.info(f"\nDetailed results saved to: {results_file}")
        
        # Print failed tests for quick reference
        failed_tests = [t for t in self.test_results["tests"] if not t.get("passed")]
        if failed_tests:
            logger.warning("\nFailed Tests:")
            for test in failed_tests:
                logger.warning(f"  - {test['name']}: {test.get('error', 'Unknown error')}")


async def main():
    """Main entry point for the test script."""
    tester = QueryToolTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())