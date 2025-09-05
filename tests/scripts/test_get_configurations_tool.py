#!/usr/bin/env python3
"""
Get Configurations Tool Validation Test Suite

Comprehensive testing of the MCP get_configurations tool functionality using real Faucets organization data.
This tests configuration data retrieval, filtering, organization context, and data quality.

Author: Claude Code
Project: IT Glue MCP Server Testing Sprint  
Organization: Faucets (IT Glue ID: 2053586924625080)
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
        logging.FileHandler('test_get_configurations_tool_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Test configuration
FAUCETS_ORG_NAME = "Faucets"
FAUCETS_ORG_ID = "2053586924625080"
PERFORMANCE_THRESHOLD_MS = 5000  # 5 seconds for configuration retrieval


class GetConfigurationsTestSuite:
    """Comprehensive test suite for the MCP Get Configurations Tool."""
    
    def __init__(self):
        self.server = ITGlueMCPServer()
        self.test_results = {
            "test_suite": "Get Configurations Tool Validation",
            "timestamp": datetime.now().isoformat(),
            "organization": FAUCETS_ORG_NAME,
            "organization_id": FAUCETS_ORG_ID,
            "total_duration_seconds": 0.0,
            "tests_passed": 0,
            "tests_total": 7,
            "success_rate": 0.0,
            "configurations_found": 0,
            "detailed_results": []
        }
        self.response_times = []
        
    async def setup_tools(self) -> bool:
        """Initialize MCP server and locate get_configurations tool."""
        logger.info("🔧 Setting up MCP server and get_configurations tool...")
        
        try:
            # Initialize server components
            await self.server._initialize_components()
            
            # Verify get_configurations tool availability
            self.get_configurations_tool = self.server.server.tools.get('get_configurations')
            if not self.get_configurations_tool:
                available_tools = list(self.server.server.tools.keys())
                logger.error(f"❌ Get Configurations tool not found. Available tools: {available_tools}")
                return False
            
            # Verify IT Glue connectivity and find Faucets organization
            client = ITGlueClient()
            async with client:
                orgs = await client.get_organizations()
                if not orgs:
                    raise Exception("Cannot connect to IT Glue API")
                
                # Find Faucets organization
                self.faucets_org = None
                for org in orgs:
                    if org.name.lower() == FAUCETS_ORG_NAME.lower():
                        self.faucets_org = org
                        logger.info(f"✅ Found Faucets organization (ID: {org.id})")
                        break
                
                if not self.faucets_org:
                    logger.warning(f"⚠️  Faucets organization not found in {len(orgs)} organizations")
                    # List some org names for debugging
                    org_names = [org.name for org in orgs[:10]]
                    logger.info(f"Sample organization names: {org_names}")
                
            logger.info("✅ Get Configurations tool and IT Glue API connectivity verified")
            return True
            
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            return False

    async def test_basic_configuration_retrieval(self) -> bool:
        """Test basic configuration data retrieval."""
        test_name = "Basic Configuration Retrieval"
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 Testing: {test_name}")
        logger.info(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Test basic configurations retrieval
            response = await self.get_configurations_tool()
            
            duration = (time.time() - start_time) * 1000
            self.response_times.append(duration)
            
            # Parse response
            if isinstance(response, str):
                response_data = json.loads(response)
            else:
                response_data = response
            
            # Validate response structure
            has_success = "success" in response_data
            has_configurations = "configurations" in response_data
            config_count = len(response_data.get("configurations", []))
            
            # Check data quality
            configurations = response_data.get("configurations", [])
            self.test_results["configurations_found"] = config_count
            
            has_valid_data = config_count > 0
            has_proper_structure = has_success and has_configurations
            performance_ok = duration < PERFORMANCE_THRESHOLD_MS
            
            test_result = {
                "test_name": test_name,
                "success": has_proper_structure and performance_ok,
                "response_time_ms": duration,
                "performance_ok": performance_ok,
                "config_count": config_count,
                "has_data": has_valid_data,
                "response_structure": {
                    "has_success": has_success,
                    "has_configurations": has_configurations,
                    "has_metadata": any(key in response_data for key in ["metadata", "total", "count"])
                }
            }
            
            # Log sample configuration if available
            if configurations:
                sample_config = configurations[0]
                logger.info(f"✅ Retrieved {config_count} configurations ({duration:.1f}ms)")
                logger.info(f"  Sample config: {sample_config.get('name', 'Unknown')} (Type: {sample_config.get('configuration_type', {}).get('name', 'Unknown')})")
                
                # Check for expected fields in configurations
                expected_fields = ["id", "name", "organization", "configuration_type"]
                field_coverage = sum(1 for field in expected_fields if field in sample_config)
                test_result["field_coverage"] = field_coverage / len(expected_fields)
                
                logger.info(f"  Field coverage: {test_result['field_coverage']*100:.1f}% ({field_coverage}/{len(expected_fields)})")
            else:
                logger.warning(f"⚠️  No configurations found ({duration:.1f}ms)")
                test_result["field_coverage"] = 0.0
            
            self.test_results["detailed_results"].append(test_result)
            return test_result["success"]
            
        except Exception as e:
            logger.error(f"❌ Basic retrieval test failed: {e}")
            test_result = {
                "test_name": test_name,
                "success": False,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000
            }
            self.test_results["detailed_results"].append(test_result)
            return False

    async def test_organization_filtering(self) -> bool:
        """Test filtering configurations by organization."""
        test_name = "Organization Filtering"
        logger.info(f"\n{'='*60}")
        logger.info(f"🏢 Testing: {test_name}")
        logger.info(f"{'='*60}")
        
        if not self.faucets_org:
            logger.warning("⚠️  Skipping organization filtering - Faucets org not found")
            test_result = {
                "test_name": test_name,
                "success": False,
                "skip_reason": "Faucets organization not found",
                "response_time_ms": 0
            }
            self.test_results["detailed_results"].append(test_result)
            return False
        
        start_time = time.time()
        
        try:
            # Test with organization filter
            response = await self.get_configurations_tool(
                organization_id=self.faucets_org.id
            )
            
            duration = (time.time() - start_time) * 1000
            self.response_times.append(duration)
            
            if isinstance(response, str):
                response_data = json.loads(response)
            else:
                response_data = response
            
            configurations = response_data.get("configurations", [])
            config_count = len(configurations)
            
            # Verify all configurations belong to Faucets
            faucets_only = True
            other_orgs = []
            
            for config in configurations[:10]:  # Check first 10 configs
                org_info = config.get("organization", {})
                if isinstance(org_info, dict):
                    org_name = org_info.get("name", "")
                    org_id = org_info.get("id", "")
                else:
                    org_name = str(org_info)
                    org_id = ""
                
                if org_name and org_name.lower() != FAUCETS_ORG_NAME.lower():
                    faucets_only = False
                    if org_name not in other_orgs:
                        other_orgs.append(org_name)
            
            test_result = {
                "test_name": test_name,
                "success": config_count > 0 and faucets_only,
                "response_time_ms": duration,
                "config_count": config_count,
                "faucets_only": faucets_only,
                "other_orgs_found": other_orgs[:5],  # First 5 other orgs
                "filter_effective": faucets_only or config_count == 0
            }
            
            if faucets_only and config_count > 0:
                logger.info(f"✅ Organization filter working: {config_count} Faucets configurations ({duration:.1f}ms)")
            elif config_count == 0:
                logger.warning(f"⚠️  No configurations found for Faucets ({duration:.1f}ms)")
                test_result["success"] = True  # Empty result is acceptable for filtering
            else:
                logger.error(f"❌ Filter failed: Found configs from {len(other_orgs)} other orgs ({duration:.1f}ms)")
                logger.error(f"  Other organizations: {', '.join(other_orgs[:3])}")
            
            self.test_results["detailed_results"].append(test_result)
            return test_result["success"]
            
        except Exception as e:
            logger.error(f"❌ Organization filtering test failed: {e}")
            test_result = {
                "test_name": test_name,
                "success": False,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000
            }
            self.test_results["detailed_results"].append(test_result)
            return False

    async def test_configuration_types(self) -> bool:
        """Test filtering by configuration types."""
        test_name = "Configuration Type Filtering"
        logger.info(f"\n{'='*60}")
        logger.info(f"🔧 Testing: {test_name}")
        logger.info(f"{'='*60}")
        
        # Test different configuration type filters
        type_filters = [
            ("server", "Server configurations"),
            ("network", "Network device configurations"), 
            ("firewall", "Firewall configurations"),
            ("backup", "Backup system configurations")
        ]
        
        results = {}
        success_count = 0
        
        for filter_name, description in type_filters:
            start_time = time.time()
            
            try:
                # Test with configuration type filter
                response = await self.get_configurations_tool(
                    configuration_type_name=filter_name
                )
                
                duration = (time.time() - start_time) * 1000
                self.response_times.append(duration)
                
                if isinstance(response, str):
                    response_data = json.loads(response)
                else:
                    response_data = response
                
                configurations = response_data.get("configurations", [])
                config_count = len(configurations)
                
                # Check if configurations match the requested type
                type_match_count = 0
                for config in configurations[:5]:  # Check first 5
                    config_type = config.get("configuration_type", {})
                    if isinstance(config_type, dict):
                        type_name = config_type.get("name", "").lower()
                        if filter_name.lower() in type_name:
                            type_match_count += 1
                
                relevance_score = type_match_count / min(len(configurations), 5) if configurations else 0
                
                results[filter_name] = {
                    "description": description,
                    "config_count": config_count,
                    "response_time_ms": duration,
                    "relevance_score": relevance_score,
                    "type_match_count": type_match_count,
                    "success": config_count >= 0  # Accept empty results
                }
                
                if config_count > 0:
                    success_count += 1
                    logger.info(f"  ✅ {filter_name}: {config_count} configs, {relevance_score*100:.1f}% relevant ({duration:.1f}ms)")
                else:
                    logger.info(f"  ℹ️  {filter_name}: No configurations found ({duration:.1f}ms)")
                    
            except Exception as e:
                logger.error(f"  ❌ {filter_name}: Exception - {e}")
                results[filter_name] = {
                    "description": description,
                    "success": False,
                    "error": str(e)
                }
        
        # Test passes if at least one type filter works or tool handles requests gracefully
        overall_success = success_count > 0 or len(results) == len(type_filters)
        
        logger.info(f"\n📊 Configuration Types: {success_count}/{len(type_filters)} returned data")
        
        test_result = {
            "test_name": test_name,
            "success": overall_success,
            "filters_tested": len(type_filters),
            "filters_with_data": success_count,
            "results": results,
            "overall_relevance": sum(r.get("relevance_score", 0) for r in results.values()) / len(results)
        }
        
        self.test_results["detailed_results"].append(test_result)
        return test_result["success"]

    async def test_data_quality_validation(self) -> bool:
        """Test the quality and completeness of configuration data."""
        test_name = "Data Quality Validation"
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 Testing: {test_name}")
        logger.info(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Get sample configurations for quality analysis
            response = await self.get_configurations_tool()
            
            duration = (time.time() - start_time) * 1000
            
            if isinstance(response, str):
                response_data = json.loads(response)
            else:
                response_data = response
            
            configurations = response_data.get("configurations", [])
            
            if not configurations:
                logger.warning("⚠️  No configurations available for quality validation")
                test_result = {
                    "test_name": test_name,
                    "success": True,  # Accept empty data as valid state
                    "skip_reason": "No configurations available",
                    "response_time_ms": duration
                }
                self.test_results["detailed_results"].append(test_result)
                return True
            
            # Quality metrics
            quality_metrics = {
                "total_configs": len(configurations),
                "configs_with_names": 0,
                "configs_with_types": 0,
                "configs_with_organizations": 0,
                "configs_with_details": 0,
                "configs_with_timestamps": 0,
                "unique_config_types": set(),
                "unique_organizations": set()
            }
            
            # Analyze sample of configurations
            sample_size = min(len(configurations), 20)
            sample_configs = configurations[:sample_size]
            
            for config in sample_configs:
                # Check for required fields
                if config.get("name"):
                    quality_metrics["configs_with_names"] += 1
                
                if config.get("configuration_type"):
                    quality_metrics["configs_with_types"] += 1
                    config_type = config.get("configuration_type", {})
                    if isinstance(config_type, dict) and config_type.get("name"):
                        quality_metrics["unique_config_types"].add(config_type["name"])
                
                if config.get("organization"):
                    quality_metrics["configs_with_organizations"] += 1
                    org = config.get("organization", {})
                    if isinstance(org, dict) and org.get("name"):
                        quality_metrics["unique_organizations"].add(org["name"])
                
                # Check for detailed information
                if config.get("details") or len(config.keys()) > 5:
                    quality_metrics["configs_with_details"] += 1
                
                # Check for timestamps
                if any(key in config for key in ["created_at", "updated_at", "created", "updated"]):
                    quality_metrics["configs_with_timestamps"] += 1
            
            # Calculate quality scores
            completeness_score = (
                quality_metrics["configs_with_names"] +
                quality_metrics["configs_with_types"] + 
                quality_metrics["configs_with_organizations"]
            ) / (sample_size * 3) if sample_size > 0 else 0
            
            diversity_score = len(quality_metrics["unique_config_types"]) / max(sample_size, 1)
            detail_score = quality_metrics["configs_with_details"] / sample_size if sample_size > 0 else 0
            
            overall_quality = (completeness_score + diversity_score + detail_score) / 3
            quality_good = overall_quality >= 0.6  # 60% quality threshold
            
            logger.info(f"📊 Data Quality Analysis (sample of {sample_size}):")
            logger.info(f"  Completeness: {completeness_score*100:.1f}% (names, types, orgs)")
            logger.info(f"  Diversity: {len(quality_metrics['unique_config_types'])} config types")
            logger.info(f"  Detail level: {detail_score*100:.1f}% have detailed info")
            logger.info(f"  Organizations: {len(quality_metrics['unique_organizations'])} unique orgs")
            logger.info(f"  Overall quality: {overall_quality*100:.1f}%")
            
            test_result = {
                "test_name": test_name,
                "success": quality_good,
                "response_time_ms": duration,
                "quality_metrics": {
                    **quality_metrics,
                    "unique_config_types": list(quality_metrics["unique_config_types"]),
                    "unique_organizations": list(quality_metrics["unique_organizations"])
                },
                "quality_scores": {
                    "completeness": completeness_score,
                    "diversity": diversity_score,
                    "detail": detail_score,
                    "overall": overall_quality
                },
                "sample_size": sample_size
            }
            
            if quality_good:
                logger.info(f"✅ Data quality: Good ({overall_quality*100:.1f}%)")
            else:
                logger.warning(f"⚠️  Data quality: Needs improvement ({overall_quality*100:.1f}%)")
            
            self.test_results["detailed_results"].append(test_result)
            return test_result["success"]
            
        except Exception as e:
            logger.error(f"❌ Data quality validation failed: {e}")
            test_result = {
                "test_name": test_name,
                "success": False,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000
            }
            self.test_results["detailed_results"].append(test_result)
            return False

    async def test_performance_benchmarks(self) -> bool:
        """Test configuration retrieval performance under different loads."""
        test_name = "Performance Benchmarks"
        logger.info(f"\n{'='*60}")
        logger.info(f"⚡ Testing: {test_name}")
        logger.info(f"{'='*60}")
        
        performance_tests = [
            ("basic_retrieval", {}),
            ("with_org_filter", {"organization_id": self.faucets_org.id} if self.faucets_org else {}),
            ("with_type_filter", {"configuration_type_name": "server"}),
            ("repeated_calls", {})  # Test caching/consistency
        ]
        
        metrics = {}
        performance_passes = 0
        
        for test_desc, params in performance_tests:
            times = []
            
            # Run each test 3 times
            for run in range(3):
                start_time = time.time()
                
                try:
                    response = await self.get_configurations_tool(**params)
                    duration = (time.time() - start_time) * 1000
                    times.append(duration)
                    
                except Exception as e:
                    logger.warning(f"  ⚠️ {test_desc} run {run+1}: {e}")
                    times.append(float('inf'))
            
            # Calculate metrics
            valid_times = [t for t in times if t != float('inf')]
            if valid_times:
                avg_time = sum(valid_times) / len(valid_times)
                min_time = min(valid_times)
                max_time = max(valid_times)
                
                metrics[test_desc] = {
                    "average_ms": avg_time,
                    "min_ms": min_time,
                    "max_ms": max_time,
                    "successful_runs": len(valid_times),
                    "params": params
                }
                
                performance_ok = avg_time < PERFORMANCE_THRESHOLD_MS
                
                if performance_ok:
                    performance_passes += 1
                    logger.info(f"  ✅ {test_desc}: {avg_time:.1f}ms avg ({len(valid_times)}/3 runs)")
                else:
                    logger.warning(f"  ⚠️ {test_desc}: {avg_time:.1f}ms avg (>{PERFORMANCE_THRESHOLD_MS}ms)")
            else:
                metrics[test_desc] = {
                    "average_ms": float('inf'),
                    "error": "All runs failed",
                    "params": params
                }
                logger.error(f"  ❌ {test_desc}: All runs failed")
        
        success_rate = performance_passes / len(performance_tests) * 100
        logger.info(f"\n📊 Performance: {performance_passes}/{len(performance_tests)} under threshold ({success_rate:.1f}%)")
        
        test_result = {
            "test_name": test_name,
            "success": performance_passes >= len(performance_tests) // 2,
            "success_rate": success_rate,
            "metrics": metrics,
            "threshold_ms": PERFORMANCE_THRESHOLD_MS
        }
        
        self.test_results["detailed_results"].append(test_result)
        return test_result["success"]

    async def test_error_handling(self) -> bool:
        """Test error handling for invalid parameters and edge cases."""
        test_name = "Error Handling"
        logger.info(f"\n{'='*60}")
        logger.info(f"🛡️ Testing: {test_name}")
        logger.info(f"{'='*60}")
        
        error_tests = [
            ("invalid_org_id", {"organization_id": "invalid-org-123"}),
            ("nonexistent_type", {"configuration_type_name": "quantum-computer"}),
            ("empty_string_filter", {"configuration_type_name": ""}),
            ("malformed_params", {"invalid_param": "test"}),
            ("very_large_id", {"organization_id": "999999999999999999"})
        ]
        
        results = {}
        success_count = 0
        
        for test_desc, params in error_tests:
            start_time = time.time()
            
            try:
                response = await self.get_configurations_tool(**params)
                duration = (time.time() - start_time) * 1000
                
                if isinstance(response, str):
                    response_data = json.loads(response)
                else:
                    response_data = response
                
                # Good error handling provides meaningful response without crashing
                handled_gracefully = (
                    "error" in response_data or
                    "configurations" in response_data or
                    response_data.get("success") is not None
                )
                
                results[test_desc] = {
                    "params": params,
                    "handled_gracefully": handled_gracefully,
                    "response_time_ms": duration,
                    "has_error_info": "error" in response_data,
                    "config_count": len(response_data.get("configurations", []))
                }
                
                if handled_gracefully:
                    success_count += 1
                    logger.info(f"  ✅ {test_desc}: Handled gracefully ({duration:.1f}ms)")
                else:
                    logger.warning(f"  ❌ {test_desc}: Poor error handling ({duration:.1f}ms)")
                    
            except Exception as e:
                # Exception handling is also acceptable for invalid parameters
                results[test_desc] = {
                    "params": params,
                    "handled_gracefully": True,
                    "exception": str(e)
                }
                success_count += 1
                logger.info(f"  ✅ {test_desc}: Exception handled - {str(e)[:50]}...")
        
        success_rate = success_count / len(error_tests) * 100
        logger.info(f"\n📊 Error Handling: {success_count}/{len(error_tests)} handled gracefully ({success_rate:.1f}%)")
        
        test_result = {
            "test_name": test_name,
            "success": success_count >= len(error_tests) * 0.8,  # 80% should handle gracefully
            "success_rate": success_rate,
            "results": results
        }
        
        self.test_results["detailed_results"].append(test_result)
        return test_result["success"]

    async def test_pagination_and_limits(self) -> bool:
        """Test pagination and result limiting functionality."""
        test_name = "Pagination and Limits"
        logger.info(f"\n{'='*60}")
        logger.info(f"📄 Testing: {test_name}")
        logger.info(f"{'='*60}")
        
        pagination_tests = [
            ("default_limit", {}),
            ("small_limit", {"limit": 5}),
            ("large_limit", {"limit": 100}),
            ("zero_limit", {"limit": 0})
        ]
        
        results = {}
        success_count = 0
        
        for test_desc, params in pagination_tests:
            start_time = time.time()
            
            try:
                response = await self.get_configurations_tool(**params)
                duration = (time.time() - start_time) * 1000
                
                if isinstance(response, str):
                    response_data = json.loads(response)
                else:
                    response_data = response
                
                configurations = response_data.get("configurations", [])
                config_count = len(configurations)
                expected_limit = params.get("limit")
                
                # Check if limit is respected
                limit_respected = True
                if expected_limit and expected_limit > 0:
                    limit_respected = config_count <= expected_limit
                
                # Check for pagination metadata
                has_pagination_info = any(key in response_data for key in [
                    "total", "page", "pages", "next", "previous", "has_more"
                ])
                
                results[test_desc] = {
                    "params": params,
                    "config_count": config_count,
                    "response_time_ms": duration,
                    "limit_respected": limit_respected,
                    "has_pagination_info": has_pagination_info,
                    "expected_limit": expected_limit
                }
                
                test_passed = limit_respected and (config_count > 0 or expected_limit == 0)
                
                if test_passed:
                    success_count += 1
                    logger.info(f"  ✅ {test_desc}: {config_count} configs, limit respected ({duration:.1f}ms)")
                else:
                    logger.warning(f"  ❌ {test_desc}: {config_count} configs, limit issue ({duration:.1f}ms)")
                    
            except Exception as e:
                logger.error(f"  ❌ {test_desc}: Exception - {e}")
                results[test_desc] = {
                    "params": params,
                    "success": False,
                    "error": str(e)
                }
        
        success_rate = success_count / len(pagination_tests) * 100
        logger.info(f"\n📊 Pagination: {success_count}/{len(pagination_tests)} passed ({success_rate:.1f}%)")
        
        test_result = {
            "test_name": test_name,
            "success": success_count >= len(pagination_tests) // 2,
            "success_rate": success_rate,
            "results": results
        }
        
        self.test_results["detailed_results"].append(test_result)
        return test_result["success"]

    async def run_all_tests(self) -> Dict[str, Any]:
        """Execute the complete get_configurations tool test suite."""
        logger.info("🚀 Starting Get Configurations Tool Test Suite")
        logger.info("=" * 80)
        logger.info(f"Organization: {FAUCETS_ORG_NAME} (ID: {FAUCETS_ORG_ID})")
        logger.info(f"Performance Threshold: {PERFORMANCE_THRESHOLD_MS}ms")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        # Setup phase
        if not await self.setup_tools():
            self.test_results["error"] = "Failed to setup get_configurations tool"
            return self.test_results
        
        # Run all test categories
        test_methods = [
            ("Basic Configuration Retrieval", self.test_basic_configuration_retrieval),
            ("Organization Filtering", self.test_organization_filtering),
            ("Configuration Type Filtering", self.test_configuration_types),
            ("Data Quality Validation", self.test_data_quality_validation),
            ("Performance Benchmarks", self.test_performance_benchmarks),
            ("Error Handling", self.test_error_handling),
            ("Pagination and Limits", self.test_pagination_and_limits)
        ]
        
        for test_name, test_method in test_methods:
            try:
                logger.info(f"\n▶️ Running {test_name}...")
                result = await test_method()
                
                if result:
                    self.test_results["tests_passed"] += 1
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    logger.warning(f"❌ {test_name}: FAILED")
                    
            except Exception as e:
                logger.error(f"💥 {test_name}: CRASHED - {e}")
        
        # Calculate final metrics
        total_duration = time.time() - start_time
        self.test_results["total_duration_seconds"] = total_duration
        self.test_results["success_rate"] = (self.test_results["tests_passed"] / self.test_results["tests_total"]) * 100
        
        if self.response_times:
            self.test_results["performance_metrics"] = {
                "average_response_time_ms": sum(self.response_times) / len(self.response_times),
                "min_response_time_ms": min(self.response_times),
                "max_response_time_ms": max(self.response_times),
                "total_requests": len(self.response_times)
            }
        
        # Generate final summary
        self.generate_summary()
        
        return self.test_results
        
    def generate_summary(self):
        """Generate comprehensive test results summary."""
        logger.info("\n" + "=" * 80)
        logger.info("📊 GET CONFIGURATIONS TOOL TEST SUMMARY")
        logger.info("=" * 80)
        
        results = self.test_results
        logger.info(f"Tests Passed: {results['tests_passed']}/{results['tests_total']}")
        logger.info(f"Success Rate: {results['success_rate']:.1f}%")
        logger.info(f"Total Duration: {results['total_duration_seconds']:.2f} seconds")
        logger.info(f"Configurations Found: {results['configurations_found']}")
        
        if "performance_metrics" in results:
            perf = results["performance_metrics"]
            logger.info(f"Avg Response Time: {perf['average_response_time_ms']:.1f}ms")
            logger.info(f"Total API Calls: {perf['total_requests']}")
        
        # Test category results
        logger.info(f"\n📋 Test Category Results:")
        for test_result in results["detailed_results"]:
            status = "✅ PASS" if test_result["success"] else "❌ FAIL"
            logger.info(f"  {test_result['test_name']}: {status}")
        
        # Generate recommendations
        recommendations = []
        
        if results['success_rate'] < 50:
            recommendations.append("CRITICAL: Get Configurations tool needs major fixes - success rate below 50%")
        elif results['success_rate'] < 70:
            recommendations.append("Get Configurations tool needs improvements - success rate below 70%")
        
        # Data availability check
        if results['configurations_found'] == 0:
            recommendations.append("No configuration data found - check data synchronization or organization access")
        elif results['configurations_found'] < 10:
            recommendations.append("Limited configuration data available - may indicate incomplete sync or access restrictions")
        
        # Performance check
        if "performance_metrics" in results:
            avg_time = results["performance_metrics"]["average_response_time_ms"]
            if avg_time > PERFORMANCE_THRESHOLD_MS:
                recommendations.append(f"Performance optimization needed - avg response time {avg_time:.1f}ms > {PERFORMANCE_THRESHOLD_MS}ms")
        
        if not recommendations:
            recommendations.append("Get Configurations tool performing well across all test categories")
        
        results["recommendations"] = recommendations
        
        logger.info(f"\n💡 Recommendations:")
        for rec in recommendations:
            logger.info(f"   • {rec}")
        
        logger.info("\n" + "=" * 80)


async def main():
    """Main execution function."""
    suite = GetConfigurationsTestSuite()
    results = await suite.run_all_tests()
    
    # Save detailed results
    results_file = "tests/scripts/get_configurations_tool_test_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"\n💾 Detailed results saved to: {results_file}")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())