"""FastAPI application for health and admin endpoints."""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config.settings import settings
from src.data import db_manager, get_uow
from src.query import QueryEngine
from src.sync import SyncOrchestrator
from src.cache import CacheManager
from src.search import SemanticSearch

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="IT Glue MCP Server API",
    description="Health, admin, and debugging endpoints for IT Glue MCP Server",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class QueryRequest(BaseModel):
    """Query request model."""
    query: str
    company: Optional[str] = None
    
    
class SyncRequest(BaseModel):
    """Sync request model."""
    organization_id: Optional[str] = None
    full_sync: bool = False
    entity_types: Optional[List[str]] = None
    

class CacheInvalidateRequest(BaseModel):
    """Cache invalidation request."""
    query: Optional[str] = None
    company: Optional[str] = None
    

# Global instances
query_engine: Optional[QueryEngine] = None
sync_orchestrator: Optional[SyncOrchestrator] = None
cache_manager: Optional[CacheManager] = None
semantic_search: Optional[SemanticSearch] = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global query_engine, sync_orchestrator, cache_manager, semantic_search
    
    logger.info("Starting FastAPI application")
    
    try:
        # Initialize database
        await db_manager.initialize()
        await db_manager.create_tables()
        
        # Initialize cache
        cache_manager = CacheManager()
        await cache_manager.connect()
        
        # Initialize search
        semantic_search = SemanticSearch()
        await semantic_search.initialize_collection()
        
        # Initialize query engine
        query_engine = QueryEngine(
            cache=cache_manager
        )
        
        # Initialize sync orchestrator
        sync_orchestrator = SyncOrchestrator()
        
        logger.info("All services initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down FastAPI application")
    
    try:
        if cache_manager:
            await cache_manager.disconnect()
            
        await db_manager.close()
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Health endpoints
@app.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0"
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check of all components."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # Check database
    try:
        if await db_manager.healthcheck():
            health_status["components"]["database"] = "healthy"
        else:
            health_status["components"]["database"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
        
    # Check cache
    try:
        if cache_manager:
            stats = await cache_manager.get_stats()
            health_status["components"]["cache"] = {
                "status": "healthy",
                "stats": stats
            }
        else:
            health_status["components"]["cache"] = "not_initialized"
    except Exception as e:
        health_status["components"]["cache"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
        
    # Check search
    try:
        if semantic_search:
            stats = await semantic_search.get_collection_stats()
            health_status["components"]["search"] = {
                "status": "healthy",
                "stats": stats
            }
        else:
            health_status["components"]["search"] = "not_initialized"
    except Exception as e:
        health_status["components"]["search"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
        
    return health_status


# Query endpoints
@app.post("/query")
async def execute_query(request: QueryRequest):
    """Execute a natural language query."""
    if not query_engine:
        raise HTTPException(status_code=503, detail="Query engine not initialized")
        
    try:
        result = await query_engine.process_query(
            query=request.query,
            company=request.company
        )
        return result
        
    except Exception as e:
        logger.error(f"Query execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/query/history")
async def get_query_history(
    limit: int = Query(100, ge=1, le=1000),
    company: Optional[str] = None
):
    """Get query history."""
    try:
        async with db_manager.get_session() as session:
            from src.data import UnitOfWork
            uow = UnitOfWork(session)
            
            queries = await uow.query_log.get_recent_queries(
                limit=limit,
                company=company
            )
            
            return {
                "success": True,
                "queries": [
                    {
                        "id": str(q.id),
                        "query": q.query,
                        "company": q.company,
                        "confidence_score": q.confidence_score,
                        "response_time_ms": q.response_time_ms,
                        "created_at": q.created_at.isoformat() if q.created_at else None
                    }
                    for q in queries
                ],
                "count": len(queries)
            }
            
    except Exception as e:
        logger.error(f"Failed to get query history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Sync endpoints
@app.post("/sync/trigger")
async def trigger_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks
):
    """Trigger data synchronization."""
    if not sync_orchestrator:
        raise HTTPException(status_code=503, detail="Sync orchestrator not initialized")
        
    try:
        # Run sync in background
        if request.organization_id:
            background_tasks.add_task(
                sync_orchestrator.sync_organization,
                request.organization_id
            )
            message = f"Sync triggered for organization {request.organization_id}"
        else:
            background_tasks.add_task(
                sync_orchestrator.sync_all,
                request.full_sync
            )
            message = f"{'Full' if request.full_sync else 'Incremental'} sync triggered"
            
        return {
            "success": True,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sync/status")
async def get_sync_status():
    """Get sync status for all entity types."""
    try:
        async with db_manager.get_session() as session:
            from src.data import UnitOfWork
            uow = UnitOfWork(session)
            
            # Get all sync statuses
            statuses = await uow.sync_status.get_all()
            
            return {
                "success": True,
                "statuses": [
                    {
                        "entity_type": s.entity_type,
                        "last_sync_started": s.last_sync_started.isoformat() if s.last_sync_started else None,
                        "last_sync_completed": s.last_sync_completed.isoformat() if s.last_sync_completed else None,
                        "last_sync_status": s.last_sync_status,
                        "records_synced": s.records_synced,
                        "error_message": s.error_message
                    }
                    for s in statuses
                ]
            }
            
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Cache endpoints
@app.post("/cache/invalidate")
async def invalidate_cache(request: CacheInvalidateRequest):
    """Invalidate cache entries."""
    if not cache_manager:
        raise HTTPException(status_code=503, detail="Cache manager not initialized")
        
    try:
        count = await cache_manager.invalidate(
            query=request.query,
            company=request.company
        )
        
        return {
            "success": True,
            "invalidated_count": count
        }
        
    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    if not cache_manager:
        raise HTTPException(status_code=503, detail="Cache manager not initialized")
        
    try:
        stats = await cache_manager.get_stats()
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Admin endpoints
@app.get("/admin/stats")
async def get_admin_stats():
    """Get overall system statistics."""
    try:
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "entities": {},
            "queries": {},
            "cache": {},
            "search": {}
        }
        
        # Get entity counts
        async with db_manager.get_session() as session:
            from src.data import UnitOfWork
            uow = UnitOfWork(session)
            
            # Count entities by type
            entities = await uow.itglue.get_all(limit=10000)
            entity_counts = {}
            
            for entity in entities:
                entity_type = entity.entity_type
                entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
                
            stats["entities"] = {
                "total": len(entities),
                "by_type": entity_counts
            }
            
            # Get query stats
            recent_queries = await uow.query_log.get_recent_queries(limit=1000)
            
            if recent_queries:
                response_times = [q.response_time_ms for q in recent_queries if q.response_time_ms]
                stats["queries"] = {
                    "total": len(recent_queries),
                    "avg_response_time_ms": sum(response_times) / len(response_times) if response_times else 0,
                    "min_response_time_ms": min(response_times) if response_times else 0,
                    "max_response_time_ms": max(response_times) if response_times else 0
                }
                
        # Get cache stats
        if cache_manager:
            stats["cache"] = await cache_manager.get_stats()
            
        # Get search stats
        if semantic_search:
            stats["search"] = await semantic_search.get_collection_stats()
            
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get admin stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/config")
async def get_config():
    """Get current configuration (non-sensitive)."""
    return {
        "environment": settings.environment,
        "debug": settings.debug,
        "log_level": settings.log_level,
        "it_glue_api_url": settings.it_glue_api_url,
        "it_glue_rate_limit": settings.it_glue_rate_limit,
        "database_url": settings.database_url.split("@")[1] if "@" in settings.database_url else "configured",
        "redis_url": "configured" if settings.redis_url else "not configured",
        "qdrant_url": settings.qdrant_url or "default",
        "ollama_url": settings.ollama_url or "not configured",
        "openai_configured": bool(settings.openai_api_key)
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "IT Glue MCP Server API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level=settings.log_level.lower()
    )