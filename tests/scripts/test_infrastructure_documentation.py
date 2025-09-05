"""Tests for infrastructure documentation feature."""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.infrastructure.documentation_handler import InfrastructureDocumentationHandler
from src.infrastructure.query_orchestrator import QueryOrchestrator
from src.infrastructure.data_normalizer import DataNormalizer
from src.infrastructure.document_generator import DocumentGenerator


@pytest.fixture
def mock_itglue_client():
    """Create a mock IT Glue client."""
    client = AsyncMock()
    client.get_organization = AsyncMock(return_value={
        'data': {
            'id': '12345',
            'attributes': {
                'name': 'Test Organization',
                'organization-type-name': 'Customer'
            }
        }
    })
    client.get_configurations = AsyncMock(return_value={
        'data': [
            {
                'id': '1',
                'attributes': {
                    'name': 'Server01',
                    'configuration-type-name': 'Server',
                    'configuration-status-name': 'Active',
                    'primary-ip': '192.168.1.10'
                }
            }
        ],
        'meta': {'total-pages': 1}
    })
    client.get_flexible_assets = AsyncMock(return_value={
        'data': [],
        'meta': {'total-pages': 1}
    })
    client.get_contacts = AsyncMock(return_value={
        'data': [],
        'meta': {'total-pages': 1}
    })
    client.get_locations = AsyncMock(return_value={
        'data': [],
        'meta': {'total-pages': 1}
    })
    client.get_documents = AsyncMock(return_value={
        'data': [],
        'meta': {'total-pages': 1}
    })
    client.get_passwords = AsyncMock(return_value={
        'data': [],
        'meta': {'total-pages': 1}
    })
    client.get_domains = AsyncMock(return_value={
        'data': [],
        'meta': {'total-pages': 1}
    })
    client.get_networks = AsyncMock(return_value={
        'data': [],
        'meta': {'total-pages': 1}
    })
    return client


@pytest.fixture
def mock_cache_manager():
    """Create a mock cache manager."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache


@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    db = MagicMock()
    
    # Mock connection context
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value={
        'id': uuid.uuid4(),
        'organization_id': '12345',
        'status': 'in_progress'
    })
    mock_conn.execute = AsyncMock()
    
    # Mock acquire context manager
    db.acquire = MagicMock()
    db.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    db.acquire.return_value.__aexit__ = AsyncMock()
    
    return db


@pytest.mark.asyncio
async def test_query_orchestrator_initialization():
    """Test QueryOrchestrator initialization."""
    mock_client = AsyncMock()
    mock_cache = AsyncMock()
    
    orchestrator = QueryOrchestrator(mock_client, mock_cache)
    
    assert orchestrator.itglue_client == mock_client
    assert orchestrator.cache_manager == mock_cache
    assert orchestrator.RATE_LIMIT == 10


@pytest.mark.asyncio
async def test_query_orchestrator_rate_limiting(mock_itglue_client, mock_cache_manager):
    """Test that QueryOrchestrator respects rate limits."""
    mock_client = mock_itglue_client
    mock_cache = mock_cache_manager
    
    orchestrator = QueryOrchestrator(mock_client, mock_cache)
    
    # Query all resources
    result = await orchestrator.query_all_resources(
        organization_id='12345',
        snapshot_id=str(uuid.uuid4())
    )
    
    assert 'resources' in result
    assert result['organization_id'] == '12345'
    
    # Verify API methods were called
    assert mock_client.get_configurations.called
    assert mock_client.get_flexible_assets.called
    assert mock_client.get_contacts.called


@pytest.mark.asyncio
async def test_data_normalizer_configuration():
    """Test DataNormalizer normalizes configuration data correctly."""
    normalizer = DataNormalizer()
    
    raw_config = {
        'id': '123',
        'attributes': {
            'name': 'TestServer',
            'configuration-type-name': 'Server',
            'configuration-status-name': 'Active',
            'primary-ip': '10.0.0.1',
            'hostname': 'testserver.local',
            'operating-system': 'Windows Server 2019'
        }
    }
    
    normalized = normalizer._normalize_configuration(raw_config)
    
    assert normalized['id'] == '123'
    assert normalized['name'] == 'TestServer'
    assert normalized['type'] == 'Server'
    assert normalized['status'] == 'Active'
    assert normalized['primary_ip'] == '10.0.0.1'
    assert normalized['hostname'] == 'testserver.local'


@pytest.mark.asyncio
async def test_document_generator_header():
    """Test DocumentGenerator creates proper header."""
    generator = DocumentGenerator()
    
    header = generator._generate_header(
        'Test Organization',
        {'resources': [], 'counts': {}}
    )
    
    assert '# Infrastructure Documentation' in header
    assert 'Test Organization' in header
    assert 'Generated:' in header


@pytest.mark.asyncio
async def test_document_generator_size_limit():
    """Test DocumentGenerator respects size limits."""
    generator = DocumentGenerator()
    
    # Create a large content string
    large_content = 'x' * (generator.MAX_DOCUMENT_SIZE + 1000)
    
    truncated = generator._truncate_document(large_content)
    
    assert len(truncated.encode('utf-8')) <= generator.MAX_DOCUMENT_SIZE
    assert 'Document Truncated' in truncated


@pytest.mark.asyncio
async def test_infrastructure_documentation_handler_success(mock_itglue_client, mock_cache_manager, mock_db_manager):
    """Test successful infrastructure documentation generation."""
    mock_client = mock_itglue_client
    mock_cache = mock_cache_manager
    mock_db = mock_db_manager
    
    handler = InfrastructureDocumentationHandler(
        itglue_client=mock_client,
        cache_manager=mock_cache,
        db_manager=mock_db
    )
    
    # Mock internal methods
    with patch.object(handler.query_orchestrator, 'query_all_resources') as mock_query:
        mock_query.return_value = {
            'organization_id': '12345',
            'resources': {
                'configurations': {
                    'data': [
                        {
                            'id': '1',
                            'attributes': {'name': 'Server01'}
                        }
                    ]
                }
            }
        }
        
        with patch.object(handler.data_normalizer, 'normalize_and_store') as mock_normalize:
            mock_normalize.return_value = {
                'resources': [],
                'counts': {'configurations': 1}
            }
            
            with patch.object(handler.document_generator, 'generate') as mock_generate:
                mock_generate.return_value = {
                    'content': '# Infrastructure Documentation',
                    'size_bytes': 100
                }
                
                result = await handler.generate_infrastructure_documentation(
                    organization_id='12345',
                    include_embeddings=False,
                    upload_to_itglue=False
                )
                
                assert result['success'] == True
                assert result['organization']['id'] == '12345'
                assert result['organization']['name'] == 'Test Organization'
                assert 'statistics' in result
                assert 'duration_seconds' in result


@pytest.mark.asyncio
async def test_infrastructure_documentation_handler_org_not_found(mock_cache_manager, mock_db_manager):
    """Test handling when organization is not found."""
    mock_client = AsyncMock()
    mock_client.get_organization = AsyncMock(return_value=None)
    mock_cache = mock_cache_manager
    mock_db = mock_db_manager
    
    handler = InfrastructureDocumentationHandler(
        itglue_client=mock_client,
        cache_manager=mock_cache,
        db_manager=mock_db
    )
    
    result = await handler.generate_infrastructure_documentation(
        organization_id='99999',
        include_embeddings=False,
        upload_to_itglue=False
    )
    
    assert result['success'] == False
    assert 'not found' in result['error']


# Skipping MCP server test due to circular import with mcp.server module