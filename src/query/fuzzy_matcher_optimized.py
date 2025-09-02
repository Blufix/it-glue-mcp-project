"""Optimized fuzzy matching system with performance enhancements."""

import asyncio
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

import jellyfish

# Try to import RapidFuzz for better performance
try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logging.warning("RapidFuzz not available, using fallback algorithms")

logger = logging.getLogger(__name__)


@dataclass
class OptimizedMatchResult:
    """Result of an optimized fuzzy match operation."""
    original: str
    matched: str
    score: float
    match_type: str
    confidence: float
    entity_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    match_time_ms: float = 0
    algorithm_used: str = "default"


class OptimizedFuzzyMatcher:
    """
    High-performance fuzzy matching for IT Glue entities.

    Performance optimizations:
    - Early termination for exact matches
    - RapidFuzz library for 10x faster fuzzy matching
    - Parallel processing for large candidate sets
    - Optimized threshold checking order
    - Caching of normalized strings
    - Pre-compiled regex patterns
    """

    def __init__(
        self,
        cache_manager=None,
        use_parallel: bool = True,
        parallel_threshold: int = 100,
        max_workers: int = 4
    ):
        """
        Initialize optimized fuzzy matcher.

        Args:
            cache_manager: Cache manager for results
            use_parallel: Enable parallel processing for large sets
            parallel_threshold: Minimum candidates for parallel processing
            max_workers: Maximum worker threads
        """
        self.cache_manager = cache_manager
        self.use_parallel = use_parallel
        self.parallel_threshold = parallel_threshold
        self.max_workers = max_workers

        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=max_workers) if use_parallel else None

        # Pre-compiled patterns for better performance
        self.normalization_pattern = re.compile(r'[^\w\s&-]')
        self.whitespace_pattern = re.compile(r'\s+')

        # Caches for performance
        self.normalization_cache = {}
        self.phonetic_cache = {}
        self.acronym_cache = {}

        # Load dictionaries
        self._load_dictionaries()

        # Performance metrics
        self.total_matches = 0
        self.exact_match_count = 0
        self.early_terminations = 0
        self.parallel_executions = 0

    def _load_dictionaries(self):
        """Load IT terms dictionary with optimized structures."""
        dict_path = Path(__file__).parent / "dictionaries" / "it_terms.json"

        if dict_path.exists():
            try:
                with open(dict_path) as f:
                    data = json.load(f)

                    # Flatten all categories into single lookup dict
                    self.corrections_dict = {}

                    for category in ['vendor_names', 'technologies', 'protocols']:
                        if category in data:
                            self.corrections_dict.update(data[category])

                    # Pre-compute lowercase versions for faster lookup
                    self.corrections_lower = {
                        k.lower(): v.lower()
                        for k, v in self.corrections_dict.items()
                    }

                    # Build reverse index for faster lookups
                    self.reverse_corrections = {}
                    for wrong, correct in self.corrections_lower.items():
                        if correct not in self.reverse_corrections:
                            self.reverse_corrections[correct] = []
                        self.reverse_corrections[correct].append(wrong)

                    logger.info(f"Loaded {len(self.corrections_dict)} corrections")

            except Exception as e:
                logger.error(f"Failed to load dictionary: {e}")
                self.corrections_dict = {}
                self.corrections_lower = {}
                self.reverse_corrections = {}
        else:
            self.corrections_dict = {}
            self.corrections_lower = {}
            self.reverse_corrections = {}

    def _normalize_string_fast(self, text: str) -> str:
        """
        Fast string normalization with caching.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        if not text:
            return ""

        # Check cache first
        if text in self.normalization_cache:
            return self.normalization_cache[text]

        # Fast normalization
        normalized = text.lower().strip()

        # Apply corrections if found (single pass)
        words = normalized.split()
        corrected_words = []

        for word in words:
            # Check for correction
            corrected = self.corrections_lower.get(word, word)
            corrected_words.append(corrected)

        normalized = ' '.join(corrected_words)

        # Remove special characters (pre-compiled pattern)
        normalized = self.normalization_pattern.sub('', normalized)

        # Normalize whitespace (pre-compiled pattern)
        normalized = self.whitespace_pattern.sub(' ', normalized)

        # Cache result
        if len(self.normalization_cache) < 10000:  # Limit cache size
            self.normalization_cache[text] = normalized

        return normalized

    def _exact_match_optimized(self, input_str: str, candidate: str) -> float:
        """
        Optimized exact match with early termination.

        Args:
            input_str: Normalized input string
            candidate: Normalized candidate string

        Returns:
            Match score (1.0 for exact, 0.0 for no match)
        """
        if input_str == candidate:
            self.exact_match_count += 1
            return 1.0
        return 0.0

    def _fuzzy_match_optimized(self, input_str: str, candidate: str) -> float:
        """
        Optimized fuzzy matching using RapidFuzz if available.

        Args:
            input_str: Normalized input string
            candidate: Normalized candidate string

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if RAPIDFUZZ_AVAILABLE:
            # RapidFuzz is 10x faster than difflib
            return fuzz.ratio(input_str, candidate) / 100.0
        else:
            # Fallback to difflib
            return SequenceMatcher(None, input_str, candidate).ratio()

    def _phonetic_match_cached(self, input_str: str, candidate: str) -> float:
        """
        Cached phonetic matching for performance.

        Args:
            input_str: Normalized input string
            candidate: Normalized candidate string

        Returns:
            Phonetic similarity score
        """
        # Generate cache key
        cache_key = f"{input_str}:{candidate}"

        if cache_key in self.phonetic_cache:
            return self.phonetic_cache[cache_key]

        score = 0.0

        try:
            # Use Double Metaphone (more accurate than Soundex)
            input_meta = jellyfish.metaphone(input_str)
            candidate_meta = jellyfish.metaphone(candidate)

            if input_meta and candidate_meta:
                if input_meta == candidate_meta:
                    score = 0.9
                else:
                    # Partial match
                    score = SequenceMatcher(None, input_meta, candidate_meta).ratio() * 0.7
        except:
            pass

        # Cache result
        if len(self.phonetic_cache) < 5000:
            self.phonetic_cache[cache_key] = score

        return score

    def _match_single_candidate(
        self,
        input_normalized: str,
        candidate: dict[str, str],
        threshold: float
    ) -> Optional[OptimizedMatchResult]:
        """
        Match against a single candidate with optimized strategy.

        Args:
            input_normalized: Normalized input string
            candidate: Candidate dictionary
            threshold: Minimum score threshold

        Returns:
            Match result or None if below threshold
        """
        candidate_name = candidate.get('name', '')
        candidate_normalized = self._normalize_string_fast(candidate_name)

        # Early termination - check exact match first (fastest)
        exact_score = self._exact_match_optimized(input_normalized, candidate_normalized)
        if exact_score == 1.0:
            self.early_terminations += 1
            return OptimizedMatchResult(
                original=input_normalized,
                matched=candidate_name,
                score=1.0,
                match_type='exact',
                confidence=1.0,
                entity_id=candidate.get('id'),
                algorithm_used='exact'
            )

        # Quick length check - if lengths are too different, skip
        len_ratio = len(input_normalized) / len(candidate_normalized) if candidate_normalized else 0
        if len_ratio < 0.5 or len_ratio > 2.0:
            return None

        # Check fuzzy match (second fastest with RapidFuzz)
        fuzzy_score = self._fuzzy_match_optimized(input_normalized, candidate_normalized)

        # Early termination if fuzzy score is too low
        if fuzzy_score < threshold * 0.8:
            return None

        # Only compute expensive phonetic match if fuzzy is promising
        phonetic_score = 0.0
        if fuzzy_score > 0.6:
            phonetic_score = self._phonetic_match_cached(input_normalized, candidate_normalized)

        # Combine scores with weights
        final_score = max(fuzzy_score * 0.7 + phonetic_score * 0.3, fuzzy_score)

        if final_score >= threshold:
            return OptimizedMatchResult(
                original=input_normalized,
                matched=candidate_name,
                score=final_score,
                match_type='fuzzy' if fuzzy_score > phonetic_score else 'phonetic',
                confidence=final_score * 0.9,
                entity_id=candidate.get('id'),
                algorithm_used='rapidfuzz' if RAPIDFUZZ_AVAILABLE else 'difflib'
            )

        return None

    def match_organization_optimized(
        self,
        input_name: str,
        candidates: list[dict[str, str]],
        threshold: float = 0.7,
        top_n: int = 5
    ) -> list[OptimizedMatchResult]:
        """
        Optimized organization matching with parallel processing.

        Args:
            input_name: Input organization name
            candidates: List of candidate organizations
            threshold: Minimum similarity threshold
            top_n: Number of top matches to return

        Returns:
            Top N match results sorted by score
        """
        start_time = time.perf_counter()
        self.total_matches += 1

        # Normalize input once
        input_normalized = self._normalize_string_fast(input_name)

        # Use RapidFuzz process extraction if available and suitable
        if RAPIDFUZZ_AVAILABLE and len(candidates) > 20:
            # Extract candidate names
            candidate_names = [c.get('name', '') for c in candidates]

            # Use RapidFuzz's optimized extraction
            rapidfuzz_matches = process.extract(
                input_normalized,
                candidate_names,
                scorer=fuzz.WRatio,
                limit=top_n * 2,  # Get more to filter by threshold
                score_cutoff=threshold * 100
            )

            # Convert to our result format
            results = []
            for match_text, score, idx in rapidfuzz_matches:
                if score / 100.0 >= threshold:
                    results.append(OptimizedMatchResult(
                        original=input_name,
                        matched=candidates[idx]['name'],
                        score=score / 100.0,
                        match_type='fuzzy',
                        confidence=score / 100.0 * 0.9,
                        entity_id=candidates[idx].get('id'),
                        match_time_ms=(time.perf_counter() - start_time) * 1000,
                        algorithm_used='rapidfuzz_batch'
                    ))

            return results[:top_n]

        # Parallel processing for large candidate sets
        if self.use_parallel and len(candidates) > self.parallel_threshold:
            self.parallel_executions += 1

            # Process candidates in parallel
            futures = []
            for candidate in candidates:
                future = self.executor.submit(
                    self._match_single_candidate,
                    input_normalized,
                    candidate,
                    threshold
                )
                futures.append(future)

            # Collect results
            results = []
            for future in futures:
                result = future.result()
                if result:
                    result.match_time_ms = (time.perf_counter() - start_time) * 1000
                    results.append(result)
        else:
            # Sequential processing for small sets
            results = []
            for candidate in candidates:
                result = self._match_single_candidate(
                    input_normalized,
                    candidate,
                    threshold
                )
                if result:
                    result.match_time_ms = (time.perf_counter() - start_time) * 1000
                    results.append(result)

                    # Early termination if we found exact match
                    if result.score == 1.0:
                        break

        # Sort by score and confidence
        results.sort(key=lambda x: (x.score, x.confidence), reverse=True)

        # Log performance if slow
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        if elapsed_ms > 500:
            logger.warning(
                f"Slow fuzzy match: {elapsed_ms:.2f}ms for {len(candidates)} candidates"
            )

        return results[:top_n]

    async def match_organization_async(
        self,
        input_name: str,
        candidates: list[dict[str, str]],
        threshold: float = 0.7,
        top_n: int = 5
    ) -> list[OptimizedMatchResult]:
        """
        Async version of optimized matching.

        Args:
            input_name: Input organization name
            candidates: List of candidate organizations
            threshold: Minimum similarity threshold
            top_n: Number of top matches to return

        Returns:
            Top N match results
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.match_organization_optimized,
            input_name,
            candidates,
            threshold,
            top_n
        )

    def get_performance_stats(self) -> dict[str, Any]:
        """
        Get performance statistics.

        Returns:
            Dictionary of performance metrics
        """
        return {
            'total_matches': self.total_matches,
            'exact_matches': self.exact_match_count,
            'exact_match_rate': self.exact_match_count / self.total_matches if self.total_matches > 0 else 0,
            'early_terminations': self.early_terminations,
            'parallel_executions': self.parallel_executions,
            'normalization_cache_size': len(self.normalization_cache),
            'phonetic_cache_size': len(self.phonetic_cache),
            'rapidfuzz_available': RAPIDFUZZ_AVAILABLE,
            'parallel_enabled': self.use_parallel,
            'max_workers': self.max_workers
        }

    def clear_caches(self):
        """Clear all internal caches."""
        self.normalization_cache.clear()
        self.phonetic_cache.clear()
        self.acronym_cache.clear()
        logger.info("Cleared all fuzzy matcher caches")

    def __del__(self):
        """Cleanup thread pool on deletion."""
        if self.executor:
            self.executor.shutdown(wait=False)


# Performance benchmark function
async def benchmark_fuzzy_matcher(
    matcher: OptimizedFuzzyMatcher,
    test_queries: list[str],
    candidates: list[dict[str, str]]
) -> dict[str, Any]:
    """
    Benchmark fuzzy matcher performance.

    Args:
        matcher: Fuzzy matcher instance
        test_queries: List of test queries
        candidates: List of candidate organizations

    Returns:
        Benchmark results
    """
    import statistics

    times = []
    results_counts = []

    for query in test_queries:
        start = time.perf_counter()
        results = matcher.match_organization_optimized(query, candidates)
        elapsed = (time.perf_counter() - start) * 1000

        times.append(elapsed)
        results_counts.append(len(results))

    return {
        'queries_tested': len(test_queries),
        'candidates_count': len(candidates),
        'avg_time_ms': statistics.mean(times),
        'median_time_ms': statistics.median(times),
        'p95_time_ms': statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
        'p99_time_ms': statistics.quantiles(times, n=100)[98] if len(times) >= 100 else max(times),
        'min_time_ms': min(times),
        'max_time_ms': max(times),
        'avg_results': statistics.mean(results_counts),
        'performance_stats': matcher.get_performance_stats()
    }


# Factory function to create optimized matcher
def create_optimized_matcher(
    redis_url: Optional[str] = None,
    enable_parallel: bool = True
) -> OptimizedFuzzyMatcher:
    """
    Create optimized fuzzy matcher with optional Redis caching.

    Args:
        redis_url: Optional Redis URL for caching
        enable_parallel: Enable parallel processing

    Returns:
        Configured OptimizedFuzzyMatcher instance
    """
    cache_manager = None

    if redis_url:
        from src.cache.redis_fuzzy_cache import RedisFuzzyCache
        cache_manager = RedisFuzzyCache(redis_url=redis_url)

    return OptimizedFuzzyMatcher(
        cache_manager=cache_manager,
        use_parallel=enable_parallel,
        parallel_threshold=50,  # Use parallel for 50+ candidates
        max_workers=4
    )
