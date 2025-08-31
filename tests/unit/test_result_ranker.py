"""Unit tests for result ranking and relevance scoring."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from src.ranking.result_ranker import (
    ResultRanker,
    RankingFactors,
    ScoredResult,
    PopularityTracker
)


class TestRankingFactors:
    """Test suite for RankingFactors."""
    
    def test_calculate_total_default_weights(self):
        """Test total score calculation with default weights."""
        factors = RankingFactors(
            fuzzy_score=0.8,
            entity_relevance=0.9,
            recency_score=0.7,
            popularity_score=0.6,
            user_context_score=0.5,
            type_priority=0.8,
            completeness_score=0.9
        )
        
        # Default weights sum to 1.0
        total = factors.calculate_total()
        
        # Manual calculation with default weights
        expected = (
            0.8 * 0.25 +  # fuzzy
            0.9 * 0.20 +  # entity
            0.7 * 0.15 +  # recency
            0.6 * 0.10 +  # popularity
            0.5 * 0.15 +  # user context
            0.8 * 0.10 +  # type priority
            0.9 * 0.05    # completeness
        )
        
        assert abs(total - expected) < 0.001
    
    def test_calculate_total_custom_weights(self):
        """Test total score calculation with custom weights."""
        factors = RankingFactors(
            fuzzy_score=1.0,
            entity_relevance=0.5
        )
        
        custom_weights = {
            'fuzzy_score': 0.7,
            'entity_relevance': 0.3
        }
        
        total = factors.calculate_total(custom_weights)
        expected = 1.0 * 0.7 + 0.5 * 0.3
        
        assert abs(total - expected) < 0.001
    
    def test_score_clamping(self):
        """Test that scores are clamped to 0-1 range."""
        factors = RankingFactors(
            fuzzy_score=2.0,  # Over 1.0
            entity_relevance=2.0
        )
        
        total = factors.calculate_total()
        assert 0.0 <= total <= 1.0


class TestResultRanker:
    """Test suite for ResultRanker."""
    
    @pytest.fixture
    def ranker(self):
        """Create a result ranker instance."""
        return ResultRanker()
    
    @pytest.fixture
    def sample_results(self):
        """Create sample results for testing."""
        now = datetime.now()
        return [
            {
                'id': '1',
                'name': 'Microsoft Server',
                'type': 'configuration',
                'organization_name': 'Microsoft Corp',
                'updated_at': now.isoformat(),
                'description': 'Main production server'
            },
            {
                'id': '2',
                'name': 'Admin Password',
                'type': 'password',
                'organization_name': 'Microsoft Corp',
                'updated_at': (now - timedelta(days=7)).isoformat(),
                'importance': 'critical'
            },
            {
                'id': '3',
                'name': 'Old Backup Server',
                'type': 'configuration',
                'organization_name': 'Apple Inc',
                'updated_at': (now - timedelta(days=365)).isoformat()
            }
        ]
    
    def test_rank_results_basic(self, ranker, sample_results):
        """Test basic result ranking."""
        query_context = {
            'query_text': 'microsoft server',
            'entities': {
                'organization': ['Microsoft']
            }
        }
        
        ranked = ranker.rank_results(sample_results, query_context)
        
        assert len(ranked) == 3
        assert all(isinstance(r, ScoredResult) for r in ranked)
        
        # Check sorting (highest score first)
        scores = [r.score for r in ranked]
        assert scores == sorted(scores, reverse=True)
    
    def test_deduplication(self, ranker):
        """Test that duplicate results are removed."""
        duplicate_results = [
            {'id': '1', 'name': 'Server A', 'type': 'configuration'},
            {'id': '1', 'name': 'Server A', 'type': 'configuration'},  # Duplicate
            {'id': '2', 'name': 'Server B', 'type': 'configuration'}
        ]
        
        ranked = ranker.rank_results(duplicate_results, {})
        
        assert len(ranked) == 2
        unique_ids = set(r.data['id'] for r in ranked)
        assert len(unique_ids) == 2
    
    def test_fuzzy_score_calculation(self, ranker):
        """Test fuzzy score calculation."""
        result = {
            'name': 'Microsoft Exchange Server',
            '_fuzzy_score': 0.85
        }
        
        query_context = {'query_text': 'exchange'}
        
        factors = ranker._calculate_factors(result, query_context, None)
        assert factors.fuzzy_score == 0.85
        
        # Test fallback when no fuzzy score provided
        result_no_score = {'name': 'Exchange Server'}
        factors = ranker._calculate_factors(result_no_score, query_context, None)
        assert factors.fuzzy_score > 0  # Should calculate based on text match
    
    def test_entity_relevance_calculation(self, ranker):
        """Test entity relevance scoring."""
        result = {
            'organization_name': 'Microsoft Corporation',
            'hostname': 'web01.microsoft.com',
            'ip_addresses': ['192.168.1.100']
        }
        
        query_context = {
            'entities': {
                'organization': ['Microsoft'],
                'server': ['web01'],
                'ip_address': ['192.168.1.100']
            }
        }
        
        factors = ranker._calculate_factors(result, query_context, None)
        
        # Should have high entity relevance (all entities match)
        assert factors.entity_relevance == 1.0
    
    def test_recency_score_calculation(self, ranker):
        """Test recency score based on timestamps."""
        now = datetime.now()
        
        # Very recent result
        recent_result = {
            'updated_at': now.isoformat()
        }
        factors = ranker._calculate_factors(recent_result, {}, None)
        assert factors.recency_score == 1.0  # Last hour
        
        # Week old result
        week_old_result = {
            'updated_at': (now - timedelta(days=7)).isoformat()
        }
        factors = ranker._calculate_factors(week_old_result, {}, None)
        assert factors.recency_score == 0.75  # Last week
        
        # Very old result
        old_result = {
            'updated_at': (now - timedelta(days=400)).isoformat()
        }
        factors = ranker._calculate_factors(old_result, {}, None)
        assert factors.recency_score == 0.1  # Very old
    
    def test_type_priority_calculation(self, ranker):
        """Test type priority scoring."""
        password_result = {'type': 'password'}
        factors = ranker._calculate_factors(password_result, {}, None)
        assert factors.type_priority == 0.95  # Highest priority
        
        config_result = {'type': 'configuration'}
        factors = ranker._calculate_factors(config_result, {}, None)
        assert factors.type_priority == 0.85
        
        unknown_result = {'type': 'unknown_type'}
        factors = ranker._calculate_factors(unknown_result, {}, None)
        assert factors.type_priority == 0.50  # Default 'other' priority
    
    def test_completeness_score_calculation(self, ranker):
        """Test data completeness scoring."""
        complete_result = {
            'name': 'Server A',
            'description': 'Production server',
            'organization_name': 'Corp A',
            'updated_at': datetime.now().isoformat(),
            'created_by': 'admin',
            'tags': ['production', 'critical']
        }
        
        factors = ranker._calculate_factors(complete_result, {}, None)
        assert factors.completeness_score == 1.0  # All fields present
        
        incomplete_result = {
            'name': 'Server B'
        }
        
        factors = ranker._calculate_factors(incomplete_result, {}, None)
        assert factors.completeness_score < 0.3  # Only 1 of 6 fields
    
    def test_result_diversification(self, ranker):
        """Test that results are diversified by type."""
        # Create many results of the same type
        results = []
        for i in range(10):
            results.append({
                'id': f'config_{i}',
                'name': f'Config {i}',
                'type': 'configuration',
                '_fuzzy_score': 0.9 - (i * 0.01)  # Slightly decreasing scores
            })
        
        # Add a few different types
        results.append({
            'id': 'pass_1',
            'name': 'Password 1',
            'type': 'password',
            '_fuzzy_score': 0.85
        })
        
        ranked = ranker.rank_results(results, {})
        
        # Check that we don't have too many configs at the top
        top_5_types = [r.data['type'] for r in ranked[:5]]
        config_count = top_5_types.count('configuration')
        assert config_count <= 3  # Max 3 per type in top positions
    
    def test_merge_multi_source_results(self, ranker):
        """Test merging results from multiple sources."""
        postgresql_results = [
            {'id': '1', 'name': 'PG Result 1'},
            {'id': '2', 'name': 'PG Result 2'}
        ]
        
        neo4j_results = [
            {'id': '3', 'name': 'Neo4j Result 1'},
            {'id': '4', 'name': 'Neo4j Result 2'}
        ]
        
        cache_results = [
            {'id': '5', 'name': 'Cached Result'}
        ]
        
        merged = ranker.merge_multi_source_results(
            postgresql_results,
            neo4j_results,
            cache_results,
            query_context={'query_text': 'result'}
        )
        
        assert len(merged) == 5
        
        # Check source markers were added
        sources = set(r.get('_source') for r in merged)
        assert sources == {'postgresql', 'neo4j', 'cache'}
    
    def test_explain_ranking(self, ranker):
        """Test ranking explanation generation."""
        result = {
            'id': '1',
            'name': 'Test Server',
            'type': 'configuration'
        }
        
        ranked = ranker.rank_results([result], {})
        explanation = ranker.explain_ranking(ranked[0], verbose=True)
        
        assert 'total_score' in explanation
        assert 'factors' in explanation
        assert 'top_factors' in explanation
        assert 'deduplication_key' in explanation
        
        # Check all factors are present in verbose mode
        assert 'fuzzy_score' in explanation['factors']
        assert 'entity_relevance' in explanation['factors']
        assert 'recency_score' in explanation['factors']


class TestPopularityTracker:
    """Test suite for PopularityTracker."""
    
    @pytest.fixture
    def tracker(self):
        """Create popularity tracker instance."""
        return PopularityTracker(decay_factor=0.95)
    
    def test_record_access(self, tracker):
        """Test recording item accesses."""
        tracker.record_access('item_1')
        tracker.record_access('item_1')
        tracker.record_access('item_2')
        
        assert tracker.get_popularity('item_1') > tracker.get_popularity('item_2')
        assert tracker.get_popularity('item_3') == 0.0
    
    def test_time_decay(self, tracker):
        """Test that popularity decays over time."""
        # Record access and get initial popularity
        tracker.record_access('item_1')
        initial_popularity = tracker.get_popularity('item_1')
        
        # Simulate time passing by modifying last_access
        item = tracker.access_counts['item_1']
        item['last_access'] = datetime.now() - timedelta(days=1)
        
        # Popularity should have decayed
        decayed_popularity = tracker.get_popularity('item_1')
        assert decayed_popularity < initial_popularity
        assert decayed_popularity == initial_popularity * 0.95  # One day decay
    
    def test_get_top_items(self, tracker):
        """Test getting top popular items."""
        # Record different access counts
        for _ in range(10):
            tracker.record_access('popular_item')
        
        for _ in range(5):
            tracker.record_access('medium_item')
        
        tracker.record_access('unpopular_item')
        
        top_items = tracker.get_top_items(n=2)
        
        assert len(top_items) == 2
        assert top_items[0][0] == 'popular_item'
        assert top_items[1][0] == 'medium_item'
        assert top_items[0][1] > top_items[1][1]  # Popularity scores


class TestIntegrationScenarios:
    """Integration tests for realistic ranking scenarios."""
    
    @pytest.fixture
    def full_ranker(self):
        """Create ranker with all components."""
        user_profile_manager = Mock()
        user_profile_manager.get_profile.return_value = {
            'typical_organizations': ['Microsoft', 'Apple'],
            'typical_query_types': {'password': 10, 'configuration': 5},
            'recent_items': ['item_1', 'item_2']
        }
        
        popularity_tracker = PopularityTracker()
        popularity_tracker.record_access('popular_item')
        popularity_tracker.record_access('popular_item')
        
        return ResultRanker(
            user_profile_manager=user_profile_manager,
            popularity_tracker=popularity_tracker
        )
    
    def test_emergency_query_ranking(self, full_ranker):
        """Test ranking for emergency support scenario."""
        now = datetime.now()
        
        results = [
            {
                'id': 'old_doc',
                'name': 'Server Documentation',
                'type': 'document',
                'organization_name': 'Microsoft',
                'updated_at': (now - timedelta(days=180)).isoformat(),
                'description': 'Comprehensive server guide'
            },
            {
                'id': 'critical_pass',
                'name': 'Admin Password',
                'type': 'password',
                'organization_name': 'Microsoft',
                'updated_at': (now - timedelta(hours=2)).isoformat(),
                'importance': 'critical'
            },
            {
                'id': 'recent_config',
                'name': 'Server Configuration',
                'type': 'configuration',
                'organization_name': 'Microsoft',
                'updated_at': now.isoformat(),
                'hostname': 'prod-server-01'
            }
        ]
        
        query_context = {
            'query_text': 'microsoft server emergency',
            'entities': {
                'organization': ['Microsoft'],
                'server': ['prod-server-01']
            },
            'intent': 'troubleshooting'
        }
        
        ranked = full_ranker.rank_results(
            results,
            query_context,
            user_id='support_engineer_1'
        )
        
        # In emergency, password should rank high despite being older
        result_ids = [r.data['id'] for r in ranked]
        
        # Password should be in top 2 due to type priority
        assert 'critical_pass' in result_ids[:2]
        
        # Recent config should also rank high
        assert 'recent_config' in result_ids[:2]
    
    def test_investigation_query_ranking(self, full_ranker):
        """Test ranking for investigation scenario."""
        now = datetime.now()
        
        results = [
            {
                'id': 'item_1',
                'name': 'Change Log Entry',
                'type': 'audit',
                'updated_at': (now - timedelta(hours=1)).isoformat(),
                'description': 'Configuration changed'
            },
            {
                'id': 'item_2',
                'name': 'System Alert',
                'type': 'alert',
                'updated_at': (now - timedelta(minutes=30)).isoformat(),
                'description': 'CPU usage spike'
            },
            {
                'id': 'popular_item',
                'name': 'Server Dashboard',
                'type': 'configuration',
                'updated_at': (now - timedelta(days=1)).isoformat()
            }
        ]
        
        query_context = {
            'query_text': 'recent changes alerts',
            'intent': 'investigation'
        }
        
        ranked = full_ranker.rank_results(
            results,
            query_context,
            user_id='analyst_1'
        )
        
        # For investigation, recency is key
        result_ids = [r.data['id'] for r in ranked]
        
        # Most recent items should rank highest
        assert result_ids[0] == 'item_2'  # Most recent
        assert result_ids[1] == 'item_1'  # Second most recent