"""Session-based context management for multi-query conversations."""

import json
import logging
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """Types of context information tracked."""
    ORGANIZATION = "organization"
    SYSTEM = "system"
    SERVICE = "service"
    TIMEFRAME = "timeframe"
    LOCATION = "location"
    USER = "user"
    CONFIGURATION = "configuration"
    NETWORK = "network"


@dataclass
class QueryContext:
    """Context extracted from a single query."""
    query_text: str
    timestamp: datetime
    entities: dict[str, list[str]] = field(default_factory=dict)
    intent: Optional[str] = None
    results_count: int = 0
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationSession:
    """Represents a multi-query conversation session."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    queries: deque = field(default_factory=lambda: deque(maxlen=5))
    current_organization: Optional[str] = None
    recent_systems: list[str] = field(default_factory=list)
    recent_services: list[str] = field(default_factory=list)
    time_context: Optional[dict[str, Any]] = None
    entity_mentions: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    context_stack: list[dict[str, Any]] = field(default_factory=list)
    user_preferences: dict[str, Any] = field(default_factory=dict)
    active: bool = True

    def add_query(self, query_context: QueryContext):
        """Add a query to the session history."""
        self.queries.append(query_context)
        self.last_activity = datetime.now()

        # Update entity mentions
        for entity_type, entities in query_context.entities.items():
            for entity in entities:
                self.entity_mentions[entity_type][entity] += 1

    def get_most_mentioned_entities(self, entity_type: str, limit: int = 3) -> list[tuple[str, int]]:
        """Get most frequently mentioned entities of a type."""
        if entity_type not in self.entity_mentions:
            return []

        sorted_entities = sorted(
            self.entity_mentions[entity_type].items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_entities[:limit]


class SessionContextManager:
    """Manages conversation sessions and context for multi-query interactions."""

    def __init__(self,
                 storage_path: str = "./data/sessions",
                 session_timeout_minutes: int = 30,
                 max_sessions: int = 100):
        """Initialize the session context manager."""
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.sessions: dict[str, ConversationSession] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.max_sessions = max_sessions

        # Entity extraction patterns
        self.entity_patterns = self._compile_entity_patterns()

        # Context resolution rules
        self.resolution_rules = self._initialize_resolution_rules()

        # Load persisted sessions
        self._load_sessions()

    def _compile_entity_patterns(self) -> dict[str, re.Pattern]:
        """Compile regex patterns for entity extraction."""
        return {
            ContextType.ORGANIZATION.value: re.compile(
                r'\b(?:org(?:anization)?|company|client|customer|account)\s+["\']?([^"\'\s,]+)["\']?', re.I
            ),
            ContextType.SYSTEM.value: re.compile(
                r'\b(?:server|host|machine|system|node|instance)\s+["\']?([^"\'\s,]+)["\']?', re.I
            ),
            ContextType.SERVICE.value: re.compile(
                r'\b(?:service|application|app|process|daemon)\s+["\']?([^"\'\s,]+)["\']?', re.I
            ),
            ContextType.TIMEFRAME.value: re.compile(
                r'\b((?:last|past|previous)\s+\d+\s+(?:minute|hour|day|week|month)s?|'
                r'yesterday|today|this\s+(?:morning|afternoon|evening|week|month)|'
                r'since\s+(?:yesterday|monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b', re.I
            ),
            ContextType.LOCATION.value: re.compile(
                r'\b(?:location|site|office|datacenter|dc|region|zone)\s+["\']?([^"\'\s,]+)["\']?', re.I
            ),
            ContextType.CONFIGURATION.value: re.compile(
                r'\b(?:config(?:uration)?|setting|parameter|property)\s+["\']?([^"\'\s,]+)["\']?', re.I
            ),
            ContextType.NETWORK.value: re.compile(
                r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)\b|'
                r'\b(?:vlan|subnet|network|segment)\s+["\']?([^"\'\s,]+)["\']?', re.I
            ),
            ContextType.USER.value: re.compile(
                r'\b(?:user|account|login|username)\s+["\']?([^"\'\s,]+)["\']?', re.I
            )
        }

    def _initialize_resolution_rules(self) -> list[dict[str, Any]]:
        """Initialize context resolution rules for incomplete queries."""
        return [
            {
                "pattern": r'^(?:show|list|get|find)\s+(?:all\s+)?(?:its|their|the)\s+(\w+)',
                "requires": [ContextType.ORGANIZATION, ContextType.SYSTEM],
                "resolution": "resolve_possessive_reference"
            },
            {
                "pattern": r'^(?:what|when|who|how)\s+(?:was|were|did)',
                "requires": [ContextType.TIMEFRAME],
                "resolution": "resolve_temporal_reference"
            },
            {
                "pattern": r'^(?:same|similar|related|connected)',
                "requires": [ContextType.SYSTEM, ContextType.SERVICE],
                "resolution": "resolve_relative_reference"
            },
            {
                "pattern": r'^(?:there|here|this|that)\s+',
                "requires": [ContextType.LOCATION],
                "resolution": "resolve_spatial_reference"
            },
            {
                "pattern": r'^(?:again|repeat|retry)',
                "requires": [],
                "resolution": "resolve_repetition_reference"
            }
        ]

    def create_session(self, session_id: str) -> ConversationSession:
        """Create a new conversation session."""
        # Clean up old sessions if at capacity
        if len(self.sessions) >= self.max_sessions:
            self._cleanup_old_sessions(force_cleanup=True)

        session = ConversationSession(
            session_id=session_id,
            created_at=datetime.now(),
            last_activity=datetime.now()
        )

        self.sessions[session_id] = session
        return session

    def get_or_create_session(self, session_id: str) -> ConversationSession:
        """Get existing session or create new one."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            # Check if session is expired
            if datetime.now() - session.last_activity > self.session_timeout:
                session.active = False
                # Create new session
                return self.create_session(session_id)
            return session
        else:
            return self.create_session(session_id)

    def process_query(self,
                     session_id: str,
                     query: str,
                     results: Optional[list[dict]] = None) -> QueryContext:
        """Process a query and extract context."""
        session = self.get_or_create_session(session_id)

        # Extract entities from query
        entities = self.extract_entities(query)

        # Detect intent
        intent = self.detect_intent(query)

        # Create query context
        query_context = QueryContext(
            query_text=query,
            timestamp=datetime.now(),
            entities=entities,
            intent=intent,
            results_count=len(results) if results else 0,
            success=bool(results and len(results) > 0)
        )

        # Update session with query context
        session.add_query(query_context)

        # Update session state based on extracted entities
        self._update_session_state(session, query_context)

        # Persist session periodically
        if len(session.queries) % 5 == 0:
            self._persist_session(session)

        return query_context

    def extract_entities(self, query: str) -> dict[str, list[str]]:
        """Extract entities from a query."""
        entities = {}

        for entity_type, pattern in self.entity_patterns.items():
            matches = pattern.findall(query)
            if matches:
                # Handle tuples from findall with groups
                if isinstance(matches[0], tuple):
                    matches = [m for group in matches for m in group if m]
                entities[entity_type] = list(set(matches))

        return entities

    def detect_intent(self, query: str) -> str:
        """Detect the intent of a query."""
        query_lower = query.lower()

        # Intent patterns
        intents = {
            "retrieval": r'\b(?:show|list|get|find|search|display)\b',
            "troubleshooting": r'\b(?:error|fail|down|broken|not\s+working|issue|problem)\b',
            "investigation": r'\b(?:who|when|what|changed|modified|audit|investigate)\b',
            "analysis": r'\b(?:analyze|compare|impact|depend|relate|connect)\b',
            "configuration": r'\b(?:configure|setup|install|deploy|update|patch)\b',
            "monitoring": r'\b(?:status|health|check|monitor|alert|metric)\b',
            "documentation": r'\b(?:how\s+to|guide|manual|procedure|document|instruction)\b'
        }

        for intent_name, pattern in intents.items():
            if re.search(pattern, query_lower):
                return intent_name

        return "general"

    def resolve_incomplete_query(self,
                                session_id: str,
                                incomplete_query: str) -> str:
        """Resolve an incomplete query using session context."""
        session = self.get_or_create_session(session_id)

        # Check resolution rules
        for rule in self.resolution_rules:
            if re.search(rule["pattern"], incomplete_query, re.I):
                resolution_method = getattr(self, rule["resolution"], None)
                if resolution_method:
                    resolved = resolution_method(session, incomplete_query, rule)
                    if resolved != incomplete_query:
                        logger.info(f"Resolved query: '{incomplete_query}' -> '{resolved}'")
                        return resolved

        # Try to fill in missing context
        resolved = self._fill_missing_context(session, incomplete_query)

        return resolved

    def resolve_possessive_reference(self,
                                    session: ConversationSession,
                                    query: str,
                                    rule: dict) -> str:
        """Resolve possessive references like 'its' or 'their'."""
        # Check recent entities
        if session.current_organization:
            query = re.sub(
                r'\b(?:its|their|the)\b',
                f"{session.current_organization}'s",
                query,
                count=1
            )
        elif session.recent_systems:
            system = session.recent_systems[0]
            query = re.sub(
                r'\b(?:its|their|the)\b',
                f"{system}'s",
                query,
                count=1
            )

        return query

    def resolve_temporal_reference(self,
                                  session: ConversationSession,
                                  query: str,
                                  rule: dict) -> str:
        """Resolve temporal references."""
        if session.time_context:
            # Add time context if missing
            if not re.search(r'\b(?:yesterday|today|last|since)', query, re.I):
                time_phrase = session.time_context.get("phrase", "recently")
                query = f"{query} {time_phrase}"

        return query

    def resolve_relative_reference(self,
                                  session: ConversationSession,
                                  query: str,
                                  rule: dict) -> str:
        """Resolve relative references like 'same' or 'similar'."""
        if session.recent_systems:
            system = session.recent_systems[0]
            query = re.sub(
                r'\b(?:same|similar)\b',
                f"similar to {system}",
                query,
                count=1
            )
        elif session.recent_services:
            service = session.recent_services[0]
            query = re.sub(
                r'\b(?:related|connected)\b',
                f"connected to {service}",
                query,
                count=1
            )

        return query

    def resolve_spatial_reference(self,
                                 session: ConversationSession,
                                 query: str,
                                 rule: dict) -> str:
        """Resolve spatial references like 'there' or 'here'."""
        # Check for location context
        location_mentions = session.get_most_mentioned_entities(ContextType.LOCATION.value, 1)
        if location_mentions:
            location = location_mentions[0][0]
            query = re.sub(
                r'\b(?:there|here|this|that)\s+(?:location|site|office|datacenter)',
                location,
                query,
                count=1
            )

        return query

    def resolve_repetition_reference(self,
                                    session: ConversationSession,
                                    query: str,
                                    rule: dict) -> str:
        """Resolve repetition references like 'again' or 'repeat'."""
        if session.queries:
            # Get the last successful query
            for query_context in reversed(session.queries):
                if query_context.success:
                    return query_context.query_text

        return query

    def _fill_missing_context(self,
                             session: ConversationSession,
                             query: str) -> str:
        """Fill in missing context from session history."""
        resolved = query

        # Add organization context if missing
        if session.current_organization:
            if not re.search(r'\b(?:org|company|client|for\s+\w+)', resolved, re.I):
                # Check if query needs organization context
                if re.search(r'\b(?:show|list|get|find)\s+(?:all\s+)?(?:passwords|configs|systems)', resolved, re.I):
                    resolved = f"{resolved} for {session.current_organization}"

        # Add system context if missing
        if session.recent_systems and len(session.recent_systems) > 0:
            if not re.search(r'\b(?:server|host|system|on\s+\w+)', resolved, re.I):
                # Check if query needs system context
                if re.search(r'\b(?:services|processes|logs|metrics)', resolved, re.I):
                    resolved = f"{resolved} on {session.recent_systems[0]}"

        return resolved

    def _update_session_state(self,
                             session: ConversationSession,
                             query_context: QueryContext):
        """Update session state based on query context."""
        # Update current organization
        if ContextType.ORGANIZATION.value in query_context.entities:
            orgs = query_context.entities[ContextType.ORGANIZATION.value]
            if orgs:
                session.current_organization = orgs[0]

        # Update recent systems
        if ContextType.SYSTEM.value in query_context.entities:
            systems = query_context.entities[ContextType.SYSTEM.value]
            for system in systems:
                if system not in session.recent_systems:
                    session.recent_systems.insert(0, system)
            # Keep only recent 5 systems
            session.recent_systems = session.recent_systems[:5]

        # Update recent services
        if ContextType.SERVICE.value in query_context.entities:
            services = query_context.entities[ContextType.SERVICE.value]
            for service in services:
                if service not in session.recent_services:
                    session.recent_services.insert(0, service)
            session.recent_services = session.recent_services[:5]

        # Update time context
        if ContextType.TIMEFRAME.value in query_context.entities:
            timeframes = query_context.entities[ContextType.TIMEFRAME.value]
            if timeframes:
                session.time_context = {
                    "phrase": timeframes[0],
                    "extracted_at": datetime.now().isoformat()
                }

    def get_session_summary(self, session_id: str) -> dict[str, Any]:
        """Get a summary of the session context."""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        # Get most mentioned entities
        top_entities = {}
        for entity_type in [ContextType.ORGANIZATION, ContextType.SYSTEM, ContextType.SERVICE]:
            mentions = session.get_most_mentioned_entities(entity_type.value, 3)
            if mentions:
                top_entities[entity_type.value] = [
                    {"name": name, "count": count} for name, count in mentions
                ]

        return {
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "query_count": len(session.queries),
            "current_organization": session.current_organization,
            "recent_systems": session.recent_systems[:3],
            "recent_services": session.recent_services[:3],
            "time_context": session.time_context,
            "top_entities": top_entities,
            "active": session.active
        }

    def _cleanup_old_sessions(self, force_cleanup: bool = False):
        """Remove expired sessions."""
        now = datetime.now()
        to_remove = []

        for session_id, session in self.sessions.items():
            if now - session.last_activity > self.session_timeout:
                to_remove.append(session_id)
            elif force_cleanup and not session.active:
                to_remove.append(session_id)

        # If still over capacity after removing expired, remove oldest
        if force_cleanup and len(self.sessions) - len(to_remove) >= self.max_sessions:
            sorted_sessions = sorted(
                self.sessions.items(),
                key=lambda x: x[1].last_activity
            )
            additional_remove = len(self.sessions) - len(to_remove) - self.max_sessions + 1
            for session_id, _ in sorted_sessions[:additional_remove]:
                if session_id not in to_remove:
                    to_remove.append(session_id)

        for session_id in to_remove:
            # Persist before removing
            if session_id in self.sessions:
                self._persist_session(self.sessions[session_id])
                del self.sessions[session_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} sessions")

    def _persist_session(self, session: ConversationSession):
        """Save session to disk."""
        try:
            session_file = self.storage_path / f"{session.session_id}.json"

            # Convert session to dict for serialization
            session_dict = {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "current_organization": session.current_organization,
                "recent_systems": session.recent_systems,
                "recent_services": session.recent_services,
                "time_context": session.time_context,
                "entity_mentions": dict(session.entity_mentions),
                "user_preferences": session.user_preferences,
                "active": session.active,
                "queries": [
                    {
                        "query_text": q.query_text,
                        "timestamp": q.timestamp.isoformat(),
                        "entities": q.entities,
                        "intent": q.intent,
                        "results_count": q.results_count,
                        "success": q.success
                    }
                    for q in session.queries
                ]
            }

            with open(session_file, 'w') as f:
                json.dump(session_dict, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to persist session {session.session_id}: {e}")

    def _load_sessions(self):
        """Load persisted sessions from disk."""
        try:
            for session_file in self.storage_path.glob("*.json"):
                try:
                    with open(session_file) as f:
                        data = json.load(f)

                    # Skip old sessions
                    last_activity = datetime.fromisoformat(data["last_activity"])
                    if datetime.now() - last_activity > self.session_timeout * 2:
                        continue

                    # Reconstruct session
                    session = ConversationSession(
                        session_id=data["session_id"],
                        created_at=datetime.fromisoformat(data["created_at"]),
                        last_activity=last_activity,
                        current_organization=data.get("current_organization"),
                        recent_systems=data.get("recent_systems", []),
                        recent_services=data.get("recent_services", []),
                        time_context=data.get("time_context"),
                        user_preferences=data.get("user_preferences", {}),
                        active=data.get("active", True)
                    )

                    # Reconstruct queries
                    for query_data in data.get("queries", []):
                        query_context = QueryContext(
                            query_text=query_data["query_text"],
                            timestamp=datetime.fromisoformat(query_data["timestamp"]),
                            entities=query_data.get("entities", {}),
                            intent=query_data.get("intent"),
                            results_count=query_data.get("results_count", 0),
                            success=query_data.get("success", True)
                        )
                        session.queries.append(query_context)

                    # Reconstruct entity mentions
                    for entity_type, mentions in data.get("entity_mentions", {}).items():
                        for entity, count in mentions.items():
                            session.entity_mentions[entity_type][entity] = count

                    self.sessions[session.session_id] = session

                except Exception as e:
                    logger.warning(f"Failed to load session from {session_file}: {e}")

            logger.info(f"Loaded {len(self.sessions)} sessions from disk")

        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")

    def export_session_history(self, session_id: str) -> list[dict[str, Any]]:
        """Export session query history for analysis."""
        session = self.sessions.get(session_id)
        if not session:
            return []

        history = []
        for query_context in session.queries:
            history.append({
                "query": query_context.query_text,
                "timestamp": query_context.timestamp.isoformat(),
                "intent": query_context.intent,
                "entities": query_context.entities,
                "results_count": query_context.results_count,
                "success": query_context.success
            })

        return history
