#!/usr/bin/env python3
"""Test script for MCP server functionality."""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings


async def test_health_check():
    """Test health check endpoint."""
    print("\n=== Testing Health Check ===")
    
    # Create a simple JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "method": "health",
        "params": {},
        "id": 1
    }
    
    print(f"Request: {json.dumps(request, indent=2)}")
    
    # In a real test, this would connect to the server
    # For now, we'll import and test directly
    from src.mcp.server import ITGlueMCPServer
    
    server = ITGlueMCPServer()
    
    # Find the health tool
    health_tool = None
    for tool in server.server._tools:
        if tool.name == "health":
            health_tool = tool
            break
    
    if health_tool:
        result = await health_tool.function()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if result.get("status") == "healthy":
            print("✅ Health check passed!")
        else:
            print("❌ Health check failed!")
    else:
        print("❌ Health tool not found!")
        

async def test_query():
    """Test query functionality."""
    print("\n=== Testing Query Tool ===")
    
    request = {
        "jsonrpc": "2.0",
        "method": "query",
        "params": {
            "query": "What are the server configurations?",
            "company": "Test Company"
        },
        "id": 2
    }
    
    print(f"Request: {json.dumps(request, indent=2)}")
    
    from src.mcp.server import ITGlueMCPServer
    
    server = ITGlueMCPServer()
    
    # Find the query tool
    query_tool = None
    for tool in server.server._tools:
        if tool.name == "query":
            query_tool = tool
            break
    
    if query_tool:
        result = await query_tool.function(
            query="What are the server configurations?",
            company="Test Company"
        )
        print(f"Response: {json.dumps(result, indent=2)}")
        print("✅ Query tool responded!")
    else:
        print("❌ Query tool not found!")


async def test_list_companies():
    """Test list companies functionality."""
    print("\n=== Testing List Companies ===")
    
    request = {
        "jsonrpc": "2.0",
        "method": "list_companies",
        "params": {},
        "id": 3
    }
    
    print(f"Request: {json.dumps(request, indent=2)}")
    
    from src.mcp.server import ITGlueMCPServer
    
    server = ITGlueMCPServer()
    
    # Find the list_companies tool
    companies_tool = None
    for tool in server.server._tools:
        if tool.name == "list_companies":
            companies_tool = tool
            break
    
    if companies_tool:
        result = await companies_tool.function()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if result.get("success"):
            print(f"✅ Found {result.get('count', 0)} companies!")
        else:
            print("❌ List companies failed!")
    else:
        print("❌ List companies tool not found!")


async def test_websocket_connection():
    """Test WebSocket connection (if server is running)."""
    print("\n=== Testing WebSocket Connection ===")
    
    try:
        import websockets
        
        uri = f"ws://localhost:{settings.mcp_websocket_port or 8001}"
        print(f"Connecting to {uri}...")
        
        try:
            async with websockets.connect(uri, timeout=2) as websocket:
                # Wait for welcome message
                welcome = await websocket.recv()
                print(f"Welcome message: {welcome}")
                
                # Send health check
                request = {
                    "jsonrpc": "2.0",
                    "method": "health",
                    "params": {},
                    "id": 1
                }
                
                await websocket.send(json.dumps(request))
                response = await websocket.recv()
                print(f"Health response: {response}")
                
                print("✅ WebSocket connection successful!")
                
        except (ConnectionRefusedError, OSError):
            print("⚠️  WebSocket server not running (this is normal if running stdio mode)")
            
    except ImportError:
        print("⚠️  websockets package not installed")


def test_environment():
    """Test environment configuration."""
    print("\n=== Testing Environment Configuration ===")
    
    checks = {
        "IT Glue API Key": bool(settings.it_glue_api_key),
        "Database URL": bool(settings.database_url),
        "Neo4j URI": bool(settings.neo4j_uri),
        "Qdrant URL": bool(settings.qdrant_url),
        "Redis URL": bool(settings.redis_url),
        "OpenAI API Key": bool(settings.openai_api_key)
    }
    
    all_good = True
    for name, status in checks.items():
        symbol = "✅" if status else "❌"
        print(f"{symbol} {name}: {'Configured' if status else 'Not configured'}")
        if not status:
            all_good = False
    
    if all_good:
        print("\n✅ All environment variables configured!")
    else:
        print("\n⚠️  Some environment variables are missing. Check your .env file.")
    
    return all_good


async def main():
    """Run all tests."""
    print("=" * 50)
    print("IT Glue MCP Server Test Suite")
    print("=" * 50)
    
    # Test environment first
    env_ok = test_environment()
    
    if not env_ok:
        print("\n⚠️  Fix environment configuration before running server.")
    
    # Test MCP functionality
    await test_health_check()
    await test_query()
    await test_list_companies()
    await test_websocket_connection()
    
    print("\n" + "=" * 50)
    print("Test suite complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())