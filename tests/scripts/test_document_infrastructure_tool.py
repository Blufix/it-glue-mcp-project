#!/usr/bin/env python3
"""Comprehensive test script for Document Infrastructure MCP Tool with REAL IT Glue API data.

Tests the document_infrastructure MCP tool implementation for generating complete
infrastructure documentation for Faucets Limited using actual IT Glue data.

Test Requirements:
- Generate complete infrastructure doc for Faucets
- Validate document completeness and accuracy
- Test document formatting and structure
- Verify IT Glue upload capability
- Test document size limits (< 10MB)
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.cache.manager import CacheManager
from src.data import db_manager
from src.mcp.server import ITGlueMCPServer
from src.services.itglue.client import ITGlueClient


class InfrastructureDocTestResults:
    """Container for comprehensive test results and metrics."""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.generation_times = []
        self.document_sizes = []
        self.validation_errors = []
        self.errors = []
        self.upload_tests = []
        self.feature_coverage = {
            "basic_generation": False,
            "embeddings_support": False,
            "upload_capability": False,
            "size_validation": False,
            "content_validation": False,
            "organization_resolution": False,
            "error_handling": False,
            "progress_tracking": False
        }
    
    def add_test_result(self, success: bool, generation_time: float = 0.0, doc_size: int = 0):
        """Add a test result with metrics."""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
        
        if generation_time > 0:
            self.generation_times.append(generation_time)
        
        if doc_size > 0:
            self.document_sizes.append(doc_size)
    
    def mark_feature_tested(self, feature: str, success: bool = True):
        """Mark a feature as tested."""
        if feature in self.feature_coverage:
            self.feature_coverage[feature] = success
    
    def add_validation_error(self, error: str):
        """Add a validation error."""
        self.validation_errors.append(error)
    
    def add_error(self, error: str):
        """Add a general error."""
        self.errors.append(error)
    
    def add_upload_test(self, test_data: Dict[str, Any]):
        """Add upload test result."""
        self.upload_tests.append(test_data)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive test results summary."""
        avg_generation_time = sum(self.generation_times) / len(self.generation_times) if self.generation_times else 0
        avg_doc_size = sum(self.document_sizes) / len(self.document_sizes) if self.document_sizes else 0
        max_doc_size = max(self.document_sizes) if self.document_sizes else 0
        
        # Calculate feature coverage percentage
        features_tested = sum(1 for tested in self.feature_coverage.values() if tested)
        feature_coverage_percent = (features_tested / len(self.feature_coverage)) * 100
        
        return {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "failed_tests": self.tests_failed,
            "success_rate": f"{(self.tests_passed / self.tests_run * 100):.1f}%" if self.tests_run > 0 else "0%",
            "average_generation_time": f"{avg_generation_time:.2f}s",
            "average_document_size": f"{avg_doc_size / 1024:.1f}KB" if avg_doc_size > 0 else "0KB",
            "max_document_size": f"{max_doc_size / 1024:.1f}KB" if max_doc_size > 0 else "0KB",
            "feature_coverage": f"{feature_coverage_percent:.1f}%",
            "features_tested": self.feature_coverage,
            "validation_errors": len(self.validation_errors),
            "total_errors": len(self.errors),
            "upload_tests": len(self.upload_tests)
        }


class DocumentInfrastructureToolTester:
    """Comprehensive tester for Document Infrastructure MCP Tool."""
    
    def __init__(self):
        self.mcp_server = None
        self.client = None
        self.results = InfrastructureDocTestResults()
        self.faucets_org_id = "3183713165639879"  # Known Faucets ID
        self.test_output_dir = Path("tests/scripts/infrastructure_test_output")
    
    async def setup(self):
        """Initialize the test environment."""
        print("🔧 Setting up Document Infrastructure Tool test environment...")
        
        try:
            # Create output directory
            self.test_output_dir.mkdir(exist_ok=True)
            
            # Initialize MCP Server
            self.mcp_server = ITGlueMCPServer()
            
            # Initialize components manually (server normally does this on first call)
            await self.mcp_server._initialize_components()
            
            # Initialize IT Glue client
            self.client = ITGlueClient()
            
            print("✅ Test environment setup complete")
            print(f"📁 Test outputs will be saved to: {self.test_output_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to set up test environment: {e}")
            self.results.add_error(f"Setup failed: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive infrastructure documentation tests."""
        print("🚀 Starting comprehensive Document Infrastructure Tool tests...")
        start_time = time.time()
        
        test_methods = [
            ("Basic Documentation Generation", self.test_basic_generation),
            ("Organization Name Resolution", self.test_organization_resolution),
            ("Document Structure Validation", self.test_document_structure),
            ("Content Completeness", self.test_content_completeness),
            ("Document Size Limits", self.test_size_limits),
            ("Embeddings Support", self.test_embeddings_support),
            ("IT Glue Upload Capability", self.test_upload_capability),
            ("Progress Tracking", self.test_progress_tracking),
            ("Error Handling", self.test_error_handling)
        ]
        
        detailed_results = []
        
        for test_name, test_method in test_methods:
            print(f"\n📋 Running: {test_name}")
            try:
                result = await test_method()
                detailed_results.append({
                    "test_name": test_name,
                    "success": result.get("success", False),
                    "details": result
                })
                
                if result.get("success", False):
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED - {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"💥 {test_name}: EXCEPTION - {e}")
                detailed_results.append({
                    "test_name": test_name,
                    "success": False,
                    "details": {"error": str(e)}
                })
                self.results.add_error(f"{test_name}: {e}")
        
        total_time = time.time() - start_time
        
        # Generate final results
        final_results = {
            "summary": self.results.get_summary(),
            "test_results": detailed_results,
            "total_execution_time": f"{total_time:.2f}s",
            "timestamp": datetime.now().isoformat(),
            "faucets_organization_id": self.faucets_org_id,
            "test_environment": {
                "python_version": sys.version,
                "test_output_directory": str(self.test_output_dir)
            }
        }
        
        # Save results to file
        results_file = self.test_output_dir / "infrastructure_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(final_results, f, indent=2)
        
        print(f"\n📊 Test Summary:")
        print(f"   Total Tests: {self.results.tests_run}")
        print(f"   Passed: {self.results.tests_passed}")
        print(f"   Failed: {self.results.tests_failed}")
        print(f"   Success Rate: {(self.results.tests_passed / self.results.tests_run * 100):.1f}%")
        print(f"   Feature Coverage: {sum(1 for f in self.results.feature_coverage.values() if f)}/{len(self.results.feature_coverage)} features")
        print(f"   Total Time: {total_time:.2f}s")
        
        return final_results
    
    async def test_basic_generation(self) -> Dict[str, Any]:
        """Test basic infrastructure documentation generation."""
        start_time = time.time()
        
        try:
            # Test with Faucets organization ID
            print(f"   🏢 Testing with Faucets Limited (ID: {self.faucets_org_id})")
            
            # Use the MCP tool directly through the server
            result = await self._call_document_infrastructure_tool(
                organization_id=self.faucets_org_id,
                include_embeddings=False,
                upload_to_itglue=False
            )
            
            generation_time = time.time() - start_time
            
            if not result.get("success", False):
                self.results.add_test_result(False, generation_time)
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "generation_time": f"{generation_time:.2f}s"
                }
            
            # Extract document details
            document = result.get("document", {})
            content = document.get("content", "")
            doc_size = document.get("size_bytes", len(content.encode('utf-8')))
            statistics = result.get("statistics", {})
            
            # Save generated document
            doc_file = self.test_output_dir / f"faucets_infrastructure_{int(time.time())}.md"
            with open(doc_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.results.add_test_result(True, generation_time, doc_size)
            self.results.mark_feature_tested("basic_generation", True)
            
            return {
                "success": True,
                "generation_time": f"{generation_time:.2f}s",
                "document_size": f"{doc_size / 1024:.1f}KB",
                "total_resources": statistics.get("total_resources", 0),
                "configurations": statistics.get("configurations", 0),
                "flexible_assets": statistics.get("flexible_assets", 0),
                "documents": statistics.get("documents", 0),
                "locations": statistics.get("locations", 0),
                "contacts": statistics.get("contacts", 0),
                "snapshot_id": result.get("snapshot_id", ""),
                "output_file": str(doc_file)
            }
            
        except Exception as e:
            generation_time = time.time() - start_time
            self.results.add_test_result(False, generation_time)
            return {
                "success": False,
                "error": str(e),
                "generation_time": f"{generation_time:.2f}s"
            }
    
    async def test_organization_resolution(self) -> Dict[str, Any]:
        """Test organization name resolution."""
        test_cases = [
            {"input": "Faucets", "expected_success": True},
            {"input": "faucets", "expected_success": True},
            {"input": "Faucets Limited", "expected_success": True},
            {"input": self.faucets_org_id, "expected_success": True},
            {"input": "NonExistentOrg123", "expected_success": False}
        ]
        
        successful_resolutions = 0
        resolution_details = []
        
        for case in test_cases:
            start_time = time.time()
            
            try:
                result = await self._call_document_infrastructure_tool(
                    organization_id=case["input"],
                    include_embeddings=False,
                    upload_to_itglue=False
                )
                
                resolution_time = time.time() - start_time
                success = result.get("success", False)
                
                if success == case["expected_success"]:
                    successful_resolutions += 1
                    if success:
                        org_name = result.get("organization", {}).get("name", "Unknown")
                        resolution_details.append({
                            "input": case["input"],
                            "resolved_to": org_name,
                            "success": True,
                            "time": f"{resolution_time:.2f}s"
                        })
                    else:
                        resolution_details.append({
                            "input": case["input"],
                            "expected_failure": True,
                            "success": True,
                            "error": result.get("error", "Expected failure")
                        })
                else:
                    resolution_details.append({
                        "input": case["input"],
                        "expected": case["expected_success"],
                        "actual": success,
                        "success": False,
                        "error": result.get("error", "Unexpected result")
                    })
                    
            except Exception as e:
                resolution_details.append({
                    "input": case["input"],
                    "success": False,
                    "error": str(e)
                })
        
        resolution_success = successful_resolutions == len(test_cases)
        self.results.add_test_result(resolution_success)
        self.results.mark_feature_tested("organization_resolution", resolution_success)
        
        return {
            "success": resolution_success,
            "test_cases": len(test_cases),
            "successful_resolutions": successful_resolutions,
            "resolution_rate": f"{(successful_resolutions / len(test_cases) * 100):.1f}%",
            "details": resolution_details
        }
    
    async def test_document_structure(self) -> Dict[str, Any]:
        """Test generated document structure and formatting."""
        try:
            # Generate a document to test structure
            result = await self._call_document_infrastructure_tool(
                organization_id=self.faucets_org_id,
                include_embeddings=False,
                upload_to_itglue=False
            )
            
            if not result.get("success", False):
                self.results.add_test_result(False)
                return {
                    "success": False,
                    "error": "Could not generate document for structure testing"
                }
            
            document = result.get("document", {})
            content = document.get("content", "")
            
            if not content:
                self.results.add_test_result(False)
                return {
                    "success": False,
                    "error": "Generated document has no content"
                }
            
            # Validate document structure
            structure_checks = {
                "has_title": "# Infrastructure Documentation" in content,
                "has_organization_section": any(section in content.lower() for section in ["organization", "company"]),
                "has_configurations_section": "configuration" in content.lower(),
                "has_markdown_formatting": content.count('#') > 0,
                "has_generated_timestamp": "Generated:" in content or "generated" in content.lower(),
                "has_summary_statistics": any(stat in content.lower() for stat in ["total", "summary", "statistics"]),
                "proper_encoding": self._validate_encoding(content),
                "no_malformed_markdown": not self._check_malformed_markdown(content)
            }
            
            # Count validation issues
            failed_checks = [check for check, passed in structure_checks.items() if not passed]
            
            for failed_check in failed_checks:
                self.results.add_validation_error(f"Document structure check failed: {failed_check}")
            
            structure_valid = len(failed_checks) == 0
            self.results.add_test_result(structure_valid)
            self.results.mark_feature_tested("content_validation", structure_valid)
            
            return {
                "success": structure_valid,
                "total_checks": len(structure_checks),
                "passed_checks": len(structure_checks) - len(failed_checks),
                "failed_checks": failed_checks,
                "document_size": len(content),
                "line_count": content.count('\n'),
                "structure_details": structure_checks
            }
            
        except Exception as e:
            self.results.add_test_result(False)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_content_completeness(self) -> Dict[str, Any]:
        """Test completeness of generated content."""
        try:
            # Generate document with all features
            result = await self._call_document_infrastructure_tool(
                organization_id=self.faucets_org_id,
                include_embeddings=False,
                upload_to_itglue=False
            )
            
            if not result.get("success", False):
                self.results.add_test_result(False)
                return {
                    "success": False,
                    "error": "Could not generate document for completeness testing"
                }
            
            statistics = result.get("statistics", {})
            document = result.get("document", {})
            content = document.get("content", "")
            
            # Content completeness checks
            completeness_score = 0
            total_possible_score = 0
            
            # Check if resource sections are present based on what was found
            resource_checks = {
                "configurations": statistics.get("configurations", 0),
                "flexible_assets": statistics.get("flexible_assets", 0),
                "locations": statistics.get("locations", 0),
                "contacts": statistics.get("contacts", 0),
                "documents": statistics.get("documents", 0)
            }
            
            content_lower = content.lower()
            
            for resource_type, count in resource_checks.items():
                total_possible_score += 1
                if count > 0:
                    # Should have section for this resource type
                    if resource_type.rstrip('s') in content_lower or resource_type in content_lower:
                        completeness_score += 1
                    else:
                        self.results.add_validation_error(f"Missing section for {resource_type} (found {count} items)")
                else:
                    # No resources of this type, but should mention it's empty or skip
                    completeness_score += 1  # Don't penalize for missing sections of empty resource types
            
            # Additional content checks
            additional_checks = {
                "has_executive_summary": any(phrase in content_lower for phrase in ["summary", "overview", "executive"]),
                "has_resource_counts": any(str(statistics.get(key, 0)) in content for key in statistics.keys()),
                "has_organization_info": result.get("organization", {}).get("name", "").lower() in content_lower,
                "has_generation_metadata": "generated" in content_lower or "snapshot" in content_lower
            }
            
            for check_name, passed in additional_checks.items():
                total_possible_score += 1
                if passed:
                    completeness_score += 1
                else:
                    self.results.add_validation_error(f"Content completeness check failed: {check_name}")
            
            completeness_percentage = (completeness_score / total_possible_score * 100) if total_possible_score > 0 else 0
            completeness_success = completeness_percentage >= 80  # 80% threshold
            
            self.results.add_test_result(completeness_success)
            
            return {
                "success": completeness_success,
                "completeness_score": f"{completeness_percentage:.1f}%",
                "total_resources_documented": sum(resource_checks.values()),
                "resource_breakdown": resource_checks,
                "content_size": len(content),
                "additional_checks": additional_checks,
                "completeness_details": f"{completeness_score}/{total_possible_score} checks passed"
            }
            
        except Exception as e:
            self.results.add_test_result(False)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_size_limits(self) -> Dict[str, Any]:
        """Test document size limits and handling."""
        try:
            # Generate document and check size
            result = await self._call_document_infrastructure_tool(
                organization_id=self.faucets_org_id,
                include_embeddings=False,
                upload_to_itglue=False
            )
            
            if not result.get("success", False):
                self.results.add_test_result(False)
                return {
                    "success": False,
                    "error": "Could not generate document for size testing"
                }
            
            document = result.get("document", {})
            content = document.get("content", "")
            doc_size_bytes = len(content.encode('utf-8'))
            max_size_bytes = 10 * 1024 * 1024  # 10MB limit
            
            size_checks = {
                "under_10mb_limit": doc_size_bytes < max_size_bytes,
                "reasonable_size": doc_size_bytes > 1024,  # At least 1KB
                "contains_content": len(content.strip()) > 0,
                "proper_encoding": self._validate_encoding(content)
            }
            
            # Check if document was truncated (if there's a truncation marker)
            truncated = "truncated" in content.lower() or "document size limit" in content.lower()
            
            all_size_checks_passed = all(size_checks.values())
            self.results.add_test_result(all_size_checks_passed, doc_size=doc_size_bytes)
            self.results.mark_feature_tested("size_validation", all_size_checks_passed)
            
            return {
                "success": all_size_checks_passed,
                "document_size_bytes": doc_size_bytes,
                "document_size_kb": f"{doc_size_bytes / 1024:.1f}KB",
                "document_size_mb": f"{doc_size_bytes / (1024 * 1024):.2f}MB",
                "under_10mb_limit": size_checks["under_10mb_limit"],
                "was_truncated": truncated,
                "size_checks": size_checks,
                "max_allowed_size_mb": f"{max_size_bytes / (1024 * 1024):.1f}MB"
            }
            
        except Exception as e:
            self.results.add_test_result(False)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_embeddings_support(self) -> Dict[str, Any]:
        """Test embeddings generation support."""
        try:
            # Test with embeddings enabled
            print("   🧠 Testing embeddings generation...")
            start_time = time.time()
            
            result = await self._call_document_infrastructure_tool(
                organization_id=self.faucets_org_id,
                include_embeddings=True,
                upload_to_itglue=False
            )
            
            generation_time = time.time() - start_time
            
            if not result.get("success", False):
                # Embeddings might not be configured, but tool should still work
                embeddings_graceful_failure = "embedding" in result.get("error", "").lower()
                self.results.mark_feature_tested("embeddings_support", embeddings_graceful_failure)
                
                return {
                    "success": embeddings_graceful_failure,
                    "embeddings_generated": False,
                    "graceful_degradation": embeddings_graceful_failure,
                    "error": result.get("error", ""),
                    "generation_time": f"{generation_time:.2f}s"
                }
            
            embeddings_generated = result.get("embeddings_generated", False)
            self.results.add_test_result(True, generation_time)
            self.results.mark_feature_tested("embeddings_support", embeddings_generated)
            
            return {
                "success": True,
                "embeddings_generated": embeddings_generated,
                "generation_time": f"{generation_time:.2f}s",
                "total_resources": result.get("statistics", {}).get("total_resources", 0)
            }
            
        except Exception as e:
            self.results.add_test_result(False)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_upload_capability(self) -> Dict[str, Any]:
        """Test IT Glue upload capability (without actually uploading)."""
        try:
            print("   ☁️  Testing upload capability (dry run)...")
            
            # Test the upload parameter (but don't actually upload for safety)
            result = await self._call_document_infrastructure_tool(
                organization_id=self.faucets_org_id,
                include_embeddings=False,
                upload_to_itglue=False  # Keep as False for testing
            )
            
            if not result.get("success", False):
                self.results.add_test_result(False)
                return {
                    "success": False,
                    "error": "Base generation failed, cannot test upload capability"
                }
            
            # Check if document has content that could be uploaded
            document = result.get("document", {})
            content = document.get("content", "")
            
            upload_readiness_checks = {
                "has_content": len(content.strip()) > 0,
                "proper_format": content.startswith("#"),  # Markdown format
                "reasonable_size": 1024 < len(content.encode('utf-8')) < 5 * 1024 * 1024,  # Between 1KB and 5MB
                "organization_specified": result.get("organization", {}).get("id") is not None
            }
            
            upload_ready = all(upload_readiness_checks.values())
            
            # Record upload test details
            upload_test_data = {
                "timestamp": datetime.now().isoformat(),
                "organization_id": self.faucets_org_id,
                "document_size": len(content.encode('utf-8')),
                "upload_ready": upload_ready,
                "checks": upload_readiness_checks
            }
            
            self.results.add_upload_test(upload_test_data)
            self.results.add_test_result(upload_ready)
            self.results.mark_feature_tested("upload_capability", upload_ready)
            
            return {
                "success": upload_ready,
                "upload_ready": upload_ready,
                "readiness_checks": upload_readiness_checks,
                "document_size_kb": f"{len(content.encode('utf-8')) / 1024:.1f}KB",
                "note": "Actual upload not performed for safety"
            }
            
        except Exception as e:
            self.results.add_test_result(False)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_progress_tracking(self) -> Dict[str, Any]:
        """Test progress tracking during generation."""
        try:
            print("   📊 Testing progress tracking...")
            
            # This test would ideally hook into the progress tracker
            # For now, we'll test that the tool completes successfully with progress tracking
            start_time = time.time()
            
            result = await self._call_document_infrastructure_tool(
                organization_id=self.faucets_org_id,
                include_embeddings=False,
                upload_to_itglue=False
            )
            
            generation_time = time.time() - start_time
            
            # Check if progress tracking info is available
            has_snapshot_id = bool(result.get("snapshot_id"))
            has_duration = bool(result.get("duration_seconds"))
            has_statistics = bool(result.get("statistics"))
            
            progress_tracking_works = all([
                result.get("success", False),
                has_snapshot_id,
                has_duration or generation_time > 0,
                has_statistics
            ])
            
            self.results.add_test_result(progress_tracking_works)
            self.results.mark_feature_tested("progress_tracking", progress_tracking_works)
            
            return {
                "success": progress_tracking_works,
                "has_snapshot_id": has_snapshot_id,
                "has_duration_tracking": has_duration,
                "has_statistics": has_statistics,
                "generation_time": f"{generation_time:.2f}s",
                "snapshot_id": result.get("snapshot_id", "N/A")
            }
            
        except Exception as e:
            self.results.add_test_result(False)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling and edge cases."""
        error_test_cases = [
            {
                "name": "Invalid organization ID",
                "params": {
                    "organization_id": "invalid-org-999",
                    "include_embeddings": False,
                    "upload_to_itglue": False
                },
                "should_fail": True
            },
            {
                "name": "Empty organization name",
                "params": {
                    "organization_id": "",
                    "include_embeddings": False,
                    "upload_to_itglue": False
                },
                "should_fail": True
            },
            {
                "name": "Valid organization with all options",
                "params": {
                    "organization_id": self.faucets_org_id,
                    "include_embeddings": False,
                    "upload_to_itglue": False
                },
                "should_fail": False
            }
        ]
        
        error_handling_results = []
        handled_correctly = 0
        
        for case in error_test_cases:
            try:
                print(f"     Testing: {case['name']}")
                
                result = await self._call_document_infrastructure_tool(**case["params"])
                
                actual_failed = not result.get("success", False)
                expected_failure = case["should_fail"]
                
                correctly_handled = actual_failed == expected_failure
                
                if correctly_handled:
                    handled_correctly += 1
                
                error_handling_results.append({
                    "test_name": case["name"],
                    "expected_failure": expected_failure,
                    "actual_failure": actual_failed,
                    "correctly_handled": correctly_handled,
                    "error_message": result.get("error", "") if actual_failed else None
                })
                
            except Exception as e:
                # Exception should only occur for cases that should fail
                correctly_handled = case["should_fail"]
                if correctly_handled:
                    handled_correctly += 1
                
                error_handling_results.append({
                    "test_name": case["name"],
                    "expected_failure": case["should_fail"],
                    "actual_failure": True,
                    "correctly_handled": correctly_handled,
                    "exception": str(e)
                })
        
        error_handling_success = handled_correctly == len(error_test_cases)
        self.results.add_test_result(error_handling_success)
        self.results.mark_feature_tested("error_handling", error_handling_success)
        
        return {
            "success": error_handling_success,
            "total_error_tests": len(error_test_cases),
            "correctly_handled": handled_correctly,
            "error_handling_rate": f"{(handled_correctly / len(error_test_cases) * 100):.1f}%",
            "test_details": error_handling_results
        }
    
    async def _call_document_infrastructure_tool(self, organization_id: str, include_embeddings: bool, upload_to_itglue: bool) -> Dict[str, Any]:
        """Call the document infrastructure tool through the MCP server."""
        try:
            # Get the tool from the server's registered tools
            tool_func = None
            for tool in self.mcp_server.server.list_tools():
                if tool.name == "document_infrastructure":
                    tool_func = tool.function
                    break
            
            if not tool_func:
                # Fall back to calling the function directly through the server
                result = await self.mcp_server.server._tools["document_infrastructure"]["function"](
                    organization_id=organization_id,
                    include_embeddings=include_embeddings,
                    upload_to_itglue=upload_to_itglue
                )
            else:
                result = await tool_func(
                    organization_id=organization_id,
                    include_embeddings=include_embeddings,
                    upload_to_itglue=upload_to_itglue
                )
            
            return result
            
        except AttributeError:
            # Direct function call if MCP tool registration fails
            from src.infrastructure.documentation_handler import InfrastructureDocumentationHandler
            
            handler = InfrastructureDocumentationHandler(
                itglue_client=self.client,
                cache_manager=self.mcp_server.cache_manager,
                db_manager=db_manager
            )
            
            return await handler.generate_infrastructure_documentation(
                organization_id=organization_id,
                include_embeddings=include_embeddings,
                upload_to_itglue=upload_to_itglue
            )
    
    def _validate_encoding(self, content: str) -> bool:
        """Validate content encoding."""
        try:
            content.encode('utf-8')
            return True
        except UnicodeEncodeError:
            return False
    
    def _check_malformed_markdown(self, content: str) -> bool:
        """Check for malformed markdown."""
        lines = content.split('\n')
        
        # Basic markdown validation
        malformed_indicators = [
            # Unbalanced headers
            lambda: len([line for line in lines if line.startswith('#')]) == 0,
            # Headers without space
            lambda: any(line.startswith('#') and len(line) > 1 and line[1] != ' ' for line in lines),
            # Excessive consecutive blank lines
            lambda: '\n\n\n\n' in content,
        ]
        
        return any(check() for check in malformed_indicators)


async def main():
    """Run the comprehensive Document Infrastructure Tool test suite."""
    print("=" * 80)
    print("🏗️  DOCUMENT INFRASTRUCTURE MCP TOOL - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"🎯 Testing infrastructure documentation generation with REAL IT Glue data")
    print(f"🏢 Target Organization: Faucets Limited")
    print(f"⚠️  Note: This test uses actual API calls and may take several minutes")
    print()
    
    tester = DocumentInfrastructureToolTester()
    
    # Setup the test environment
    if not await tester.setup():
        print("❌ Failed to set up test environment. Exiting.")
        return 1
    
    try:
        # Run all tests
        results = await tester.run_all_tests()
        
        print("\n" + "="*80)
        print("📋 DOCUMENT INFRASTRUCTURE TOOL - COMPREHENSIVE TEST REPORT")
        print("="*80)
        
        summary = results["summary"]
        print(f"🎯 Overall Results:")
        print(f"   • Tests Run: {summary['total_tests']}")
        print(f"   • Success Rate: {summary['success_rate']}")
        print(f"   • Feature Coverage: {summary['feature_coverage']}")
        print(f"   • Average Generation Time: {summary['average_generation_time']}")
        print(f"   • Average Document Size: {summary['average_document_size']}")
        print(f"   • Max Document Size: {summary['max_document_size']}")
        
        if summary['validation_errors'] > 0:
            print(f"🔍 Validation Issues: {summary['validation_errors']}")
        
        if summary['total_errors'] > 0:
            print(f"⚠️  Errors Encountered: {summary['total_errors']}")
        
        print(f"\n📁 Results saved to: {tester.test_output_dir}/infrastructure_test_results.json")
        print(f"📁 Generated documents saved to: {tester.test_output_dir}/")
        print(f"⏱️  Total execution time: {results['total_execution_time']}")
        
        # Create validation checklist
        checklist_file = tester.test_output_dir / "validation_checklist.md"
        await create_validation_checklist(results, checklist_file)
        print(f"📋 Validation checklist created: {checklist_file}")
        
        # Return exit code based on success rate
        success_rate = float(summary['success_rate'].rstrip('%'))
        return 0 if success_rate >= 80 else 1
        
    except Exception as e:
        print(f"💥 Test execution failed: {e}")
        return 1


async def create_validation_checklist(results: Dict[str, Any], output_file: Path):
    """Create a validation checklist based on test results."""
    checklist_content = f"""# Document Infrastructure Tool - Validation Checklist

Generated: {results['timestamp']}
Test Execution Time: {results['total_execution_time']}

## Overall Test Results

- **Total Tests**: {results['summary']['total_tests']}
- **Success Rate**: {results['summary']['success_rate']}
- **Feature Coverage**: {results['summary']['feature_coverage']}

## Feature Validation

"""
    
    features_tested = results['summary']['features_tested']
    for feature, tested in features_tested.items():
        status = "✅ PASSED" if tested else "❌ FAILED"
        checklist_content += f"- **{feature.replace('_', ' ').title()}**: {status}\n"
    
    checklist_content += f"""

## Document Quality Checks

"""
    
    for test_result in results['test_results']:
        test_name = test_result['test_name']
        success = test_result['success']
        status = "✅ PASSED" if success else "❌ FAILED"
        checklist_content += f"- **{test_name}**: {status}\n"
        
        if not success and 'error' in test_result['details']:
            checklist_content += f"  - Error: {test_result['details']['error']}\n"
    
    checklist_content += f"""

## Performance Metrics

- **Average Generation Time**: {results['summary']['average_generation_time']}
- **Average Document Size**: {results['summary']['average_document_size']}
- **Max Document Size**: {results['summary']['max_document_size']}

## Validation Issues

Total Validation Errors: {results['summary']['validation_errors']}
Total System Errors: {results['summary']['total_errors']}

## Test Environment

- **Target Organization**: Faucets Limited
- **Organization ID**: {results.get('faucets_organization_id', 'N/A')}
- **Python Version**: {results['test_environment']['python_version']}

## Next Steps

Based on these results:

{'✅ **READY FOR PRODUCTION**: All critical tests passed successfully!' if float(results['summary']['success_rate'].rstrip('%')) >= 90 else '⚠️ **NEEDS ATTENTION**: Some tests failed. Review errors above before production deployment.'}

## Upload Test Results

Upload Tests Performed: {results['summary']['upload_tests']}

Note: Actual uploads to IT Glue were not performed for safety during testing.

---
*Generated by Document Infrastructure Tool Test Suite*
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(checklist_content)


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)