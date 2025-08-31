"""Unit tests for fuzzy query enhancer."""

import pytest
from typing import List

from src.query.fuzzy_enhancer import (
    QueryFuzzyEnhancer,
    EnhancedQuery,
    FuzzyMatch,
    FuzzyMatchType
)


class TestQueryFuzzyEnhancer:
    """Test the fuzzy query enhancer."""
    
    @pytest.fixture
    def enhancer(self):
        """Create a fuzzy enhancer instance."""
        return QueryFuzzyEnhancer(
            min_confidence=0.7,
            enable_typo_correction=True,
            enable_phonetic=True,
            enable_acronyms=True,
            preserve_exact_match=True
        )
    
    def test_exact_match_preservation(self, enhancer):
        """Test that exact matches are preserved."""
        query = "show all servers"
        candidates = ["servers", "services", "systems"]
        
        result = enhancer.enhance_query(query, candidates)
        
        assert result.original_query == query
        assert "servers" in result.enhanced_query
        assert not result.fallback_to_exact
        
        # Check exact match was found
        server_match = next(
            (m for m in result.fuzzy_matches if m.matched == "servers"),
            None
        )
        assert server_match is not None
        assert server_match.match_type == FuzzyMatchType.EXACT
        assert server_match.confidence == 1.0
    
    def test_typo_correction(self, enhancer):
        """Test typo correction functionality."""
        queries = [
            ("show all paswords", "show all password"),
            ("check servr status", "check server status"),
            ("backup databse", "backup database"),
            ("netwok configuration", "network configuration"),
            ("firewal rules", "firewall rules")
        ]
        
        for original, expected in queries:
            result = enhancer.enhance_query(original)
            
            # Check typo was corrected
            assert any(
                m.match_type == FuzzyMatchType.TYPO_CORRECTION
                for m in result.fuzzy_matches
            )
            
            # Verify correction in enhanced query
            for word in expected.split():
                if word not in ["show", "all", "check", "status", "rules"]:
                    assert word in result.enhanced_query
    
    def test_acronym_expansion(self, enhancer):
        """Test acronym expansion."""
        queries = [
            ("check db status", ["database"]),
            ("restart vm", ["virtual machine"]),
            ("configure vpn", ["virtual private network"]),
            ("update ad", ["active directory"]),
            ("deploy to k8s", ["kubernetes"])
        ]
        
        for query, expansions in queries:
            result = enhancer.enhance_query(query)
            
            # Check acronym was expanded
            acronym_matches = [
                m for m in result.fuzzy_matches
                if m.match_type == FuzzyMatchType.ACRONYM
            ]
            assert len(acronym_matches) > 0
            
            # Verify expansion in metadata
            for match in acronym_matches:
                assert "expansions" in match.metadata
                for expansion in expansions:
                    assert expansion in match.metadata["expansions"]
    
    def test_fuzzy_matching(self, enhancer):
        """Test fuzzy matching against candidates."""
        query = "show acme servers"
        candidates = ["Acme Corporation", "AcmeCorp", "ACME Inc", "Apex Systems"]
        
        result = enhancer.enhance_query(query, candidates)
        
        # Should find fuzzy match for "acme"
        acme_matches = [
            m for m in result.fuzzy_matches
            if "acme" in m.original.lower()
        ]
        assert len(acme_matches) > 0
        
        # Check match confidence
        for match in acme_matches:
            assert match.confidence >= enhancer.min_confidence
    
    def test_confidence_scoring(self, enhancer):
        """Test confidence score calculation."""
        # High confidence query (exact matches)
        query1 = "show servers"
        candidates = ["servers", "show"]
        result1 = enhancer.enhance_query(query1, candidates)
        assert result1.confidence > 0.9
        
        # Lower confidence query (fuzzy matches)
        query2 = "shw srvrs"
        result2 = enhancer.enhance_query(query2, candidates)
        assert result2.confidence < result1.confidence
        
        # Very low confidence (no good matches)
        query3 = "xyz abc def"
        result3 = enhancer.enhance_query(query3, candidates)
        assert result3.confidence < enhancer.min_confidence
    
    def test_fallback_to_exact(self, enhancer):
        """Test fallback to exact match when confidence is low."""
        query = "xyz abc def"  # No good matches
        candidates = ["servers", "systems", "services"]
        
        result = enhancer.enhance_query(query, candidates)
        
        # Should fallback to exact match
        assert result.fallback_to_exact
        assert result.enhanced_query == query  # Original query preserved
        assert result.confidence < enhancer.min_confidence
    
    def test_batch_enhancement(self, enhancer):
        """Test batch query enhancement."""
        queries = [
            "show pasword",
            "list servrs",
            "check db status"
        ]
        candidates = ["password", "servers", "database"]
        
        results = enhancer.batch_enhance(queries, candidates)
        
        assert len(results) == 3
        
        # Each query should be enhanced
        for i, result in enumerate(results):
            assert result.original_query == queries[i]
            assert len(result.fuzzy_matches) > 0
    
    def test_match_type_determination(self, enhancer):
        """Test correct match type identification."""
        test_cases = [
            ("serv", "server", FuzzyMatchType.PREFIX),
            ("base", "database", FuzzyMatchType.SUBSTRING),
            ("passwrd", "password", FuzzyMatchType.LEVENSHTEIN),
            ("server", "server", FuzzyMatchType.EXACT)
        ]
        
        for token, candidate, expected_type in test_cases:
            result = enhancer._fuzzy_match(token, [candidate])
            if result:
                assert result.match_type == expected_type
    
    def test_tokenization(self, enhancer):
        """Test query tokenization."""
        query = "server-01.example.com at 192.168.1.1"
        tokens = enhancer._tokenize(query)
        
        assert "server-01.example.com" in tokens
        assert "at" in tokens
        assert "192.168.1.1" in tokens
    
    def test_should_use_fuzzy(self, enhancer):
        """Test decision logic for using fuzzy matching."""
        # Should use fuzzy (good matches, high confidence)
        query1 = "show pasword"
        result1 = enhancer.enhance_query(query1)
        assert enhancer.should_use_fuzzy(result1)
        
        # Should not use fuzzy (fallback to exact)
        query2 = "xyz abc"
        result2 = enhancer.enhance_query(query2, ["servers"])
        assert not enhancer.should_use_fuzzy(result2)
    
    def test_match_explanations(self, enhancer):
        """Test generation of match explanations."""
        query = "check pasword for db"
        result = enhancer.enhance_query(query)
        
        explanations = enhancer.get_match_explanations(result)
        
        assert len(explanations) > 0
        
        # Check explanations mention corrections
        explanation_text = " ".join(explanations)
        assert "typo correction" in explanation_text or "acronym" in explanation_text
    
    def test_dictionary_updates(self, enhancer):
        """Test updating typo and acronym dictionaries."""
        # Add custom typos
        custom_typos = {
            "custm": "custom",
            "confg": "config"
        }
        
        # Add custom acronyms
        custom_acronyms = {
            "lb": ["load balancer"],
            "cdn": ["content delivery network"]
        }
        
        enhancer.update_dictionaries(
            typos=custom_typos,
            acronyms=custom_acronyms
        )
        
        # Test custom typo correction
        result1 = enhancer.enhance_query("check custm confg")
        assert "custom" in result1.enhanced_query
        assert "config" in result1.enhanced_query
        
        # Test custom acronym expansion
        result2 = enhancer.enhance_query("configure lb and cdn")
        acronym_matches = [
            m for m in result2.fuzzy_matches
            if m.match_type == FuzzyMatchType.ACRONYM
        ]
        assert len(acronym_matches) == 2
    
    def test_confidence_threshold(self, enhancer):
        """Test minimum confidence threshold enforcement."""
        enhancer.min_confidence = 0.9  # Set high threshold
        
        query = "srvr"  # Slightly misspelled
        candidates = ["server", "service"]
        
        result = enhancer.enhance_query(query, candidates)
        
        # With high threshold, fuzzy match might not be included
        if result.fuzzy_matches:
            for match in result.fuzzy_matches:
                assert match.confidence >= 0.9
    
    def test_preserve_exact_match_disabled(self):
        """Test behavior when preserve_exact_match is disabled."""
        enhancer = QueryFuzzyEnhancer(preserve_exact_match=False)
        
        query = "show servers xyz"
        candidates = ["servers"]
        
        result = enhancer.enhance_query(query, candidates)
        
        # Should not fallback even with low confidence on some tokens
        assert not result.fallback_to_exact
    
    def test_complex_query(self, enhancer):
        """Test enhancement of complex multi-token query."""
        query = "show paswords for db servr in prod enviornment"
        candidates = ["password", "database", "server", "production", "environment"]
        
        result = enhancer.enhance_query(query, candidates)
        
        # Should correct multiple typos and expand acronyms
        assert "password" in result.enhanced_query
        assert "database" in result.enhanced_query
        assert "server" in result.enhanced_query
        
        # Should have multiple fuzzy matches
        assert len(result.fuzzy_matches) >= 3
        
        # Should have reasonable confidence
        assert result.confidence > 0.5
    
    def test_empty_query(self, enhancer):
        """Test handling of empty query."""
        result = enhancer.enhance_query("")
        
        assert result.original_query == ""
        assert result.enhanced_query == ""
        assert len(result.fuzzy_matches) == 0
        assert result.confidence == 1.0
    
    def test_no_candidates(self, enhancer):
        """Test enhancement without candidates."""
        query = "show pasword for db"
        
        result = enhancer.enhance_query(query, candidates=None)
        
        # Should still do typo correction and acronym expansion
        assert "password" in result.enhanced_query
        assert "database" in result.enhanced_query
        
        # Should have matches from typo and acronym
        assert len(result.fuzzy_matches) > 0