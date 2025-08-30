"""Main MCP server implementation."""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from mcp.server import Server, Tool
from mcp.server.stdio import stdio_server
import json

from src.config.settings import settings
from src.data import db_manager
from src.query import QueryEngine
from src.search import HybridSearch
from src.sync import SyncOrchestrator
from src.cache import CacheManager
from src.services.itglue import ITGlueClient

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
        async def query(query: str, company: Optional[str] = None) -> Dict:
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
            filters: Optional[Dict] = None
        ) -> Dict:
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
        async def health() -> Dict:
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
        async def list_companies() -> Dict:
            """
            List available companies.
            
            Returns:
                List of companies
            """
            try:
                # Initialize if needed
                if not self._initialized:
                    await self._initialize_components()
                
                if not self.itglue_client:
                    return {
                        "success": False,
                        "error": "IT Glue client not initialized",
                        "companies": []
                    }
                
                # Fetch organizations from IT Glue
                async with self.itglue_client:
                    organizations = await self.itglue_client.get_organizations()
                
                # Format results
                companies = [
                    {
                        "id": org.id,
                        "name": org.attributes.get("name", ""),
                        "type": org.attributes.get("organization_type_name", "Customer")
                    }
                    for org in organizations[:50]  # Limit to 50 for response size
                ]
                
                return {
                    "success": True,
                    "companies": companies,
                    "count": len(companies)
                }
                
            except Exception as e:
                logger.error(f"List companies error: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e),
                    "companies": []
                }
        
        @self.server.tool()
        async def sync_data(
            organization_id: Optional[str] = None,
            full_sync: bool = False
        ) -> Dict:
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
        logger.info(f"Starting MCP server on stdio")
        
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