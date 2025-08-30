"""Integration tests for MCP protocol compliance."""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from io import StringIO

from src.mcp.server import ITGlueMCPServer
from tests.fixtures.mock_data import (
    get_mock_organizations,
    get_mock_configurations,
    get_mock_search_results
)


@pytest.fixture
async def mcp_server():
    """Create MCP server for testing."""
    server = ITGlueMCPServer()
    
    # Mock components
    server.query_engine = Mock()
    server.search_engine = Mock()
    server.sync_orchestrator = Mock()
    server.cache_manager = Mock()
    server.itglue_client = Mock()
    server._initialized = True
    
    return server


@pytest.mark.asyncio
async def test_mcp_query_tool(mcp_server):
    """Test MCP query tool end-to-end."""
    # Setup mock response
    query_response = {
        "success": True,
        "data": {
            "ip": "192.168.1.100",
            "name": "Office Printer",
            "type": "printer"
        },
        "confidence": 0.92,
        "source_ids": ["entity-1"],
        "timestamp": "2024-01-30T12:00:00Z"
    }
    
    mcp_server.query_engine.process_query = AsyncMock(return_value=query_response)
    
    # Get the query tool
    tools = mcp_server.server.list_tools()
    query_tool = next((t for t in tools if t.name == "query"), None)
    assert query_tool is not None
    
    # Execute query
    result = await query_tool.fn(
        query="What's the printer IP for Happy Frog?",
        company="Happy Frog"
    )
    
    # Verify result
    assert result["success"] is True
    assert "data" in result
    assert result["data"]["ip"] == "192.168.1.100"
    assert result["confidence"] == 0.92
    
    # Verify query engine was called
    mcp_server.query_engine.process_query.assert_called_once_with(
        query="What's the printer IP for Happy Frog?",
        company="Happy Frog"
    )


@pytest.mark.asyncio
async def test_mcp_search_tool(mcp_server):
    """Test MCP search tool."""
    # Setup mock search results
    from src.search import HybridSearchResult
    
    search_results = [
        HybridSearchResult(
            id="result-1",
            entity_id="config-1",
            score=0.92,
            payload={"name": "Main Router", "type": "router"}
        ),
        HybridSearchResult(
            id="result-2",
            entity_id="config-3",
            score=0.85,
            payload={"name": "Office Printer", "type": "printer"}
        )
    ]
    
    mcp_server.search_engine.search = AsyncMock(return_value=search_results)
    
    # Get the search tool
    tools = mcp_server.server.list_tools()
    search_tool = next((t for t in tools if t.name == "search"), None)
    assert search_tool is not None
    
    # Execute search
    result = await search_tool.fn(
        query="router configuration",
        limit=10,
        filters={"entity_type": "router"}
    )
    
    # Verify result
    assert result["success"] is True
    assert "results" in result
    assert len(result["results"]) == 2
    assert result["results"][0]["score"] == 0.92
    
    # Verify search engine was called
    mcp_server.search_engine.search.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_list_companies_tool(mcp_server):
    """Test MCP list companies tool."""
    # Setup mock organizations
    from src.services.itglue.models import Organization
    
    mock_orgs = [
        Organization(**org) for org in get_mock_organizations()
    ]
    
    mcp_server.itglue_client.get_organizations = AsyncMock(return_value=mock_orgs)
    mcp_server.itglue_client.__aenter__ = AsyncMock(return_value=mcp_server.itglue_client)
    mcp_server.itglue_client.__aexit__ = AsyncMock()
    
    # Get the list_companies tool
    tools = mcp_server.server.list_tools()
    list_companies_tool = next((t for t in tools if t.name == "list_companies"), None)
    assert list_companies_tool is not None
    
    # Execute tool
    result = await list_companies_tool.fn()
    
    # Verify result
    assert result["success"] is True
    assert "companies" in result
    assert len(result["companies"]) == 3
    assert result["companies"][0]["name"] == "Happy Frog Inc"
    assert result["companies"][0]["type"] == "Customer"


@pytest.mark.asyncio
async def test_mcp_sync_data_tool(mcp_server):
    """Test MCP sync data tool."""
    # Setup mock sync response
    sync_stats = {
        "started_at": "2024-01-30T12:00:00Z",
        "completed_at": "2024-01-30T12:05:00Z",
        "total_synced": 150,
        "entity_types": {
            "organizations": {"synced": 10},
            "configurations": {"synced": 50},
            "passwords": {"synced": 30}
        }
    }
    
    mcp_server.sync_orchestrator.sync_all = AsyncMock(return_value=sync_stats)
    mcp_server.sync_orchestrator.sync_organization = AsyncMock(return_value=sync_stats)
    
    # Get the sync_data tool
    tools = mcp_server.server.list_tools()
    sync_tool = next((t for t in tools if t.name == "sync_data"), None)
    assert sync_tool is not None
    
    # Test full sync
    result = await sync_tool.fn(full_sync=True)
    
    assert result["success"] is True
    assert "stats" in result
    assert result["stats"]["total_synced"] == 150
    
    mcp_server.sync_orchestrator.sync_all.assert_called_once_with(full_sync=True)
    
    # Test organization sync
    result = await sync_tool.fn(organization_id="org-1")
    
    assert result["success"] is True
    mcp_server.sync_orchestrator.sync_organization.assert_called_once_with("org-1")


@pytest.mark.asyncio
async def test_mcp_health_tool(mcp_server):
    """Test MCP health check tool."""
    # Get the health tool
    tools = mcp_server.server.list_tools()
    health_tool = next((t for t in tools if t.name == "health"), None)
    assert health_tool is not None
    
    # Execute health check
    result = await health_tool.fn()
    
    # Verify result
    assert result["status"] == "healthy"
    assert "version" in result
    assert "components" in result
    assert result["components"]["mcp_server"] == "healthy"
    assert result["components"]["query_engine"] == "healthy"
    assert result["components"]["search_engine"] == "healthy"


@pytest.mark.asyncio
async def test_mcp_tool_registration():
    """Test that all required MCP tools are registered."""
    server = ITGlueMCPServer()
    
    # Get all registered tools
    tools = server.server.list_tools()
    tool_names = [tool.name for tool in tools]
    
    # Verify required tools are registered
    required_tools = [
        "query",
        "search",
        "health",
        "list_companies",
        "sync_data"
    ]
    
    for tool_name in required_tools:
        assert tool_name in tool_names, f"Tool '{tool_name}' not registered"


@pytest.mark.asyncio
async def test_mcp_error_handling(mcp_server):
    """Test MCP error handling."""
    # Setup query engine to raise an error
    mcp_server.query_engine.process_query = AsyncMock(
        side_effect=Exception("Database connection failed")
    )
    
    # Get the query tool
    tools = mcp_server.server.list_tools()
    query_tool = next((t for t in tools if t.name == "query"), None)
    
    # Execute query that will fail
    result = await query_tool.fn(
        query="Test query",
        company="Test Co"
    )
    
    # Verify error response
    assert result["success"] is False
    assert "error" in result
    assert "Database connection failed" in result["error"]


@pytest.mark.asyncio
async def test_mcp_initialization():
    """Test MCP server component initialization."""
    server = ITGlueMCPServer()
    
    # Initially not initialized
    assert server._initialized is False
    assert server.query_engine is None
    assert server.search_engine is None
    
    # Mock database manager
    with patch('src.mcp.server.db_manager') as mock_db:
        mock_db.initialize = AsyncMock()
        mock_db.create_tables = AsyncMock()
        
        # Mock cache manager
        with patch('src.mcp.server.CacheManager') as MockCache:
            mock_cache = Mock()
            mock_cache.connect = AsyncMock()
            MockCache.return_value = mock_cache
            
            # Mock search
            with patch('src.mcp.server.HybridSearch') as MockSearch:
                mock_search = Mock()
                mock_search.semantic_search = Mock()
                mock_search.semantic_search.initialize_collection = AsyncMock()
                MockSearch.return_value = mock_search
                
                # Initialize components
                await server._initialize_components()
    
    # Verify initialization
    assert server._initialized is True
    assert server.query_engine is not None
    assert server.search_engine is not None
    assert server.cache_manager is not None
    assert server.itglue_client is not None
    assert server.sync_orchestrator is not None


@pytest.mark.asyncio
async def test_mcp_query_with_no_results(mcp_server):
    """Test MCP query tool when no results are found."""
    # Setup empty response
    query_response = {
        "success": False,
        "message": "No data available",
        "data": None,
        "confidence": 0.0,
        "source_ids": [],
        "timestamp": "2024-01-30T12:00:00Z"
    }
    
    mcp_server.query_engine.process_query = AsyncMock(return_value=query_response)
    
    # Get the query tool
    tools = mcp_server.server.list_tools()
    query_tool = next((t for t in tools if t.name == "query"), None)
    
    # Execute query
    result = await query_tool.fn(
        query="What's the configuration for NonExistentCompany?",
        company="NonExistentCompany"
    )
    
    # Verify result
    assert result["success"] is False
    assert result["message"] == "No data available"
    assert result["data"] is None
    assert result["confidence"] == 0.0