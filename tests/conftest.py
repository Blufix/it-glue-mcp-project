"""Pytest configuration and shared fixtures."""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Common test fixtures
import pytest
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_cache_manager():
    """Create a mock cache manager."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    return cache


@pytest.fixture
def mock_itglue_client():
    """Create a mock IT Glue client."""
    client = Mock()
    client.get_organizations = AsyncMock(return_value=[])
    client.get_configurations = AsyncMock(return_value=[])
    client.get_passwords = AsyncMock(return_value=[])
    client.get_flexible_assets = AsyncMock(return_value=[])
    return client


@pytest.fixture
def sample_organizations():
    """Sample organization data for testing."""
    return [
        {"id": "1", "name": "Microsoft Corporation"},
        {"id": "2", "name": "Amazon Web Services"},
        {"id": "3", "name": "Google Cloud Platform"},
        {"id": "4", "name": "International Business Machines"},
        {"id": "5", "name": "Hewlett Packard Enterprise"}
    ]


@pytest.fixture
def sample_configurations():
    """Sample configuration data for testing."""
    return [
        {
            "id": "1",
            "name": "Production Server",
            "configuration_type": "Server",
            "organization_id": "1"
        },
        {
            "id": "2",
            "name": "Database Server",
            "configuration_type": "Database",
            "organization_id": "1"
        }
    ]