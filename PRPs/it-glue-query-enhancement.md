name: "IT Glue Query Enhancement PRP - Phase 1 Implementation"
description: |

## Purpose
Implement intelligent fuzzy matching and natural language query processing for IT Glue MCP Server to improve query success rate from 60% to 95%, reducing support engineer resolution time by 40%.

## Core Principles
1. **Zero Hallucination**: Never return data not backed by IT Glue sources
2. **Progressive Enhancement**: Start with fuzzy matching, then add NLP features
3. **Performance First**: Sub-500ms P95 response time for Phase 1
4. **Brownfield Respect**: Enhance existing QueryEngine without breaking changes
5. **Global rules**: Follow all rules in /home/jamie/projects/itglue-mcp-server/CLAUDE.md

---

## Goal
Transform the existing IT Glue MCP Server query system from exact-match only to an intelligent, error-tolerant search platform that corrects typos, understands natural language, and reveals hidden relationships through Neo4j graph traversal.

## Why
- **Business Impact**: Save 2.5 hours per engineer per day (2,000+ engineers = $937,500 annual ROI)
- **User Pain**: 40% of queries currently fail due to typos/exact-match requirements
- **Ticket Impact**: 25 minutes additional resolution time per failed query
- **Competitive Edge**: First IT documentation tool with true fuzzy + graph intelligence

## What
Phase 1 deliverables (Weeks 1-2):
- Organization name fuzzy matching with 85% accuracy
- IT term correction dictionary (500+ terms)
- Top 10 query templates for common engineer tasks
- Query success rate improvement from 60% to 80%

### Success Criteria
- [ ] Fuzzy matcher correctly identifies organizations with 1-2 character typos
- [ ] Common IT term misspellings auto-corrected (e.g., "microsft" → "microsoft")
- [ ] Query templates expand single queries to comprehensive result sets
- [ ] All queries return in <500ms P95
- [ ] Zero false positives (no hallucinated data)
- [ ] Existing exact-match queries continue working

## All Needed Context

### Documentation & References
```yaml
# MUST READ - External Documentation
Use Archon for documents and code examples. Project = IT Glue MCP Server - Intelligent Documentation Query System

- url: https://github.com/jamesturk/jellyfish
  why: Jellyfish library docs for phonetic matching algorithms
  
- url: https://jamesturk.github.io/jellyfish/
  why: API reference for metaphone, soundex, levenshtein functions
  
- url: https://neo4j.com/docs/cypher-manual/current/indexes/search-performance-indexes/
  why: Neo4j index optimization for fuzzy pattern matching
  
- url: https://neo4j.com/docs/cypher-manual/current/planning-and-tuning/query-tuning/
  why: Query performance tuning with PROFILE and EXPLAIN

# Existing Codebase Files - Study These Patterns
- file: /home/jamie/projects/itglue-mcp-server/src/query/fuzzy_matcher.py
  why: Current fuzzy matching implementation to enhance
  
- file: /home/jamie/projects/itglue-mcp-server/src/query/intelligent_query_processor.py
  why: Query processor that needs fuzzy enhancement integration
  
- file: /home/jamie/projects/itglue-mcp-server/src/query/neo4j_query_builder.py
  why: Neo4j query templates that need fuzzy pattern support

- file: /home/jamie/projects/itglue-mcp-server/src/mcp/tools/query_tool.py
  why: MCP tool interface that exposes query functionality
  
- file: /home/jamie/projects/itglue-mcp-server/tests/unit/test_fuzzy_matcher.py
  why: Test patterns and existing test coverage
  
- file: /home/jamie/projects/itglue-mcp-server/tests/unit/test_query_engine.py
  why: Query engine test structure and mocking patterns

# Project Configuration
- file: /home/jamie/projects/itglue-mcp-server/pyproject.toml
  why: Dependencies - note jellyfish already installed
```

### Current Codebase Tree
```bash
/home/jamie/projects/itglue-mcp-server/
├── src/
│   ├── query/
│   │   ├── __init__.py
│   │   ├── engine.py              # Main query engine
│   │   ├── fuzzy_matcher.py       # Fuzzy matching (EXISTS)
│   │   ├── intelligent_query_processor.py  # NLP processor (EXISTS)
│   │   ├── neo4j_query_builder.py # Graph queries (EXISTS)
│   │   ├── parser.py              # Query parser
│   │   └── validator.py           # Zero-hallucination validator
│   ├── cache/
│   │   └── manager.py             # Cache management
│   ├── mcp/
│   │   └── tools/
│   │       └── query_tool.py      # MCP interface
│   └── services/
│       └── query_engine.py        # Service layer
└── tests/
    └── unit/
        ├── test_fuzzy_matcher.py
        └── test_query_engine.py
```

### Desired Codebase Tree with Phase 1 Enhancements
```bash
/home/jamie/projects/itglue-mcp-server/
├── src/
│   ├── query/
│   │   ├── fuzzy_matcher.py       # ENHANCE: Add caching, better algorithms
│   │   ├── intelligent_query_processor.py  # ENHANCE: Integrate fuzzy results
│   │   ├── neo4j_query_builder.py # ENHANCE: Add fuzzy pattern queries
│   │   ├── dictionaries/          # NEW
│   │   │   ├── __init__.py        
│   │   │   ├── it_terms.json      # 500+ IT term corrections
│   │   │   └── company_aliases.json # Common company name variations
│   │   └── templates/             # NEW
│   │       ├── __init__.py
│   │       └── engineer_queries.py # Top 10 query templates
```

### Known Gotchas of our Codebase & Library Quirks
```python
# CRITICAL: jellyfish returns None for empty strings - always check
# Example: jellyfish.metaphone('') returns None, not empty string

# CRITICAL: Neo4j driver requires async context manager
# Always use: async with self.neo4j_driver.session() as session

# CRITICAL: FuzzyMatcher normalizes organization names internally
# Don't double-normalize or you'll break matching

# CRITICAL: Cache keys must be serializable strings
# Use: str(cache_key) not complex objects

# CRITICAL: IT Glue API is READ-ONLY
# Never attempt writes, only queries

# GOTCHA: Similarity scores are 0-1 floats
# 0.7 threshold = 70% similarity minimum
```

## Implementation Blueprint

### Data Models and Structure

```python
# Enhanced MatchResult with caching support
@dataclass
class EnhancedMatchResult:
    """Enhanced result with performance metrics."""
    original: str
    matched: str
    score: float
    match_type: str  # 'exact', 'fuzzy', 'phonetic', 'acronym', 'partial'
    confidence: float
    entity_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    match_time_ms: float = 0  # Performance tracking
    from_cache: bool = False  # Cache hit indicator

# Query Template structure
@dataclass
class QueryTemplate:
    """Predefined query template for common tasks."""
    name: str  # e.g., 'emergency_server_down'
    pattern: str  # User-facing pattern
    expands_to: List[str]  # Multiple queries to execute
    parameters: List[str]  # Required parameters
    priority: int  # Execution order
```

### List of Tasks to Complete (in order)

```yaml
Task 1 - Enhance Dictionary Loading:
MODIFY src/query/fuzzy_matcher.py:
  - FIND pattern: "def _build_common_mistakes"
  - ADD JSON file loading for extensible dictionaries
  - PRESERVE existing hardcoded terms as fallback
  - ADD method to reload dictionaries without restart

Task 2 - Create IT Terms Dictionary:
CREATE src/query/dictionaries/it_terms.json:
  - INCLUDE 500+ common IT term misspellings
  - FORMAT: {"misspelling": "correct_term"}
  - ADD vendor names, technologies, protocols
  - INCLUDE phonetic variations

Task 3 - Implement Caching Layer:
MODIFY src/query/fuzzy_matcher.py:
  - ADD Redis cache integration for match results
  - IMPLEMENT TTL of 3600 seconds
  - ADD cache key: f"fuzzy:{input}:{candidates_hash}"
  - TRACK cache hit rates for monitoring

Task 4 - Optimize Fuzzy Matching Algorithm:
MODIFY src/query/fuzzy_matcher.py:
  - ADD RapidFuzz as fallback for performance
  - IMPLEMENT parallel matching for large candidate sets
  - ADD early termination for exact matches
  - OPTIMIZE threshold checking order

Task 5 - Create Query Templates:
CREATE src/query/templates/engineer_queries.py:
  - IMPLEMENT top 10 templates from PRD
  - ADD parameter validation for each template
  - INCLUDE template expansion logic
  - ADD priority-based execution

Task 6 - Enhance Neo4j Query Builder:
MODIFY src/query/neo4j_query_builder.py:
  - ADD fuzzy pattern support in Cypher queries
  - IMPLEMENT index hints for performance
  - ADD query result ranking by match confidence
  - OPTIMIZE traversal depth limits

Task 7 - Integrate Fuzzy with Intelligent Processor:
MODIFY src/query/intelligent_query_processor.py:
  - WIRE fuzzy results into query pipeline
  - ADD confidence score aggregation
  - IMPLEMENT fallback to exact match
  - ADD fuzzy correction tracking

Task 8 - Add Performance Monitoring:
MODIFY src/query/intelligent_query_processor.py:
  - ADD execution time tracking
  - IMPLEMENT P95 latency monitoring
  - ADD fuzzy match success rate metrics
  - LOG slow queries for analysis

Task 9 - Comprehensive Testing:
CREATE tests/unit/test_query_enhancement.py:
  - TEST all fuzzy matching scenarios
  - VERIFY zero hallucination guarantee
  - BENCHMARK performance requirements
  - ADD integration tests with Neo4j

Task 10 - Documentation and Metrics:
UPDATE docs/query_enhancement.md:
  - DOCUMENT new fuzzy capabilities
  - ADD performance baseline metrics
  - INCLUDE usage examples
  - CREATE monitoring dashboard config
```

### Per Task Pseudocode

```python
# Task 1 - Dictionary Loading Enhancement
class FuzzyMatcher:
    def __init__(self):
        # PATTERN: Load from JSON with fallback
        self.common_mistakes = self._load_or_build_mistakes()
        self.dict_cache = {}  # In-memory cache
        
    def _load_or_build_mistakes(self) -> Dict[str, str]:
        try:
            # NEW: Load from JSON file
            dict_path = Path(__file__).parent / "dictionaries" / "it_terms.json"
            if dict_path.exists():
                with open(dict_path) as f:
                    external_dict = json.load(f)
                # CRITICAL: Merge with hardcoded for backward compatibility
                return {**self._build_common_mistakes(), **external_dict}
        except Exception as e:
            logger.warning(f"Failed to load external dictionary: {e}")
        # FALLBACK: Use existing hardcoded dictionary
        return self._build_common_mistakes()

# Task 3 - Caching Implementation
async def match_organization_cached(
    self,
    input_name: str,
    candidates: List[Dict[str, str]],
    threshold: float = 0.7
) -> List[MatchResult]:
    # PATTERN: Check cache first (from src/cache/manager.py pattern)
    cache_key = f"fuzzy:{input_name}:{hash(str(candidates))}"
    
    cached = await self.cache_manager.get(cache_key)
    if cached:
        return [EnhancedMatchResult(**r, from_cache=True) for r in cached]
    
    # Perform matching
    start_time = time.perf_counter()
    results = self.match_organization(input_name, candidates, threshold)
    match_time = (time.perf_counter() - start_time) * 1000
    
    # Enhance results with timing
    enhanced = [
        EnhancedMatchResult(**r.__dict__, match_time_ms=match_time)
        for r in results
    ]
    
    # Cache results
    await self.cache_manager.set(
        cache_key,
        [r.__dict__ for r in enhanced],
        ttl=3600
    )
    
    return enhanced

# Task 5 - Query Templates
class EngineerQueryTemplates:
    def __init__(self):
        self.templates = {
            'emergency_server_down': QueryTemplate(
                name='emergency_server_down',
                pattern='EMERGENCY: {server} is down',
                expands_to=[
                    'show dependencies for {server}',
                    'what changed recently for {server}',
                    'show passwords for {server}',
                    'find documentation for {server}'
                ],
                parameters=['server'],
                priority=1
            ),
            # ... other 9 templates
        }
    
    async def expand_template(
        self,
        template_name: str,
        params: Dict[str, str]
    ) -> List[str]:
        # PATTERN: Validate then expand
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}")
        
        # Validate required parameters
        missing = set(template.parameters) - set(params.keys())
        if missing:
            raise ValueError(f"Missing parameters: {missing}")
        
        # Expand queries
        return [q.format(**params) for q in template.expands_to]

# Task 6 - Neo4j Fuzzy Pattern Support
def build_fuzzy_organization_query(
    self,
    org_input: str,
    fuzzy_matches: List[MatchResult]
) -> Neo4jQuery:
    # Build OR pattern for fuzzy matches
    org_patterns = [m.matched for m in fuzzy_matches[:3]]  # Top 3
    
    cypher = """
    MATCH (o:Organization)
    WHERE o.name IN $org_patterns
    OR o.name =~ $fuzzy_pattern
    WITH o, 
         CASE 
           WHEN o.name IN $org_patterns THEN 1.0
           ELSE 0.7
         END as match_score
    MATCH (c:Configuration)-[:BELONGS_TO]->(o)
    RETURN c, o, match_score
    ORDER BY match_score DESC, c.updated_at DESC
    LIMIT 50
    """
    
    return Neo4jQuery(
        cypher=cypher,
        parameters={
            'org_patterns': org_patterns,
            'fuzzy_pattern': f'(?i).*{org_input}.*'
        },
        description="Fuzzy organization configuration search",
        expected_return_type="configurations",
        fuzzy_matched_entities=fuzzy_matches,
        confidence=fuzzy_matches[0].confidence if fuzzy_matches else 0.5
    )
```

### Integration Points
```yaml
CACHE:
  - service: Redis (already configured)
  - pattern: "await self.cache_manager.get/set"
  - ttl: settings.FUZZY_CACHE_TTL (3600)
  
MONITORING:
  - add to: src/monitoring/metrics.py
  - metrics:
    - fuzzy_match_success_rate
    - fuzzy_match_latency_p95
    - cache_hit_rate
  
CONFIG:
  - add to: src/config/settings.py
  - settings:
    FUZZY_THRESHOLD = float(os.getenv('FUZZY_THRESHOLD', '0.7'))
    FUZZY_CACHE_TTL = int(os.getenv('FUZZY_CACHE_TTL', '3600'))
    FUZZY_MAX_CANDIDATES = int(os.getenv('FUZZY_MAX_CANDIDATES', '5'))
  
NEO4J:
  - indexes: CREATE INDEX org_name_index IF NOT EXISTS FOR (o:Organization) ON (o.name)
  - indexes: CREATE FULLTEXT INDEX org_fulltext IF NOT EXISTS FOR (o:Organization) ON (o.name)
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
cd /home/jamie/projects/itglue-mcp-server
poetry run ruff check src/query/ --fix  # Auto-fix formatting
poetry run mypy src/query/              # Type checking

# Expected: No errors. If errors, READ and fix them.
```

### Level 2: Unit Tests
```python
# CREATE tests/unit/test_query_enhancement.py
import pytest
from src.query.fuzzy_matcher import FuzzyMatcher, EnhancedMatchResult

def test_fuzzy_typo_correction():
    """Test common typo corrections."""
    matcher = FuzzyMatcher()
    orgs = [
        {'name': 'Microsoft Corporation', 'id': '1'},
        {'name': 'Amazon Web Services', 'id': '2'}
    ]
    
    # Test typo correction
    results = matcher.match_organization('Microsft', orgs)
    assert results[0].matched == 'Microsoft Corporation'
    assert results[0].score > 0.85
    
def test_phonetic_matching():
    """Test phonetic algorithm matching."""
    matcher = FuzzyMatcher()
    orgs = [{'name': 'Johnson & Associates', 'id': '1'}]
    
    results = matcher.match_organization('Jonsen & Associates', orgs)
    assert results[0].matched == 'Johnson & Associates'
    assert results[0].match_type in ['phonetic', 'fuzzy']

def test_no_hallucination():
    """Ensure no data is invented."""
    matcher = FuzzyMatcher()
    orgs = []  # Empty candidate list
    
    results = matcher.match_organization('Any Company', orgs)
    assert len(results) == 0  # No matches invented

def test_performance_threshold():
    """Test sub-500ms response time."""
    import time
    matcher = FuzzyMatcher()
    orgs = [{'name': f'Company {i}', 'id': str(i)} for i in range(1000)]
    
    start = time.perf_counter()
    results = matcher.match_organization('Company 500', orgs)
    elapsed = (time.perf_counter() - start) * 1000
    
    assert elapsed < 500  # Must be under 500ms
    assert len(results) > 0

@pytest.mark.asyncio
async def test_template_expansion():
    """Test query template expansion."""
    from src.query.templates.engineer_queries import EngineerQueryTemplates
    
    templates = EngineerQueryTemplates()
    queries = await templates.expand_template(
        'emergency_server_down',
        {'server': 'PROD-WEB-01'}
    )
    
    assert len(queries) == 4
    assert 'PROD-WEB-01' in queries[0]
```

```bash
# Run tests iteratively until passing
cd /home/jamie/projects/itglue-mcp-server
poetry run pytest tests/unit/test_query_enhancement.py -v
# If failing: Read errors, fix code, re-run
```

### Level 3: Integration Test
```bash
# Start services
cd /home/jamie/projects/itglue-mcp-server
docker-compose up -d redis neo4j
poetry run python -m src.main --dev

# Test fuzzy matching endpoint
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "query",
    "arguments": {
      "query": "show servers for Microsft",
      "company": "Microsft Corporation"
    }
  }'

# Expected: Returns Microsoft results despite typo
# Check response has: "fuzzy_corrections": {"organization": {...}}
```

### Level 4: Performance Validation
```bash
# Load test with Apache Bench
ab -n 100 -c 10 -p query.json -T application/json \
  http://localhost:8000/mcp/tools/call

# Check P95 latency < 500ms
# Check success rate > 80%
```

## Final Validation Checklist
- [ ] All unit tests pass: `poetry run pytest tests/unit/test_query_enhancement.py -v`
- [ ] No linting errors: `poetry run ruff check src/query/`
- [ ] No type errors: `poetry run mypy src/query/`
- [ ] Integration test returns fuzzy corrected results
- [ ] P95 latency < 500ms verified
- [ ] Cache hit rate > 50% after warmup
- [ ] Zero hallucination - all results traceable to IT Glue
- [ ] Backward compatibility - exact matches still work
- [ ] Logs show fuzzy corrections applied
- [ ] Monitoring metrics exposed

---

## Anti-Patterns to Avoid
- ❌ Don't modify existing exact-match behavior - add fuzzy as enhancement
- ❌ Don't skip caching - it's critical for <500ms performance
- ❌ Don't return low-confidence matches (<0.7) - maintain quality
- ❌ Don't mix sync/async - use async throughout query pipeline
- ❌ Don't hardcode thresholds - use settings/environment variables
- ❌ Don't ignore Neo4j indexes - they're required for performance
- ❌ Don't invent data - every result must trace to IT Glue source

---

## Implementation Confidence Score: 8.5/10

### Confidence Factors:
- ✅ Existing fuzzy matcher foundation (just needs enhancement)
- ✅ Clear test patterns and validation approach
- ✅ Jellyfish library already in dependencies
- ✅ Redis cache already configured
- ✅ Neo4j query builder exists and is extensible
- ⚠️ Neo4j index optimization may need tuning
- ⚠️ Performance target aggressive but achievable with caching

This PRP provides comprehensive context for one-pass implementation of Phase 1 fuzzy matching enhancement, with all necessary documentation, patterns, and validation gates included.