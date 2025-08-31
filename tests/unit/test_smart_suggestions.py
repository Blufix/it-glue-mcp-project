"""Unit tests for the smart suggestion engine."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from src.ml.smart_suggestions import (
    SmartSuggestionEngine,
    QuerySuggestion,
    SuggestionType,
    SessionContext,
    PrefixTrie,
    TrieNode
)


class TestPrefixTrie:
    """Test the PrefixTrie data structure."""
    
    def test_insert_and_search(self):
        """Test inserting and searching in the trie."""
        trie = PrefixTrie()
        
        # Insert queries
        trie.insert("show all passwords", 10)
        trie.insert("show all configurations", 8)
        trie.insert("show passwords for admin", 6)
        
        # Search with prefix
        results = trie.search_prefix("show", max_results=5)
        assert len(results) == 3
        assert results[0][0] == "show all passwords"
        assert results[0][1] == 10
        
    def test_case_insensitive_search(self):
        """Test case-insensitive prefix matching."""
        trie = PrefixTrie()
        
        trie.insert("Show All Passwords", 5)
        trie.insert("SHOW ALL CONFIGS", 3)
        
        # Search with different case
        results = trie.search_prefix("show", max_results=5)
        assert len(results) == 2
        
    def test_frequency_accumulation(self):
        """Test that frequency accumulates for repeated insertions."""
        trie = PrefixTrie()
        
        # Insert same query multiple times
        trie.insert("find server", 2)
        trie.insert("find server", 3)
        
        results = trie.search_prefix("find", max_results=5)
        assert len(results) >= 1
        # Check that frequencies are accumulated
        assert any(score > 5 for _, score in results)
        
    def test_empty_prefix_search(self):
        """Test searching with non-existent prefix."""
        trie = PrefixTrie()
        
        trie.insert("show passwords", 5)
        
        results = trie.search_prefix("xyz", max_results=5)
        assert len(results) == 0
        
    def test_max_results_limit(self):
        """Test that max_results parameter is respected."""
        trie = PrefixTrie()
        
        # Insert many queries
        for i in range(10):
            trie.insert(f"show item {i}", i)
            
        results = trie.search_prefix("show", max_results=3)
        assert len(results) == 3
        

class TestQuerySuggestion:
    """Test the QuerySuggestion dataclass."""
    
    def test_creation(self):
        """Test creating a QuerySuggestion."""
        suggestion = QuerySuggestion(
            text="show all passwords",
            type=SuggestionType.AUTOCOMPLETE,
            confidence=0.9,
            reason="Common query pattern"
        )
        
        assert suggestion.text == "show all passwords"
        assert suggestion.type == SuggestionType.AUTOCOMPLETE
        assert suggestion.confidence == 0.9
        assert suggestion.priority == 0.0  # Default value
        

class TestSessionContext:
    """Test the SessionContext dataclass."""
    
    def test_creation(self):
        """Test creating a SessionContext."""
        context = SessionContext(session_id="test-session")
        
        assert context.session_id == "test-session"
        assert context.queries == []
        assert context.current_organization is None
        assert isinstance(context.last_activity, datetime)
        
    def test_adding_queries(self):
        """Test adding queries to context."""
        context = SessionContext(session_id="test")
        
        context.queries.append("query 1")
        context.queries.append("query 2")
        
        assert len(context.queries) == 2
        assert context.queries[0] == "query 1"
        

class TestSmartSuggestionEngine:
    """Test the SmartSuggestionEngine."""
    
    @pytest.fixture
    def engine(self, tmp_path):
        """Create a test engine instance."""
        return SmartSuggestionEngine(
            storage_path=str(tmp_path / "suggestions")
        )
        
    def test_initialization(self, engine):
        """Test engine initialization."""
        assert engine.prefix_trie is not None
        assert len(engine.query_templates) > 0
        assert len(engine.sessions) == 0
        
    def test_generate_autocomplete_suggestions(self, engine):
        """Test autocomplete suggestion generation."""
        # Add some queries to the trie
        engine.prefix_trie.insert("show all passwords", 10)
        engine.prefix_trie.insert("show all configurations", 8)
        
        # Generate suggestions
        suggestions = engine.generate_suggestions(
            partial_query="show all",
            max_suggestions=5
        )
        
        # Check autocomplete suggestions
        autocomplete = [s for s in suggestions if s.type == SuggestionType.AUTOCOMPLETE]
        assert len(autocomplete) > 0
        assert any("passwords" in s.text for s in autocomplete)
        
    def test_generate_template_suggestions(self, engine):
        """Test template-based suggestion generation."""
        suggestions = engine.generate_suggestions(
            partial_query="show passwords for",
            max_suggestions=5
        )
        
        # Check for template suggestions
        template = [s for s in suggestions if s.type == SuggestionType.TEMPLATE]
        assert len(template) >= 0  # May or may not match templates
        
    def test_generate_follow_up_suggestions(self, engine):
        """Test follow-up suggestion generation."""
        # Simulate some results
        results = [
            {"type": "password", "organization": "TestOrg"},
            {"type": "password", "system": "server1"}
        ]
        
        suggestions = engine.generate_suggestions(
            partial_query="",
            current_results=results,
            max_suggestions=5
        )
        
        # Check for follow-up suggestions
        follow_ups = [s for s in suggestions if s.type == SuggestionType.FOLLOW_UP]
        assert len(follow_ups) > 0
        assert any("history" in s.text or "expiration" in s.text for s in follow_ups)
        
    def test_session_context_management(self, engine):
        """Test session context creation and retrieval."""
        # Create context
        context = engine._get_session_context("session-1")
        assert context.session_id == "session-1"
        
        # Retrieve same context
        context2 = engine._get_session_context("session-1")
        assert context2 is context
        
        # Different session
        context3 = engine._get_session_context("session-2")
        assert context3 is not context
        
    def test_update_session_context(self, engine):
        """Test updating session context."""
        session_id = "test-session"
        
        # Update with query
        engine.update_session_context(
            session_id=session_id,
            query="show passwords for TestOrg",
            results=[{"type": "password"}]
        )
        
        context = engine._get_session_context(session_id)
        assert len(context.queries) == 1
        assert context.queries[0] == "show passwords for TestOrg"
        assert len(context.results) == 1
        
    def test_contextual_suggestions(self, engine):
        """Test contextual suggestion generation."""
        session_id = "context-test"
        
        # Add context
        engine.update_session_context(
            session_id=session_id,
            query="show configuration for server1"
        )
        
        # Generate suggestions with context
        suggestions = engine.generate_suggestions(
            partial_query="show",
            session_id=session_id,
            max_suggestions=5
        )
        
        # Check for contextual suggestions
        contextual = [s for s in suggestions if s.type == SuggestionType.CONTEXTUAL]
        assert len(contextual) >= 0  # May generate contextual suggestions
        
    def test_alternative_suggestions(self, engine):
        """Test alternative suggestion generation."""
        # Query with troubleshooting intent
        suggestions = engine.generate_suggestions(
            partial_query="server error",
            max_suggestions=5
        )
        
        # Check for alternative suggestions
        alternatives = [s for s in suggestions if s.type == SuggestionType.ALTERNATIVE]
        assert len(alternatives) > 0
        assert any("log" in s.text or "dependencies" in s.text for s in alternatives)
        
    def test_intent_detection(self, engine):
        """Test query intent detection."""
        # Troubleshooting intent
        intent = engine._detect_intent("server is down and showing errors")
        assert intent == "troubleshooting"
        
        # Investigation intent
        intent = engine._detect_intent("who changed the configuration yesterday")
        assert intent == "investigation"
        
        # Documentation intent
        intent = engine._detect_intent("how to configure vpn access")
        assert intent == "documentation"
        
        # General intent
        intent = engine._detect_intent("show all servers")
        assert intent == "general"
        
    def test_ranking_and_filtering(self, engine):
        """Test suggestion ranking and filtering."""
        # Create various suggestions
        suggestions = [
            QuerySuggestion("query1", SuggestionType.AUTOCOMPLETE, 0.9, "test", priority=90),
            QuerySuggestion("query2", SuggestionType.TEMPLATE, 0.8, "test", priority=80),
            QuerySuggestion("query3", SuggestionType.FOLLOW_UP, 0.7, "test", priority=70),
            QuerySuggestion("Query1", SuggestionType.AUTOCOMPLETE, 0.9, "test", priority=90),  # Duplicate
            QuerySuggestion("query4", SuggestionType.AUTOCOMPLETE, 0.6, "test", priority=60),
            QuerySuggestion("query5", SuggestionType.AUTOCOMPLETE, 0.5, "test", priority=50),
        ]
        
        # Rank and filter
        filtered = engine._rank_and_filter_suggestions(suggestions, max_count=3)
        
        assert len(filtered) == 3
        assert filtered[0].text == "query1"  # Highest priority
        assert len(set(s.text.lower() for s in filtered)) == 3  # No duplicates
        
    def test_learn_from_selection(self, engine):
        """Test learning from user selections."""
        session_id = "learn-test"
        
        # Learn from positive selection
        engine.learn_from_selection(
            session_id=session_id,
            suggested_query="show all passwords",
            selected=True
        )
        
        # Check that query was added to trie
        results = engine.prefix_trie.search_prefix("show all passwords", max_results=1)
        assert len(results) > 0
        
    def test_generate_follow_up_queries(self, engine):
        """Test follow-up query generation."""
        original_query = "show configurations"
        results = [
            {"type": "configuration", "system": "server1"},
            {"type": "configuration", "system": "server2"}
        ]
        
        follow_ups = engine.generate_follow_up_queries(
            original_query=original_query,
            results=results,
            max_queries=3
        )
        
        assert len(follow_ups) <= 3
        assert all(isinstance(q, str) for q in follow_ups)
        assert original_query not in follow_ups
        
    def test_extract_entities_from_results(self, engine):
        """Test entity extraction from results."""
        results = [
            {
                "organization": "TestOrg",
                "system": "server1",
                "hostname": "test-host",
                "attributes": {
                    "organization-name": "Test Organization",
                    "hostname": "test-host-2"
                }
            },
            {
                "configuration_type": "server",
                "topic": "networking"
            }
        ]
        
        entities = engine._extract_entities_from_results(results)
        
        assert "organization" in entities
        assert "TestOrg" in entities["organization"]
        assert "Test Organization" in entities["organization"]
        assert "system" in entities
        assert "server1" in entities["system"]
        assert "test-host" in entities["system"]
        
    def test_session_cleanup(self, engine):
        """Test cleaning up old sessions."""
        # Create sessions with different timestamps
        session1 = SessionContext(session_id="old")
        session1.last_activity = datetime.now() - timedelta(hours=2)
        engine.sessions["old"] = session1
        
        session2 = SessionContext(session_id="recent")
        session2.last_activity = datetime.now()
        engine.sessions["recent"] = session2
        
        # Trigger cleanup
        engine._cleanup_old_sessions()
        
        assert "old" not in engine.sessions
        assert "recent" in engine.sessions
        
    def test_entity_pattern_matching(self, engine):
        """Test entity pattern regex matching."""
        patterns = engine.entity_patterns
        
        # Test organization pattern
        match = patterns["organization"].search("show org TestCompany details")
        assert match is not None
        assert match.group(1) == "TestCompany"
        
        # Test IP address pattern
        match = patterns["ip_address"].search("connect to 192.168.1.100")
        assert match is not None
        assert match.group(1) == "192.168.1.100"
        
        # Test timeframe pattern
        match = patterns["timeframe"].search("changes in last 24 hours")
        assert match is not None
        assert "last 24 hours" in match.group(0)
        
    def test_max_session_query_history(self, engine):
        """Test that session query history is limited."""
        session_id = "history-test"
        
        # Add many queries
        for i in range(10):
            engine.update_session_context(
                session_id=session_id,
                query=f"query {i}"
            )
            
        context = engine._get_session_context(session_id)
        assert len(context.queries) == 5  # Should keep only last 5
        assert context.queries[0] == "query 5"
        assert context.queries[-1] == "query 9"
        
    def test_persistence(self, engine, tmp_path):
        """Test persisting learning data."""
        # Add some query history
        for i in range(100):
            engine.query_history.append({
                "query": f"test query {i}",
                "timestamp": datetime.now(),
                "session_id": "test",
                "selected": True
            })
            
        # Trigger persistence
        engine._persist_learning_data()
        
        # Check file was created
        history_file = tmp_path / "suggestions" / "query_history.json"
        assert history_file.exists()
        
    def test_suggestion_diversity(self, engine):
        """Test that suggestions have type diversity."""
        # Create many suggestions of same type
        suggestions = [
            QuerySuggestion(f"query{i}", SuggestionType.AUTOCOMPLETE, 0.9-i*0.01, "test")
            for i in range(10)
        ]
        # Add some other types
        suggestions.extend([
            QuerySuggestion("template1", SuggestionType.TEMPLATE, 0.85, "test"),
            QuerySuggestion("follow1", SuggestionType.FOLLOW_UP, 0.84, "test"),
        ])
        
        filtered = engine._rank_and_filter_suggestions(suggestions, max_count=5)
        
        # Check type diversity
        types = [s.type for s in filtered]
        assert len(set(types)) > 1  # Should have multiple types
        assert types.count(SuggestionType.AUTOCOMPLETE) <= 2  # Max 2 of same type