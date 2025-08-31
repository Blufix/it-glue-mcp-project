"""Comprehensive unit tests for fuzzy matching functionality - 90% coverage target."""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile

import sys
sys.path.insert(0, '/home/jamie/projects/itglue-mcp-server')

from src.query.fuzzy_matcher import (
    FuzzyMatcher,
    MatchResult,
    EnhancedMatchResult,
    QueryFuzzyEnhancer
)


@pytest.fixture
def fuzzy_matcher():
    """Create FuzzyMatcher instance for testing."""
    return FuzzyMatcher(cache_manager=None)


@pytest.fixture
def fuzzy_matcher_with_cache():
    """Create FuzzyMatcher with mock cache manager."""
    cache_manager = AsyncMock()
    cache_manager.get = AsyncMock(return_value=None)
    cache_manager.set = AsyncMock()
    return FuzzyMatcher(cache_manager=cache_manager)


@pytest.fixture
def sample_organizations():
    """Sample organization data for testing."""
    return [
        {"id": "1", "name": "Microsoft Corporation"},
        {"id": "2", "name": "Amazon Web Services"},
        {"id": "3", "name": "Google Cloud Platform"},
        {"id": "4", "name": "International Business Machines"},
        {"id": "5", "name": "Hewlett Packard Enterprise"},
        {"id": "6", "name": "Johnson & Johnson"},
        {"id": "7", "name": "JP Morgan Chase"}
    ]


@pytest.fixture
def temp_dictionaries(tmp_path):
    """Create temporary dictionary files for testing."""
    dict_dir = tmp_path / "dictionaries"
    dict_dir.mkdir()
    
    # IT terms dictionary
    it_terms = {
        "pasword": "password",
        "windoes": "windows",
        "kubernets": "kubernetes",
        "dockar": "docker"
    }
    with open(dict_dir / "it_terms.json", "w") as f:
        json.dump(it_terms, f)
    
    # IT dictionary
    it_dict = ["server", "database", "network", "firewall", "kubernetes"]
    with open(dict_dir / "it_dictionary.json", "w") as f:
        json.dump(it_dict, f)
    
    # Company aliases
    aliases = {
        "ms": ["Microsoft", "Microsoft Corporation"],
        "aws": ["Amazon Web Services", "AWS"]
    }
    with open(dict_dir / "company_aliases.json", "w") as f:
        json.dump(aliases, f)
    
    return dict_dir


class TestFuzzyMatcherInit:
    """Test FuzzyMatcher initialization."""
    
    def test_init_without_cache(self):
        """Test initialization without cache manager."""
        matcher = FuzzyMatcher()
        assert matcher.cache_manager is None
        assert matcher.cache_hits == 0
        assert matcher.cache_misses == 0
        assert len(matcher.acronym_map) > 0
        assert len(matcher.common_mistakes) > 0
        assert len(matcher.it_terms) > 0
    
    def test_init_with_cache(self):
        """Test initialization with cache manager."""
        cache = Mock()
        matcher = FuzzyMatcher(cache_manager=cache)
        assert matcher.cache_manager == cache
    
    def test_load_dictionaries_from_json(self, temp_dictionaries, monkeypatch):
        """Test loading dictionaries from JSON files."""
        monkeypatch.setattr(Path, '__new__', lambda cls, *args: temp_dictionaries / args[0] 
                          if len(args) > 0 and 'dictionaries' in str(args[0]) 
                          else Path(*args))
        
        matcher = FuzzyMatcher()
        # Should have loaded and merged with hardcoded values
        assert "pasword" in matcher.common_mistakes
        assert matcher.common_mistakes["pasword"] == "password"


class TestOrganizationMatching:
    """Test organization matching functionality."""
    
    def test_exact_match(self, fuzzy_matcher, sample_organizations):
        """Test exact organization name matching."""
        results = fuzzy_matcher.match_organization(
            "Microsoft Corporation",
            sample_organizations,
            threshold=0.7
        )
        
        assert len(results) > 0
        assert results[0].matched == "Microsoft Corporation"
        assert results[0].score == 1.0
        assert results[0].match_type == "exact"
        assert results[0].entity_id == "1"
    
    def test_fuzzy_match_typo(self, fuzzy_matcher, sample_organizations):
        """Test fuzzy matching with typos."""
        results = fuzzy_matcher.match_organization(
            "Microsft Corporation",  # Missing 'o'
            sample_organizations,
            threshold=0.8
        )
        
        assert len(results) > 0
        assert results[0].matched == "Microsoft Corporation"
        assert results[0].score > 0.8
        assert results[0].match_type == "fuzzy"
    
    def test_acronym_match(self, fuzzy_matcher, sample_organizations):
        """Test acronym matching."""
        results = fuzzy_matcher.match_organization(
            "IBM",
            sample_organizations,
            threshold=0.7
        )
        
        assert len(results) > 0
        assert results[0].matched == "International Business Machines"
        assert results[0].match_type == "acronym"
        assert results[0].score >= 0.85
    
    def test_partial_match(self, fuzzy_matcher, sample_organizations):
        """Test partial name matching."""
        results = fuzzy_matcher.match_organization(
            "Google",
            sample_organizations,
            threshold=0.5
        )
        
        assert len(results) > 0
        assert "Google" in results[0].matched
        assert results[0].match_type == "partial"
    
    def test_phonetic_match(self, fuzzy_matcher):
        """Test phonetic matching."""
        orgs = [
            {"id": "1", "name": "Johnson Company"},
            {"id": "2", "name": "Jonsen Company"}
        ]
        
        results = fuzzy_matcher.match_organization(
            "Johnsen Company",
            orgs,
            threshold=0.7
        )
        
        assert len(results) > 0
        # Should match phonetically similar names
        assert results[0].match_type in ["phonetic", "fuzzy"]
    
    def test_no_matches(self, fuzzy_matcher, sample_organizations):
        """Test when no matches are found."""
        results = fuzzy_matcher.match_organization(
            "NonExistentCompany123",
            sample_organizations,
            threshold=0.9
        )
        
        assert len(results) == 0
    
    def test_threshold_filtering(self, fuzzy_matcher, sample_organizations):
        """Test threshold filtering of results."""
        # Low threshold should return more results
        results_low = fuzzy_matcher.match_organization(
            "Morgan",
            sample_organizations,
            threshold=0.3
        )
        
        # High threshold should return fewer results
        results_high = fuzzy_matcher.match_organization(
            "Morgan",
            sample_organizations,
            threshold=0.8
        )
        
        assert len(results_low) >= len(results_high)
    
    def test_result_limit(self, fuzzy_matcher):
        """Test that results are limited to top 5."""
        # Create many similar organizations
        orgs = [{"id": str(i), "name": f"Company {i}"} for i in range(20)]
        
        results = fuzzy_matcher.match_organization(
            "Company",
            orgs,
            threshold=0.1
        )
        
        assert len(results) <= 5
    
    def test_empty_input(self, fuzzy_matcher, sample_organizations):
        """Test handling of empty input."""
        results = fuzzy_matcher.match_organization(
            "",
            sample_organizations,
            threshold=0.7
        )
        
        assert len(results) == 0
    
    def test_empty_candidates(self, fuzzy_matcher):
        """Test handling of empty candidate list."""
        results = fuzzy_matcher.match_organization(
            "Microsoft",
            [],
            threshold=0.7
        )
        
        assert len(results) == 0


class TestNormalization:
    """Test organization name normalization."""
    
    def test_normalize_basic(self, fuzzy_matcher):
        """Test basic normalization."""
        normalized = fuzzy_matcher._normalize_organization("  Microsoft Corp.  ")
        assert normalized == "microsoft corp"
    
    def test_normalize_abbreviations(self, fuzzy_matcher):
        """Test abbreviation normalization."""
        normalized = fuzzy_matcher._normalize_organization("Microsoft Incorporated")
        assert "inc" in normalized
    
    def test_normalize_corrections(self, fuzzy_matcher):
        """Test common mistake corrections."""
        normalized = fuzzy_matcher._normalize_organization("Microsft")
        assert normalized == "microsoft"
    
    def test_normalize_special_chars(self, fuzzy_matcher):
        """Test special character handling."""
        normalized = fuzzy_matcher._normalize_organization("Johnson & Johnson, Inc.")
        assert "&" in normalized
        assert "," not in normalized
        assert "." not in normalized


class TestMatchingStrategies:
    """Test individual matching strategies."""
    
    def test_exact_match_strategy(self, fuzzy_matcher):
        """Test exact match strategy."""
        score = fuzzy_matcher._exact_match("microsoft", "microsoft")
        assert score == 1.0
        
        score = fuzzy_matcher._exact_match("microsoft", "google")
        assert score == 0.0
    
    def test_fuzzy_match_strategy(self, fuzzy_matcher):
        """Test fuzzy match strategy."""
        score = fuzzy_matcher._fuzzy_match("microsoft", "microsft")
        assert 0.8 < score < 1.0
        
        score = fuzzy_matcher._fuzzy_match("abc", "xyz")
        assert score < 0.5
    
    def test_phonetic_match_strategy(self, fuzzy_matcher):
        """Test phonetic match strategy."""
        score = fuzzy_matcher._phonetic_match("johnson", "jonsen")
        assert score > 0.7
        
        score = fuzzy_matcher._phonetic_match("", "test")
        assert score == 0.0
        
        score = fuzzy_matcher._phonetic_match("test", "")
        assert score == 0.0
    
    def test_acronym_match_strategy(self, fuzzy_matcher):
        """Test acronym match strategy."""
        # Known acronym
        score = fuzzy_matcher._acronym_match("ibm", "international business machines")
        assert score >= 0.85
        
        # Generated acronym
        score = fuzzy_matcher._acronym_match("aws", "amazon web services")
        assert score >= 0.85
        
        # No match
        score = fuzzy_matcher._acronym_match("xyz", "microsoft corporation")
        assert score == 0.0
    
    def test_partial_match_strategy(self, fuzzy_matcher):
        """Test partial match strategy."""
        # Substring match
        score = fuzzy_matcher._partial_match("micro", "microsoft")
        assert score > 0.5
        
        # Word overlap
        score = fuzzy_matcher._partial_match("web services", "amazon web services")
        assert score > 0.5
        
        # No match
        score = fuzzy_matcher._partial_match("xyz", "abc")
        assert score == 0.0


class TestConfidenceCalculation:
    """Test confidence score calculation."""
    
    def test_confidence_exact(self, fuzzy_matcher):
        """Test confidence for exact match."""
        confidence = fuzzy_matcher._calculate_confidence(1.0, "exact")
        assert confidence == 1.0
    
    def test_confidence_fuzzy(self, fuzzy_matcher):
        """Test confidence for fuzzy match."""
        confidence = fuzzy_matcher._calculate_confidence(0.9, "fuzzy")
        assert 0.8 <= confidence <= 1.0
    
    def test_confidence_phonetic(self, fuzzy_matcher):
        """Test confidence for phonetic match."""
        confidence = fuzzy_matcher._calculate_confidence(0.9, "phonetic")
        assert 0.7 <= confidence <= 0.9
    
    def test_confidence_boost(self, fuzzy_matcher):
        """Test confidence boost for high scores."""
        confidence = fuzzy_matcher._calculate_confidence(0.98, "fuzzy")
        assert confidence > 0.98 * 0.9  # Should be boosted


class TestCaching:
    """Test caching functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, fuzzy_matcher_with_cache, sample_organizations):
        """Test cache miss scenario."""
        matcher = fuzzy_matcher_with_cache
        matcher.cache_manager.get.return_value = None
        
        results = await matcher.match_organization_cached(
            "Microsoft",
            sample_organizations,
            threshold=0.7
        )
        
        assert matcher.cache_hits == 0
        assert matcher.cache_misses == 1
        assert matcher.cache_manager.get.called
        assert matcher.cache_manager.set.called
        assert all(isinstance(r, EnhancedMatchResult) for r in results)
        assert all(not r.from_cache for r in results)
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, fuzzy_matcher_with_cache, sample_organizations):
        """Test cache hit scenario."""
        matcher = fuzzy_matcher_with_cache
        
        # Mock cached result
        cached_data = json.dumps([{
            'original': 'Microsoft',
            'matched': 'Microsoft Corporation',
            'score': 0.95,
            'match_type': 'fuzzy',
            'confidence': 0.9,
            'entity_id': '1',
            'metadata': {},
            'match_time_ms': 10.5
        }])
        matcher.cache_manager.get.return_value = cached_data
        
        results = await matcher.match_organization_cached(
            "Microsoft",
            sample_organizations,
            threshold=0.7
        )
        
        assert matcher.cache_hits == 1
        assert matcher.cache_misses == 0
        assert all(r.from_cache for r in results)
        assert not matcher.cache_manager.set.called
    
    @pytest.mark.asyncio
    async def test_cache_without_manager(self, sample_organizations):
        """Test caching when no cache manager is present."""
        matcher = FuzzyMatcher(cache_manager=None)
        
        results = await matcher.match_organization_cached(
            "Microsoft",
            sample_organizations,
            threshold=0.7
        )
        
        assert all(isinstance(r, EnhancedMatchResult) for r in results)
        assert all(not r.from_cache for r in results)


class TestSuggestions:
    """Test correction suggestions."""
    
    def test_suggest_corrections_typos(self, fuzzy_matcher):
        """Test suggestions for known typos."""
        suggestions = fuzzy_matcher.suggest_correction("pasword windoes")
        assert "password" in suggestions
        assert "windows" in suggestions
    
    def test_suggest_corrections_unknown(self, fuzzy_matcher):
        """Test suggestions for unknown words."""
        # Add some IT terms to the matcher's dictionary
        fuzzy_matcher.it_terms.add("kubernetes")
        
        suggestions = fuzzy_matcher.suggest_correction("kubernete")
        # Should suggest similar IT term
        assert any("kubernetes" in str(s).lower() for s in suggestions)
    
    def test_suggest_corrections_none(self, fuzzy_matcher):
        """Test when no suggestions are available."""
        suggestions = fuzzy_matcher.suggest_correction("correctword")
        # Should not suggest anything for correctly spelled unknown words
        assert len(suggestions) == 0 or suggestions == []


class TestDictionaryReloading:
    """Test dictionary reloading functionality."""
    
    def test_reload_dictionaries(self, fuzzy_matcher, temp_dictionaries, monkeypatch):
        """Test reloading dictionaries from files."""
        # Monkeypatch Path to use temp directory
        def mock_path_new(cls, *args):
            if args and 'dictionaries' in str(args[0]):
                return temp_dictionaries / args[0]
            return Path(*args)
        
        monkeypatch.setattr(Path, '__new__', mock_path_new)
        
        # Clear cache before reload
        fuzzy_matcher.dict_cache.clear()
        initial_mistakes = len(fuzzy_matcher.common_mistakes)
        
        # Reload dictionaries
        fuzzy_matcher.reload_dictionaries()
        
        # Cache should be cleared
        assert len(fuzzy_matcher.dict_cache) == 0
        
        # Should have loaded new terms
        assert "pasword" in fuzzy_matcher.common_mistakes


class TestCacheStatistics:
    """Test cache statistics functionality."""
    
    def test_cache_stats_empty(self, fuzzy_matcher):
        """Test cache stats when empty."""
        stats = fuzzy_matcher.get_cache_stats()
        
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0
        assert stats['hit_rate'] == 0
        assert stats['dict_cache_size'] == 0
        assert stats['org_cache_size'] == 0
        assert stats['common_mistakes_count'] > 0
        assert stats['it_terms_count'] > 0
    
    @pytest.mark.asyncio
    async def test_cache_stats_with_usage(self, fuzzy_matcher_with_cache, sample_organizations):
        """Test cache stats after usage."""
        matcher = fuzzy_matcher_with_cache
        
        # Generate some cache activity
        matcher.cache_manager.get.return_value = None
        await matcher.match_organization_cached("Test1", sample_organizations, 0.7)
        
        # Mock a cache hit
        matcher.cache_manager.get.return_value = json.dumps([])
        await matcher.match_organization_cached("Test2", sample_organizations, 0.7)
        
        stats = matcher.get_cache_stats()
        
        assert stats['cache_hits'] == 1
        assert stats['cache_misses'] == 1
        assert stats['hit_rate'] == 0.5


class TestQueryFuzzyEnhancer:
    """Test QueryFuzzyEnhancer functionality."""
    
    @pytest.fixture
    def query_enhancer(self, fuzzy_matcher):
        """Create QueryFuzzyEnhancer instance."""
        return QueryFuzzyEnhancer(fuzzy_matcher)
    
    def test_enhance_query_basic(self, query_enhancer):
        """Test basic query enhancement."""
        known_entities = {
            'organizations': [
                {'id': '1', 'name': 'Microsoft Corporation'},
                {'id': '2', 'name': 'Google Inc'}
            ]
        }
        
        result = query_enhancer.enhance_query(
            "show all servers for Microsoft",
            known_entities
        )
        
        assert result['original'] == "show all servers for Microsoft"
        assert 'entities' in result
        assert 'suggestions' in result
        assert result['intent'] is not None
    
    def test_enhance_query_with_match(self, query_enhancer):
        """Test query enhancement with entity matching."""
        known_entities = {
            'organizations': [
                {'id': '1', 'name': 'Microsoft Corporation'}
            ]
        }
        
        result = query_enhancer.enhance_query(
            "get servers for Microsft",  # Typo
            known_entities
        )
        
        if 'organization' in result['entities']:
            assert result['entities']['organization']['input'] == 'Microsft'
            assert 'Microsoft' in result['entities']['organization']['matched']
            assert result['corrected'] != result['original']
    
    def test_enhance_query_patterns(self, query_enhancer):
        """Test different query patterns."""
        known_entities = {'organizations': []}
        
        patterns = [
            ("show me all servers for Company", "list_assets"),
            ("get configurations for Company", "get_entity"),
            ("find servers in Company", "search_entity"),
            ("list servers for Company", "list_entity"),
            ("what servers does Company have", "query_assets")
        ]
        
        for query, expected_intent in patterns:
            result = query_enhancer.enhance_query(query, known_entities)
            assert result['intent'] == expected_intent
    
    def test_enhance_query_no_pattern_match(self, query_enhancer):
        """Test query with no pattern match."""
        result = query_enhancer.enhance_query(
            "random query text",
            {'organizations': []}
        )
        
        assert result['intent'] is None
        assert result['original'] == "random query text"
        assert result['corrected'] == "random query text"


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_none_candidate_name(self, fuzzy_matcher):
        """Test handling of None in candidate names."""
        candidates = [
            {"id": "1", "name": None},
            {"id": "2", "name": "Valid Company"}
        ]
        
        results = fuzzy_matcher.match_organization(
            "Valid",
            candidates,
            threshold=0.5
        )
        
        # Should handle None gracefully and match valid entries
        assert len(results) > 0
        assert results[0].matched == "Valid Company"
    
    def test_special_characters_in_names(self, fuzzy_matcher):
        """Test handling of special characters."""
        candidates = [
            {"id": "1", "name": "Company (USA) Ltd."},
            {"id": "2", "name": "Comp@ny #1"}
        ]
        
        results = fuzzy_matcher.match_organization(
            "Company USA",
            candidates,
            threshold=0.5
        )
        
        assert len(results) > 0
    
    def test_very_long_names(self, fuzzy_matcher):
        """Test handling of very long organization names."""
        long_name = "Company " * 100  # Very long name
        candidates = [{"id": "1", "name": long_name}]
        
        results = fuzzy_matcher.match_organization(
            "Company",
            candidates,
            threshold=0.1
        )
        
        assert len(results) > 0
    
    def test_unicode_characters(self, fuzzy_matcher):
        """Test handling of Unicode characters."""
        candidates = [
            {"id": "1", "name": "Société Générale"},
            {"id": "2", "name": "北京公司"}
        ]
        
        results = fuzzy_matcher.match_organization(
            "Societe Generale",
            candidates,
            threshold=0.7
        )
        
        # Should handle Unicode gracefully
        assert isinstance(results, list)


class TestPerformance:
    """Test performance characteristics."""
    
    def test_match_performance(self, fuzzy_matcher):
        """Test matching performance with large dataset."""
        # Create large candidate list
        candidates = [
            {"id": str(i), "name": f"Company {i % 100} Corporation"}
            for i in range(1000)
        ]
        
        start_time = time.perf_counter()
        results = fuzzy_matcher.match_organization(
            "Company 50",
            candidates,
            threshold=0.7
        )
        elapsed_time = time.perf_counter() - start_time
        
        # Should complete within reasonable time (< 1 second for 1000 candidates)
        assert elapsed_time < 1.0
        assert len(results) > 0
    
    def test_normalization_performance(self, fuzzy_matcher):
        """Test normalization performance."""
        long_text = "Microsoft Corporation " * 100
        
        start_time = time.perf_counter()
        for _ in range(100):
            fuzzy_matcher._normalize_organization(long_text)
        elapsed_time = time.perf_counter() - start_time
        
        # Should normalize 100 long texts quickly
        assert elapsed_time < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.query.fuzzy_matcher", "--cov-report=term-missing"])