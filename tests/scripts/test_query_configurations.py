#!/usr/bin/env python3
"""
Quick test to check if the Query tool can access configuration data.

Since there's no direct get_configurations MCP tool, we need to test if
configurations are accessible through the Query tool.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.mcp.server import ITGlueMCPServer


async def test_query_configurations():
    """Test if Query tool can access configuration data."""
    print("🔍 Testing Query tool for configuration data access...")
    
    try:
        server = ITGlueMCPServer()
        await server._initialize_components()
        
        # Get the query tool
        query_tool = server.server.tools.get('query')
        if not query_tool:
            print("❌ Query tool not found")
            return False
        
        # Test configuration-related queries
        config_queries = [
            "show configurations",
            "find server configurations",
            "list all configuration items",
            "show network configurations"
        ]
        
        for query in config_queries:
            print(f"\n📋 Testing query: '{query}'")
            start_time = time.time()
            
            try:
                response = await query_tool(query=query, company="Faucets")
                duration = (time.time() - start_time) * 1000
                
                if isinstance(response, str):
                    response_data = json.loads(response)
                else:
                    response_data = response
                
                success = response_data.get("success", False)
                results = response_data.get("results", [])
                
                print(f"  Success: {success}")
                print(f"  Results: {len(results)} items")
                print(f"  Duration: {duration:.1f}ms")
                
                if results:
                    sample = results[0]
                    print(f"  Sample result keys: {list(sample.keys())}")
                    if 'entity_type' in sample:
                        print(f"  Entity type: {sample['entity_type']}")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        print("\n✅ Configuration query testing completed")
        return True
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_query_configurations())