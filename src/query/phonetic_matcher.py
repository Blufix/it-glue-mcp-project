"""Phonetic matching algorithms for fuzzy search."""

from dataclasses import dataclass
from enum import Enum


class PhoneticAlgorithm(Enum):
    """Types of phonetic algorithms."""
    SOUNDEX = "soundex"
    METAPHONE = "metaphone"
    DOUBLE_METAPHONE = "double_metaphone"


@dataclass
class PhoneticMatch:
    """Represents a phonetic match result."""
    original: str
    matched: str
    algorithm: PhoneticAlgorithm
    phonetic_key: str
    confidence: float
    metadata: dict[str, any]


class PhoneticMatcher:
    """Phonetic matching for sound-alike terms."""

    def __init__(self, weight: float = 0.3):
        """
        Initialize phonetic matcher.

        Args:
            weight: Weight of phonetic matching in overall score (default 30%)
        """
        self.weight = weight

        # Soundex character mappings
        self.soundex_map = {
            'B': '1', 'F': '1', 'P': '1', 'V': '1',
            'C': '2', 'G': '2', 'J': '2', 'K': '2',
            'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
            'D': '3', 'T': '3',
            'L': '4',
            'M': '5', 'N': '5',
            'R': '6'
        }

        # Double Metaphone rules
        self.metaphone_rules = self._init_metaphone_rules()

    def _init_metaphone_rules(self) -> dict:
        """Initialize Double Metaphone transformation rules."""
        return {
            # Initial transformations
            'initial': {
                'KN': 'N', 'GN': 'N', 'PN': 'N', 'AE': 'E', 'WR': 'R',
                'PS': 'S', 'TS': 'S', 'X': 'S'
            },
            # Vowel handling
            'vowels': {'A', 'E', 'I', 'O', 'U', 'Y'},
            # Special cases
            'special': {
                'GH': '',  # Silent
                'DG': 'J', # As in 'edge'
                'PH': 'F', # As in 'phone'
                'SH': 'X', # Special marker for SH sound
                'CH': 'X', # Can be K or X depending on origin
                'TH': '0', # Theta sound
                'CK': 'K', # Simplify
                'CC': 'K', # Before E,I,Y -> KS, else K
                'SC': 'S', # Before E,I,Y -> S, else SK
            }
        }

    def soundex(self, word: str) -> str:
        """
        Generate Soundex code for a word.

        Args:
            word: Word to encode

        Returns:
            Soundex code (e.g., "S530" for "Smith")
        """
        if not word:
            return ""

        word = word.upper()

        # Keep first letter
        soundex_code = word[0]

        # Map remaining letters
        prev_code = self.soundex_map.get(word[0], '0')

        for char in word[1:]:
            code = self.soundex_map.get(char, '0')

            # Skip consecutive duplicates and vowels/H/W/Y
            if code != '0' and code != prev_code:
                soundex_code += code
                prev_code = code
            elif code == '0':
                prev_code = '0'

        # Pad with zeros and truncate to 4 characters
        soundex_code = (soundex_code + '000')[:4]

        return soundex_code

    def metaphone(self, word: str, max_length: int = 10) -> str:
        """
        Generate Metaphone code for a word.

        Args:
            word: Word to encode
            max_length: Maximum length of result

        Returns:
            Metaphone code
        """
        if not word:
            return ""

        word = word.upper()
        result = []

        # Apply initial transformations
        for pattern, replacement in self.metaphone_rules['initial'].items():
            if word.startswith(pattern):
                word = replacement + word[len(pattern):]
                break

        i = 0
        while i < len(word) and len(result) < max_length:
            char = word[i]

            # Check for multi-character patterns
            if i < len(word) - 1:
                two_char = word[i:i+2]
                if two_char in self.metaphone_rules['special']:
                    replacement = self.metaphone_rules['special'][two_char]
                    if replacement:
                        result.append(replacement)
                    i += 2
                    continue

            # Single character rules
            if char in self.metaphone_rules['vowels']:
                if i == 0:  # Keep initial vowel
                    result.append(char)
            elif char == 'B':
                if i < len(word) - 1 or word[i-1:i] != 'M':
                    result.append('B')
            elif char == 'C':
                if i < len(word) - 1:
                    next_char = word[i + 1]
                    if next_char in 'EIY':
                        result.append('S')
                    else:
                        result.append('K')
                else:
                    result.append('K')
            elif char == 'D':
                result.append('T')
            elif char == 'F':
                result.append('F')
            elif char == 'G':
                if i < len(word) - 1:
                    next_char = word[i + 1]
                    if next_char in 'EIY':
                        result.append('J')
                    else:
                        result.append('K')
                else:
                    result.append('K')
            elif char == 'H':
                # H is silent unless at beginning or after C,S,P,T,G
                if i == 0 or word[i-1] in 'CSPTG':
                    result.append('H')
            elif char == 'J':
                result.append('J')
            elif char == 'K':
                result.append('K')
            elif char == 'L':
                result.append('L')
            elif char == 'M':
                result.append('M')
            elif char == 'N':
                result.append('N')
            elif char == 'P':
                result.append('P')
            elif char == 'Q':
                result.append('K')
            elif char == 'R':
                result.append('R')
            elif char == 'S':
                result.append('S')
            elif char == 'T':
                result.append('T')
            elif char == 'V':
                result.append('F')
            elif char == 'W':
                if i < len(word) - 1 and word[i + 1] in self.metaphone_rules['vowels']:
                    result.append('W')
            elif char == 'X':
                result.append('KS')
            elif char == 'Y':
                if i < len(word) - 1:
                    result.append('Y')
            elif char == 'Z':
                result.append('S')

            i += 1

        return ''.join(result)[:max_length]

    def double_metaphone(self, word: str) -> tuple[str, str]:
        """
        Generate Double Metaphone codes for a word.

        Returns two codes: primary and alternate pronunciation.

        Args:
            word: Word to encode

        Returns:
            Tuple of (primary, alternate) metaphone codes
        """
        if not word:
            return ("", "")

        # Generate primary code
        primary = self.metaphone(word)

        # Generate alternate code with different rules
        word_upper = word.upper()
        alternate = []

        # Alternate rules for common variations
        if 'SCH' in word_upper:
            # German/Yiddish pronunciation
            alternate_word = word_upper.replace('SCH', 'SK')
            alternate = self.metaphone(alternate_word)
        elif word_upper.startswith('C'):
            # C can be K or S
            if len(word_upper) > 1 and word_upper[1] in 'EIY':
                alternate = 'S' + self.metaphone(word_upper[1:])
            else:
                alternate = primary  # Same as primary
        elif 'CC' in word_upper:
            # CC can be K or KS
            alternate_word = word_upper.replace('CC', 'KS')
            alternate = self.metaphone(alternate_word)
        else:
            alternate = primary  # No alternate pronunciation

        return (primary, alternate if alternate != primary else "")

    def match_phonetic(
        self,
        word1: str,
        word2: str,
        algorithm: PhoneticAlgorithm = PhoneticAlgorithm.DOUBLE_METAPHONE
    ) -> float:
        """
        Calculate phonetic similarity between two words.

        Args:
            word1: First word
            word2: Second word
            algorithm: Phonetic algorithm to use

        Returns:
            Similarity score between 0 and 1
        """
        if not word1 or not word2:
            return 0.0

        if algorithm == PhoneticAlgorithm.SOUNDEX:
            code1 = self.soundex(word1)
            code2 = self.soundex(word2)
            return 1.0 if code1 == code2 else 0.0

        elif algorithm == PhoneticAlgorithm.METAPHONE:
            code1 = self.metaphone(word1)
            code2 = self.metaphone(word2)
            return 1.0 if code1 == code2 else 0.0

        elif algorithm == PhoneticAlgorithm.DOUBLE_METAPHONE:
            primary1, alt1 = self.double_metaphone(word1)
            primary2, alt2 = self.double_metaphone(word2)

            # Check all combinations
            if primary1 == primary2:
                return 1.0
            elif alt1 and (primary1 == alt2 or alt1 == primary2):
                return 0.9
            elif alt1 and alt2 and alt1 == alt2:
                return 0.8
            else:
                return 0.0

        return 0.0

    def find_phonetic_matches(
        self,
        query: str,
        candidates: list[str],
        threshold: float = 0.7,
        algorithm: PhoneticAlgorithm = PhoneticAlgorithm.DOUBLE_METAPHONE
    ) -> list[PhoneticMatch]:
        """
        Find phonetic matches for a query in candidates.

        Args:
            query: Query term
            candidates: List of candidate strings
            threshold: Minimum similarity threshold
            algorithm: Phonetic algorithm to use

        Returns:
            List of phonetic matches
        """
        matches = []

        # Generate phonetic code for query
        if algorithm == PhoneticAlgorithm.SOUNDEX:
            query_code = self.soundex(query)
        elif algorithm == PhoneticAlgorithm.METAPHONE:
            query_code = self.metaphone(query)
        else:  # DOUBLE_METAPHONE
            query_code = self.double_metaphone(query)

        for candidate in candidates:
            score = self.match_phonetic(query, candidate, algorithm)

            if score >= threshold:
                matches.append(PhoneticMatch(
                    original=query,
                    matched=candidate,
                    algorithm=algorithm,
                    phonetic_key=str(query_code),
                    confidence=score * self.weight,  # Apply weight
                    metadata={
                        "raw_score": score,
                        "weighted_score": score * self.weight
                    }
                ))

        # Sort by confidence
        matches.sort(key=lambda x: x.confidence, reverse=True)

        return matches

    def batch_phonetic_match(
        self,
        queries: list[str],
        candidates: list[str],
        algorithm: PhoneticAlgorithm = PhoneticAlgorithm.DOUBLE_METAPHONE
    ) -> dict[str, list[PhoneticMatch]]:
        """
        Perform phonetic matching for multiple queries.

        Args:
            queries: List of query terms
            candidates: List of candidate strings
            algorithm: Phonetic algorithm to use

        Returns:
            Dictionary mapping queries to their matches
        """
        results = {}

        for query in queries:
            results[query] = self.find_phonetic_matches(
                query, candidates, algorithm=algorithm
            )

        return results

    def get_phonetic_variants(
        self,
        word: str
    ) -> dict[str, str]:
        """
        Get all phonetic encodings for a word.

        Args:
            word: Word to encode

        Returns:
            Dictionary of algorithm names to codes
        """
        primary, alternate = self.double_metaphone(word)

        return {
            "soundex": self.soundex(word),
            "metaphone": self.metaphone(word),
            "double_metaphone_primary": primary,
            "double_metaphone_alternate": alternate
        }

    def precompute_phonetic_index(
        self,
        terms: list[str]
    ) -> dict[str, set[str]]:
        """
        Precompute phonetic index for fast lookups.

        Args:
            terms: List of terms to index

        Returns:
            Dictionary mapping phonetic codes to terms
        """
        index = {}

        for term in terms:
            # Get all phonetic codes
            variants = self.get_phonetic_variants(term)

            for algorithm, code in variants.items():
                if code:  # Skip empty codes
                    key = f"{algorithm}:{code}"
                    if key not in index:
                        index[key] = set()
                    index[key].add(term)

        return index

    def lookup_phonetic_index(
        self,
        query: str,
        index: dict[str, set[str]]
    ) -> set[str]:
        """
        Look up terms in phonetic index.

        Args:
            query: Query term
            index: Precomputed phonetic index

        Returns:
            Set of matching terms
        """
        matches = set()
        variants = self.get_phonetic_variants(query)

        for algorithm, code in variants.items():
            if code:
                key = f"{algorithm}:{code}"
                if key in index:
                    matches.update(index[key])

        return matches
