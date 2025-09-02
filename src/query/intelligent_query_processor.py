"""Intelligent query processor combining fuzzy matching, Neo4j, and natural language understanding."""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from src.cache.manager import CacheManager
from src.query.fuzzy_enhancer import QueryFuzzyEnhancer
from src.query.fuzzy_matcher import FuzzyMatcher
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

            # Documentation (expanded)
            (re.compile(r'(?:show|find|get)\s+(?:docs?|documentation)\s+(?:for|about|on)\s+(.+)', re.I),
             'find_documentation', {}),

            (re.compile(r'(?:find|search|show)\s+(?:runbooks?|guides?|knowledge\s+base)\s+(?:for|about|on)?\s*(.+)?', re.I),
             'find_documentation', {'doc_type': 'runbook'}),

            (re.compile(r'search\s+knowledge\s+base\s+(?:for\s+)?(.+)', re.I),
             'find_documentation', {'doc_type': 'knowledge_base'}),

            # Organizations
            (re.compile(r'(?:show|list|get)\s+(?:all\s+)?organizations?', re.I),
             'list_organizations', {}),

            (re.compile(r'(?:find|search|lookup)\s+(?:organization|org|company|customer)\s+(.+)', re.I),
             'find_organization', {}),

            (re.compile(r'list\s+(?:all\s+)?(?:customers?|clients?)', re.I),
             'list_organizations', {'type': 'customer'}),

            # Locations (must be before generic find patterns)
            (re.compile(r'(?:show|list|get)\s+(?:all\s+)?locations?\s+(?:for|at|in)\s+(.+)', re.I),
             'find_locations', {}),

            (re.compile(r'(?:find|show)\s+(.+?)\s+(?:office|site|location|branch)', re.I),
             'find_location_by_city', {}),

            (re.compile(r'(?:list|show)\s+(?:sites?|offices?|branches?)\s+(?:for|of)\s+(.+)', re.I),
             'find_locations', {'filter': 'organization'}),

            # Flexible Assets
            (re.compile(r'(?:show|list|get)\s+(?:all\s+)?(?:SSL\s+)?(?:certificates?|certs?)', re.I),
             'find_flexible_assets', {'type': 'SSL Certificate'}),

            (re.compile(r'(?:show|list|find)\s+(?:warranties?|warranty\s+info)(?:\s+for\s+(.+))?', re.I),
             'find_flexible_assets', {'type': 'Warranty'}),

            (re.compile(r'(?:show|list|get)\s+(?:all\s+)?(.+?)\s+(?:assets?|licenses?)', re.I),
             'find_flexible_assets', {}),

            (re.compile(r'(?:show|list)\s+asset\s+types?', re.I),
             'list_asset_types', {}),

            (re.compile(r'what\s+(?:fields?|properties?)\s+does?\s+(.+?)\s+have', re.I),
             'describe_asset_type', {}),

            # Contacts
            (re.compile(r'(?:find|show|get)\s+(?:contact\s+)?(?:info|information)\s+(?:for\s+)?(.+)', re.I),
             'find_contact', {}),

            (re.compile(r'(?:find|show|list)\s+(?:all\s+)?IT\s+(?:managers?|staff|team)\s+(?:for|at|in)\s+(.+)', re.I),
             'find_contacts', {'title_filter': 'IT'}),

            (re.compile(r'who\s+is\s+(?:the\s+)?(.+?)(?:\s+contact)?', re.I),
             'find_contact_by_name', {}),

            (re.compile(r'(?:find)\s+(.+?)\s+(?:contact|email|phone)', re.I),
             'find_contact_by_name', {}),

            (re.compile(r'(?:list|show)\s+(?:all\s+)?contacts?\s+(?:for|at|in)\s+(.+)', re.I),
             'find_contacts', {}),

            # Generic search (must be last to avoid overriding specific patterns)
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
        """Detect query intent and extract entities with disambiguation."""
        query_lower = query.lower().strip()

        # Track all matching intents for disambiguation
        matching_intents = []

        # Check against patterns
        for pattern, intent_name, default_entities in self.intent_patterns:
            match = pattern.match(query)
            if match:
                entities = default_entities.copy()
                confidence = 0.9  # Base confidence for pattern match

                # Extract matched groups as entities
                if match.groups():
                    # First group is usually the target entity
                    target = match.group(1) if match.group(1) else ""

                    # Enhanced entity type detection with disambiguation
                    entity_type = self._determine_entity_type(target, intent_name)
                    if entity_type:
                        entities[entity_type] = target

                    # Adjust confidence based on entity clarity
                    if entity_type == 'ambiguous':
                        confidence *= 0.9  # Minor reduction for ambiguous entities

                matching_intents.append({
                    'intent': intent_name,
                    'entities': entities,
                    'confidence': confidence,
                    'match_span': match.span()
                })

        # Handle multiple matching intents (disambiguation)
        if len(matching_intents) > 1:
            # Sort by confidence and specificity
            matching_intents.sort(key=lambda x: (x['confidence'], -x['match_span'][0]), reverse=True)

            # Check if top intents have similar confidence
            top_intent = matching_intents[0]
            similar_intents = [i for i in matching_intents[1:3]
                             if abs(i['confidence'] - top_intent['confidence']) < 0.1]

            if similar_intents:
                # Ambiguous - provide suggestions
                suggested_queries = self._generate_disambiguation_suggestions(
                    query, top_intent, similar_intents
                )

                return QueryIntent(
                    primary_intent=top_intent['intent'],
                    entities=top_intent['entities'],
                    confidence=top_intent['confidence'] * 0.8,  # Reduce confidence due to ambiguity
                    suggested_queries=suggested_queries,
                    fuzzy_corrections={},
                    secondary_intents=[i['intent'] for i in similar_intents]
                )
            else:
                # Clear winner
                return QueryIntent(
                    primary_intent=top_intent['intent'],
                    entities=top_intent['entities'],
                    confidence=top_intent['confidence'],
                    suggested_queries=self._generate_follow_up_suggestions(top_intent['intent']),
                    fuzzy_corrections={}
                )

        elif len(matching_intents) == 1:
            # Single clear match
            match = matching_intents[0]

            # For general_search, always provide clarification suggestions
            if match['intent'] == 'general_search':
                suggestions = self._suggest_query_clarifications(query)
            else:
                suggestions = self._generate_follow_up_suggestions(match['intent'])
                # Ensure we have suggestions
                if not suggestions:
                    suggestions = self._suggest_query_clarifications(query)

            return QueryIntent(
                primary_intent=match['intent'],
                entities=match['entities'],
                confidence=match['confidence'],
                suggested_queries=suggestions,
                fuzzy_corrections={}
            )

        # No matches - default to general search with helpful suggestions
        return QueryIntent(
            primary_intent='general_search',
            entities={'query': query},
            confidence=0.5,
            suggested_queries=self._suggest_query_clarifications(query),
            fuzzy_corrections={}
        )

    def _determine_entity_type(self, target: str, intent_name: str) -> str:
        """Determine the type of entity based on context and keywords."""
        if not target:
            return None

        target_lower = target.lower()

        # Intent-specific entity determination
        if 'organization' in intent_name or 'companies' in intent_name:
            return 'organization'
        elif 'location' in intent_name or 'office' in intent_name:
            return 'location'
        elif 'contact' in intent_name:
            return 'contact'
        elif 'asset' in intent_name:
            return 'asset_type'
        elif 'document' in intent_name:
            return 'document'

        # Keyword-based detection
        if any(org_keyword in target_lower for org_keyword in
               ['company', 'client', 'organization', 'customer', 'corp', 'inc', 'ltd']):
            return 'organization'
        elif any(loc_keyword in target_lower for loc_keyword in
                ['office', 'site', 'location', 'branch', 'building', 'floor']):
            return 'location'
        elif any(sys_keyword in target_lower for sys_keyword in
                ['server', 'system', 'host', 'machine', 'workstation', 'desktop']):
            return 'configuration'
        elif any(person_keyword in target_lower for person_keyword in
                ['john', 'jane', 'smith', 'manager', 'admin', 'engineer']):
            return 'contact'
        elif any(asset_keyword in target_lower for asset_keyword in
                ['certificate', 'warranty', 'license', 'asset']):
            return 'asset_type'

        # Default based on intent
        if 'configuration' in intent_name or 'server' in intent_name:
            return 'configuration'
        elif 'password' in intent_name:
            return 'configuration'  # Passwords usually relate to systems

        return 'ambiguous'  # Can't determine clearly

    def _generate_disambiguation_suggestions(
        self,
        query: str,
        primary: dict,
        alternatives: list[dict]
    ) -> list[str]:
        """Generate suggestions to disambiguate unclear queries."""
        suggestions = []

        # Add clarifying prefixes
        if primary['intent'] == 'general_search':
            if any('organization' in alt['intent'] for alt in alternatives):
                suggestions.append(f"find organization {query}")
            if any('location' in alt['intent'] for alt in alternatives):
                suggestions.append(f"show location {query}")
            if any('contact' in alt['intent'] for alt in alternatives):
                suggestions.append(f"find contact {query}")

        # Add context specifiers
        if 'for' not in query.lower() and 'at' not in query.lower():
            suggestions.append(f"{query} for [specific organization]")
            suggestions.append(f"{query} at [specific location]")

        # Add type specifiers for assets
        if 'asset' in primary['intent'] or any('asset' in alt['intent'] for alt in alternatives):
            suggestions.append("show SSL certificates")
            suggestions.append("list warranties")
            suggestions.append("show all asset types")

        return suggestions[:5]  # Return top 5 suggestions

    def _generate_follow_up_suggestions(self, intent: str) -> list[str]:
        """Generate follow-up query suggestions based on intent."""
        suggestions = {
            'find_organization': [
                "show all configurations for this organization",
                "list contacts for this organization",
                "show locations for this organization"
            ],
            'find_locations': [
                "show configurations at this location",
                "list contacts at this location",
                "show assets at this location"
            ],
            'find_flexible_assets': [
                "show expiring certificates",
                "list warranties by vendor",
                "show asset fields"
            ],
            'find_documentation': [
                "search runbooks",
                "find setup guides",
                "show knowledge base articles"
            ],
            'find_contact': [
                "show contact's organization",
                "list contact's responsibilities",
                "show contact's location"
            ]
        }

        return suggestions.get(intent, [])

    def _suggest_query_clarifications(self, query: str) -> list[str]:
        """Suggest query clarifications for ambiguous queries."""
        suggestions = []
        query_lower = query.lower()

        # Check if organization is missing
        if not any(word in query_lower for word in ['for', 'at', 'in']):
            suggestions.append(f"{query} for [organization name]")

        # Check if query type is unclear
        if not any(word in query_lower for word in ['show', 'list', 'find', 'get', 'search']):
            suggestions.append(f"show {query}")
            suggestions.append(f"find {query}")
            suggestions.append(f"search {query}")

        # Suggest specific resource types if generic
        if 'microsoft' in query_lower or 'google' in query_lower or 'amazon' in query_lower:
            suggestions.append(f"find organization {query}")
            suggestions.append(f"find contact at {query}")
            suggestions.append(f"show configurations for {query}")

        # Generic terms need specification
        if any(term in query_lower for term in ['info', 'details', 'data', 'information']):
            suggestions.append(f"show configurations {query}")
            suggestions.append(f"find documentation {query}")
            suggestions.append(f"list contacts {query}")

        # Always provide at least one suggestion for general searches
        if not suggestions:
            suggestions.append(f"show all information for {query}")
            suggestions.append(f"search documentation for {query}")
            suggestions.append(f"find {query} in all resources")

        return suggestions[:5]  # Return top 5 suggestions

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
