"""Query documents tool for MCP server."""

from typing import Any, Optional

from src.cache.manager import CacheManager
from src.query.documents_handler import DocumentsHandler
from src.services.itglue.client import ITGlueClient

from .base import BaseTool


class QueryDocumentsTool(BaseTool):
    """Tool for querying IT Glue documents."""

    def __init__(
        self, 
        itglue_client: ITGlueClient, 
        cache_manager: Optional[CacheManager] = None
    ):
        """Initialize query documents tool.

        Args:
            itglue_client: IT Glue API client
            cache_manager: Optional cache manager
        """
        super().__init__(
            name="query_documents",
            description="Query and search IT Glue documents by organization, content, or metadata"
        )
        self.documents_handler = DocumentsHandler(itglue_client, cache_manager)

    async def execute(
        self,
        action: str = "list_all",
        organization: Optional[str] = None,
        query: Optional[str] = None,
        document_id: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
        include_folders: bool = False,
        folder_id: Optional[str] = None,
        **kwargs
    ) -> dict[str, Any]:
        """Execute documents query.

        Args:
            action: Action to perform (list_all, by_org, search, details, categories, folders, in_folder)
            organization: Organization name or ID to filter by
            query: Search query for document content
            document_id: Specific document ID to get details
            category: Document category to filter by
            limit: Maximum number of results
            include_folders: Whether to include documents in folders (default: False for root only)
            folder_id: Specific folder ID to filter by (optional)
            **kwargs: Additional arguments

        Returns:
            Query results
        """
        try:
            self.logger.info(f"Executing documents query: action={action}")

            # Route to appropriate handler method based on action
            if action == "list_all":
                result = await self.documents_handler.list_all_documents(
                    organization=organization,
                    limit=limit,
                    include_folders=include_folders,
                    folder_id=folder_id
                )
                
            elif action == "by_org" or organization:
                if not organization:
                    return self.format_error("Organization parameter required for by_org action")
                result = await self.documents_handler.find_documents_for_org(
                    organization=organization,
                    category=category,
                    include_folders=include_folders,
                    folder_id=folder_id
                )

            elif action == "folders" or action == "with_folders":
                # List all documents including those in folders
                result = await self.documents_handler.list_all_documents(
                    organization=organization,
                    limit=limit,
                    include_folders=True
                )
                
            elif action == "in_folder" or folder_id:
                # List documents in a specific folder
                if not folder_id:
                    return self.format_error("Folder ID parameter required for in_folder action")
                result = await self.documents_handler.list_all_documents(
                    organization=organization,
                    limit=limit,
                    folder_id=folder_id
                )
                
            elif action == "search" or query:
                if not query:
                    return self.format_error("Query parameter required for search action")
                result = await self.documents_handler.search_documents(
                    query=query,
                    organization=organization,
                    category=category
                )
                
            elif action == "details" or document_id:
                if not document_id:
                    return self.format_error("Document ID parameter required for details action")
                result = await self.documents_handler.get_document_details(document_id)
                
            elif action == "categories" or action == "stats":
                result = await self.documents_handler.get_document_categories(
                    organization=organization
                )
                
            else:
                return self.format_error(
                    f"Unknown action '{action}'. Supported actions: "
                    "list_all, by_org, search, details, categories, folders, with_folders, in_folder"
                )

            # Add metadata to successful results
            if result.get("success", False):
                result["action"] = action
                result["parameters"] = {
                    "organization": organization,
                    "query": query,
                    "document_id": document_id,
                    "category": category,
                    "limit": limit,
                    "include_folders": include_folders,
                    "folder_id": folder_id
                }

            return self.format_success(result)

        except Exception as e:
            self.logger.error(f"Documents query failed: {e}", exc_info=True)
            return self.format_error(
                f"Failed to query documents: {str(e)}",
                action=action,
                organization=organization,
                query=query,
                document_id=document_id,
                category=category
            )

    def format_success(self, data: dict[str, Any]) -> dict[str, Any]:
        """Format successful response.

        Args:
            data: Response data

        Returns:
            Formatted success response
        """
        return {
            "success": True,
            "tool": self.name,
            "data": data
        }

    def format_error(self, message: str, **context) -> dict[str, Any]:
        """Format error response.

        Args:
            message: Error message
            **context: Additional context

        Returns:
            Formatted error response
        """
        return {
            "success": False,
            "tool": self.name,
            "error": message,
            "context": context
        }