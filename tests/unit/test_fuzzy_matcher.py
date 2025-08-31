"""Unit tests for fuzzy matching system."""

import pytest
from src.query.fuzzy_matcher import FuzzyMatcher, QueryFuzzyEnhancer, MatchResult


class TestFuzzyMatcher:
    """Test fuzzy matching functionality."""
    
    @pytest.fixture
    def fuzzy_matcher(self):
        """Create fuzzy matcher instance."""
        return FuzzyMatcher()
    
    @pytest.fixture
    def test_organizations(self):
        """Sample organizations for testing."""
        return [
            {'name': 'Microsoft Corporation', 'id': 'org-001'},
            {'name': 'Amazon Web Services', 'id': 'org-002'},
            {'name': 'Johnson & Associates', 'id': 'org-003'},
            {'name': 'Smith Technologies Inc', 'id': 'org-004'},
            {'name': 'ABC Company Ltd', 'id': 'org-005'},
            {'name': 'XYZ Solutions', 'id': 'org-006'}
        ]
    
    def test_exact_match(self, fuzzy_matcher, test_organizations):
        """Test exact organization name matching."""
        results = fuzzy_matcher.match_organization(
            'Microsoft Corporation',
            test_organizations
        )
        
        assert len(results) > 0
        assert results[0].matched == 'Microsoft Corporation'
        assert results[0].score == 1.0
        assert results[0].match_type == 'exact'
    
    def test_spelling_correction(self, fuzzy_matcher, test_organizations):
        """Test spelling mistake correction."""
        # Common misspelling
        results = fuzzy_matcher.match_organization(
            'Microsft Corporation',
            test_organizations
        )
        
        assert len(results) > 0
        assert results[0].matched == 'Microsoft Corporation'
        assert results[0].score > 0.9
        assert results[0].match_type == 'fuzzy'
    
    def test_phonetic_matching(self, fuzzy_matcher, test_organizations):
        """Test phonetic matching for sound-alike names."""
        results = fuzzy_matcher.match_organization(
            'Jonsen & Associates',
            test_organizations
        )
        
        assert len(results) > 0
        assert results[0].matched == 'Johnson & Associates'
        assert results[0].match_type in ['phonetic', 'fuzzy']
    
    def test_acronym_expansion(self, fuzzy_matcher, test_organizations):
        """Test acronym matching."""
        # Test known acronym
        results = fuzzy_matcher.match_organization(
            'AWS',
            test_organizations
        )
        
        assert len(results) > 0
        assert 'Amazon' in results[0].matched
        assert results[0].match_type == 'acronym'
    
    def test_partial_match(self, fuzzy_matcher, test_organizations):
        """Test partial name matching."""
        results = fuzzy_matcher.match_organization(
            'Smith Tech',
            test_organizations
        )
        
        assert len(results) > 0
        assert 'Smith Technologies' in results[0].matched
        assert results[0].match_type in ['partial', 'fuzzy']
    
    def test_abbreviation_normalization(self, fuzzy_matcher, test_organizations):
        """Test company suffix normalization."""
        results = fuzzy_matcher.match_organization(
            'ABC Company Limited',
            test_organizations
        )
        
        assert len(results) > 0
        assert results[0].matched == 'ABC Company Ltd'
        assert results[0].score > 0.8
    
    def test_case_insensitive(self, fuzzy_matcher, test_organizations):
        """Test case insensitive matching."""
        results = fuzzy_matcher.match_organization(
            'microsoft corporation',
            test_organizations
        )
        
        assert len(results) > 0
        assert results[0].matched == 'Microsoft Corporation'
        assert results[0].score == 1.0
    
    def test_no_match_below_threshold(self, fuzzy_matcher, test_organizations):
        """Test that poor matches are filtered by threshold."""
        results = fuzzy_matcher.match_organization(
            'Completely Different Company Name',
            test_organizations,
            threshold=0.8
        )
        
        assert len(results) == 0 or all(r.score < 0.8 for r in results)
    
    def test_multiple_matches_ranked(self, fuzzy_matcher):
        """Test that multiple matches are properly ranked."""
        organizations = [
            {'name': 'Microsoft Corporation', 'id': '1'},
            {'name': 'Microsoft Azure', 'id': '2'},
            {'name': 'Microsoft Office 365', 'id': '3'}
        ]
        
        results = fuzzy_matcher.match_organization(
            'Microsoft',
            organizations
        )
        
        assert len(results) >= 2
        # Results should be sorted by score
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score
    
    def test_it_term_suggestions(self, fuzzy_matcher):
        """Test IT-specific term correction suggestions."""
        suggestions = fuzzy_matcher.suggest_correction('kubernets pasword windws')
        
        assert 'kubernetes' in suggestions
        assert 'password' in suggestions
        assert 'windows' in suggestions


class TestQueryFuzzyEnhancer:
    """Test query enhancement with fuzzy matching."""
    
    @pytest.fixture
    def enhancer(self):
        """Create query enhancer instance."""
        matcher = FuzzyMatcher()
        return QueryFuzzyEnhancer(matcher)
    
    @pytest.fixture
    def known_entities(self):
        """Sample known entities."""
        return {
            'organizations': [
                {'name': 'Acme Corporation', 'id': 'org-1'},
                {'name': 'TechCorp Solutions', 'id': 'org-2'}
            ],
            'configurations': [
                {'name': 'mail-server-01', 'id': 'cfg-1'},
                {'name': 'web-server-prod', 'id': 'cfg-2'}
            ]
        }
    
    def test_enhance_query_with_organization(self, enhancer, known_entities):
        """Test query enhancement with organization fuzzy matching."""
        enhanced = enhancer.enhance_query(
            'show all servers for acme corp',
            known_entities
        )
        
        assert enhanced['intent'] == 'list_assets'
        assert 'organization' in enhanced['entities']
        assert enhanced['entities']['organization']['matched'] == 'Acme Corporation'
        assert enhanced['corrected'] == 'show all servers for Acme Corporation'
    
    def test_enhance_query_with_typos(self, enhancer, known_entities):
        """Test query enhancement with spelling corrections."""
        enhanced = enhancer.enhance_query(
            'get paswords for techcorp',
            known_entities
        )
        
        assert 'password' in enhanced['suggestions']
        assert 'organization' in enhanced['entities']
    
    def test_enhance_query_no_match(self, enhancer, known_entities):
        """Test query enhancement when no entities match."""
        enhanced = enhancer.enhance_query(
            'show servers for unknown company',
            known_entities
        )
        
        assert enhanced['original'] == enhanced['corrected']
        assert 'organization' not in enhanced['entities']
    
    def test_query_pattern_detection(self, enhancer, known_entities):
        """Test different query patterns are detected."""
        patterns = [
            ('show me all windows servers for acme', 'list_assets'),
            ('get configurations for techcorp', 'get_entity'),
            ('find passwords in acme corp', 'search_entity'),
            ('list servers for techcorp', 'list_entity'),
            ('what servers does acme have', 'query_assets')
        ]
        
        for query, expected_intent in patterns:
            enhanced = enhancer.enhance_query(query, known_entities)
            assert enhanced['intent'] == expected_intent