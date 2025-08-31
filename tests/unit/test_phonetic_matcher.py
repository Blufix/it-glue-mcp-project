"""Unit tests for phonetic matching algorithms."""

import pytest
from typing import List, Set

from src.query.phonetic_matcher import (
    PhoneticMatcher,
    PhoneticAlgorithm,
    PhoneticMatch
)


class TestPhoneticMatcher:
    """Test the phonetic matcher."""
    
    @pytest.fixture
    def matcher(self):
        """Create a phonetic matcher instance."""
        return PhoneticMatcher(weight=0.3)
    
    def test_soundex_encoding(self, matcher):
        """Test Soundex encoding."""
        test_cases = [
            ("Smith", "S530"),
            ("Schmidt", "S530"),  # Should match Smith
            ("Johnson", "J525"),
            ("Jonsen", "J525"),   # Should match Johnson
            ("Williams", "W452"),
            ("Wilson", "W425"),
            ("Microsoft", "M262"),
            ("Microsft", "M262"),  # Typo should match
            ("Google", "G240"),
            ("Goggle", "G240"),    # Should match
        ]
        
        for word, expected in test_cases:
            result = matcher.soundex(word)
            assert result == expected, f"Soundex({word}) = {result}, expected {expected}"
    
    def test_soundex_similar_sounds(self, matcher):
        """Test that similar sounding names get same Soundex."""
        similar_groups = [
            ["Smith", "Smythe", "Schmidt"],
            ["Johnson", "Jonsen", "Johnsen"],
            ["Catherine", "Katherine", "Kathryn"],
        ]
        
        for group in similar_groups:
            codes = [matcher.soundex(name) for name in group]
            assert len(set(codes)) == 1, f"Group {group} should have same Soundex"
    
    def test_metaphone_encoding(self, matcher):
        """Test Metaphone encoding."""
        test_cases = [
            ("phone", "FN"),
            ("fone", "FN"),      # Should match
            ("quick", "KK"),
            ("quik", "KK"),      # Should match
            ("server", "SRFR"),
            ("service", "SRFS"),
            ("database", "TTBS"),
            ("network", "NTWRK"),
        ]
        
        for word, expected_prefix in test_cases:
            result = matcher.metaphone(word)
            assert result.startswith(expected_prefix), \
                f"Metaphone({word}) = {result}, should start with {expected_prefix}"
    
    def test_double_metaphone(self, matcher):
        """Test Double Metaphone with alternate pronunciations."""
        test_cases = [
            # Word, primary starts with, has alternate
            ("Caesar", "S", False),  # Can be pronounced with S or K
            ("School", "S", True),   # SCH can be SK in some languages
            ("Chemistry", "K", False),
            ("Charlotte", "X", False),  # CH as SH sound
        ]
        
        for word, primary_start, has_alternate in test_cases:
            primary, alternate = matcher.double_metaphone(word)
            
            assert primary.startswith(primary_start), \
                f"Primary metaphone for {word} should start with {primary_start}"
            
            if has_alternate:
                assert alternate != "", f"{word} should have alternate pronunciation"
                assert alternate != primary, "Alternate should differ from primary"
    
    def test_match_phonetic_soundex(self, matcher):
        """Test phonetic matching using Soundex."""
        test_cases = [
            ("Smith", "Smythe", 1.0),
            ("Johnson", "Jonsen", 1.0),
            ("Microsoft", "Microsft", 1.0),
            ("Apple", "Orange", 0.0),
            ("Server", "Service", 0.0),
        ]
        
        for word1, word2, expected in test_cases:
            score = matcher.match_phonetic(
                word1, word2, 
                algorithm=PhoneticAlgorithm.SOUNDEX
            )
            assert score == expected, \
                f"Soundex match({word1}, {word2}) = {score}, expected {expected}"
    
    def test_match_phonetic_metaphone(self, matcher):
        """Test phonetic matching using Metaphone."""
        test_cases = [
            ("phone", "fone", 1.0),
            ("quick", "quik", 1.0),
            ("night", "nite", 1.0),
            ("server", "service", 0.0),
            ("database", "network", 0.0),
        ]
        
        for word1, word2, expected in test_cases:
            score = matcher.match_phonetic(
                word1, word2,
                algorithm=PhoneticAlgorithm.METAPHONE
            )
            assert abs(score - expected) < 0.1, \
                f"Metaphone match({word1}, {word2}) = {score}, expected ~{expected}"
    
    def test_find_phonetic_matches(self, matcher):
        """Test finding phonetic matches in candidates."""
        query = "Jonsen"
        candidates = [
            "Johnson Corporation",
            "Jonsen Systems",
            "Jackson Industries",
            "Microsoft",
            "Apple Inc"
        ]
        
        matches = matcher.find_phonetic_matches(
            query, candidates,
            threshold=0.7,
            algorithm=PhoneticAlgorithm.SOUNDEX
        )
        
        assert len(matches) >= 2  # Should match Johnson and Jonsen
        
        # Check that matches are sorted by confidence
        for i in range(len(matches) - 1):
            assert matches[i].confidence >= matches[i + 1].confidence
        
        # Verify Johnson variations are matched
        matched_names = [m.matched for m in matches]
        assert any("Johnson" in name for name in matched_names)
        assert any("Jonsen" in name for name in matched_names)
    
    def test_weight_application(self, matcher):
        """Test that weight is correctly applied to scores."""
        matcher.weight = 0.5  # Set specific weight
        
        query = "Smith"
        candidates = ["Smythe"]
        
        matches = matcher.find_phonetic_matches(
            query, candidates,
            algorithm=PhoneticAlgorithm.SOUNDEX
        )
        
        assert len(matches) == 1
        match = matches[0]
        
        # Raw score should be 1.0 for Soundex match
        assert match.metadata["raw_score"] == 1.0
        # Weighted score should be raw * weight
        assert match.confidence == 0.5
        assert match.metadata["weighted_score"] == 0.5
    
    def test_batch_phonetic_match(self, matcher):
        """Test batch phonetic matching."""
        queries = ["Smith", "Jonsen", "Microsft"]
        candidates = [
            "Smythe Corporation",
            "Johnson Systems",
            "Microsoft Inc",
            "Apple Corp"
        ]
        
        results = matcher.batch_phonetic_match(
            queries, candidates,
            algorithm=PhoneticAlgorithm.SOUNDEX
        )
        
        assert len(results) == 3
        assert "Smith" in results
        assert "Jonsen" in results
        assert "Microsft" in results
        
        # Check Smith matches Smythe
        smith_matches = results["Smith"]
        assert any("Smythe" in m.matched for m in smith_matches)
        
        # Check Microsft matches Microsoft
        ms_matches = results["Microsft"]
        assert any("Microsoft" in m.matched for m in ms_matches)
    
    def test_get_phonetic_variants(self, matcher):
        """Test getting all phonetic variants of a word."""
        word = "Johnson"
        variants = matcher.get_phonetic_variants(word)
        
        assert "soundex" in variants
        assert "metaphone" in variants
        assert "double_metaphone_primary" in variants
        assert "double_metaphone_alternate" in variants
        
        # Soundex should be J525
        assert variants["soundex"] == "J525"
        
        # All variants should be non-empty except possibly alternate
        assert variants["soundex"]
        assert variants["metaphone"]
        assert variants["double_metaphone_primary"]
    
    def test_precompute_phonetic_index(self, matcher):
        """Test precomputing phonetic index."""
        terms = [
            "Microsoft",
            "Microsft",  # Typo
            "Apple",
            "Google",
            "Goggle",    # Typo
            "Amazon",
            "Johnson",
            "Jonsen"     # Variation
        ]
        
        index = matcher.precompute_phonetic_index(terms)
        
        # Check index structure
        assert isinstance(index, dict)
        assert len(index) > 0
        
        # Check that similar terms are indexed together
        # Find Soundex key for Microsoft
        ms_soundex = matcher.soundex("Microsoft")
        soundex_key = f"soundex:{ms_soundex}"
        
        if soundex_key in index:
            assert "Microsoft" in index[soundex_key]
            assert "Microsft" in index[soundex_key]
    
    def test_lookup_phonetic_index(self, matcher):
        """Test looking up terms in phonetic index."""
        terms = [
            "Microsoft Corporation",
            "Microsft Corp",  # Typo
            "Apple Inc",
            "Johnson Systems",
            "Jonsen Corp"
        ]
        
        index = matcher.precompute_phonetic_index(terms)
        
        # Lookup variations
        matches = matcher.lookup_phonetic_index("Johnsen", index)
        
        assert len(matches) > 0
        assert any("Johnson" in m for m in matches)
        assert any("Jonsen" in m for m in matches)
    
    def test_empty_input(self, matcher):
        """Test handling of empty input."""
        assert matcher.soundex("") == ""
        assert matcher.metaphone("") == ""
        assert matcher.double_metaphone("") == ("", "")
        
        score = matcher.match_phonetic("", "test")
        assert score == 0.0
        
        score = matcher.match_phonetic("test", "")
        assert score == 0.0
    
    def test_special_characters(self, matcher):
        """Test handling of special characters."""
        test_cases = [
            "O'Brien",
            "Smith-Jones",
            "McDonald's",
            "AT&T",
            "3Com"
        ]
        
        for term in test_cases:
            # Should not crash
            soundex = matcher.soundex(term)
            metaphone = matcher.metaphone(term)
            primary, alternate = matcher.double_metaphone(term)
            
            # Should produce some output
            assert soundex or metaphone or primary
    
    def test_case_insensitive(self, matcher):
        """Test that phonetic matching is case-insensitive."""
        test_cases = [
            ("smith", "SMITH"),
            ("Johnson", "johnson"),
            ("MicroSoft", "microsoft")
        ]
        
        for word1, word2 in test_cases:
            soundex1 = matcher.soundex(word1)
            soundex2 = matcher.soundex(word2)
            assert soundex1 == soundex2
            
            metaphone1 = matcher.metaphone(word1)
            metaphone2 = matcher.metaphone(word2)
            assert metaphone1 == metaphone2
    
    def test_phonetic_match_types(self, matcher):
        """Test different phonetic algorithms produce different results."""
        word1 = "phone"
        word2 = "fone"
        
        soundex_score = matcher.match_phonetic(
            word1, word2,
            algorithm=PhoneticAlgorithm.SOUNDEX
        )
        
        metaphone_score = matcher.match_phonetic(
            word1, word2,
            algorithm=PhoneticAlgorithm.METAPHONE
        )
        
        double_metaphone_score = matcher.match_phonetic(
            word1, word2,
            algorithm=PhoneticAlgorithm.DOUBLE_METAPHONE
        )
        
        # All should match but potentially with different scores
        assert soundex_score > 0
        assert metaphone_score > 0
        assert double_metaphone_score > 0
    
    def test_it_specific_terms(self, matcher):
        """Test phonetic matching for IT-specific terms."""
        it_variations = [
            ("kubernetes", "kubernets"),  # Common typo
            ("nginx", "enjinx"),          # Phonetic spelling
            ("PostgreSQL", "PostgressSQL"), # Extra s
            ("GitHub", "GitHab"),          # Similar sound
            ("Docker", "Dokker"),          # Alternative spelling
        ]
        
        for correct, variation in it_variations:
            # At least one algorithm should match
            soundex_match = matcher.match_phonetic(
                correct, variation,
                algorithm=PhoneticAlgorithm.SOUNDEX
            )
            metaphone_match = matcher.match_phonetic(
                correct, variation,
                algorithm=PhoneticAlgorithm.METAPHONE
            )
            
            assert soundex_match > 0 or metaphone_match > 0, \
                f"Should find phonetic match between {correct} and {variation}"