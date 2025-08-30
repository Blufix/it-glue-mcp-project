# IT Glue MCP Server - Development Workflow Guide 🛠️

## Overview

This guide establishes development workflows, standards, and best practices for contributing to the IT Glue MCP Server project. It covers everything from setting up your development environment to deploying code to production.

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Git Workflow & Branching Strategy](#git-workflow--branching-strategy)
3. [Development Process](#development-process)
4. [Code Standards & Style Guide](#code-standards--style-guide)
5. [Testing Requirements](#testing-requirements)
6. [Code Review Process](#code-review-process)
7. [Documentation Standards](#documentation-standards)
8. [Release Process](#release-process)
9. [Debugging & Profiling](#debugging--profiling)
10. [Development Tools & Scripts](#development-tools--scripts)

## Development Environment Setup

### Prerequisites

```bash
# Required tools
python >= 3.11
node >= 18.0.0
docker >= 24.0.0
docker-compose >= 2.20.0
git >= 2.40.0
make >= 4.3

# Development tools
poetry >= 1.6.0  # Python dependency management
pre-commit >= 3.5.0  # Git hooks
black >= 23.0.0  # Code formatting
ruff >= 0.1.0  # Linting
mypy >= 1.7.0  # Type checking
```

### Initial Setup

#### 1. Clone Repository

```bash
# Clone with SSH (recommended)
git clone git@github.com:your-org/itglue-mcp-server.git
cd itglue-mcp-server

# Or with HTTPS
git clone https://github.com/your-org/itglue-mcp-server.git
cd itglue-mcp-server
```

#### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env.development

# Edit with your settings
nano .env.development

# Required environment variables
export IT_GLUE_API_KEY="your_dev_api_key"
export DATABASE_URL="postgresql://user:pass@localhost/itglue_dev"
export REDIS_URL="redis://localhost:6379/0"
```

#### 3. Python Environment

```bash
# Using Poetry (recommended)
poetry install --with dev
poetry shell

# Or using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### 4. Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install
pre-commit install --hook-type commit-msg

# Run hooks manually
pre-commit run --all-files
```

#### 5. Docker Services

```bash
# Start development services
docker-compose -f docker-compose.dev.yml up -d

# Verify services
docker-compose ps
docker-compose logs -f

# Stop services
docker-compose down
```

### IDE Configuration

#### VS Code

```json
// .vscode/settings.json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.rulers": [88],
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

#### PyCharm

```xml
<!-- .idea/codeStyles/Project.xml -->
<component name="ProjectCodeStyleConfiguration">
  <code_scheme name="Project" version="173">
    <Python>
      <option name="RIGHT_MARGIN" value="88" />
      <option name="OPTIMIZE_IMPORTS_ON_THE_FLY" value="true" />
      <option name="SORT_IMPORTS" value="true" />
    </Python>
  </code_scheme>
</component>
```

## Git Workflow & Branching Strategy

### Branch Naming Convention

```
feature/ISSUE-description  # New features
bugfix/ISSUE-description   # Bug fixes
hotfix/ISSUE-description   # Production hotfixes
chore/ISSUE-description    # Maintenance tasks
docs/ISSUE-description     # Documentation updates
refactor/ISSUE-description # Code refactoring
```

### Branching Strategy

```mermaid
gitGraph
    commit
    branch develop
    checkout develop
    commit
    branch feature/123-new-feature
    checkout feature/123-new-feature
    commit
    commit
    checkout develop
    merge feature/123-new-feature
    branch release/1.0.0
    checkout release/1.0.0
    commit
    checkout main
    merge release/1.0.0 tag: "v1.0.0"
    checkout develop
    merge release/1.0.0
```

### Workflow Steps

#### 1. Start New Feature

```bash
# Update develop branch
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/123-query-optimization

# Make changes
git add .
git commit -m "feat: optimize vector search queries

- Implement caching for frequent queries
- Add query result pagination
- Improve response time by 40%

Closes #123"
```

#### 2. Keep Branch Updated

```bash
# Regularly sync with develop
git checkout develop
git pull origin develop
git checkout feature/123-query-optimization
git rebase develop

# Resolve conflicts if any
git status
git add .
git rebase --continue
```

#### 3. Submit Pull Request

```bash
# Push branch
git push origin feature/123-query-optimization

# Create PR via CLI (using GitHub CLI)
gh pr create \
  --title "feat: optimize vector search queries" \
  --body "## Description
  Optimizes vector search performance
  
  ## Changes
  - Implement query caching
  - Add pagination
  - Improve response time
  
  ## Testing
  - Unit tests added
  - Performance benchmarks included
  
  Closes #123" \
  --base develop \
  --reviewer @teamlead
```

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (formatting, missing semi-colons, etc)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Testing
- `chore`: Maintenance
- `ci`: CI/CD changes

**Examples:**

```bash
# Feature
git commit -m "feat(api): add batch query endpoint

Implement endpoint for processing multiple queries in single request
- Add /api/batch endpoint
- Support up to 10 queries per batch
- Include rate limiting

Closes #234"

# Bug fix
git commit -m "fix(auth): resolve token expiration issue

Token expiration was not being validated correctly
- Fix JWT expiration check
- Add proper error handling
- Include unit tests

Fixes #567"

# Breaking change
git commit -m "feat(api)!: change response format

BREAKING CHANGE: API response structure has changed
- Results now nested under 'data' key
- Added pagination metadata
- Removed deprecated fields

Migration guide in docs/migration/v2.md"
```

## Development Process

### Feature Development Workflow

#### 1. Planning Phase

```markdown
## Feature Specification

**Feature**: Advanced Query Filtering
**Issue**: #456
**Epic**: Query Enhancement

### Requirements
- [ ] Support metadata filtering
- [ ] Implement date range queries
- [ ] Add regex pattern matching

### Technical Design
- Use PostgreSQL full-text search
- Implement caching layer
- Add query validation

### Testing Strategy
- Unit tests for validators
- Integration tests for filters
- Performance benchmarks
```

#### 2. Implementation Phase

```python
# src/features/query_filtering.py
"""
Advanced query filtering implementation.

This module provides enhanced filtering capabilities for documentation queries.
"""

from typing import Dict, List, Optional
from datetime import datetime
from src.models import Query, Filter

class QueryFilter:
    """Handles advanced query filtering logic."""
    
    def __init__(self, filters: Dict[str, any]):
        """
        Initialize query filter.
        
        Args:
            filters: Dictionary of filter criteria
        """
        self.filters = self._validate_filters(filters)
    
    def apply(self, query: Query) -> Query:
        """
        Apply filters to query.
        
        Args:
            query: Base query object
            
        Returns:
            Filtered query object
        """
        for filter_type, filter_value in self.filters.items():
            query = self._apply_filter(query, filter_type, filter_value)
        return query
    
    def _validate_filters(self, filters: Dict) -> Dict:
        """Validate and sanitize filter inputs."""
        # Implementation here
        pass
    
    def _apply_filter(self, query: Query, filter_type: str, value: any) -> Query:
        """Apply individual filter to query."""
        # Implementation here
        pass
```

#### 3. Testing Phase

```python
# tests/features/test_query_filtering.py
import pytest
from src.features.query_filtering import QueryFilter

class TestQueryFilter:
    """Test cases for query filtering."""
    
    @pytest.fixture
    def sample_filters(self):
        """Provide sample filter data."""
        return {
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
            "document_type": ["password", "configuration"],
            "company_id": "123"
        }
    
    def test_filter_initialization(self, sample_filters):
        """Test filter initialization and validation."""
        filter_obj = QueryFilter(sample_filters)
        assert filter_obj.filters is not None
        assert "date_range" in filter_obj.filters
    
    def test_apply_date_filter(self):
        """Test date range filtering."""
        # Test implementation
        pass
    
    @pytest.mark.parametrize("filter_type,expected", [
        ("document_type", ["password"]),
        ("company_id", "123"),
    ])
    def test_individual_filters(self, filter_type, expected):
        """Test individual filter types."""
        # Test implementation
        pass
```

### Daily Development Routine

```bash
# Morning routine
git checkout develop
git pull origin develop
git checkout -b feature/today-task

# During development
make lint          # Run linters
make format        # Format code
make test-unit     # Run unit tests
make test-integration  # Run integration tests

# Before commit
pre-commit run --all-files
git add .
git commit -m "feat: implement feature"

# End of day
git push origin feature/today-task
gh pr create  # Create pull request
```

## Code Standards & Style Guide

### Python Standards

#### Code Style

```python
# Good example
from typing import Optional, List, Dict
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DocumentQuery:
    """Represents a document search query."""
    
    text: str
    filters: Optional[Dict[str, any]] = None
    limit: int = 10
    
    def validate(self) -> bool:
        """Validate query parameters."""
        if not self.text or len(self.text.strip()) == 0:
            logger.error("Query text cannot be empty")
            return False
        
        if self.limit < 1 or self.limit > 100:
            logger.error(f"Invalid limit: {self.limit}")
            return False
        
        return True


class QueryProcessor:
    """Processes document queries."""
    
    def __init__(self, vector_store: VectorStore):
        """
        Initialize query processor.
        
        Args:
            vector_store: Vector storage backend
        """
        self.vector_store = vector_store
        self._cache = {}
    
    async def process(self, query: DocumentQuery) -> List[Document]:
        """
        Process a document query.
        
        Args:
            query: Query to process
            
        Returns:
            List of matching documents
            
        Raises:
            ValueError: If query is invalid
        """
        if not query.validate():
            raise ValueError("Invalid query")
        
        # Check cache
        cache_key = self._get_cache_key(query)
        if cache_key in self._cache:
            logger.info(f"Cache hit for query: {query.text[:50]}...")
            return self._cache[cache_key]
        
        # Process query
        results = await self._execute_query(query)
        
        # Cache results
        self._cache[cache_key] = results
        
        return results
```

#### Type Hints

```python
from typing import TypeVar, Generic, Protocol, Union, Literal
from collections.abc import Sequence

T = TypeVar('T')

class Searchable(Protocol):
    """Protocol for searchable objects."""
    
    def search(self, query: str) -> Sequence[str]:
        """Search method signature."""
        ...

class Repository(Generic[T]):
    """Generic repository pattern."""
    
    def __init__(self) -> None:
        self._items: List[T] = []
    
    def add(self, item: T) -> None:
        """Add item to repository."""
        self._items.append(item)
    
    def find(self, predicate: Callable[[T], bool]) -> Optional[T]:
        """Find item matching predicate."""
        return next((item for item in self._items if predicate(item)), None)

# Use Union types appropriately
ResponseType = Union[Dict[str, any], List[Dict], str]

# Use Literal for specific values
Status = Literal["pending", "processing", "completed", "failed"]
```

### Code Quality Tools

#### Linting Configuration

```toml
# pyproject.toml
[tool.ruff]
line-length = 88
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = ["E501"]  # Line too long (handled by black)

[tool.black]
line-length = 88
target-version = ['py311']

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_unimported = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
```

#### Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      
  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black
        
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]
        
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

## Testing Requirements

### Test Coverage Requirements

```yaml
# Minimum coverage requirements
coverage:
  minimum:
    overall: 80%
    critical_paths: 95%
    new_code: 90%
  
  critical_paths:
    - src/services/query_handler.py
    - src/services/validation.py
    - src/auth/
    - src/api/endpoints/
```

### Test Structure

```python
# tests/test_structure_example.py
"""
Test module structure example.

Follow AAA pattern: Arrange, Act, Assert
"""

import pytest
from unittest.mock import Mock, patch
from src.module import MyClass

class TestMyClass:
    """Test cases for MyClass."""
    
    @pytest.fixture
    def instance(self):
        """Provide MyClass instance."""
        return MyClass()
    
    @pytest.fixture
    def mock_dependency(self):
        """Provide mocked dependency."""
        with patch('src.module.external_service') as mock:
            yield mock
    
    def test_should_perform_action_when_condition_met(self, instance, mock_dependency):
        """
        Test that action is performed when condition is met.
        
        Given: Valid input and mocked dependency
        When: Method is called with valid parameters
        Then: Expected action should be performed
        """
        # Arrange
        mock_dependency.return_value = {"status": "success"}
        input_data = {"key": "value"}
        
        # Act
        result = instance.perform_action(input_data)
        
        # Assert
        assert result is not None
        assert result["status"] == "completed"
        mock_dependency.assert_called_once_with(input_data)
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test categories
make test-unit
make test-integration
make test-e2e

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Run specific test file
pytest tests/services/test_query_handler.py -v

# Run tests matching pattern
pytest -k "test_query" -v

# Run tests in parallel
pytest -n auto

# Run with specific markers
pytest -m "not slow"
```

## Code Review Process

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- List specific changes
- Include technical details
- Reference related issues

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Tests added/updated
- [ ] All tests passing

## Screenshots (if applicable)
Add screenshots for UI changes

## Performance Impact
Describe any performance implications

## Migration Guide (if breaking change)
Steps to migrate existing code
```

### Review Guidelines

#### For Reviewers

```python
"""
Code Review Checklist

1. Functionality
   - Does the code do what it's supposed to?
   - Are edge cases handled?
   - Is error handling appropriate?

2. Design
   - Is the code well-structured?
   - Does it follow SOLID principles?
   - Is it maintainable?

3. Performance
   - Are there any obvious performance issues?
   - Is caching used appropriately?
   - Are database queries optimized?

4. Security
   - Are inputs validated?
   - Is sensitive data protected?
   - Are there SQL injection risks?

5. Testing
   - Are tests comprehensive?
   - Do tests cover edge cases?
   - Are mocks used appropriately?

6. Documentation
   - Is the code self-documenting?
   - Are complex parts commented?
   - Is API documentation updated?
"""

# Example review comment
"""
Consider using a more efficient data structure here.
A set would provide O(1) lookup instead of O(n) with a list.

Suggested change:
```python
valid_types = {'password', 'configuration', 'guide'}
if doc_type in valid_types:
    # process
```
"""
```

#### For Authors

```bash
# Before requesting review
make lint
make format
make test
pre-commit run --all-files

# Self-review checklist
git diff develop...HEAD  # Review all changes
# - Check for debug code
# - Verify no secrets committed
# - Ensure consistent naming
# - Remove commented code
# - Check for TODOs

# Request review
gh pr create --draft  # Create draft first
# Make final adjustments
gh pr ready  # Mark ready for review
```

### Review Response Time

- **Critical/Hotfix**: Within 1 hour
- **Regular PR**: Within 4 hours
- **Large PR (>500 lines)**: Within 24 hours

## Documentation Standards

### Code Documentation

```python
"""
Module documentation example.

This module provides functionality for X, Y, and Z.
It is primarily used by the A and B components.

Example:
    Basic usage of this module:
    
    >>> from my_module import MyClass
    >>> instance = MyClass()
    >>> result = instance.process("data")
    >>> print(result)

Note:
    This module requires Python 3.11+ and the following packages:
    - numpy
    - pandas

Attributes:
    MODULE_CONSTANT (str): Description of module constant
    
Todo:
    * Add support for feature X
    * Optimize performance of method Y
"""

from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class MyClass:
    """
    Brief description of class purpose.
    
    Longer description explaining the class's role in the system,
    its main responsibilities, and any important design decisions.
    
    Attributes:
        attribute1: Description of attribute1
        attribute2: Description of attribute2
    
    Example:
        >>> obj = MyClass(param1="value")
        >>> obj.method()
        'result'
    """
    
    def __init__(self, param1: str, param2: Optional[int] = None):
        """
        Initialize MyClass instance.
        
        Args:
            param1: Description of param1
            param2: Description of param2. Defaults to None.
            
        Raises:
            ValueError: If param1 is empty
        """
        if not param1:
            raise ValueError("param1 cannot be empty")
        
        self.param1 = param1
        self.param2 = param2 or 10
    
    def complex_method(
        self,
        data: Dict[str, List[str]],
        options: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Perform complex operation on data.
        
        This method does X, Y, and Z. It's used primarily for A and B.
        The algorithm used is based on [reference].
        
        Args:
            data: Input data mapping keys to lists of values
            options: Optional processing options:
                - 'sort': Whether to sort results (default: True)
                - 'limit': Maximum results to return (default: 100)
        
        Returns:
            Dictionary containing:
                - 'results': Processed results
                - 'metadata': Processing metadata
                - 'errors': Any errors encountered
        
        Raises:
            ValueError: If data is malformed
            ProcessingError: If processing fails
            
        Example:
            >>> obj.complex_method(
            ...     {"key": ["val1", "val2"]},
            ...     {"sort": False}
            ... )
            {'results': [...], 'metadata': {...}, 'errors': []}
            
        Note:
            This method is CPU-intensive for large datasets.
            Consider using the async version for better performance.
            
        See Also:
            async_complex_method: Async version of this method
            simple_method: Simpler alternative for basic use cases
        """
        # Implementation
        pass
```

### API Documentation

```python
# src/api/endpoints/query.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["queries"])

class QueryRequest(BaseModel):
    """Query request model."""
    
    query: str = Field(
        ...,
        description="Natural language query text",
        example="What is the WiFi password?",
        min_length=1,
        max_length=500
    )
    company_id: str = Field(
        ...,
        description="Company identifier",
        example="comp_123",
        regex="^comp_[a-zA-Z0-9]+$"
    )
    filters: Optional[Dict] = Field(
        None,
        description="Optional filters to apply",
        example={"document_type": "password", "location": "main_office"}
    )
    limit: int = Field(
        10,
        description="Maximum number of results",
        ge=1,
        le=100
    )

@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Execute documentation query",
    description="""
    Execute a natural language query against IT documentation.
    
    This endpoint processes natural language queries and returns
    relevant documentation with confidence scores.
    """,
    responses={
        200: {
            "description": "Query executed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "results": [
                            {
                                "content": "WiFi password is: SecurePass123",
                                "confidence": 0.95,
                                "source": "Network Documentation"
                            }
                        ]
                    }
                }
            }
        },
        400: {"description": "Invalid query"},
        401: {"description": "Unauthorized"},
        429: {"description": "Rate limit exceeded"}
    }
)
async def execute_query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user)
) -> QueryResponse:
    """
    Execute a documentation query.
    
    Args:
        request: Query request parameters
        current_user: Authenticated user
        
    Returns:
        Query results with confidence scores
        
    Raises:
        HTTPException: On query errors
    """
    # Implementation
    pass
```

## Release Process

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 2.1.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Workflow

#### 1. Create Release Branch

```bash
# Create release branch from develop
git checkout develop
git pull origin develop
git checkout -b release/1.2.0

# Update version
poetry version 1.2.0  # or manually update version files
git add pyproject.toml
git commit -m "chore: bump version to 1.2.0"
```

#### 2. Release Checklist

```markdown
## Release Checklist v1.2.0

### Pre-release
- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped
- [ ] Security scan completed
- [ ] Performance benchmarks acceptable

### Release
- [ ] Release branch created
- [ ] Release notes written
- [ ] Tag created
- [ ] Docker images built
- [ ] Packages published

### Post-release
- [ ] Production deployment successful
- [ ] Smoke tests passed
- [ ] Monitoring verified
- [ ] Team notified
- [ ] Social media announcement
```

#### 3. Generate Changelog

```bash
# Generate changelog from commits
git log --pretty=format:"- %s (%h)" develop..release/1.2.0 > CHANGELOG_DRAFT.md

# Organize by category
cat CHANGELOG_DRAFT.md | grep "^- feat" > features.md
cat CHANGELOG_DRAFT.md | grep "^- fix" > fixes.md

# Update CHANGELOG.md
```

#### 4. Create Release

```bash
# Merge to main
git checkout main
git merge --no-ff release/1.2.0

# Tag release
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin main --tags

# Merge back to develop
git checkout develop
git merge --no-ff release/1.2.0
git push origin develop

# Create GitHub release
gh release create v1.2.0 \
  --title "Release v1.2.0" \
  --notes-file RELEASE_NOTES.md \
  --target main
```

#### 5. Deploy to Production

```bash
# Build and push Docker images
make docker-build VERSION=1.2.0
make docker-push VERSION=1.2.0

# Deploy to Kubernetes
kubectl set image deployment/itglue-mcp \
  itglue-mcp=itglue-mcp:1.2.0 \
  --namespace=production

# Verify deployment
kubectl rollout status deployment/itglue-mcp -n production
```

## Debugging & Profiling

### Debug Configuration

```python
# src/config/debug.py
import os
import logging
from typing import Any

DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

if DEBUG_MODE:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    # Enable SQL query logging
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    
    # Enable asyncio debug mode
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def debug_print(message: str, data: Any = None):
    """Print debug information if debug mode is enabled."""
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")
        if data:
            import pprint
            pprint.pprint(data)
```

### Performance Profiling

```python
# src/utils/profiling.py
import cProfile
import pstats
import io
from functools import wraps
import time
import tracemalloc

def profile_function(func):
    """Decorator to profile function execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        
        result = func(*args, **kwargs)
        
        profiler.disable()
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats('cumulative')
        stats.print_stats(20)
        
        print(f"\nProfile for {func.__name__}:")
        print(stream.getvalue())
        
        return result
    return wrapper

def measure_memory(func):
    """Decorator to measure memory usage."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        tracemalloc.start()
        
        result = func(*args, **kwargs)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        print(f"\n{func.__name__} memory usage:")
        print(f"  Current: {current / 1024 / 1024:.2f} MB")
        print(f"  Peak: {peak / 1024 / 1024:.2f} MB")
        
        return result
    return wrapper

class Timer:
    """Context manager for timing code blocks."""
    
    def __init__(self, name: str = "Block"):
        self.name = name
        self.start = None
    
    def __enter__(self):
        self.start = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        elapsed = time.perf_counter() - self.start
        print(f"{self.name} took {elapsed:.4f} seconds")
```

### Debug Commands

```bash
# Run with debug logging
DEBUG=true python -m src.main

# Run with profiling
python -m cProfile -o profile.stats src/main.py
python -m pstats profile.stats

# Memory profiling
python -m memory_profiler src/main.py

# Line profiling
kernprof -l -v src/main.py

# Debug with pdb
python -m pdb src/main.py

# Remote debugging with debugpy
python -m debugpy --listen 5678 --wait-for-client src/main.py
```

## Development Tools & Scripts

### Makefile

```makefile
# Makefile
.PHONY: help install dev test lint format clean

help:
	@echo "Available commands:"
	@echo "  install    Install dependencies"
	@echo "  dev        Run development server"
	@echo "  test       Run all tests"
	@echo "  lint       Run linters"
	@echo "  format     Format code"
	@echo "  clean      Clean build artifacts"

install:
	poetry install --with dev

dev:
	docker-compose -f docker-compose.dev.yml up -d
	poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8080

test:
	poetry run pytest

test-unit:
	poetry run pytest tests/unit -v

test-integration:
	poetry run pytest tests/integration -v

test-coverage:
	poetry run pytest --cov=src --cov-report=html --cov-report=term

lint:
	poetry run ruff check src tests
	poetry run mypy src

format:
	poetry run black src tests
	poetry run ruff check --fix src tests

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov .mypy_cache

docker-build:
	docker build -t itglue-mcp:latest .

docker-run:
	docker-compose up -d

migrate:
	poetry run alembic upgrade head

migrate-create:
	poetry run alembic revision --autogenerate -m "$(message)"

db-reset:
	poetry run alembic downgrade base
	poetry run alembic upgrade head
	poetry run python scripts/seed_data.py
```

### Development Scripts

```python
# scripts/dev_setup.py
#!/usr/bin/env python
"""
Development environment setup script.
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd: str, check: bool = True):
    """Run shell command."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, check=check)
    return result.returncode == 0

def setup_development_environment():
    """Set up complete development environment."""
    
    print("🚀 Setting up development environment...")
    
    # Check Python version
    if sys.version_info < (3, 11):
        print("❌ Python 3.11+ required")
        sys.exit(1)
    
    # Install poetry
    if not run_command("poetry --version", check=False):
        print("Installing Poetry...")
        run_command("pip install poetry")
    
    # Install dependencies
    print("Installing dependencies...")
    run_command("poetry install --with dev")
    
    # Set up pre-commit
    print("Setting up pre-commit hooks...")
    run_command("poetry run pre-commit install")
    
    # Create .env file
    if not Path(".env").exists():
        print("Creating .env file...")
        run_command("cp .env.example .env")
        print("⚠️  Please update .env with your settings")
    
    # Start Docker services
    print("Starting Docker services...")
    run_command("docker-compose -f docker-compose.dev.yml up -d")
    
    # Run database migrations
    print("Running database migrations...")
    run_command("poetry run alembic upgrade head")
    
    # Seed development data
    print("Seeding development data...")
    run_command("poetry run python scripts/seed_data.py")
    
    print("✅ Development environment ready!")
    print("\nNext steps:")
    print("1. Update .env with your API keys")
    print("2. Run 'make dev' to start the development server")
    print("3. Visit http://localhost:8080")

if __name__ == "__main__":
    setup_development_environment()
```

### Database Management Scripts

```python
# scripts/db_management.py
#!/usr/bin/env python
"""
Database management utilities.
"""

import asyncio
import click
from sqlalchemy import text
from src.database import get_db_engine

@click.group()
def cli():
    """Database management commands."""
    pass

@cli.command()
@click.option('--force', is_flag=True, help='Force reset without confirmation')
async def reset(force: bool):
    """Reset database to clean state."""
    if not force:
        click.confirm('This will delete all data. Continue?', abort=True)
    
    engine = get_db_engine()
    async with engine.begin() as conn:
        # Drop all tables
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        
        # Run migrations
        from alembic import command
        from alembic.config import Config
        
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
    
    click.echo("✅ Database reset complete")

@cli.command()
@click.option('--tables', help='Comma-separated list of tables')
async def backup(tables: str):
    """Backup database tables."""
    # Implementation
    pass

@cli.command()
@click.option('--file', required=True, help='Backup file to restore')
async def restore(file: str):
    """Restore database from backup."""
    # Implementation
    pass

if __name__ == "__main__":
    cli()
```

## Summary

This development workflow guide provides comprehensive guidelines for contributing to the IT Glue MCP Server project. Key takeaways:

1. **Environment Setup**: Standardized development environment with Docker and Poetry
2. **Git Workflow**: Clear branching strategy and commit conventions
3. **Code Standards**: Consistent style with automated formatting and linting
4. **Testing**: Comprehensive testing requirements and strategies
5. **Code Review**: Structured review process with clear guidelines
6. **Documentation**: Detailed documentation standards for code and APIs
7. **Release Process**: Systematic release workflow with versioning
8. **Development Tools**: Helpful scripts and commands for productivity

Remember:
- Follow the established patterns and conventions
- Write tests for all new code
- Document complex logic
- Request reviews early and often
- Keep the codebase clean and maintainable

Happy coding! 🚀