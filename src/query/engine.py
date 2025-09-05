"""Query processing engine."""

import logging
import time
from datetime import datetime
from typing import Any, Optional

from src.cache import CacheManager
from src.data import UnitOfWork, db_manager
from src.search import HybridSearch
from src.services.itglue import ITGlueClient

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
        cache: Optional[CacheManager] = None,
        itglue_client: Optional[ITGlueClient] = None
    ):
        """Initialize query engine.

        Args:
            parser: Query parser
            validator: Response validator
            search: Search engine
            cache: Cache manager
            itglue_client: IT Glue API client
        """
        self.parser = parser or QueryParser()
        self.validator = validator or ZeroHallucinationValidator()
        self.search = search or HybridSearch()
        self.cache = cache or CacheManager()
        self.itglue_client = itglue_client or ITGlueClient()
        self._company_cache = {}  # Cache company name to ID mappings

    async def process_query(
        self,
        query: str,
        company: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Process a natural language query.

        Args:
            query: Natural language query
            company: Company/organization filter (name or ID)
            context: Additional context

        Returns:
            Query response with validation
        """
        start_time = time.time()

        logger.info(f"Processing query: {query} for company: {company}")

        # Check cache first
        cached_response = await self._check_cache(query, company)
        if cached_response:
            logger.info("Returning cached response")
            return cached_response

        try:
            # Parse query
            parsed = self.parser.parse(query)

            # Resolve company name to ID if provided
            company_id = None
            if company:
                company_id = await self._resolve_company_to_id(company)
                if not company_id:
                    logger.warning(f"Could not resolve company '{company}' to ID")
                    # Still set the company name for fallback filtering
                    parsed.company = company
                else:
                    logger.info(f"Resolved company '{company}' to ID: {company_id}")
                    parsed.company = company_id
                    parsed.company_name = company
            
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
        # Only pass company_id if it's numeric (successfully resolved)
        search_company_id = None
        if parsed.company and str(parsed.company).isdigit():
            search_company_id = parsed.company
            
        # Search for entities
        search_results = await self.search.search(
            query=parsed.original_query,
            company_id=search_company_id,  # Only pass numeric IDs
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
        logger.info(f"LIST_ENTITIES: company={parsed.company}, entity_type={parsed.entity_type}")
        
        async with db_manager.get_session() as session:
            uow = UnitOfWork(session)

            # Get entities based on filters
            # Only use get_by_organization if we have a numeric ID
            if parsed.company and str(parsed.company).isdigit():
                logger.info(f"Using get_by_organization with ID: {parsed.company}")
                entities = await uow.itglue.get_by_organization(
                    organization_id=parsed.company,
                    entity_type=parsed.entity_type
                )
            else:
                logger.info(f"Using search with entity_type: {parsed.entity_type}")
                entities = await uow.itglue.search(
                    query="",
                    entity_type=parsed.entity_type,
                    limit=1000  # Get ALL entities for testing
                )
        
        logger.info(f"Found {len(entities) if entities else 0} entities")

        if not entities:
            return self.validator.create_safe_response(
                query=parsed.original_query,
                reason="No entities found"
            )

        # Format response
        entity_list = []
        source_ids = []

        for entity in entities:  # NO LIMIT - show ALL entities
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
        # Only pass company_id if it's numeric (successfully resolved)
        # If it's a string name, don't pass it to avoid SQL mismatch
        search_company_id = None
        if parsed.company and str(parsed.company).isdigit():
            search_company_id = parsed.company
            
        # Perform hybrid search
        logger.info(f"Searching with: query='{parsed.original_query}', company_id={search_company_id}, entity_type={parsed.entity_type}")
        search_results = await self.search.search(
            query=parsed.original_query,
            company_id=search_company_id,  # Only pass numeric IDs
            entity_type=parsed.entity_type,
            limit=200,  # No limit for testing - get ALL results
            min_score=0.0  # Accept ALL results regardless of score
        )
        logger.info(f"Search returned {len(search_results)} results")

        if not search_results:
            return self.validator.create_safe_response(
                query=parsed.original_query,
                reason="No search results found"
            )

        # Get full entity data for results
        result_data = []
        source_ids = []
        scores = []
        company_name = getattr(parsed, 'company_name', None)

        async with db_manager.get_session() as session:
            uow = UnitOfWork(session)

            # Check if we have a resolved company ID (numeric) vs name
            company_id_resolved = parsed.company and str(parsed.company).isdigit()
            
            # If we couldn't resolve company to ID, we need to filter by name
            company_name_filter = None
            if parsed.company and not company_id_resolved:
                # We have a company name but couldn't resolve it to ID
                company_name_filter = parsed.company.lower()
            
            for result in search_results:  # Process all results
                entity = await uow.itglue.get_by_id(result.entity_id)

                if entity:
                    # Filter by organization ID if we have a resolved numeric ID
                    if company_id_resolved and hasattr(entity, 'organization_id'):
                        # Compare numeric IDs
                        if entity.organization_id and str(entity.organization_id) != str(parsed.company):
                            logger.debug(f"Filtering out entity from org {entity.organization_id} (looking for {parsed.company})")
                            continue
                    
                    # Filter by organization name if we couldn't resolve to ID
                    # This is a fallback when IT Glue API organization lookup fails
                    elif company_name_filter and hasattr(entity, 'attributes'):
                        # Check if entity has organization info in attributes
                        org_info = entity.attributes.get('organization', {})
                        if isinstance(org_info, dict):
                            org_name = org_info.get('name', '').lower()
                            if org_name and company_name_filter not in org_name:
                                logger.debug(f"Filtering out entity from org '{org_name}' (looking for '{company_name_filter}')")
                                continue
                    
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
                    
                    # NO LIMIT for testing - show ALL results
                    # if len(result_data) >= 20:
                    #     break

        logger.info(f"After filtering, returning {len(result_data)} results")

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
            # Only use get_by_organization if we have a numeric ID
            if parsed.company and str(parsed.company).isdigit():
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
            # Use the new cache interface if available
            if self.cache and hasattr(self.cache, 'query_cache'):
                cache_key = f"query:{query}:company:{company or ''}"
                return await self.cache.query_cache.get(cache_key)
            # Fallback to legacy cache interface  
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
            # Use the new cache interface if available
            if self.cache and hasattr(self.cache, 'query_cache'):
                cache_key = f"query:{query}:company:{company or ''}"
                from ..cache.redis_cache import QueryType
                await self.cache.query_cache.set(cache_key, response, QueryType.OPERATIONAL)
            else:
                # Fallback to legacy cache interface
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
    
    async def _resolve_company_to_id(self, company: str) -> Optional[str]:
        """Resolve company name to IT Glue organization ID.
        
        Args:
            company: Company name or ID
            
        Returns:
            Organization ID or None if not found
        """
        # Check cache first
        if company in self._company_cache:
            return self._company_cache[company]
        
        # If already looks like an ID (numeric), return as-is
        if company.isdigit():
            return company
            
        try:
            # First try exact search with API filter
            orgs = await self.itglue_client.get_organizations(
                filters={"name": company}
            )
            
            # If no results from filtered search, get all organizations for fuzzy matching
            if not orgs:
                logger.debug(f"No exact match for '{company}', trying fuzzy search")
                orgs = await self.itglue_client.get_organizations()
            
            if orgs:
                # The response is a list of Organization objects
                # Look for exact match first
                for org in orgs:
                    org_name = org.name if hasattr(org, 'name') else org.get('name', '')
                    org_id = org.id if hasattr(org, 'id') else org.get('id')
                    
                    if org_name and org_name.lower() == company.lower():
                        if org_id:
                            self._company_cache[company] = str(org_id)
                            logger.info(f"Resolved company '{company}' to ID: {org_id} (exact match)")
                            return str(org_id)
                
                # If no exact match, try partial match (company name contained in org name)
                for org in orgs:
                    org_name = org.name if hasattr(org, 'name') else org.get('name', '')
                    org_id = org.id if hasattr(org, 'id') else org.get('id')
                    
                    if org_name and company.lower() in org_name.lower():
                        if org_id:
                            self._company_cache[company] = str(org_id)
                            logger.info(f"Resolved company '{company}' to ID: {org_id} (partial match: '{org_name}')")
                            return str(org_id)
                
                # Try reverse partial match (org name contained in company name)
                for org in orgs:
                    org_name = org.name if hasattr(org, 'name') else org.get('name', '')
                    org_id = org.id if hasattr(org, 'id') else org.get('id')
                    
                    if org_name and org_name.lower() in company.lower():
                        if org_id:
                            self._company_cache[company] = str(org_id)
                            logger.info(f"Resolved company '{company}' to ID: {org_id} (reverse match: '{org_name}')")
                            return str(org_id)
            
            logger.warning(f"Could not find organization for company: {company}")
            return None
            
        except Exception as e:
            logger.error(f"Error resolving company to ID: {e}")
            return None
