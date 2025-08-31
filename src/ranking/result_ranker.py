"""Result ranking and relevance scoring system for query results."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


@dataclass
class RankingFactors:
    """Factors used for ranking calculation."""
    fuzzy_score: float = 0.0  # Fuzzy match score (0-1)
    entity_relevance: float = 0.0  # Entity match relevance (0-1)
    recency_score: float = 0.0  # How recent the item is (0-1)
    popularity_score: float = 0.0  # Item access frequency (0-1)
    user_context_score: float = 0.0  # User-specific relevance (0-1)
    type_priority: float = 0.0  # Resource type priority (0-1)
    completeness_score: float = 0.0  # Data completeness (0-1)
    
    def calculate_total(self, weights: Dict[str, float] = None) -> float:
        """Calculate weighted total score."""
        default_weights = {
            'fuzzy_score': 0.25,
            'entity_relevance': 0.20,
            'recency_score': 0.15,
            'popularity_score': 0.10,
            'user_context_score': 0.15,
            'type_priority': 0.10,
            'completeness_score': 0.05
        }
        
        weights = weights or default_weights
        
        total = (
            self.fuzzy_score * weights.get('fuzzy_score', 0.25) +
            self.entity_relevance * weights.get('entity_relevance', 0.20) +
            self.recency_score * weights.get('recency_score', 0.15) +
            self.popularity_score * weights.get('popularity_score', 0.10) +
            self.user_context_score * weights.get('user_context_score', 0.15) +
            self.type_priority * weights.get('type_priority', 0.10) +
            self.completeness_score * weights.get('completeness_score', 0.05)
        )
        
        return min(1.0, max(0.0, total))


@dataclass
class ScoredResult:
    """A result with its ranking score and factors."""
    data: Dict[str, Any]
    score: float
    factors: RankingFactors
    deduplication_key: str
    source_type: str  # 'postgresql', 'neo4j', 'cache', etc.
    

class ResultRanker:
    """Ranks and deduplicates query results based on multiple factors."""
    
    def __init__(self, user_profile_manager=None, popularity_tracker=None):
        """Initialize result ranker.
        
        Args:
            user_profile_manager: Optional manager for user context scoring
            popularity_tracker: Optional tracker for item popularity
        """
        self.user_profile_manager = user_profile_manager
        self.popularity_tracker = popularity_tracker
        
        # Type priorities for different resource types
        self.type_priorities = {
            'password': 0.95,  # Highest priority for critical data
            'configuration': 0.85,
            'organization': 0.80,
            'flexible_asset': 0.75,
            'document': 0.70,
            'contact': 0.65,
            'location': 0.60,
            'other': 0.50
        }
        
        # Recency decay factors
        self.recency_thresholds = [
            (timedelta(hours=1), 1.0),    # Last hour: full score
            (timedelta(days=1), 0.9),     # Last day: 90%
            (timedelta(days=7), 0.75),    # Last week: 75%
            (timedelta(days=30), 0.6),    # Last month: 60%
            (timedelta(days=90), 0.4),    # Last quarter: 40%
            (timedelta(days=365), 0.2),   # Last year: 20%
        ]
        
        self.deduplication_cache = {}
        
    def rank_results(
        self,
        results: List[Dict[str, Any]],
        query_context: Dict[str, Any],
        user_id: Optional[str] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> List[ScoredResult]:
        """Rank results based on multiple factors.
        
        Args:
            results: List of raw results to rank
            query_context: Context about the query (entities, intent, etc.)
            user_id: Optional user ID for personalization
            weights: Optional custom weights for ranking factors
            
        Returns:
            List of scored and ranked results (highest score first)
        """
        scored_results = []
        seen_keys = set()
        
        for result in results:
            # Generate deduplication key
            dedup_key = self._generate_deduplication_key(result)
            
            # Skip duplicates
            if dedup_key in seen_keys:
                logger.debug(f"Skipping duplicate result: {dedup_key}")
                continue
            
            seen_keys.add(dedup_key)
            
            # Calculate ranking factors
            factors = self._calculate_factors(result, query_context, user_id)
            
            # Calculate total score
            total_score = factors.calculate_total(weights)
            
            # Determine source type
            source_type = result.get('_source', 'unknown')
            
            scored_result = ScoredResult(
                data=result,
                score=total_score,
                factors=factors,
                deduplication_key=dedup_key,
                source_type=source_type
            )
            
            scored_results.append(scored_result)
        
        # Sort by score (highest first)
        scored_results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply result diversification
        diversified_results = self._diversify_results(scored_results)
        
        return diversified_results
    
    def _calculate_factors(
        self,
        result: Dict[str, Any],
        query_context: Dict[str, Any],
        user_id: Optional[str]
    ) -> RankingFactors:
        """Calculate all ranking factors for a result."""
        factors = RankingFactors()
        
        # Fuzzy match score
        factors.fuzzy_score = self._calculate_fuzzy_score(result, query_context)
        
        # Entity relevance
        factors.entity_relevance = self._calculate_entity_relevance(result, query_context)
        
        # Recency score
        factors.recency_score = self._calculate_recency_score(result)
        
        # Popularity score
        factors.popularity_score = self._calculate_popularity_score(result)
        
        # User context score
        if user_id and self.user_profile_manager:
            factors.user_context_score = self._calculate_user_context_score(
                result, user_id, query_context
            )
        
        # Type priority
        factors.type_priority = self._calculate_type_priority(result)
        
        # Completeness score
        factors.completeness_score = self._calculate_completeness_score(result)
        
        return factors
    
    def _calculate_fuzzy_score(
        self,
        result: Dict[str, Any],
        query_context: Dict[str, Any]
    ) -> float:
        """Calculate fuzzy match score from result metadata."""
        # Check if fuzzy score is already provided
        if '_fuzzy_score' in result:
            return result['_fuzzy_score']
        
        # Check for text similarity score
        if 'similarity_score' in result:
            return result['similarity_score']
        
        # Check query context for match scores
        query_text = query_context.get('query_text', '').lower()
        result_name = result.get('name', '').lower()
        
        if query_text and result_name:
            # Simple substring matching as fallback
            if query_text in result_name:
                return 0.9
            elif result_name in query_text:
                return 0.8
            
            # Partial word matching
            query_words = set(query_text.split())
            result_words = set(result_name.split())
            common_words = query_words & result_words
            
            if common_words:
                return len(common_words) / max(len(query_words), len(result_words))
        
        return 0.5  # Default neutral score
    
    def _calculate_entity_relevance(
        self,
        result: Dict[str, Any],
        query_context: Dict[str, Any]
    ) -> float:
        """Calculate how relevant the result is to extracted entities."""
        score = 0.0
        entity_count = 0
        
        query_entities = query_context.get('entities', {})
        
        if not query_entities:
            return 0.5  # Neutral score if no entities
        
        # Check organization match
        if 'organization' in query_entities:
            entity_count += 1
            result_org = result.get('organization_name', '').lower()
            for org in query_entities['organization']:
                if org.lower() in result_org or result_org in org.lower():
                    score += 1.0
                    break
        
        # Check IP address match
        if 'ip_address' in query_entities:
            entity_count += 1
            result_ips = result.get('ip_addresses', [])
            if isinstance(result_ips, str):
                result_ips = [result_ips]
            
            for ip in query_entities['ip_address']:
                if ip in result_ips or ip in str(result):
                    score += 1.0
                    break
        
        # Check server/system name match
        if 'server' in query_entities:
            entity_count += 1
            result_name = result.get('name', '').lower()
            result_hostname = result.get('hostname', '').lower()
            
            for server in query_entities['server']:
                server_lower = server.lower()
                if (server_lower in result_name or 
                    server_lower in result_hostname or
                    result_name in server_lower):
                    score += 1.0
                    break
        
        # Check date relevance
        if 'date' in query_entities:
            entity_count += 1
            result_date = result.get('updated_at') or result.get('created_at')
            if result_date:
                # Simple date proximity check
                score += 0.5  # Partial credit for having date info
        
        if entity_count > 0:
            return score / entity_count
        
        return 0.5  # Neutral score
    
    def _calculate_recency_score(self, result: Dict[str, Any]) -> float:
        """Calculate score based on how recent the result is."""
        # Try different date fields
        date_fields = ['updated_at', 'modified_at', 'created_at', 'timestamp']
        result_date = None
        
        for field in date_fields:
            if field in result:
                try:
                    if isinstance(result[field], str):
                        result_date = datetime.fromisoformat(
                            result[field].replace('Z', '+00:00')
                        )
                    elif isinstance(result[field], datetime):
                        result_date = result[field]
                    break
                except (ValueError, TypeError):
                    continue
        
        if not result_date:
            return 0.5  # Neutral score if no date
        
        # Calculate age
        now = datetime.now(result_date.tzinfo) if result_date.tzinfo else datetime.now()
        age = now - result_date
        
        # Apply decay based on thresholds
        for threshold, score in self.recency_thresholds:
            if age <= threshold:
                return score
        
        return 0.1  # Very old items get minimal score
    
    def _calculate_popularity_score(self, result: Dict[str, Any]) -> float:
        """Calculate score based on item popularity/access frequency."""
        if self.popularity_tracker:
            item_id = result.get('id')
            if item_id:
                popularity = self.popularity_tracker.get_popularity(item_id)
                # Normalize popularity to 0-1 range
                return min(1.0, popularity / 100.0)
        
        # Check for built-in popularity indicators
        if 'access_count' in result:
            # Logarithmic scaling for access counts
            count = result['access_count']
            if count > 0:
                return min(1.0, math.log10(count + 1) / 3)  # Assuming 1000 is very popular
        
        if 'importance' in result:
            importance_map = {
                'critical': 1.0,
                'high': 0.8,
                'medium': 0.5,
                'low': 0.3
            }
            return importance_map.get(result['importance'], 0.5)
        
        return 0.5  # Neutral score
    
    def _calculate_user_context_score(
        self,
        result: Dict[str, Any],
        user_id: str,
        query_context: Dict[str, Any]
    ) -> float:
        """Calculate score based on user's context and history."""
        if not self.user_profile_manager:
            return 0.5
        
        profile = self.user_profile_manager.get_profile(user_id)
        if not profile:
            return 0.5
        
        score = 0.0
        factors = 0
        
        # Check if result matches user's typical organizations
        if 'typical_organizations' in profile:
            factors += 1
            result_org = result.get('organization_name', '')
            if result_org in profile['typical_organizations']:
                score += 1.0
        
        # Check if result type matches user's typical query types
        if 'typical_query_types' in profile:
            factors += 1
            result_type = result.get('_type', result.get('type', ''))
            user_types = profile['typical_query_types']
            if result_type in user_types:
                # Weight by frequency
                type_freq = user_types[result_type]
                total_freq = sum(user_types.values())
                score += type_freq / total_freq if total_freq > 0 else 0.5
        
        # Check recent access patterns
        if 'recent_items' in profile:
            factors += 1
            item_id = result.get('id')
            if item_id in profile['recent_items']:
                score += 0.8  # High score for recently accessed items
        
        if factors > 0:
            return score / factors
        
        return 0.5
    
    def _calculate_type_priority(self, result: Dict[str, Any]) -> float:
        """Calculate priority score based on resource type."""
        result_type = result.get('_type', result.get('type', 'other')).lower()
        
        # Direct type match
        if result_type in self.type_priorities:
            return self.type_priorities[result_type]
        
        # Check for partial matches
        for type_key, priority in self.type_priorities.items():
            if type_key in result_type or result_type in type_key:
                return priority
        
        return self.type_priorities['other']
    
    def _calculate_completeness_score(self, result: Dict[str, Any]) -> float:
        """Calculate score based on data completeness."""
        important_fields = [
            'name', 'description', 'organization_name',
            'updated_at', 'created_by', 'tags'
        ]
        
        present_fields = 0
        total_fields = len(important_fields)
        
        for field in important_fields:
            if field in result and result[field]:
                # Check if field has meaningful content
                value = result[field]
                if isinstance(value, str) and len(value.strip()) > 0:
                    present_fields += 1
                elif isinstance(value, (list, dict)) and len(value) > 0:
                    present_fields += 1
                elif value is not None:
                    present_fields += 1
        
        return present_fields / total_fields
    
    def _generate_deduplication_key(self, result: Dict[str, Any]) -> str:
        """Generate a unique key for deduplication."""
        # Try to use ID first
        if 'id' in result:
            return f"{result.get('_type', 'unknown')}:{result['id']}"
        
        # Fall back to content-based key
        key_parts = []
        
        # Add type
        key_parts.append(result.get('_type', result.get('type', 'unknown')))
        
        # Add name
        if 'name' in result:
            key_parts.append(result['name'].lower().strip())
        
        # Add organization
        if 'organization_name' in result:
            key_parts.append(result['organization_name'].lower().strip())
        elif 'organization_id' in result:
            key_parts.append(str(result['organization_id']))
        
        # Generate hash for complex objects
        if len(key_parts) < 2:
            # Use hash of entire result for complex deduplication
            result_str = str(sorted(result.items()))
            return hashlib.md5(result_str.encode()).hexdigest()
        
        return ':'.join(key_parts)
    
    def _diversify_results(
        self,
        results: List[ScoredResult],
        max_per_type: int = 3
    ) -> List[ScoredResult]:
        """Diversify results to avoid too many of the same type at the top.
        
        Args:
            results: Sorted list of scored results
            max_per_type: Maximum number of results per type in top positions
            
        Returns:
            Diversified list of results
        """
        if len(results) <= 5:
            return results  # Don't diversify small result sets
        
        diversified = []
        type_counts = defaultdict(int)
        deferred = []
        
        for result in results:
            result_type = result.data.get('_type', result.data.get('type', 'unknown'))
            
            # Check if we've hit the limit for this type
            if type_counts[result_type] >= max_per_type and len(diversified) < 10:
                deferred.append(result)
            else:
                diversified.append(result)
                type_counts[result_type] += 1
        
        # Add deferred results at the end
        diversified.extend(deferred)
        
        return diversified
    
    def merge_multi_source_results(
        self,
        postgresql_results: List[Dict[str, Any]],
        neo4j_results: List[Dict[str, Any]],
        cache_results: List[Dict[str, Any]] = None,
        query_context: Dict[str, Any] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Merge and rank results from multiple sources.
        
        Args:
            postgresql_results: Results from PostgreSQL
            neo4j_results: Results from Neo4j
            cache_results: Optional cached results
            query_context: Query context for ranking
            user_id: Optional user ID for personalization
            
        Returns:
            Merged and ranked results
        """
        all_results = []
        
        # Add source markers
        for result in postgresql_results:
            result['_source'] = 'postgresql'
            all_results.append(result)
        
        for result in neo4j_results:
            result['_source'] = 'neo4j'
            all_results.append(result)
        
        if cache_results:
            for result in cache_results:
                result['_source'] = 'cache'
                # Boost cache results slightly (they were popular enough to cache)
                result['_cache_boost'] = 0.1
                all_results.append(result)
        
        # Rank all results
        scored_results = self.rank_results(
            all_results,
            query_context or {},
            user_id
        )
        
        # Return just the data portion
        return [sr.data for sr in scored_results]
    
    def explain_ranking(
        self,
        result: ScoredResult,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Explain why a result was ranked at its position.
        
        Args:
            result: A scored result
            verbose: Include detailed factor breakdowns
            
        Returns:
            Explanation of ranking factors
        """
        explanation = {
            'total_score': result.score,
            'deduplication_key': result.deduplication_key,
            'source_type': result.source_type
        }
        
        if verbose:
            explanation['factors'] = {
                'fuzzy_score': result.factors.fuzzy_score,
                'entity_relevance': result.factors.entity_relevance,
                'recency_score': result.factors.recency_score,
                'popularity_score': result.factors.popularity_score,
                'user_context_score': result.factors.user_context_score,
                'type_priority': result.factors.type_priority,
                'completeness_score': result.factors.completeness_score
            }
        
        # Add human-readable explanation
        top_factors = []
        if result.factors.fuzzy_score > 0.8:
            top_factors.append("Strong text match")
        if result.factors.entity_relevance > 0.8:
            top_factors.append("High entity relevance")
        if result.factors.recency_score > 0.8:
            top_factors.append("Recently updated")
        if result.factors.user_context_score > 0.8:
            top_factors.append("Matches user context")
        
        explanation['top_factors'] = top_factors
        
        return explanation


class PopularityTracker:
    """Track item popularity for ranking purposes."""
    
    def __init__(self, decay_factor: float = 0.95):
        """Initialize popularity tracker.
        
        Args:
            decay_factor: Factor to decay old accesses (0-1)
        """
        self.access_counts = defaultdict(lambda: {'count': 0, 'last_access': None})
        self.decay_factor = decay_factor
    
    def record_access(self, item_id: str) -> None:
        """Record an access to an item."""
        now = datetime.now()
        item = self.access_counts[item_id]
        
        # Apply time decay to old count
        if item['last_access']:
            days_elapsed = (now - item['last_access']).days
            if days_elapsed > 0:
                item['count'] *= (self.decay_factor ** days_elapsed)
        
        item['count'] += 1
        item['last_access'] = now
    
    def get_popularity(self, item_id: str) -> float:
        """Get popularity score for an item."""
        if item_id not in self.access_counts:
            return 0.0
        
        item = self.access_counts[item_id]
        if not item['last_access']:
            return 0.0
        
        # Apply time decay to get current popularity
        now = datetime.now()
        days_elapsed = (now - item['last_access']).days
        
        if days_elapsed > 0:
            return item['count'] * (self.decay_factor ** days_elapsed)
        
        return item['count']
    
    def get_top_items(self, n: int = 10) -> List[Tuple[str, float]]:
        """Get top N most popular items."""
        items_with_scores = [
            (item_id, self.get_popularity(item_id))
            for item_id in self.access_counts
        ]
        
        items_with_scores.sort(key=lambda x: x[1], reverse=True)
        return items_with_scores[:n]


# Export main classes
__all__ = ['ResultRanker', 'RankingFactors', 'ScoredResult', 'PopularityTracker']