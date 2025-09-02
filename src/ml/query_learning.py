"""Query learning and personalization system for predictive assistance."""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class QueryPattern:
    """Represents a learned query pattern."""
    pattern_id: str
    query_text: str
    query_type: str
    entity_types: list[str]
    success_count: int = 0
    failure_count: int = 0
    avg_execution_time: float = 0.0
    corrections: list[str] = field(default_factory=list)
    follow_up_queries: list[str] = field(default_factory=list)
    user_contexts: dict[str, int] = field(default_factory=dict)
    last_used: datetime = field(default_factory=datetime.now)
    confidence_score: float = 0.0


@dataclass
class UserProfile:
    """User-specific query preferences and patterns."""
    user_id: str
    organization_id: str
    query_history: list[dict[str, Any]] = field(default_factory=list)
    frequent_queries: list[str] = field(default_factory=list)
    preferred_entities: dict[str, int] = field(default_factory=dict)
    typical_query_types: dict[str, int] = field(default_factory=dict)
    avg_query_length: float = 0.0
    success_rate: float = 0.0
    correction_patterns: dict[str, str] = field(default_factory=dict)
    session_contexts: list[dict[str, Any]] = field(default_factory=list)
    last_activity: datetime = field(default_factory=datetime.now)


class QueryLearningEngine:
    """Machine learning engine for query pattern learning and personalization."""

    def __init__(self, storage_path: str = "./data/ml", cache_manager=None):
        """Initialize the query learning engine."""
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.cache_manager = cache_manager
        self.patterns: dict[str, QueryPattern] = {}
        self.user_profiles: dict[str, UserProfile] = {}

        # Learning parameters
        self.min_pattern_occurrences = 3
        self.pattern_confidence_threshold = 0.7
        self.max_history_size = 1000
        self.suggestion_count = 5

        # Pattern recognition settings
        self.entity_extractors = {
            "organization": r"\b(?:company|org|organization)\s+(\w+)",
            "server": r"\b(?:server|host|machine)\s+([a-zA-Z0-9\-\.]+)",
            "ip_address": r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b",
            "date": r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|yesterday|today|last\s+\w+)\b",
            "service": r"\b(?:service|application|app)\s+(\w+)",
            "user": r"\b(?:user|account)\s+(\w+)"
        }

        # Load existing patterns and profiles
        self._load_patterns()
        self._load_user_profiles()

        # Start background learning task
        self.learning_task = None

    def _load_patterns(self) -> None:
        """Load saved query patterns from storage."""
        pattern_file = self.storage_path / "query_patterns.json"
        if pattern_file.exists():
            try:
                with open(pattern_file) as f:
                    data = json.load(f)
                    for pattern_data in data:
                        pattern = QueryPattern(**pattern_data)
                        if isinstance(pattern.last_used, str):
                            pattern.last_used = datetime.fromisoformat(pattern.last_used)
                        self.patterns[pattern.pattern_id] = pattern
                logger.info(f"Loaded {len(self.patterns)} query patterns")
            except Exception as e:
                logger.error(f"Error loading patterns: {e}")

    def _load_user_profiles(self) -> None:
        """Load saved user profiles from storage."""
        profile_file = self.storage_path / "user_profiles.json"
        if profile_file.exists():
            try:
                with open(profile_file) as f:
                    data = json.load(f)
                    for profile_data in data:
                        profile = UserProfile(**profile_data)
                        if isinstance(profile.last_activity, str):
                            profile.last_activity = datetime.fromisoformat(profile.last_activity)
                        self.user_profiles[profile.user_id] = profile
                logger.info(f"Loaded {len(self.user_profiles)} user profiles")
            except Exception as e:
                logger.error(f"Error loading profiles: {e}")

    def _save_patterns(self) -> None:
        """Save query patterns to storage."""
        pattern_file = self.storage_path / "query_patterns.json"
        try:
            patterns_data = []
            for pattern in self.patterns.values():
                pattern_dict = asdict(pattern)
                pattern_dict['last_used'] = pattern.last_used.isoformat()
                patterns_data.append(pattern_dict)

            with open(pattern_file, 'w') as f:
                json.dump(patterns_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving patterns: {e}")

    def _save_user_profiles(self) -> None:
        """Save user profiles to storage."""
        profile_file = self.storage_path / "user_profiles.json"
        try:
            profiles_data = []
            for profile in self.user_profiles.values():
                profile_dict = asdict(profile)
                profile_dict['last_activity'] = profile.last_activity.isoformat()
                profiles_data.append(profile_dict)

            with open(profile_file, 'w') as f:
                json.dump(profiles_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving profiles: {e}")

    async def record_query(self, query_data: dict[str, Any]) -> None:
        """Record a query for learning purposes."""
        user_id = query_data.get('user_id', 'anonymous')
        query_text = query_data.get('query_text', '')
        query_type = query_data.get('query_type', 'unknown')
        success = query_data.get('success', False)
        execution_time = query_data.get('execution_time', 0.0)
        organization_id = query_data.get('organization_id', '')

        # Update user profile
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile(
                user_id=user_id,
                organization_id=organization_id
            )

        profile = self.user_profiles[user_id]

        # Add to query history
        profile.query_history.append({
            'query': query_text,
            'type': query_type,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'execution_time': execution_time
        })

        # Limit history size
        if len(profile.query_history) > self.max_history_size:
            profile.query_history = profile.query_history[-self.max_history_size:]

        # Update profile statistics
        profile.typical_query_types[query_type] = profile.typical_query_types.get(query_type, 0) + 1
        profile.last_activity = datetime.now()

        # Extract entities and update preferences
        entities = self._extract_entities(query_text)
        for entity_type, entity_values in entities.items():
            for value in entity_values:
                key = f"{entity_type}:{value}"
                profile.preferred_entities[key] = profile.preferred_entities.get(key, 0) + 1

        # Update or create pattern
        pattern_id = self._generate_pattern_id(query_text, query_type)
        if pattern_id not in self.patterns:
            self.patterns[pattern_id] = QueryPattern(
                pattern_id=pattern_id,
                query_text=query_text,
                query_type=query_type,
                entity_types=list(entities.keys())
            )

        pattern = self.patterns[pattern_id]
        if success:
            pattern.success_count += 1
        else:
            pattern.failure_count += 1

        # Update average execution time
        total_executions = pattern.success_count + pattern.failure_count
        pattern.avg_execution_time = (
            (pattern.avg_execution_time * (total_executions - 1) + execution_time) / total_executions
        )

        pattern.last_used = datetime.now()
        pattern.user_contexts[user_id] = pattern.user_contexts.get(user_id, 0) + 1

        # Calculate pattern confidence
        pattern.confidence_score = self._calculate_confidence(pattern)

        # Save periodically
        if len(profile.query_history) % 10 == 0:
            self._save_patterns()
            self._save_user_profiles()

    async def get_suggestions(self, partial_query: str, user_id: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Get query suggestions based on partial input and user context."""
        suggestions = []

        # Get user profile
        profile = self.user_profiles.get(user_id)
        if not profile:
            return self._get_default_suggestions(partial_query)

        # Find matching patterns
        matching_patterns = self._find_matching_patterns(partial_query, profile)

        # Score and rank patterns
        scored_patterns = []
        for pattern in matching_patterns:
            score = self._score_pattern(pattern, profile, context)
            scored_patterns.append((score, pattern))

        # Sort by score
        scored_patterns.sort(key=lambda x: x[0], reverse=True)

        # Build suggestions
        for score, pattern in scored_patterns[:self.suggestion_count]:
            suggestion = {
                'query': pattern.query_text,
                'type': pattern.query_type,
                'confidence': score,
                'avg_execution_time': pattern.avg_execution_time,
                'success_rate': pattern.success_count / max(1, pattern.success_count + pattern.failure_count),
                'entities': self._extract_entities(pattern.query_text)
            }
            suggestions.append(suggestion)

        # Add contextual suggestions
        contextual_suggestions = await self._get_contextual_suggestions(
            partial_query, profile, context
        )
        suggestions.extend(contextual_suggestions)

        # Deduplicate and limit
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            query_key = suggestion['query'].lower()
            if query_key not in seen:
                seen.add(query_key)
                unique_suggestions.append(suggestion)

        return unique_suggestions[:self.suggestion_count]

    async def record_correction(self, original_query: str, corrected_query: str, user_id: str) -> None:
        """Record a query correction for learning."""
        if user_id in self.user_profiles:
            profile = self.user_profiles[user_id]
            profile.correction_patterns[original_query] = corrected_query

            # Find and update pattern
            original_pattern_id = self._generate_pattern_id(original_query, 'unknown')
            if original_pattern_id in self.patterns:
                pattern = self.patterns[original_pattern_id]
                if corrected_query not in pattern.corrections:
                    pattern.corrections.append(corrected_query)

    async def record_follow_up(self, original_query: str, follow_up_query: str, user_id: str) -> None:
        """Record a follow-up query for pattern learning."""
        pattern_id = self._generate_pattern_id(original_query, 'unknown')
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            if follow_up_query not in pattern.follow_up_queries:
                pattern.follow_up_queries.append(follow_up_query)

    def _extract_entities(self, query: str) -> dict[str, list[str]]:
        """Extract entities from query text."""
        import re
        entities = {}

        for entity_type, pattern in self.entity_extractors.items():
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches

        return entities

    def _generate_pattern_id(self, query: str, query_type: str) -> str:
        """Generate unique pattern ID."""
        # Normalize query
        normalized = query.lower().strip()
        # Remove numbers and special chars for pattern matching
        normalized = ''.join(c if c.isalpha() or c.isspace() else ' ' for c in normalized)
        normalized = ' '.join(normalized.split())

        # Create hash
        pattern_str = f"{query_type}:{normalized}"
        return hashlib.md5(pattern_str.encode()).hexdigest()[:16]

    def _calculate_confidence(self, pattern: QueryPattern) -> float:
        """Calculate confidence score for a pattern."""
        total = pattern.success_count + pattern.failure_count
        if total < self.min_pattern_occurrences:
            return 0.0

        success_rate = pattern.success_count / total
        recency_factor = 1.0 / (1 + (datetime.now() - pattern.last_used).days / 7)
        usage_factor = min(1.0, total / 20)  # Cap at 20 uses

        confidence = (success_rate * 0.5 + recency_factor * 0.3 + usage_factor * 0.2)
        return min(1.0, confidence)

    def _find_matching_patterns(self, partial_query: str, profile: UserProfile) -> list[QueryPattern]:
        """Find patterns matching partial query."""
        matching = []
        partial_lower = partial_query.lower()

        for pattern in self.patterns.values():
            # Check if pattern matches partial query
            if pattern.query_text.lower().startswith(partial_lower):
                matching.append(pattern)
            # Check corrections
            elif any(corr.lower().startswith(partial_lower) for corr in pattern.corrections):
                matching.append(pattern)
            # Check user's frequent patterns
            elif pattern.pattern_id in [self._generate_pattern_id(q['query'], q['type'])
                                       for q in profile.query_history[-20:]]:
                if self._fuzzy_match(partial_lower, pattern.query_text.lower()):
                    matching.append(pattern)

        return matching

    def _score_pattern(self, pattern: QueryPattern, profile: UserProfile, context: dict[str, Any]) -> float:
        """Score a pattern based on user profile and context."""
        score = pattern.confidence_score

        # User preference bonus
        if pattern.query_type in profile.typical_query_types:
            type_frequency = profile.typical_query_types[pattern.query_type]
            total_queries = sum(profile.typical_query_types.values())
            preference_ratio = type_frequency / max(1, total_queries)
            score += preference_ratio * 0.2

        # Context relevance bonus
        context_org = context.get('organization_id')
        if context_org and profile.organization_id == context_org:
            score += 0.1

        # Recency bonus
        if profile.user_id in pattern.user_contexts:
            recent_uses = pattern.user_contexts[profile.user_id]
            score += min(0.2, recent_uses * 0.02)

        # Entity match bonus
        query_entities = self._extract_entities(pattern.query_text)
        for entity_type, values in query_entities.items():
            for value in values:
                key = f"{entity_type}:{value}"
                if key in profile.preferred_entities:
                    score += 0.05

        return min(1.0, score)

    def _fuzzy_match(self, str1: str, str2: str, threshold: float = 0.7) -> bool:
        """Simple fuzzy string matching."""
        # Levenshtein distance ratio
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, str1, str2).ratio()
        return ratio >= threshold

    def _get_default_suggestions(self, partial_query: str) -> list[dict[str, Any]]:
        """Get default suggestions when no user profile exists."""
        defaults = [
            {
                'query': 'show all servers for ',
                'type': 'list',
                'confidence': 0.5
            },
            {
                'query': 'find password for ',
                'type': 'password',
                'confidence': 0.5
            },
            {
                'query': 'what changed on ',
                'type': 'audit',
                'confidence': 0.5
            },
            {
                'query': 'show configuration for ',
                'type': 'configuration',
                'confidence': 0.5
            },
            {
                'query': 'troubleshoot issue with ',
                'type': 'troubleshooting',
                'confidence': 0.5
            }
        ]

        # Filter by partial query
        return [s for s in defaults if s['query'].startswith(partial_query.lower())][:3]

    async def _get_contextual_suggestions(self, partial_query: str, profile: UserProfile,
                                         context: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate contextual suggestions based on recent activity."""
        suggestions = []

        # Check recent queries for follow-up patterns
        if len(profile.query_history) > 0:
            last_query = profile.query_history[-1]
            last_pattern_id = self._generate_pattern_id(last_query['query'], last_query['type'])

            if last_pattern_id in self.patterns:
                pattern = self.patterns[last_pattern_id]
                for follow_up in pattern.follow_up_queries[:2]:
                    if follow_up.lower().startswith(partial_query.lower()):
                        suggestions.append({
                            'query': follow_up,
                            'type': 'follow_up',
                            'confidence': 0.7,
                            'context': 'Based on previous query'
                        })

        # Add time-based suggestions
        current_hour = datetime.now().hour
        if 0 <= current_hour < 12:
            time_context = "morning"
        elif 12 <= current_hour < 17:
            time_context = "afternoon"
        else:
            time_context = "evening"

        # Common patterns by time of day
        time_patterns = {
            "morning": ["check overnight alerts", "review backup status"],
            "afternoon": ["investigate performance issues", "check service health"],
            "evening": ["prepare maintenance tasks", "review daily changes"]
        }

        for pattern in time_patterns.get(time_context, []):
            if pattern.startswith(partial_query.lower()):
                suggestions.append({
                    'query': pattern,
                    'type': 'contextual',
                    'confidence': 0.6,
                    'context': f'Common {time_context} query'
                })

        return suggestions

    async def get_personalization_stats(self, user_id: str) -> dict[str, Any]:
        """Get personalization statistics for a user."""
        if user_id not in self.user_profiles:
            return {'personalized': False}

        profile = self.user_profiles[user_id]

        # Calculate statistics
        total_queries = len(profile.query_history)
        successful_queries = sum(1 for q in profile.query_history if q.get('success', False))
        success_rate = successful_queries / max(1, total_queries)

        # Most frequent query types
        top_types = sorted(
            profile.typical_query_types.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        # Most used entities
        top_entities = sorted(
            profile.preferred_entities.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        # Average query characteristics
        if profile.query_history:
            query_lengths = [len(q['query'].split()) for q in profile.query_history]
            avg_length = sum(query_lengths) / len(query_lengths)

            exec_times = [q.get('execution_time', 0) for q in profile.query_history]
            avg_exec_time = sum(exec_times) / len(exec_times)
        else:
            avg_length = 0
            avg_exec_time = 0

        return {
            'personalized': True,
            'total_queries': total_queries,
            'success_rate': success_rate,
            'top_query_types': top_types,
            'top_entities': top_entities,
            'avg_query_length': avg_length,
            'avg_execution_time': avg_exec_time,
            'correction_count': len(profile.correction_patterns),
            'last_activity': profile.last_activity.isoformat()
        }

    async def start_background_learning(self) -> None:
        """Start background learning task."""
        async def learn_patterns():
            while True:
                try:
                    # Analyze patterns every hour
                    await asyncio.sleep(3600)
                    await self._analyze_patterns()
                    self._save_patterns()
                    self._save_user_profiles()
                except Exception as e:
                    logger.error(f"Error in background learning: {e}")

        self.learning_task = asyncio.create_task(learn_patterns())

    async def _analyze_patterns(self) -> None:
        """Analyze and optimize learned patterns."""
        # Remove old patterns
        cutoff_date = datetime.now() - timedelta(days=30)
        old_patterns = [
            pid for pid, pattern in self.patterns.items()
            if pattern.last_used < cutoff_date and pattern.confidence_score < 0.5
        ]

        for pattern_id in old_patterns:
            del self.patterns[pattern_id]

        if old_patterns:
            logger.info(f"Removed {len(old_patterns)} old patterns")

        # Merge similar patterns
        merged_count = self._merge_similar_patterns()
        if merged_count > 0:
            logger.info(f"Merged {merged_count} similar patterns")

        # Update pattern relationships
        self._update_pattern_relationships()

    def _merge_similar_patterns(self) -> int:
        """Merge similar patterns to reduce redundancy."""
        merged = 0
        pattern_list = list(self.patterns.values())

        for i, pattern1 in enumerate(pattern_list):
            for pattern2 in pattern_list[i+1:]:
                if self._fuzzy_match(pattern1.query_text, pattern2.query_text, 0.9):
                    # Merge pattern2 into pattern1
                    pattern1.success_count += pattern2.success_count
                    pattern1.failure_count += pattern2.failure_count
                    pattern1.corrections.extend(pattern2.corrections)
                    pattern1.follow_up_queries.extend(pattern2.follow_up_queries)

                    # Remove duplicates
                    pattern1.corrections = list(set(pattern1.corrections))
                    pattern1.follow_up_queries = list(set(pattern1.follow_up_queries))

                    # Remove pattern2
                    if pattern2.pattern_id in self.patterns:
                        del self.patterns[pattern2.pattern_id]
                        merged += 1

        return merged

    def _update_pattern_relationships(self) -> None:
        """Update relationships between patterns based on usage."""
        for user_profile in self.user_profiles.values():
            if len(user_profile.query_history) < 2:
                continue

            # Find sequential patterns
            for i in range(len(user_profile.query_history) - 1):
                query1 = user_profile.query_history[i]
                query2 = user_profile.query_history[i + 1]

                pattern1_id = self._generate_pattern_id(query1['query'], query1['type'])
                pattern2_id = self._generate_pattern_id(query2['query'], query2['type'])

                if pattern1_id in self.patterns and pattern2_id in self.patterns:
                    pattern1 = self.patterns[pattern1_id]
                    if query2['query'] not in pattern1.follow_up_queries:
                        pattern1.follow_up_queries.append(query2['query'])


class QueryPersonalizer:
    """High-level interface for query personalization."""

    def __init__(self, learning_engine: QueryLearningEngine):
        """Initialize the personalizer."""
        self.learning_engine = learning_engine
        self.active_sessions: dict[str, dict[str, Any]] = {}

    async def personalize_query(self, query: str, user_id: str, context: dict[str, Any]) -> dict[str, Any]:
        """Personalize a query based on user patterns."""
        # Get suggestions
        suggestions = await self.learning_engine.get_suggestions(query, user_id, context)

        # Get user stats
        stats = await self.learning_engine.get_personalization_stats(user_id)

        # Build personalized response
        response = {
            'original_query': query,
            'suggestions': suggestions,
            'user_stats': stats,
            'personalization_applied': len(suggestions) > 0
        }

        # Apply corrections if available
        if user_id in self.learning_engine.user_profiles:
            profile = self.learning_engine.user_profiles[user_id]
            if query in profile.correction_patterns:
                response['suggested_correction'] = profile.correction_patterns[query]

        return response

    async def start_session(self, user_id: str, organization_id: str) -> str:
        """Start a personalized session."""
        session_id = hashlib.md5(f"{user_id}:{time.time()}".encode()).hexdigest()[:16]

        self.active_sessions[session_id] = {
            'user_id': user_id,
            'organization_id': organization_id,
            'start_time': datetime.now(),
            'query_count': 0,
            'context': {}
        }

        return session_id

    async def end_session(self, session_id: str) -> dict[str, Any]:
        """End a session and return session statistics."""
        if session_id not in self.active_sessions:
            return {'error': 'Session not found'}

        session = self.active_sessions[session_id]
        duration = (datetime.now() - session['start_time']).total_seconds()

        stats = {
            'session_id': session_id,
            'duration_seconds': duration,
            'query_count': session['query_count'],
            'user_id': session['user_id']
        }

        del self.active_sessions[session_id]
        return stats

    async def update_session_context(self, session_id: str, context: dict[str, Any]) -> None:
        """Update session context for better personalization."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['context'].update(context)


# Export main classes
__all__ = ["QueryLearningEngine", "QueryPersonalizer", "QueryPattern", "UserProfile"]
