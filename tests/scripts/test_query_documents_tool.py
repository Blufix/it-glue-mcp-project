#!/usr/bin/env python3
"""Test script for Query Documents Tool with comprehensive validation."""

import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.cache.manager import CacheManager
from src.mcp.tools.query_documents_tool import QueryDocumentsTool
from src.services.itglue.client import ITGlueClient


class DocumentTestResults:
    """Container for test results and performance metrics."""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.total_documents_found = 0
        self.search_accuracy_scores = []
        self.response_times = []
        self.errors = []
        self.validation_errors = []
        
    def add_test_result(self, success: bool, response_time: float = 0.0):
        """Add a test result."""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
        
        if response_time > 0:
            self.response_times.append(response_time)
    
    def add_documents_found(self, count: int):
        """Add document count."""
        self.total_documents_found += count
    
    def add_accuracy_score(self, score: float):
        """Add search accuracy score."""
        self.search_accuracy_scores.append(score)
    
    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)
    
    def add_validation_error(self, error: str):
        """Add a validation error."""
        self.validation_errors.append(error)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test results summary."""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        avg_accuracy = sum(self.search_accuracy_scores) / len(self.search_accuracy_scores) if self.search_accuracy_scores else 0
        
        return {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "failed_tests": self.tests_failed,
            "success_rate": f"{(self.tests_passed / self.tests_run * 100):.1f}%" if self.tests_run > 0 else "0%",
            "total_documents_found": self.total_documents_found,
            "average_response_time": f"{avg_response_time:.2f}s",
            "search_accuracy": f"{avg_accuracy:.1f}%",
            "errors_count": len(self.errors),
            "validation_errors_count": len(self.validation_errors)
        }


class QueryDocumentsToolTester:
    """Comprehensive tester for Query Documents Tool."""
    
    def __init__(self):
        self.client = None
        self.tool = None
        self.results = DocumentTestResults()
        
    async def setup(self):
        """Initialize the test environment."""
        print("🔧 Setting up Query Documents Tool test environment...")
        
        try:
            # Initialize IT Glue client
            self.client = ITGlueClient()
            
            # Initialize cache manager
            cache_manager = CacheManager()
            
            # Initialize the documents tool
            self.tool = QueryDocumentsTool(self.client, cache_manager)
            
            print("✅ Test environment setup complete")
            return True
            
        except Exception as e:
            print(f"❌ Failed to set up test environment: {e}")
            self.results.add_error(f"Setup failed: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all document tool tests."""
        print("🚀 Starting comprehensive Query Documents Tool tests...")
        start_time = time.time()
        
        # Test individual actions
        test_methods = [
            ("List Faucets documents", self.test_list_faucets_documents),
            ("Document search functionality", self.test_document_search),
            ("Document categories", self.test_document_categories),
            ("Document content retrieval", self.test_document_details),
            ("Semantic search capabilities", self.test_semantic_search),
            ("Error handling and edge cases", self.test_error_handling)
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
            "validation_errors": self.results.validation_errors
        }
        
        # Save results to file
        with open('/home/jamie/projects/itglue-mcp-server/tests/scripts/documents_test_results.json', 'w') as f:
            json.dump(final_results, f, indent=2)
        
        print(f"\n📊 Test Summary:")
        print(f"   Total Tests: {self.results.tests_run}")
        print(f"   Passed: {self.results.tests_passed}")
        print(f"   Failed: {self.results.tests_failed}")
        print(f"   Success Rate: {(self.results.tests_passed / self.results.tests_run * 100):.1f}%")
        print(f"   Documents Found: {self.results.total_documents_found}")
        print(f"   Total Time: {total_time:.2f}s")
        
        return final_results
    
    async def test_list_faucets_documents(self) -> Dict[str, Any]:
        """Test listing documents for Faucets organization."""
        start_time = time.time()
        
        try:
            # Test with explicit organization
            result = await self.tool.execute(
                action="list_all",
                organization="Faucets"
            )
            
            response_time = time.time() - start_time
            
            if not result.get("success", False):
                self.results.add_test_result(False, response_time)
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "response_time": f"{response_time:.2f}s"
                }
            
            data = result.get("data", {})
            documents = data.get("documents", [])
            org_resolved = data.get("organization_name") == "Faucets"
            
            self.results.add_test_result(True, response_time)
            self.results.add_documents_found(len(documents))
            
            # Validate document structure
            for doc in documents[:3]:  # Check first 3 documents
                self._validate_document_structure(doc, "list_faucets_documents")
            
            return {
                "success": True,
                "documents_found": len(documents),
                "organization_resolved": org_resolved,
                "response_time": f"{response_time:.2f}s",
                "sample_documents": [doc.get("name", "Unnamed") for doc in documents[:3]]
            }
            
        except Exception as e:
            self.results.add_test_result(False, time.time() - start_time)
            return {
                "success": False,
                "error": str(e),
                "response_time": f"{time.time() - start_time:.2f}s"
            }
    
    async def test_document_search(self) -> Dict[str, Any]:
        """Test document search functionality."""
        search_terms = [
            "network",
            "security",
            "backup",
            "policy",
            "guide"
        ]
        
        successful_searches = 0
        total_results = 0
        search_details = []
        
        for term in search_terms:
            start_time = time.time()
            
            try:
                result = await self.tool.execute(
                    action="search",
                    query=term,
                    organization="Faucets"
                )
                
                response_time = time.time() - start_time
                
                if result.get("success", False):
                    data = result.get("data", {})
                    documents = data.get("documents", [])
                    count = len(documents)
                    
                    if count > 0:
                        successful_searches += 1
                        total_results += count
                        
                        # Calculate relevance accuracy
                        relevance_score = self._calculate_search_relevance(term, documents)
                        self.results.add_accuracy_score(relevance_score)
                    
                    search_details.append({
                        "term": term,
                        "found": count,
                        "response_time": f"{response_time:.2f}s"
                    })
                    
                    self.results.add_test_result(True, response_time)
                else:
                    self.results.add_test_result(False, response_time)
                    search_details.append({
                        "term": term,
                        "found": 0,
                        "error": result.get("error", "Unknown error")
                    })
                    
            except Exception as e:
                self.results.add_test_result(False, time.time() - start_time)
                search_details.append({
                    "term": term,
                    "found": 0,
                    "error": str(e)
                })
        
        self.results.add_documents_found(total_results)
        
        return {
            "success": successful_searches > 0,
            "terms_tested": len(search_terms),
            "successful_searches": successful_searches,
            "total_results": total_results,
            "success_rate": f"{(successful_searches / len(search_terms) * 100):.1f}%",
            "search_details": search_details
        }
    
    async def test_document_categories(self) -> Dict[str, Any]:
        """Test document category retrieval."""
        start_time = time.time()
        
        try:
            result = await self.tool.execute(
                action="categories",
                organization="Faucets"
            )
            
            response_time = time.time() - start_time
            
            if not result.get("success", False):
                self.results.add_test_result(False, response_time)
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "response_time": f"{response_time:.2f}s"
                }
            
            data = result.get("data", {})
            categories = data.get("categories", [])
            total_docs = data.get("total_documents", 0)
            
            self.results.add_test_result(True, response_time)
            
            # Validate category structure
            for category in categories[:3]:
                if not isinstance(category, dict) or "name" not in category or "count" not in category:
                    self.results.add_validation_error(f"Invalid category structure: {category}")
            
            return {
                "success": True,
                "categories_found": len(categories),
                "total_documents": total_docs,
                "response_time": f"{response_time:.2f}s",
                "top_categories": [cat.get("name", "Unknown") for cat in categories[:5]]
            }
            
        except Exception as e:
            self.results.add_test_result(False, time.time() - start_time)
            return {
                "success": False,
                "error": str(e),
                "response_time": f"{time.time() - start_time:.2f}s"
            }
    
    async def test_document_details(self) -> Dict[str, Any]:
        """Test document detail retrieval."""
        # First get some documents to test details
        try:
            list_result = await self.tool.execute(
                action="list_all",
                organization="Faucets",
                limit=5
            )
            
            if not list_result.get("success", False):
                return {
                    "success": False,
                    "error": "Could not list documents for detail testing"
                }
            
            documents = list_result.get("data", {}).get("documents", [])
            
            if not documents:
                return {
                    "success": False,
                    "error": "No documents available for detail testing"
                }
            
            # Test details for first document
            test_doc = documents[0]
            doc_id = test_doc.get("id")
            
            start_time = time.time()
            
            result = await self.tool.execute(
                action="details",
                document_id=doc_id
            )
            
            response_time = time.time() - start_time
            
            if not result.get("success", False):
                self.results.add_test_result(False, response_time)
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "response_time": f"{response_time:.2f}s"
                }
            
            data = result.get("data", {})
            document = data.get("document", {})
            
            self.results.add_test_result(True, response_time)
            
            # Validate document detail structure
            self._validate_document_structure(document, "document_details", full_detail=True)
            
            return {
                "success": True,
                "document_id": doc_id,
                "document_name": document.get("name", "Unknown"),
                "has_content": bool(document.get("content_preview")),
                "response_time": f"{response_time:.2f}s"
            }
            
        except Exception as e:
            self.results.add_test_result(False)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_semantic_search(self) -> Dict[str, Any]:
        """Test semantic search capabilities."""
        semantic_queries = [
            "How to configure firewall rules",
            "Backup and recovery procedures",
            "User access management policies",
            "Network troubleshooting steps",
            "Security incident response"
        ]
        
        successful_queries = 0
        total_results = 0
        
        for query in semantic_queries:
            start_time = time.time()
            
            try:
                result = await self.tool.execute(
                    action="search",
                    query=query,
                    organization="Faucets"
                )
                
                response_time = time.time() - start_time
                
                if result.get("success", False):
                    data = result.get("data", {})
                    documents = data.get("documents", [])
                    
                    if documents:
                        successful_queries += 1
                        total_results += len(documents)
                        
                        # Check for semantic relevance
                        relevance_score = self._calculate_semantic_relevance(query, documents)
                        self.results.add_accuracy_score(relevance_score)
                    
                    self.results.add_test_result(True, response_time)
                else:
                    self.results.add_test_result(False, response_time)
                    
            except Exception as e:
                self.results.add_test_result(False, time.time() - start_time)
        
        self.results.add_documents_found(total_results)
        
        return {
            "success": successful_queries > 0,
            "queries_tested": len(semantic_queries),
            "successful_queries": successful_queries,
            "total_results": total_results,
            "semantic_accuracy": f"{(successful_queries / len(semantic_queries) * 100):.1f}%"
        }
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling and edge cases."""
        error_tests = []
        
        # Test 1: Invalid action
        try:
            result = await self.tool.execute(action="invalid_action")
            error_tests.append({
                "test": "invalid_action",
                "handled": not result.get("success", True),
                "error": result.get("error", "")
            })
        except Exception as e:
            error_tests.append({
                "test": "invalid_action",
                "handled": True,
                "error": str(e)
            })
        
        # Test 2: Missing required parameter
        try:
            result = await self.tool.execute(action="search")  # Missing query
            error_tests.append({
                "test": "missing_query",
                "handled": not result.get("success", True),
                "error": result.get("error", "")
            })
        except Exception as e:
            error_tests.append({
                "test": "missing_query",
                "handled": True,
                "error": str(e)
            })
        
        # Test 3: Nonexistent organization
        try:
            result = await self.tool.execute(
                action="list_all",
                organization="NonExistentOrganization123"
            )
            error_tests.append({
                "test": "nonexistent_org",
                "handled": not result.get("success", True),
                "error": result.get("error", "")
            })
        except Exception as e:
            error_tests.append({
                "test": "nonexistent_org",
                "handled": True,
                "error": str(e)
            })
        
        # Test 4: Invalid document ID
        try:
            result = await self.tool.execute(
                action="details",
                document_id="invalid-id-123"
            )
            error_tests.append({
                "test": "invalid_document_id",
                "handled": not result.get("success", True),
                "error": result.get("error", "")
            })
        except Exception as e:
            error_tests.append({
                "test": "invalid_document_id",
                "handled": True,
                "error": str(e)
            })
        
        handled_count = sum(1 for test in error_tests if test["handled"])
        
        self.results.add_test_result(handled_count == len(error_tests))
        
        return {
            "success": handled_count == len(error_tests),
            "total_error_tests": len(error_tests),
            "properly_handled": handled_count,
            "error_handling_rate": f"{(handled_count / len(error_tests) * 100):.1f}%",
            "error_tests": error_tests
        }
    
    def _validate_document_structure(self, document: Dict[str, Any], test_context: str, full_detail: bool = False):
        """Validate document structure."""
        required_fields = ["id", "name"]
        if full_detail:
            required_fields.extend(["content_preview", "created_at", "updated_at"])
        
        for field in required_fields:
            if field not in document:
                self.results.add_validation_error(f"{test_context}: Missing field '{field}' in document")
    
    def _calculate_search_relevance(self, query: str, documents: List[Dict[str, Any]]) -> float:
        """Calculate search relevance score."""
        if not documents:
            return 0.0
        
        query_words = query.lower().split()
        relevant_docs = 0
        
        for doc in documents:
            name = (doc.get("name", "") or "").lower()
            content = (doc.get("content_preview", "") or "").lower()
            
            # Check if any query words appear in name or content
            if any(word in name or word in content for word in query_words):
                relevant_docs += 1
        
        return (relevant_docs / len(documents)) * 100
    
    def _calculate_semantic_relevance(self, query: str, documents: List[Dict[str, Any]]) -> float:
        """Calculate semantic search relevance score."""
        if not documents:
            return 0.0
        
        # Simple semantic relevance check based on document types and content themes
        query_lower = query.lower()
        semantic_matches = 0
        
        for doc in documents:
            doc_type = doc.get("document_type", "").lower()
            name = (doc.get("name", "") or "").lower()
            content = (doc.get("content_preview", "") or "").lower()
            
            # Check for semantic alignment
            semantic_score = 0
            
            # Query about configuration and doc is guide/policy
            if "configure" in query_lower or "setup" in query_lower:
                if "guide" in doc_type or "policy" in doc_type or "procedure" in name:
                    semantic_score += 1
            
            # Query about procedures and doc is runbook/guide
            if "procedure" in query_lower or "steps" in query_lower:
                if "runbook" in doc_type or "guide" in doc_type or "checklist" in doc_type:
                    semantic_score += 1
            
            # Query about policies and doc is policy/sop
            if "policy" in query_lower or "management" in query_lower:
                if "policy" in doc_type or "sop" in doc_type:
                    semantic_score += 1
            
            if semantic_score > 0:
                semantic_matches += 1
        
        return (semantic_matches / len(documents)) * 100


async def main():
    """Run the comprehensive test suite."""
    tester = QueryDocumentsToolTester()
    
    # Setup the test environment
    if not await tester.setup():
        print("❌ Failed to set up test environment. Exiting.")
        return
    
    try:
        # Run all tests
        results = await tester.run_all_tests()
        
        print("\n" + "="*80)
        print("📋 QUERY DOCUMENTS TOOL - COMPREHENSIVE TEST REPORT")
        print("="*80)
        
        summary = results["summary"]
        print(f"🎯 Overall Results:")
        print(f"   • Tests Run: {summary['total_tests']}")
        print(f"   • Success Rate: {summary['success_rate']}")
        print(f"   • Documents Found: {summary['total_documents_found']}")
        print(f"   • Average Response Time: {summary['average_response_time']}")
        print(f"   • Search Accuracy: {summary['search_accuracy']}")
        
        if summary['errors_count'] > 0:
            print(f"⚠️  Errors Encountered: {summary['errors_count']}")
        
        if summary['validation_errors_count'] > 0:
            print(f"🔍 Validation Issues: {summary['validation_errors_count']}")
        
        print(f"\n📁 Results saved to: tests/scripts/documents_test_results.json")
        print(f"⏱️  Total execution time: {results['total_execution_time']}")
        
    except Exception as e:
        print(f"💥 Test execution failed: {e}")
        return


if __name__ == "__main__":
    asyncio.run(main())