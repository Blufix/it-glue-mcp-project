#!/usr/bin/env python3
"""
Test script to verify the organization resolution fix works with actual Query tool.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Import QueryTool directly to avoid package import issues
import importlib.util
query_tool_spec = importlib.util.spec_from_file_location(
    "query_tool", 
    project_root / "src/mcp/tools/query_tool.py"
)
query_tool_module = importlib.util.module_from_spec(query_tool_spec)
query_tool_spec.loader.exec_module(query_tool_module)
QueryTool = query_tool_module.QueryTool
from src.query.engine import QueryEngine
from src.services.itglue.client import ITGlueClient
from src.services.query_engine import QueryEngine as ServiceQueryEngine
from src.cache.manager import CacheManager


async def test_fixed_organization_resolution():
    """Test that the organization resolution fix works with Query tool."""
    print("=== Testing Fixed Organization Resolution ===\n")
    
    try:
        # Initialize components
        api_key = os.getenv('ITGLUE_API_KEY')
        if not api_key:
            print("❌ ERROR: ITGLUE_API_KEY not found")
            return
        
        itglue_client = ITGlueClient(api_key=api_key)
        cache_manager = CacheManager()
        query_engine = QueryEngine(itglue_client=itglue_client, cache=cache_manager)
        
        # Test direct organization resolution
        print("🧪 Test 1: Direct organization resolution")
        print("-" * 45)
        
        test_names = ["Faucets", "faucets", "FAUCETS"]
        for test_name in test_names:
            org_id = await query_engine._resolve_company_to_id(test_name)
            if org_id:
                print(f"✅ '{test_name}' → ID: {org_id}")
            else:
                print(f"❌ '{test_name}' → Failed to resolve")
        
        print()
        
        # Test Query tool with the fixed resolution
        print("🔍 Test 2: Query tool with Faucets organization")
        print("-" * 46)
        
        # Check if CacheService exists, if not, create a simple mock
        try:
            from src.services.cache import CacheService
            cache_service = CacheService()
        except ImportError:
            # Create a simple mock cache service
            class MockCacheService:
                async def get(self, key): return None
                async def set(self, key, value, ttl=None): pass
            cache_service = MockCacheService()
        
        service_query_engine = ServiceQueryEngine()
        query_tool = QueryTool(service_query_engine, cache_service)
        
        # Test the specific query that was failing before
        result = await query_tool.execute(
            query="list all organizations",
            company="Faucets"
        )
        
        if result.get("success", False):
            print("✅ Query tool SUCCESS")
            data = result.get("data", {})
            answer = data.get("answer", "No answer provided")
            confidence = data.get("confidence", "unknown")
            
            print(f"   Answer: {answer}")
            print(f"   Confidence: {confidence}")
            print(f"   Company resolved: {data.get('company', 'not specified')}")
        else:
            print("❌ Query tool FAILED")
            print(f"   Error: {result.get('error', 'Unknown error')}")
        
        print("\n=== Test Complete ===")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_fixed_organization_resolution())