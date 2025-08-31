"""Fuzzy matching system for IT Glue entity resolution."""

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

import jellyfish  # For phonetic matching

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of a fuzzy match operation."""
    original: str
    matched: str
    score: float
    match_type: str  # 'exact', 'fuzzy', 'phonetic', 'acronym', 'partial'
    confidence: float
    entity_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass
class EnhancedMatchResult(MatchResult):
    """Enhanced result with performance metrics."""
    match_time_ms: float = 0  # Performance tracking
    from_cache: bool = False  # Cache hit indicator


class FuzzyMatcher:
    """Advanced fuzzy matching for IT Glue entities."""

    def __init__(self, cache_manager=None):
        """Initialize fuzzy matcher with IT-specific knowledge."""
        self.cache_manager = cache_manager
        self.dict_cache = {}  # In-memory cache for dictionaries
        self.organization_cache = {}

        # Load dictionaries with JSON fallback
        self.acronym_map = self._build_acronym_map()
        self.common_mistakes = self._load_or_build_mistakes()
        self.it_terms = self._load_or_build_it_dictionary()
        self.abbreviation_patterns = self._build_abbreviation_patterns()
        self.company_aliases = self._load_company_aliases()

        # Performance metrics
        self.cache_hits = 0
        self.cache_misses = 0

    def _build_acronym_map(self) -> dict[str, list[str]]:
        """Build IT industry acronym mappings."""
        return {
            # Company acronyms
            "ms": ["microsoft", "morgan stanley"],
            "ibm": ["international business machines"],
            "hp": ["hewlett packard", "hp inc", "hp enterprise"],
            "ge": ["general electric"],
            "aws": ["amazon web services"],
            "gcp": ["google cloud platform"],
            "ad": ["active directory"],

            # Technical acronyms
            "db": ["database"],
            "dc": ["domain controller", "data center"],
            "vm": ["virtual machine"],
            "vpn": ["virtual private network"],
            "ssl": ["secure sockets layer"],
            "sql": ["structured query language"],
            "api": ["application programming interface"],
            "dns": ["domain name system"],
            "dhcp": ["dynamic host configuration protocol"],
            "nas": ["network attached storage"],
            "san": ["storage area network"],
            "wan": ["wide area network"],
            "lan": ["local area network"]
        }

    def _load_or_build_mistakes(self) -> dict[str, str]:
        """Load common mistakes from JSON or build from hardcoded values."""
        # Try to load from JSON file first
        dict_path = Path(__file__).parent / "dictionaries" / "it_terms.json"
        if dict_path.exists():
            try:
                with open(dict_path) as f:
                    external_dict = json.load(f)
                    # Merge with hardcoded for backward compatibility
                    hardcoded = self._build_common_mistakes()
                    logger.info(f"Loaded {len(external_dict)} terms from {dict_path}")
                    return {**hardcoded, **external_dict}
            except Exception as e:
                logger.warning(f"Failed to load external dictionary: {e}")

        # Fallback to hardcoded
        return self._build_common_mistakes()

    def _build_common_mistakes(self) -> dict[str, str]:
        """Build common spelling mistakes in IT context."""
        return {
            # Company names
            "microsft": "microsoft",
            "mikrosoft": "microsoft",
            "amazone": "amazon",
            "goggle": "google",
            "oracal": "oracle",

            # Technical terms
            "pasword": "password",
            "windoes": "windows",
            "windws": "windows",
            "ubunto": "ubuntu",
            "ubunu": "ubuntu",
            "centos": "centos",
            "postgress": "postgresql",
            "postgre": "postgresql",
            "maria db": "mariadb",
            "my sql": "mysql",
            "kubernets": "kubernetes",
            "kubernetees": "kubernetes",
            "dockar": "docker",
            "jenkin": "jenkins",
            "nagix": "nginx",
            "appache": "apache",
            "tomcatt": "tomcat",
            "vmwear": "vmware",
            "vitualbox": "virtualbox",
            "hiperv": "hyper-v",
            "hypervisr": "hypervisor",

            # Common IT typos
            "sever": "server",
            "sevrer": "server",
            "databse": "database",
            "netwrok": "network",
            "firewal": "firewall",
            "bacup": "backup",
            "restoe": "restore",
            "moniter": "monitor",
            "dashbord": "dashboard",
            "configuation": "configuration"
        }

    def _load_or_build_it_dictionary(self) -> set:
        """Load IT dictionary from JSON or build from hardcoded values."""
        # Try to load from JSON file first
        dict_path = Path(__file__).parent / "dictionaries" / "it_dictionary.json"
        if dict_path.exists():
            try:
                with open(dict_path) as f:
                    external_terms = json.load(f)
                    if isinstance(external_terms, list):
                        external_terms = set(external_terms)
                    # Merge with hardcoded
                    hardcoded = self._build_it_dictionary()
                    logger.info(f"Loaded {len(external_terms)} IT terms from {dict_path}")
                    return hardcoded | external_terms
            except Exception as e:
                logger.warning(f"Failed to load IT dictionary: {e}")

        # Fallback to hardcoded
        return self._build_it_dictionary()

    def _build_it_dictionary(self) -> set:
        """Build IT-specific term dictionary."""
        return {
            # Infrastructure
            "server", "workstation", "laptop", "desktop", "router", "switch",
            "firewall", "load balancer", "proxy", "gateway", "access point",

            # Software
            "windows", "linux", "ubuntu", "centos", "redhat", "debian",
            "macos", "vmware", "docker", "kubernetes", "openstack",
            "office365", "azure", "aws", "google cloud",

            # Services
            "active directory", "dns", "dhcp", "smtp", "imap", "pop3",
            "http", "https", "ftp", "sftp", "ssh", "rdp", "vnc",

            # Databases
            "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
            "mssql", "oracle", "mariadb", "cassandra", "dynamodb"
        }

    def _build_abbreviation_patterns(self) -> dict[str, str]:
        """Build company suffix patterns."""
        return {
            "incorporated": "inc",
            "corporation": "corp",
            "limited": "ltd",
            "company": "co",
            "enterprises": "ent",
            "solutions": "sol",
            "services": "svc",
            "technologies": "tech",
            "systems": "sys",
            "associates": "assoc",
            "partners": "ptr",
            "group": "grp",
            "international": "intl",
            "& associates": "& assoc",
            "and associates": "& assoc"
        }

    def _load_company_aliases(self) -> dict[str, list[str]]:
        """Load company aliases from JSON file."""
        dict_path = Path(__file__).parent / "dictionaries" / "company_aliases.json"
        if dict_path.exists():
            try:
                with open(dict_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load company aliases: {e}")
        return {}

    def reload_dictionaries(self) -> None:
        """Reload dictionaries from files without restart."""
        logger.info("Reloading dictionaries...")
        self.common_mistakes = self._load_or_build_mistakes()
        self.it_terms = self._load_or_build_it_dictionary()
        self.company_aliases = self._load_company_aliases()
        self.dict_cache.clear()  # Clear cache after reload
        logger.info("Dictionaries reloaded successfully")

    async def match_organization_cached(
        self,
        input_name: str,
        candidates: list[dict[str, str]],
        threshold: float = 0.7
    ) -> list[EnhancedMatchResult]:
        """Match organization with caching support."""
        if not self.cache_manager:
            # No cache, use regular matching
            start_time = time.perf_counter()
            results = self.match_organization(input_name, candidates, threshold)
            match_time = (time.perf_counter() - start_time) * 1000
            return [
                EnhancedMatchResult(
                    **r.__dict__,
                    match_time_ms=match_time,
                    from_cache=False
                )
                for r in results
            ]

        # Generate cache key
        candidates_hash = hashlib.md5(
            str(sorted([c['id'] for c in candidates])).encode()
        ).hexdigest()
        cache_key = f"fuzzy:{input_name}:{candidates_hash}:{threshold}"

        # Check cache
        cached = await self.cache_manager.get(cache_key)
        if cached:
            self.cache_hits += 1
            return [
                EnhancedMatchResult(**r, from_cache=True)
                for r in json.loads(cached)
            ]

        self.cache_misses += 1

        # Perform matching
        start_time = time.perf_counter()
        results = self.match_organization(input_name, candidates, threshold)
        match_time = (time.perf_counter() - start_time) * 1000

        # Enhance results
        enhanced = [
            EnhancedMatchResult(
                **r.__dict__,
                match_time_ms=match_time,
                from_cache=False
            )
            for r in results
        ]

        # Cache results
        await self.cache_manager.set(
            cache_key,
            json.dumps([{
                'original': r.original,
                'matched': r.matched,
                'score': r.score,
                'match_type': r.match_type,
                'confidence': r.confidence,
                'entity_id': r.entity_id,
                'metadata': r.metadata,
                'match_time_ms': r.match_time_ms
            } for r in enhanced]),
            ttl=3600  # 1 hour cache
        )

        return enhanced

    def match_organization(
        self,
        input_name: str,
        candidates: list[dict[str, str]],
        threshold: float = 0.7
    ) -> list[MatchResult]:
        """
        Match input organization name against candidates.

        Args:
            input_name: User input organization name
            candidates: List of candidate organizations with 'name' and 'id'
            threshold: Minimum similarity threshold

        Returns:
            Sorted list of match results
        """
        input_normalized = self._normalize_organization(input_name)
        results = []

        for candidate in candidates:
            candidate_name = candidate.get('name', '')
            candidate_normalized = self._normalize_organization(candidate_name)

            # Try different matching strategies
            strategies = [
                ('exact', self._exact_match),
                ('fuzzy', self._fuzzy_match),
                ('phonetic', self._phonetic_match),
                ('acronym', self._acronym_match),
                ('partial', self._partial_match)
            ]

            best_score = 0
            best_type = None

            for match_type, match_func in strategies:
                score = match_func(input_normalized, candidate_normalized)
                if score > best_score:
                    best_score = score
                    best_type = match_type

            if best_score >= threshold:
                results.append(MatchResult(
                    original=input_name,
                    matched=candidate_name,
                    score=best_score,
                    match_type=best_type,
                    confidence=self._calculate_confidence(best_score, best_type),
                    entity_id=candidate.get('id'),
                    metadata={'normalized': candidate_normalized}
                ))

        # Sort by score descending
        results.sort(key=lambda x: (x.score, x.confidence), reverse=True)
        return results[:5]  # Return top 5 matches

    def _normalize_organization(self, name: str) -> str:
        """Normalize organization name for matching."""
        if not name:
            return ""

        normalized = name.lower().strip()

        # Apply common corrections
        for mistake, correction in self.common_mistakes.items():
            normalized = normalized.replace(mistake, correction)

        # Normalize abbreviations
        for long_form, short_form in self.abbreviation_patterns.items():
            normalized = normalized.replace(long_form, short_form)

        # Remove special characters but keep spaces
        normalized = re.sub(r'[^\w\s&-]', '', normalized)

        # Normalize whitespace
        normalized = ' '.join(normalized.split())

        return normalized

    def _exact_match(self, input_str: str, candidate: str) -> float:
        """Check for exact match with early termination."""
        if input_str == candidate:
            return 1.0
        # Check company aliases
        if input_str in self.company_aliases:
            if candidate in self.company_aliases[input_str]:
                return 0.95
        return 0.0

    def _fuzzy_match(self, input_str: str, candidate: str) -> float:
        """Calculate fuzzy similarity using SequenceMatcher."""
        return SequenceMatcher(None, input_str, candidate).ratio()

    def _phonetic_match(self, input_str: str, candidate: str) -> float:
        """Calculate phonetic similarity using multiple algorithms."""
        if not input_str or not candidate:
            return 0.0

        try:
            # Use Double Metaphone for better phonetic matching
            input_metaphone = jellyfish.metaphone(input_str)
            candidate_metaphone = jellyfish.metaphone(candidate)

            # Handle None returns from jellyfish
            if input_metaphone is None or candidate_metaphone is None:
                return 0.0

            if input_metaphone == candidate_metaphone:
                return 0.9  # High score but not perfect

            # Try Soundex as fallback
            try:
                input_soundex = jellyfish.soundex(input_str)
                candidate_soundex = jellyfish.soundex(candidate)

                if input_soundex == candidate_soundex:
                    return 0.85
            except:
                pass

            # Partial phonetic match
            return SequenceMatcher(None, input_metaphone, candidate_metaphone).ratio() * 0.8
        except Exception as e:
            logger.debug(f"Phonetic matching error: {e}")
            return 0.0

    def _acronym_match(self, input_str: str, candidate: str) -> float:
        """Check if input is an acronym of candidate."""
        input_lower = input_str.lower()

        # Check acronym map
        if input_lower in self.acronym_map:
            for expansion in self.acronym_map[input_lower]:
                if expansion in candidate.lower():
                    return 0.95

        # Check if input could be acronym of candidate
        words = candidate.split()
        if len(words) > 1:
            acronym = ''.join(w[0] for w in words if w)
            if input_lower == acronym.lower():
                return 0.85

        return 0.0

    def _partial_match(self, input_str: str, candidate: str) -> float:
        """Check for partial/substring match."""
        if not input_str or not candidate:
            return 0.0

        # Check if input is substring of candidate or vice versa
        if input_str in candidate:
            return len(input_str) / len(candidate) * 0.9
        elif candidate in input_str:
            return len(candidate) / len(input_str) * 0.9

        # Check word-level partial match
        input_words = set(input_str.split())
        candidate_words = set(candidate.split())

        if input_words and candidate_words:
            intersection = input_words & candidate_words
            union = input_words | candidate_words
            if union:
                return len(intersection) / len(union) * 0.8

        return 0.0

    def _calculate_confidence(self, score: float, match_type: str) -> float:
        """Calculate confidence based on score and match type."""
        confidence_multipliers = {
            'exact': 1.0,
            'fuzzy': 0.9,
            'phonetic': 0.8,
            'acronym': 0.85,
            'partial': 0.7
        }

        base_confidence = score * confidence_multipliers.get(match_type, 0.5)

        # Boost confidence for very high scores
        if score > 0.95:
            base_confidence = min(1.0, base_confidence * 1.1)

        return min(1.0, base_confidence)

    def suggest_correction(self, input_text: str) -> list[str]:
        """Suggest corrections for input text."""
        suggestions = []
        words = input_text.lower().split()

        for word in words:
            # Check common mistakes
            if word in self.common_mistakes:
                suggestions.append(self.common_mistakes[word])
            # Check IT dictionary
            elif word not in self.it_terms:
                # Find closest match in IT terms
                best_match = None
                best_score = 0
                for term in self.it_terms:
                    score = SequenceMatcher(None, word, term).ratio()
                    if score > best_score and score > 0.8:
                        best_score = score
                        best_match = term
                if best_match:
                    suggestions.append(best_match)

        return suggestions

    def get_cache_stats(self) -> dict[str, Any]:
        """Get fuzzy matcher cache statistics."""
        hit_rate = (
            self.cache_hits / (self.cache_hits + self.cache_misses)
            if (self.cache_hits + self.cache_misses) > 0
            else 0
        )

        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': hit_rate,
            'dict_cache_size': len(self.dict_cache),
            'org_cache_size': len(self.organization_cache),
            'common_mistakes_count': len(self.common_mistakes),
            'it_terms_count': len(self.it_terms)
        }


class QueryFuzzyEnhancer:
    """Enhance queries with fuzzy matching capabilities."""

    def __init__(self, fuzzy_matcher: FuzzyMatcher):
        """Initialize query enhancer."""
        self.fuzzy_matcher = fuzzy_matcher
        self.query_patterns = self._build_query_patterns()

    def _build_query_patterns(self) -> list[tuple[re.Pattern, str]]:
        """Build common query patterns."""
        return [
            (re.compile(r'show\s+(?:me\s+)?all\s+(\w+)\s+for\s+(.+)', re.I), 'list_assets'),
            (re.compile(r'get\s+(\w+)\s+(?:for|of)\s+(.+)', re.I), 'get_entity'),
            (re.compile(r'find\s+(\w+)\s+(?:in|at|for)\s+(.+)', re.I), 'search_entity'),
            (re.compile(r'list\s+(\w+)\s+(?:for|in)\s+(.+)', re.I), 'list_entity'),
            (re.compile(r'what\s+(\w+)\s+does\s+(.+)\s+have', re.I), 'query_assets'),
        ]

    def enhance_query(
        self,
        query: str,
        known_entities: dict[str, list[dict[str, str]]]
    ) -> dict[str, Any]:
        """
        Enhance query with fuzzy matched entities.

        Args:
            query: Raw user query
            known_entities: Dictionary of entity types to known entities

        Returns:
            Enhanced query with matched entities and corrections
        """
        enhanced = {
            'original': query,
            'corrected': query,
            'entities': {},
            'suggestions': [],
            'intent': None
        }

        # Detect query pattern and extract entities
        for pattern, intent in self.query_patterns:
            match = pattern.match(query)
            if match:
                enhanced['intent'] = intent

                # Extract potential organization name
                if len(match.groups()) >= 2:
                    org_input = match.group(2)

                    # Try to match organization
                    if 'organizations' in known_entities:
                        matches = self.fuzzy_matcher.match_organization(
                            org_input,
                            known_entities['organizations']
                        )

                        if matches:
                            best_match = matches[0]
                            enhanced['entities']['organization'] = {
                                'input': org_input,
                                'matched': best_match.matched,
                                'confidence': best_match.confidence,
                                'alternatives': [
                                    {'name': m.matched, 'score': m.score}
                                    for m in matches[1:3]
                                ]
                            }

                            # Update corrected query
                            enhanced['corrected'] = query.replace(
                                org_input,
                                best_match.matched
                            )
                break

        # Suggest corrections for unknown words
        suggestions = self.fuzzy_matcher.suggest_correction(query)
        if suggestions:
            enhanced['suggestions'] = suggestions

        return enhanced
