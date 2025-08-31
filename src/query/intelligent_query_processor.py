"""Intelligent query processor combining fuzzy matching, Neo4j, and natural language understanding."""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from src.cache.manager import CacheManager
from src.query.fuzzy_matcher import FuzzyMatcher
from src.query.fuzzy_enhancer import QueryFuzzyEnhancer
from src.query.neo4j_query_builder import Neo4jQueryBuilder
from src.query.parser import QueryParser

logger = logging.getLogger(__name__)


@dataclass
class QueryIntent:
    """Detected query intent with confidence."""
    primary_intent: str
    entities: dict[str, Any]
    confidence: float
    suggested_queries: list[str]
    fuzzy_corrections: dict[str, str]
    secondary_intents: list[str] = None
    
    def __post_init__(self):
        if self.secondary_intents is None:
            self.secondary_intents = []


class IntelligentQueryProcessor:
    """Process natural language queries with fuzzy matching and Neo4j integration."""

    def __init__(
        self,
        neo4j_driver=None,
        cache_manager: Optional[CacheManager] = None,
        enable_fuzzy: bool = True,
        fuzzy_threshold: float = 0.8
    ):
        """Initialize intelligent query processor."""
        self.fuzzy_matcher = FuzzyMatcher() if enable_fuzzy else None
        self.query_enhancer = QueryFuzzyEnhancer() if enable_fuzzy else None
        self.neo4j_builder = Neo4jQueryBuilder(self.fuzzy_matcher)
        self.query_parser = QueryParser()
        self.cache_manager = cache_manager or CacheManager()
        self.neo4j_driver = neo4j_driver
        self.enable_fuzzy = enable_fuzzy
        self.fuzzy_threshold = fuzzy_threshold

        # Query patterns for intent detection
        self.intent_patterns = self._build_intent_patterns()

        # Common query templates for engineers
        self.query_templates = self._build_query_templates()

    def _build_intent_patterns(self) -> list[tuple[re.Pattern, str, dict]]:
        """Build patterns for intent detection."""
        return [
            # Configuration queries
            (re.compile(r'show\s+(?:me\s+)?(?:all\s+)?servers?\s+(?:for|at|in)\s+(.+)', re.I),
             'find_configurations', {'type': 'server'}),

            (re.compile(r'(?:list|show|get)\s+(?:all\s+)?configurations?\s+(?:for|at|in)\s+(.+)', re.I),
             'find_configurations', {}),

            (re.compile(r'(?:find|show|get)\s+windows\s+(?:servers?|machines?|systems?)\s+(?:for|at|in)\s+(.+)', re.I),
             'find_configurations', {'type': 'server', 'os': 'Windows'}),

            # Dependency queries
            (re.compile(r'(?:what|show)\s+(?:depends|relies)\s+on\s+(.+)', re.I),
             'find_dependencies', {}),

            (re.compile(r'(?:show|find|get)\s+dependencies\s+(?:for|of)\s+(.+)', re.I),
             'find_dependencies', {}),

            # Impact analysis
            (re.compile(r'(?:what|show)\s+(?:would|will)\s+(?:be\s+)?(?:affected|impacted)\s+(?:if|when)\s+(.+)\s+(?:fails?|goes?\s+down|stops?)', re.I),
             'impact_analysis', {}),

            (re.compile(r'impact\s+(?:analysis|assessment)\s+(?:for|of)\s+(.+)', re.I),
             'impact_analysis', {}),

            # Password/credential queries
            (re.compile(r'(?:show|get|find)\s+(?:admin\s+)?passwords?\s+(?:for|to)\s+(.+)', re.I),
             'find_passwords', {}),

            (re.compile(r'(?:show|list)\s+(?:old|expired|stale)\s+passwords?\s+(?:for|at|in)\s+(.+)', re.I),
             'credential_audit', {}),

            # Recent changes
            (re.compile(r'(?:show|what|list)\s+(?:recent\s+)?changes?\s+(?:for|to|in)\s+(.+)', re.I),
             'recent_changes', {}),

            (re.compile(r'what\s+(?:was\s+)?changed\s+(?:recently|today|yesterday|this\s+week)\s+(?:for|in|at)\s+(.+)', re.I),
             'recent_changes', {'time_range': 'recent'}),

            # Service mapping
            (re.compile(r'(?:show|map|display)\s+(?:service\s+)?(?:connections?|topology|map)\s+(?:for|of)\s+(.+)', re.I),
             'service_map', {}),

            # Network topology
            (re.compile(r'(?:show|display|map)\s+network\s+(?:topology|map|layout)\s+(?:for|at|in)\s+(.+)', re.I),
             'network_topology', {}),

            # Documentation
            (re.compile(r'(?:show|find|get)\s+(?:docs?|documentation)\s+(?:for|about|on)\s+(.+)', re.I),
             'find_documentation', {}),

            # Generic search
            (re.compile(r'(?:search|find|lookup|query)\s+(.+)', re.I),
             'general_search', {}),
        ]

    def _build_query_templates(self) -> dict[str, dict[str, Any]]:
        """Build common query templates for engineers."""
        return {
            'emergency_server_down': {
                'pattern': 'EMERGENCY: {server} is down',
                'expands_to': [
                    'show dependencies for {server}',
                    'what changed recently for {server}',
                    'show passwords for {server}',
                    'find documentation for {server}'
                ]
            },
            'password_recovery': {
                'pattern': 'need password for {system}',
                'expands_to': [
                    'show admin password for {system}',
                    'show service accounts for {system}',
                    'show related passwords for {system}'
                ]
            },
            'change_investigation': {
                'pattern': 'investigate changes for {system}',
                'expands_to': [
                    'show recent changes for {system}',
                    'show who changed {system}',
                    'show change history for {system}'
                ]
            },
            'impact_assessment': {
                'pattern': 'assess impact of {system} failure',
                'expands_to': [
                    'what depends on {system}',
                    'show critical dependencies for {system}',
                    'find affected services if {system} fails'
                ]
            },
            'compliance_audit': {
                'pattern': 'audit {organization}',
                'expands_to': [
                    'show expired passwords for {organization}',
                    'find systems without backups for {organization}',
                    'list non-compliant configurations for {organization}'
                ]
            }
        }

    async def process_query(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Process natural language query with full intelligence stack.

        Args:
            query: Natural language query from engineer
            context: Optional context (current ticket, organization, etc.)

        Returns:
            Query results with metadata
        """
        start_time = datetime.utcnow()

        # Step 1: Apply fuzzy enhancement if enabled
        corrected_query = query
        fuzzy_corrections = {}
        overall_confidence = 1.0
        
        if self.enable_fuzzy and self.query_enhancer:
            enhanced = self.query_enhancer.enhance_query(
                query,
                candidates=context.get('organizations', []) if context else None,
                context=context
            )
            corrected_query = enhanced.corrected_query
            overall_confidence = enhanced.overall_confidence
            
            # Track corrections
            for token in enhanced.enhanced_tokens:
                if token.corrections:
                    fuzzy_corrections[token.original] = {
                        'corrected': token.corrections[0],
                        'confidence': token.confidence,
                        'type': 'typo'
                    }
        
        # Step 2: Detect intent and extract entities (using corrected query)
        intent = self._detect_intent(corrected_query)
        intent.fuzzy_corrections = fuzzy_corrections
        
        # Adjust confidence based on fuzzy matching
        intent.confidence *= overall_confidence
        
        # Fallback to exact match if confidence too low
        if intent.confidence < self.fuzzy_threshold and corrected_query != query:
            # Try with original query
            intent_original = self._detect_intent(query)
            if intent_original.confidence > intent.confidence:
                intent = intent_original
                corrected_query = query
                fuzzy_corrections = {}

        # Step 3: Check cache
        cache_key = f"{intent.primary_intent}:{intent.entities}"
        cached_result = await self.cache_manager.get(str(cache_key))
        if cached_result:
            cached_result['from_cache'] = True
            return cached_result

        # Step 4: Build and execute Neo4j query
        neo4j_query = self.neo4j_builder.build_query(
            intent.primary_intent,
            intent.entities,
            context.get('organizations', []) if context else []
        )

        # Step 5: Execute query
        results = await self._execute_neo4j_query(neo4j_query)

        # Step 6: Post-process results
        processed_results = self._post_process_results(
            results,
            intent,
            neo4j_query
        )

        # Step 7: Cache results
        await self.cache_manager.set(
            str(cache_key),
            processed_results,
            ttl=300  # 5 minute cache
        )

        # Step 8: Build response
        response = {
            'query': query,
            'corrected_query': corrected_query if corrected_query != query else None,
            'intent': intent.primary_intent,
            'entities': intent.entities,
            'fuzzy_corrections': intent.fuzzy_corrections,
            'confidence': intent.confidence,
            'overall_confidence': overall_confidence,
            'results': processed_results,
            'suggested_queries': self._generate_follow_up_queries(intent, results),
            'execution_time': (datetime.utcnow() - start_time).total_seconds(),
            'from_cache': False,
            'fuzzy_enabled': self.enable_fuzzy
        }

        return response

    def _detect_intent(self, query: str) -> QueryIntent:
        """Detect query intent and extract entities."""
        query_lower = query.lower().strip()

        # Check against patterns
        for pattern, intent_name, default_entities in self.intent_patterns:
            match = pattern.match(query)
            if match:
                entities = default_entities.copy()

                # Extract matched groups as entities
                if match.groups():
                    # First group is usually the target entity
                    target = match.group(1)

                    # Try to identify what type of entity this is
                    if any(org_keyword in target.lower() for org_keyword in ['company', 'client', 'organization']):
                        entities['organization'] = target
                    elif any(sys_keyword in target.lower() for sys_keyword in ['server', 'system', 'host', 'machine']):
                        entities['configuration'] = target
                    else:
                        # Default to configuration for most IT queries
                        entities['configuration'] = target

                return QueryIntent(
                    primary_intent=intent_name,
                    entities=entities,
                    confidence=0.9,
                    suggested_queries=[],
                    fuzzy_corrections={}
                )

        # Default to general search
        return QueryIntent(
            primary_intent='general_search',
            entities={'query': query},
            confidence=0.5,
            suggested_queries=self._suggest_query_clarifications(query),
            fuzzy_corrections={}
        )

    def _suggest_query_clarifications(self, query: str) -> list[str]:
        """Suggest query clarifications for ambiguous queries."""
        suggestions = []

        # Check if organization is missing
        if not any(word in query.lower() for word in ['for', 'at', 'in']):
            suggestions.append(f"{query} for [organization name]")

        # Check if query type is unclear
        if not any(word in query.lower() for word in ['show', 'list', 'find', 'get']):
            suggestions.append(f"show {query}")
            suggestions.append(f"find {query}")

        return suggestions[:3]  # Return top 3 suggestions

    async def _execute_neo4j_query(self, neo4j_query) -> list[dict[str, Any]]:
        """Execute Neo4j query."""
        if not self.neo4j_driver:
            logger.warning("Neo4j driver not initialized")
            return []

        async with self.neo4j_driver.session() as session:
            try:
                result = await session.run(
                    neo4j_query.cypher,
                    **neo4j_query.parameters
                )

                records = []
                async for record in result:
                    records.append(dict(record))

                return records

            except Exception as e:
                logger.error(f"Neo4j query execution failed: {e}")
                return []

    def _post_process_results(
        self,
        results: list[dict[str, Any]],
        intent: QueryIntent,
        neo4j_query
    ) -> list[dict[str, Any]]:
        """Post-process query results."""
        processed = []

        for result in results:
            # Convert Neo4j nodes to dictionaries
            processed_result = {}
            for key, value in result.items():
                if hasattr(value, 'get'):  # Neo4j node
                    processed_result[key] = dict(value)
                else:
                    processed_result[key] = value

            # Add relevance score based on fuzzy matching
            if neo4j_query.fuzzy_matched_entities:
                processed_result['_relevance'] = neo4j_query.fuzzy_matched_entities[0].score

            processed.append(processed_result)

        # Sort by relevance if available
        if processed and '_relevance' in processed[0]:
            processed.sort(key=lambda x: x.get('_relevance', 0), reverse=True)

        return processed

    def _generate_follow_up_queries(
        self,
        intent: QueryIntent,
        results: list[dict[str, Any]]
    ) -> list[str]:
        """Generate relevant follow-up queries based on results."""
        follow_ups = []

        # Intent-specific follow-ups
        if intent.primary_intent == 'find_configurations':
            follow_ups.extend([
                "Show dependencies for these configurations",
                "What changed recently for these systems",
                "Show related passwords"
            ])
        elif intent.primary_intent == 'find_dependencies':
            follow_ups.extend([
                "What would be impacted if this fails",
                "Show service connections",
                "Find documentation for these dependencies"
            ])
        elif intent.primary_intent == 'recent_changes':
            follow_ups.extend([
                "Show who made these changes",
                "Compare with previous configuration",
                "Find related tickets"
            ])

        # Add context-aware suggestions
        if results and len(results) > 0:
            if 'configuration' in str(results[0]):
                follow_ups.append("Show similar configurations")
            if 'password' in str(results[0]):
                follow_ups.append("Audit password age")

        return follow_ups[:5]  # Return top 5 suggestions

    async def process_template_query(
        self,
        template_name: str,
        parameters: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Process a query using a predefined template."""
        if template_name not in self.query_templates:
            raise ValueError(f"Unknown template: {template_name}")

        template = self.query_templates[template_name]
        results = []

        # Expand template to multiple queries
        for query_pattern in template.get('expands_to', []):
            query = query_pattern.format(**parameters)
            result = await self.process_query(query)
            results.append(result)

        return results
