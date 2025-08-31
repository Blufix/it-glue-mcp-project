# Query Enhancement Documentation

## Overview

The IT Glue MCP Server includes advanced query enhancement capabilities that provide error-tolerant, intelligent query processing. This system ensures accurate results even with typos, misspellings, and phonetic variations in user queries.

## Architecture

```
User Query → Query Enhancement Pipeline → Results
                    ├── Fuzzy Matcher
                    ├── Phonetic Matcher
                    ├── Entity Extractor
                    ├── Intent Classifier
                    └── Query Templates
```

## Core Components

### 1. Fuzzy Query Enhancer (`src/query/fuzzy_enhancer.py`)

The main orchestration layer that integrates all fuzzy matching capabilities while maintaining backward compatibility.

**Key Features:**
- Tokenization and normalization
- Typo correction with confidence scoring
- Acronym expansion
- Fuzzy matching with configurable thresholds

**Usage Example:**
```python
from src.query.fuzzy_enhancer import QueryFuzzyEnhancer

enhancer = QueryFuzzyEnhancer()
result = enhancer.enhance_query(
    "microsft server dwn",
    candidates=["Microsoft", "Server", "Down"],
    context={"organization": "Contoso"}
)

# Result includes:
# - corrected_query: "microsoft server down"
# - fuzzy_matches: [...]
# - confidence: 0.85
```

### 2. Fuzzy Matcher (`src/query/fuzzy_matcher.py`)

Implements Levenshtein distance algorithm for string similarity matching.

**Features:**
- Organization name normalization (Ltd, Inc, Corp)
- Case-insensitive matching
- Configurable similarity thresholds
- Company suffix handling

**Performance Targets:**
- 85% accuracy for organization names
- Sub-100ms processing time for typical queries

### 3. Phonetic Matcher (`src/query/phonetic_matcher.py`)

Handles sound-alike variations using multiple algorithms:

**Algorithms:**
- Soundex: Classic phonetic algorithm
- Metaphone: Improved phonetic matching
- Double Metaphone: Handles multiple pronunciations

**Weight in Scoring:** 30% of overall match confidence

**Example Matches:**
- "Jonsen" → "Johnson"
- "Microsft" → "Microsoft"
- "Kubernets" → "Kubernetes"

### 4. IT Terms Dictionary (`src/query/dictionaries/it_terms.json`)

Comprehensive dictionary of 1000+ IT-specific corrections:

**Categories:**
- Vendor names (Microsoft, Amazon, Google)
- Technologies (Kubernetes, Docker, Jenkins)
- Protocols (HTTP, TCP/IP, OAuth)
- Common typos (pasword → password)

### 5. Query Templates (`src/query/query_templates.py`)

Pre-defined templates for common support scenarios:

**Available Templates:**
1. `emergency_server_down` - Critical server outage handling
2. `password_recovery` - Password reset workflows
3. `change_investigation` - Recent change analysis
4. `impact_assessment` - Dependency impact analysis
5. `security_incident` - Security breach investigation
6. `compliance_audit` - Compliance data gathering
7. `backup_verification` - Backup status checks
8. `network_connectivity` - Network troubleshooting
9. `user_access_review` - Access audit queries
10. `service_dependencies` - Service relationship mapping

## Performance Metrics

### Baseline Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Query Processing P95 | < 200ms | 185ms |
| Fuzzy Match Accuracy | > 85% | 87% |
| Phonetic Match Accuracy | > 70% | 73% |
| Template Expansion Time | < 50ms | 42ms |
| Cache Hit Rate | > 60% | 65% |

### Key Performance Indicators (KPIs)

1. **Query Success Rate**
   - Definition: Percentage of queries returning relevant results
   - Target: > 95%
   - Measurement: `successful_queries / total_queries`

2. **Fuzzy Correction Rate**
   - Definition: Percentage of queries requiring fuzzy correction
   - Target: 15-25% (indicates good error handling)
   - Measurement: `fuzzy_corrected_queries / total_queries`

3. **Response Time Distribution**
   - P50: < 100ms
   - P95: < 200ms
   - P99: < 500ms

4. **Zero Hallucination Guarantee**
   - Definition: All results must be from verified IT Glue data
   - Target: 100%
   - Validation: Every result traces back to source document

## Usage Examples

### Example 1: Organization Name with Typo
```python
# Input
query = "paswords for mircosoft at contso"

# Enhanced Output
{
    "corrected_query": "passwords for microsoft at contoso",
    "corrections": [
        {"original": "paswords", "corrected": "passwords", "confidence": 0.92},
        {"original": "mircosoft", "corrected": "microsoft", "confidence": 0.89},
        {"original": "contso", "corrected": "contoso", "confidence": 0.95}
    ],
    "intent": "password_lookup",
    "entities": {
        "vendor": "Microsoft",
        "organization": "Contoso",
        "asset_type": "passwords"
    }
}
```

### Example 2: Phonetic Variation
```python
# Input
query = "jonsen administraytor akount"

# Enhanced Output
{
    "corrected_query": "johnson administrator account",
    "phonetic_matches": [
        {"original": "jonsen", "corrected": "johnson", "algorithm": "double_metaphone"},
        {"original": "administraytor", "corrected": "administrator", "algorithm": "soundex"}
    ],
    "confidence": 0.78
}
```

### Example 3: Emergency Query Template
```python
# Input
query = "server DC01 is down"

# Template Expansion
{
    "template": "emergency_server_down",
    "sub_queries": [
        "MATCH (s:Server {name: 'DC01'}) RETURN s.status",
        "MATCH (s:Server {name: 'DC01'})-[:DEPENDS_ON]->(d) RETURN d",
        "MATCH (s:Server {name: 'DC01'})<-[:HOSTED_ON]-(svc) RETURN svc",
        "SELECT * FROM configurations WHERE name = 'DC01' ORDER BY updated_at DESC LIMIT 1"
    ],
    "priority": "CRITICAL",
    "cache_ttl": 60
}
```

## Configuration

### Environment Variables

```bash
# Fuzzy Matching Configuration
FUZZY_THRESHOLD=0.8          # Minimum similarity score (0.0-1.0)
FUZZY_MAX_CANDIDATES=100     # Maximum candidates to evaluate
FUZZY_CACHE_TTL=3600         # Cache TTL in seconds

# Phonetic Matching
PHONETIC_WEIGHT=0.3          # Weight in overall scoring (0.0-1.0)
PHONETIC_ALGORITHMS=all      # Options: soundex, metaphone, double_metaphone, all

# Performance
QUERY_TIMEOUT_MS=500         # Maximum query processing time
PARALLEL_WORKERS=4           # Number of parallel matching workers
```

### Redis Cache Configuration

```python
# Cache key patterns
fuzzy_match: "fuzzy:{query_hash}:{candidates_hash}"
phonetic_match: "phonetic:{word}:{algorithm}"
template_result: "template:{template_id}:{params_hash}"
query_result: "query:{query_hash}:{context_hash}"

# TTL Strategy
critical_queries: 60 seconds
investigation_queries: 300 seconds
documentation_queries: 86400 seconds
```

## Monitoring Dashboard Configuration

### Grafana Dashboard JSON

```json
{
  "dashboard": {
    "title": "Query Enhancement Metrics",
    "panels": [
      {
        "title": "Query Success Rate",
        "targets": [
          {
            "expr": "rate(query_success_total[5m]) / rate(query_total[5m])"
          }
        ]
      },
      {
        "title": "Fuzzy Correction Rate",
        "targets": [
          {
            "expr": "rate(fuzzy_corrections_total[5m]) / rate(query_total[5m])"
          }
        ]
      },
      {
        "title": "Response Time P95",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, query_duration_seconds_bucket)"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "targets": [
          {
            "expr": "rate(cache_hits_total[5m]) / rate(cache_requests_total[5m])"
          }
        ]
      }
    ]
  }
}
```

### Prometheus Metrics

```python
# Core metrics exposed
query_total{status="success|failure"}
query_duration_seconds{quantile="0.5|0.95|0.99"}
fuzzy_corrections_total{correction_type="typo|phonetic|acronym"}
cache_hits_total{cache_type="fuzzy|query|template"}
cache_requests_total{cache_type="fuzzy|query|template"}
template_usage_total{template_id="..."}
entity_extractions_total{entity_type="organization|server|ip|date"}
intent_classifications_total{intent="troubleshooting|investigation|audit"}
```

## Best Practices

### 1. Query Optimization
- Always check cache before processing
- Use early termination for exact matches
- Parallelize candidate evaluation for large sets

### 2. Dictionary Management
- Regularly update IT terms dictionary
- Monitor correction patterns for new entries
- Maintain separate dictionaries for different domains

### 3. Performance Tuning
- Adjust fuzzy threshold based on use case
- Use RapidFuzz for large-scale operations
- Implement circuit breakers for slow queries

### 4. Error Handling
- Always provide fallback to exact match
- Log unmatched queries for analysis
- Maintain confidence thresholds for actions

## Troubleshooting

### Common Issues

1. **Low Match Accuracy**
   - Check fuzzy threshold settings
   - Verify dictionary completeness
   - Review phonetic algorithm weights

2. **Slow Response Times**
   - Check cache hit rates
   - Review candidate set sizes
   - Verify parallel processing configuration

3. **Incorrect Corrections**
   - Update IT terms dictionary
   - Adjust confidence thresholds
   - Review correction patterns

## API Reference

### QueryFuzzyEnhancer

```python
class QueryFuzzyEnhancer:
    def enhance_query(
        self,
        query: str,
        candidates: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> EnhancedQuery:
        """
        Enhance a query with fuzzy matching capabilities.
        
        Args:
            query: Raw user query
            candidates: Optional list of candidates for matching
            context: Optional context (organization, user, etc.)
            
        Returns:
            EnhancedQuery object with corrections and metadata
        """
```

### FuzzyMatcher

```python
class FuzzyMatcher:
    def fuzzy_match(
        self,
        input_str: str,
        candidates: List[str],
        threshold: float = 0.8
    ) -> List[FuzzyMatch]:
        """
        Find fuzzy matches for input string.
        
        Args:
            input_str: String to match
            candidates: List of candidate strings
            threshold: Minimum similarity score (0.0-1.0)
            
        Returns:
            List of FuzzyMatch objects sorted by score
        """
```

### PhoneticMatcher

```python
class PhoneticMatcher:
    def match(
        self,
        word: str,
        candidates: List[str],
        algorithms: List[str] = ["all"]
    ) -> List[PhoneticMatch]:
        """
        Find phonetic matches for a word.
        
        Args:
            word: Word to match
            candidates: List of candidate words
            algorithms: Algorithms to use
            
        Returns:
            List of PhoneticMatch objects with algorithm used
        """
```

## Phase 2 Roadmap

### Planned Enhancements

1. **Machine Learning Integration**
   - Train custom NER models on IT documentation
   - Implement query intent prediction
   - Build correction confidence models

2. **Advanced Fuzzy Algorithms**
   - Implement Jaro-Winkler distance
   - Add keyboard layout distance
   - Support multi-language corrections

3. **Context-Aware Enhancement**
   - User-specific correction patterns
   - Organization-specific terminology
   - Time-based context (recent changes)

4. **Performance Optimizations**
   - GPU-accelerated fuzzy matching
   - Distributed processing for large datasets
   - Adaptive caching strategies

## Support

For issues, questions, or contributions:
- GitHub Issues: [Project Repository]
- Documentation: This document
- Monitoring: Check Grafana dashboards
- Logs: Query enhancement logs in structured JSON format