"""Performance benchmark tests for query processing."""

import pytest
import time
import asyncio
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch
import json

# Add project root to path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import modules to test
from src.query.fuzzy_matcher import FuzzyMatcher, QueryFuzzyEnhancer
from src.query.parser import QueryParser
from src.query.validator import ZeroHallucinationValidator as QueryValidator


class PerformanceMetrics:
    """Helper class to track performance metrics."""
    
    def __init__(self):
        self.measurements = []
    
    def record(self, duration: float):
        """Record a measurement."""
        self.measurements.append(duration)
    
    def get_stats(self) -> Dict[str, float]:
        """Get performance statistics."""
        if not self.measurements:
            return {"count": 0}
        
        sorted_measurements = sorted(self.measurements)
        count = len(sorted_measurements)
        
        return {
            "count": count,
            "min": min(sorted_measurements),
            "max": max(sorted_measurements),
            "mean": statistics.mean(sorted_measurements),
            "median": statistics.median(sorted_measurements),
            "p95": sorted_measurements[int(count * 0.95)] if count > 0 else 0,
            "p99": sorted_measurements[int(count * 0.99)] if count > 0 else 0,
            "stdev": statistics.stdev(sorted_measurements) if count > 1 else 0
        }


@pytest.fixture
def fuzzy_matcher():
    """Create FuzzyMatcher instance."""
    return FuzzyMatcher()


@pytest.fixture
def query_parser():
    """Create QueryParser instance."""
    return QueryParser()


@pytest.fixture
def query_validator():
    """Create QueryValidator instance."""
    return QueryValidator()


@pytest.fixture
def large_organization_dataset():
    """Generate large dataset of organizations for performance testing."""
    return [
        {"id": str(i), "name": f"Company {i % 100} {suffix}"}
        for i in range(10000)
        for suffix in ["Corporation", "Inc", "Ltd", "LLC", "Group"]
    ]


@pytest.fixture
def complex_queries():
    """Generate complex query patterns for testing."""
    return [
        "show all servers for Microsoft Corporation with Windows Server 2019",
        "find passwords for database servers in production environment at Google",
        "list configurations changed in the last 7 days for Amazon Web Services",
        "what depends on the primary domain controller at Company ABC",
        "show network topology for all branch offices of International Business Machines",
        "investigate performance issues on application servers running Java 11",
        "audit compliance for PCI DSS requirements at Financial Corp",
        "find all SSL certificates expiring in the next 30 days",
        "show backup status for critical databases at Healthcare Inc",
        "list security incidents in the last 24 hours for all organizations"
    ]


class TestFuzzyMatchingPerformance:
    """Performance tests for fuzzy matching."""
    
    def test_fuzzy_match_large_dataset(self, fuzzy_matcher, large_organization_dataset):
        """Test fuzzy matching performance with large dataset."""
        metrics = PerformanceMetrics()
        test_queries = [
            "Microsoft",
            "Microsft",  # Typo
            "IBM",
            "Company 50",
            "Google Cloud"
        ]
        
        for query in test_queries * 20:  # Run each query 20 times
            start = time.perf_counter()
            results = fuzzy_matcher.match_organization(
                query,
                large_organization_dataset[:1000],  # Test with 1000 candidates
                threshold=0.7
            )
            duration = (time.perf_counter() - start) * 1000  # Convert to ms
            metrics.record(duration)
        
        stats = metrics.get_stats()
        
        # Performance assertions
        assert stats["p95"] < 200, f"P95 latency {stats['p95']}ms exceeds 200ms target"
        assert stats["mean"] < 100, f"Mean latency {stats['mean']}ms exceeds 100ms"
        assert len(results) <= 5, "Should return at most 5 results"
    
    def test_phonetic_matching_performance(self, fuzzy_matcher):
        """Test phonetic matching performance."""
        metrics = PerformanceMetrics()
        test_pairs = [
            ("Johnson", "Jonsen"),
            ("Smith", "Smythe"),
            ("Microsoft", "Mikrosoft"),
            ("Google", "Googel"),
            ("Amazon", "Amazone")
        ]
        
        for input_str, candidate in test_pairs * 100:
            start = time.perf_counter()
            score = fuzzy_matcher._phonetic_match(input_str, candidate)
            duration = (time.perf_counter() - start) * 1000
            metrics.record(duration)
        
        stats = metrics.get_stats()
        
        # Phonetic matching should be fast
        assert stats["p95"] < 10, f"P95 latency {stats['p95']}ms exceeds 10ms"
        assert stats["mean"] < 5, f"Mean latency {stats['mean']}ms exceeds 5ms"
    
    def test_normalization_performance(self, fuzzy_matcher):
        """Test organization name normalization performance."""
        metrics = PerformanceMetrics()
        test_names = [
            "Microsoft Corporation, Inc.",
            "International Business Machines (IBM)",
            "Amazon Web Services - AWS",
            "Google Cloud Platform & Partners",
            "Very Long Company Name " * 10
        ]
        
        for name in test_names * 200:
            start = time.perf_counter()
            normalized = fuzzy_matcher._normalize_organization(name)
            duration = (time.perf_counter() - start) * 1000
            metrics.record(duration)
        
        stats = metrics.get_stats()
        
        # Normalization should be very fast
        assert stats["p95"] < 5, f"P95 latency {stats['p95']}ms exceeds 5ms"
        assert stats["mean"] < 2, f"Mean latency {stats['mean']}ms exceeds 2ms"
    
    @pytest.mark.asyncio
    async def test_cached_matching_performance(self, large_organization_dataset):
        """Test performance improvement with caching."""
        cache_manager = AsyncMock()
        cache_manager.get = AsyncMock(return_value=None)
        cache_manager.set = AsyncMock()
        
        matcher = FuzzyMatcher(cache_manager=cache_manager)
        metrics_uncached = PerformanceMetrics()
        metrics_cached = PerformanceMetrics()
        
        # First pass - no cache
        for i in range(50):
            start = time.perf_counter()
            await matcher.match_organization_cached(
                "Microsoft",
                large_organization_dataset[:100],
                threshold=0.7
            )
            duration = (time.perf_counter() - start) * 1000
            metrics_uncached.record(duration)
        
        # Setup cache hit
        cached_result = json.dumps([{
            'original': 'Microsoft',
            'matched': 'Microsoft Corporation',
            'score': 0.95,
            'match_type': 'fuzzy',
            'confidence': 0.9,
            'entity_id': '1',
            'metadata': {},
            'match_time_ms': 10.5
        }])
        cache_manager.get = AsyncMock(return_value=cached_result)
        
        # Second pass - with cache
        for i in range(50):
            start = time.perf_counter()
            await matcher.match_organization_cached(
                "Microsoft",
                large_organization_dataset[:100],
                threshold=0.7
            )
            duration = (time.perf_counter() - start) * 1000
            metrics_cached.record(duration)
        
        stats_uncached = metrics_uncached.get_stats()
        stats_cached = metrics_cached.get_stats()
        
        # Cached should be significantly faster
        assert stats_cached["mean"] < stats_uncached["mean"] * 0.5, \
            "Cached queries should be at least 50% faster"
        assert stats_cached["p95"] < 50, "Cached P95 should be under 50ms"


class TestQueryParsingPerformance:
    """Performance tests for query parsing."""
    
    def test_parse_complex_queries(self, query_parser, complex_queries):
        """Test parsing performance for complex queries."""
        metrics = PerformanceMetrics()
        
        for query in complex_queries * 10:
            start = time.perf_counter()
            parsed = query_parser.parse(query)
            duration = (time.perf_counter() - start) * 1000
            metrics.record(duration)
        
        stats = metrics.get_stats()
        
        # Query parsing should be fast
        assert stats["p95"] < 50, f"P95 latency {stats['p95']}ms exceeds 50ms"
        assert stats["mean"] < 20, f"Mean latency {stats['mean']}ms exceeds 20ms"
    
    def test_pattern_matching_performance(self, query_parser):
        """Test performance of pattern matching in queries."""
        metrics = PerformanceMetrics()
        
        # Generate queries with various patterns
        queries = []
        for i in range(100):
            queries.extend([
                f"show all servers for Company{i}",
                f"get password for system{i}",
                f"find configuration for server{i}",
                f"list changes for organization{i}",
                f"what depends on service{i}"
            ])
        
        for query in queries:
            start = time.perf_counter()
            intent = query_parser.detect_intent(query)
            duration = (time.perf_counter() - start) * 1000
            metrics.record(duration)
        
        stats = metrics.get_stats()
        
        # Intent detection should be very fast
        assert stats["p95"] < 10, f"P95 latency {stats['p95']}ms exceeds 10ms"
        assert stats["mean"] < 5, f"Mean latency {stats['mean']}ms exceeds 5ms"


class TestQueryValidationPerformance:
    """Performance tests for query validation."""
    
    def test_validation_performance(self, query_validator):
        """Test query validation performance."""
        metrics = PerformanceMetrics()
        
        test_queries = [
            {"query": "show servers", "organization": "Microsoft"},
            {"query": "get passwords", "filters": {"type": "database"}},
            {"query": "find changes", "time_range": "last 7 days"},
            {"query": "list configurations", "limit": 100},
            {"query": "show dependencies", "depth": 5}
        ]
        
        for query_data in test_queries * 100:
            start = time.perf_counter()
            is_valid = query_validator.validate(query_data)
            duration = (time.perf_counter() - start) * 1000
            metrics.record(duration)
        
        stats = metrics.get_stats()
        
        # Validation should be very fast
        assert stats["p95"] < 5, f"P95 latency {stats['p95']}ms exceeds 5ms"
        assert stats["mean"] < 2, f"Mean latency {stats['mean']}ms exceeds 2ms"
    
    def test_sanitization_performance(self, query_validator):
        """Test input sanitization performance."""
        metrics = PerformanceMetrics()
        
        # Test with potentially malicious inputs
        test_inputs = [
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "../../etc/passwd",
            "SELECT * FROM passwords WHERE 1=1",
            "a" * 10000  # Very long input
        ]
        
        for input_str in test_inputs * 50:
            start = time.perf_counter()
            sanitized = query_validator.sanitize(input_str)
            duration = (time.perf_counter() - start) * 1000
            metrics.record(duration)
        
        stats = metrics.get_stats()
        
        # Sanitization should handle edge cases quickly
        assert stats["p95"] < 10, f"P95 latency {stats['p95']}ms exceeds 10ms"
        assert stats["mean"] < 5, f"Mean latency {stats['mean']}ms exceeds 5ms"


class TestEndToEndQueryPerformance:
    """End-to-end query performance tests."""
    
    def test_complete_query_pipeline(self, fuzzy_matcher, query_parser, query_validator):
        """Test complete query processing pipeline performance."""
        metrics = PerformanceMetrics()
        
        # Mock organization data
        organizations = [
            {"id": str(i), "name": f"Company {i}"}
            for i in range(100)
        ]
        
        test_queries = [
            "show all servers for Company 1",
            "get passwords for Compny 2",  # Typo
            "find changes at Company 3",
            "list configurations for Cmpany 4",  # Typo
            "what depends on Company 5"
        ]
        
        for query in test_queries * 20:
            start = time.perf_counter()
            
            # Step 1: Parse query
            parsed = query_parser.parse(query)
            
            # Step 2: Validate query
            is_valid = query_validator.validate(parsed)
            
            # Step 3: Extract organization name (simplified)
            org_name = query.split(" for ")[-1] if " for " in query else \
                      query.split(" at ")[-1] if " at " in query else \
                      query.split(" on ")[-1] if " on " in query else None
            
            # Step 4: Fuzzy match organization
            if org_name:
                matches = fuzzy_matcher.match_organization(
                    org_name,
                    organizations,
                    threshold=0.7
                )
            
            duration = (time.perf_counter() - start) * 1000
            metrics.record(duration)
        
        stats = metrics.get_stats()
        
        # Complete pipeline should meet performance targets
        assert stats["p95"] < 200, f"P95 latency {stats['p95']}ms exceeds 200ms target"
        assert stats["mean"] < 100, f"Mean latency {stats['mean']}ms exceeds 100ms"
        assert stats["p99"] < 500, f"P99 latency {stats['p99']}ms exceeds 500ms"


class TestScalabilityBenchmarks:
    """Scalability benchmark tests."""
    
    def test_concurrent_query_processing(self, fuzzy_matcher):
        """Test performance under concurrent load."""
        async def process_query(query: str, candidates: List[Dict]):
            """Simulate concurrent query processing."""
            return fuzzy_matcher.match_organization(query, candidates, 0.7)
        
        async def run_concurrent_test():
            """Run concurrent queries."""
            candidates = [
                {"id": str(i), "name": f"Company {i}"}
                for i in range(100)
            ]
            
            queries = ["Company 1", "Company 2", "Company 3"] * 100
            
            start = time.perf_counter()
            tasks = [process_query(q, candidates) for q in queries]
            results = await asyncio.gather(*tasks)
            duration = time.perf_counter() - start
            
            return duration, len(results)
        
        # Run the async test
        duration, count = asyncio.run(run_concurrent_test())
        
        # Calculate throughput
        throughput = count / duration
        
        # Should handle at least 100 queries per second
        assert throughput > 100, f"Throughput {throughput:.2f} q/s is below 100 q/s target"
    
    def test_memory_efficiency(self, fuzzy_matcher, large_organization_dataset):
        """Test memory efficiency with large datasets."""
        import tracemalloc
        
        tracemalloc.start()
        
        # Process many queries
        for i in range(100):
            fuzzy_matcher.match_organization(
                f"Company {i}",
                large_organization_dataset[:1000],
                threshold=0.7
            )
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Convert to MB
        peak_mb = peak / 1024 / 1024
        
        # Should not use excessive memory
        assert peak_mb < 100, f"Peak memory usage {peak_mb:.2f}MB exceeds 100MB limit"


class TestPerformanceRegression:
    """Performance regression tests."""
    
    def test_fuzzy_match_regression(self, fuzzy_matcher):
        """Test for performance regression in fuzzy matching."""
        # Baseline performance (these should be updated based on actual baseline)
        baseline_p95 = 150  # ms
        baseline_mean = 75  # ms
        
        metrics = PerformanceMetrics()
        candidates = [
            {"id": str(i), "name": f"Company {i}"}
            for i in range(500)
        ]
        
        for i in range(100):
            start = time.perf_counter()
            fuzzy_matcher.match_organization(
                f"Company {i % 50}",
                candidates,
                threshold=0.7
            )
            duration = (time.perf_counter() - start) * 1000
            metrics.record(duration)
        
        stats = metrics.get_stats()
        
        # Check for regression (allow 10% degradation)
        assert stats["p95"] < baseline_p95 * 1.1, \
            f"P95 regression: {stats['p95']}ms vs baseline {baseline_p95}ms"
        assert stats["mean"] < baseline_mean * 1.1, \
            f"Mean regression: {stats['mean']}ms vs baseline {baseline_mean}ms"


def generate_performance_report(results: Dict[str, Any]):
    """Generate a performance test report."""
    report = [
        "=" * 60,
        "PERFORMANCE TEST REPORT",
        "=" * 60,
        "",
        "Query Processing Performance:",
        f"  P95 Latency: {results.get('p95', 0):.2f}ms",
        f"  P99 Latency: {results.get('p99', 0):.2f}ms",
        f"  Mean Latency: {results.get('mean', 0):.2f}ms",
        f"  Throughput: {results.get('throughput', 0):.2f} queries/sec",
        "",
        "Performance Targets:",
        "  ✓ P95 < 200ms" if results.get('p95', 999) < 200 else "  ✗ P95 < 200ms",
        "  ✓ P99 < 500ms" if results.get('p99', 999) < 500 else "  ✗ P99 < 500ms",
        "  ✓ Throughput > 100 q/s" if results.get('throughput', 0) > 100 else "  ✗ Throughput > 100 q/s",
        "",
        "=" * 60
    ]
    
    return "\n".join(report)


if __name__ == "__main__":
    # Run performance tests with detailed output
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "performance",
        "--benchmark-only"
    ])