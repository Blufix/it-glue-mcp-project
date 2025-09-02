# IT Glue API Limitations

This document outlines the limitations discovered with the IT Glue API regarding document access and file management.

## Document Access Limitations

### Two Separate Document Systems

IT Glue maintains two distinct document storage systems:

1. **API Documents**
   - Created programmatically via the API
   - Accessible through `/organizations/{id}/relationships/documents` endpoint
   - Can be queried, updated, and deleted via API
   - Typically plain text or HTML content

2. **File Uploads (NOT accessible via API)**
   - Word documents (.docx)
   - PDF files (.pdf)
   - Excel spreadsheets (.xlsx)
   - Other file types uploaded through the IT Glue web interface
   - Stored in IT Glue's file management system
   - Can be organized in folders in the UI
   - **Cannot be accessed, downloaded, or searched via the public API**

### Key Findings

- The global `/documents` endpoint returns 404
- Document folders (`/document-folders`) are not accessible via API
- File attachments (`/attachments`) endpoint returns 404
- Files endpoint (`/files`) returns 404
- Moving documents out of folders in the UI does not make them API-accessible if they were originally file uploads

### Pagination

- Default page size: 50 items
- Maximum page size: 1,000 items
- Use `page[size]` and `page[number]` parameters
- The API correctly returns `total-count` and `total-pages` in metadata

## Impact on MCP Server

### What Works
- Retrieving API-created documents
- Searching document content and metadata for API documents
- Creating new documents via API
- Updating existing API documents

### What Doesn't Work
- Accessing uploaded files (Word, PDF, etc.)
- Browsing document folder structures
- Downloading file attachments
- Searching content within uploaded files

### User Experience

When users search for documents that are file uploads (like "Bawso Autopilot Configuration"), the system will:

1. Search available API documents
2. If not found, inform users that the document may be a file upload only viewable in the IT Glue web interface
3. Suggest checking the IT Glue web UI directly for file uploads

## Workarounds

### For Essential File Access

If file upload access is critical for your use case, consider:

1. **Re-creating documents as API documents**: Copy content from file uploads into new API-created documents
2. **Using IT Glue's web interface**: Direct users to the web UI for file access
3. **Storing files elsewhere**: Use a separate document management system with API access
4. **Contact IT Glue support**: Request access to file upload endpoints (may require Enterprise features)

## Code Implementation

The MCP server handles these limitations by:

```python
async def get_documents(self, org_id: Optional[str] = None) -> List[Document]:
    """Get API-created documents.
    
    NOTE: This only returns documents created via the IT Glue API.
    File uploads (Word docs, PDFs) made through the IT Glue UI are not 
    accessible via the public API.
    """
    # Implementation uses organization-specific endpoint
    # Global documents endpoint returns 404
```

## Testing

Test scripts have been created to verify these limitations:

- `tests/scripts/test_document_folders.py` - Tests folder endpoints (all return 404)
- `tests/scripts/test_attachments_files.py` - Tests attachment/file endpoints (all return 404)
- `tests/scripts/test_document_pagination.py` - Verifies pagination works correctly
- `tests/scripts/test_document_visibility.py` - Confirms file uploads remain inaccessible

## Recommendations

1. **Set user expectations**: Clearly communicate that only API documents are searchable
2. **Document migration**: Consider migrating critical file uploads to API documents
3. **API feedback**: Provide feedback to IT Glue about the need for file access APIs
4. **Alternative storage**: For new documents, prefer API creation over file uploads when possible