#!/usr/bin/env python3
"""
Comprehensive test script for the 'health' MCP tool.

This script tests all health check components of the IT Glue MCP server,
including database connectivity, API endpoints, cache status, and error recovery.
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.mcp.server import ITGlueMCPServer
from src.config.settings import settings
from src.services.itglue import ITGlueClient
from src.cache import CacheManager
from src.data import db_manager
import psycopg2
import redis
from neo4j import GraphDatabase
import httpx


class HealthToolTester:
    """Comprehensive health tool testing suite."""
    
    def __init__(self):
        """Initialize test suite."""
        self.server = ITGlueMCPServer()
        self.test_results = []
        self.performance_metrics = {}
        
    async def run_all_tests(self):
        """Run complete test suite."""
        print("=" * 80)
        print("IT GLUE MCP SERVER - HEALTH TOOL TEST SUITE")
        print("=" * 80)
        print(f"Test Started: {datetime.now().isoformat()}\n")
        
        # Test Cases
        await self.test_basic_health_check()
        await self.test_component_specific_health()
        await self.test_performance_metrics()
        await self.test_error_state_detection()
        await self.test_recovery_after_failure()
        await self.test_dependency_validation()
        
        # Generate report
        self.generate_test_report()
        
    async def test_basic_health_check(self):
        """Test Case 1: Full system health check."""
        print("\n" + "=" * 60)
        print("TEST CASE 1: Basic Health Check")
        print("=" * 60)
        
        try:
            start_time = time.time()
            
            # Call health tool directly through the registered method
            # Find the health tool in the server's registered tools
            health_tool = None
            for tool in self.server.server.tools:
                if tool.name == "health":
                    health_tool = tool
                    break
            
            if not health_tool:
                raise Exception("Health tool not found in registered tools")
            
            # Call the health tool
            health_status = await health_tool.handler()
            
            elapsed = (time.time() - start_time) * 1000
            
            # Validate response structure
            assert "status" in health_status, "Missing 'status' field"
            assert "version" in health_status, "Missing 'version' field"
            assert "environment" in health_status, "Missing 'environment' field"
            assert "components" in health_status, "Missing 'components' field"
            
            # Check component statuses
            components = health_status.get("components", {})
            assert "mcp_server" in components, "Missing MCP server status"
            assert "query_engine" in components, "Missing query engine status"
            assert "search_engine" in components, "Missing search engine status"
            
            print(f"✅ Basic health check passed")
            print(f"   Status: {health_status['status']}")
            print(f"   Version: {health_status['version']}")
            print(f"   Environment: {health_status['environment']}")
            print(f"   Response time: {elapsed:.2f}ms")
            
            # Store metrics
            self.performance_metrics["basic_health_check"] = elapsed
            
            self.test_results.append({
                "test": "Basic Health Check",
                "status": "PASSED",
                "response_time_ms": elapsed,
                "details": health_status
            })
            
        except Exception as e:
            print(f"❌ Basic health check failed: {e}")
            self.test_results.append({
                "test": "Basic Health Check",
                "status": "FAILED",
                "error": str(e)
            })
    
    async def test_component_specific_health(self):
        """Test Case 2: Component-specific health checks."""
        print("\n" + "=" * 60)
        print("TEST CASE 2: Component-Specific Health")
        print("=" * 60)
        
        components_to_test = {
            "PostgreSQL": self._test_postgresql_health,
            "Neo4j": self._test_neo4j_health,
            "Redis": self._test_redis_health,
            "Qdrant": self._test_qdrant_health,
            "IT Glue API": self._test_itglue_api_health,
            "Ollama": self._test_ollama_health
        }
        
        component_results = {}
        
        for component_name, test_func in components_to_test.items():
            try:
                start_time = time.time()
                is_healthy, details = await test_func()
                elapsed = (time.time() - start_time) * 1000
                
                status = "healthy" if is_healthy else "unhealthy"
                print(f"   {component_name}: {status} ({elapsed:.2f}ms)")
                
                component_results[component_name] = {
                    "status": status,
                    "response_time_ms": elapsed,
                    "details": details
                }
                
                if not is_healthy:
                    print(f"      ⚠️ {details}")
                    
            except Exception as e:
                print(f"   {component_name}: error - {e}")
                component_results[component_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        self.test_results.append({
            "test": "Component-Specific Health",
            "status": "COMPLETED",
            "components": component_results
        })
    
    async def _test_postgresql_health(self) -> tuple[bool, str]:
        """Test PostgreSQL connectivity."""
        try:
            # Parse connection URL
            import urllib.parse
            url = urllib.parse.urlparse(settings.database_url)
            
            conn = psycopg2.connect(
                host=url.hostname,
                port=url.port or 5432,
                database=url.path[1:],
                user=url.username,
                password=url.password
            )
            
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
            
            conn.close()
            
            return (True, "Connected successfully")
            
        except Exception as e:
            return (False, f"Connection failed: {e}")
    
    async def _test_neo4j_health(self) -> tuple[bool, str]:
        """Test Neo4j connectivity."""
        try:
            driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            
            # Use synchronous session for now
            with driver.session() as session:
                result = session.run("RETURN 1 AS test")
                result.single()
            
            driver.close()
            
            return (True, "Connected successfully")
            
        except Exception as e:
            return (False, f"Connection failed: {e}")
    
    async def _test_redis_health(self) -> tuple[bool, str]:
        """Test Redis connectivity."""
        try:
            client = redis.from_url(settings.redis_url)
            client.ping()
            
            # Check memory usage
            info = client.info("memory")
            used_memory_mb = info.get("used_memory", 0) / (1024 * 1024)
            
            client.close()
            
            return (True, f"Connected, memory: {used_memory_mb:.2f}MB")
            
        except Exception as e:
            return (False, f"Connection failed: {e}")
    
    async def _test_qdrant_health(self) -> tuple[bool, str]:
        """Test Qdrant connectivity."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{settings.qdrant_url}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    return (True, f"Version: {data.get('version', 'unknown')}")
                else:
                    return (False, f"HTTP {response.status_code}")
                    
        except Exception as e:
            return (False, f"Connection failed: {e}")
    
    async def _test_itglue_api_health(self) -> tuple[bool, str]:
        """Test IT Glue API connectivity."""
        try:
            client = ITGlueClient(
                api_key=settings.itglue_api_key,
                api_url=settings.itglue_api_url
            )
            
            # Try to fetch one organization to test API
            orgs = await client.get_organizations()
            
            await client.disconnect()
            
            return (True, f"API accessible, found {len(orgs)} org(s)")
            
        except Exception as e:
            return (False, f"API error: {e}")
    
    async def _test_ollama_health(self) -> tuple[bool, str]:
        """Test Ollama connectivity."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{settings.ollama_url}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    return (True, f"Available models: {len(models)}")
                else:
                    return (False, f"HTTP {response.status_code}")
                    
        except Exception as e:
            return (False, f"Connection failed: {e}")
    
    async def test_performance_metrics(self):
        """Test Case 3: Performance metrics validation."""
        print("\n" + "=" * 60)
        print("TEST CASE 3: Performance Metrics")
        print("=" * 60)
        
        # Run health check multiple times to get metrics
        response_times = []
        
        # Find health tool
        health_tool = None
        for tool in self.server.server.tools:
            if tool.name == "health":
                health_tool = tool
                break
        
        if not health_tool:
            raise Exception("Health tool not found")
        
        for i in range(10):
            start_time = time.time()
            await health_tool.handler()
            elapsed = (time.time() - start_time) * 1000
            response_times.append(elapsed)
        
        # Calculate statistics
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        
        # Check performance thresholds
        performance_passed = avg_time < 100  # Should respond in < 100ms
        
        print(f"   Average response time: {avg_time:.2f}ms")
        print(f"   Min response time: {min_time:.2f}ms")
        print(f"   Max response time: {max_time:.2f}ms")
        print(f"   Performance threshold (<100ms): {'✅ PASSED' if performance_passed else '❌ FAILED'}")
        
        self.test_results.append({
            "test": "Performance Metrics",
            "status": "PASSED" if performance_passed else "WARNING",
            "metrics": {
                "avg_response_ms": avg_time,
                "min_response_ms": min_time,
                "max_response_ms": max_time,
                "samples": len(response_times)
            }
        })
        
        self.performance_metrics["health_check_avg"] = avg_time
    
    async def test_error_state_detection(self):
        """Test Case 4: Error state detection."""
        print("\n" + "=" * 60)
        print("TEST CASE 4: Error State Detection")
        print("=" * 60)
        
        error_scenarios = []
        
        # Scenario 1: Uninitialized components
        print("   Testing uninitialized component detection...")
        if not self.server._initialized:
            # Find health tool
            health_tool = None
            for tool in self.server.server.tools:
                if tool.name == "health":
                    health_tool = tool
                    break
            
            if health_tool:
                health = await health_tool.handler()
            else:
                health = {"components": {}}
            
            # Should show components as not_initialized
            components = health.get("components", {})
            if components.get("query_engine") == "not_initialized":
                print("   ✅ Correctly detected uninitialized query engine")
                error_scenarios.append({
                    "scenario": "Uninitialized components",
                    "result": "PASSED"
                })
            else:
                print("   ❌ Failed to detect uninitialized state")
                error_scenarios.append({
                    "scenario": "Uninitialized components",
                    "result": "FAILED"
                })
        
        # Scenario 2: Simulated exception handling
        print("   Testing exception handling...")
        
        # Check if exception handling is present in the function
        import inspect
        # Get the actual health tool function
        for tool in self.server.server.tools:
            if tool.name == "health":
                health_func = tool.handler
                break
        source = inspect.getsource(health_func)
        
        if "except Exception" in source:
            print("   ✅ Exception handling implemented")
            error_scenarios.append({
                "scenario": "Exception handling",
                "result": "PASSED"
            })
        else:
            print("   ❌ No exception handling found")
            error_scenarios.append({
                "scenario": "Exception handling",
                "result": "FAILED"
            })
        
        self.test_results.append({
            "test": "Error State Detection",
            "status": "COMPLETED",
            "scenarios": error_scenarios
        })
    
    async def test_recovery_after_failure(self):
        """Test Case 5: Recovery testing after failures."""
        print("\n" + "=" * 60)
        print("TEST CASE 5: Recovery After Failure")
        print("=" * 60)
        
        recovery_tests = []
        
        # Test 1: Recovery after initialization
        print("   Testing recovery after initialization...")
        
        try:
            # Force initialization
            await self.server._initialize_components()
            
            # Check health after initialization
            # Find health tool
            health_tool = None
            for tool in self.server.server.tools:
                if tool.name == "health":
                    health_tool = tool
                    break
            
            if not health_tool:
                raise Exception("Health tool not found")
            
            health = await health_tool.handler()
            
            if health["status"] == "healthy":
                print("   ✅ System recovered after initialization")
                recovery_tests.append({
                    "test": "Post-initialization recovery",
                    "result": "PASSED"
                })
            else:
                print("   ❌ System unhealthy after initialization")
                recovery_tests.append({
                    "test": "Post-initialization recovery",
                    "result": "FAILED"
                })
                
        except Exception as e:
            print(f"   ❌ Recovery test failed: {e}")
            recovery_tests.append({
                "test": "Post-initialization recovery",
                "result": "ERROR",
                "error": str(e)
            })
        
        # Test 2: Multiple rapid health checks (stress test)
        print("   Testing rapid successive health checks...")
        
        try:
            errors = 0
            # Find health tool
            health_tool = None
            for tool in self.server.server.tools:
                if tool.name == "health":
                    health_tool = tool
                    break
            
            if not health_tool:
                raise Exception("Health tool not found")
            
            for _ in range(50):
                try:
                    await health_tool.handler()
                except:
                    errors += 1
            
            if errors == 0:
                print("   ✅ No failures in 50 rapid checks")
                recovery_tests.append({
                    "test": "Rapid health checks",
                    "result": "PASSED"
                })
            else:
                print(f"   ⚠️ {errors} failures in 50 rapid checks")
                recovery_tests.append({
                    "test": "Rapid health checks",
                    "result": "WARNING",
                    "failures": errors
                })
                
        except Exception as e:
            print(f"   ❌ Stress test failed: {e}")
            recovery_tests.append({
                "test": "Rapid health checks",
                "result": "ERROR",
                "error": str(e)
            })
        
        self.test_results.append({
            "test": "Recovery After Failure",
            "status": "COMPLETED",
            "recovery_tests": recovery_tests
        })
    
    async def test_dependency_validation(self):
        """Test Case 6: System dependency validation."""
        print("\n" + "=" * 60)
        print("TEST CASE 6: System Dependency Validation")
        print("=" * 60)
        
        dependencies = {
            "Python": self._check_python_version,
            "Environment Variables": self._check_env_vars,
            "Network Connectivity": self._check_network,
            "Disk Space": self._check_disk_space,
            "Memory": self._check_memory
        }
        
        dependency_results = {}
        
        for dep_name, check_func in dependencies.items():
            try:
                is_valid, details = await check_func()
                status = "valid" if is_valid else "invalid"
                
                print(f"   {dep_name}: {status}")
                if details:
                    print(f"      {details}")
                
                dependency_results[dep_name] = {
                    "status": status,
                    "details": details
                }
                
            except Exception as e:
                print(f"   {dep_name}: error - {e}")
                dependency_results[dep_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        self.test_results.append({
            "test": "System Dependency Validation",
            "status": "COMPLETED",
            "dependencies": dependency_results
        })
    
    async def _check_python_version(self) -> tuple[bool, str]:
        """Check Python version requirement."""
        import sys
        version = sys.version_info
        
        if version.major >= 3 and version.minor >= 9:
            return (True, f"Python {version.major}.{version.minor}.{version.micro}")
        else:
            return (False, f"Python {version.major}.{version.minor} (requires 3.9+)")
    
    async def _check_env_vars(self) -> tuple[bool, str]:
        """Check required environment variables."""
        required_vars = [
            "ITGLUE_API_KEY",
            "DATABASE_URL",
            "NEO4J_URI",
            "NEO4J_PASSWORD",
            "JWT_SECRET"
        ]
        
        missing = []
        for var in required_vars:
            if not getattr(settings, var.lower(), None):
                missing.append(var)
        
        if missing:
            return (False, f"Missing: {', '.join(missing)}")
        else:
            return (True, "All required variables set")
    
    async def _check_network(self) -> tuple[bool, str]:
        """Check network connectivity."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.itglue.com", timeout=5.0)
                return (True, f"IT Glue API reachable (HTTP {response.status_code})")
        except:
            return (False, "Cannot reach IT Glue API")
    
    async def _check_disk_space(self) -> tuple[bool, str]:
        """Check available disk space."""
        import shutil
        
        total, used, free = shutil.disk_usage("/")
        free_gb = free / (1024 ** 3)
        
        if free_gb > 1:
            return (True, f"Free space: {free_gb:.2f}GB")
        else:
            return (False, f"Low disk space: {free_gb:.2f}GB")
    
    async def _check_memory(self) -> tuple[bool, str]:
        """Check available memory."""
        import psutil
        
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024 ** 3)
        
        if available_gb > 0.5:
            return (True, f"Available: {available_gb:.2f}GB ({memory.percent}% used)")
        else:
            return (False, f"Low memory: {available_gb:.2f}GB")
    
    def generate_test_report(self):
        """Generate comprehensive test report."""
        print("\n" + "=" * 80)
        print("TEST REPORT SUMMARY")
        print("=" * 80)
        
        # Count results
        passed = sum(1 for r in self.test_results if r.get("status") in ["PASSED", "COMPLETED"])
        failed = sum(1 for r in self.test_results if r.get("status") == "FAILED")
        warnings = sum(1 for r in self.test_results if r.get("status") == "WARNING")
        
        print(f"\nTest Results:")
        print(f"  ✅ Passed/Completed: {passed}")
        print(f"  ❌ Failed: {failed}")
        print(f"  ⚠️  Warnings: {warnings}")
        
        # Performance summary
        print(f"\nPerformance Metrics:")
        for metric, value in self.performance_metrics.items():
            print(f"  {metric}: {value:.2f}ms")
        
        # Recommendations
        print("\n" + "=" * 80)
        print("HEALTH MONITORING RECOMMENDATIONS")
        print("=" * 80)
        
        recommendations = [
            "1. Alert Thresholds:",
            "   - Set health check response time alert at 200ms (warn) / 500ms (critical)",
            "   - Monitor individual component health every 60 seconds",
            "   - Alert if any component is unhealthy for > 5 minutes",
            "",
            "2. Monitoring Dashboard:",
            "   - Display real-time status for all 6 components (PostgreSQL, Neo4j, Redis, Qdrant, IT Glue API, Ollama)",
            "   - Track response time trends with 24-hour rolling window",
            "   - Show API rate limit usage percentage",
            "",
            "3. Health Check Enhancements:",
            "   - Add database connection pool status",
            "   - Include cache hit rate metrics",
            "   - Monitor query queue depth",
            "   - Track IT Glue API rate limit remaining",
            "",
            "4. Recovery Procedures:",
            "   - Implement automatic component restart on failure",
            "   - Add circuit breaker for IT Glue API calls",
            "   - Create fallback to cache when API is unavailable",
            "",
            "5. Logging and Alerting:",
            "   - Log all health check failures with full stack traces",
            "   - Send alerts via webhook/email for critical failures",
            "   - Maintain 30-day health history for trend analysis"
        ]
        
        for rec in recommendations:
            print(rec)
        
        # Save report to file
        report_file = Path(__file__).parent / "health_tool_test_report.json"
        
        report_data = {
            "test_date": datetime.now().isoformat(),
            "summary": {
                "passed": passed,
                "failed": failed,
                "warnings": warnings
            },
            "performance_metrics": self.performance_metrics,
            "test_results": self.test_results,
            "recommendations": recommendations
        }
        
        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n📄 Full report saved to: {report_file}")
        print("=" * 80)


async def main():
    """Run the health tool test suite."""
    tester = HealthToolTester()
    
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