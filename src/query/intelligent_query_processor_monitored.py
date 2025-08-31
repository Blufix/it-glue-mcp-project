"""Enhanced intelligent query processor with performance monitoring."""

import uuid
import asyncio
from typing import Any, Dict, List, Optional

from src.query.intelligent_query_processor import IntelligentQueryProcessor, QueryIntent
from src.monitoring.query_performance import (
    QueryPerformanceMonitor,
    QueryStage,
    monitor_performance
)
from src.query.fuzzy_enhancer import QueryFuzzyEnhancer
from src.nlp.entity_extractor import EntityExtractor
from src.nlp.intent_classifier import IntentClassifier
from src.context.session_manager import SessionManager
from src.ranking.result_ranker import ResultRanker
from src.cache.redis_cache import RedisCache


class MonitoredIntelligentQueryProcessor(IntelligentQueryProcessor):
    """Intelligent query processor with integrated performance monitoring."""
    
    def __init__(
        self,
        neo4j_driver=None,
        cache_manager=None,
        enable_monitoring: bool = True,
        slow_query_threshold_ms: float = 500
    ):
        """
        Initialize monitored query processor.
        
        Args:
            neo4j_driver: Neo4j driver instance
            cache_manager: Cache manager instance
            enable_monitoring: Enable performance monitoring
            slow_query_threshold_ms: Threshold for slow query detection
        """
        super().__init__(neo4j_driver, cache_manager)
        
        # Initialize components
        self.fuzzy_enhancer = QueryFuzzyEnhancer()
        self.entity_extractor = EntityExtractor()
        self.intent_classifier = IntentClassifier()
        self.session_manager = SessionManager()
        self.result_ranker = ResultRanker()
        self.redis_cache = RedisCache() if not cache_manager else cache_manager
        
        # Initialize performance monitor
        self.performance_monitor = QueryPerformanceMonitor(
            slow_query_threshold_ms=slow_query_threshold_ms,
            enable_tracing=enable_monitoring,
            log_slow_queries=True
        ) if enable_monitoring else None
    
    async def process_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a query with full performance monitoring.
        
        Args:
            query: User query
            context: Query context
            session_id: Session ID for context tracking
            
        Returns:
            Query results with metadata
        """
        # Generate query ID
        query_id = str(uuid.uuid4())
        
        if not self.performance_monitor:
            # Fall back to parent implementation without monitoring
            return await super().process_query(query, context)
        
        # Start monitoring
        async with self.performance_monitor.track_async_query(query_id, query) as metrics:
            
            # Stage 1: Cache lookup
            async with self.performance_monitor.track_async_stage(query_id, QueryStage.CACHE_LOOKUP):
                cache_key = self._generate_cache_key(query, context)
                cached_result = await self.redis_cache.get(cache_key)
                
                if cached_result:
                    self.performance_monitor.record_cache_hit(query_id, "query")
                    metrics.cache_hit = True
                    return cached_result
                else:
                    self.performance_monitor.record_cache_miss(query_id, "query")
            
            # Stage 2: Query enhancement with fuzzy matching
            async with self.performance_monitor.track_async_stage(query_id, QueryStage.ENHANCEMENT):
                enhanced = await self._enhance_query_async(query_id, query, context)
            
            # Stage 3: Entity extraction
            async with self.performance_monitor.track_async_stage(query_id, QueryStage.ENTITY_EXTRACTION):
                entities = await self._extract_entities_async(enhanced.corrected_query)
            
            # Stage 4: Intent classification
            async with self.performance_monitor.track_async_stage(query_id, QueryStage.INTENT_CLASSIFICATION):
                intent = await self._classify_intent_async(enhanced.corrected_query)
            
            # Stage 5: Template matching
            async with self.performance_monitor.track_async_stage(query_id, QueryStage.TEMPLATE_MATCHING):
                templates = await self._match_templates_async(enhanced.corrected_query, intent)
            
            # Stage 6: Database query
            async with self.performance_monitor.track_async_stage(query_id, QueryStage.DATABASE_QUERY):
                results = await self._execute_queries_async(
                    query_id,
                    enhanced.corrected_query,
                    entities,
                    intent,
                    templates
                )
            
            # Stage 7: Result ranking
            async with self.performance_monitor.track_async_stage(query_id, QueryStage.RESULT_RANKING):
                ranked_results = await self.result_ranker.rank_results(
                    results,
                    enhanced.corrected_query
                )
            
            # Record result count
            self.performance_monitor.record_result_count(query_id, len(ranked_results))
            
            # Stage 8: Response formatting
            async with self.performance_monitor.track_async_stage(query_id, QueryStage.RESPONSE_FORMATTING):
                response = self._format_response(
                    query_id,
                    query,
                    enhanced,
                    entities,
                    intent,
                    ranked_results,
                    templates
                )
            
            # Cache the response
            await self.redis_cache.set(
                cache_key,
                response,
                ttl=self._get_cache_ttl(intent)
            )
            
            # Update session context if provided
            if session_id:
                await self.session_manager.add_query(session_id, query)
                await self.session_manager.update_context(session_id, {
                    "last_intent": intent.primary_intent,
                    "last_entities": entities
                })
            
            return response
    
    async def _enhance_query_async(
        self,
        query_id: str,
        query: str,
        context: Optional[Dict[str, Any]]
    ):
        """Enhance query with fuzzy matching (async wrapper)."""
        # Run in executor for sync code
        loop = asyncio.get_event_loop()
        enhanced = await loop.run_in_executor(
            None,
            self.fuzzy_enhancer.enhance_query,
            query,
            None,  # candidates
            context
        )
        
        # Record fuzzy corrections
        for token in enhanced.enhanced_tokens:
            if token.corrections:
                for correction in token.corrections:
                    self.performance_monitor.record_fuzzy_correction(
                        query_id,
                        "typo",
                        token.original,
                        correction,
                        token.confidence
                    )
        
        return enhanced
    
    async def _extract_entities_async(self, query: str) -> Dict[str, List[str]]:
        """Extract entities from query (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.entity_extractor.extract,
            query
        )
    
    async def _classify_intent_async(self, query: str):
        """Classify query intent (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.intent_classifier.classify,
            query
        )
    
    async def _match_templates_async(self, query: str, intent):
        """Match query templates (async wrapper)."""
        # Import here to avoid circular dependency
        from src.query.query_templates import QueryTemplateManager
        
        manager = QueryTemplateManager()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            manager.find_matching_templates,
            query
        )
    
    async def _execute_queries_async(
        self,
        query_id: str,
        query: str,
        entities: Dict[str, List[str]],
        intent,
        templates: List
    ) -> List[Dict[str, Any]]:
        """Execute database queries."""
        results = []
        
        # Execute template queries if matched
        if templates:
            for template in templates[:2]:  # Limit to top 2 templates
                template_results = await self._execute_template_queries(
                    template,
                    entities
                )
                results.extend(template_results)
        
        # Execute Neo4j query if available
        if self.neo4j_driver:
            neo4j_results = await self._execute_neo4j_query_monitored(
                query_id,
                query,
                entities,
                intent
            )
            results.extend(neo4j_results)
        
        # Deduplicate results
        seen = set()
        unique_results = []
        for result in results:
            result_id = result.get("id") or result.get("name")
            if result_id and result_id not in seen:
                seen.add(result_id)
                unique_results.append(result)
        
        return unique_results
    
    async def _execute_neo4j_query_monitored(
        self,
        query_id: str,
        query: str,
        entities: Dict[str, List[str]],
        intent
    ) -> List[Dict[str, Any]]:
        """Execute Neo4j query with monitoring."""
        if not self.neo4j_driver:
            return []
        
        # Build Neo4j query
        neo4j_query = self.neo4j_builder.build(
            intent.primary_intent,
            intent.entities,
            entities.get("organizations", [])
        )
        
        # Execute query
        async with self.neo4j_driver.session() as session:
            try:
                result = await session.run(
                    neo4j_query.query,
                    **neo4j_query.parameters
                )
                records = await result.data()
                return records
            except Exception as e:
                # Log error but don't fail
                if self.performance_monitor:
                    metrics = self.performance_monitor.active_queries_map.get(query_id)
                    if metrics:
                        metrics.metadata["neo4j_error"] = str(e)
                return []
    
    async def _execute_template_queries(
        self,
        template,
        entities: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """Execute template queries."""
        results = []
        
        # Build parameters from entities
        params = {}
        if entities.get("organizations"):
            params["organization"] = entities["organizations"][0]
        if entities.get("servers"):
            params["server_name"] = entities["servers"][0]
        if entities.get("users"):
            params["user_name"] = entities["users"][0]
        
        # Expand template
        try:
            expanded = template.expand(params)
            
            # Execute sub-queries (mock for now)
            for sub_query in expanded.sub_queries[:3]:  # Limit sub-queries
                # In production, execute actual queries
                # For now, return mock results
                results.append({
                    "query": sub_query.query,
                    "purpose": sub_query.purpose,
                    "priority": sub_query.priority.value
                })
        except ValueError:
            # Missing required parameters
            pass
        
        return results
    
    def _format_response(
        self,
        query_id: str,
        original_query: str,
        enhanced,
        entities: Dict[str, List[str]],
        intent,
        results: List[Dict[str, Any]],
        templates: List
    ) -> Dict[str, Any]:
        """Format the final response."""
        response = {
            "query_id": query_id,
            "original_query": original_query,
            "corrected_query": enhanced.corrected_query,
            "confidence": enhanced.overall_confidence,
            "intent": {
                "primary": intent.primary_intent,
                "confidence": intent.confidence,
                "secondary_intents": intent.secondary_intents
            },
            "entities": entities,
            "corrections": [
                {
                    "original": token.original,
                    "corrected": token.corrections[0] if token.corrections else token.original,
                    "confidence": token.confidence
                }
                for token in enhanced.enhanced_tokens
                if token.corrections
            ],
            "results": results,
            "result_count": len(results),
            "templates_matched": [t.id for t in templates] if templates else [],
            "suggested_queries": self._generate_follow_up_queries(intent, results)
        }
        
        # Add performance metrics if available
        if self.performance_monitor:
            metrics = self.performance_monitor.active_queries_map.get(query_id)
            if metrics:
                response["performance"] = {
                    "total_duration_ms": metrics.total_duration_ms,
                    "stages": metrics.stage_durations,
                    "cache_hit": metrics.cache_hit,
                    "fuzzy_corrections": metrics.fuzzy_corrections
                }
        
        return response
    
    def _get_cache_ttl(self, intent) -> int:
        """Get cache TTL based on intent."""
        # Critical queries - short TTL
        if intent.primary_intent in ["troubleshooting", "emergency"]:
            return 60  # 1 minute
        
        # Investigation queries - medium TTL
        if intent.primary_intent in ["investigation", "recent_changes"]:
            return 300  # 5 minutes
        
        # Documentation/audit queries - long TTL
        if intent.primary_intent in ["documentation", "audit", "compliance"]:
            return 86400  # 24 hours
        
        # Default
        return 600  # 10 minutes
    
    def _generate_cache_key(self, query: str, context: Optional[Dict[str, Any]]) -> str:
        """Generate cache key for query."""
        import hashlib
        import json
        
        key_data = {
            "query": query.lower().strip(),
            "context": context or {}
        }
        
        key_json = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_json.encode()).hexdigest()
        
        return f"query:{key_hash}"
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.performance_monitor:
            return {}
        
        return self.performance_monitor.get_performance_summary()
    
    def get_active_queries(self) -> List[Dict[str, Any]]:
        """Get currently active queries."""
        if not self.performance_monitor:
            return []
        
        return self.performance_monitor.get_active_queries()