"""Unit tests for Neo4j setup and schema management."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from neo4j.exceptions import ServiceUnavailable

from src.database.neo4j_setup import (
    Neo4jConfig,
    Neo4jSchemaManager
)


class TestNeo4jConfig:
    """Test Neo4j configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = Neo4jConfig()
        
        assert config.uri == "bolt://localhost:7687"
        assert config.username == "neo4j"
        assert config.password == "password"
        assert config.database == "itglue"
        assert config.max_connection_pool_size == 50
        
    def test_custom_config(self):
        """Test custom configuration."""
        config = Neo4jConfig(
            uri="bolt://remote:7687",
            username="admin",
            password="secret",
            database="production"
        )
        
        assert config.uri == "bolt://remote:7687"
        assert config.username == "admin"
        assert config.database == "production"
        

class TestNeo4jSchemaManager:
    """Test Neo4j schema manager."""
    
    @pytest.fixture
    def mock_driver(self):
        """Create mock Neo4j driver."""
        driver = MagicMock()
        driver.verify_connectivity.return_value = None
        return driver
        
    @pytest.fixture
    def mock_session(self):
        """Create mock Neo4j session."""
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=None)
        return session
        
    @pytest.fixture
    def manager(self, mock_driver):
        """Create schema manager with mock driver."""
        config = Neo4jConfig()
        with patch('src.database.neo4j_setup.GraphDatabase.driver', return_value=mock_driver):
            manager = Neo4jSchemaManager(config)
        return manager
        
    def test_initialization(self, mock_driver):
        """Test schema manager initialization."""
        config = Neo4jConfig()
        
        with patch('src.database.neo4j_setup.GraphDatabase.driver', return_value=mock_driver):
            manager = Neo4jSchemaManager(config)
            
        assert manager.config == config
        assert manager.driver == mock_driver
        mock_driver.verify_connectivity.assert_called_once()
        
    def test_connection_failure(self):
        """Test handling connection failure."""
        config = Neo4jConfig()
        
        with patch('src.database.neo4j_setup.GraphDatabase.driver') as mock_driver_class:
            mock_driver_class.side_effect = ServiceUnavailable("Connection failed")
            
            with pytest.raises(ServiceUnavailable):
                Neo4jSchemaManager(config)
                
    def test_close_connection(self, manager, mock_driver):
        """Test closing connection."""
        manager.close()
        mock_driver.close.assert_called_once()
        
    def test_initialize_schema(self, manager, mock_driver, mock_session):
        """Test schema initialization."""
        mock_driver.session.return_value = mock_session
        
        manager.initialize_schema()
        
        # Verify session was created with correct database
        mock_driver.session.assert_called_with(database=manager.config.database)
        
        # Verify schema creation methods were called
        # (These are called internally, we just verify session.run was called)
        assert mock_session.run.called
        
    def test_create_constraints(self, manager, mock_session):
        """Test constraint creation."""
        manager._create_constraints(mock_session)
        
        # Check that constraints were created
        calls = mock_session.run.call_args_list
        
        # Verify organization constraints
        assert any("org_id_unique" in str(call) for call in calls)
        assert any("org_name_unique" in str(call) for call in calls)
        
        # Verify other constraints
        assert any("config_id_unique" in str(call) for call in calls)
        assert any("password_id_unique" in str(call) for call in calls)
        
    def test_create_indexes(self, manager, mock_session):
        """Test index creation."""
        manager._create_indexes(mock_session)
        
        calls = mock_session.run.call_args_list
        
        # Verify various indexes
        assert any("org_name_idx" in str(call) for call in calls)
        assert any("config_hostname_idx" in str(call) for call in calls)
        assert any("password_username_idx" in str(call) for call in calls)
        
        # Verify composite indexes
        assert any("config_org_type_idx" in str(call) for call in calls)
        
        # Verify full-text indexes
        assert any("org_search_idx" in str(call) for call in calls)
        
    def test_create_node_labels(self, manager, mock_session):
        """Test node label creation."""
        manager._create_node_labels(mock_session)
        
        calls = mock_session.run.call_args_list
        
        # Verify all node types are created
        node_types = ["Organization", "Configuration", "Password", "Document", 
                     "Asset", "Service", "User", "Network", "Application", "Database"]
        
        for node_type in node_types:
            assert any(node_type in str(call) for call in calls)
            
    def test_initialize_relationships(self, manager, mock_session):
        """Test relationship initialization."""
        # Setup mock to return success
        mock_result = MagicMock()
        mock_session.run.return_value = mock_result
        
        manager._initialize_relationships(mock_session)
        
        calls = mock_session.run.call_args_list
        
        # Verify various relationship types
        assert any("BELONGS_TO" in str(call) for call in calls)
        assert any("DEPENDS_ON" in str(call) for call in calls)
        assert any("AUTHENTICATES" in str(call) for call in calls)
        
    def test_import_organizations(self, manager, mock_session):
        """Test importing organizations."""
        mock_result = MagicMock()
        mock_result.single.return_value = {"imported": 2}
        mock_session.run.return_value = mock_result
        
        organizations = [
            {"id": "org-1", "name": "Org 1"},
            {"id": "org-2", "name": "Org 2"}
        ]
        
        manager._import_organizations(mock_session, organizations)
        
        # Verify query was executed
        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        assert "MERGE (o:Organization" in call_args[0][0]
        assert call_args[1]["organizations"] == organizations
        
    def test_import_configurations(self, manager, mock_session):
        """Test importing configurations."""
        mock_result = MagicMock()
        mock_result.single.return_value = {"imported": 3}
        mock_session.run.return_value = mock_result
        
        configurations = [
            {"id": "cfg-1", "name": "Server 1", "organization_id": "org-1"},
            {"id": "cfg-2", "name": "Server 2", "organization_id": "org-1"},
            {"id": "cfg-3", "name": "Server 3", "organization_id": "org-2"}
        ]
        
        manager._import_configurations(mock_session, configurations)
        
        # Verify query creates configurations and relationships
        call_args = mock_session.run.call_args
        assert "MERGE (c:Configuration" in call_args[0][0]
        assert "BELONGS_TO" in call_args[0][0]
        
    def test_import_passwords(self, manager, mock_session):
        """Test importing passwords."""
        mock_result = MagicMock()
        mock_result.single.return_value = {"imported": 2}
        mock_session.run.return_value = mock_result
        
        passwords = [
            {"id": "pwd-1", "name": "Admin Password", "organization_id": "org-1"},
            {"id": "pwd-2", "name": "Service Account", "organization_id": "org-1"}
        ]
        
        manager._import_passwords(mock_session, passwords)
        
        call_args = mock_session.run.call_args
        assert "MERGE (p:Password" in call_args[0][0]
        assert call_args[1]["passwords"] == passwords
        
    def test_import_data(self, manager, mock_driver, mock_session):
        """Test full data import."""
        mock_driver.session.return_value = mock_session
        mock_result = MagicMock()
        mock_result.single.return_value = {"imported": 1}
        mock_session.run.return_value = mock_result
        
        data = {
            "organizations": [{"id": "org-1", "name": "Test Org"}],
            "configurations": [{"id": "cfg-1", "name": "Server", "organization_id": "org-1"}],
            "passwords": [{"id": "pwd-1", "name": "Password", "organization_id": "org-1"}],
            "documents": [{"id": "doc-1", "name": "Manual", "organization_id": "org-1"}],
            "dependencies": [{"source_id": "cfg-1", "target_id": "cfg-2"}]
        }
        
        manager.import_data(data)
        
        # Verify all import methods were called
        assert mock_session.run.called
        
    def test_get_statistics(self, manager, mock_driver, mock_session):
        """Test getting database statistics."""
        mock_driver.session.return_value = mock_session
        
        # Mock count queries
        def mock_run(query, **kwargs):
            result = MagicMock()
            if "count(n)" in query:
                result.single.return_value = {"count": 10}
            elif "type(r)" in query:
                result.__iter__ = lambda self: iter([
                    {"type": "BELONGS_TO", "count": 20},
                    {"type": "DEPENDS_ON", "count": 15}
                ])
            elif "apoc.meta.stats" in query:
                result.single.return_value = {
                    "nodeCount": 50,
                    "relCount": 35,
                    "propertyKeyCount": 25
                }
            return result
            
        mock_session.run.side_effect = mock_run
        
        stats = manager.get_statistics()
        
        assert "nodes" in stats
        assert "relationships" in stats
        assert "totals" in stats
        
    def test_health_check_success(self, manager, mock_driver, mock_session):
        """Test successful health check."""
        mock_driver.session.return_value = mock_session
        mock_result = MagicMock()
        mock_result.single.return_value = {"health": 1}
        mock_session.run.return_value = mock_result
        
        assert manager.health_check() is True
        
    def test_health_check_failure(self, manager, mock_driver, mock_session):
        """Test failed health check."""
        mock_driver.session.return_value = mock_session
        mock_session.run.side_effect = Exception("Connection failed")
        
        assert manager.health_check() is False
        
    def test_clear_database(self, manager, mock_driver, mock_session):
        """Test clearing database."""
        mock_driver.session.return_value = mock_session
        
        manager.clear_database()
        
        # Verify deletion queries were executed
        calls = mock_session.run.call_args_list
        assert any("DELETE r" in str(call) for call in calls)
        assert any("DELETE n" in str(call) for call in calls)