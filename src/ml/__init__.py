"""Machine learning module for query enhancement and personalization."""

from .query_learning import (
    QueryLearningEngine,
    QueryPattern,
    QueryPersonalizer,
    UserProfile,
)
from .smart_suggestions import (
    PrefixTrie,
    QuerySuggestion,
    SessionContext,
    SmartSuggestionEngine,
    SuggestionType,
)

__all__ = [
    "QueryLearningEngine",
    "QueryPersonalizer",
    "QueryPattern",
    "UserProfile",
    "SmartSuggestionEngine",
    "QuerySuggestion",
    "SuggestionType",
    "SessionContext",
    "PrefixTrie"
]
