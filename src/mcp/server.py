"""Main MCP server implementation."""

import asyncio
import logging
from typing import Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from src.cache import CacheManager
from src.config.settings import settings
from src.data import db_manager
from src.query import QueryEngine
from src.search import HybridSearch
from src.services.itglue import ITGlueClient
from src.sync import SyncOrchestrator

logger = logging.getLogger(__name__)


class ITGlueMCPServer:
    """IT Glue MCP Server implementation."""

    def __init__(self):
        """Initialize the MCP server."""
        self.server = Server("itglue-mcp")
        self.query_engine: Optional[QueryEngine] = None
        self.search_engine: Optional[HybridSearch] = None
        self.sync_orchestrator: Optional[SyncOrchestrator] = None
        self.cache_manager: Optional[CacheManager] = None
        self.itglue_client: Optional[ITGlueClient] = None
        self._initialized = False
        self._register_tools()
        logger.info("IT Glue MCP Server initialized")

    def _register_tools(self):
        """Register MCP tools."""

        @self.server.tool()
        async def query(query: str, company: Optional[str] = None) -> dict:
            """
            Natural language query tool for IT Glue documentation.

            Args:
                query: Natural language question
                company: Company name or ID (optional)

            Returns:
                Query results or error message
            """
            try:
                logger.info(f"Query received: {query} for company: {company}")

                # Initialize if needed
                if not self._initialized:
                    await self._initialize_components()

                if not self.query_engine:
                    return {
                        "success": False,
                        "error": "Query engine not initialized"
                    }

                # Process query
                result = await self.query_engine.process_query(
                    query=query,
                    company=company
                )

                return result

            except Exception as e:
                logger.error(f"Query error: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.server.tool()
        async def search(
            query: str,
            limit: int = 10,
            filters: Optional[dict] = None
        ) -> dict:
            """
            Cross-company search tool.

            Args:
                query: Search query
                limit: Maximum number of results
                filters: Optional filters

            Returns:
                Search results
            """
            try:
                logger.info(f"Search received: {query} with limit: {limit}")

                # Initialize if needed
                if not self._initialized:
                    await self._initialize_components()

                if not self.search_engine:
                    return {
                        "success": False,
                        "error": "Search engine not initialized",
                        "results": []
                    }

                # Perform search
                results = await self.search_engine.search(
                    query=query,
                    company_id=filters.get("company_id") if filters else None,
                    entity_type=filters.get("entity_type") if filters else None,
                    limit=limit
                )

                # Format results
                formatted_results = [
                    {
                        "id": r.entity_id,
                        "score": r.score,
                        "data": r.payload
                    }
                    for r in results
                ]

                return {
                    "success": True,
                    "results": formatted_results,
                    "count": len(formatted_results)
                }

            except Exception as e:
                logger.error(f"Search error: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                    "results": []
                }

        @self.server.tool()
        async def health() -> dict:
            """
            Health check tool.

            Returns:
                Server health status
            """
            try:
                # Check component health
                health_status = {
                    "status": "healthy",
                    "version": "0.1.0",
                    "environment": settings.environment,
                    "components": {
                        "mcp_server": "healthy",
                        "query_engine": "healthy" if self.query_engine else "not_initialized",
                        "search_engine": "healthy" if self.search_engine else "not_initialized"
                    }
                }

                logger.debug(f"Health check: {health_status}")
                return health_status

            except Exception as e:
                logger.error(f"Health check error: {e}", exc_info=True)
                return {
                    "status": "unhealthy",
                    "error": str(e)
                }

        @self.server.tool()
        async def query_organizations(
            action: str = "list",
            name: Optional[str] = None,
            query: Optional[str] = None,
            org_type: Optional[str] = None,
            limit: int = 100
        ) -> dict:
            """
            Query IT Glue organizations with fuzzy matching and <500ms response time.

            Args:
                action: Action - 'list', 'find', 'search', 'customers', 'vendors', or 'stats'
                name: Organization name for 'find' action
                query: Search query for 'search' action
                org_type: Organization type filter (e.g., 'Customer', 'Vendor')
                limit: Maximum number of results

            Returns:
                Organization information based on action
            """
            try:
                # Initialize if needed
                if not self._initialized:
                    await self._initialize_components()

                if not self.itglue_client:
                    return {
                        "success": False,
                        "error": "IT Glue client not initialized"
                    }

                # Import handler here to avoid circular imports
                from src.query.organizations_handler import OrganizationsHandler

                # Create handler instance
                handler = OrganizationsHandler(
                    itglue_client=self.itglue_client,
                    cache_manager=self.cache_manager
                )

                # Perform action
                if action == "list":
                    return await handler.list_all_organizations(
                        org_type=org_type,
                        limit=limit
                    )

                elif action == "find":
                    if not name:
                        return {
                            "success": False,
                            "error": "name required for 'find' action"
                        }
                    return await handler.find_organization(name, use_fuzzy=True)

                elif action == "search":
                    if not query:
                        return {
                            "success": False,
                            "error": "query required for 'search' action"
                        }
                    return await handler.search_organizations(query, limit=limit)

                elif action == "customers":
                    return await handler.list_customers(limit=limit)

                elif action == "vendors":
                    return await handler.list_vendors(limit=limit)

                elif action == "stats":
                    return await handler.get_organization_stats()

                else:
                    return {
                        "success": False,
                        "error": f"Unknown action: {action}. Use 'list', 'find', 'search', 'customers', 'vendors', or 'stats'"
                    }

            except Exception as e:
                logger.error(f"Organization query error: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.server.tool()
        async def sync_data(
            organization_id: Optional[str] = None,
            full_sync: bool = False
        ) -> dict:
            """
            Trigger data synchronization from IT Glue.

            Args:
                organization_id: Specific organization to sync (optional)
                full_sync: Whether to perform full sync

            Returns:
                Sync status
            """
            try:
                # Initialize if needed
                if not self._initialized:
                    await self._initialize_components()

                if not self.sync_orchestrator:
                    return {
                        "success": False,
                        "error": "Sync orchestrator not initialized"
                    }

                # Trigger sync
                if organization_id:
                    stats = await self.sync_orchestrator.sync_organization(
                        organization_id
                    )
                else:
                    stats = await self.sync_orchestrator.sync_all(
                        full_sync=full_sync
                    )

                return {
                    "success": True,
                    "stats": stats
                }

            except Exception as e:
                logger.error(f"Sync error: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.server.tool()
        async def query_documents(
            action: str = "search",
            query: Optional[str] = None,
            organization: Optional[str] = None,
            system_name: Optional[str] = None,
            document_id: Optional[str] = None,
            doc_type: Optional[str] = None
        ) -> dict:
            """
            Query IT Glue documents with semantic search support.

            Args:
                action: Action - 'search', 'find_for_system', 'runbooks', 'knowledge_base', 'recent', or 'details'
                query: Search query for 'search' and 'knowledge_base' actions
                organization: Organization name/ID filter
                system_name: System name for 'find_for_system' action
                document_id: Document ID for 'details' action
                doc_type: Document type filter (e.g., 'runbook', 'guide')

            Returns:
                Document information based on action
            """
            try:
                # Initialize if needed
                if not self._initialized:
                    await self._initialize_components()

                if not self.itglue_client:
                    return {
                        "success": False,
                        "error": "IT Glue client not initialized"
                    }

                # Import handler here to avoid circular imports
                from src.query.documents_handler import DocumentsHandler

                # Create handler instance with semantic search if available
                handler = DocumentsHandler(
                    itglue_client=self.itglue_client,
                    semantic_search=self.search_engine.semantic_search if self.search_engine else None,
                    cache_manager=self.cache_manager
                )

                # Perform action
                if action == "search":
                    if not query:
                        return {
                            "success": False,
                            "error": "query required for 'search' action"
                        }
                    return await handler.search_documents(
                        query=query,
                        organization=organization,
                        use_semantic=True
                    )

                elif action == "find_for_system":
                    if not system_name:
                        return {
                            "success": False,
                            "error": "system_name required for 'find_for_system' action"
                        }
                    return await handler.find_documentation_for_system(
                        system_name=system_name,
                        doc_type=doc_type
                    )

                elif action == "runbooks":
                    return await handler.list_runbooks(organization=organization)

                elif action == "knowledge_base":
                    if not query:
                        return {
                            "success": False,
                            "error": "query required for 'knowledge_base' action"
                        }
                    return await handler.search_knowledge_base(query)

                elif action == "recent":
                    return await handler.list_recent_documents(
                        organization=organization,
                        limit=20
                    )

                elif action == "details":
                    if not document_id:
                        return {
                            "success": False,
                            "error": "document_id required for 'details' action"
                        }
                    return await handler.get_document_by_id(document_id)

                else:
                    return {
                        "success": False,
                        "error": f"Unknown action: {action}. Use 'search', 'find_for_system', 'runbooks', 'knowledge_base', 'recent', or 'details'"
                    }

            except Exception as e:
                logger.error(f"Document query error: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.server.tool()
        async def query_flexible_assets(
            action: str = "list",
            asset_type: Optional[str] = None,
            organization: Optional[str] = None,
            query: Optional[str] = None,
            asset_id: Optional[str] = None
        ) -> dict:
            """
            Query IT Glue flexible assets (SSL certs, warranties, licenses, etc.).

            Args:
                action: Action to perform - 'list', 'by_org', 'search', 'stats', or 'details'
                asset_type: Asset type name (e.g., 'SSL Certificate', 'Warranty')
                organization: Organization name/ID for 'by_org' action
                query: Search query for 'search' action
                asset_id: Asset ID for 'details' action

            Returns:
                Flexible asset information based on action
            """
            try:
                # Initialize if needed
                if not self._initialized:
                    await self._initialize_components()

                if not self.itglue_client:
                    return {
                        "success": False,
                        "error": "IT Glue client not initialized"
                    }

                # Import handler here to avoid circular imports
                from src.query.flexible_assets_handler import FlexibleAssetsHandler

                # Create handler instance
                handler = FlexibleAssetsHandler(
                    itglue_client=self.itglue_client,
                    cache_manager=self.cache_manager
                )

                # Perform action
                if action == "list":
                    return await handler.list_all_flexible_assets(
                        asset_type=asset_type,
                        limit=100
                    )

                elif action == "by_org":
                    if not organization:
                        return {
                            "success": False,
                            "error": "organization required for 'by_org' action"
                        }
                    return await handler.find_assets_for_org(
                        organization=organization,
                        asset_type=asset_type
                    )

                elif action == "search":
                    if not query:
                        return {
                            "success": False,
                            "error": "query required for 'search' action"
                        }
                    return await handler.search_flexible_assets(
                        query=query,
                        asset_type=asset_type
                    )

                elif action == "stats":
                    return await handler.get_common_asset_types_with_counts()

                elif action == "details":
                    if not asset_id:
                        return {
                            "success": False,
                            "error": "asset_id required for 'details' action"
                        }
                    return await handler.get_asset_details(asset_id)

                else:
                    return {
                        "success": False,
                        "error": f"Unknown action: {action}. Use 'list', 'by_org', 'search', 'stats', or 'details'"
                    }

            except Exception as e:
                logger.error(f"Flexible assets query error: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.server.tool()
        async def query_locations(
            action: str = "list",
            organization: Optional[str] = None,
            city: Optional[str] = None,
            name: Optional[str] = None,
            query: Optional[str] = None
        ) -> dict:
            """
            Query IT Glue locations and sites.

            Args:
                action: Action to perform - 'list', 'by_org', 'by_city', 'by_name', or 'search'
                organization: Organization name/ID for 'by_org' action
                city: City name for 'by_city' action
                name: Location name for 'by_name' action
                query: Search query for 'search' action

            Returns:
                Location information based on action
            """
            try:
                # Initialize if needed
                if not self._initialized:
                    await self._initialize_components()

                if not self.itglue_client:
                    return {
                        "success": False,
                        "error": "IT Glue client not initialized"
                    }

                # Import handler here to avoid circular imports
                from src.query.locations_handler import LocationsHandler

                # Create handler instance
                handler = LocationsHandler(
                    itglue_client=self.itglue_client,
                    cache_manager=self.cache_manager
                )

                # Perform action
                if action == "list":
                    return await handler.list_all_locations()

                elif action == "by_org":
                    if not organization:
                        return {
                            "success": False,
                            "error": "organization required for 'by_org' action"
                        }
                    return await handler.find_locations_for_org(organization)

                elif action == "by_city":
                    if not city:
                        return {
                            "success": False,
                            "error": "city required for 'by_city' action"
                        }
                    return await handler.find_location_by_city(city)

                elif action == "by_name":
                    if not name:
                        return {
                            "success": False,
                            "error": "name required for 'by_name' action"
                        }
                    return await handler.find_location_by_name(name)

                elif action == "search":
                    if not query:
                        return {
                            "success": False,
                            "error": "query required for 'search' action"
                        }
                    return await handler.search_locations(query)

                else:
                    return {
                        "success": False,
                        "error": f"Unknown action: {action}. Use 'list', 'by_org', 'by_city', 'by_name', or 'search'"
                    }

            except Exception as e:
                logger.error(f"Location query error: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.server.tool()
        async def discover_asset_types(
            action: str = "list",
            asset_type_name: Optional[str] = None,
            query: Optional[str] = None
        ) -> dict:
            """
            Discover available flexible asset types in IT Glue.

            Args:
                action: Action to perform - 'list', 'describe', 'search', or 'common'
                asset_type_name: Name of asset type for 'describe' action
                query: Search query for 'search' action

            Returns:
                Asset type information based on action
            """
            try:
                # Initialize if needed
                if not self._initialized:
                    await self._initialize_components()

                if not self.itglue_client:
                    return {
                        "success": False,
                        "error": "IT Glue client not initialized"
                    }

                # Import handler here to avoid circular imports
                from src.query.asset_type_handler import AssetTypeHandler

                # Create handler instance
                handler = AssetTypeHandler(
                    itglue_client=self.itglue_client,
                    cache_manager=self.cache_manager
                )

                # Perform action
                if action == "list":
                    return await handler.list_asset_types()

                elif action == "describe":
                    if not asset_type_name:
                        return {
                            "success": False,
                            "error": "asset_type_name required for 'describe' action"
                        }
                    return await handler.describe_asset_type(asset_type_name)

                elif action == "search":
                    if not query:
                        return {
                            "success": False,
                            "error": "query required for 'search' action"
                        }
                    return await handler.search_asset_types(query)

                elif action == "common":
                    return await handler.get_common_asset_types()

                else:
                    return {
                        "success": False,
                        "error": f"Unknown action: {action}. Use 'list', 'describe', 'search', or 'common'"
                    }

            except Exception as e:
                logger.error(f"Asset type discovery error: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.server.tool()
        async def document_infrastructure(
            organization_id: str,
            include_embeddings: bool = True,
            upload_to_itglue: bool = False
        ) -> dict:
            """
            Generate comprehensive infrastructure documentation for an organization.
            Implements @organisations <organization_id> document infrastructure command.
            Also supports @<org_name> document infrastructure format.

            Args:
                organization_id: IT Glue organization ID or name to document
                include_embeddings: Whether to generate embeddings for future queries
                upload_to_itglue: Whether to upload the document to IT Glue

            Returns:
                Documentation generation status and results
            """
            try:
                logger.info(f"Infrastructure documentation request for org: {organization_id}")

                # Initialize if needed
                if not self._initialized:
                    await self._initialize_components()

                if not self.itglue_client:
                    return {
                        "success": False,
                        "error": "IT Glue client not initialized"
                    }

                # Check if it's a numeric ID or a name
                org_id_resolved = None
                try:
                    org_id_resolved = str(int(organization_id))
                except ValueError:
                    # Not numeric, try to resolve organization name
                    logger.info(f"Resolving organization name: {organization_id}")

                    # Query organizations to find matching name
                    from src.query.organizations_handler import OrganizationsHandler
                    handler = OrganizationsHandler(
                        itglue_client=self.itglue_client,
                        cache_manager=self.cache_manager
                    )

                    # Try to find organization by name
                    result = await handler.find_organization(organization_id, use_fuzzy=True)

                    if result.get('success') and result.get('data'):
                        org_data = result['data']
                        if isinstance(org_data, list) and len(org_data) > 0:
                            org_id_resolved = str(org_data[0].get('id'))
                            logger.info(f"Resolved '{organization_id}' to organization ID: {org_id_resolved}")
                        elif isinstance(org_data, dict):
                            org_id_resolved = str(org_data.get('id'))
                            logger.info(f"Resolved '{organization_id}' to organization ID: {org_id_resolved}")

                    if not org_id_resolved:
                        return {
                            "success": False,
                            "error": f"Organization '{organization_id}' not found. Please check the name or use the numeric ID."
                        }

                # Use resolved ID
                organization_id = org_id_resolved

                # Import handler here to avoid circular imports
                from src.infrastructure.documentation_handler import (
                    InfrastructureDocumentationHandler,
                )

                # Create handler instance
                handler = InfrastructureDocumentationHandler(
                    itglue_client=self.itglue_client,
                    cache_manager=self.cache_manager,
                    db_manager=db_manager
                )

                # Generate documentation with progress tracking
                result = await handler.generate_infrastructure_documentation(
                    organization_id=str(org_id_int),
                    include_embeddings=include_embeddings,
                    upload_to_itglue=upload_to_itglue
                )

                return result

            except ImportError as e:
                logger.error(f"Infrastructure handler not implemented yet: {e}")
                return {
                    "success": False,
                    "error": "Infrastructure documentation feature not yet implemented. Please complete the infrastructure module setup.",
                    "hint": "Need to implement InfrastructureDocumentationHandler"
                }
            except Exception as e:
                logger.error(f"Infrastructure documentation error: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

    async def _initialize_components(self):
        """Initialize all components."""
        if self._initialized:
            return

        try:
            logger.info("Initializing MCP server components")

            # Initialize database
            await db_manager.initialize()
            await db_manager.create_tables()

            # Initialize cache
            self.cache_manager = CacheManager()
            await self.cache_manager.connect()

            # Initialize search
            self.search_engine = HybridSearch()
            await self.search_engine.semantic_search.initialize_collection()

            # Initialize query engine
            self.query_engine = QueryEngine(
                search=self.search_engine,
                cache=self.cache_manager
            )

            # Initialize IT Glue client
            self.itglue_client = ITGlueClient()

            # Initialize sync orchestrator
            self.sync_orchestrator = SyncOrchestrator(
                itglue_client=self.itglue_client
            )

            self._initialized = True
            logger.info("All components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise

    async def run(self):
        """Run the MCP server."""
        logger.info("Starting MCP server on stdio")

        try:
            async with stdio_server() as (read_stream, write_stream):
                logger.info("MCP server started successfully")

                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )

        except Exception as e:
            logger.error(f"MCP server error: {e}", exc_info=True)
            raise

    async def run_websocket(self, host: str = "0.0.0.0", port: int = 8001):
        """Run the MCP server with WebSocket support."""
        # WebSocket implementation will be added when needed
        logger.info(f"WebSocket server would start on {host}:{port}")
        raise NotImplementedError("WebSocket support not yet implemented")


async def main():
    """Main entry point."""
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and run server
    server = ITGlueMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
