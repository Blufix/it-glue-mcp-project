"""Unit tests for Neo4j query builder."""

import pytest
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any

from src.query.neo4j_query_builder import (
    Neo4jQueryBuilder,
    Neo4jQuery,
    RelationshipType,
    NodeType,
    QueryType,
    CypherQuery,
    QueryFilter
)
from src.query.fuzzy_matcher import FuzzyMatcher, MatchResult


class TestNeo4jQueryBuilder:
    """Test the Neo4j query builder."""
    
    @pytest.fixture
    def builder(self):
        """Create a test query builder instance."""
        fuzzy_matcher = Mock(spec=FuzzyMatcher)
        return Neo4jQueryBuilder(fuzzy_matcher=fuzzy_matcher)
        
    @pytest.fixture
    def sample_organizations(self):
        """Sample organizations for testing."""
        return [
            {"id": "org-1", "name": "Acme Corporation"},
            {"id": "org-2", "name": "TechCorp"},
            {"id": "org-3", "name": "Global Systems Inc"}
        ]
        
    def test_initialization(self, builder):
        """Test query builder initialization."""
        assert builder.fuzzy_matcher is not None
        assert len(builder.query_templates) > 0
        assert 'find_organization' in builder.query_templates
        assert 'find_dependencies' in builder.query_templates
        
    def test_build_dependency_query(self, builder, sample_organizations):
        """Test building dependency query."""
        # Setup fuzzy matcher mock
        match_result = MatchResult(
            original="Acme",
            matched="Acme Corporation",
            confidence=0.95,
            match_type="fuzzy",
            entity_id="org-1"
        )
        builder.fuzzy_matcher.match_organization.return_value = [match_result]
        
        entities = {
            "organization": "Acme",
            "configuration": "web-server-01"
        }
        
        query = builder.build_query(
            intent="find_dependencies",
            entities=entities,
            organizations=sample_organizations
        )
        
        assert isinstance(query, Neo4jQuery)
        assert "DEPENDS_ON" in query.cypher
        assert query.parameters["config_name"] == "web-server-01"
        assert query.confidence == 0.95
        assert len(query.fuzzy_matched_entities) == 1
        
    def test_build_impact_analysis_query(self, builder):
        """Test building impact analysis query."""
        builder.fuzzy_matcher.match_organization.return_value = []
        
        entities = {
            "system": "database-server"
        }
        
        query = builder.build_query(
            intent="impact_analysis",
            entities=entities,
            organizations=[]
        )
        
        assert isinstance(query, Neo4jQuery)
        assert "DEPENDS_ON" in query.cypher
        assert "impact_distance" in query.cypher
        assert query.expected_return_type == "impact_list"
        
    def test_build_service_map_query(self, builder):
        """Test building service map query."""
        builder.fuzzy_matcher.match_organization.return_value = []
        
        entities = {
            "application": "user-api",
            "service": "authentication"
        }
        
        query = builder.build_query(
            intent="service_map",
            entities=entities,
            organizations=[]
        )
        
        assert isinstance(query, Neo4jQuery)
        assert "CONNECTS_TO|DEPENDS_ON|USES" in query.cypher
        assert query.expected_return_type == "graph"
        
    def test_build_recent_changes_query(self, builder):
        """Test building recent changes query."""
        builder.fuzzy_matcher.match_organization.return_value = []
        
        entities = {
            "configuration": "firewall-01"
        }
        
        query = builder.build_query(
            intent="recent_changes",
            entities=entities,
            organizations=[]
        )
        
        assert isinstance(query, Neo4jQuery)
        assert "CHANGED" in query.cypher
        assert "datetime()" in query.cypher
        assert query.expected_return_type == "change_list"
        
    def test_build_credential_audit_query(self, builder, sample_organizations):
        """Test building credential audit query."""
        match_result = MatchResult(
            original="TechCorp",
            matched="TechCorp",
            confidence=1.0,
            match_type="exact",
            entity_id="org-2"
        )
        builder.fuzzy_matcher.match_organization.return_value = [match_result]
        
        entities = {
            "organization": "TechCorp"
        }
        
        query = builder.build_query(
            intent="credential_audit",
            entities=entities,
            organizations=sample_organizations
        )
        
        assert isinstance(query, Neo4jQuery)
        assert "Password" in query.cypher
        assert "password_updated_at" in query.cypher
        assert "duration" in query.cypher
        assert query.expected_return_type == "audit_report"
        
    def test_build_network_topology_query(self, builder):
        """Test building network topology query."""
        builder.fuzzy_matcher.match_organization.return_value = []
        
        entities = {
            "location": "datacenter-east"
        }
        
        query = builder.build_query(
            intent="network_topology",
            entities=entities,
            organizations=[]
        )
        
        assert isinstance(query, Neo4jQuery)
        assert "Network Device" in query.cypher
        assert "CONNECTS_TO" in query.cypher
        assert query.parameters["location"] == "datacenter-east"
        
    def test_build_default_query(self, builder):
        """Test building default query when intent not recognized."""
        builder.fuzzy_matcher.match_organization.return_value = []
        
        entities = {
            "type": "Server",
            "os": "Windows"
        }
        
        query = builder.build_query(
            intent="unknown_intent",
            entities=entities,
            organizations=[]
        )
        
        assert isinstance(query, Neo4jQuery)
        assert "Configuration" in query.cypher
        assert query.parameters["config_type"] == "Server"
        assert query.parameters["os"] == "Windows"
        
    def test_fuzzy_organization_matching(self, builder, sample_organizations):
        """Test fuzzy matching of organization names."""
        # Test with typo
        match_result = MatchResult(
            original="Acmi Corp",  # Typo
            matched="Acme Corporation",
            confidence=0.85,
            match_type="fuzzy",
            entity_id="org-1"
        )
        builder.fuzzy_matcher.match_organization.return_value = [match_result]
        
        entities = {
            "organization": "Acmi Corp"
        }
        
        query = builder.build_query(
            intent="find_dependencies",
            entities=entities,
            organizations=sample_organizations
        )
        
        assert query.fuzzy_matched_entities[0].matched == "Acme Corporation"
        assert query.confidence == 0.85
        assert "(?i).*Acme Corporation.*" in query.parameters["org_pattern"]
        
    def test_build_relationship_query(self, builder):
        """Test building relationship traversal query."""
        query = builder.build_relationship_query(
            source_type="Configuration",
            source_id="config-123",
            relationship=RelationshipType.DEPENDS_ON,
            target_type="Service",
            max_depth=3
        )
        
        assert isinstance(query, Neo4jQuery)
        assert "DEPENDS_ON*1..3" in query.cypher
        assert ":Service" in query.cypher
        assert query.parameters["source_id"] == "config-123"
        assert query.confidence == 1.0  # Direct ID query
        
    def test_get_return_type(self, builder):
        """Test getting expected return type for different intents."""
        assert builder._get_return_type("find_dependencies") == "dependency_tree"
        assert builder._get_return_type("impact_analysis") == "impact_list"
        assert builder._get_return_type("service_map") == "graph"
        assert builder._get_return_type("unknown") == "entity_list"
        
    def test_query_with_no_organization(self, builder):
        """Test building query without organization context."""
        builder.fuzzy_matcher.match_organization.return_value = []
        
        entities = {
            "configuration": "server-01"
        }
        
        query = builder.build_query(
            intent="find_dependencies",
            entities=entities,
            organizations=[]
        )
        
        assert query.confidence == 0.5  # Lower confidence without org match
        assert len(query.fuzzy_matched_entities) == 0
        
    def test_query_parameters_escaping(self, builder):
        """Test that query parameters are properly set."""
        builder.fuzzy_matcher.match_organization.return_value = []
        
        entities = {
            "configuration": "server-01'; DROP TABLE--"  # SQL injection attempt
        }
        
        query = builder.build_query(
            intent="find_dependencies",
            entities=entities,
            organizations=[]
        )
        
        # Parameters should be safely passed as parameters, not interpolated
        assert query.parameters["config_name"] == "server-01'; DROP TABLE--"
        assert "$config_name" in query.cypher  # Using parameterized query
        
    def test_relationship_types_enum(self):
        """Test relationship types enum."""
        assert RelationshipType.DEPENDS_ON.value == "DEPENDS_ON"
        assert RelationshipType.BELONGS_TO.value == "BELONGS_TO"
        assert RelationshipType.AUTHENTICATES.value == "AUTHENTICATES"
        
        # Check all relationship types have values
        for rel_type in RelationshipType:
            assert rel_type.value is not None
            assert isinstance(rel_type.value, str)
            
    def test_query_template_structure(self, builder):
        """Test that all query templates have required structure."""
        for template_name, template in builder.query_templates.items():
            # Check that templates use parameters
            assert "$" in template or template_name == "network_topology"  # Some templates might not need params
            
            # Check for MATCH clause
            assert "MATCH" in template
            
            # Check for RETURN clause
            assert "RETURN" in template
            
    def test_multiple_fuzzy_matches(self, builder, sample_organizations):
        """Test handling multiple fuzzy match results."""
        # Return multiple matches
        matches = [
            MatchResult("Global", "Global Systems Inc", 0.9, "fuzzy", "org-3"),
            MatchResult("Global", "Global Tech", 0.8, "fuzzy", "org-4")
        ]
        builder.fuzzy_matcher.match_organization.return_value = matches
        
        entities = {
            "organization": "Global"
        }
        
        query = builder.build_query(
            intent="find_dependencies",
            entities=entities,
            organizations=sample_organizations
        )
        
        # Should use best match (first one)
        assert query.fuzzy_matched_entities[0].matched == "Global Systems Inc"
        assert query.confidence == 0.9
        
    def test_empty_entities(self, builder):
        """Test building query with empty entities."""
        builder.fuzzy_matcher.match_organization.return_value = []
        
        query = builder.build_query(
            intent="find_dependencies",
            entities={},
            organizations=[]
        )
        
        assert isinstance(query, Neo4jQuery)
        # Should still produce a valid query with defaults
        assert query.cypher is not None