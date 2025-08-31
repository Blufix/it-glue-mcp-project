"""Unit tests for session context manager."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from collections import deque
import json
from pathlib import Path

from src.context.session_manager import (
    SessionContextManager,
    ConversationSession,
    QueryContext,
    ContextType
)


class TestQueryContext:
    """Test QueryContext dataclass."""
    
    def test_creation(self):
        """Test creating a QueryContext."""
        context = QueryContext(
            query_text="show all passwords",
            timestamp=datetime.now(),
            entities={"organization": ["TestOrg"]},
            intent="retrieval",
            results_count=5,
            success=True
        )
        
        assert context.query_text == "show all passwords"
        assert context.intent == "retrieval"
        assert context.results_count == 5
        assert context.success is True
        

class TestConversationSession:
    """Test ConversationSession dataclass."""
    
    def test_creation(self):
        """Test creating a ConversationSession."""
        session = ConversationSession(
            session_id="test-session",
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        assert session.session_id == "test-session"
        assert isinstance(session.queries, deque)
        assert session.current_organization is None
        assert session.active is True
        
    def test_add_query(self):
        """Test adding queries to session."""
        session = ConversationSession(
            session_id="test",
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        query_context = QueryContext(
            query_text="test query",
            timestamp=datetime.now(),
            entities={"system": ["server1"]},
            intent="retrieval"
        )
        
        session.add_query(query_context)
        
        assert len(session.queries) == 1
        assert session.queries[0] == query_context
        assert "system" in session.entity_mentions
        assert session.entity_mentions["system"]["server1"] == 1
        
    def test_query_limit(self):
        """Test that query history is limited to 5."""
        session = ConversationSession(
            session_id="test",
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        # Add more than 5 queries
        for i in range(10):
            query_context = QueryContext(
                query_text=f"query {i}",
                timestamp=datetime.now()
            )
            session.add_query(query_context)
            
        assert len(session.queries) == 5
        assert session.queries[0].query_text == "query 5"
        assert session.queries[-1].query_text == "query 9"
        
    def test_get_most_mentioned_entities(self):
        """Test getting most mentioned entities."""
        session = ConversationSession(
            session_id="test",
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        # Add queries with entities
        for i in range(3):
            query_context = QueryContext(
                query_text=f"query {i}",
                timestamp=datetime.now(),
                entities={"system": ["server1", "server2"]}
            )
            session.add_query(query_context)
            
        query_context = QueryContext(
            query_text="another query",
            timestamp=datetime.now(),
            entities={"system": ["server1"]}
        )
        session.add_query(query_context)
        
        top_systems = session.get_most_mentioned_entities("system", limit=2)
        assert len(top_systems) == 2
        assert top_systems[0] == ("server1", 4)
        assert top_systems[1] == ("server2", 3)
        

class TestSessionContextManager:
    """Test SessionContextManager class."""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """Create a test manager instance."""
        return SessionContextManager(
            storage_path=str(tmp_path / "sessions"),
            session_timeout_minutes=30,
            max_sessions=10
        )
        
    def test_initialization(self, manager):
        """Test manager initialization."""
        assert len(manager.sessions) == 0
        assert manager.max_sessions == 10
        assert manager.session_timeout == timedelta(minutes=30)
        
    def test_create_session(self, manager):
        """Test creating a new session."""
        session = manager.create_session("test-session")
        
        assert session.session_id == "test-session"
        assert "test-session" in manager.sessions
        assert session.active is True
        
    def test_get_or_create_session(self, manager):
        """Test getting existing or creating new session."""
        # Create new
        session1 = manager.get_or_create_session("session1")
        assert session1.session_id == "session1"
        
        # Get existing
        session2 = manager.get_or_create_session("session1")
        assert session2 is session1
        
        # Test expired session
        session1.last_activity = datetime.now() - timedelta(hours=1)
        session3 = manager.get_or_create_session("session1")
        assert session3 is not session1
        assert session3.active is True
        
    def test_extract_entities(self, manager):
        """Test entity extraction from queries."""
        query = "show passwords for org TestCompany on server prod-web-01"
        entities = manager.extract_entities(query)
        
        assert ContextType.ORGANIZATION.value in entities
        assert "TestCompany" in entities[ContextType.ORGANIZATION.value]
        assert ContextType.SYSTEM.value in entities
        assert "prod-web-01" in entities[ContextType.SYSTEM.value]
        
    def test_extract_network_entities(self, manager):
        """Test network entity extraction."""
        query = "check connectivity to 192.168.1.100"
        entities = manager.extract_entities(query)
        
        assert ContextType.NETWORK.value in entities
        assert "192.168.1.100" in entities[ContextType.NETWORK.value]
        
    def test_extract_timeframe_entities(self, manager):
        """Test timeframe entity extraction."""
        queries = [
            ("changes in last 24 hours", "last 24 hours"),
            ("what happened yesterday", "yesterday"),
            ("logs since monday", "since monday")
        ]
        
        for query, expected in queries:
            entities = manager.extract_entities(query)
            assert ContextType.TIMEFRAME.value in entities
            assert expected in entities[ContextType.TIMEFRAME.value][0].lower()
            
    def test_detect_intent(self, manager):
        """Test intent detection."""
        intents = [
            ("show all passwords", "retrieval"),
            ("server is down with errors", "troubleshooting"),
            ("who changed the configuration", "investigation"),
            ("analyze dependencies for service", "analysis"),
            ("how to configure vpn", "documentation"),
            ("check service status", "monitoring")
        ]
        
        for query, expected_intent in intents:
            intent = manager.detect_intent(query)
            assert intent == expected_intent
            
    def test_process_query(self, manager):
        """Test processing a query."""
        session_id = "test-session"
        query = "show configurations for org Acme on server web-01"
        results = [{"type": "configuration"}]
        
        context = manager.process_query(session_id, query, results)
        
        assert context.query_text == query
        assert context.results_count == 1
        assert context.success is True
        assert ContextType.ORGANIZATION.value in context.entities
        
        # Check session was updated
        session = manager.sessions[session_id]
        assert len(session.queries) == 1
        assert session.current_organization == "Acme"
        assert "web-01" in session.recent_systems
        
    def test_resolve_possessive_reference(self, manager):
        """Test resolving possessive references."""
        session_id = "test-session"
        
        # Set up context
        manager.process_query(session_id, "show details for org Acme", [{"result": "data"}])
        
        # Resolve incomplete query
        resolved = manager.resolve_incomplete_query(session_id, "show its configurations")
        assert "Acme" in resolved
        
    def test_resolve_temporal_reference(self, manager):
        """Test resolving temporal references."""
        session_id = "test-session"
        
        # Set up time context
        manager.process_query(session_id, "changes in last 24 hours", [{"result": "data"}])
        
        # Resolve incomplete query
        resolved = manager.resolve_incomplete_query(session_id, "what was modified")
        assert resolved != "what was modified"  # Should be enhanced
        
    def test_resolve_repetition_reference(self, manager):
        """Test resolving repetition references."""
        session_id = "test-session"
        
        # Set up query history
        manager.process_query(session_id, "show all passwords for Acme", [{"result": "data"}])
        
        # Resolve repetition
        resolved = manager.resolve_incomplete_query(session_id, "run that again")
        assert resolved == "show all passwords for Acme"
        
    def test_fill_missing_context(self, manager):
        """Test filling missing context."""
        session_id = "test-session"
        
        # Set up context
        manager.process_query(session_id, "configurations for org TestCorp", [{"result": "data"}])
        manager.process_query(session_id, "server prod-db-01 status", [{"result": "data"}])
        
        # Test organization context
        resolved = manager.resolve_incomplete_query(session_id, "show all passwords")
        assert "TestCorp" in resolved
        
        # Test system context
        resolved = manager.resolve_incomplete_query(session_id, "show services")
        assert "prod-db-01" in resolved
        
    def test_session_summary(self, manager):
        """Test getting session summary."""
        session_id = "test-session"
        
        # Create session with activity
        manager.process_query(session_id, "org Acme server web-01", [{"result": "data"}])
        manager.process_query(session_id, "org Acme server web-02", [{"result": "data"}])
        manager.process_query(session_id, "service nginx status", [{"result": "data"}])
        
        summary = manager.get_session_summary(session_id)
        
        assert summary["session_id"] == session_id
        assert summary["query_count"] == 3
        assert summary["current_organization"] == "Acme"
        assert "web-01" in summary["recent_systems"]
        assert summary["active"] is True
        
        # Check top entities
        assert "organization" in summary["top_entities"]
        assert summary["top_entities"]["organization"][0]["name"] == "Acme"
        assert summary["top_entities"]["organization"][0]["count"] == 2
        
    def test_cleanup_old_sessions(self, manager):
        """Test cleaning up old sessions."""
        # Create sessions
        for i in range(5):
            session = manager.create_session(f"session-{i}")
            if i < 3:
                # Make old
                session.last_activity = datetime.now() - timedelta(hours=1)
                
        assert len(manager.sessions) == 5
        
        # Cleanup
        manager._cleanup_old_sessions()
        
        assert len(manager.sessions) == 2
        assert "session-3" in manager.sessions
        assert "session-4" in manager.sessions
        
    def test_max_sessions_limit(self, manager):
        """Test max sessions enforcement."""
        # Create max sessions
        for i in range(12):
            manager.create_session(f"session-{i}")
            
        # Should not exceed max_sessions (10)
        assert len(manager.sessions) <= manager.max_sessions
        
    def test_persistence(self, manager, tmp_path):
        """Test session persistence."""
        session_id = "persist-test"
        
        # Create session with data
        manager.process_query(session_id, "test query for org Acme", [{"result": "data"}])
        session = manager.sessions[session_id]
        session.user_preferences = {"theme": "dark"}
        
        # Persist
        manager._persist_session(session)
        
        # Check file exists
        session_file = tmp_path / "sessions" / f"{session_id}.json"
        assert session_file.exists()
        
        # Load and verify
        with open(session_file) as f:
            data = json.load(f)
            
        assert data["session_id"] == session_id
        assert data["current_organization"] == "Acme"
        assert data["user_preferences"]["theme"] == "dark"
        assert len(data["queries"]) == 1
        
    def test_load_sessions(self, tmp_path):
        """Test loading sessions from disk."""
        # Create session file
        session_data = {
            "session_id": "loaded-session",
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "current_organization": "LoadedOrg",
            "recent_systems": ["sys1", "sys2"],
            "recent_services": [],
            "time_context": None,
            "entity_mentions": {"organization": {"LoadedOrg": 1}},
            "user_preferences": {},
            "active": True,
            "queries": [
                {
                    "query_text": "loaded query",
                    "timestamp": datetime.now().isoformat(),
                    "entities": {},
                    "intent": "general",
                    "results_count": 0,
                    "success": True
                }
            ]
        }
        
        sessions_path = tmp_path / "sessions"
        sessions_path.mkdir(parents=True)
        
        with open(sessions_path / "loaded-session.json", 'w') as f:
            json.dump(session_data, f)
            
        # Create manager and load
        manager = SessionContextManager(storage_path=str(sessions_path))
        
        assert "loaded-session" in manager.sessions
        session = manager.sessions["loaded-session"]
        assert session.current_organization == "LoadedOrg"
        assert len(session.queries) == 1
        
    def test_export_session_history(self, manager):
        """Test exporting session history."""
        session_id = "export-test"
        
        # Create session with queries
        manager.process_query(session_id, "query 1", [{"result": "data"}])
        manager.process_query(session_id, "query 2", [])
        
        history = manager.export_session_history(session_id)
        
        assert len(history) == 2
        assert history[0]["query"] == "query 1"
        assert history[0]["success"] is True
        assert history[1]["query"] == "query 2"
        assert history[1]["success"] is False
        
    def test_complex_entity_extraction(self, manager):
        """Test complex entity extraction scenarios."""
        query = (
            "show configuration for server prod-web-01 and prod-web-02 "
            "at location datacenter-east for user admin since yesterday"
        )
        
        entities = manager.extract_entities(query)
        
        assert ContextType.SYSTEM.value in entities
        assert "prod-web-01" in entities[ContextType.SYSTEM.value]
        assert "prod-web-02" in entities[ContextType.SYSTEM.value]
        assert ContextType.LOCATION.value in entities
        assert "datacenter-east" in entities[ContextType.LOCATION.value]
        assert ContextType.USER.value in entities
        assert "admin" in entities[ContextType.USER.value]
        assert ContextType.TIMEFRAME.value in entities
        assert "yesterday" in entities[ContextType.TIMEFRAME.value][0].lower()