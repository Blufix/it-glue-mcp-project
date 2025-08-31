"""Query processing engine."""

import logging
import time
from datetime import datetime
from typing import Any, Optional

from src.cache import CacheManager
from src.data import UnitOfWork, db_manager
from src.search import HybridSearch

from .parser import ParsedQuery, QueryIntent, QueryParser
from .validator import ZeroHallucinationValidator

logger = logging.getLogger(__name__)


class QueryEngine:
    """Main query processing engine."""

    def __init__(
        self,
        parser: Optional[QueryParser] = None,
        validator: Optional[ZeroHallucinationValidator] = None,
        search: Optional[HybridSearch] = None,
        cache: Optional[CacheManager] = None
    ):
        """Initialize query engine.

        Args:
            parser: Query parser
            validator: Response validator
            search: Search engine
            cache: Cache manager
        """
        self.parser = parser or QueryParser()
        self.validator = validator or ZeroHallucinationValidator()
        self.search = search or HybridSearch()
        self.cache = cache or CacheManager()

    async def process_query(
        self,
        query: str,
        company: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Process a natural language query.

        Args:
            query: Natural language query
            company: Company/organization filter
            context: Additional context

        Returns:
            Query response with validation
        """
        start_time = time.time()

        logger.info(f"Processing query: {query}")

        # Check cache first
        cached_response = await self._check_cache(query, company)
        if cached_response:
            logger.info("Returning cached response")
            return cached_response

        try:
            # Parse query
            parsed = self.parser.parse(query)

            # Add company if provided
            if company and not parsed.company:
                parsed.company = company

            # Enhance with context
            if context:
                parsed = self.parser.enhance_with_context(parsed, context)

            # Route based on intent
            if parsed.intent == QueryIntent.GET_ATTRIBUTE:
                response = await self._handle_get_attribute(parsed)
            elif parsed.intent == QueryIntent.LIST_ENTITIES:
                response = await self._handle_list_entities(parsed)
            elif parsed.intent == QueryIntent.SEARCH:
                response = await self._handle_search(parsed)
            elif parsed.intent == QueryIntent.AGGREGATE:
                response = await self._handle_aggregate(parsed)
            elif parsed.intent == QueryIntent.HELP:
                response = await self._handle_help(parsed)
            else:
                response = await self._handle_search(parsed)

            # Add timing
            response["response_time_ms"] = (time.time() - start_time) * 1000

            # Cache successful responses
            if response.get("success"):
                await self._cache_response(query, company, response)

            # Log query
            await self._log_query(
                query=query,
                company=company,
                response=response
            )

            return response

        except Exception as e:
            logger.error(f"Query processing failed: {e}")

            # Return safe response
            return self.validator.create_safe_response(
                query=query,
                reason=f"Query processing error: {str(e)}"
            )

    async def _handle_get_attribute(self, parsed: ParsedQuery) -> dict[str, Any]:
        """Handle GET_ATTRIBUTE queries.

        Args:
            parsed: Parsed query

        Returns:
            Query response
        """
        # Search for entities
        search_results = await self.search.search(
            query=parsed.original_query,
            company_id=parsed.company,
            entity_type=parsed.entity_type,
            limit=5
        )

        if not search_results:
            return self.validator.create_safe_response(
                query=parsed.original_query,
                reason="No matching entities found"
            )

        # Get top result
        top_result = search_results[0]

        # Fetch full entity data
        async with db_manager.get_session() as session:
            uow = UnitOfWork(session)
            entity = await uow.itglue.get_by_id(top_result.entity_id)

            if not entity:
                return self.validator.create_safe_response(
                    query=parsed.original_query,
                    reason="Entity not found"
                )

            # Extract requested attributes
            response_data = {
                "id": entity.itglue_id,
                "name": entity.name,
                "type": entity.entity_type
            }

            if parsed.attributes:
                for attr in parsed.attributes:
                    if attr in entity.attributes:
                        response_data[attr] = entity.attributes[attr]
            else:
                # Return all key attributes
                response_data.update(entity.attributes)

        # Validate response
        validation = await self.validator.validate_response(
            response={"data": response_data},
            source_ids=[str(entity.id)],
            similarity_scores=[top_result.score]
        )

        if validation.valid:
            return {
                "success": True,
                "query": parsed.original_query,
                "data": response_data,
                "confidence": validation.confidence,
                "source_ids": validation.source_ids,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return self.validator.create_safe_response(
                query=parsed.original_query,
                reason=validation.message
            )

    async def _handle_list_entities(self, parsed: ParsedQuery) -> dict[str, Any]:
        """Handle LIST_ENTITIES queries.

        Args:
            parsed: Parsed query

        Returns:
            Query response
        """
        async with db_manager.get_session() as session:
            uow = UnitOfWork(session)

            # Get entities based on filters
            if parsed.company:
                entities = await uow.itglue.get_by_organization(
                    organization_id=parsed.company,
                    entity_type=parsed.entity_type
                )
            else:
                entities = await uow.itglue.search(
                    query="",
                    entity_type=parsed.entity_type,
                    limit=50
                )

        if not entities:
            return self.validator.create_safe_response(
                query=parsed.original_query,
                reason="No entities found"
            )

        # Format response
        entity_list = []
        source_ids = []

        for entity in entities[:20]:  # Limit to 20 for response size
            entity_list.append({
                "id": entity.itglue_id,
                "name": entity.name,
                "type": entity.entity_type,
                "organization_id": entity.organization_id
            })
            source_ids.append(str(entity.id))

        return {
            "success": True,
            "query": parsed.original_query,
            "data": entity_list,
            "total_count": len(entities),
            "returned_count": len(entity_list),
            "confidence": 1.0,
            "source_ids": source_ids,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _handle_search(self, parsed: ParsedQuery) -> dict[str, Any]:
        """Handle SEARCH queries.

        Args:
            parsed: Parsed query

        Returns:
            Query response
        """
        # Perform hybrid search
        search_results = await self.search.search(
            query=parsed.original_query,
            company_id=parsed.company,
            entity_type=parsed.entity_type,
            limit=10
        )

        if not search_results:
            return self.validator.create_safe_response(
                query=parsed.original_query,
                reason="No search results found"
            )

        # Get full entity data for results
        result_data = []
        source_ids = []
        scores = []

        async with db_manager.get_session() as session:
            uow = UnitOfWork(session)

            for result in search_results[:5]:  # Top 5 results
                entity = await uow.itglue.get_by_id(result.entity_id)

                if entity:
                    result_data.append({
                        "id": entity.itglue_id,
                        "name": entity.name,
                        "type": entity.entity_type,
                        "organization_id": entity.organization_id,
                        "relevance_score": result.score,
                        "highlights": self._extract_highlights(
                            entity,
                            parsed.keywords
                        )
                    })
                    source_ids.append(str(entity.id))
                    scores.append(result.score)

        # Validate response
        validation = await self.validator.validate_response(
            response={"data": result_data},
            source_ids=source_ids,
            similarity_scores=scores
        )

        if validation.valid:
            return {
                "success": True,
                "query": parsed.original_query,
                "data": result_data,
                "total_results": len(search_results),
                "confidence": validation.confidence,
                "source_ids": source_ids,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return self.validator.create_safe_response(
                query=parsed.original_query,
                reason=validation.message
            )

    async def _handle_aggregate(self, parsed: ParsedQuery) -> dict[str, Any]:
        """Handle AGGREGATE queries.

        Args:
            parsed: Parsed query

        Returns:
            Query response
        """
        async with db_manager.get_session() as session:
            uow = UnitOfWork(session)

            # Get entities for aggregation
            if parsed.company:
                entities = await uow.itglue.get_by_organization(
                    organization_id=parsed.company,
                    entity_type=parsed.entity_type
                )
            else:
                entities = await uow.itglue.search(
                    query="",
                    entity_type=parsed.entity_type,
                    limit=1000
                )

        # Calculate aggregates
        count = len(entities)

        # Group by type if no specific type requested
        if not parsed.entity_type:
            type_counts = {}
            for entity in entities:
                entity_type = entity.entity_type
                type_counts[entity_type] = type_counts.get(entity_type, 0) + 1

            aggregate_data = {
                "total_count": count,
                "by_type": type_counts
            }
        else:
            aggregate_data = {
                "count": count,
                "entity_type": parsed.entity_type
            }

        return {
            "success": True,
            "query": parsed.original_query,
            "data": aggregate_data,
            "confidence": 1.0,
            "source_ids": [str(e.id) for e in entities[:10]],  # Sample IDs
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _handle_help(self, parsed: ParsedQuery) -> dict[str, Any]:
        """Handle HELP queries.

        Args:
            parsed: Parsed query

        Returns:
            Query response
        """
        help_text = """
        I can help you with:

        1. **Finding specific information**:
           - "What's the router IP for Company X?"
           - "Show me the printer configuration for Office Y"

        2. **Listing entities**:
           - "List all servers"
           - "Show me all passwords for Company X"

        3. **Searching**:
           - "Search for Windows servers"
           - "Find all printers with IP 192.168.1.*"

        4. **Counting and aggregation**:
           - "How many routers do we have?"
           - "Count of servers by operating system"

        Tips:
        - Be specific about company names
        - Use entity types like: router, server, printer, password, document
        - Ask for specific attributes like: IP, hostname, username, model
        """

        return {
            "success": True,
            "query": parsed.original_query,
            "data": {
                "help": help_text,
                "examples": [
                    "What's the main router IP for Acme Corp?",
                    "List all printers at the Seattle office",
                    "Search for servers with Windows 2019",
                    "How many active configurations do we have?"
                ]
            },
            "confidence": 1.0,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _extract_highlights(
        self,
        entity: Any,
        keywords: Optional[list[str]]
    ) -> list[str]:
        """Extract text highlights based on keywords.

        Args:
            entity: Entity to extract from
            keywords: Keywords to highlight

        Returns:
            List of highlight snippets
        """
        if not keywords:
            return []

        highlights = []
        search_text = entity.search_text or ""

        for keyword in keywords[:3]:  # Limit to 3 keywords
            # Find keyword in text
            index = search_text.lower().find(keyword.lower())
            if index >= 0:
                # Extract snippet around keyword
                start = max(0, index - 30)
                end = min(len(search_text), index + len(keyword) + 30)
                snippet = search_text[start:end]

                if start > 0:
                    snippet = "..." + snippet
                if end < len(search_text):
                    snippet = snippet + "..."

                highlights.append(snippet)

        return highlights

    async def _check_cache(
        self,
        query: str,
        company: Optional[str]
    ) -> Optional[dict[str, Any]]:
        """Check cache for query result.

        Args:
            query: Query string
            company: Company filter

        Returns:
            Cached response or None
        """
        try:
            return await self.cache.get(query, company)
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
            return None

    async def _cache_response(
        self,
        query: str,
        company: Optional[str],
        response: dict[str, Any]
    ):
        """Cache query response.

        Args:
            query: Query string
            company: Company filter
            response: Response to cache
        """
        try:
            await self.cache.set(
                query=query,
                company=company,
                response=response,
                ttl=300  # 5 minutes
            )
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")

    async def _log_query(
        self,
        query: str,
        company: Optional[str],
        response: dict[str, Any]
    ):
        """Log query for audit.

        Args:
            query: Query string
            company: Company filter
            response: Query response
        """
        try:
            async with db_manager.get_session() as session:
                uow = UnitOfWork(session)

                await uow.query_log.log_query(
                    query=query,
                    company=company,
                    response=response,
                    confidence_score=response.get("confidence"),
                    source_ids=response.get("source_ids"),
                    response_time_ms=response.get("response_time_ms")
                )

                await uow.commit()

        except Exception as e:
            logger.error(f"Failed to log query: {e}")
