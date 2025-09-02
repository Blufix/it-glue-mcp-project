"""Smart suggestion engine for intelligent query autocomplete and follow-up generation."""

import json
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SuggestionType(Enum):
    """Types of suggestions the engine can generate."""
    AUTOCOMPLETE = "autocomplete"      # Complete the current partial query
    REFINEMENT = "refinement"          # Refine/narrow current query
    FOLLOW_UP = "follow_up"             # Natural follow-up based on results
    ALTERNATIVE = "alternative"         # Alternative query approach
    TEMPLATE = "template"               # Template-based suggestion
    CONTEXTUAL = "contextual"           # Based on current context/session


@dataclass
class QuerySuggestion:
    """Represents a single query suggestion."""
    text: str
    type: SuggestionType
    confidence: float
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)
    priority: float = 0.0


@dataclass
class SessionContext:
    """Maintains context for multi-query sessions."""
    session_id: str
    queries: list[str] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)
    current_organization: Optional[str] = None
    recent_systems: list[str] = field(default_factory=list)
    recent_entities: dict[str, list[str]] = field(default_factory=dict)
    time_context: Optional[datetime] = None
    last_activity: datetime = field(default_factory=datetime.now)


class TrieNode:
    """Node in the prefix trie for efficient autocomplete."""
    def __init__(self):
        self.children: dict[str, 'TrieNode'] = {}
        self.is_end: bool = False
        self.frequency: int = 0
        self.full_queries: list[tuple[str, float]] = []  # (query, score)


class PrefixTrie:
    """Trie data structure for efficient prefix matching."""

    def __init__(self):
        self.root = TrieNode()

    def insert(self, query: str, frequency: float = 1.0):
        """Insert a query into the trie."""
        node = self.root
        query_lower = query.lower()

        for char in query_lower:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]

        node.is_end = True
        node.frequency += frequency
        node.full_queries.append((query, frequency))

    def search_prefix(self, prefix: str, max_results: int = 5) -> list[tuple[str, float]]:
        """Search for queries starting with the given prefix."""
        node = self.root
        prefix_lower = prefix.lower()

        # Navigate to prefix node
        for char in prefix_lower:
            if char not in node.children:
                return []
            node = node.children[char]

        # Collect all complete queries from this point
        results = []
        self._collect_queries(node, results)

        # Sort by score and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_results]

    def _collect_queries(self, node: TrieNode, results: list[tuple[str, float]]):
        """Recursively collect all queries from a node."""
        if node.is_end:
            for query, score in node.full_queries:
                results.append((query, score * node.frequency))

        for child in node.children.values():
            self._collect_queries(child, results)


class SmartSuggestionEngine:
    """ML-based suggestion system for intelligent query assistance."""

    def __init__(self,
                 storage_path: str = "./data/suggestions",
                 query_learning_engine=None,
                 cache_manager=None):
        """Initialize the suggestion engine."""
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.query_learning = query_learning_engine
        self.cache = cache_manager

        # Prefix trie for autocomplete
        self.prefix_trie = PrefixTrie()

        # Common query templates
        self.query_templates = self._initialize_templates()

        # Sessions for context tracking
        self.sessions: dict[str, SessionContext] = {}

        # Pattern matchers
        self.entity_patterns = self._compile_entity_patterns()

        # Query history for learning
        self.query_history: list[dict[str, Any]] = []

        # Load pre-trained data
        self._load_pretrained_data()

    def _initialize_templates(self) -> list[dict[str, Any]]:
        """Initialize common query templates."""
        return [
            {
                "pattern": r"show (?:me )?(.+) for (.+)",
                "template": "show {entity} for {organization}",
                "type": "retrieval",
                "suggestions": [
                    "show passwords for {organization}",
                    "show configurations for {organization}",
                    "show documentation for {organization}"
                ]
            },
            {
                "pattern": r"what (?:is|are) (.+) (?:password|credentials)",
                "template": "what is {system} password",
                "type": "credential",
                "suggestions": [
                    "what is {system} admin password",
                    "what is {system} root password",
                    "what is {system} service account"
                ]
            },
            {
                "pattern": r"(?:find|search) (.+) (?:changed|modified) (?:in )?(.+)",
                "template": "find {entity} changed in {timeframe}",
                "type": "audit",
                "suggestions": [
                    "find configurations changed in last 24 hours",
                    "find passwords modified yesterday",
                    "find documents updated this week"
                ]
            },
            {
                "pattern": r"(?:show|list) (?:all )?(.+) (?:related to|connected to|for) (.+)",
                "template": "show {entity} related to {target}",
                "type": "relationship",
                "suggestions": [
                    "show systems connected to {target}",
                    "show dependencies for {target}",
                    "show configurations related to {target}"
                ]
            },
            {
                "pattern": r"(?:impact|what happens) (?:if|when) (.+) (?:fails|goes down|stops)",
                "template": "impact if {system} fails",
                "type": "impact",
                "suggestions": [
                    "what services depend on {system}",
                    "show blast radius for {system}",
                    "list affected systems if {system} fails"
                ]
            }
        ]

    def _compile_entity_patterns(self) -> dict[str, re.Pattern]:
        """Compile regex patterns for entity extraction."""
        return {
            "organization": re.compile(r"\b(?:org|organization|company|client)\s+([^\s]+)", re.I),
            "system": re.compile(r"\b(?:server|system|host|machine)\s+([^\s]+)", re.I),
            "ip_address": re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b"),
            "timeframe": re.compile(r"\b(last\s+\d+\s+(?:hours?|days?|weeks?)|yesterday|today|this\s+week)\b", re.I),
            "configuration": re.compile(r"\b(?:config|configuration)\s+([^\s]+)", re.I),
            "service": re.compile(r"\b(?:service|application|app)\s+([^\s]+)", re.I)
        }

    def _load_pretrained_data(self):
        """Load pre-trained patterns and common queries."""
        # Common IT queries for autocomplete
        common_queries = [
            ("show all passwords", 100),
            ("show passwords for", 95),
            ("what is the admin password", 90),
            ("find server configuration", 85),
            ("show network diagram", 80),
            ("list all servers", 75),
            ("show firewall rules", 70),
            ("find SSL certificates", 65),
            ("show backup status", 60),
            ("check service status", 55),
            ("show recent changes", 50),
            ("find documentation for", 45),
            ("show dependencies for", 40),
            ("what systems connect to", 35),
            ("show audit log", 30),
            ("find expired passwords", 25),
            ("show network topology", 20),
            ("list database servers", 15),
            ("show vpn configuration", 10),
            ("find emergency contacts", 5)
        ]

        for query, freq in common_queries:
            self.prefix_trie.insert(query, freq)

    def generate_suggestions(self,
                            partial_query: str,
                            session_id: Optional[str] = None,
                            current_results: Optional[list[dict]] = None,
                            max_suggestions: int = 5) -> list[QuerySuggestion]:
        """Generate smart suggestions based on input and context."""
        suggestions = []

        # Get or create session context
        context = self._get_session_context(session_id)

        # 1. Autocomplete suggestions from prefix trie
        if len(partial_query) >= 2:
            autocomplete = self._generate_autocomplete(partial_query, context)
            suggestions.extend(autocomplete)

        # 2. Template-based suggestions
        template_suggestions = self._generate_template_suggestions(partial_query, context)
        suggestions.extend(template_suggestions)

        # 3. Follow-up suggestions based on current results
        if current_results:
            follow_ups = self._generate_follow_ups(partial_query, current_results, context)
            suggestions.extend(follow_ups)

        # 4. Contextual suggestions based on session history
        if context and len(context.queries) > 0:
            contextual = self._generate_contextual_suggestions(partial_query, context)
            suggestions.extend(contextual)

        # 5. Alternative query approaches
        alternatives = self._generate_alternatives(partial_query, context)
        suggestions.extend(alternatives)

        # Deduplicate and rank suggestions
        suggestions = self._rank_and_filter_suggestions(suggestions, max_suggestions)

        return suggestions

    def _generate_autocomplete(self,
                              partial: str,
                              context: SessionContext) -> list[QuerySuggestion]:
        """Generate autocomplete suggestions using prefix trie."""
        suggestions = []

        # Search prefix trie
        matches = self.prefix_trie.search_prefix(partial, max_results=10)

        for query, score in matches:
            # Skip if too similar to partial
            if query.lower() == partial.lower():
                continue

            # Boost score based on context
            if context and context.current_organization:
                if context.current_organization.lower() in query.lower():
                    score *= 1.5

            suggestion = QuerySuggestion(
                text=query,
                type=SuggestionType.AUTOCOMPLETE,
                confidence=min(1.0, score / 100),
                reason="Common query pattern",
                priority=score
            )
            suggestions.append(suggestion)

        return suggestions

    def _generate_template_suggestions(self,
                                      partial: str,
                                      context: SessionContext) -> list[QuerySuggestion]:
        """Generate suggestions based on query templates."""
        suggestions = []

        for template in self.query_templates:
            pattern = template["pattern"]
            match = re.search(pattern, partial, re.IGNORECASE)

            if match:
                # Extract matched groups
                groups = match.groups()

                # Generate suggestions from template
                for suggestion_template in template["suggestions"]:
                    # Replace placeholders with context or matched values
                    text = suggestion_template

                    if context and context.current_organization:
                        text = text.replace("{organization}", context.current_organization)

                    if context and context.recent_systems:
                        text = text.replace("{system}", context.recent_systems[0])

                    if groups:
                        text = text.replace("{entity}", groups[0] if len(groups) > 0 else "")
                        text = text.replace("{target}", groups[1] if len(groups) > 1 else "")

                    suggestion = QuerySuggestion(
                        text=text,
                        type=SuggestionType.TEMPLATE,
                        confidence=0.8,
                        reason=f"Based on {template['type']} query pattern",
                        metadata={"template": template["template"]}
                    )
                    suggestions.append(suggestion)

        return suggestions

    def _generate_follow_ups(self,
                            partial: str,
                            results: list[dict],
                            context: SessionContext) -> list[QuerySuggestion]:
        """Generate follow-up queries based on current results."""
        suggestions = []

        # Analyze result types
        result_types = Counter()
        entities = defaultdict(set)

        for result in results[:10]:  # Analyze top 10 results
            if "type" in result:
                result_types[result["type"]] += 1

            # Extract entities from results
            if "organization" in result:
                entities["organization"].add(result["organization"])
            if "system" in result:
                entities["system"].add(result["system"])
            if "configuration" in result:
                entities["configuration"].add(result["configuration"])

        # Generate follow-ups based on result analysis
        if result_types.get("password", 0) > 0:
            suggestions.extend([
                QuerySuggestion(
                    text="show password history",
                    type=SuggestionType.FOLLOW_UP,
                    confidence=0.7,
                    reason="Password results found - check history"
                ),
                QuerySuggestion(
                    text="check password expiration",
                    type=SuggestionType.FOLLOW_UP,
                    confidence=0.7,
                    reason="Password results found - check expiration"
                )
            ])

        if result_types.get("configuration", 0) > 0:
            suggestions.extend([
                QuerySuggestion(
                    text="show related configurations",
                    type=SuggestionType.FOLLOW_UP,
                    confidence=0.7,
                    reason="Configuration results found - explore related"
                ),
                QuerySuggestion(
                    text="show configuration dependencies",
                    type=SuggestionType.FOLLOW_UP,
                    confidence=0.7,
                    reason="Configuration results found - check dependencies"
                )
            ])

        # Entity-specific follow-ups
        if entities["system"]:
            system = list(entities["system"])[0]
            suggestions.append(
                QuerySuggestion(
                    text=f"show all documentation for {system}",
                    type=SuggestionType.FOLLOW_UP,
                    confidence=0.8,
                    reason=f"Explore more about {system}"
                )
            )

        return suggestions

    def _generate_contextual_suggestions(self,
                                        partial: str,
                                        context: SessionContext) -> list[QuerySuggestion]:
        """Generate suggestions based on session context."""
        suggestions = []

        if not context or not context.queries:
            return suggestions

        # Analyze recent queries for patterns
        recent_query = context.queries[-1] if context.queries else ""

        # If previous query was about a specific entity, suggest related queries
        for entity_type, pattern in self.entity_patterns.items():
            match = pattern.search(recent_query)
            if match:
                entity_value = match.group(1)

                if entity_type == "organization":
                    suggestions.extend([
                        QuerySuggestion(
                            text=f"show all assets for {entity_value}",
                            type=SuggestionType.CONTEXTUAL,
                            confidence=0.75,
                            reason="Continue exploring this organization"
                        ),
                        QuerySuggestion(
                            text=f"show network topology for {entity_value}",
                            type=SuggestionType.CONTEXTUAL,
                            confidence=0.7,
                            reason="Visualize organization infrastructure"
                        )
                    ])
                elif entity_type == "system":
                    suggestions.extend([
                        QuerySuggestion(
                            text=f"show services running on {entity_value}",
                            type=SuggestionType.CONTEXTUAL,
                            confidence=0.75,
                            reason="Explore system services"
                        ),
                        QuerySuggestion(
                            text=f"check last reboot of {entity_value}",
                            type=SuggestionType.CONTEXTUAL,
                            confidence=0.7,
                            reason="Check system status"
                        )
                    ])

        # Time-based contextual suggestions
        if context.time_context:
            time_diff = datetime.now() - context.time_context
            if time_diff < timedelta(minutes=5):
                suggestions.append(
                    QuerySuggestion(
                        text="show changes in last hour",
                        type=SuggestionType.CONTEXTUAL,
                        confidence=0.6,
                        reason="Recent time-based query detected"
                    )
                )

        return suggestions

    def _generate_alternatives(self,
                              partial: str,
                              context: SessionContext) -> list[QuerySuggestion]:
        """Generate alternative query approaches."""
        suggestions = []

        # Detect query intent
        intent = self._detect_intent(partial)

        # Suggest alternatives based on intent
        if intent == "troubleshooting":
            suggestions.extend([
                QuerySuggestion(
                    text="show recent error logs",
                    type=SuggestionType.ALTERNATIVE,
                    confidence=0.6,
                    reason="Alternative troubleshooting approach"
                ),
                QuerySuggestion(
                    text="check service dependencies",
                    type=SuggestionType.ALTERNATIVE,
                    confidence=0.6,
                    reason="Check for dependency issues"
                )
            ])
        elif intent == "investigation":
            suggestions.extend([
                QuerySuggestion(
                    text="show audit trail",
                    type=SuggestionType.ALTERNATIVE,
                    confidence=0.6,
                    reason="Alternative investigation method"
                ),
                QuerySuggestion(
                    text="compare with baseline configuration",
                    type=SuggestionType.ALTERNATIVE,
                    confidence=0.6,
                    reason="Check for deviations"
                )
            ])

        return suggestions

    def _detect_intent(self, query: str) -> str:
        """Detect the intent of a query."""
        query_lower = query.lower()

        troubleshooting_keywords = ["error", "fail", "down", "not working", "issue", "problem"]
        investigation_keywords = ["who", "when", "changed", "modified", "audit", "investigate"]
        documentation_keywords = ["how to", "guide", "documentation", "procedure", "manual"]

        for keyword in troubleshooting_keywords:
            if keyword in query_lower:
                return "troubleshooting"

        for keyword in investigation_keywords:
            if keyword in query_lower:
                return "investigation"

        for keyword in documentation_keywords:
            if keyword in query_lower:
                return "documentation"

        return "general"

    def _rank_and_filter_suggestions(self,
                                    suggestions: list[QuerySuggestion],
                                    max_count: int) -> list[QuerySuggestion]:
        """Rank and filter suggestions to return the best ones."""
        # Remove duplicates
        seen = set()
        unique_suggestions = []

        for suggestion in suggestions:
            key = suggestion.text.lower()
            if key not in seen:
                seen.add(key)
                unique_suggestions.append(suggestion)

        # Calculate final scores
        for suggestion in unique_suggestions:
            # Combine confidence and priority
            suggestion.priority = (
                suggestion.confidence * 0.7 +
                (suggestion.priority / 100 if suggestion.priority > 0 else 0) * 0.3
            )

        # Sort by priority
        unique_suggestions.sort(key=lambda x: x.priority, reverse=True)

        # Return top suggestions with diversity
        final_suggestions = []
        type_counts = Counter()

        for suggestion in unique_suggestions:
            # Ensure diversity in suggestion types
            if type_counts[suggestion.type] < 2:
                final_suggestions.append(suggestion)
                type_counts[suggestion.type] += 1

            if len(final_suggestions) >= max_count:
                break

        return final_suggestions

    def _get_session_context(self, session_id: Optional[str]) -> SessionContext:
        """Get or create session context."""
        if not session_id:
            return SessionContext(session_id="default")

        if session_id not in self.sessions:
            self.sessions[session_id] = SessionContext(session_id=session_id)

        # Clean up old sessions
        self._cleanup_old_sessions()

        return self.sessions[session_id]

    def _cleanup_old_sessions(self):
        """Remove inactive sessions."""
        now = datetime.now()
        inactive_threshold = timedelta(hours=1)

        to_remove = []
        for session_id, context in self.sessions.items():
            if now - context.last_activity > inactive_threshold:
                to_remove.append(session_id)

        for session_id in to_remove:
            del self.sessions[session_id]

    def update_session_context(self,
                              session_id: str,
                              query: str,
                              results: Optional[list[dict]] = None):
        """Update session context with new query and results."""
        context = self._get_session_context(session_id)

        # Add query to history
        context.queries.append(query)
        if len(context.queries) > 5:  # Keep last 5 queries
            context.queries.pop(0)

        # Add results
        if results:
            context.results.append(results)
            if len(context.results) > 5:
                context.results.pop(0)

        # Extract entities from query
        for entity_type, pattern in self.entity_patterns.items():
            matches = pattern.findall(query)
            if matches:
                if entity_type not in context.recent_entities:
                    context.recent_entities[entity_type] = []
                context.recent_entities[entity_type].extend(matches)
                # Keep only recent entities
                context.recent_entities[entity_type] = context.recent_entities[entity_type][-5:]

        # Update activity timestamp
        context.last_activity = datetime.now()

        # Update trie with successful query
        self.prefix_trie.insert(query, 1.0)

    def learn_from_selection(self,
                            session_id: str,
                            suggested_query: str,
                            selected: bool):
        """Learn from user's selection of suggestions."""
        if selected:
            # Increase frequency in trie
            self.prefix_trie.insert(suggested_query, 2.0)

            # Store in history for pattern learning
            self.query_history.append({
                "query": suggested_query,
                "timestamp": datetime.now(),
                "session_id": session_id,
                "selected": True
            })

        # Persist learning data periodically
        if len(self.query_history) % 100 == 0:
            self._persist_learning_data()

    def _persist_learning_data(self):
        """Save learned patterns to disk."""
        try:
            history_file = self.storage_path / "query_history.json"
            with open(history_file, 'w') as f:
                # Convert datetime to string for JSON serialization
                history_data = []
                for item in self.query_history[-1000:]:  # Keep last 1000 entries
                    item_copy = item.copy()
                    if isinstance(item_copy.get("timestamp"), datetime):
                        item_copy["timestamp"] = item_copy["timestamp"].isoformat()
                    history_data.append(item_copy)
                json.dump(history_data, f, indent=2)

            logger.info(f"Persisted {len(history_data)} query history entries")

        except Exception as e:
            logger.error(f"Failed to persist learning data: {e}")

    def generate_follow_up_queries(self,
                                  original_query: str,
                                  results: list[dict],
                                  max_queries: int = 3) -> list[str]:
        """Generate follow-up queries based on current results."""
        follow_ups = []

        # Analyze results for entities and patterns
        entities = self._extract_entities_from_results(results)

        # Generate follow-ups based on result type
        if any(r.get("type") == "configuration" for r in results):
            if entities.get("system"):
                system = entities["system"][0]
                follow_ups.extend([
                    f"show dependencies for {system}",
                    f"check health status of {system}",
                    f"show recent changes to {system}"
                ])

        if any(r.get("type") == "password" for r in results):
            follow_ups.extend([
                "check for expired passwords",
                "show password policy compliance",
                "list accounts with weak passwords"
            ])

        if any(r.get("type") == "documentation" for r in results):
            if entities.get("topic"):
                topic = entities["topic"][0]
                follow_ups.extend([
                    f"show troubleshooting guide for {topic}",
                    f"find related documentation for {topic}",
                    f"show configuration examples for {topic}"
                ])

        # Remove duplicates and limit count
        seen = set()
        unique_follow_ups = []
        for query in follow_ups:
            if query not in seen and query != original_query:
                seen.add(query)
                unique_follow_ups.append(query)
                if len(unique_follow_ups) >= max_queries:
                    break

        return unique_follow_ups

    def _extract_entities_from_results(self, results: list[dict]) -> dict[str, list[str]]:
        """Extract entities from search results."""
        entities = defaultdict(set)

        for result in results[:20]:  # Analyze top 20 results
            # Extract standard fields
            if "organization" in result:
                entities["organization"].add(result["organization"])
            if "system" in result:
                entities["system"].add(result["system"])
            if "hostname" in result:
                entities["system"].add(result["hostname"])
            if "configuration_type" in result:
                entities["type"].add(result["configuration_type"])
            if "topic" in result:
                entities["topic"].add(result["topic"])

            # Extract from nested attributes
            if "attributes" in result:
                attrs = result["attributes"]
                if "organization-name" in attrs:
                    entities["organization"].add(attrs["organization-name"])
                if "hostname" in attrs:
                    entities["system"].add(attrs["hostname"])
                if "name" in attrs:
                    entities["name"].add(attrs["name"])

        # Convert sets to lists
        return {k: list(v) for k, v in entities.items()}
