"""Unit tests for intent classification."""

import pytest
from typing import List

from src.nlp.intent_classifier import (
    IntentClassifier,
    IntentClassification,
    QueryIntent,
    IntentPattern
)


class TestIntentClassifier:
    """Test the intent classifier."""
    
    @pytest.fixture
    def classifier(self):
        """Create an intent classifier instance."""
        return IntentClassifier()
        
    def test_retrieval_intent(self, classifier):
        """Test classification of retrieval queries."""
        queries = [
            "Show all passwords for Acme",
            "List servers in production",
            "Get configuration for web-server",
            "Display network topology",
            "What is the admin password"
        ]
        
        for query in queries:
            result = classifier.classify_intent(query)
            assert result.primary_intent == QueryIntent.RETRIEVAL
            assert result.confidence > 0.5
            assert result.query_strategy == "direct_query"
            
    def test_search_intent(self, classifier):
        """Test classification of search queries."""
        queries = [
            "Find all expired passwords",
            "Search for servers with Windows",
            "Locate configuration files",
            "Where is the backup stored",
            "Look for documentation on VPN"
        ]
        
        for query in queries:
            result = classifier.classify_intent(query)
            assert result.primary_intent == QueryIntent.SEARCH
            assert result.query_strategy == "fuzzy_search"
            
    def test_troubleshooting_intent(self, classifier):
        """Test classification of troubleshooting queries."""
        queries = [
            "Server is down and showing errors",
            "Fix authentication failure",
            "Debug connection timeout",
            "Why is the service not working",
            "Application crashed with error code 500"
        ]
        
        for query in queries:
            result = classifier.classify_intent(query)
            assert result.primary_intent == QueryIntent.TROUBLESHOOTING
            assert result.confidence > 0.5
            assert result.query_strategy == "diagnostic_analysis"
            assert len(result.suggested_actions) > 0
            
    def test_investigation_intent(self, classifier):
        """Test classification of investigation queries."""
        queries = [
            "Who changed the configuration yesterday",
            "When was the password last modified",
            "What modifications were made last week",
            "Show audit trail for admin user",
            "Track recent changes to the firewall"
        ]
        
        for query in queries:
            result = classifier.classify_intent(query)
            assert result.primary_intent == QueryIntent.INVESTIGATION
            assert result.query_strategy == "audit_trail"
            
    def test_root_cause_intent(self, classifier):
        """Test classification of root cause queries."""
        queries = [
            "Find root cause of service failure",
            "What caused the outage",
            "Why did the system crash",
            "Find the source of the problem"
        ]
        
        for query in queries:
            result = classifier.classify_intent(query)
            assert result.primary_intent == QueryIntent.ROOT_CAUSE
            assert result.query_strategy == "root_cause_analysis"
            
    def test_audit_intent(self, classifier):
        """Test classification of audit queries."""
        queries = [
            "Audit password compliance",
            "Check for expired certificates",
            "Review security settings",
            "Find unused accounts",
            "Verify compliance status"
        ]
        
        for query in queries:
            result = classifier.classify_intent(query)
            assert result.primary_intent == QueryIntent.AUDIT
            assert result.query_strategy == "compliance_check"
            
    def test_analysis_intent(self, classifier):
        """Test classification of analysis queries."""
        queries = [
            "Analyze server performance metrics",
            "Examine traffic patterns",
            "How many servers are in production",
            "Evaluate resource usage"
        ]
        
        for query in queries:
            result = classifier.classify_intent(query)
            assert result.primary_intent == QueryIntent.ANALYSIS
            assert result.query_strategy == "statistical_analysis"
            
    def test_comparison_intent(self, classifier):
        """Test classification of comparison queries."""
        queries = [
            "Compare production and staging configs",
            "Diff between current and previous version",
            "What's different between these servers",
            "Show similarities between systems"
        ]
        
        for query in queries:
            result = classifier.classify_intent(query)
            assert result.primary_intent == QueryIntent.COMPARISON
            assert result.query_strategy == "comparative_analysis"
            
    def test_monitoring_intent(self, classifier):
        """Test classification of monitoring queries."""
        queries = [
            "Check server status",
            "Is the service running",
            "Monitor health metrics",
            "Show performance stats",
            "Ping the database server"
        ]
        
        for query in queries:
            result = classifier.classify_intent(query)
            assert result.primary_intent == QueryIntent.MONITORING
            assert result.query_strategy == "status_check"
            
    def test_documentation_intent(self, classifier):
        """Test classification of documentation queries."""
        queries = [
            "How to configure VPN access",
            "Guide for setting up backup",
            "Documentation for API endpoints",
            "Steps to reset password",
            "Tutorial on deployment"
        ]
        
        for query in queries:
            result = classifier.classify_intent(query)
            assert result.primary_intent == QueryIntent.DOCUMENTATION
            assert result.query_strategy == "knowledge_search"
            
    def test_configuration_intent(self, classifier):
        """Test classification of configuration queries."""
        queries = [
            "Configure firewall rules",
            "Setup new server",
            "Install monitoring agent",
            "Deploy application",
            "Enable two-factor authentication"
        ]
        
        for query in queries:
            result = classifier.classify_intent(query)
            assert result.primary_intent == QueryIntent.CONFIGURATION
            assert result.query_strategy == "config_guide"
            
    def test_dependency_intent(self, classifier):
        """Test classification of dependency queries."""
        queries = [
            "What does this service depend on",
            "Show dependencies for web server",
            "List upstream services",
            "What requires database connection"
        ]
        
        for query in queries:
            result = classifier.classify_intent(query)
            assert result.primary_intent == QueryIntent.DEPENDENCY
            assert result.query_strategy == "dependency_graph"
            
    def test_impact_intent(self, classifier):
        """Test classification of impact queries."""
        queries = [
            "What happens if server fails",
            "Impact of database shutdown",
            "Blast radius for this change",
            "What will be affected by upgrade"
        ]
        
        for query in queries:
            result = classifier.classify_intent(query)
            assert result.primary_intent == QueryIntent.IMPACT
            assert result.query_strategy == "impact_analysis"
            
    def test_topology_intent(self, classifier):
        """Test classification of topology queries."""
        queries = [
            "Show network topology",
            "Service map for application",
            "How are systems connected",
            "Architecture diagram"
        ]
        
        for query in queries:
            result = classifier.classify_intent(query)
            assert result.primary_intent == QueryIntent.TOPOLOGY
            assert result.query_strategy == "topology_mapping"
            
    def test_unknown_intent(self, classifier):
        """Test classification of ambiguous queries."""
        queries = [
            "Hello",
            "Thanks",
            "xyz123",
            "..."
        ]
        
        for query in queries:
            result = classifier.classify_intent(query)
            assert result.primary_intent == QueryIntent.UNKNOWN
            assert result.confidence == 0.0
            
    def test_secondary_intents(self, classifier):
        """Test detection of secondary intents."""
        # Query with multiple intents
        query = "Find and fix errors in the configuration"
        result = classifier.classify_intent(query)
        
        # Should have both SEARCH and TROUBLESHOOTING
        assert result.primary_intent in [QueryIntent.SEARCH, QueryIntent.TROUBLESHOOTING]
        assert len(result.secondary_intents) > 0
        
    def test_keyword_matching(self, classifier):
        """Test that matched keywords are tracked."""
        query = "Show all servers with errors and failures"
        result = classifier.classify_intent(query)
        
        assert len(result.keywords_matched) > 0
        assert any(keyword in ["error", "fail", "show"] for keyword in result.keywords_matched)
        
    def test_confidence_scores(self, classifier):
        """Test confidence score calculation."""
        # Clear intent should have high confidence
        clear_query = "Show all passwords"
        clear_result = classifier.classify_intent(clear_query)
        assert clear_result.confidence > 0.7
        
        # Ambiguous query should have lower confidence
        ambiguous_query = "Check the thing"
        ambiguous_result = classifier.classify_intent(ambiguous_query)
        assert ambiguous_result.confidence < 0.7
        
    def test_suggested_actions(self, classifier):
        """Test that appropriate actions are suggested."""
        query = "Server is down"
        result = classifier.classify_intent(query)
        
        assert result.primary_intent == QueryIntent.TROUBLESHOOTING
        assert len(result.suggested_actions) > 0
        assert any("status" in action.lower() for action in result.suggested_actions)
        
    def test_batch_classification(self, classifier):
        """Test batch classification of queries."""
        queries = [
            "Show all servers",
            "Find configuration errors",
            "How to setup VPN"
        ]
        
        results = classifier.classify_batch(queries)
        
        assert len(results) == 3
        assert results[0].primary_intent == QueryIntent.RETRIEVAL
        assert results[1].primary_intent == QueryIntent.SEARCH
        assert results[2].primary_intent == QueryIntent.DOCUMENTATION
        
    def test_intent_distribution(self, classifier):
        """Test getting intent distribution across queries."""
        queries = [
            "Show servers",
            "List configurations",
            "Find errors",
            "Debug issue",
            "How to configure"
        ]
        
        distribution = classifier.get_intent_distribution(queries)
        
        assert QueryIntent.RETRIEVAL in distribution
        assert sum(distribution.values()) == pytest.approx(1.0)
        
    def test_suggest_refinement(self, classifier):
        """Test query refinement suggestions."""
        # Low confidence query
        query = "Check thing"
        result = classifier.classify_intent(query)
        suggestions = classifier.suggest_refinement(query, result)
        
        assert len(suggestions) > 0
        
        # Troubleshooting without error
        trouble_query = "Fix the server"
        trouble_result = classifier.classify_intent(trouble_query)
        trouble_suggestions = classifier.suggest_refinement(trouble_query, trouble_result)
        
        assert any("error" in s.lower() for s in trouble_suggestions)
        
    def test_is_action_query(self, classifier):
        """Test detection of action queries."""
        action_queries = [
            "Configure firewall",
            "Update software",
            "Backup database"
        ]
        
        for query in action_queries:
            result = classifier.classify_intent(query)
            assert classifier.is_action_query(result) is True
            
        non_action_queries = [
            "Show servers",
            "Find documentation",
            "Check status"
        ]
        
        for query in non_action_queries:
            result = classifier.classify_intent(query)
            assert classifier.is_action_query(result) is False
            
    def test_required_permissions(self, classifier):
        """Test permission requirements for intents."""
        # Read-only query
        read_query = "Show all servers"
        read_result = classifier.classify_intent(read_query)
        read_perms = classifier.get_required_permissions(read_result)
        assert "read" in read_perms
        assert "write" not in read_perms
        
        # Write query
        write_query = "Configure server settings"
        write_result = classifier.classify_intent(write_query)
        write_perms = classifier.get_required_permissions(write_result)
        assert "write" in write_perms
        
        # Audit query
        audit_query = "Audit password compliance"
        audit_result = classifier.classify_intent(audit_query)
        audit_perms = classifier.get_required_permissions(audit_result)
        assert "audit" in audit_perms
        
    def test_context_boost(self, classifier):
        """Test context-based confidence boosting."""
        # Query with urgency context
        urgent_query = "urgent: server is down with errors"
        result = classifier.classify_intent(urgent_query)
        
        assert result.primary_intent == QueryIntent.TROUBLESHOOTING
        # Should have boosted confidence due to "urgent"
        assert result.confidence > 0.7
        
    def test_complex_query(self, classifier):
        """Test classification of complex multi-intent query."""
        query = ("Find all servers that failed in the last hour and show "
                "their dependencies to analyze the impact")
                
        result = classifier.classify_intent(query)
        
        # Should identify multiple intents
        assert result.primary_intent in [
            QueryIntent.SEARCH,
            QueryIntent.TROUBLESHOOTING,
            QueryIntent.IMPACT,
            QueryIntent.DEPENDENCY
        ]
        assert len(result.secondary_intents) > 0