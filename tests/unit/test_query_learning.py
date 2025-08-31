"""Unit tests for query learning and personalization system."""

import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from src.ml.query_learning import (
    QueryLearningEngine,
    QueryPersonalizer,
    QueryPattern,
    UserProfile
)


class TestQueryLearningEngine:
    """Test suite for QueryLearningEngine."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def learning_engine(self, temp_storage):
        """Create learning engine instance."""
        return QueryLearningEngine(storage_path=temp_storage)
    
    @pytest.mark.asyncio
    async def test_record_query(self, learning_engine):
        """Test recording queries for learning."""
        query_data = {
            'user_id': 'user123',
            'query_text': 'show all servers for Microsoft',
            'query_type': 'list',
            'success': True,
            'execution_time': 150.0,
            'organization_id': 'org456'
        }
        
        await learning_engine.record_query(query_data)
        
        # Check user profile created
        assert 'user123' in learning_engine.user_profiles
        profile = learning_engine.user_profiles['user123']
        assert len(profile.query_history) == 1
        assert profile.typical_query_types['list'] == 1
    
    @pytest.mark.asyncio
    async def test_pattern_learning(self, learning_engine):
        """Test pattern learning from multiple queries."""
        # Record same query pattern multiple times
        for i in range(5):
            query_data = {
                'user_id': f'user{i}',
                'query_text': 'find password for server DB01',
                'query_type': 'password',
                'success': True if i < 4 else False,
                'execution_time': 100.0 + i * 10,
                'organization_id': 'org456'
            }
            await learning_engine.record_query(query_data)
        
        # Check pattern was learned
        patterns = list(learning_engine.patterns.values())
        assert len(patterns) > 0
        
        password_pattern = next(
            (p for p in patterns if p.query_type == 'password'),
            None
        )
        assert password_pattern is not None
        assert password_pattern.success_count == 4
        assert password_pattern.failure_count == 1
        assert password_pattern.confidence_score > 0
    
    @pytest.mark.asyncio
    async def test_get_suggestions(self, learning_engine):
        """Test getting query suggestions."""
        # Build query history
        queries = [
            'show all servers for Microsoft',
            'show all servers for Amazon',
            'show all configurations for Google',
            'find password for server DB01',
            'find password for server WEB02'
        ]
        
        for i, query in enumerate(queries):
            await learning_engine.record_query({
                'user_id': 'user123',
                'query_text': query,
                'query_type': 'list' if 'show' in query else 'password',
                'success': True,
                'execution_time': 100.0,
                'organization_id': 'org456'
            })
        
        # Get suggestions
        suggestions = await learning_engine.get_suggestions(
            'show all',
            'user123',
            {'organization_id': 'org456'}
        )
        
        assert len(suggestions) > 0
        assert any('show all' in s['query'].lower() for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_record_correction(self, learning_engine):
        """Test recording query corrections."""
        # Record original query
        await learning_engine.record_query({
            'user_id': 'user123',
            'query_text': 'find pasword for server',
            'query_type': 'password',
            'success': False,
            'execution_time': 100.0
        })
        
        # Record correction
        await learning_engine.record_correction(
            'find pasword for server',
            'find password for server',
            'user123'
        )
        
        # Check correction was recorded
        profile = learning_engine.user_profiles.get('user123')
        assert profile is not None
        assert 'find pasword for server' in profile.correction_patterns
        assert profile.correction_patterns['find pasword for server'] == 'find password for server'
    
    @pytest.mark.asyncio
    async def test_follow_up_queries(self, learning_engine):
        """Test recording follow-up queries."""
        # Record initial query
        await learning_engine.record_query({
            'user_id': 'user123',
            'query_text': 'show server DB01 configuration',
            'query_type': 'configuration',
            'success': True,
            'execution_time': 100.0
        })
        
        # Record follow-up
        await learning_engine.record_follow_up(
            'show server DB01 configuration',
            'show server DB01 passwords',
            'user123'
        )
        
        # Check follow-up was recorded
        patterns = list(learning_engine.patterns.values())
        config_pattern = next(
            (p for p in patterns if 'configuration' in p.query_text),
            None
        )
        
        if config_pattern:
            assert 'show server DB01 passwords' in config_pattern.follow_up_queries
    
    @pytest.mark.asyncio
    async def test_entity_extraction(self, learning_engine):
        """Test entity extraction from queries."""
        entities = learning_engine._extract_entities(
            'show server WEB01 at 192.168.1.100 for company Microsoft'
        )
        
        assert 'server' in entities
        assert 'WEB01' in entities['server']
        assert 'ip_address' in entities
        assert '192.168.1.100' in entities['ip_address']
        assert 'organization' in entities
        assert 'Microsoft' in entities['organization']
    
    @pytest.mark.asyncio
    async def test_personalization_stats(self, learning_engine):
        """Test getting personalization statistics."""
        # Build query history
        for i in range(10):
            await learning_engine.record_query({
                'user_id': 'user123',
                'query_text': f'query {i}',
                'query_type': 'list' if i % 2 == 0 else 'password',
                'success': i < 8,
                'execution_time': 100.0 + i * 10,
                'organization_id': 'org456'
            })
        
        stats = await learning_engine.get_personalization_stats('user123')
        
        assert stats['personalized'] is True
        assert stats['total_queries'] == 10
        assert stats['success_rate'] == 0.8
        assert len(stats['top_query_types']) > 0
    
    @pytest.mark.asyncio
    async def test_contextual_suggestions(self, learning_engine):
        """Test contextual query suggestions."""
        # Record morning queries
        morning_queries = [
            'check overnight alerts',
            'review backup status',
            'check overnight alerts for Microsoft'
        ]
        
        for query in morning_queries:
            await learning_engine.record_query({
                'user_id': 'user123',
                'query_text': query,
                'query_type': 'audit',
                'success': True,
                'execution_time': 100.0
            })
        
        # Get contextual suggestions
        suggestions = await learning_engine._get_contextual_suggestions(
            'check',
            learning_engine.user_profiles['user123'],
            {}
        )
        
        # Should get time-based suggestions
        assert len(suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_pattern_confidence_calculation(self, learning_engine):
        """Test pattern confidence score calculation."""
        pattern = QueryPattern(
            pattern_id='test123',
            query_text='test query',
            query_type='test',
            entity_types=[],
            success_count=8,
            failure_count=2,
            last_used=datetime.now()
        )
        
        confidence = learning_engine._calculate_confidence(pattern)
        
        # Should have high confidence (80% success rate)
        assert confidence > 0.7
        
        # Old pattern should have lower confidence
        old_pattern = QueryPattern(
            pattern_id='old123',
            query_text='old query',
            query_type='test',
            entity_types=[],
            success_count=8,
            failure_count=2,
            last_used=datetime.now() - timedelta(days=30)
        )
        
        old_confidence = learning_engine._calculate_confidence(old_pattern)
        assert old_confidence < confidence
    
    @pytest.mark.asyncio
    async def test_pattern_merging(self, learning_engine):
        """Test merging similar patterns."""
        # Create similar patterns
        learning_engine.patterns['pat1'] = QueryPattern(
            pattern_id='pat1',
            query_text='show all servers',
            query_type='list',
            entity_types=[],
            success_count=5,
            failure_count=1
        )
        
        learning_engine.patterns['pat2'] = QueryPattern(
            pattern_id='pat2',
            query_text='show all server',  # Very similar
            query_type='list',
            entity_types=[],
            success_count=3,
            failure_count=0
        )
        
        merged = learning_engine._merge_similar_patterns()
        
        # Should merge similar patterns
        assert merged > 0
        assert len(learning_engine.patterns) == 1
    
    @pytest.mark.asyncio
    async def test_storage_persistence(self, temp_storage):
        """Test pattern and profile persistence."""
        engine1 = QueryLearningEngine(storage_path=temp_storage)
        
        # Record some data
        await engine1.record_query({
            'user_id': 'user123',
            'query_text': 'test query',
            'query_type': 'test',
            'success': True,
            'execution_time': 100.0
        })
        
        # Save data
        engine1._save_patterns()
        engine1._save_user_profiles()
        
        # Create new engine and load data
        engine2 = QueryLearningEngine(storage_path=temp_storage)
        
        # Check data was loaded
        assert 'user123' in engine2.user_profiles
        assert len(engine2.patterns) > 0


class TestQueryPersonalizer:
    """Test suite for QueryPersonalizer."""
    
    @pytest.fixture
    def personalizer(self):
        """Create personalizer instance."""
        engine = QueryLearningEngine(storage_path=tempfile.mkdtemp())
        return QueryPersonalizer(engine)
    
    @pytest.mark.asyncio
    async def test_personalize_query(self, personalizer):
        """Test query personalization."""
        # Build history
        await personalizer.learning_engine.record_query({
            'user_id': 'user123',
            'query_text': 'show all servers',
            'query_type': 'list',
            'success': True,
            'execution_time': 100.0
        })
        
        # Personalize query
        result = await personalizer.personalize_query(
            'show',
            'user123',
            {}
        )
        
        assert 'suggestions' in result
        assert 'user_stats' in result
        assert result['personalization_applied'] is True
    
    @pytest.mark.asyncio
    async def test_session_management(self, personalizer):
        """Test session management."""
        # Start session
        session_id = await personalizer.start_session('user123', 'org456')
        assert session_id in personalizer.active_sessions
        
        # Update context
        await personalizer.update_session_context(
            session_id,
            {'current_page': 'servers'}
        )
        
        session = personalizer.active_sessions[session_id]
        assert 'current_page' in session['context']
        
        # End session
        stats = await personalizer.end_session(session_id)
        assert 'duration_seconds' in stats
        assert session_id not in personalizer.active_sessions
    
    @pytest.mark.asyncio
    async def test_query_correction_suggestion(self, personalizer):
        """Test suggesting query corrections."""
        # Record correction
        await personalizer.learning_engine.record_correction(
            'find pasword',
            'find password',
            'user123'
        )
        
        # Get personalization with correction
        result = await personalizer.personalize_query(
            'find pasword',
            'user123',
            {}
        )
        
        assert 'suggested_correction' in result
        assert result['suggested_correction'] == 'find password'