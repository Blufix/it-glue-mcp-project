# Coding Standards

## Python Code Standards

### Code Formatting
- **Black**: Line length 88 characters, target Python 3.11+
- **isort**: Import sorting with black profile
- **Pre-commit hooks**: Automatically enforce formatting

```bash
# Format code
poetry run black src tests
poetry run isort src tests
```

### Type Checking
- **mypy**: Strict type checking enabled
- **Disallow untyped defs**: All functions must have type hints
- **Target**: Python 3.11+ type annotations

```python
# Good: Proper type hints
async def query_organizations(
    self,
    org_type: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
```

### Linting
- **Ruff**: Modern Python linter with strict rules
- **Selected rules**: E, W, F, I, C, B, UP (pycodestyle, pyflakes, isort, comprehensions, bugbear, pyupgrade)
- **Ignored**: E501 (line too long), B008 (function calls in defaults)

### Import Organization
```python
# Standard library imports
import asyncio
import logging
from typing import Optional, Dict, Any

# Third-party imports  
import aiohttp
from pydantic import BaseModel

# Local imports
from src.config.settings import settings
from src.services.itglue.client import ITGlueClient
```

## Async/Await Patterns

### Mandatory Async Usage
- **All I/O operations** must use async/await
- **Database operations** via asyncpg, aioredis
- **HTTP requests** via aiohttp
- **MCP tools** are async functions

```python
# Good: Proper async patterns
async def process_query(self, query: str) -> Dict[str, Any]:
    async with self.session.get(url) as response:
        return await response.json()

# Bad: Blocking operations
def process_query(self, query: str) -> Dict[str, Any]:
    response = requests.get(url)  # Blocking!
```

### Error Handling
```python
try:
    result = await self.client.fetch_data()
except ClientError as e:
    logger.error(f"Client error: {e}", exc_info=True)
    return {"success": False, "error": str(e)}
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True) 
    return {"success": False, "error": "Internal server error"}
```

## MCP Tool Standards

### Tool Registration Pattern
```python
@self.server.tool()
async def query_organizations(
    action: str = "list",
    name: Optional[str] = None,
    # ... other params
) -> Dict[str, Any]:
    """
    Docstring explaining the tool.
    
    Args:
        action: Action to perform
        name: Organization name
        
    Returns:
        Structured response with success/error
    """
```

### Response Format Standard
```python
# Success response
return {
    "success": True,
    "data": {...},
    "count": 10,
    "message": "Operation completed"
}

# Error response  
return {
    "success": False,
    "error": "Descriptive error message",
    "data": None
}
```

## Database Patterns

### Connection Management
- **Lazy initialization**: Initialize connections on first use
- **Connection pooling**: Use asyncpg pools
- **Graceful shutdown**: Properly close connections

### Caching Strategy
- **Redis TTL**: 5-minute default for query results
- **In-memory caching**: For frequently accessed data
- **Cache invalidation**: Clear on data updates

```python
# Cache pattern
cache_key = f"org_query:{hash(query_params)}"
if cached := await self.cache.get(cache_key):
    return cached
    
result = await self._fetch_from_api(query_params)
await self.cache.set(cache_key, result, ttl=300)
return result
```

## Testing Standards

### Test Coverage
- **Minimum 80%** coverage required
- **Unit tests**: Individual function testing
- **Integration tests**: Database and API integration
- **Performance tests**: Response time validation

### Test Organization
```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Database/API tests  
├── performance/    # Response time tests
└── fixtures/       # Test data and mocks
```

### Test Naming
```python
class TestOrganizationsHandler:
    async def test_list_organizations_success(self):
        """Test successful organization listing."""
        
    async def test_list_organizations_api_error(self):
        """Test handling of API errors."""
```

## Logging Standards

### Structured Logging
```python
import logging
logger = logging.getLogger(__name__)

# Good: Structured with context
logger.info(
    "Organization query completed", 
    extra={
        "query": query,
        "org_count": len(results),
        "response_time": elapsed
    }
)

# Bad: String formatting only
logger.info(f"Found {len(results)} organizations")
```

### Log Levels
- **DEBUG**: Development debugging
- **INFO**: Normal operation events  
- **WARNING**: Recoverable issues
- **ERROR**: Error conditions with stack traces
- **CRITICAL**: System failures

## Performance Standards

### Response Time Targets
- **Organization queries**: < 500ms
- **General queries**: < 2s
- **Infrastructure documentation**: < 30s
- **Cache hit ratio**: > 80%

### Resource Limits
- **Memory**: Monitor for leaks, especially in-memory caches
- **Connection pools**: Limit concurrent connections
- **Rate limiting**: Respect IT Glue API limits (100 req/min)

## Security Standards

### API Key Management
- **Environment variables only**: Never hardcode keys
- **No logging**: Never log API keys or passwords
- **Rotation ready**: Support key rotation without restart

### Input Validation
```python
from pydantic import BaseModel, validator

class QueryRequest(BaseModel):
    query: str
    company: Optional[str] = None
    
    @validator('query')
    def validate_query(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Query too short')
        return v.strip()
```

## File Organization

### Module Structure
```python
# src/query/organizations_handler.py
"""Handler for organization queries with fuzzy matching."""

import asyncio
import logging
# ... other imports

logger = logging.getLogger(__name__)

# Constants at module level
MAX_RESPONSE_TIME_MS = 500

class OrganizationsHandler:
    """Handles queries related to IT Glue organizations."""
    
    def __init__(self, ...):
        """Initialize handler with dependencies."""
```

### Configuration Management
- **Pydantic Settings**: Type-safe configuration
- **Environment-based**: Different configs per environment
- **Validation**: Fail fast on invalid config

These standards reflect the actual patterns used in the current Epic 1.1 implementation.