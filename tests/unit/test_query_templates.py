"""Unit tests for query templates."""

import pytest
from datetime import datetime, timedelta

from src.query.query_templates import (
    QueryTemplateEngine,
    QueryTemplate,
    TemplateCategory,
    QueryPriority,
    QueryParameter,
    SubQuery,
    ExpandedQuery
)


class TestQueryTemplateEngine:
    """Test the query template engine."""
    
    @pytest.fixture
    def engine(self):
        """Create a query template engine instance."""
        return QueryTemplateEngine()
    
    def test_template_initialization(self, engine):
        """Test that all 10 templates are initialized."""
        templates = engine.list_templates()
        assert len(templates) >= 10
        
        # Check specific templates exist
        expected_ids = [
            "emergency_server_down",
            "password_recovery",
            "change_investigation",
            "impact_assessment",
            "security_audit",
            "network_connectivity",
            "backup_verification",
            "service_health",
            "config_drift",
            "incident_root_cause"
        ]
        
        template_ids = [t.id for t in templates]
        for expected_id in expected_ids:
            assert expected_id in template_ids
    
    def test_get_template(self, engine):
        """Test getting a specific template."""
        template = engine.get_template("emergency_server_down")
        
        assert template is not None
        assert template.id == "emergency_server_down"
        assert template.name == "Emergency Server Down"
        assert template.category == TemplateCategory.EMERGENCY
        assert len(template.parameters) > 0
        assert len(template.sub_queries) > 0
    
    def test_list_templates_by_category(self, engine):
        """Test filtering templates by category."""
        emergency_templates = engine.list_templates(
            category=TemplateCategory.EMERGENCY
        )
        
        assert len(emergency_templates) > 0
        for template in emergency_templates:
            assert template.category == TemplateCategory.EMERGENCY
        
        investigation_templates = engine.list_templates(
            category=TemplateCategory.INVESTIGATION
        )
        
        assert len(investigation_templates) > 0
        for template in investigation_templates:
            assert template.category == TemplateCategory.INVESTIGATION
    
    def test_expand_emergency_server_template(self, engine):
        """Test expanding emergency server down template."""
        parameters = {
            "server_name": "prod-web-01",
            "time_window": 24
        }
        
        result = engine.expand_template("emergency_server_down", parameters)
        
        assert result.template_id == "emergency_server_down"
        assert result.template_name == "Emergency Server Down"
        assert len(result.expanded_queries) > 0
        
        # Check parameter substitution
        for query in result.expanded_queries:
            assert "{{server_name}}" not in query
            assert "{{time_window}}" not in query
            if "$server_name" in query:
                # Parameter is referenced but not substituted in Cypher
                pass
        
        assert "server_name" in result.parameters_used
        assert result.parameters_used["server_name"] == "prod-web-01"
    
    def test_expand_password_recovery_template(self, engine):
        """Test expanding password recovery template."""
        parameters = {
            "system_name": "database-server",
            "password_type": "admin"
        }
        
        result = engine.expand_template("password_recovery", parameters)
        
        assert len(result.expanded_queries) > 0
        assert result.parameters_used["password_type"] == "admin"
        
        # Check queries contain system name
        combined_queries = " ".join(result.expanded_queries)
        assert "database-server" in combined_queries or "$system_name" in combined_queries
    
    def test_required_parameter_validation(self, engine):
        """Test that required parameters are validated."""
        # Missing required parameter
        with pytest.raises(ValueError) as exc_info:
            engine.expand_template("emergency_server_down", {})
        
        assert "Required parameter" in str(exc_info.value)
        assert "server_name" in str(exc_info.value)
    
    def test_default_parameter_values(self, engine):
        """Test that default parameter values are applied."""
        parameters = {
            "system_name": "test-system"
            # password_type should default to "admin"
        }
        
        result = engine.expand_template("password_recovery", parameters)
        
        assert result.parameters_used["password_type"] == "admin"
    
    def test_search_templates(self, engine):
        """Test searching templates by keyword."""
        # Search for password-related templates
        password_templates = engine.search_templates("password")
        
        assert len(password_templates) > 0
        assert any(t.id == "password_recovery" for t in password_templates)
        
        # Search for server-related templates
        server_templates = engine.search_templates("server")
        
        assert len(server_templates) > 0
        assert any(t.id == "emergency_server_down" for t in server_templates)
    
    def test_get_template_suggestions(self, engine):
        """Test getting template suggestions for scenarios."""
        # Server down scenario
        suggestions = engine.get_template_suggestions(
            "Our production server is down and not responding"
        )
        
        assert "emergency_server_down" in suggestions
        assert "impact_assessment" in suggestions
        
        # Password scenario
        suggestions = engine.get_template_suggestions(
            "I need to recover the admin password"
        )
        
        assert "password_recovery" in suggestions
        
        # Security audit scenario
        suggestions = engine.get_template_suggestions(
            "We need to perform a security audit"
        )
        
        assert "security_audit" in suggestions
    
    def test_template_priority_breakdown(self, engine):
        """Test priority breakdown in template metadata."""
        result = engine.expand_template(
            "emergency_server_down",
            {"server_name": "test-server"}
        )
        
        assert "priority_breakdown" in result.metadata
        breakdown = result.metadata["priority_breakdown"]
        
        assert QueryPriority.CRITICAL.value in breakdown
        assert QueryPriority.HIGH.value in breakdown
        assert QueryPriority.MEDIUM.value in breakdown
        
        # Should have some critical queries for emergency
        assert breakdown[QueryPriority.CRITICAL.value] > 0
    
    def test_impact_assessment_template(self, engine):
        """Test impact assessment template."""
        parameters = {
            "target_system": "database-master",
            "impact_depth": 2
        }
        
        result = engine.expand_template("impact_assessment", parameters)
        
        assert len(result.expanded_queries) > 0
        
        # Check for dependency traversal query
        has_dependency_query = any(
            "DEPENDS_ON" in query for query in result.expanded_queries
        )
        assert has_dependency_query
    
    def test_security_audit_template(self, engine):
        """Test security audit template."""
        parameters = {
            "audit_scope": "passwords",
            "days_threshold": 90
        }
        
        result = engine.expand_template("security_audit", parameters)
        
        assert len(result.expanded_queries) > 0
        
        # Check for password and certificate queries
        combined = " ".join(result.expanded_queries)
        assert "Password" in combined
        assert "Certificate" in combined
    
    def test_network_connectivity_template(self, engine):
        """Test network connectivity template."""
        parameters = {
            "source_system": "web-server",
            "target_system": "database-server"
        }
        
        result = engine.expand_template("network_connectivity", parameters)
        
        assert len(result.expanded_queries) > 0
        
        # Check for path finding query
        has_path_query = any(
            "shortestPath" in query for query in result.expanded_queries
        )
        assert has_path_query
    
    def test_change_investigation_template(self, engine):
        """Test change investigation template."""
        parameters = {
            "time_range": 48,
            "change_type": "configuration"
        }
        
        result = engine.expand_template("change_investigation", parameters)
        
        assert len(result.expanded_queries) > 0
        
        # Check for change-related queries
        combined = " ".join(result.expanded_queries)
        assert "Change" in combined
        assert "timestamp" in combined
    
    def test_incident_root_cause_template(self, engine):
        """Test incident root cause analysis template."""
        parameters = {
            "incident_id": "INC-12345",
            "hours_before": 12
        }
        
        result = engine.expand_template("incident_root_cause", parameters)
        
        assert len(result.expanded_queries) > 0
        
        # Check for incident analysis queries
        combined = " ".join(result.expanded_queries)
        assert "Incident" in combined
        assert "INC-12345" in combined or "$incident_id" in combined
    
    def test_estimated_time_calculation(self, engine):
        """Test that estimated execution time is calculated."""
        result = engine.expand_template(
            "emergency_server_down",
            {"server_name": "test"}
        )
        
        assert result.estimated_time_ms > 0
        # Should be proportional to number of queries
        assert result.estimated_time_ms >= len(result.expanded_queries) * 50
    
    def test_sub_query_dependencies(self, engine):
        """Test sub-query dependency handling."""
        template = engine.get_template("emergency_server_down")
        
        # Check sub-queries have proper structure
        for sub_query in template.sub_queries:
            assert sub_query.query
            assert sub_query.purpose
            assert sub_query.priority in QueryPriority
    
    def test_parameter_type_validation(self, engine):
        """Test parameter type information."""
        template = engine.get_template("emergency_server_down")
        
        # Check parameters have types
        for param in template.parameters:
            assert param.value_type in [str, int, bool, float]
            assert param.name
            assert param.description
    
    def test_system_parameters(self, engine):
        """Test that system parameters are added automatically."""
        result = engine.expand_template(
            "password_recovery",
            {"system_name": "test"}
        )
        
        # Should have current_time added
        assert "current_time" in result.parameters_used
        
        # Should be a valid ISO timestamp
        try:
            datetime.fromisoformat(result.parameters_used["current_time"])
        except ValueError:
            pytest.fail("current_time is not a valid ISO timestamp")
    
    def test_template_metadata(self, engine):
        """Test template metadata."""
        template = engine.get_template("emergency_server_down")
        
        assert isinstance(template.metadata, dict)
        
        result = engine.expand_template(
            "emergency_server_down",
            {"server_name": "test"}
        )
        
        assert "category" in result.metadata
        assert "sub_query_count" in result.metadata
        assert result.metadata["sub_query_count"] == len(result.expanded_queries)
    
    def test_all_templates_expandable(self, engine):
        """Test that all templates can be expanded with minimal parameters."""
        templates = engine.list_templates()
        
        for template in templates:
            # Build minimal required parameters
            params = {}
            for param in template.parameters:
                if param.required:
                    if param.value_type == str:
                        params[param.name] = "test_value"
                    elif param.value_type == int:
                        params[param.name] = 1
                    elif param.value_type == bool:
                        params[param.name] = True
            
            # Should not raise an exception
            try:
                result = engine.expand_template(template.id, params)
                assert len(result.expanded_queries) > 0
            except Exception as e:
                pytest.fail(f"Failed to expand template {template.id}: {e}")