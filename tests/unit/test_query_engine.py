"""Unit tests for query engine."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.query.engine import QueryEngine
from src.query.parser import QueryParser, ParsedQuery, QueryIntent
from src.query.validator import ZeroHallucinationValidator, ValidationResult


@pytest.fixture
def query_engine():
    """Create query engine for testing."""
    parser = Mock(spec=QueryParser)
    validator = Mock(spec=ZeroHallucinationValidator)
    search = Mock()
    cache = Mock()
    
    engine = QueryEngine(
        parser=parser,
        validator=validator,
        search=search,
        cache=cache
    )
    
    return engine


@pytest.mark.asyncio
async def test_query_parsing():
    """Test natural language query parsing."""
    parser = QueryParser()
    
    # Test GET_ATTRIBUTE query
    result = parser.parse("What's the router IP for Company A?")
    assert result.intent == QueryIntent.GET_ATTRIBUTE
    assert result.entity_type == "router"
    assert result.company == "Company A"
    assert "ip" in result.attributes
    
    # Test LIST_ENTITIES query
    result = parser.parse("List all servers")
    assert result.intent == QueryIntent.LIST_ENTITIES
    assert result.entity_type == "server"
    
    # Test SEARCH query
    result = parser.parse("Search for printers with IP 192.168.1.100")
    assert result.intent == QueryIntent.SEARCH
    assert result.entity_type == "printer"
    
    # Test AGGREGATE query
    result = parser.parse("How many routers do we have?")
    assert result.intent == QueryIntent.AGGREGATE
    assert result.entity_type == "router"


@pytest.mark.asyncio
async def test_validation_threshold():
    """Test confidence threshold enforcement."""
    validator = ZeroHallucinationValidator(threshold=0.7)
    
    # Test below threshold
    result = await validator.validate_response(
        response={"ip": "192.168.1.1"},
        source_ids=["doc-123"],
        similarity_scores=[0.6]  # Below threshold
    )
    
    assert not result.valid
    assert "below threshold" in result.message
    assert result.confidence == 0.6
    
    # Test above threshold
    result = await validator.validate_response(
        response={"ip": "192.168.1.1"},
        source_ids=["doc-123"],
        similarity_scores=[0.8]  # Above threshold
    )
    
    assert result.valid
    assert result.confidence == 0.8


@pytest.mark.asyncio
async def test_no_hallucination():
    """Test zero-hallucination guarantee."""
    validator = ZeroHallucinationValidator()
    
    # Test with no sources
    result = await validator.validate_response(
        response={"data": "test"},
        source_ids=[],  # No sources
        similarity_scores=[]
    )
    
    assert not result.valid
    assert result.confidence == 0.0
    assert "No source documents" in result.message


@pytest.mark.asyncio
async def test_process_query_with_cache_hit(query_engine):
    """Test query processing with cache hit."""
    # Setup cache hit
    cached_response = {
        "success": True,
        "data": {"ip": "192.168.1.1"},
        "from_cache": True
    }
    query_engine.cache.get = AsyncMock(return_value=cached_response)
    
    # Process query
    result = await query_engine.process_query(
        query="What's the router IP?",
        company="Test Co"
    )
    
    # Verify cache was checked
    query_engine.cache.get.assert_called_once_with("What's the router IP?", "Test Co")
    
    # Verify cached response returned
    assert result == cached_response


@pytest.mark.asyncio
async def test_process_query_with_cache_miss(query_engine):
    """Test query processing with cache miss."""
    # Setup cache miss
    query_engine.cache.get = AsyncMock(return_value=None)
    query_engine.cache.set = AsyncMock()
    
    # Setup parser
    parsed = ParsedQuery(
        original_query="What's the router IP?",
        intent=QueryIntent.GET_ATTRIBUTE,
        entity_type="router",
        company="Test Co",
        attributes=["ip"]
    )
    query_engine.parser.parse = Mock(return_value=parsed)
    
    # Setup search results
    search_result = Mock(entity_id="entity-1", score=0.9, payload={})
    query_engine.search.search = AsyncMock(return_value=[search_result])
    
    # Setup validation
    validation = ValidationResult(
        valid=True,
        confidence=0.9,
        response={"data": {"ip": "192.168.1.1"}},
        source_ids=["entity-1"]
    )
    query_engine.validator.validate_response = AsyncMock(return_value=validation)
    
    # Mock database access
    with patch('src.query.engine.db_manager') as mock_db:
        mock_session = AsyncMock()
        mock_db.get_session = AsyncMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        
        # Mock entity
        mock_entity = Mock(
            id="entity-1",
            itglue_id="itglue-1",
            name="Main Router",
            entity_type="router",
            attributes={"ip": "192.168.1.1"}
        )
        
        mock_uow = Mock()
        mock_uow.itglue.get_by_id = AsyncMock(return_value=mock_entity)
        mock_uow.query_log.log_query = AsyncMock()
        mock_uow.commit = AsyncMock()
        
        with patch('src.query.engine.UnitOfWork', return_value=mock_uow):
            # Process query
            result = await query_engine.process_query(
                query="What's the router IP?",
                company="Test Co"
            )
    
    # Verify result
    assert result["success"] is True
    assert result["confidence"] == 0.9
    assert "ip" in result["data"]
    
    # Verify cache was set
    query_engine.cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_entity_type_extraction():
    """Test entity type extraction from queries."""
    parser = QueryParser()
    
    test_cases = [
        ("Show me the router configuration", "router"),
        ("List all servers in the datacenter", "server"),
        ("What printers are available?", "printer"),
        ("Find all passwords for the admin", "password"),
        ("Get the main configuration", "configuration"),
        ("Show contacts for the company", "contact"),
        ("List all office locations", "location"),
        ("What flexible assets do we have?", "flexible_asset"),
    ]
    
    for query, expected_type in test_cases:
        result = parser.parse(query)
        assert result.entity_type == expected_type, f"Failed for query: {query}"


@pytest.mark.asyncio
async def test_company_extraction():
    """Test company name extraction from queries."""
    parser = QueryParser()
    
    test_cases = [
        ("What's the router IP for Acme Corp?", "Acme Corp"),
        ("Show servers at Microsoft", "Microsoft"),
        ("List printers in Apple Inc", "Apple"),
        ("Get Happy Frog's configuration", "Happy Frog"),
        ('Find assets for company "Test & Co"', "Test & Co"),
    ]
    
    for query, expected_company in test_cases:
        result = parser.parse(query)
        assert result.company == expected_company, f"Failed for query: {query}"


@pytest.mark.asyncio
async def test_attribute_extraction():
    """Test attribute extraction from queries."""
    parser = QueryParser()
    
    # Test IP extraction
    result = parser.parse("What's the IP address of the router?")
    assert "ip" in result.attributes
    
    # Test hostname extraction
    result = parser.parse("Show me the hostname of the server")
    assert "hostname" in result.attributes
    
    # Test multiple attributes
    result = parser.parse("Get the IP and hostname of the router")
    assert "ip" in result.attributes
    assert "hostname" in result.attributes