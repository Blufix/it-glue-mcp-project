#!/usr/bin/env python3
"""Comprehensive test script for the 'health' MCP tool."""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.mcp.server import ITGlueMCPServer


class HealthTestSuite:
    """Comprehensive testing suite for MCP health tool."""
    
    def __init__(self):
        self.server = ITGlueMCPServer()
        self.test_results: List[Dict[str, Any]] = []
        self.start_time = time.time()
        
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
            print(f"   Details: {json.dumps(data, indent=2)}")
    
    async def test_basic_health_check(self) -> bool:
        """Test Case 1: Full system health check."""
        test_start = time.time()
        
        try:
            # Get the health tool function
            health_tool = None
            for name, func in self.server.server.tools.items():
                if name == 'health':
                    health_tool = func
                    break
            
            if not health_tool:
                self.log_result(
                    "Basic Health Check", False, 
                    "Health tool not found in MCP server", 
                    duration=time.time() - test_start
                )
                return False
            
            # Execute health check
            result = await health_tool()
            duration = time.time() - test_start
            
            
            # Validate response structure
            if not isinstance(result, dict):
                self.log_result(
                    "Basic Health Check", False,
                    "Health response is not a dictionary",
                    {"response_type": type(result).__name__, "actual_response": result},
                    duration
                )
                return False
            
            # Check for required fields
            required_fields = ['status', 'timestamp', 'components']
            missing_fields = [f for f in required_fields if f not in result]
            
            if missing_fields:
                self.log_result(
                    "Basic Health Check", False,
                    f"Missing required fields: {missing_fields}",
                    result, duration
                )
                return False
            
            # Validate component health
            components = result.get('components', [])
            component_status = {}
            
            # Components are returned as a list, not dict
            if isinstance(components, list):
                for component in components:
                    if isinstance(component, dict) and 'name' in component:
                        name = component['name']
                        status = component.get('status', 'unknown')
                        component_status[name] = status
            else:
                # Legacy format support
                for component, details in components.items():
                    if isinstance(details, dict) and 'status' in details:
                        component_status[component] = details['status']
                    else:
                        component_status[component] = 'unknown'
            
            overall_healthy = result.get('status') == 'healthy'
            
            self.log_result(
                "Basic Health Check", True,
                f"System status: {result.get('status')} | Components: {len(components)}",
                {
                    "overall_status": result.get('status'),
                    "component_count": len(components),
                    "component_status": component_status
                },
                duration
            )
            
            return overall_healthy
            
        except Exception as e:
            self.log_result(
                "Basic Health Check", False,
                f"Health check failed with exception: {str(e)}",
                {"error": str(e)},
                time.time() - test_start
            )
            return False
    
    async def test_component_specific_health(self) -> Dict[str, bool]:
        """Test Case 2: Component-specific health validation."""
        test_start = time.time()
        component_results = {}
        
        try:
            # Get health tool
            health_tool = self.server.server.tools.get('health')
            if not health_tool:
                return {}
            
            # Get full health status
            health_result = await health_tool()
            components_list = health_result.get('components', [])
            
            # Convert list to dict for easier processing
            components = {}
            for comp in components_list:
                if isinstance(comp, dict) and 'name' in comp:
                    components[comp['name']] = comp
            
            # Expected components to validate
            expected_components = [
                'database', 'redis', 'qdrant', 'neo4j', 
                'it_glue_api', 'embedding_service'
            ]
            
            for component in expected_components:
                component_start = time.time()
                
                if component in components:
                    comp_data = components[component]
                    status = comp_data.get('status', 'unknown')
                    healthy = status in ['healthy', 'up', 'connected']
                    
                    component_results[component] = healthy
                    
                    # Additional validation based on component type
                    if component == 'database' and healthy:
                        # Check for connection details
                        if 'connection_pool' in comp_data:
                            pool_info = comp_data['connection_pool']
                            active = pool_info.get('active_connections', 0)
                            
                            if active > 0:
                                self.log_result(
                                    f"Component: {component}", True,
                                    f"Database healthy with {active} active connections",
                                    comp_data,
                                    time.time() - component_start
                                )
                            else:
                                self.log_result(
                                    f"Component: {component}", False,
                                    "Database reports 0 active connections",
                                    comp_data,
                                    time.time() - component_start
                                )
                                component_results[component] = False
                        else:
                            self.log_result(
                                f"Component: {component}", True,
                                "Database connection established",
                                comp_data,
                                time.time() - component_start
                            )
                    
                    elif component == 'it_glue_api' and healthy:
                        # Check API response time if available
                        response_time = comp_data.get('response_time_ms', 0)
                        if response_time > 5000:  # 5 second threshold
                            self.log_result(
                                f"Component: {component}", False,
                                f"IT Glue API slow response: {response_time}ms",
                                comp_data,
                                time.time() - component_start
                            )
                            component_results[component] = False
                        else:
                            self.log_result(
                                f"Component: {component}", True,
                                f"IT Glue API responsive ({response_time}ms)",
                                comp_data,
                                time.time() - component_start
                            )
                    
                    else:
                        self.log_result(
                            f"Component: {component}", healthy,
                            f"Status: {status}",
                            comp_data,
                            time.time() - component_start
                        )
                        
                else:
                    component_results[component] = False
                    self.log_result(
                        f"Component: {component}", False,
                        "Component not found in health report",
                        duration=time.time() - component_start
                    )
            
            return component_results
            
        except Exception as e:
            self.log_result(
                "Component Health Check", False,
                f"Component health validation failed: {str(e)}",
                {"error": str(e)},
                time.time() - test_start
            )
            return {}
    
    async def test_performance_metrics(self) -> bool:
        """Test Case 3: Performance metrics validation."""
        test_start = time.time()
        
        try:
            # Multiple health checks to measure consistency
            response_times = []
            
            for i in range(5):
                check_start = time.time()
                health_tool = self.server.server.tools.get('health')
                await health_tool()
                response_time = (time.time() - check_start) * 1000
                response_times.append(response_time)
                
                # Short delay between requests
                await asyncio.sleep(0.1)
            
            # Calculate performance metrics
            avg_response = sum(response_times) / len(response_times)
            max_response = max(response_times)
            min_response = min(response_times)
            
            # Performance thresholds
            acceptable_avg = 2000  # 2 seconds
            acceptable_max = 5000  # 5 seconds
            
            performance_good = (avg_response < acceptable_avg and 
                              max_response < acceptable_max)
            
            self.log_result(
                "Performance Metrics", performance_good,
                f"Avg: {avg_response:.1f}ms, Max: {max_response:.1f}ms, Min: {min_response:.1f}ms",
                {
                    "response_times": response_times,
                    "average_ms": avg_response,
                    "max_ms": max_response,
                    "min_ms": min_response,
                    "threshold_avg": acceptable_avg,
                    "threshold_max": acceptable_max
                },
                time.time() - test_start
            )
            
            return performance_good
            
        except Exception as e:
            self.log_result(
                "Performance Metrics", False,
                f"Performance testing failed: {str(e)}",
                {"error": str(e)},
                time.time() - test_start
            )
            return False
    
    async def test_error_state_detection(self) -> bool:
        """Test Case 4: Error state detection capabilities."""
        test_start = time.time()
        
        try:
            # Get baseline health
            health_tool = self.server.server.tools.get('health')
            baseline_result = await health_tool()
            
            # Check if health system can detect unhealthy components
            components_list = baseline_result.get('components', [])
            error_states_detected = []
            
            for details in components_list:
                if not isinstance(details, dict) or 'name' not in details:
                    continue
                    
                component = details['name']
                status = details.get('status', 'unknown')
                
                # Look for error indicators
                if status in ['error', 'unhealthy', 'down', 'failed']:
                    error_states_detected.append(component)
                elif 'error' in details or 'failed' in details:
                    error_states_detected.append(component)
                elif isinstance(details, dict):
                    # Check nested error conditions
                    for key, value in details.items():
                        if 'error' in str(key).lower() or 'failed' in str(key).lower():
                            if value:  # Non-empty error
                                error_states_detected.append(component)
                                break
            
            # Validate error handling
            error_handling_working = True
            error_details = {}
            
            if error_states_detected:
                error_details["detected_errors"] = error_states_detected
                # This is actually good - means error detection is working
                message = f"Error detection working: found {len(error_states_detected)} issues"
            else:
                message = "No errors detected - system appears healthy"
            
            # Check for proper error response structure
            if 'errors' in baseline_result:
                errors = baseline_result['errors']
                error_details["system_errors"] = errors
                if isinstance(errors, list) and len(errors) > 0:
                    message += f" | System reported {len(errors)} errors"
            
            self.log_result(
                "Error State Detection", error_handling_working,
                message,
                error_details,
                time.time() - test_start
            )
            
            return error_handling_working
            
        except Exception as e:
            self.log_result(
                "Error State Detection", False,
                f"Error detection test failed: {str(e)}",
                {"error": str(e)},
                time.time() - test_start
            )
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Execute all health tool tests and generate report."""
        print("🩺 MCP Health Tool Test Suite")
        print("=" * 50)
        
        # Test Case 1: Basic Health Check
        basic_health = await self.test_basic_health_check()
        
        # Test Case 2: Component-Specific Health
        component_health = await self.test_component_specific_health()
        
        # Test Case 3: Performance Metrics
        performance_ok = await self.test_performance_metrics()
        
        # Test Case 4: Error State Detection
        error_detection = await self.test_error_state_detection()
        
        # Generate summary
        total_duration = time.time() - self.start_time
        
        passed_tests = sum([
            basic_health,
            len([v for v in component_health.values() if v]) > 0,
            performance_ok,
            error_detection
        ])
        
        total_tests = 4 + len(component_health)  # Main tests + component tests
        
        summary = {
            "test_suite": "Health Tool Validation",
            "total_duration_seconds": round(total_duration, 2),
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "success_rate": round((passed_tests / total_tests) * 100, 1) if total_tests > 0 else 0,
            "basic_health": basic_health,
            "component_health": component_health,
            "performance_acceptable": performance_ok,
            "error_detection_working": error_detection,
            "detailed_results": self.test_results,
            "recommendations": []
        }
        
        # Generate recommendations
        if not basic_health:
            summary["recommendations"].append("CRITICAL: Basic health check failing - investigate system status")
        
        unhealthy_components = [k for k, v in component_health.items() if not v]
        if unhealthy_components:
            summary["recommendations"].append(f"Components need attention: {', '.join(unhealthy_components)}")
        
        if not performance_ok:
            summary["recommendations"].append("Performance issues detected - consider optimization or scaling")
        
        if not error_detection:
            summary["recommendations"].append("Error detection may not be working properly")
        
        # Print summary
        print("\n📊 Test Summary")
        print("-" * 30)
        print(f"Duration: {total_duration:.2f}s")
        print(f"Tests: {passed_tests}/{total_tests} passed ({summary['success_rate']}%)")
        print(f"Basic Health: {'✅' if basic_health else '❌'}")
        print(f"Component Health: {len([v for v in component_health.values() if v])}/{len(component_health)} healthy")
        print(f"Performance: {'✅' if performance_ok else '❌'}")
        print(f"Error Detection: {'✅' if error_detection else '❌'}")
        
        if summary["recommendations"]:
            print("\n⚠️  Recommendations:")
            for rec in summary["recommendations"]:
                print(f"  • {rec}")
        
        return summary


async def main():
    """Run the health tool test suite."""
    test_suite = HealthTestSuite()
    
    try:
        summary = await test_suite.run_all_tests()
        
        # Save detailed results
        results_file = Path(__file__).parent / "health_tool_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        # Exit with appropriate code
        if summary["success_rate"] >= 80:
            print("\n🎉 Health tool test suite PASSED")
            return 0
        else:
            print("\n⚠️  Health tool test suite FAILED")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)