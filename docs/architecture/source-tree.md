# Source Tree Organization

## Project Structure Overview

```
itglue-mcp-server/
├── src/                           # Application source code
│   ├── mcp/                      # MCP server implementation
│   ├── query/                    # Query processing engines
│   ├── services/                 # External service integrations  
│   ├── cache/                    # Multi-layer caching system
│   ├── db/                       # Database connection management
│   ├── ui/                       # Streamlit web interface
│   ├── infrastructure/           # Infrastructure documentation
│   ├── monitoring/               # Metrics and observability
│   └── config/                   # Configuration management
├── tests/                        # Test suites
├── docs/                         # Project documentation
├── docker-compose.yml            # Service orchestration
└── pyproject.toml               # Python project configuration
```

## Core Application (`src/`)

### MCP Server Core (`src/mcp/`)
```
src/mcp/
├── __main__.py                   # Entry point (stdio/WebSocket modes)
├── server.py                     # Main MCP server (10 tools)
├── websocket_server.py           # WebSocket transport
└── tools/                        # Individual MCP tool implementations
    ├── base.py                   # Base tool class
    ├── query_tool.py             # Natural language query tool
    └── sync_tool.py              # Data synchronization tool
```

**Key Files:**
- **`server.py`**: 900+ lines, registers 10 specialized MCP tools
- **`__main__.py`**: Entry point supporting both stdio and WebSocket transports

### Query Processing (`src/query/`)
```
src/query/
├── engine.py                     # Main query coordinator
├── organizations_handler.py      # Organization queries (<500ms target)
├── documents_handler.py          # Document search with semantic support
├── flexible_assets_handler.py    # SSL certs, warranties, licenses
├── locations_handler.py          # Location and site queries
├── asset_type_handler.py         # Asset type discovery
├── intelligent_query_processor.py # NLP query analysis
├── fuzzy_matcher_optimized.py    # Fuzzy string matching
├── performance_optimizer.py      # Query optimization
└── templates/                    # Query templates and patterns
```

**Specialization Pattern:**
- Each handler focuses on specific IT Glue resource types
- Performance targets vary by handler (organizations: <500ms, general: <2s)
- Consistent caching and error handling patterns

### External Services (`src/services/`)
```
src/services/
└── itglue/
    ├── client.py                 # Rate-limited HTTP client
    └── models.py                 # Pydantic models for IT Glue entities
```

**Integration Patterns:**
- **Rate limiting**: 100 requests/minute with backoff
- **Retry logic**: Exponential backoff on API failures
- **Type safety**: Full Pydantic model coverage

### Database Layer (`src/db/`)
```
src/db/
├── postgres/                     # PostgreSQL (structured data)
├── neo4j/                       # Neo4j (graph relationships)
├── qdrant/                      # Qdrant (vector embeddings)
└── __init__.py                  # Database manager coordination
```

**Multi-Database Strategy:**
- **PostgreSQL**: Primary structured data (active)
- **Qdrant**: Vector search and embeddings (active)
- **Neo4j**: Graph relationships (provisioned, not implemented)
- **Redis**: Distributed in `cache/` module

### Caching System (`src/cache/`)
```
src/cache/
├── manager.py                    # Cache coordination
├── redis_cache.py               # Redis distributed caching
├── redis_fuzzy_cache.py         # Specialized fuzzy search cache
└── strategies.py                # Cache invalidation strategies
```

**Caching Layers:**
- **Redis**: Distributed cache with 5-minute TTL
- **In-memory**: Handler-level caches for performance
- **Strategy**: Cache-aside pattern with lazy loading

### User Interface (`src/ui/`)
```
src/ui/
├── streamlit_app.py             # Main UI (700+ lines)
├── components/                  # Reusable UI components
├── services/                    # UI-specific service layer
├── pages/                       # Multi-page application structure
└── utils/                       # UI utility functions
```

**UI Features:**
- **@organization commands**: `@faucets`, `@[org_name]` parsing
- **Chat interface**: Natural language query input
- **Rich display**: IP addresses, serial numbers, status formatting
- **Progress tracking**: Real-time operation monitoring

### Configuration (`src/config/`)
```
src/config/
└── settings.py                  # Pydantic settings (100+ config options)
```

**Configuration Management:**
- **Environment-based**: Different configs per environment
- **Type validation**: Pydantic ensures configuration correctness
- **Feature flags**: Enable/disable functionality

## Support Directories

### Testing (`tests/`)
```
tests/
├── unit/                        # Fast, isolated tests (80%+ coverage)
├── integration/                 # Database/API integration tests
├── performance/                 # Response time validation
├── mcp_tools/                   # MCP tool-specific testing
├── fixtures/                    # Test data and mocks
└── scripts/                     # Manual testing utilities
```

**Testing Strategy:**
- **Unit tests**: Individual component validation
- **Integration tests**: Multi-service interaction testing
- **Performance tests**: Response time and throughput validation
- **MCP tests**: Protocol-specific testing

### Documentation (`docs/`)
```
docs/
├── architecture/                # Dev agent required files
│   ├── coding-standards.md      # Code style and patterns
│   ├── tech-stack.md           # Technology decisions
│   └── source-tree.md          # This file
├── brownfield-architecture.md   # Complete current system state
├── QUICK_START.md              # 5-minute setup guide
├── DOCKER_DEPLOYMENT.md        # Production deployment
└── stories/                    # Epic and story documentation
```

## File Naming Conventions

### Python Modules
- **snake_case**: All Python files and modules
- **Descriptive names**: `organizations_handler.py`, `fuzzy_matcher_optimized.py`
- **Handler suffix**: For query processing modules
- **Client suffix**: For external service integrations

### Configuration Files
- **Environment files**: `.env`, `.env.example`
- **Docker files**: `docker-compose.yml`, `Dockerfile`
- **Python config**: `pyproject.toml`, `alembic.ini`

### Documentation
- **UPPERCASE**: Important project files (`README.md`, `CLAUDE.md`)
- **kebab-case**: Multi-word documentation (`quick-start.md`)
- **Descriptive**: Clear purpose indication

## Import Structure Patterns

### Standard Import Organization
```python
# Standard library (alphabetical)
import asyncio
import logging
from typing import Dict, List, Optional

# Third-party packages (alphabetical) 
import aiohttp
from pydantic import BaseModel

# Local application imports (relative)
from src.config.settings import settings
from src.services.itglue.client import ITGlueClient
```

### Circular Import Prevention
- **Lazy imports**: Import within functions when needed
- **Type checking imports**: Use `if TYPE_CHECKING:` blocks
- **Dependency injection**: Pass dependencies rather than importing

## Code Organization Patterns

### Class Structure
```python
class OrganizationsHandler:
    """Handler for organization queries with fuzzy matching."""
    
    def __init__(self, client: ITGlueClient, cache: CacheManager):
        """Initialize handler with dependencies."""
        
    async def public_method(self) -> Dict[str, Any]:
        """Public interface method."""
        
    async def _private_method(self) -> Any:
        """Private implementation detail."""
```

### Module Structure
1. **Module docstring**: Purpose and usage
2. **Imports**: Standard, third-party, local
3. **Constants**: Module-level constants
4. **Classes**: Primary functionality
5. **Functions**: Standalone utilities

## Performance Considerations

### File Size Guidelines
- **Large files identified**: `server.py` (900+ lines), `streamlit_app.py` (700+ lines)
- **Acceptable**: Core coordination files can be large
- **Split when**: Single responsibility principle violated

### Import Performance
- **Lazy loading**: Expensive imports only when needed
- **Module caching**: Python's import caching utilized
- **Startup optimization**: Critical path imports minimized

## Development Workflow Integration

### BMad Agent Files
The dev agent automatically loads these 3 files:
- **`docs/architecture/coding-standards.md`**: Code style enforcement
- **`docs/architecture/tech-stack.md`**: Technology decisions
- **`docs/architecture/source-tree.md`**: This navigation guide

### IDE Integration
- **VSCode**: Settings in `.vscode/` (if present)
- **PyCharm**: Project configuration automatic detection
- **Type checking**: mypy configuration in `pyproject.toml`

This source tree organization supports the sophisticated multi-database MCP server architecture while maintaining clear separation of concerns and development workflow integration.