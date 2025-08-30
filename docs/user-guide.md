# IT Glue MCP Server - User Guide 📚

## Welcome to IT Glue MCP Server

The IT Glue MCP Server transforms your IT documentation into an intelligent, queryable knowledge base. This guide will help you get started and make the most of the system's capabilities.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Usage](#basic-usage)
3. [Query Syntax & Examples](#query-syntax--examples)
4. [Advanced Features](#advanced-features)
5. [User Interface Guide](#user-interface-guide)
6. [API Usage](#api-usage)
7. [Common Use Cases](#common-use-cases)
8. [Tips & Best Practices](#tips--best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Keyboard Shortcuts](#keyboard-shortcuts)

## Getting Started

### First-Time Setup

1. **Access the System**
   ```
   Web Interface: https://your-domain.com
   API Endpoint: https://api.your-domain.com
   MCP Interface: Available through Claude, ChatGPT, or other MCP clients
   ```

2. **Authentication**
   ```json
   {
     "method": "authenticate",
     "params": {
       "api_key": "your_api_key_here",
       "company_id": "your_company_id"
     }
   }
   ```

3. **Verify Connection**
   ```bash
   curl -X GET https://api.your-domain.com/health \
     -H "X-API-Key: your_api_key"
   ```

### Quick Start Tutorial

#### Step 1: Your First Query

```python
# Using Python client
from itglue_mcp import Client

client = Client(api_key="your_api_key")
response = client.query("What is the WiFi password?")
print(response.answer)
```

#### Step 2: Understanding Responses

Every response includes:
- **Answer**: Direct answer to your question
- **Sources**: Documentation references used
- **Confidence**: How certain the system is (0-1 scale)
- **Related**: Additional relevant information

#### Step 3: Refining Queries

```python
# Be specific with context
response = client.query(
    "What is the WiFi password for the guest network at the main office?",
    filters={"location": "main_office", "network_type": "guest"}
)
```

## Basic Usage

### Natural Language Queries

The system understands natural language questions. Just ask like you would ask a colleague:

✅ **Good Queries:**
- "What's the admin password for server-01?"
- "Show me the network diagram for the Seattle office"
- "How do I reset a user's password in Active Directory?"
- "List all servers running Windows Server 2019"

❌ **Avoid:**
- Single words: "password"
- Ambiguous: "that server"
- Too broad: "tell me everything"

### Query Categories

| Category | Example Queries | Response Type |
|----------|----------------|---------------|
| **Passwords** | "What's the WiFi password?" | Secure credential display |
| **Configurations** | "Show MySQL configuration" | Configuration details |
| **Procedures** | "How to backup the database?" | Step-by-step guide |
| **Inventory** | "List all printers" | Table/list format |
| **Diagrams** | "Network topology diagram" | Visual diagram |
| **Contacts** | "Who manages the firewall?" | Contact information |

## Query Syntax & Examples

### Basic Syntax

```
[Action] [Entity] [Filters/Context]
```

### Query Examples by Category

#### 🔐 Credentials & Passwords

```python
# Get specific password
"What is the password for admin@company.com?"

# Get service credentials
"Show me the database credentials for the production MySQL server"

# Get WiFi passwords
"List all WiFi passwords for the branch offices"
```

#### 🖥️ Server & Infrastructure

```python
# Server information
"Show details for server PROD-WEB-01"

# Server inventory
"List all Linux servers in the DMZ"

# Service status
"Which servers are running Apache?"

# Resource allocation
"Show servers with more than 16GB RAM"
```

#### 🌐 Network Information

```python
# Network configuration
"What is the subnet mask for the guest network?"

# VLAN information
"Show VLAN configuration for the main switch"

# Firewall rules
"List firewall rules for port 443"

# IP assignments
"Which device has IP 192.168.1.100?"
```

#### 📋 Procedures & Guides

```python
# Backup procedures
"How do we backup the Exchange server?"

# Disaster recovery
"Show the disaster recovery procedure for the database"

# Maintenance tasks
"What's the monthly maintenance checklist?"

# Troubleshooting
"How to troubleshoot VPN connection issues?"
```

#### 📊 Reports & Analytics

```python
# License information
"Show all software licenses expiring this month"

# Compliance
"Generate PCI compliance checklist"

# Inventory reports
"Count of workstations by operating system"

# Change history
"Show recent changes to firewall configuration"
```

### Advanced Query Operators

#### Filtering

```python
# By time
"Show passwords changed in the last 30 days"

# By location
"List servers at the Dallas datacenter"

# By type
"Show only physical servers, not virtual"

# By status
"List active user accounts only"
```

#### Sorting & Limiting

```python
# Sort results
"List servers sorted by last backup date"

# Limit results
"Show top 5 largest databases"

# Pagination
"Show servers 10-20 from the inventory"
```

#### Aggregation

```python
# Count
"How many Windows servers do we have?"

# Sum
"Total storage capacity across all file servers"

# Average
"Average CPU usage for web servers"

# Group by
"Count of servers grouped by operating system"
```

## Advanced Features

### 🔍 Smart Search

The system uses AI to understand context and intent:

```python
# Understands synonyms
"Show me the wifi code" → Returns WiFi password

# Understands context
"What's John's extension?" → Returns phone extension for John

# Understands relationships
"Servers connected to SWITCH-01" → Returns connected servers
```

### 🔗 Cross-Reference Intelligence

Automatically finds related information:

```python
response = client.query("Show configuration for WEB-01")
# Also returns:
# - Related servers in the same cluster
# - Network connections
# - Recent changes
# - Dependent services
```

### 📈 Trend Analysis

```python
# Historical queries
"Show disk usage trend for FILE-01 over last 6 months"

# Predictive alerts
"Which servers will run out of space in the next week?"

# Change tracking
"What changed in the network configuration yesterday?"
```

### 🔒 Security Features

#### Role-Based Access

```python
# Queries respect user permissions
client = Client(api_key="user_api_key")

# User with limited access
response = client.query("Show all passwords")
# Returns: Only passwords user has permission to view

# Admin user
admin_client = Client(api_key="admin_api_key")
response = admin_client.query("Show all passwords")
# Returns: All passwords in the system
```

#### Audit Logging

All queries are logged for security:

```python
# View your query history
history = client.get_query_history(days=7)
for query in history:
    print(f"{query.timestamp}: {query.text}")
```

## User Interface Guide

### Web Dashboard

#### Main Components

```
┌─────────────────────────────────────────────┐
│  🔍 Search Bar                              │
├─────────────────┬───────────────────────────┤
│                 │                           │
│  Quick Actions  │      Results Area         │
│                 │                           │
│  • Passwords    │   Answer: ...             │
│  • Servers      │                           │
│  • Networks     │   Sources: [1] [2] [3]    │
│  • Procedures   │                           │
│                 │   Related: ...            │
├─────────────────┴───────────────────────────┤
│           Recent Queries History            │
└─────────────────────────────────────────────┘
```

#### Search Interface

1. **Smart Suggestions**: As you type, see suggested queries
2. **Query Builder**: Use the visual builder for complex queries
3. **Filters Panel**: Apply filters before searching
4. **Save Queries**: Save frequently used queries

#### Results Display

- **Card View**: Visual cards for each result
- **Table View**: Structured data in tables
- **Detail View**: Full documentation view
- **Export Options**: PDF, CSV, JSON formats

### Mobile App

#### Key Features

- **Offline Mode**: Cache critical documentation
- **Voice Search**: "Hey, what's the WiFi password?"
- **Quick Actions**: One-tap common queries
- **Push Notifications**: Alerts for documentation updates

#### Mobile-Optimized Queries

```python
# Shortened queries for mobile
"wifi pass main office"
"backup procedure"
"john phone"
```

## API Usage

### REST API

#### Authentication

```bash
# Using API Key
curl -H "X-API-Key: your_api_key" \
     https://api.your-domain.com/query

# Using Bearer Token
curl -H "Authorization: Bearer your_token" \
     https://api.your-domain.com/query
```

#### Query Endpoint

```bash
# POST /api/query
curl -X POST https://api.your-domain.com/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "query": "What is the backup schedule?",
    "company_id": "123",
    "filters": {
      "document_type": "procedure"
    },
    "limit": 5
  }'
```

#### Response Format

```json
{
  "success": true,
  "answer": "Backups run daily at 2:00 AM EST",
  "confidence": 0.95,
  "sources": [
    {
      "id": "doc_456",
      "title": "Backup Procedures",
      "snippet": "...daily at 2:00 AM EST...",
      "url": "https://..."
    }
  ],
  "related": [
    {
      "title": "Restore Procedures",
      "relevance": 0.8
    }
  ],
  "query_id": "qry_789",
  "execution_time_ms": 145
}
```

### Python SDK

```python
from itglue_mcp import Client, QueryOptions

# Initialize client
client = Client(
    api_key="your_api_key",
    base_url="https://api.your-domain.com"
)

# Simple query
response = client.query("Show all servers")

# Advanced query with options
options = QueryOptions(
    filters={"os": "linux"},
    sort_by="hostname",
    limit=10,
    include_related=True
)
response = client.query("List servers", options=options)

# Async query
async def async_query():
    response = await client.async_query("Complex analysis query")
    return response
```

### JavaScript/Node.js SDK

```javascript
const { ITGlueMCP } = require('@itglue/mcp-client');

// Initialize
const client = new ITGlueMCP({
  apiKey: 'your_api_key',
  baseUrl: 'https://api.your-domain.com'
});

// Query
client.query('What is the WiFi password?')
  .then(response => {
    console.log('Answer:', response.answer);
    console.log('Confidence:', response.confidence);
  })
  .catch(error => {
    console.error('Error:', error);
  });

// With async/await
async function getServerInfo() {
  try {
    const response = await client.query('Show details for WEB-01');
    return response;
  } catch (error) {
    console.error('Query failed:', error);
  }
}
```

## Common Use Cases

### Daily Operations

#### Morning Checklist

```python
# Create a morning routine query
morning_checks = [
    "Show any servers with critical alerts",
    "List backups that failed last night",
    "Show disk space below 10% free",
    "Display expiring certificates within 30 days"
]

for check in morning_checks:
    response = client.query(check)
    print(f"✓ {check}: {response.summary}")
```

#### Password Lookups

```python
# Quick password retrieval
def get_password(service_name):
    response = client.query(
        f"What is the password for {service_name}?",
        options={"secure_display": True}
    )
    return response.secure_answer
```

### Troubleshooting

#### Network Issues

```python
# Diagnose network problems
def troubleshoot_network(device_name):
    queries = [
        f"Show network configuration for {device_name}",
        f"Recent changes to {device_name}",
        f"Devices connected to {device_name}",
        f"Error logs for {device_name} in last 24 hours"
    ]
    
    diagnosis = {}
    for query in queries:
        diagnosis[query] = client.query(query)
    
    return diagnosis
```

#### Service Outages

```python
# Quick service recovery information
def service_recovery(service_name):
    recovery_info = client.query(
        f"Show recovery procedure for {service_name}",
        options={"format": "step_by_step"}
    )
    
    contacts = client.query(
        f"Emergency contacts for {service_name}"
    )
    
    return {
        "steps": recovery_info.steps,
        "contacts": contacts.results,
        "estimated_time": recovery_info.estimated_duration
    }
```

### Compliance & Auditing

#### Compliance Reports

```python
# Generate compliance checklist
def compliance_check(standard="PCI"):
    response = client.query(
        f"Generate {standard} compliance checklist",
        options={"include_evidence": True}
    )
    
    return {
        "compliant_items": response.compliant,
        "non_compliant": response.non_compliant,
        "evidence_links": response.evidence
    }
```

#### Audit Trails

```python
# Get audit information
def audit_trail(resource, days=30):
    response = client.query(
        f"Show all changes to {resource} in last {days} days",
        options={"include_user": True, "include_diff": True}
    )
    
    return response.changes
```

### Reporting

#### Executive Summaries

```python
# Generate executive report
def executive_summary():
    metrics = {
        "total_servers": client.query("Count all servers"),
        "critical_issues": client.query("Count critical alerts"),
        "backup_success": client.query("Backup success rate this month"),
        "uptime": client.query("Average uptime this month"),
        "incidents": client.query("Count of incidents this month")
    }
    
    return format_executive_report(metrics)
```

#### Inventory Reports

```python
# Generate inventory report
def inventory_report(category="all"):
    if category == "all":
        categories = ["servers", "workstations", "network_devices", "software"]
    else:
        categories = [category]
    
    inventory = {}
    for cat in categories:
        inventory[cat] = client.query(f"List all {cat} with details")
    
    return generate_report(inventory)
```

## Tips & Best Practices

### Query Optimization

#### Be Specific

```python
# ❌ Too vague
"password"

# ✅ Specific
"What is the admin password for the production MySQL database?"
```

#### Use Context

```python
# ❌ Missing context
"Show configuration"

# ✅ With context
"Show Apache configuration for the web server WEB-PROD-01"
```

#### Specify Time Frames

```python
# ❌ No time frame
"Show changes"

# ✅ With time frame
"Show network configuration changes in the last 7 days"
```

### Performance Tips

1. **Cache Common Queries**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def get_cached_info(query):
       return client.query(query)
   ```

2. **Batch Related Queries**
   ```python
   # Instead of multiple queries
   responses = client.batch_query([
       "Server details for WEB-01",
       "Network config for WEB-01",
       "Recent changes to WEB-01"
   ])
   ```

3. **Use Filters Early**
   ```python
   # Filter at query time, not after
   response = client.query(
       "List servers",
       filters={"os": "linux", "environment": "production"}
   )
   ```

### Security Best Practices

1. **Never Share API Keys**
   ```python
   # Use environment variables
   import os
   api_key = os.environ.get('ITGLUE_API_KEY')
   ```

2. **Rotate Keys Regularly**
   ```python
   # Set up key rotation
   client.rotate_api_key(old_key, new_key)
   ```

3. **Use Least Privilege**
   ```python
   # Create role-specific clients
   read_only_client = Client(api_key=read_only_key)
   admin_client = Client(api_key=admin_key)
   ```

## Troubleshooting

### Common Issues

#### No Results Found

**Problem**: Query returns no results
```python
# Debugging steps
response = client.query("your query", debug=True)
print(response.debug_info)
```

**Solutions**:
1. Check spelling and typos
2. Broaden the search terms
3. Remove unnecessary filters
4. Verify permissions

#### Slow Responses

**Problem**: Queries take too long
```python
# Check performance
response = client.query("your query", profile=True)
print(f"Execution time: {response.execution_time_ms}ms")
```

**Solutions**:
1. Use more specific queries
2. Add filters to reduce search scope
3. Enable query caching
4. Check system status

#### Authentication Errors

**Problem**: API key not working
```bash
# Test authentication
curl -I -H "X-API-Key: your_key" https://api.your-domain.com/health
```

**Solutions**:
1. Verify API key is correct
2. Check key hasn't expired
3. Confirm IP whitelist settings
4. Verify account is active

### Error Messages

| Error Code | Message | Solution |
|------------|---------|----------|
| 401 | Unauthorized | Check API key |
| 403 | Forbidden | Verify permissions |
| 404 | Not Found | Check query syntax |
| 429 | Rate Limited | Reduce request frequency |
| 500 | Server Error | Contact support |

### Debug Mode

Enable debug mode for detailed information:

```python
# Python
client = Client(api_key="key", debug=True)
response = client.query("test query")
print(response.debug_log)

# CLI
itglue-mcp query "test query" --debug

# API
curl -X POST https://api.your-domain.com/api/query \
  -H "X-Debug: true" \
  -d '{"query": "test query"}'
```

## Keyboard Shortcuts

### Web Interface

| Shortcut | Action |
|----------|--------|
| `/` | Focus search bar |
| `Ctrl+K` | Quick search |
| `Ctrl+Enter` | Submit query |
| `Ctrl+S` | Save query |
| `Ctrl+H` | Show history |
| `Ctrl+F` | Filter results |
| `Ctrl+E` | Export results |
| `Esc` | Clear search |
| `?` | Show help |

### CLI Shortcuts

| Shortcut | Action |
|----------|--------|
| `↑/↓` | Navigate history |
| `Tab` | Auto-complete |
| `Ctrl+R` | Search history |
| `Ctrl+L` | Clear screen |
| `Ctrl+C` | Cancel query |

## Getting Help

### Resources

- **Documentation**: https://docs.your-domain.com
- **API Reference**: https://api.your-domain.com/docs
- **Video Tutorials**: https://learn.your-domain.com
- **Community Forum**: https://community.your-domain.com

### Support Channels

- **Email**: support@your-domain.com
- **Chat**: Available in the web interface
- **Phone**: 1-800-XXX-XXXX (Business hours)
- **Slack**: #itglue-mcp-support

### Feedback

We value your feedback! Submit suggestions through:

```python
client.submit_feedback(
    type="feature_request",
    message="Your feedback here"
)
```

## Summary

The IT Glue MCP Server makes IT documentation instantly accessible through natural language queries. Key takeaways:

1. **Natural Language**: Just ask questions naturally
2. **Smart Search**: AI understands context and intent
3. **Secure**: Role-based access and audit logging
4. **Fast**: Instant answers to common questions
5. **Integrated**: Works with your existing tools

Start with simple queries and gradually explore advanced features. The system learns from usage patterns to provide increasingly relevant results.

Happy querying! 🚀