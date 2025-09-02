# IT Glue MCP Server - Workflow and Code Examples

## Project Overview

This MCP (Model Context Protocol) server integrates with IT Glue API to provide natural language querying of IT documentation. The server includes a Streamlit web UI for interactive queries.

## Key Workflows

### 1. Organization Filtering Workflow

**Problem**: Queries were returning data from all organizations instead of just the specified one.

**Solution**: Implement proper company name to ID resolution and post-filtering.

```python
# Company resolution pattern
async def _resolve_company_to_id(self, company: str) -> Optional[str]:
    """Resolve company name to IT Glue organization ID."""
    # Check cache first
    if company in self._company_cache:
        return self._company_cache[company]
    
    # If already numeric, return as-is
    if company.isdigit():
        return company
        
    # Query IT Glue for organization
    orgs = await self.itglue_client.get_organizations(
        filters={"name": company}
    )
    
    # Find exact match
    for org in orgs:
        if org.name.lower() == company.lower():
            self._company_cache[company] = str(org.id)
            return str(org.id)
    
    return None  # Unresolved - will use post-filtering
```

### 2. Archive Filtering Logic

**Key Rule**: Use the `archived` field as the authoritative indicator, not status fields.

```python
# Archive filtering pattern
for config in configs:
    attrs = config.attributes if hasattr(config, 'attributes') else {}
    is_archived = attrs.get('archived', False)
    
    # Check if user wants to see archived items
    listing_archived = "list archive" in query_lower or "list archived" in query_lower
    
    # Skip archived items unless explicitly requested
    if is_archived and not listing_archived:
        continue
    
    # Process active item
    filtered_configs.append(config)
```

## Query Patterns

### Basic Organization Queries

```
# List all configurations for an organization
@faucets list configurations
@faucets list all

# List specific device types
@faucets list switches
@faucets list servers
@faucets list firewalls
@faucets list printers
@faucets list access points

# List other entity types
@faucets list contacts
@faucets list passwords
@faucets list documents

# List archived items
@faucets list archived
@faucets list archive configurations
```

### Search Queries

```
# Search for specific items
What are the network configurations for Faucets?
Show me all printers at Faucets Limited
Find servers for Faucets
```

## Configuration Types Mapping

IT Glue uses specific configuration types that we map in queries:

```python
CONFIGURATION_TYPES = {
    "switches": ["switch"],
    "servers": ["server"],
    "firewalls": ["firewall"],
    "printers": ["printer"],
    "access points": ["ubiquiti access point", "access point"],
    "workstations": ["workstation"],
    "nas": ["nas"],
    "ups": ["ups"],
    "routers": ["router"],
    "network devices": ["network device"]
}
```

## Code Examples

### 1. List Query Handler

```python
async def handle_list_query(query: str, organization_id: str):
    """Handle '@organization list [type]' queries."""
    
    query_lower = query.lower()
    
    # Determine what to list
    if "list contacts" in query_lower:
        return await list_contacts(organization_id)
    elif "list passwords" in query_lower:
        return await list_passwords(organization_id)
    elif "list documents" in query_lower:
        return await list_documents(organization_id)
    else:
        # Handle configuration types
        return await list_configurations(query_lower, organization_id)
```

### 2. Configuration Type Filtering

```python
def filter_by_configuration_type(configs, query_lower):
    """Filter configurations by type based on query."""
    
    # Map query terms to configuration types
    type_keywords = {
        "switch": ["switch"],
        "server": ["server"],
        "firewall": ["firewall"],
        "printer": ["printer"],
        "access point": ["ubiquiti access point", "access point"],
        "router": ["router"],
        "nas": ["nas"],
        "ups": ["ups"],
        "workstation": ["workstation"]
    }
    
    # Find matching type
    for keyword, types in type_keywords.items():
        if keyword in query_lower:
            return [c for c in configs 
                   if any(t in (c.configuration_type or "").lower() 
                         for t in types)]
    
    return configs  # Return all if no type specified
```

### 3. Result Formatting

```python
def format_configuration_result(config):
    """Format a configuration for display."""
    
    attrs = config.attributes if hasattr(config, 'attributes') else {}
    
    result = {
        "name": config.name,
        "type": config.configuration_type,
        "status": attrs.get('configuration-status-name', 'Unknown'),
        "archived": attrs.get('archived', False),
        "primary_ip": attrs.get('primary-ip'),
        "location": attrs.get('location-name')
    }
    
    # Filter out None values
    return {k: v for k, v in result.items() if v is not None}
```

## Testing Workflow

### 1. Verify Organization Data

```python
# Test script: discover_config_types.py
# Lists all configuration types and counts
python discover_config_types.py
```

### 2. Check Archive Status

```python
# Test script: verify_archive_counts.py
# Shows active vs archived counts
python verify_archive_counts.py
```

### 3. Test Queries in Streamlit

```bash
# Run Streamlit app
streamlit run src/ui/streamlit_app.py

# Test queries:
# 1. Select organization from dropdown
# 2. Try various list queries
# 3. Verify counts match expectations
```

## Troubleshooting

### Issue: Limited Results (6-10 items only)

**Cause**: Hardcoded limits in query functions.

**Fix**: Remove all limits:
```python
# Before (LIMITED)
configs = await client.get_configurations(org_id=org_id)[:10]

# After (ALL RESULTS)
configs = await client.get_configurations(org_id=org_id)
```

### Issue: Wrong Entity Type Returned

**Example**: "@faucets list access points" showing passwords.

**Cause**: Keyword overlap ("access" triggers password search).

**Fix**: Order matters in conditional checks:
```python
# Check specific phrases first
if "access point" in query_lower:
    # Handle access points
elif "access" in query_lower:
    # Handle passwords
```

### Issue: Archived Items Showing

**Fix**: Always check the `archived` field:
```python
if config.attributes.get('archived', False):
    continue  # Skip archived items
```

## Performance Optimizations

### 1. Caching Organization IDs

```python
class QueryEngine:
    def __init__(self):
        self._company_cache = {}  # Cache org name -> ID mappings
```

### 2. Batch Fetching

```python
# Fetch all data once, then filter
configs = await client.get_configurations(org_id=org_id)
filtered = [c for c in configs if not c.attributes.get('archived')]
```

### 3. Early Returns

```python
# Return immediately when organization not found
if not org_id:
    return {"error": "Organization not found"}
```

## Current Statistics (Faucets Limited)

- **Total Configurations**: 96
- **Active Configurations**: 15
- **Archived Configurations**: 81
- **Configuration Types**: 12 unique types

### Active Configuration Breakdown:
- Firewall: 3 items
- Switch: 3 items  
- Ubiquiti Access Point: 3 items
- Server: 2 items
- NAS: 2 items
- Printer: 1 item
- UPS: 1 item

## Future Enhancements

1. **Connect Streamlit to MCP Server**: Currently Streamlit calls IT Glue directly instead of using the MCP server.

2. **Add Pagination**: For organizations with hundreds of items.

3. **Export Functionality**: Allow exporting query results to CSV/JSON.

4. **Advanced Filtering**: Support date ranges, multiple statuses, etc.

5. **Query History**: Track and replay previous queries.

## Query Examples That Work

```
# Organization-specific queries
@faucets list all
@faucets list configurations
@faucets list switches
@faucets list servers  
@faucets list printers
@faucets list access points
@faucets list contacts
@faucets list passwords
@faucets list documents
@faucets list archived

# Natural language queries
What are the network configurations for Faucets?
Show me all active servers at Faucets Limited
Find printers for Faucets
List archived configurations for Faucets

# Search queries (when organization selected in dropdown)
network devices
firewall configurations
ubiquiti access points
```

## Key Learnings

1. **Always verify data sources**: The Streamlit app wasn't using the MCP server, causing confusion during debugging.

2. **Use authoritative fields**: The `archived` field is more reliable than status fields.

3. **Test with real data**: Discovery scripts revealed the actual configuration types and counts.

4. **Remove artificial limits**: Default limits can hide data and confuse users.

5. **Handle name variations**: "Faucets" vs "Faucets Limited" - implement fuzzy matching.

6. **Order matters in parsing**: Check specific phrases before general keywords.