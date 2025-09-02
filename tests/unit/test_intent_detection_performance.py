"""Performance tests for query intent detection with new resource types."""

import pytest
import time
import asyncio
from unittest.mock import Mock, AsyncMock

from src.query.intelligent_query_processor import IntelligentQueryProcessor


class TestIntentDetectionPerformance:
    """Test performance of intent detection to ensure <50ms requirement."""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance for testing."""
        return IntelligentQueryProcessor(
            neo4j_driver=None,
            cache_manager=None,
            enable_fuzzy=True,
            fuzzy_threshold=0.8
        )
    
    def test_intent_detection_performance_single_query(self, processor):
        """Test single query intent detection performance."""
        test_queries = [
            # Organizations
            "show all organizations",
            "find organization Microsoft",
            "list customers",
            
            # Locations
            "show all locations for TechCorp",
            "find San Francisco office",
            "list sites for customer",
            
            # Flexible Assets
            "show SSL certificates",
            "list warranties for Dell",
            "show all software licenses",
            "show asset types",
            "what fields does warranty have",
            
            # Documents
            "find documentation for server setup",
            "search runbooks",
            "search knowledge base for password reset",
            
            # Contacts
            "find John Smith contact",
            "list IT managers for TechCorp",
            "who is the network admin",
            
            # Existing patterns
            "show servers for Microsoft",
            "what depends on PROD-DB-01",
            "show admin password for server",
            "what changed recently for system"
        ]
        
        # Warm up
        for _ in range(3):
            processor._detect_intent("warm up query")
        
        # Test each query
        max_time = 0
        total_time = 0
        
        for query in test_queries:
            start = time.perf_counter()
            result = processor._detect_intent(query)
            end = time.perf_counter()
            
            duration_ms = (end - start) * 1000
            total_time += duration_ms
            max_time = max(max_time, duration_ms)
            
            # Each query should be under 50ms
            assert duration_ms < 50, f"Query '{query}' took {duration_ms:.2f}ms (limit: 50ms)"
            
            # Verify intent was detected
            assert result.primary_intent != 'general_search' or 'search' in query.lower(), \
                f"Query '{query}' should have specific intent, got '{result.primary_intent}'"
        
        avg_time = total_time / len(test_queries)
        
        # Average should be well under 50ms
        assert avg_time < 30, f"Average detection time {avg_time:.2f}ms exceeds 30ms target"
        
        # P95 (max in this case) should be under 50ms
        assert max_time < 50, f"Max detection time {max_time:.2f}ms exceeds 50ms P95 target"
        
        print(f"\nPerformance Results:")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Max: {max_time:.2f}ms")
        print(f"  Total queries tested: {len(test_queries)}")
    
    def test_intent_detection_batch_performance(self, processor):
        """Test batch query processing performance."""
        # Generate 100 queries mixing all resource types
        batch_queries = []
        patterns = [
            "show all organizations",
            "find location {}",
            "list SSL certificates",
            "search documentation for {}",
            "find contact {}",
            "show servers for {}",
            "list warranties",
            "show asset types",
            "who is {} contact",
            "what changed for {}"
        ]
        
        # Generate 100 queries
        for i in range(100):
            pattern = patterns[i % len(patterns)]
            query = pattern.format(f"Entity{i}")
            batch_queries.append(query)
        
        # Process all queries and measure time
        start = time.perf_counter()
        
        results = []
        for query in batch_queries:
            result = processor._detect_intent(query)
            results.append(result)
        
        end = time.perf_counter()
        
        total_duration_ms = (end - start) * 1000
        avg_per_query = total_duration_ms / len(batch_queries)
        
        # 100 queries should complete in under 5 seconds (50ms each)
        assert total_duration_ms < 5000, \
            f"Batch of 100 queries took {total_duration_ms:.2f}ms (limit: 5000ms)"
        
        # Average per query should be under 50ms
        assert avg_per_query < 50, \
            f"Average per query {avg_per_query:.2f}ms exceeds 50ms"
        
        # Verify all queries got processed
        assert len(results) == 100
        
        # Check intent distribution
        intent_counts = {}
        for result in results:
            intent = result.primary_intent
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        print(f"\nBatch Performance Results:")
        print(f"  Total time for 100 queries: {total_duration_ms:.2f}ms")
        print(f"  Average per query: {avg_per_query:.2f}ms")
        print(f"  Intent distribution: {intent_counts}")
    
    def test_disambiguation_performance(self, processor):
        """Test performance of disambiguation logic."""
        # Ambiguous queries that might match multiple patterns
        ambiguous_queries = [
            "find microsoft",  # Could be org, contact, or config
            "show john",  # Could be contact or configuration
            "list all",  # Very generic
            "get info",  # Very generic
            "search system",  # Could be config or documentation
            "find office",  # Could be location or contact
            "show certificate",  # Could be asset or password
            "list manager"  # Could be contact or role
        ]
        
        max_time = 0
        total_time = 0
        
        for query in ambiguous_queries:
            start = time.perf_counter()
            result = processor._detect_intent(query)
            end = time.perf_counter()
            
            duration_ms = (end - start) * 1000
            total_time += duration_ms
            max_time = max(max_time, duration_ms)
            
            # Even ambiguous queries should be under 50ms
            assert duration_ms < 50, \
                f"Ambiguous query '{query}' took {duration_ms:.2f}ms (limit: 50ms)"
            
            # Should provide suggestions for disambiguation or follow-ups
            # Note: Some queries may match specific intents and get follow-up suggestions instead
            if result.primary_intent == 'general_search' or result.confidence < 0.7:
                assert len(result.suggested_queries) > 0, \
                    f"Ambiguous query '{query}' should have suggestions"
        
        avg_time = total_time / len(ambiguous_queries)
        
        print(f"\nDisambiguation Performance:")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Max: {max_time:.2f}ms")
        
        assert avg_time < 40, f"Average disambiguation time {avg_time:.2f}ms exceeds 40ms"
    
    def test_no_regression_existing_patterns(self, processor):
        """Ensure no performance regression on existing patterns."""
        existing_queries = [
            "show servers for Microsoft",
            "what depends on PROD-WEB-01",
            "impact analysis for database",
            "show admin passwords for server",
            "what changed recently for system",
            "show service connections for app",
            "show network topology for datacenter",
            "find documentation for setup"
        ]
        
        # Test original patterns still work fast
        for query in existing_queries:
            start = time.perf_counter()
            result = processor._detect_intent(query)
            end = time.perf_counter()
            
            duration_ms = (end - start) * 1000
            
            # Should be very fast for existing patterns
            assert duration_ms < 30, \
                f"Existing pattern '{query}' regressed: {duration_ms:.2f}ms (limit: 30ms)"
            
            # Should have reasonable confidence for existing patterns
            # Some patterns may have slightly lower confidence due to entity ambiguity
            assert result.confidence >= 0.7, \
                f"Existing pattern '{query}' has low confidence: {result.confidence}"
    
    def test_resource_type_specific_intents(self, processor):
        """Test that each resource type has working intent detection."""
        resource_type_queries = {
            'Organizations': [
                ("show all organizations", "list_organizations"),
                ("find organization TechCorp", "find_organization"),
                ("list customers", "list_organizations")
            ],
            'Locations': [
                ("show all locations for Org", "find_locations"),
                ("find San Francisco office", "find_location_by_city"),
                ("list sites for company", "find_locations")
            ],
            'Flexible Assets': [
                ("show SSL certificates", "find_flexible_assets"),
                ("list warranties", "find_flexible_assets"),
                ("show asset types", "list_asset_types")
            ],
            'Documents': [
                ("find documentation for server", "find_documentation"),
                ("search runbooks", "find_documentation"),
                ("search knowledge base", "find_documentation")
            ],
            'Contacts': [
                ("find John Smith contact", "find_contact"),
                ("list IT managers for Org", "find_contacts"),
                ("who is admin contact", "find_contact_by_name")
            ]
        }
        
        for resource_type, queries in resource_type_queries.items():
            print(f"\nTesting {resource_type}:")
            
            for query, expected_intent in queries:
                start = time.perf_counter()
                result = processor._detect_intent(query)
                end = time.perf_counter()
                
                duration_ms = (end - start) * 1000
                
                # Performance check
                assert duration_ms < 50, \
                    f"{resource_type} query '{query}' took {duration_ms:.2f}ms"
                
                # Intent check
                assert result.primary_intent == expected_intent, \
                    f"{resource_type} query '{query}' got intent '{result.primary_intent}', expected '{expected_intent}'"
                
                print(f"  ✓ '{query}' -> {expected_intent} ({duration_ms:.2f}ms)")


if __name__ == "__main__":
    # Run tests directly
    processor = IntelligentQueryProcessor(
        neo4j_driver=None,
        cache_manager=None,
        enable_fuzzy=True,
        fuzzy_threshold=0.8
    )
    
    test = TestIntentDetectionPerformance()
    
    print("Running performance tests...")
    test.test_intent_detection_performance_single_query(processor)
    test.test_intent_detection_batch_performance(processor)
    test.test_disambiguation_performance(processor)
    test.test_no_regression_existing_patterns(processor)
    test.test_resource_type_specific_intents(processor)
    
    print("\n✓ All performance tests passed!")
    print("Intent detection meets <50ms requirement with new resource types")