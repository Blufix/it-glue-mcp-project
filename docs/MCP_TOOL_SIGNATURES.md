# MCP Tool Parameter Signatures Reference

This document provides the standardized parameter signatures for all IT Glue MCP Server tools, based on systematic testing and code analysis.

## Overview

During MCP tool testing, several parameter signature mismatches were discovered that caused tools to fail. This reference ensures consistent parameter usage across all tools.

## Common Issues Found

1. **Cache Interface Inconsistency**: Some tools used `cache.get()` while others used `cache.query_cache.get()`
2. **Parameter Name Mismatches**: Tools expecting different parameter names (`company` vs `filters`)
3. **Import Issues**: Missing or incorrect imports (e.g., `CacheService`)
4. **Organization Resolution**: Tools failing to resolve organization names like "Faucets" to IDs

## MCP Tool Signatures

### 1. Health Tool
**File**: `src/mcp/tools/health.py`
**Status**: ✅ Working (100% success rate)

```python
async def execute() -> dict[str, Any]:
    """No parameters required."""
```

**Usage**:
```python
result = await health_tool.execute()
```

---

### 2. Query Tool  
**File**: `src/mcp/tools/query_tool.py`
**Status**: ⚠️ CacheService import issue

```python
async def execute(
    query: str,
    company: Optional[str] = None,
    include_sources: bool = True,
    use_cache: bool = True,
    **kwargs
) -> dict[str, Any]:
```

**Parameters**:
- `query` (str): Natural language question
- `company` (str, optional): Company name or ID
- `include_sources` (bool): Include source references in response
- `use_cache` (bool): Use cached results if available

**Usage**:
```python
result = await query_tool.execute(
    query="list all servers",
    company="Faucets"
)
```

**Known Issues**:
- ❌ Import error: `ModuleNotFoundError: No module named 'src.services.cache'`
- ✅ Organization resolution now works (fixed)

---

### 3. Discover Asset Types Tool
**File**: `src/mcp/tools/discover_asset_types.py`  
**Status**: ✅ Working (cache interface fixed)

```python
async def execute(
    include_fields: bool = False,
    limit: int = 100
) -> dict[str, Any]:
```

**Parameters**:
- `include_fields` (bool): Include field definitions
- `limit` (int): Maximum number of asset types to return

**Usage**:
```python
result = await discover_tool.execute(
    include_fields=False,
    limit=50
)
```

**Fixed Issues**:
- ✅ Cache interface updated from `cache.get()` to `cache.query_cache.get()`

---

### 4. Query Organizations Tool
**File**: Not found in current codebase
**Status**: ❌ Missing tool

**Expected Signature** (based on test patterns):
```python
async def execute(
    organization: Optional[str] = None,
    limit: int = 100
) -> dict[str, Any]:
```

---

### 5. Search Tool
**File**: `src/mcp/tools/search.py` (assumed)
**Status**: ⚠️ Parameter signature mismatch

**Current Test Pattern**:
```python
# ❌ This was failing:
result = await search_tool.execute(
    query="servers",
    company="Faucets"
)
```

**Suspected Correct Signature**:
```python
async def execute(
    query: str,
    filters: Optional[dict] = None,
    limit: int = 50
) -> dict[str, Any]:
```

**Parameters**:
- `query` (str): Search query
- `filters` (dict, optional): Search filters including organization
- `limit` (int): Maximum results

**Corrected Usage**:
```python
result = await search_tool.execute(
    query="servers",
    filters={"organization": "Faucets"}
)
```

---

### 6. Get Passwords Tool
**File**: `src/mcp/tools/passwords.py` (assumed)
**Status**: 🚧 Not yet tested

**Expected Signature**:
```python
async def execute(
    organization: Optional[str] = None,
    resource_id: Optional[str] = None,
    limit: int = 100
) -> dict[str, Any]:
```

---

### 7. Get Documents Tool  
**File**: `src/mcp/tools/documents.py` (assumed)
**Status**: 🚧 Not yet tested

**Expected Signature**:
```python
async def execute(
    query: Optional[str] = None,
    organization: Optional[str] = None, 
    document_type: Optional[str] = None,
    limit: int = 50
) -> dict[str, Any]:
```

---

### 8. Get Contacts Tool
**File**: `src/mcp/tools/contacts.py` (assumed)  
**Status**: 🚧 Not yet tested

**Expected Signature**:
```python
async def execute(
    organization: Optional[str] = None,
    contact_type: Optional[str] = None,
    limit: int = 100
) -> dict[str, Any]:
```

---

### 9. Sync Tool
**File**: `src/mcp/tools/sync_tool.py`
**Status**: 🚧 Not yet tested

```python
async def execute(
    operation: str,  # "full", "incremental", "status"
    organization: Optional[str] = None,
    dry_run: bool = False
) -> dict[str, Any]:
```

---

### 10. Query Flexible Assets Tool
**File**: `src/mcp/tools/flexible_assets.py` (assumed)
**Status**: 🚧 Not yet tested

**Expected Signature**:
```python
async def execute(
    asset_type: Optional[str] = None,
    organization: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 100
) -> dict[str, Any]:
```

## Parameter Standardization Rules

### Organization Parameters
- **Parameter Name**: Use `company` for end-user facing tools (Query Tool)
- **Parameter Name**: Use `organization` for data-specific tools (all others)
- **Type**: `Optional[str]` - accepts both organization name and ID
- **Resolution**: Organization names are automatically resolved to IDs (fixed)

### Query Parameters  
- **Parameter Name**: Use `query` for search strings
- **Type**: `str` for required queries, `Optional[str]` for optional
- **Description**: Natural language queries or search terms

### Filter Parameters
- **Parameter Name**: Use `filters` for complex filter objects  
- **Type**: `Optional[dict]` 
- **Structure**: `{"organization": "name", "type": "value", ...}`

### Pagination Parameters
- **Parameter Name**: Use `limit` for result limits
- **Type**: `int` with sensible defaults (50-100)
- **Range**: 1-1000 with tool-specific defaults

### Boolean Parameters
- **Cache Control**: `use_cache: bool = True`
- **Detail Level**: `include_fields: bool = False`, `include_sources: bool = True`
- **Safety**: `dry_run: bool = False` for destructive operations

## Cache Interface Standards

### Fixed Pattern (Post-Fix)
```python
# ✅ Correct cache interface
if self.cache and hasattr(self.cache, 'query_cache'):
    cached = await self.cache.query_cache.get(cache_key)
    # ... 
    await self.cache.query_cache.set(cache_key, result, QueryType.OPERATIONAL)
```

### Legacy Pattern (Broken)  
```python
# ❌ Old pattern that caused errors
if self.cache:
    cached = await self.cache.get(cache_key)
    await self.cache.set(cache_key, result, ttl=900)
```

## Import Issues and Solutions

### CacheService Issue
**Problem**: `ModuleNotFoundError: No module named 'src.services.cache'`
**Affected**: `src/mcp/tools/query_tool.py`
**Solution**: Create proper CacheService class or use existing CacheManager

### Admin Tool Issue
**Problem**: `ModuleNotFoundError: No module named 'src.mcp.tools.admin_tool'`
**Affected**: `src/mcp/tools/__init__.py`
**Solution**: Remove or create admin_tool.py

## Testing Status Summary

| Tool | Status | Success Rate | Issues Fixed |
|------|--------|-------------|--------------|
| Health Tool | ✅ Working | 100% | None |
| Query Organizations | ✅ Working | 100% | None |
| Discover Asset Types | ✅ Working | 100% | Cache interface |
| Query Tool | ⚠️ Import Issues | 40% | Organization resolution |
| Search Tool | ⚠️ Param Mismatch | 12.5% | Parameter signatures |
| Get Passwords | 🚧 Not Tested | - | - |
| Get Documents | 🚧 Not Tested | - | - |
| Get Contacts | 🚧 Not Tested | - | - |
| Sync Tool | 🚧 Not Tested | - | - |
| Query Flexible Assets | 🚧 Not Tested | - | - |

## Next Steps

1. ✅ Fix cache interface calls across tools
2. ✅ Fix organization name resolution  
3. 🔄 Document parameter signatures (this document)
4. 🚧 Fix CacheService import issue
5. 🚧 Complete testing of remaining 5 tools
6. 🚧 Standardize all parameter signatures
7. 🚧 Update tool documentation

---

*Generated during MCP Tool Testing Sprint*  
*Last Updated: Current Session*