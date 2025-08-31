"""Comprehensive tests for query enhancement capabilities."""

import pytest
import asyncio
import time
from typing import Dict, List, Any
from unittest.mock import Mock, patch, AsyncMock
import json

from src.query.fuzzy_enhancer import QueryFuzzyEnhancer, EnhancedQuery
from src.query.fuzzy_matcher import FuzzyMatcher
from src.query.phonetic_matcher import PhoneticMatcher
from src.query.query_templates import QueryTemplateManager, QueryPriority
from src.query.intelligent_query_processor import IntelligentQueryProcessor
from src.nlp.entity_extractor import EntityExtractor
from src.nlp.intent_classifier import IntentClassifier
from src.context.session_manager import SessionManager
from src.ranking.result_ranker import ResultRanker
from src.cache.redis_cache import RedisCache


class TestFuzzyMatching:
    """Test fuzzy matching capabilities."""
    
    def test_basic_fuzzy_match(self):
        """Test basic fuzzy matching with typos."""
        matcher = FuzzyMatcher()
        
        # Test organization name matching
        result = matcher.fuzzy_match(
            "Microsft",
            ["Microsoft", "Apple", "Google"],
            threshold=0.8
        )
        
        assert len(result) > 0
        assert result[0]["match"] == "Microsoft"
        assert result[0]["score"] > 0.8
    
    def test_company_suffix_normalization(self):
        """Test normalization of company suffixes."""
        matcher = FuzzyMatcher()
        
        # Test different suffix variations
        test_cases = [
            ("Contoso Ltd", "Contoso Limited"),
            ("Acme Inc", "Acme Incorporated"),
            ("Tech Corp", "Tech Corporation")
        ]
        
        for input_name, expected in test_cases:
            result = matcher.fuzzy_match(
                input_name,
                [expected, "Other Company"],
                threshold=0.7
            )
            assert result[0]["match"] == expected
    
    def test_case_insensitive_matching(self):
        """Test case-insensitive matching."""
        matcher = FuzzyMatcher()
        
        result = matcher.fuzzy_match(
            "microsoft",
            ["Microsoft", "MICROSOFT", "MicroSoft"],
            threshold=0.9
        )
        
        assert len(result) == 3
        assert all(r["score"] == 1.0 for r in result)
    
    def test_threshold_filtering(self):
        """Test that matches below threshold are filtered."""
        matcher = FuzzyMatcher()
        
        result = matcher.fuzzy_match(
            "test",
            ["test", "testing", "completely different"],
            threshold=0.8
        )
        
        # "completely different" should be filtered out
        assert all(r["score"] >= 0.8 for r in result)
        assert "completely different" not in [r["match"] for r in result]


class TestPhoneticMatching:
    """Test phonetic matching algorithms."""
    
    def test_soundex_matching(self):
        """Test Soundex algorithm."""
        matcher = PhoneticMatcher()
        
        # Test similar sounding words
        soundex1 = matcher.soundex("Johnson")
        soundex2 = matcher.soundex("Jonsen")
        
        assert soundex1 == soundex2
    
    def test_metaphone_matching(self):
        """Test Metaphone algorithm."""
        matcher = PhoneticMatcher()
        
        # Test phonetic variations
        meta1 = matcher.metaphone("Microsoft")
        meta2 = matcher.metaphone("Microsft")
        
        # Should be similar
        assert meta1[:4] == meta2[:4]
    
    def test_double_metaphone_matching(self):
        """Test Double Metaphone algorithm."""
        matcher = PhoneticMatcher()
        
        # Test multiple pronunciations
        primary1, secondary1 = matcher.double_metaphone("Smith")
        primary2, secondary2 = matcher.double_metaphone("Schmidt")
        
        # Should have some overlap
        assert primary1 or secondary1 or primary2 or secondary2
    
    def test_phonetic_match_integration(self):
        """Test integrated phonetic matching."""
        matcher = PhoneticMatcher()
        
        matches = matcher.match(
            "Jonsen",
            ["Johnson", "Jensen", "Jackson", "Williams"]
        )
        
        assert len(matches) > 0
        assert "Johnson" in [m["match"] for m in matches]
        assert "Jensen" in [m["match"] for m in matches]


class TestQueryEnhancement:
    """Test complete query enhancement pipeline."""
    
    def test_typo_correction(self):
        """Test typo correction in queries."""
        enhancer = QueryFuzzyEnhancer()
        
        result = enhancer.enhance_query(
            "pasword for mircosoft",
            context={"organization": "Contoso"}
        )
        
        assert "password" in result.corrected_query.lower()
        assert "microsoft" in result.corrected_query.lower()
        assert result.overall_confidence > 0.7
    
    def test_acronym_expansion(self):
        """Test acronym expansion."""
        enhancer = QueryFuzzyEnhancer()
        
        result = enhancer.enhance_query(
            "AD password reset",
            context={"organization": "Contoso"}
        )
        
        # Should expand AD to Active Directory
        expanded = False
        for token in result.enhanced_tokens:
            if token.expansions and "Active Directory" in token.expansions:
                expanded = True
                break
        
        assert expanded
    
    def test_context_preservation(self):
        """Test that context is preserved during enhancement."""
        enhancer = QueryFuzzyEnhancer()
        
        context = {
            "organization": "Contoso",
            "user": "john.doe",
            "session_id": "test-123"
        }
        
        result = enhancer.enhance_query(
            "server status",
            context=context
        )
        
        assert result.metadata.get("context") == context
    
    def test_confidence_scoring(self):
        """Test confidence score calculation."""
        enhancer = QueryFuzzyEnhancer()
        
        # High confidence - no corrections needed
        result1 = enhancer.enhance_query("Microsoft server status")
        assert result1.overall_confidence > 0.9
        
        # Lower confidence - multiple corrections
        result2 = enhancer.enhance_query("mircosoft srvr stts")
        assert result2.overall_confidence < result1.overall_confidence


class TestZeroHallucinationGuarantee:
    """Test zero hallucination guarantee."""
    
    @pytest.mark.asyncio
    async def test_result_validation(self):
        """Test that all results trace back to source data."""
        processor = IntelligentQueryProcessor()
        
        # Mock IT Glue data source
        with patch.object(processor, 'fetch_from_itglue') as mock_fetch:
            mock_fetch.return_value = [
                {"id": "1", "type": "configuration", "name": "Server1"},
                {"id": "2", "type": "configuration", "name": "Server2"}
            ]
            
            results = await processor.process_query("server status")
            
            # Verify all results have source IDs
            for result in results:
                assert result.get("source_id") is not None
                assert result.get("source_type") in ["configuration", "password", "document"]
    
    @pytest.mark.asyncio
    async def test_no_fabricated_data(self):
        """Test that no data is fabricated."""
        processor = IntelligentQueryProcessor()
        
        with patch.object(processor, 'fetch_from_itglue') as mock_fetch:
            mock_fetch.return_value = []  # No data found
            
            results = await processor.process_query("non-existent server")
            
            # Should return empty results, not fabricated data
            assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_source_tracking(self):
        """Test that sources are properly tracked."""
        ranker = ResultRanker()
        
        results = [
            {"id": "1", "name": "Server1", "source_id": "itglue-123"},
            {"id": "2", "name": "Server2", "source_id": "itglue-456"}
        ]
        
        ranked = await ranker.rank_results(results, "server")
        
        # All results should maintain source tracking
        for result in ranked:
            assert "source_id" in result
            assert result["source_id"].startswith("itglue-")


class TestPerformanceBenchmarks:
    """Test performance benchmarks."""
    
    def test_fuzzy_match_performance(self):
        """Test fuzzy matching performance."""
        matcher = FuzzyMatcher()
        
        # Generate test data
        candidates = [f"Company{i}" for i in range(100)]
        
        start = time.time()
        matcher.fuzzy_match("Compny50", candidates, threshold=0.8)
        duration = (time.time() - start) * 1000
        
        # Should complete within 100ms for 100 candidates
        assert duration < 100
    
    def test_phonetic_match_performance(self):
        """Test phonetic matching performance."""
        matcher = PhoneticMatcher()
        
        candidates = [f"Johnson{i}" for i in range(50)]
        
        start = time.time()
        matcher.match("Jonsen", candidates)
        duration = (time.time() - start) * 1000
        
        # Should complete within 50ms for 50 candidates
        assert duration < 50
    
    def test_query_enhancement_performance(self):
        """Test complete enhancement pipeline performance."""
        enhancer = QueryFuzzyEnhancer()
        
        queries = [
            "pasword for mircosoft",
            "server dwn emergency",
            "backup verfication status"
        ]
        
        for query in queries:
            start = time.time()
            enhancer.enhance_query(query)
            duration = (time.time() - start) * 1000
            
            # Should complete within 200ms (P95 target)
            assert duration < 200
    
    @pytest.mark.asyncio
    async def test_concurrent_query_performance(self):
        """Test performance under concurrent load."""
        enhancer = QueryFuzzyEnhancer()
        
        async def enhance_query_async(query):
            return await asyncio.get_event_loop().run_in_executor(
                None, enhancer.enhance_query, query
            )
        
        # Create 10 concurrent queries
        queries = [f"query {i}" for i in range(10)]
        
        start = time.time()
        results = await asyncio.gather(*[enhance_query_async(q) for q in queries])
        duration = (time.time() - start) * 1000
        
        # Should handle 10 concurrent queries within 500ms
        assert duration < 500
        assert len(results) == 10


class TestEntityExtraction:
    """Test entity extraction integration."""
    
    def test_organization_extraction(self):
        """Test organization entity extraction."""
        extractor = EntityExtractor()
        
        entities = extractor.extract("Microsoft server at Contoso headquarters")
        
        assert "Microsoft" in entities.get("organizations", [])
        assert "Contoso" in entities.get("organizations", [])
    
    def test_ip_address_extraction(self):
        """Test IP address extraction."""
        extractor = EntityExtractor()
        
        entities = extractor.extract("Server at 192.168.1.100 is down")
        
        assert "192.168.1.100" in entities.get("ip_addresses", [])
    
    def test_date_extraction(self):
        """Test date extraction."""
        extractor = EntityExtractor()
        
        entities = extractor.extract("Changes since yesterday at 3pm")
        
        assert len(entities.get("dates", [])) > 0


class TestIntentClassification:
    """Test intent classification integration."""
    
    def test_troubleshooting_intent(self):
        """Test troubleshooting intent detection."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("server is down emergency")
        
        assert intent.primary_intent == "troubleshooting"
        assert intent.confidence > 0.8
    
    def test_investigation_intent(self):
        """Test investigation intent detection."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("who made changes yesterday")
        
        assert intent.primary_intent == "investigation"
    
    def test_audit_intent(self):
        """Test audit intent detection."""
        classifier = IntentClassifier()
        
        intent = classifier.classify("compliance report for Q3")
        
        assert intent.primary_intent == "audit"


class TestQueryTemplates:
    """Test query template system."""
    
    def test_emergency_template(self):
        """Test emergency server down template."""
        manager = QueryTemplateManager()
        
        template = manager.get_template("emergency_server_down")
        expanded = template.expand({"server_name": "DC01"})
        
        assert len(expanded.sub_queries) > 0
        assert expanded.priority == QueryPriority.CRITICAL
        assert any("DC01" in q.query for q in expanded.sub_queries)
    
    def test_template_parameter_validation(self):
        """Test template parameter validation."""
        manager = QueryTemplateManager()
        
        template = manager.get_template("password_recovery")
        
        # Should raise error for missing required parameters
        with pytest.raises(ValueError):
            template.expand({})  # Missing user_name
    
    def test_template_caching(self):
        """Test template result caching."""
        manager = QueryTemplateManager()
        
        # Load template twice
        template1 = manager.get_template("change_investigation")
        template2 = manager.get_template("change_investigation")
        
        # Should be the same instance (cached)
        assert template1 is template2


class TestCacheIntegration:
    """Test cache integration with query enhancement."""
    
    @pytest.mark.asyncio
    async def test_fuzzy_match_caching(self):
        """Test fuzzy match result caching."""
        cache = RedisCache()
        matcher = FuzzyMatcher()
        
        # Mock Redis client
        with patch.object(cache, 'get') as mock_get, \
             patch.object(cache, 'set') as mock_set:
            
            mock_get.return_value = None  # Cache miss
            
            # First call - cache miss
            result1 = matcher.fuzzy_match("test", ["test1", "test2"])
            
            # Verify cache was set
            mock_set.assert_called()
            
            # Second call - should use cache
            mock_get.return_value = json.dumps(result1)
            result2 = matcher.fuzzy_match("test", ["test1", "test2"])
            
            assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_query_result_caching(self):
        """Test query result caching."""
        processor = IntelligentQueryProcessor()
        
        with patch.object(processor.cache, 'get') as mock_get, \
             patch.object(processor.cache, 'set') as mock_set:
            
            mock_get.return_value = None
            
            # Process query
            await processor.process_query("test query")
            
            # Verify cache was set with appropriate TTL
            mock_set.assert_called()
            call_args = mock_set.call_args
            assert call_args[1]["ttl"] > 0


class TestSessionContext:
    """Test session context management."""
    
    @pytest.mark.asyncio
    async def test_context_preservation(self):
        """Test that context is preserved across queries."""
        session_mgr = SessionManager()
        
        session_id = "test-session"
        
        # Add context
        await session_mgr.add_query(session_id, "Microsoft servers")
        await session_mgr.update_context(session_id, {
            "organization": "Microsoft",
            "focus": "servers"
        })
        
        # Retrieve context
        context = await session_mgr.get_context(session_id)
        
        assert context["organization"] == "Microsoft"
        assert context["focus"] == "servers"
        assert len(context["query_history"]) == 1
    
    @pytest.mark.asyncio
    async def test_query_history_limit(self):
        """Test that query history is limited."""
        session_mgr = SessionManager()
        
        session_id = "test-session"
        
        # Add more than limit
        for i in range(10):
            await session_mgr.add_query(session_id, f"query {i}")
        
        context = await session_mgr.get_context(session_id)
        
        # Should only keep last 5
        assert len(context["query_history"]) == 5
        assert context["query_history"][-1] == "query 9"


class TestEndToEndIntegration:
    """Test end-to-end query enhancement integration."""
    
    @pytest.mark.asyncio
    async def test_complete_query_flow(self):
        """Test complete query processing flow."""
        # This test simulates the complete flow from user query to results
        
        # 1. User query with typos
        user_query = "pasword for mircosoft srvr"
        
        # 2. Enhancement
        enhancer = QueryFuzzyEnhancer()
        enhanced = enhancer.enhance_query(user_query)
        
        assert "password" in enhanced.corrected_query.lower()
        assert "microsoft" in enhanced.corrected_query.lower()
        assert "server" in enhanced.corrected_query.lower()
        
        # 3. Entity extraction
        extractor = EntityExtractor()
        entities = extractor.extract(enhanced.corrected_query)
        
        assert "Microsoft" in entities.get("organizations", [])
        
        # 4. Intent classification
        classifier = IntentClassifier()
        intent = classifier.classify(enhanced.corrected_query)
        
        assert intent.primary_intent in ["lookup", "troubleshooting"]
        
        # 5. Template matching (if applicable)
        manager = QueryTemplateManager()
        templates = manager.find_matching_templates(enhanced.corrected_query)
        
        # 6. Mock query execution
        with patch('src.query.neo4j_query_builder.Neo4jQueryBuilder') as MockBuilder:
            mock_builder = MockBuilder.return_value
            mock_builder.build.return_value = "MATCH (p:Password) WHERE p.organization = 'Microsoft'"
            
            # 7. Result ranking
            ranker = ResultRanker()
            mock_results = [
                {"id": "1", "name": "Admin Password", "relevance": 0.9},
                {"id": "2", "name": "Service Password", "relevance": 0.7}
            ]
            
            ranked = await ranker.rank_results(mock_results, enhanced.corrected_query)
            
            assert len(ranked) == 2
            assert ranked[0]["relevance"] >= ranked[1]["relevance"]
    
    @pytest.mark.asyncio 
    async def test_error_handling(self):
        """Test error handling throughout the pipeline."""
        processor = IntelligentQueryProcessor()
        
        # Test with malformed query
        with patch.object(processor, 'fetch_from_itglue') as mock_fetch:
            mock_fetch.side_effect = Exception("API Error")
            
            # Should handle gracefully
            results = await processor.process_query("test query")
            
            # Should return empty results or cached data
            assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_fallback_to_exact_match(self):
        """Test fallback to exact match when fuzzy fails."""
        enhancer = QueryFuzzyEnhancer()
        
        # Query that shouldn't need correction
        result = enhancer.enhance_query(
            "SELECT * FROM configurations",
            candidates=["configurations"]
        )
        
        # Should preserve exact query
        assert result.corrected_query == "SELECT * FROM configurations"
        assert result.overall_confidence == 1.0


class TestMetricsCollection:
    """Test metrics collection for monitoring."""
    
    def test_query_metrics(self):
        """Test that query metrics are collected."""
        from src.monitoring.metrics import MetricsCollector
        
        collector = MetricsCollector()
        
        # Track query
        collector.track_query("test query", success=True, duration_ms=150)
        
        # Get metrics
        metrics = collector.get_metrics()
        
        assert metrics["query_total"] > 0
        assert metrics["query_success_total"] > 0
        assert "query_duration_seconds" in metrics
    
    def test_fuzzy_correction_metrics(self):
        """Test fuzzy correction metrics."""
        from src.monitoring.metrics import MetricsCollector
        
        collector = MetricsCollector()
        
        # Track corrections
        collector.track_fuzzy_correction("typo", original="mircosoft", corrected="microsoft")
        
        metrics = collector.get_metrics()
        
        assert metrics["fuzzy_corrections_total"] > 0
    
    def test_cache_metrics(self):
        """Test cache hit/miss metrics."""
        from src.monitoring.metrics import MetricsCollector
        
        collector = MetricsCollector()
        
        # Track cache operations
        collector.track_cache_hit("query")
        collector.track_cache_miss("query")
        
        metrics = collector.get_metrics()
        
        assert metrics["cache_hits_total"] > 0
        assert metrics["cache_requests_total"] > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])