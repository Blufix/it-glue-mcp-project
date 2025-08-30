"""Query tool for natural language IT Glue queries."""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from .base import BaseTool
from src.services.query_engine import QueryEngine
from src.services.cache import CacheService
from src.config.settings import settings


class QueryTool(BaseTool):
    """Natural language query tool for IT Glue documentation."""
    
    def __init__(self, query_engine: QueryEngine, cache_service: CacheService):
        """Initialize query tool.
        
        Args:
            query_engine: Query engine instance
            cache_service: Cache service instance
        """
        super().__init__(
            name="query",
            description="Natural language query for IT Glue documentation"
        )
        self.query_engine = query_engine
        self.cache = cache_service
        
    async def execute(
        self,
        query: str,
        company: Optional[str] = None,
        include_sources: bool = True,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute natural language query.
        
        Args:
            query: Natural language question
            company: Company name or ID (optional)
            include_sources: Include source references in response
            use_cache: Use cached results if available
            **kwargs: Additional query parameters
            
        Returns:
            Query results
        """
        try:
            # Validate parameters
            if not query:
                return self.format_error("Query cannot be empty")
                
            self.logger.info(f"Processing query: {query[:100]}... for company: {company}")
            
            # Check cache if enabled
            cache_key = None
            if use_cache:
                cache_key = f"query:{company or 'all'}:{query}"
                cached = await self.cache.get(cache_key)
                if cached:
                    self.logger.debug(f"Cache hit for query: {cache_key}")
                    return self.format_success(
                        cached,
                        cached=True,
                        cache_key=cache_key
                    )
            
            # Execute query through query engine
            result = await self.query_engine.execute(
                query=query,
                company=company,
                include_sources=include_sources
            )
            
            # Format response
            response_data = {
                "query": query,
                "company": company,
                "answer": result.answer,
                "confidence": result.confidence,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if include_sources and result.sources:
                response_data["sources"] = [
                    {
                        "id": source.id,
                        "type": source.type,
                        "title": source.title,
                        "relevance": source.relevance
                    }
                    for source in result.sources
                ]
            
            # Additional metadata
            if result.metadata:
                response_data["metadata"] = result.metadata
            
            # Cache the result
            if use_cache and cache_key:
                await self.cache.set(
                    cache_key,
                    response_data,
                    ttl=settings.cache_ttl
                )
                self.logger.debug(f"Cached query result: {cache_key}")
            
            return self.format_success(
                response_data,
                cached=False
            )
            
        except Exception as e:
            self.logger.error(f"Query execution error: {e}", exc_info=True)
            return self.format_error(
                f"Query failed: {str(e)}",
                query=query,
                company=company
            )
            
    async def validate_query(self, query: str) -> Dict[str, Any]:
        """Validate and analyze query before execution.
        
        Args:
            query: Query to validate
            
        Returns:
            Validation result with query analysis
        """
        try:
            analysis = await self.query_engine.analyze_query(query)
            
            return {
                "valid": analysis.is_valid,
                "query_type": analysis.query_type,
                "entities": analysis.entities,
                "intent": analysis.intent,
                "suggestions": analysis.suggestions
            }
            
        except Exception as e:
            self.logger.error(f"Query validation error: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
            
    async def get_suggestions(
        self,
        partial_query: str,
        company: Optional[str] = None,
        limit: int = 5
    ) -> List[str]:
        """Get query suggestions based on partial input.
        
        Args:
            partial_query: Partial query string
            company: Company context
            limit: Maximum number of suggestions
            
        Returns:
            List of query suggestions
        """
        try:
            suggestions = await self.query_engine.get_suggestions(
                partial_query=partial_query,
                company=company,
                limit=limit
            )
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Suggestion generation error: {e}")
            return []