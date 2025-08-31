"""Fuzzy query enhancer for intelligent query processing."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import re
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


class FuzzyMatchType(Enum):
    """Types of fuzzy matching strategies."""
    EXACT = "exact"
    LEVENSHTEIN = "levenshtein"
    PHONETIC = "phonetic"
    PREFIX = "prefix"
    SUBSTRING = "substring"
    ACRONYM = "acronym"
    TYPO_CORRECTION = "typo_correction"


@dataclass
class FuzzyMatch:
    """Represents a fuzzy match result."""
    original: str
    matched: str
    confidence: float
    match_type: FuzzyMatchType
    metadata: Dict[str, Any]


@dataclass
class EnhancedQuery:
    """Query enhanced with fuzzy matching capabilities."""
    original_query: str
    enhanced_query: str
    fuzzy_matches: List[FuzzyMatch]
    confidence: float
    fallback_to_exact: bool
    metadata: Dict[str, Any]


class QueryFuzzyEnhancer:
    """Enhance queries with fuzzy matching capabilities."""
    
    def __init__(
        self,
        min_confidence: float = 0.7,
        enable_typo_correction: bool = True,
        enable_phonetic: bool = True,
        enable_acronyms: bool = True,
        preserve_exact_match: bool = True
    ):
        """
        Initialize fuzzy enhancer.
        
        Args:
            min_confidence: Minimum confidence score for fuzzy matches
            enable_typo_correction: Enable typo correction
            enable_phonetic: Enable phonetic matching
            enable_acronyms: Enable acronym expansion
            preserve_exact_match: Always try exact match first
        """
        self.min_confidence = min_confidence
        self.enable_typo_correction = enable_typo_correction
        self.enable_phonetic = enable_phonetic
        self.enable_acronyms = enable_acronyms
        self.preserve_exact_match = preserve_exact_match
        
        # Common IT acronyms and their expansions
        self.acronyms = {
            "db": ["database"],
            "srv": ["server"],
            "vm": ["virtual machine"],
            "vpn": ["virtual private network"],
            "api": ["application programming interface"],
            "dns": ["domain name system"],
            "dhcp": ["dynamic host configuration protocol"],
            "ad": ["active directory"],
            "dc": ["domain controller", "data center"],
            "ha": ["high availability"],
            "dr": ["disaster recovery"],
            "ssl": ["secure sockets layer"],
            "tls": ["transport layer security"],
            "ssh": ["secure shell"],
            "http": ["hypertext transfer protocol"],
            "https": ["hypertext transfer protocol secure"],
            "ip": ["internet protocol"],
            "tcp": ["transmission control protocol"],
            "udp": ["user datagram protocol"],
            "lan": ["local area network"],
            "wan": ["wide area network"],
            "vlan": ["virtual local area network"],
            "nas": ["network attached storage"],
            "san": ["storage area network"],
            "raid": ["redundant array of independent disks"],
            "cpu": ["central processing unit"],
            "ram": ["random access memory"],
            "ssd": ["solid state drive"],
            "hdd": ["hard disk drive"],
            "os": ["operating system"],
            "ci": ["continuous integration"],
            "cd": ["continuous deployment", "continuous delivery"],
            "k8s": ["kubernetes"],
            "aws": ["amazon web services"],
            "gcp": ["google cloud platform"],
            "azure": ["microsoft azure"]
        }
        
        # Common typos in IT terms
        self.typo_corrections = {
            "pasword": "password",
            "passwrd": "password",
            "pssword": "password",
            "servr": "server",
            "sever": "server",
            "servre": "server",
            "databse": "database",
            "datbase": "database",
            "datebase": "database",
            "netwok": "network",
            "netowrk": "network",
            "netwrok": "network",
            "firwall": "firewall",
            "firewal": "firewall",
            "fierwall": "firewall",
            "bacup": "backup",
            "backp": "backup",
            "bakup": "backup",
            "confg": "config",
            "cofig": "config",
            "conifg": "config",
            "configuartion": "configuration",
            "configuraton": "configuration",
            "adminstrator": "administrator",
            "administator": "administrator",
            "secuirty": "security",
            "securty": "security",
            "secutiry": "security",
            "authetication": "authentication",
            "authentcation": "authentication",
            "authntication": "authentication",
            "authorizaton": "authorization",
            "authroization": "authorization",
            "certifcate": "certificate",
            "certificat": "certificate",
            "certficate": "certificate",
            "encyrption": "encryption",
            "encrytion": "encryption",
            "encription": "encryption",
            "connecton": "connection",
            "conection": "connection",
            "conexion": "connection",
            "permisson": "permission",
            "permision": "permission",
            "permissoin": "permission"
        }
        
    def enhance_query(
        self,
        query: str,
        candidates: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> EnhancedQuery:
        """
        Enhance query with fuzzy matching.
        
        Args:
            query: Original query string
            candidates: List of candidate strings to match against
            context: Additional context for enhancement
            
        Returns:
            Enhanced query with fuzzy matches
        """
        fuzzy_matches = []
        enhanced_tokens = []
        overall_confidence = 1.0
        
        # Tokenize query
        tokens = self._tokenize(query)
        
        for token in tokens:
            token_lower = token.lower()
            best_match = None
            
            # Try exact match first if preserve_exact_match is enabled
            if self.preserve_exact_match and candidates:
                exact_match = self._find_exact_match(token_lower, candidates)
                if exact_match:
                    best_match = FuzzyMatch(
                        original=token,
                        matched=exact_match,
                        confidence=1.0,
                        match_type=FuzzyMatchType.EXACT,
                        metadata={}
                    )
            
            # Try typo correction
            if not best_match and self.enable_typo_correction:
                corrected = self._correct_typo(token_lower)
                if corrected and corrected != token_lower:
                    best_match = FuzzyMatch(
                        original=token,
                        matched=corrected,
                        confidence=0.9,
                        match_type=FuzzyMatchType.TYPO_CORRECTION,
                        metadata={"correction": corrected}
                    )
            
            # Try acronym expansion
            if not best_match and self.enable_acronyms:
                expansions = self._expand_acronym(token_lower)
                if expansions:
                    best_match = FuzzyMatch(
                        original=token,
                        matched=expansions[0],
                        confidence=0.85,
                        match_type=FuzzyMatchType.ACRONYM,
                        metadata={"expansions": expansions}
                    )
            
            # Try fuzzy matching against candidates
            if not best_match and candidates:
                fuzzy_result = self._fuzzy_match(token_lower, candidates)
                if fuzzy_result:
                    best_match = fuzzy_result
            
            # Add match or original token
            if best_match and best_match.confidence >= self.min_confidence:
                fuzzy_matches.append(best_match)
                enhanced_tokens.append(best_match.matched)
                overall_confidence *= best_match.confidence
            else:
                enhanced_tokens.append(token)
        
        # Build enhanced query
        enhanced_query = " ".join(enhanced_tokens)
        
        # Determine if we should fallback to exact match
        fallback_to_exact = (
            self.preserve_exact_match and 
            overall_confidence < self.min_confidence
        )
        
        return EnhancedQuery(
            original_query=query,
            enhanced_query=enhanced_query if not fallback_to_exact else query,
            fuzzy_matches=fuzzy_matches,
            confidence=overall_confidence,
            fallback_to_exact=fallback_to_exact,
            metadata={
                "tokens_processed": len(tokens),
                "matches_found": len(fuzzy_matches),
                "enhancement_applied": not fallback_to_exact
            }
        )
    
    def _tokenize(self, query: str) -> List[str]:
        """Tokenize query into words."""
        # Split on whitespace and punctuation, but preserve certain patterns
        tokens = re.findall(r'\b[\w\-\.]+\b|[^\w\s]', query)
        return [t for t in tokens if t.strip()]
    
    def _find_exact_match(
        self,
        token: str,
        candidates: List[str]
    ) -> Optional[str]:
        """Find exact match in candidates."""
        token_lower = token.lower()
        for candidate in candidates:
            if candidate.lower() == token_lower:
                return candidate
        return None
    
    def _correct_typo(self, token: str) -> Optional[str]:
        """Correct common typos."""
        return self.typo_corrections.get(token.lower())
    
    def _expand_acronym(self, token: str) -> Optional[List[str]]:
        """Expand acronyms."""
        return self.acronyms.get(token.lower())
    
    def _fuzzy_match(
        self,
        token: str,
        candidates: List[str]
    ) -> Optional[FuzzyMatch]:
        """
        Perform fuzzy matching against candidates.
        
        Args:
            token: Token to match
            candidates: List of candidate strings
            
        Returns:
            Best fuzzy match or None
        """
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            # Calculate similarity score
            score = self._calculate_similarity(token, candidate.lower())
            
            if score > best_score and score >= self.min_confidence:
                best_score = score
                best_match = candidate
        
        if best_match:
            # Determine match type
            match_type = self._determine_match_type(token, best_match.lower())
            
            return FuzzyMatch(
                original=token,
                matched=best_match,
                confidence=best_score,
                match_type=match_type,
                metadata={
                    "similarity_score": best_score,
                    "algorithm": "sequence_matcher"
                }
            )
        
        return None
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score between 0 and 1
        """
        # Use SequenceMatcher for now (can be replaced with Levenshtein)
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def _determine_match_type(self, token: str, matched: str) -> FuzzyMatchType:
        """
        Determine the type of fuzzy match.
        
        Args:
            token: Original token
            matched: Matched string
            
        Returns:
            Type of fuzzy match
        """
        token_lower = token.lower()
        matched_lower = matched.lower()
        
        if token_lower == matched_lower:
            return FuzzyMatchType.EXACT
        elif matched_lower.startswith(token_lower):
            return FuzzyMatchType.PREFIX
        elif token_lower in matched_lower:
            return FuzzyMatchType.SUBSTRING
        else:
            return FuzzyMatchType.LEVENSHTEIN
    
    def batch_enhance(
        self,
        queries: List[str],
        candidates: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[EnhancedQuery]:
        """
        Enhance multiple queries in batch.
        
        Args:
            queries: List of queries to enhance
            candidates: List of candidate strings
            context: Additional context
            
        Returns:
            List of enhanced queries
        """
        return [
            self.enhance_query(query, candidates, context)
            for query in queries
        ]
    
    def get_confidence_score(self, enhanced_query: EnhancedQuery) -> float:
        """
        Get overall confidence score for enhanced query.
        
        Args:
            enhanced_query: Enhanced query object
            
        Returns:
            Confidence score between 0 and 1
        """
        return enhanced_query.confidence
    
    def should_use_fuzzy(self, enhanced_query: EnhancedQuery) -> bool:
        """
        Determine if fuzzy matching should be used.
        
        Args:
            enhanced_query: Enhanced query object
            
        Returns:
            True if fuzzy matching should be used
        """
        return (
            not enhanced_query.fallback_to_exact and
            enhanced_query.confidence >= self.min_confidence and
            len(enhanced_query.fuzzy_matches) > 0
        )
    
    def get_match_explanations(
        self,
        enhanced_query: EnhancedQuery
    ) -> List[str]:
        """
        Get human-readable explanations for fuzzy matches.
        
        Args:
            enhanced_query: Enhanced query object
            
        Returns:
            List of explanation strings
        """
        explanations = []
        
        for match in enhanced_query.fuzzy_matches:
            if match.match_type == FuzzyMatchType.TYPO_CORRECTION:
                explanations.append(
                    f"Corrected '{match.original}' to '{match.matched}' (typo correction)"
                )
            elif match.match_type == FuzzyMatchType.ACRONYM:
                expansions = match.metadata.get("expansions", [])
                explanations.append(
                    f"Expanded '{match.original}' to '{match.matched}' (acronym)"
                )
            elif match.match_type == FuzzyMatchType.LEVENSHTEIN:
                score = match.metadata.get("similarity_score", 0)
                explanations.append(
                    f"Matched '{match.original}' to '{match.matched}' "
                    f"(similarity: {score:.2%})"
                )
            elif match.match_type == FuzzyMatchType.PREFIX:
                explanations.append(
                    f"Matched '{match.original}' as prefix of '{match.matched}'"
                )
            elif match.match_type == FuzzyMatchType.SUBSTRING:
                explanations.append(
                    f"Found '{match.original}' within '{match.matched}'"
                )
        
        return explanations
    
    def update_dictionaries(
        self,
        typos: Optional[Dict[str, str]] = None,
        acronyms: Optional[Dict[str, List[str]]] = None
    ):
        """
        Update typo corrections and acronym dictionaries.
        
        Args:
            typos: Additional typo corrections
            acronyms: Additional acronym expansions
        """
        if typos:
            self.typo_corrections.update(typos)
        if acronyms:
            self.acronyms.update(acronyms)