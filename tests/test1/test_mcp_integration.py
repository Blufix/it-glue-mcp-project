#!/usr/bin/env python3
"""Test MCP server integration with semantic search."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def test_mcp_server():
    """Test MCP server search tool."""
    from src.mcp.server import ITGlueMCPServer
    
    print("🔍 Testing MCP Server Integration")
    print("=" * 40)
    
    server = ITGlueMCPServer()
    
    # Test the search tool method directly
    try:
        print("🔧 Testing MCP search tool...")
        
        # Call the search tool function directly
        search_tool = None
        for name, func in server.server.tools.items():
            if name == 'search':
                search_tool = func
                break
        
        if search_tool:
            result = await search_tool(query="server", limit=3)
            
            print(f"✅ MCP Tool Response:")
            print(f"  Success: {result.get('success', False)}")
            
            if result.get('success') and result.get('results'):
                print(f"  Results: {len(result['results'])}")
                for i, item in enumerate(result['results'][:2], 1):
                    name = item.get('name', 'N/A')
                    entity_type = item.get('entity_type', 'N/A')
                    score = item.get('score', 0)
                    print(f"    {i}. {name} ({entity_type}) - {score:.3f}")
            else:
                print(f"  Error: {result.get('error', 'Unknown error')}")
        else:
            print("❌ Search tool not found in MCP server")
            
    except Exception as e:
        print(f"❌ MCP integration error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_server())