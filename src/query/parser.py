"""Query parsing and intent extraction."""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Types of query intents."""

    GET_ATTRIBUTE = "get_attribute"
    LIST_ENTITIES = "list_entities"
    SEARCH = "search"
    COMPARE = "compare"
    AGGREGATE = "aggregate"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class ParsedQuery:
    """Parsed query with extracted components."""

    original_query: str
    intent: QueryIntent
    entity_type: Optional[str] = None
    company: Optional[str] = None
    attributes: list[str] = None
    filters: dict[str, Any] = None
    keywords: list[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_query": self.original_query,
            "intent": self.intent.value,
            "entity_type": self.entity_type,
            "company": self.company,
            "attributes": self.attributes,
            "filters": self.filters,
            "keywords": self.keywords
        }


class QueryParser:
    """Parses natural language queries."""

    def __init__(self):
        """Initialize query parser."""
        # Entity type patterns
        self.entity_patterns = {
            "router": ["router", "routers", "routing", "gateway"],
            "server": ["server", "servers", "host", "hosts", "machine"],
            "printer": ["printer", "printers", "print", "printing"],
            "password": ["password", "passwords", "credential", "credentials", "login"],
            "configuration": ["config", "configuration", "configurations", "setup"],
            "document": ["document", "documents", "doc", "docs", "documentation"],
            "contact": ["contact", "contacts", "person", "people", "user", "users"],
            "location": ["location", "locations", "site", "sites", "office"],
            "flexible_asset": ["asset", "assets", "flexible asset"],
            "organization": ["organization", "organizations", "company", "companies", "client"]
        }

        # Attribute patterns
        self.attribute_patterns = {
            "ip": ["ip", "ip address", "address", "ipv4", "ipv6"],
            "hostname": ["hostname", "host name", "name", "fqdn"],
            "mac": ["mac", "mac address", "physical address"],
            "model": ["model", "model number", "make"],
            "serial": ["serial", "serial number", "sn"],
            "username": ["username", "user name", "user", "login"],
            "url": ["url", "link", "website", "site"],
            "email": ["email", "e-mail", "mail"],
            "phone": ["phone", "telephone", "tel", "mobile"],
            "description": ["description", "desc", "notes", "info"],
            "status": ["status", "state", "condition"],
            "type": ["type", "kind", "category"],
            "location": ["location", "where", "place", "site"]
        }

        # Intent patterns
        self.intent_patterns = {
            QueryIntent.GET_ATTRIBUTE: [
                r"what('s|'s| is| are) the",
                r"show (me )?the",
                r"get (me )?the",
                r"find (me )?the",
                r"tell me the"
            ],
            QueryIntent.LIST_ENTITIES: [
                r"list( all)?",
                r"show( me)? all",
                r"what .* (do we have|are there)",
                r"all (the )?",
                r"every "
            ],
            QueryIntent.SEARCH: [
                r"search for",
                r"find .* (with|that|having)",
                r"look for",
                r"locate"
            ],
            QueryIntent.COMPARE: [
                r"compare",
                r"difference between",
                r"versus",
                r"vs\."
            ],
            QueryIntent.AGGREGATE: [
                r"how many",
                r"count of",
                r"total",
                r"sum of",
                r"average"
            ],
            QueryIntent.HELP: [
                r"help",
                r"how (do|can) (i|we)",
                r"what can (you|this)",
                r"instructions"
            ]
        }

    def parse(self, query: str) -> ParsedQuery:
        """Parse a natural language query.

        Args:
            query: Natural language query

        Returns:
            Parsed query with extracted components
        """
        query_lower = query.lower().strip()

        # Extract intent
        intent = self._extract_intent(query_lower)

        # Extract entity type
        entity_type = self._extract_entity_type(query_lower)

        # Extract company/organization
        company = self._extract_company(query)

        # Extract attributes
        attributes = self._extract_attributes(query_lower)

        # Extract keywords
        keywords = self._extract_keywords(query_lower)

        # Build filters
        filters = self._build_filters(query_lower)

        parsed = ParsedQuery(
            original_query=query,
            intent=intent,
            entity_type=entity_type,
            company=company,
            attributes=attributes,
            filters=filters,
            keywords=keywords
        )

        logger.debug(f"Parsed query: {parsed.to_dict()}")

        return parsed

    def _extract_intent(self, query: str) -> QueryIntent:
        """Extract query intent.

        Args:
            query: Lowercase query

        Returns:
            Query intent
        """
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query):
                    return intent

        # Default intents based on keywords
        if "?" in query:
            if any(word in query for word in ["what", "where", "when", "who", "which"]):
                return QueryIntent.GET_ATTRIBUTE

        return QueryIntent.SEARCH

    def _extract_entity_type(self, query: str) -> Optional[str]:
        """Extract entity type from query.

        Args:
            query: Lowercase query

        Returns:
            Entity type or None
        """
        for entity_type, keywords in self.entity_patterns.items():
            for keyword in keywords:
                if keyword in query:
                    return entity_type

        return None

    def _extract_company(self, query: str) -> Optional[str]:
        """Extract company/organization name.

        Args:
            query: Original query (case-sensitive)

        Returns:
            Company name or None
        """
        # Common patterns for company names
        patterns = [
            r"for ([A-Z][A-Za-z0-9\s&,.-]+?)(?:\?|$|,|\s+and\s+)",
            r"at ([A-Z][A-Za-z0-9\s&,.-]+?)(?:\?|$|,|\s+and\s+)",
            r"in ([A-Z][A-Za-z0-9\s&,.-]+?)(?:\?|$|,|\s+and\s+)",
            r"([A-Z][A-Za-z0-9\s&,.-]+?)('s|'s)",
            r"company ['\"]([^'\"]+)['\"]"
        ]

        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                company = match.group(1).strip()
                # Clean up common suffixes
                company = re.sub(r'\s+(Inc|LLC|Ltd|Corp)\.?$', '', company)
                return company

        return None

    def _extract_attributes(self, query: str) -> list[str]:
        """Extract requested attributes.

        Args:
            query: Lowercase query

        Returns:
            List of attributes
        """
        attributes = []

        for attr, keywords in self.attribute_patterns.items():
            for keyword in keywords:
                if keyword in query:
                    attributes.append(attr)
                    break

        return attributes if attributes else None

    def _extract_keywords(self, query: str) -> list[str]:
        """Extract important keywords.

        Args:
            query: Lowercase query

        Returns:
            List of keywords
        """
        # Remove common stop words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "is", "are", "was", "were",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "should", "could", "may", "might", "must", "can",
            "me", "my", "we", "our", "what", "which", "who", "where", "when",
            "how", "why", "all", "each", "every", "both", "few", "more", "most",
            "other", "some", "such", "only", "own", "same", "so", "than", "too",
            "very", "just", "show", "get", "find", "list", "tell"
        }

        # Split and filter
        words = query.split()
        keywords = [
            word for word in words
            if word not in stop_words and len(word) > 2
        ]

        return keywords if keywords else None

    def _build_filters(self, query: str) -> dict[str, Any]:
        """Build filters from query.

        Args:
            query: Lowercase query

        Returns:
            Filter dictionary
        """
        filters = {}

        # Status filters
        if "active" in query:
            filters["status"] = "active"
        elif "inactive" in query:
            filters["status"] = "inactive"
        elif "disabled" in query:
            filters["status"] = "disabled"

        # Time filters
        if "recent" in query or "latest" in query:
            filters["sort"] = "updated_at_desc"
        elif "oldest" in query:
            filters["sort"] = "updated_at_asc"

        # Type filters
        if "windows" in query:
            filters["os"] = "windows"
        elif "linux" in query:
            filters["os"] = "linux"
        elif "mac" in query or "macos" in query:
            filters["os"] = "macos"

        return filters if filters else None

    def enhance_with_context(
        self,
        parsed_query: ParsedQuery,
        context: dict[str, Any]
    ) -> ParsedQuery:
        """Enhance parsed query with context.

        Args:
            parsed_query: Parsed query
            context: Additional context

        Returns:
            Enhanced parsed query
        """
        # Add company from context if not extracted
        if not parsed_query.company and "company" in context:
            parsed_query.company = context["company"]

        # Add recent entity type if ambiguous
        if not parsed_query.entity_type and "recent_entity_type" in context:
            parsed_query.entity_type = context["recent_entity_type"]

        # Merge filters
        if "filters" in context:
            if parsed_query.filters:
                parsed_query.filters.update(context["filters"])
            else:
                parsed_query.filters = context["filters"]

        return parsed_query
