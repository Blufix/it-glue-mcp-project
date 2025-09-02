# Infrastructure Documentation Feature

The IT Glue MCP Server includes a powerful infrastructure documentation generation feature that creates comprehensive documentation for an entire organization's IT infrastructure.

## Overview

The infrastructure documentation feature queries all IT Glue resources for an organization and generates a professional, markdown-formatted document containing:

- Complete configuration inventory
- Network topology and details
- Contact information
- Location details  
- Flexible assets (SSL certificates, warranties, etc.)
- Domain information
- Document library references
- Password vault metadata (no actual passwords)

## Usage

### MCP Command

To generate infrastructure documentation for an organization, you can use either the organization ID or name:

```
@organisations <organization_id_or_name> document infrastructure
```

Examples:
```
# Using organization ID
@organisations 12345 document infrastructure

# Using organization name
@organisations bawso document infrastructure
@bawso document infrastructure
```

### Parameters

- `organization_id` (required): The IT Glue organization ID (numeric) or organization name (will be resolved automatically)
- `include_embeddings` (optional, default: true): Generate embeddings for semantic search
- `upload_to_itglue` (optional, default: false): Upload the generated document to IT Glue

### Response

The command returns:

```json
{
  "success": true,
  "snapshot_id": "550e8400-e29b-41d4-a716-446655440000",
  "organization": {
    "id": "12345",
    "name": "Acme Corporation"
  },
  "statistics": {
    "total_resources": 487,
    "configurations": 145,
    "flexible_assets": 89,
    "contacts": 67,
    "locations": 12,
    "documents": 174
  },
  "document": {
    "size_bytes": 245789,
    "url": "https://yourdomain.itglue.com/organizations/12345/docs/67890"
  },
  "duration_seconds": 95.3,
  "embeddings_generated": true,
  "uploaded_to_itglue": true
}
```

## Features

### 1. Efficient API Querying

- **Parallel Processing**: Queries multiple resource types simultaneously
- **Rate Limiting**: Respects IT Glue's 10 requests/second limit
- **Pagination Handling**: Automatically handles paginated responses
- **Retry Logic**: Implements exponential backoff for failed requests
- **Caching**: 15-minute cache for repeated queries

### 2. Data Normalization

The feature normalizes varying IT Glue API response formats into consistent structures:

- **Configurations**: Servers, workstations, network devices
- **Flexible Assets**: Custom asset types with dynamic fields
- **Contacts**: Important contacts with priority flagging
- **Locations**: Primary and secondary site information
- **Networks**: Network segments and VLANs
- **Domains**: Domain registrations and expiry dates
- **Documents**: Knowledge base references
- **Passwords**: Metadata only (categories, URLs, usernames)

### 3. Progress Tracking

Real-time progress monitoring provides:

- Current operation status
- Completion percentage
- Items processed vs. total
- Elapsed time
- Error reporting with recovery
- Step-by-step progress updates

Progress states:
- `initializing`: Setting up documentation generation
- `querying`: Fetching IT Glue resources
- `normalizing`: Processing and structuring data
- `generating_embeddings`: Creating search embeddings
- `generating_document`: Building documentation
- `uploading`: Uploading to IT Glue
- `completed`: Successfully finished
- `failed`: Error occurred

### 4. Document Generation

The generated document includes:

#### Executive Summary
- Resource overview table
- Total counts by category
- Generation metadata

#### Table of Contents
- Numbered sections with item counts
- Direct links to sections

#### Configuration Details
- Grouped by type and status
- IP addresses, operating systems, locations
- Serial numbers and asset tags
- Warranty expiration dates

#### Flexible Assets
- Organized by asset type
- Key traits and attributes
- Custom field values

#### Contact Directory
- Important contacts highlighted
- Contact details and locations
- Communication preferences

#### Location Information
- Primary locations detailed
- Full address information
- Contact numbers

#### Network Documentation
- Network segments with CIDR notation
- VLAN configurations
- Location associations

#### Domain Registry
- Domain names and registrars
- Expiration dates
- Associated notes

#### Password Vault Summary
- Categories and counts
- No actual passwords displayed
- Security-first approach

### 5. Database Persistence

All documentation generation is tracked in PostgreSQL:

- **infrastructure_snapshots**: Main documentation records
- **api_queries**: API call logging for monitoring
- **infrastructure_embeddings**: Vector embeddings for search
- **infrastructure_documents**: Generated document storage
- **infrastructure_progress**: Real-time progress tracking

### 6. Error Handling

Comprehensive error handling includes:

- Graceful degradation for missing resources
- Partial failure recovery
- Detailed error logging
- Non-fatal error continuation
- Transaction rollback on critical failures

## Performance

Typical performance metrics:

- **Small Organization** (< 100 resources): 15-30 seconds
- **Medium Organization** (100-500 resources): 30-90 seconds  
- **Large Organization** (500-2000 resources): 90-180 seconds
- **Enterprise** (2000+ resources): 3-5 minutes

Performance optimizations:
- Parallel API calls (up to 10 concurrent)
- Result caching (15-minute TTL)
- Batch processing for embeddings
- Efficient data structures
- Connection pooling

## Security

- **Read-Only Operations**: Never modifies IT Glue data
- **Password Protection**: Never displays actual passwords
- **Secure Storage**: Encrypted database storage
- **Access Control**: Organization-level permissions
- **Audit Logging**: All operations logged

## Limitations

- **Document Size**: Maximum 10MB per document (automatically truncated)
- **Rate Limiting**: 10 requests/second to IT Glue API
- **Embedding Generation**: Requires OpenAI API key (optional)
- **pgvector**: Vector search requires PostgreSQL pgvector extension (optional)

## Configuration

Environment variables:

```bash
# Required
ITGLUE_API_KEY=your-api-key
ITGLUE_API_URL=https://api.itglue.com

# Optional
OPENAI_API_KEY=your-openai-key  # For embeddings
REDIS_URL=redis://localhost:6379  # For caching
DATABASE_URL=postgresql://user:pass@localhost/itglue

# Performance Tuning
INFRASTRUCTURE_DOC_CACHE_TTL=900  # Cache TTL in seconds
INFRASTRUCTURE_DOC_MAX_PARALLEL=10  # Max parallel API calls
INFRASTRUCTURE_DOC_RETRY_MAX=3  # Max retry attempts
```

## Troubleshooting

### Common Issues

1. **"Organization not found"**
   - Verify the organization ID is correct
   - Check API key has access to the organization

2. **"Rate limit exceeded"**
   - The system automatically handles rate limiting
   - If persistent, check if other processes are using the API

3. **"Document too large"**
   - Document exceeds 10MB limit
   - Automatically truncated with notice
   - Consider generating separate documents for different resource types

4. **"pgvector extension not available"**
   - Embeddings will be stored as arrays
   - Vector similarity search won't be available
   - Install pgvector for full functionality

### Monitoring

Check progress and logs:

```sql
-- View recent documentation generations
SELECT * FROM infrastructure_snapshots 
ORDER BY created_at DESC 
LIMIT 10;

-- Check progress of current generation
SELECT * FROM infrastructure_progress 
WHERE snapshot_id = 'your-snapshot-id';

-- View API query performance
SELECT resource_type, AVG(duration_ms), COUNT(*)
FROM api_queries
GROUP BY resource_type;
```

## Future Enhancements

Planned improvements:

1. **Incremental Updates**: Only query changed resources
2. **Template Customization**: User-defined document templates
3. **Export Formats**: PDF, HTML, DOCX support
4. **Scheduled Generation**: Automated periodic documentation
5. **Diff Tracking**: Track changes between generations
6. **Relationship Mapping**: Visual network diagrams
7. **Compliance Reports**: SOC2, HIPAA, PCI templates
8. **Multi-Organization**: Batch documentation for MSPs