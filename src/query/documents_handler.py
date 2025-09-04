"""Handler for document queries with semantic search."""

import hashlib
import logging
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Optional

from src.cache.manager import CacheManager
from src.search.semantic import SemanticSearch
from src.services.itglue.client import ITGlueClient
from src.services.itglue.models import Document

logger = logging.getLogger(__name__)

# Maximum document content length to prevent MCP payload issues
MAX_CONTENT_LENGTH = 5000
MAX_DOCUMENTS_PER_RESPONSE = 20


class DocumentsHandler:
    """Handles queries related to IT Glue documents with semantic search."""

    def __init__(
        self,
        itglue_client: ITGlueClient,
        semantic_search: Optional[SemanticSearch] = None,
        cache_manager: Optional[CacheManager] = None
    ):
        """Initialize documents handler.

        Args:
            itglue_client: IT Glue API client
            semantic_search: Optional semantic search engine
            cache_manager: Optional cache manager
        """
        self.client = itglue_client
        self.semantic = semantic_search
        self.cache = cache_manager

    async def search_documents(
        self,
        query: str,
        organization: Optional[str] = None,
        use_semantic: bool = True,
        limit: int = MAX_DOCUMENTS_PER_RESPONSE
    ) -> dict[str, Any]:
        """Search documents using semantic search and/or keyword matching.

        Args:
            query: Search query
            organization: Optional organization filter
            use_semantic: Whether to use semantic search if available
            limit: Maximum number of results

        Returns:
            Dictionary with matching documents
        """
        # Check cache first
        cache_key = f"documents:search:{self._hash_query(query)}:{organization or 'all'}"
        if self.cache and hasattr(self.cache, 'query_cache'):
            cached = await self.cache.query_cache.get(cache_key)
            if cached:
                logger.debug(f"Returning cached search results for '{query}'")
                return cached

        try:
            # Try semantic search first if available
            if use_semantic and self.semantic:
                result = await self._semantic_search(query, organization, limit)
                if result["count"] > 0:
                    # Cache for 10 minutes
                    if self.cache and hasattr(self.cache, 'query_cache'):
                        from ..cache.redis_cache import QueryType
                        await self.cache.query_cache.set(cache_key, result, QueryType.OPERATIONAL)
                    return result

            # Fall back to keyword search
            result = await self._keyword_search(query, organization, limit)

            # Cache for 10 minutes
            if self.cache and hasattr(self.cache, 'query_cache'):
                from ..cache.redis_cache import QueryType
                await self.cache.query_cache.set(cache_key, result, QueryType.OPERATIONAL)

            return result

        except Exception as e:
            logger.error(f"Failed to search documents for '{query}': {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "documents": []
            }

    async def find_documentation_for_system(
        self,
        system_name: str,
        doc_type: Optional[str] = None
    ) -> dict[str, Any]:
        """Find documentation for a specific system.

        Args:
            system_name: System or service name
            doc_type: Optional document type filter (e.g., 'runbook', 'guide')

        Returns:
            Dictionary with relevant documentation
        """
        try:
            # Build search query
            if doc_type:
                query = f"{system_name} {doc_type}"
            else:
                query = f"{system_name} documentation OR {system_name} guide OR {system_name} runbook"

            # Search with semantic if available
            result = await self.search_documents(query, use_semantic=True)

            if result.get("success", True):
                # Filter results to most relevant
                filtered_docs = []
                system_lower = system_name.lower()

                for doc in result.get("documents", []):
                    # Check relevance
                    name_match = system_lower in doc.get("name", "").lower()
                    content_match = system_lower in (doc.get("content_preview", "") or "").lower()

                    if name_match or content_match:
                        filtered_docs.append(doc)

                result["documents"] = filtered_docs[:10]  # Limit to top 10
                result["count"] = len(filtered_docs)
                result["system"] = system_name
                result["doc_type"] = doc_type

            return result

        except Exception as e:
            logger.error(f"Failed to find documentation for {system_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "system": system_name,
                "documents": []
            }

    async def list_runbooks(
        self,
        organization: Optional[str] = None
    ) -> dict[str, Any]:
        """List all runbooks.

        Args:
            organization: Optional organization filter

        Returns:
            Dictionary with runbook documents
        """
        return await self._list_by_type("runbook", organization)

    async def search_knowledge_base(
        self,
        query: str
    ) -> dict[str, Any]:
        """Search the knowledge base.

        Args:
            query: Search query

        Returns:
            Dictionary with knowledge base articles
        """
        # Knowledge base typically includes guides, FAQs, how-tos
        enhanced_query = f"{query} OR guide OR FAQ OR how-to OR knowledge"

        result = await self.search_documents(
            enhanced_query,
            use_semantic=True,
            limit=15
        )

        if result.get("success", True):
            result["knowledge_type"] = "knowledge_base"
            result["original_query"] = query

        return result

    async def get_document_by_id(
        self,
        document_id: str
    ) -> dict[str, Any]:
        """Get a specific document by ID.

        Args:
            document_id: Document ID

        Returns:
            Dictionary with document details
        """
        # Check cache first
        cache_key = f"documents:detail:{document_id}"
        if self.cache and hasattr(self.cache, 'query_cache'):
            cached = await self.cache.query_cache.get(cache_key)
            if cached:
                logger.debug(f"Returning cached document {document_id}")
                return cached

        try:
            # Get all documents and find the specific one
            # Note: IT Glue API might require organization context
            all_docs = await self.client.get_documents()

            document = None
            for doc in all_docs:
                if doc.id == document_id:
                    document = doc
                    break

            if not document:
                return {
                    "success": False,
                    "error": f"Document with ID '{document_id}' not found",
                    "document": None
                }

            # Get organization name if available
            org_name = None
            if document.organization_id:
                try:
                    org = await self.client.get_organization(document.organization_id)
                    org_name = org.name
                except:
                    pass

            # Format response
            result = {
                "success": True,
                "document": self._format_document(document, include_full_content=True),
                "organization_name": org_name
            }

            # Cache for 30 minutes
            if self.cache and hasattr(self.cache, 'query_cache'):
                from ..cache.redis_cache import QueryType
                await self.cache.query_cache.set(cache_key, result, QueryType.OPERATIONAL)

            logger.info(f"Retrieved document {document_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "document": None
            }

    async def list_recent_documents(
        self,
        organization: Optional[str] = None,
        limit: int = 20
    ) -> dict[str, Any]:
        """List recently updated documents.

        Args:
            organization: Optional organization filter
            limit: Maximum number of results

        Returns:
            Dictionary with recent documents
        """
        try:
            # Get organization ID if specified
            org_id = None
            if organization:
                orgs = await self.client.get_organizations(filters={"name": organization})
                if orgs:
                    org_id = orgs[0].id

            # Get documents
            documents = await self.client.get_documents(org_id=org_id)

            # Sort by updated_at (most recent first)
            sorted_docs = sorted(
                documents,
                key=lambda d: d.updated_at or d.created_at or datetime.min,
                reverse=True
            )

            # Format response
            result = {
                "success": True,
                "organization": organization,
                "count": min(len(sorted_docs), limit),
                "documents": [
                    self._format_document(doc)
                    for doc in sorted_docs[:limit]
                ]
            }

            logger.info(f"Listed {result['count']} recent documents")
            return result

        except Exception as e:
            logger.error(f"Failed to list recent documents: {e}")
            return {
                "success": False,
                "error": str(e),
                "documents": []
            }

    async def _semantic_search(
        self,
        query: str,
        organization: Optional[str] = None,
        limit: int = MAX_DOCUMENTS_PER_RESPONSE
    ) -> dict[str, Any]:
        """Perform semantic search using Qdrant.

        Args:
            query: Search query
            organization: Optional organization filter
            limit: Maximum number of results

        Returns:
            Dictionary with search results
        """
        try:
            # Build filter for organization if specified
            filters = {}
            if organization:
                filters["organization_name"] = organization

            # Perform semantic search
            results = await self.semantic.search(
                query=query,
                collection_name="itglue_documents",
                filters=filters,
                limit=limit
            )

            # Format documents from search results
            documents = []
            for result in results:
                doc_data = result.payload
                documents.append({
                    "id": result.source_id or result.id,
                    "name": doc_data.get("name", "Untitled"),
                    "content_preview": self._truncate_content(
                        doc_data.get("content", ""),
                        max_length=500
                    ),
                    "organization_id": doc_data.get("organization_id"),
                    "organization_name": doc_data.get("organization_name"),
                    "relevance_score": result.score,
                    "updated_at": doc_data.get("updated_at"),
                    "document_type": self._infer_document_type(doc_data)
                })

            return {
                "success": True,
                "query": query,
                "search_type": "semantic",
                "count": len(documents),
                "documents": documents
            }

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            # Return empty results rather than error
            return {
                "success": True,
                "query": query,
                "search_type": "semantic",
                "count": 0,
                "documents": []
            }

    async def _keyword_search(
        self,
        query: str,
        organization: Optional[str] = None,
        limit: int = MAX_DOCUMENTS_PER_RESPONSE
    ) -> dict[str, Any]:
        """Perform keyword-based search.

        Args:
            query: Search query
            organization: Optional organization filter
            limit: Maximum number of results

        Returns:
            Dictionary with search results
        """
        try:
            # Get organization ID if specified
            org_id = None
            if organization:
                orgs = await self.client.get_organizations(filters={"name": organization})
                if orgs:
                    org_id = orgs[0].id

            # Get all documents
            all_documents = await self.client.get_documents(org_id=org_id)

            # Search through documents
            query_lower = query.lower()
            query_words = query_lower.split()

            matching_docs = []
            for doc in all_documents:
                # Calculate relevance score
                score = 0
                name_lower = (doc.name or "").lower()
                content_lower = (doc.content or "").lower()

                # Check name matches
                for word in query_words:
                    if word in name_lower:
                        score += 2  # Name matches are more important
                    if word in content_lower:
                        score += 1

                # Check fuzzy matching
                name_similarity = SequenceMatcher(None, query_lower, name_lower).ratio()
                score += name_similarity * 3

                if score > 0:
                    matching_docs.append((doc, score))

            # Sort by relevance
            matching_docs.sort(key=lambda x: x[1], reverse=True)

            # Format results
            documents = [
                self._format_document(doc, relevance_score=score)
                for doc, score in matching_docs[:limit]
            ]

            return {
                "success": True,
                "query": query,
                "search_type": "keyword",
                "count": len(documents),
                "documents": documents
            }

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "documents": []
            }

    async def _list_by_type(
        self,
        doc_type: str,
        organization: Optional[str] = None
    ) -> dict[str, Any]:
        """List documents by type.

        Args:
            doc_type: Document type to filter by
            organization: Optional organization filter

        Returns:
            Dictionary with filtered documents
        """
        try:
            # Get organization ID if specified
            org_id = None
            if organization:
                orgs = await self.client.get_organizations(filters={"name": organization})
                if orgs:
                    org_id = orgs[0].id

            # Get all documents
            all_documents = await self.client.get_documents(org_id=org_id)

            # Filter by type
            type_lower = doc_type.lower()
            filtered_docs = []

            for doc in all_documents:
                # Check if document name or content suggests it's the right type
                name_lower = (doc.name or "").lower()
                content_lower = (doc.content or "")[:500].lower()

                if (type_lower in name_lower or
                    f"{type_lower}s" in name_lower or
                    type_lower in content_lower):
                    filtered_docs.append(doc)

            # Format response
            result = {
                "success": True,
                "document_type": doc_type,
                "organization": organization,
                "count": len(filtered_docs),
                "documents": [
                    self._format_document(doc)
                    for doc in filtered_docs[:MAX_DOCUMENTS_PER_RESPONSE]
                ]
            }

            logger.info(f"Found {result['count']} {doc_type} documents")
            return result

        except Exception as e:
            logger.error(f"Failed to list {doc_type} documents: {e}")
            return {
                "success": False,
                "error": str(e),
                "document_type": doc_type,
                "documents": []
            }

    def _format_document(
        self,
        document: Document,
        include_full_content: bool = False,
        relevance_score: Optional[float] = None
    ) -> dict[str, Any]:
        """Format a document for response.

        Args:
            document: Document object
            include_full_content: Whether to include full content
            relevance_score: Optional relevance score

        Returns:
            Formatted document dictionary
        """
        # Prepare content
        content = document.content or ""

        if include_full_content:
            # Truncate if too long to prevent MCP payload issues
            content = self._truncate_content(content, MAX_CONTENT_LENGTH)
        else:
            # Just a preview
            content = self._truncate_content(content, 500)

        result = {
            "id": document.id,
            "name": document.name,
            "content_preview": content,
            "organization_id": document.organization_id,
            "document_folder_id": document.document_folder_id,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            "document_type": self._infer_document_type(document)
        }

        if relevance_score is not None:
            result["relevance_score"] = relevance_score

        return result

    def _truncate_content(self, content: str, max_length: int) -> str:
        """Truncate content to maximum length.

        Args:
            content: Content to truncate
            max_length: Maximum length

        Returns:
            Truncated content
        """
        if not content:
            return ""

        if len(content) <= max_length:
            return content

        # Find a good break point (end of sentence or paragraph)
        truncated = content[:max_length]

        # Try to break at sentence
        last_period = truncated.rfind('.')
        last_newline = truncated.rfind('\n')

        break_point = max(last_period, last_newline)
        if break_point > max_length * 0.8:  # Only if we're not losing too much
            truncated = truncated[:break_point + 1]

        return truncated + "..."

    def _infer_document_type(self, document: Any) -> str:
        """Infer document type from name and content.

        Args:
            document: Document object or dictionary

        Returns:
            Inferred document type
        """
        # Get name and content
        if isinstance(document, dict):
            name = (document.get("name") or "").lower()
            content = (document.get("content") or "")[:500].lower()
        else:
            name = (document.name or "").lower()
            content = (document.content or "")[:500].lower()

        # Check for common document types
        if "runbook" in name or "runbook" in content:
            return "runbook"
        elif "guide" in name or "how-to" in name:
            return "guide"
        elif "policy" in name or "procedure" in name:
            return "policy"
        elif "faq" in name or "frequently asked" in content:
            return "faq"
        elif "sop" in name or "standard operating" in content:
            return "sop"
        elif "template" in name:
            return "template"
        elif "checklist" in name:
            return "checklist"
        else:
            return "document"

    async def list_all_documents(
        self,
        organization: Optional[str] = None,
        limit: int = MAX_DOCUMENTS_PER_RESPONSE,
        include_folders: bool = False,
        folder_id: Optional[str] = None
    ) -> dict[str, Any]:
        """List all documents, optionally filtered by organization and folders.

        Args:
            organization: Optional organization name to filter by
            limit: Maximum number of results
            include_folders: Whether to include documents in folders (default: False for root only)
            folder_id: Specific folder ID to filter by (optional)

        Returns:
            Dictionary with document information
        """
        # Check cache first - include folder parameters in cache key
        cache_key = f"documents:all:{organization or 'all'}:folders_{include_folders}:folder_{folder_id or 'none'}"
        if self.cache and hasattr(self.cache, 'query_cache'):
            cached = await self.cache.query_cache.get(cache_key)
            if cached:
                logger.debug(f"Returning cached documents for {organization}")
                return cached

        try:
            # Get organization ID if specified
            org_id = None
            org_name = organization
            
            if organization:
                orgs = await self.client.get_organizations(filters={"name": organization})
                if not orgs:
                    # Try fuzzy match
                    all_orgs = await self.client.get_organizations()
                    org_match = self._find_best_match(
                        organization,
                        [(org.id, org.name) for org in all_orgs]
                    )
                    
                    if not org_match:
                        return {
                            "success": False,
                            "error": f"Organization '{organization}' not found",
                            "documents": []
                        }
                    
                    org_id = org_match[0]
                    org_name = org_match[1]
                else:
                    org_id = orgs[0].id
                    org_name = orgs[0].name

            # Get documents with folder filtering
            documents = await self.client.get_documents(
                org_id=org_id,
                include_folders=include_folders,
                folder_id=folder_id
            )

            # Format response
            result = {
                "success": True,
                "organization": org_name,
                "count": len(documents),
                "documents": [
                    self._format_document(doc)
                    for doc in documents[:limit]
                ]
            }

            # Cache for 15 minutes
            if self.cache and hasattr(self.cache, 'query_cache'):
                from ..cache.redis_cache import QueryType
                await self.cache.query_cache.set(cache_key, result, QueryType.OPERATIONAL)

            logger.info(f"Listed {len(result['documents'])} documents")
            return result

        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return {
                "success": False,
                "error": str(e),
                "documents": []
            }

    async def find_documents_for_org(
        self,
        organization: str,
        category: Optional[str] = None,
        include_folders: bool = False,
        folder_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Find documents for a specific organization.

        Args:
            organization: Organization name or ID
            category: Optional document category to filter by
            include_folders: Whether to include documents in folders (default: False for root only)
            folder_id: Specific folder ID to filter by (optional)

        Returns:
            Dictionary with matching documents
        """
        # Check cache first - include folder parameters in cache key
        cache_key = f"documents:org:{organization.lower()}:{category or 'all'}:folders_{include_folders}:folder_{folder_id or 'none'}"
        if self.cache and hasattr(self.cache, 'query_cache'):
            cached = await self.cache.query_cache.get(cache_key)
            if cached:
                logger.debug(f"Returning cached documents for {organization}")
                return cached

        try:
            # Find the organization
            organizations = await self.client.get_organizations(
                filters={"name": organization}
            )

            if not organizations:
                # Try fuzzy match
                all_orgs = await self.client.get_organizations()
                org_match = self._find_best_match(
                    organization,
                    [(org.id, org.name) for org in all_orgs]
                )

                if not org_match:
                    return {
                        "success": False,
                        "error": f"Organization '{organization}' not found",
                        "documents": []
                    }

                org_id = org_match[0]
                org_name = org_match[1]
            else:
                org_id = organizations[0].id
                org_name = organizations[0].name

            # Get documents for the organization with folder filtering
            documents = await self.client.get_documents(
                org_id=org_id,
                include_folders=include_folders,
                folder_id=folder_id
            )

            # Filter by category if specified
            if category:
                category_lower = category.lower()
                documents = [
                    doc for doc in documents
                    if category_lower in (doc.name or "").lower()
                    or category_lower in self._infer_document_type(doc).lower()
                ]

            # Format response
            result = {
                "success": True,
                "organization_id": org_id,
                "organization_name": org_name,
                "category": category,
                "count": len(documents),
                "documents": [
                    self._format_document(doc)
                    for doc in documents
                ]
            }

            # Cache for 15 minutes
            if self.cache and hasattr(self.cache, 'query_cache'):
                from ..cache.redis_cache import QueryType
                await self.cache.query_cache.set(cache_key, result, QueryType.OPERATIONAL)

            logger.info(f"Found {len(result['documents'])} documents for {organization}")
            return result

        except Exception as e:
            logger.error(f"Failed to find documents for {organization}: {e}")
            return {
                "success": False,
                "error": str(e),
                "documents": []
            }

    async def get_document_details(
        self,
        document_id: str
    ) -> dict[str, Any]:
        """Get detailed information about a specific document.

        Args:
            document_id: Document ID

        Returns:
            Dictionary with document details
        """
        return await self.get_document_by_id(document_id)

    async def get_document_categories(
        self,
        organization: Optional[str] = None
    ) -> dict[str, Any]:
        """Get document categories/types with counts.

        Args:
            organization: Optional organization to filter by

        Returns:
            Dictionary with category statistics
        """
        # Check cache first
        cache_key = f"documents:categories:{organization or 'all'}"
        if self.cache and hasattr(self.cache, 'query_cache'):
            cached = await self.cache.query_cache.get(cache_key)
            if cached:
                logger.debug("Returning cached document categories")
                return cached

        try:
            # Get organization ID if specified
            org_id = None
            if organization:
                orgs = await self.client.get_organizations(filters={"name": organization})
                if orgs:
                    org_id = orgs[0].id

            # Get all documents
            documents = await self.client.get_documents(org_id=org_id)

            # Count document types
            category_counts = {}
            for doc in documents:
                doc_type = self._infer_document_type(doc)
                category_counts[doc_type] = category_counts.get(doc_type, 0) + 1

            # Format response
            categories = [
                {
                    "name": category,
                    "count": count,
                    "examples": [
                        doc.name for doc in documents[:3]
                        if self._infer_document_type(doc) == category
                    ]
                }
                for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
            ]

            result = {
                "success": True,
                "organization": organization,
                "total_documents": len(documents),
                "categories": categories,
                "category_count": len(categories)
            }

            # Cache for 30 minutes
            if self.cache and hasattr(self.cache, 'query_cache'):
                from ..cache.redis_cache import QueryType
                await self.cache.query_cache.set(cache_key, result, QueryType.OPERATIONAL)

            logger.info(f"Retrieved {len(categories)} document categories")
            return result

        except Exception as e:
            logger.error(f"Failed to get document categories: {e}")
            return {
                "success": False,
                "error": str(e),
                "categories": []
            }

    def _find_best_match(
        self,
        query: str,
        candidates: list[tuple]
    ) -> Optional[tuple]:
        """Find best matching candidate using fuzzy matching.

        Args:
            query: Search query
            candidates: List of (id, name) tuples

        Returns:
            Best matching tuple or None
        """
        if not candidates:
            return None

        query_lower = query.lower()
        best_match = None
        best_score = 0

        for candidate_id, candidate_name in candidates:
            score = SequenceMatcher(
                None,
                query_lower,
                candidate_name.lower()
            ).ratio()

            if score > best_score and score > 0.6:
                best_score = score
                best_match = (candidate_id, candidate_name)

        return best_match

    def _hash_query(self, query: str) -> str:
        """Create a hash of the query for caching.

        Args:
            query: Search query

        Returns:
            Hash string
        """
        return hashlib.md5(query.lower().encode()).hexdigest()[:8]
