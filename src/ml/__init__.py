"""Machine learning module for query enhancement and personalization."""

from .query_learning import (
    QueryLearningEngine,
    QueryPersonalizer,
    QueryPattern,
    UserProfile
)
from .smart_suggestions import (
    SmartSuggestionEngine,
    QuerySuggestion,
    SuggestionType,
    SessionContext,
    PrefixTrie
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