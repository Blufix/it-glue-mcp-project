#!/usr/bin/env python3
"""
Comprehensive integration test suite for all MCP tools working together.
Tests all 10 MCP tools using REAL IT Glue API data from Faucets organization.

This test suite validates:
1. Complete Query Workflow - End-to-end data flow
2. Documentation Generation - Full infrastructure documentation 
3. Performance Under Load - Concurrent tool usage and rate limits
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys
import concurrent.futures
from contextlib import asynccontextmanager

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.mcp.server import ITGlueMCPServer
from src.services.itglue import ITGlueClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_integration_suite_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Test configuration
FAUCETS_ORG_ID = "3183713165639879"  # Known Faucets organization ID
FAUCETS_ORG_NAME = "Faucets"
PERFORMANCE_THRESHOLD_MS = 5000  # 5 seconds for integration tests
CONCURRENT_REQUESTS = 5  # Number of concurrent requests for load testing


class IntegrationTestSuite:
    """Comprehensive integration test suite for MCP tools."""
    
    def __init__(self):
        self.server = ITGlueMCPServer()
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "organization": FAUCETS_ORG_NAME,
            "organization_id": FAUCETS_ORG_ID,
            "scenarios": [],
            "summary": {
                "total_scenarios": 0,
                "passed_scenarios": 0,
                "failed_scenarios": 0,
                "total_duration_seconds": 0,
                "success_rate": 0
            }
        }
        self.start_time = time.time()
        
    def log_scenario(self, scenario_name: str, success: bool, message: str, 
                    data: Any = None, duration: float = 0.0):
        """Log scenario result with detailed information."""
        result = {
            "scenario_name": scenario_name,
            "success": success,
            "message": message,
            "data": data,
            "duration_seconds": round(duration, 2),
            "timestamp": time.time() - self.start_time
        }
        self.test_results["scenarios"].append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"\n{status} {scenario_name}")
        print(f"   {message} ({duration:.2f}s)")
        
        if data and not success:
            print(f"   Error Details: {json.dumps(data, indent=2)[:500]}")
    
    async def setup(self) -> bool:
        """Initialize the MCP server and verify all components."""
        logger.info("🔧 Initializing MCP Server and components...")
        
        try:
            # Initialize server components
            await self.server._initialize_components()
            
            # Verify IT Glue API connectivity
            client = ITGlueClient()
            orgs = await client.get_organizations()
            if not orgs:
                raise Exception("Cannot connect to IT Glue API")
                
            # Verify Faucets organization exists
            faucets_org = await client.get_organization(FAUCETS_ORG_ID)
            if not faucets_org:
                raise Exception(f"Cannot find Faucets organization with ID {FAUCETS_ORG_ID}")
                
            logger.info("✓ Successfully connected to IT Glue API")
            logger.info(f"✓ Verified Faucets organization: {faucets_org.get('name', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            return False
    
    async def scenario_1_complete_query_workflow(self) -> Dict[str, Any]:
        """
        Scenario 1: Complete Query Workflow
        Tests the full end-to-end data flow across multiple tools.
        """
        scenario_name = "Complete Query Workflow"
        scenario_start = time.time()
        
        logger.info(f"\n{'='*70}")
        logger.info(f"🔄 Running Scenario 1: {scenario_name}")
        logger.info(f"{'='*70}")
        
        workflow_results = {}
        workflow_success = True
        
        try:
            # Step 1: Health Check - Verify system ready
            logger.info("Step 1: Health check...")
            step_start = time.time()
            
            health_tool = self.server.server.tools.get('health')
            health_result = await health_tool()
            step_duration = time.time() - step_start
            
            health_success = health_result.get('status') == 'healthy'
            workflow_results['health_check'] = {
                'success': health_success,
                'duration': step_duration,
                'components': len(health_result.get('components', []))
            }
            
            if not health_success:
                workflow_success = False
                logger.error(f"   ❌ Health check failed: {health_result.get('status')}")
            else:
                logger.info(f"   ✅ System healthy ({step_duration:.2f}s)")
            
            # Step 2: Query Organizations - Find Faucets
            logger.info("Step 2: Finding Faucets organization...")
            step_start = time.time()
            
            query_orgs_tool = self.server.server.tools.get('query_organizations')
            org_result = await query_orgs_tool(action="find", name="Faucets")
            step_duration = time.time() - step_start
            
            org_success = org_result.get('success') and org_result.get('organization')
            workflow_results['find_organization'] = {
                'success': org_success,
                'duration': step_duration,
                'found_org': org_result.get('organization', {}).get('name') if org_success else None
            }
            
            if not org_success:
                workflow_success = False
                logger.error(f"   ❌ Could not find Faucets organization")
            else:
                logger.info(f"   ✅ Found organization: {org_result['organization']['name']} ({step_duration:.2f}s)")
            
            # Step 3: Sync Data - Sync Faucets data
            logger.info("Step 3: Syncing Faucets data...")
            step_start = time.time()
            
            sync_tool = self.server.server.tools.get('sync_data')
            sync_result = await sync_tool(organization_id=FAUCETS_ORG_ID, sync_type="incremental")
            step_duration = time.time() - step_start
            
            sync_success = sync_result.get('success', False)
            workflow_results['sync_data'] = {
                'success': sync_success,
                'duration': step_duration,
                'entities_synced': sync_result.get('entities_synced', 0) if sync_success else 0
            }
            
            if not sync_success:
                # Sync might fail but we continue with existing data
                logger.warning(f"   ⚠️ Data sync had issues but continuing: {sync_result.get('message', 'Unknown error')}")
            else:
                logger.info(f"   ✅ Synced {sync_result.get('entities_synced', 0)} entities ({step_duration:.2f}s)")
            
            # Step 4: Query - Natural language queries on synced data
            logger.info("Step 4: Running natural language queries...")
            step_start = time.time()
            
            queries = [
                "Show all configurations for Faucets",
                "What servers does Faucets have?",
                "List all documents for Faucets"
            ]
            
            query_tool = self.server.server.tools.get('query')
            query_results = []
            
            for query_text in queries:
                try:
                    query_result = await query_tool(query=query_text, company=FAUCETS_ORG_NAME)
                    query_results.append({
                        'query': query_text,
                        'success': query_result.get('success', False),
                        'results_count': len(query_result.get('results', []))
                    })
                except Exception as e:
                    query_results.append({
                        'query': query_text,
                        'success': False,
                        'error': str(e)
                    })
            
            step_duration = time.time() - step_start
            successful_queries = sum(1 for r in query_results if r.get('success'))
            
            workflow_results['natural_language_queries'] = {
                'success': successful_queries >= len(queries) * 0.5,  # 50% success rate
                'duration': step_duration,
                'successful_queries': successful_queries,
                'total_queries': len(queries),
                'details': query_results
            }
            
            if successful_queries < len(queries) * 0.5:
                workflow_success = False
                logger.error(f"   ❌ Only {successful_queries}/{len(queries)} queries succeeded")
            else:
                logger.info(f"   ✅ {successful_queries}/{len(queries)} queries successful ({step_duration:.2f}s)")
            
            # Step 5: Search - Cross-reference search results
            logger.info("Step 5: Cross-referencing with search...")
            step_start = time.time()
            
            search_tool = self.server.server.tools.get('search')
            search_result = await search_tool(query="server", company=FAUCETS_ORG_NAME, limit=10)
            step_duration = time.time() - step_start
            
            search_success = search_result.get('success', False)
            workflow_results['cross_reference_search'] = {
                'success': search_success,
                'duration': step_duration,
                'results_count': len(search_result.get('results', []))
            }
            
            if not search_success:
                workflow_success = False
                logger.error(f"   ❌ Search failed: {search_result.get('error', 'Unknown error')}")
            else:
                logger.info(f"   ✅ Search returned {len(search_result.get('results', []))} results ({step_duration:.2f}s)")
            
            # Calculate total workflow time
            total_duration = time.time() - scenario_start
            
            # Final validation
            if workflow_success:
                message = f"Complete workflow executed successfully in {total_duration:.2f}s"
                logger.info(f"   🎉 {message}")
            else:
                message = f"Workflow had failures but partially completed in {total_duration:.2f}s"
                logger.error(f"   ⚠️ {message}")
            
            self.log_scenario(scenario_name, workflow_success, message, workflow_results, total_duration)
            
            return {
                'scenario': scenario_name,
                'success': workflow_success,
                'results': workflow_results,
                'duration': total_duration
            }
            
        except Exception as e:
            total_duration = time.time() - scenario_start
            error_message = f"Scenario failed with exception: {str(e)}"
            logger.error(f"   💥 {error_message}")
            
            self.log_scenario(scenario_name, False, error_message, {"error": str(e)}, total_duration)
            
            return {
                'scenario': scenario_name,
                'success': False,
                'error': str(e),
                'duration': total_duration
            }
    
    async def scenario_2_documentation_generation(self) -> Dict[str, Any]:
        """
        Scenario 2: Documentation Generation
        Tests comprehensive infrastructure documentation generation.
        """
        scenario_name = "Documentation Generation"
        scenario_start = time.time()
        
        logger.info(f"\n{'='*70}")
        logger.info(f"📄 Running Scenario 2: {scenario_name}")
        logger.info(f"{'='*70}")
        
        doc_results = {}
        doc_success = True
        
        try:
            # Step 1: Discover Asset Types - Get all schemas
            logger.info("Step 1: Discovering asset types...")
            step_start = time.time()
            
            discover_tool = self.server.server.tools.get('discover_asset_types')
            asset_types_result = await discover_tool(action="list")
            step_duration = time.time() - step_start
            
            asset_types_success = asset_types_result.get('success', False)
            doc_results['discover_asset_types'] = {
                'success': asset_types_success,
                'duration': step_duration,
                'types_count': len(asset_types_result.get('asset_types', []))
            }
            
            if not asset_types_success:
                doc_success = False
                logger.error(f"   ❌ Asset type discovery failed")
            else:
                logger.info(f"   ✅ Discovered {len(asset_types_result.get('asset_types', []))} asset types ({step_duration:.2f}s)")
            
            # Step 2: Query Flexible Assets - Get all assets
            logger.info("Step 2: Querying flexible assets...")
            step_start = time.time()
            
            flexible_assets_tool = self.server.server.tools.get('query_flexible_assets')
            assets_result = await flexible_assets_tool(
                action="list", 
                organization_id=FAUCETS_ORG_ID,
                limit=50
            )
            step_duration = time.time() - step_start
            
            assets_success = assets_result.get('success', False)
            doc_results['query_flexible_assets'] = {
                'success': assets_success,
                'duration': step_duration,
                'assets_count': len(assets_result.get('assets', []))
            }
            
            if not assets_success:
                doc_success = False
                logger.error(f"   ❌ Flexible assets query failed")
            else:
                logger.info(f"   ✅ Found {len(assets_result.get('assets', []))} flexible assets ({step_duration:.2f}s)")
            
            # Step 3: Query Documents - Get all docs
            logger.info("Step 3: Querying documents...")
            step_start = time.time()
            
            docs_tool = self.server.server.tools.get('query_documents')
            docs_result = await docs_tool(
                action="list",
                organization_id=FAUCETS_ORG_ID,
                limit=20
            )
            step_duration = time.time() - step_start
            
            docs_success = docs_result.get('success', False)
            doc_results['query_documents'] = {
                'success': docs_success,
                'duration': step_duration,
                'documents_count': len(docs_result.get('documents', []))
            }
            
            if not docs_success:
                doc_success = False
                logger.error(f"   ❌ Documents query failed")
            else:
                logger.info(f"   ✅ Found {len(docs_result.get('documents', []))} documents ({step_duration:.2f}s)")
            
            # Step 4: Query Locations - Get all locations
            logger.info("Step 4: Querying locations...")
            step_start = time.time()
            
            locations_tool = self.server.server.tools.get('query_locations')
            locations_result = await locations_tool(
                action="list",
                organization_id=FAUCETS_ORG_ID,
                limit=10
            )
            step_duration = time.time() - step_start
            
            locations_success = locations_result.get('success', False)
            doc_results['query_locations'] = {
                'success': locations_success,
                'duration': step_duration,
                'locations_count': len(locations_result.get('locations', []))
            }
            
            if not locations_success:
                # Locations might be optional
                logger.warning(f"   ⚠️ Locations query had issues but continuing")
            else:
                logger.info(f"   ✅ Found {len(locations_result.get('locations', []))} locations ({step_duration:.2f}s)")
            
            # Step 5: Document Infrastructure - Generate complete doc
            logger.info("Step 5: Generating infrastructure documentation...")
            step_start = time.time()
            
            doc_infra_tool = self.server.server.tools.get('document_infrastructure')
            infra_result = await doc_infra_tool(
                organization_id=FAUCETS_ORG_ID,
                upload_to_itglue=False  # Don't upload during testing
            )
            step_duration = time.time() - step_start
            
            infra_success = infra_result.get('success', False)
            doc_results['document_infrastructure'] = {
                'success': infra_success,
                'duration': step_duration,
                'document_size_kb': infra_result.get('document_size_kb', 0) if infra_success else 0,
                'sections_count': infra_result.get('sections_count', 0) if infra_success else 0
            }
            
            if not infra_success:
                doc_success = False
                logger.error(f"   ❌ Infrastructure documentation failed: {infra_result.get('error', 'Unknown error')}")
            else:
                size_kb = infra_result.get('document_size_kb', 0)
                sections = infra_result.get('sections_count', 0)
                logger.info(f"   ✅ Generated {size_kb}KB documentation with {sections} sections ({step_duration:.2f}s)")
            
            # Calculate total documentation time
            total_duration = time.time() - scenario_start
            
            # Validate overall documentation generation
            if doc_success:
                message = f"Complete infrastructure documentation generated successfully in {total_duration:.2f}s"
                logger.info(f"   🎉 {message}")
            else:
                message = f"Documentation generation had failures in {total_duration:.2f}s"
                logger.error(f"   ⚠️ {message}")
            
            self.log_scenario(scenario_name, doc_success, message, doc_results, total_duration)
            
            return {
                'scenario': scenario_name,
                'success': doc_success,
                'results': doc_results,
                'duration': total_duration
            }
            
        except Exception as e:
            total_duration = time.time() - scenario_start
            error_message = f"Documentation scenario failed: {str(e)}"
            logger.error(f"   💥 {error_message}")
            
            self.log_scenario(scenario_name, False, error_message, {"error": str(e)}, total_duration)
            
            return {
                'scenario': scenario_name,
                'success': False,
                'error': str(e),
                'duration': total_duration
            }
    
    async def scenario_3_performance_under_load(self) -> Dict[str, Any]:
        """
        Scenario 3: Performance Under Load
        Tests concurrent tool usage, rate limits, and system reliability.
        """
        scenario_name = "Performance Under Load"
        scenario_start = time.time()
        
        logger.info(f"\n{'='*70}")
        logger.info(f"⚡ Running Scenario 3: {scenario_name}")
        logger.info(f"{'='*70}")
        
        perf_results = {}
        perf_success = True
        
        try:
            # Test 1: Concurrent tool usage
            logger.info("Test 1: Concurrent tool execution...")
            concurrent_start = time.time()
            
            # Define concurrent operations
            async def concurrent_health_check():
                health_tool = self.server.server.tools.get('health')
                return await health_tool()
            
            async def concurrent_org_query():
                query_orgs_tool = self.server.server.tools.get('query_organizations')
                return await query_orgs_tool(action="find", name="Faucets")
            
            async def concurrent_search():
                search_tool = self.server.server.tools.get('search')
                return await search_tool(query="configuration", company=FAUCETS_ORG_NAME, limit=5)
            
            async def concurrent_nl_query():
                query_tool = self.server.server.tools.get('query')
                return await query_tool(query="Show configurations", company=FAUCETS_ORG_NAME)
            
            async def concurrent_docs_query():
                docs_tool = self.server.server.tools.get('query_documents')
                return await docs_tool(action="list", organization_id=FAUCETS_ORG_ID, limit=5)
            
            # Execute concurrent operations
            concurrent_tasks = [
                concurrent_health_check(),
                concurrent_org_query(),
                concurrent_search(),
                concurrent_nl_query(),
                concurrent_docs_query()
            ]
            
            concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            concurrent_duration = time.time() - concurrent_start
            
            # Analyze concurrent results
            successful_concurrent = sum(
                1 for result in concurrent_results 
                if isinstance(result, dict) and result.get('success', False)
            )
            
            concurrent_success = successful_concurrent >= len(concurrent_tasks) * 0.7  # 70% success rate
            perf_results['concurrent_execution'] = {
                'success': concurrent_success,
                'duration': concurrent_duration,
                'successful_operations': successful_concurrent,
                'total_operations': len(concurrent_tasks),
                'operations_per_second': len(concurrent_tasks) / concurrent_duration
            }
            
            if not concurrent_success:
                perf_success = False
                logger.error(f"   ❌ Concurrent execution: {successful_concurrent}/{len(concurrent_tasks)} succeeded")
            else:
                ops_per_sec = len(concurrent_tasks) / concurrent_duration
                logger.info(f"   ✅ Concurrent execution: {successful_concurrent}/{len(concurrent_tasks)} succeeded ({ops_per_sec:.1f} ops/sec)")
            
            # Test 2: Rate limit compliance
            logger.info("Test 2: Rate limit compliance...")
            rate_limit_start = time.time()
            
            # Make rapid sequential requests to test rate limiting
            rate_test_results = []
            for i in range(10):  # 10 rapid requests
                try:
                    start = time.time()
                    health_tool = self.server.server.tools.get('health')
                    result = await health_tool()
                    duration = time.time() - start
                    
                    rate_test_results.append({
                        'request_number': i + 1,
                        'success': result.get('status') == 'healthy',
                        'duration': duration
                    })
                    
                    # Small delay to avoid overwhelming the system
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    rate_test_results.append({
                        'request_number': i + 1,
                        'success': False,
                        'error': str(e)
                    })
            
            rate_limit_duration = time.time() - rate_limit_start
            successful_rate_tests = sum(1 for r in rate_test_results if r.get('success'))
            avg_response_time = sum(r.get('duration', 0) for r in rate_test_results if r.get('duration')) / len([r for r in rate_test_results if r.get('duration')])
            
            rate_limit_success = (
                successful_rate_tests >= 8 and  # At least 80% success
                avg_response_time < 2.0  # Average under 2 seconds
            )
            
            perf_results['rate_limit_compliance'] = {
                'success': rate_limit_success,
                'duration': rate_limit_duration,
                'successful_requests': successful_rate_tests,
                'total_requests': len(rate_test_results),
                'average_response_time': avg_response_time,
                'requests_per_second': len(rate_test_results) / rate_limit_duration
            }
            
            if not rate_limit_success:
                perf_success = False
                logger.error(f"   ❌ Rate limit test: {successful_rate_tests}/10 succeeded, avg {avg_response_time:.2f}s")
            else:
                req_per_sec = len(rate_test_results) / rate_limit_duration
                logger.info(f"   ✅ Rate limit test: {successful_rate_tests}/10 succeeded, avg {avg_response_time:.2f}s ({req_per_sec:.1f} req/sec)")
            
            # Test 3: Cache effectiveness
            logger.info("Test 3: Cache effectiveness...")
            cache_start = time.time()
            
            # Make the same query twice to test caching
            query_tool = self.server.server.tools.get('query')
            test_query = "Show all configurations for Faucets"
            
            # First request (cache miss)
            first_start = time.time()
            first_result = await query_tool(query=test_query, company=FAUCETS_ORG_NAME)
            first_duration = time.time() - first_start
            
            # Small delay
            await asyncio.sleep(0.5)
            
            # Second request (potential cache hit)
            second_start = time.time()
            second_result = await query_tool(query=test_query, company=FAUCETS_ORG_NAME)
            second_duration = time.time() - second_start
            
            cache_duration = time.time() - cache_start
            
            # Cache effectiveness: second request should be faster
            cache_effective = (
                first_result.get('success') and 
                second_result.get('success') and
                second_duration < first_duration * 0.8  # 20% improvement
            )
            
            perf_results['cache_effectiveness'] = {
                'success': cache_effective,
                'duration': cache_duration,
                'first_request_time': first_duration,
                'second_request_time': second_duration,
                'improvement_factor': first_duration / second_duration if second_duration > 0 else 0,
                'cache_hit_likely': second_duration < first_duration * 0.5
            }
            
            if not cache_effective:
                perf_success = False
                logger.error(f"   ❌ Cache test: First {first_duration:.2f}s, Second {second_duration:.2f}s (no improvement)")
            else:
                improvement = first_duration / second_duration if second_duration > 0 else 1
                logger.info(f"   ✅ Cache test: {improvement:.1f}x improvement ({first_duration:.2f}s → {second_duration:.2f}s)")
            
            # Test 4: Response time consistency
            logger.info("Test 4: Response time consistency...")
            consistency_start = time.time()
            
            # Multiple identical requests to measure consistency
            consistency_times = []
            for i in range(5):
                start = time.time()
                try:
                    health_tool = self.server.server.tools.get('health')
                    result = await health_tool()
                    if result.get('status') == 'healthy':
                        consistency_times.append(time.time() - start)
                    await asyncio.sleep(0.2)
                except Exception:
                    pass  # Skip failed requests
            
            consistency_duration = time.time() - consistency_start
            
            if consistency_times:
                avg_time = sum(consistency_times) / len(consistency_times)
                max_time = max(consistency_times)
                min_time = min(consistency_times)
                variance = max_time - min_time
                
                # Good consistency: variance < 50% of average
                consistent = variance < avg_time * 0.5
            else:
                consistent = False
                avg_time = max_time = min_time = variance = 0
            
            perf_results['response_time_consistency'] = {
                'success': consistent,
                'duration': consistency_duration,
                'average_time': avg_time,
                'max_time': max_time,
                'min_time': min_time,
                'variance': variance,
                'consistency_ratio': (avg_time - variance) / avg_time if avg_time > 0 else 0
            }
            
            if not consistent:
                perf_success = False
                logger.error(f"   ❌ Consistency test: High variance {variance:.2f}s (avg {avg_time:.2f}s)")
            else:
                consistency_ratio = (avg_time - variance) / avg_time * 100 if avg_time > 0 else 0
                logger.info(f"   ✅ Consistency test: {consistency_ratio:.1f}% consistent (variance {variance:.2f}s)")
            
            # Calculate total performance testing time
            total_duration = time.time() - scenario_start
            
            if perf_success:
                message = f"Performance tests passed - system handles load well ({total_duration:.2f}s)"
                logger.info(f"   🎉 {message}")
            else:
                message = f"Performance issues detected during load testing ({total_duration:.2f}s)"
                logger.error(f"   ⚠️ {message}")
            
            self.log_scenario(scenario_name, perf_success, message, perf_results, total_duration)
            
            return {
                'scenario': scenario_name,
                'success': perf_success,
                'results': perf_results,
                'duration': total_duration
            }
            
        except Exception as e:
            total_duration = time.time() - scenario_start
            error_message = f"Performance scenario failed: {str(e)}"
            logger.error(f"   💥 {error_message}")
            
            self.log_scenario(scenario_name, False, error_message, {"error": str(e)}, total_duration)
            
            return {
                'scenario': scenario_name,
                'success': False,
                'error': str(e),
                'duration': total_duration
            }
    
    async def run_all_scenarios(self):
        """Execute all integration test scenarios and generate comprehensive report."""
        logger.info("\n" + "="*80)
        logger.info("🚀 STARTING MCP INTEGRATION TEST SUITE")
        logger.info(f"Organization: {FAUCETS_ORG_NAME} (ID: {FAUCETS_ORG_ID})")
        logger.info(f"Performance Threshold: {PERFORMANCE_THRESHOLD_MS}ms")
        logger.info("="*80)
        
        # Setup
        if not await self.setup():
            logger.error("Setup failed - cannot proceed with integration tests")
            return
        
        # Run all scenarios
        scenario_functions = [
            self.scenario_1_complete_query_workflow,
            self.scenario_2_documentation_generation,
            self.scenario_3_performance_under_load
        ]
        
        scenario_results = []
        
        for scenario_func in scenario_functions:
            try:
                result = await scenario_func()
                scenario_results.append(result)
                
                self.test_results["summary"]["total_scenarios"] += 1
                if result.get("success"):
                    self.test_results["summary"]["passed_scenarios"] += 1
                else:
                    self.test_results["summary"]["failed_scenarios"] += 1
                    
            except Exception as e:
                logger.error(f"Scenario execution failed: {e}")
                scenario_results.append({
                    'scenario': scenario_func.__name__,
                    'success': False,
                    'error': str(e)
                })
                self.test_results["summary"]["total_scenarios"] += 1
                self.test_results["summary"]["failed_scenarios"] += 1
        
        # Calculate final summary
        total_duration = time.time() - self.start_time
        self.test_results["summary"]["total_duration_seconds"] = total_duration
        
        if self.test_results["summary"]["total_scenarios"] > 0:
            self.test_results["summary"]["success_rate"] = (
                self.test_results["summary"]["passed_scenarios"] / 
                self.test_results["summary"]["total_scenarios"] * 100
            )
        
        # Generate comprehensive report
        self.generate_final_report(scenario_results)
    
    def generate_final_report(self, scenario_results: List[Dict]):
        """Generate comprehensive integration test report."""
        logger.info("\n" + "="*80)
        logger.info("📊 INTEGRATION TEST SUITE COMPLETE - FINAL REPORT")
        logger.info("="*80)
        
        summary = self.test_results["summary"]
        
        # Overall statistics
        logger.info(f"Total Scenarios: {summary['total_scenarios']}")
        logger.info(f"Passed: {summary['passed_scenarios']}")
        logger.info(f"Failed: {summary['failed_scenarios']}")
        logger.info(f"Success Rate: {summary['success_rate']:.1f}%")
        logger.info(f"Total Duration: {summary['total_duration_seconds']:.2f}s")
        
        # Detailed scenario results
        logger.info(f"\n📋 Scenario Results:")
        for result in scenario_results:
            status = "✅ PASS" if result.get('success') else "❌ FAIL"
            duration = result.get('duration', 0)
            scenario = result.get('scenario', 'Unknown')
            logger.info(f"  {status} {scenario}: {duration:.2f}s")
            
            if not result.get('success') and 'error' in result:
                logger.info(f"    Error: {result['error']}")
        
        # Performance summary
        logger.info(f"\n⚡ Performance Highlights:")
        for result in scenario_results:
            if result.get('results'):
                scenario_name = result.get('scenario', 'Unknown')
                logger.info(f"  {scenario_name}:")
                
                # Extract key performance metrics
                results = result['results']
                for step_name, step_data in results.items():
                    if isinstance(step_data, dict) and 'duration' in step_data:
                        success_indicator = "✅" if step_data.get('success') else "❌"
                        duration = step_data['duration']
                        logger.info(f"    {success_indicator} {step_name}: {duration:.2f}s")
        
        # Tool interaction matrix
        logger.info(f"\n🔗 Tool Interaction Summary:")
        tools_used = set()
        for scenario in self.test_results["scenarios"]:
            if scenario.get("data"):
                tools_used.update(scenario["data"].keys())
        
        logger.info(f"  Tools Tested: {len(tools_used)}")
        logger.info(f"  Tools: {', '.join(sorted(tools_used))}")
        
        # System reliability metrics
        total_operations = sum(
            len(scenario.get("data", {})) for scenario in self.test_results["scenarios"]
        )
        successful_operations = sum(
            sum(1 for step_data in scenario.get("data", {}).values() 
                if isinstance(step_data, dict) and step_data.get("success"))
            for scenario in self.test_results["scenarios"]
        )
        
        reliability = (successful_operations / total_operations * 100) if total_operations > 0 else 0
        
        logger.info(f"\n🛡️ System Reliability:")
        logger.info(f"  Total Operations: {total_operations}")
        logger.info(f"  Successful Operations: {successful_operations}")
        logger.info(f"  Reliability: {reliability:.1f}%")
        
        # Save detailed results
        results_file = Path("test_integration_suite_results.json")
        with open(results_file, "w") as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        logger.info(f"\n📄 Detailed results saved to: {results_file}")
        
        # Recommendations
        recommendations = []
        
        if summary['success_rate'] < 80:
            recommendations.append("Overall success rate below 80% - investigate failing scenarios")
        
        if summary['total_duration_seconds'] > 300:  # 5 minutes
            recommendations.append("Total test duration excessive - consider optimizing slow operations")
        
        # Check for specific failures
        for result in scenario_results:
            if not result.get('success'):
                scenario_name = result.get('scenario', 'Unknown')
                recommendations.append(f"Fix issues in {scenario_name} scenario")
        
        if recommendations:
            logger.warning("\n⚠️ Recommendations:")
            for rec in recommendations:
                logger.warning(f"  • {rec}")
        
        # Final verdict
        if summary['success_rate'] >= 80:
            logger.info("\n🎉 INTEGRATION TEST SUITE PASSED")
            logger.info("   System is ready for production deployment")
        elif summary['success_rate'] >= 60:
            logger.warning("\n⚠️ INTEGRATION TEST SUITE PARTIAL PASS")
            logger.warning("   System has issues but core functionality works")
        else:
            logger.error("\n❌ INTEGRATION TEST SUITE FAILED")
            logger.error("   System has critical issues - not ready for deployment")


async def main():
    """Main entry point for the integration test suite."""
    test_suite = IntegrationTestSuite()
    await test_suite.run_all_scenarios()


if __name__ == "__main__":
    asyncio.run(main())