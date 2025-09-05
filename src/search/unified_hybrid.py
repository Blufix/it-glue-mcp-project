"""Unified hybrid search combining PostgreSQL, Qdrant, and Neo4j."""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum

from neo4j import AsyncGraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
import aiohttp

from src.data import UnitOfWork, db_manager
from src.config.settings import settings
from src.graph.graph_traversal import GraphTraversal, TraversalType

logger = logging.getLogger(__name__)


class SearchMode(Enum):
    """Search modes for unified search."""
    KEYWORD = "keyword"  # PostgreSQL text search
    SEMANTIC = "semantic"  # Qdrant vector search
    GRAPH = "graph"  # Neo4j relationship search
    HYBRID = "hybrid"  # Combined all three
    IMPACT = "impact"  # Neo4j impact analysis
    DEPENDENCY = "dependency"  # Neo4j dependency tree


@dataclass
class UnifiedSearchResult:
    """Unified search result from all sources."""
    
    id: str
    entity_id: str
    name: str
    entity_type: str
    organization_id: Optional[str]
    
    # Scores from different sources
    total_score: float
    keyword_score: Optional[float] = None
    semantic_score: Optional[float] = None
    graph_score: Optional[float] = None
    
    # Source information
    sources: list[str] = field(default_factory=list)
    
    # Additional context
    highlights: list[str] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)
    impact_analysis: Optional[dict] = None
    payload: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "name": self.name,
            "entity_type": self.entity_type,
            "organization_id": self.organization_id,
            "total_score": self.total_score,
            "keyword_score": self.keyword_score,
            "semantic_score": self.semantic_score,
            "graph_score": self.graph_score,
            "sources": self.sources,
            "highlights": self.highlights,
            "relationships": self.relationships,
            "impact_analysis": self.impact_analysis,
            "payload": self.payload
        }


class UnifiedHybridSearch:
    """Unified search across PostgreSQL, Qdrant, and Neo4j."""
    
    def __init__(
        self,
        keyword_weight: float = 0.3,
        semantic_weight: float = 0.5,
        graph_weight: float = 0.2
    ):
        """Initialize unified hybrid search.
        
        Args:
            keyword_weight: Weight for PostgreSQL keyword search
            semantic_weight: Weight for Qdrant semantic search  
            graph_weight: Weight for Neo4j graph relationships
        """
        # Normalize weights
        total = keyword_weight + semantic_weight + graph_weight
        self.keyword_weight = keyword_weight / total
        self.semantic_weight = semantic_weight / total
        self.graph_weight = graph_weight / total
        
        # Initialize clients
        self.qdrant_client = None
        self.neo4j_driver = None
        self.graph_traversal = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize all database connections."""
        if self._initialized:
            return
            
        try:
            # Initialize PostgreSQL (through db_manager)
            await db_manager.initialize()
            logger.info("✅ PostgreSQL initialized")
            
            # Initialize Qdrant
            self.qdrant_client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key if settings.qdrant_api_key else None,
                check_compatibility=False
            )
            logger.info("✅ Qdrant client initialized")
            
            # Initialize Neo4j
            self.neo4j_driver = AsyncGraphDatabase.driver(
                "bolt://localhost:7688",
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            
            # Initialize GraphTraversal
            self.graph_traversal = GraphTraversal(
                neo4j_uri="bolt://localhost:7688",
                neo4j_user=settings.neo4j_user,
                neo4j_password=settings.neo4j_password
            )
            await self.graph_traversal.connect()
            logger.info("✅ Neo4j initialized")
            
            self._initialized = True
            logger.info("✅ UnifiedHybridSearch fully initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize UnifiedHybridSearch: {e}")
            raise
    
    async def search(
        self,
        query: str,
        mode: SearchMode = SearchMode.HYBRID,
        organization_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 10,
        min_score: float = 0.3
    ) -> list[UnifiedSearchResult]:
        """Perform unified search across all systems.
        
        Args:
            query: Search query
            mode: Search mode to use
            organization_id: Filter by organization
            entity_type: Filter by entity type
            limit: Maximum results
            min_score: Minimum score threshold
            
        Returns:
            List of unified search results
        """
        await self.initialize()
        
        if mode == SearchMode.KEYWORD:
            return await self._keyword_only_search(
                query, organization_id, entity_type, limit
            )
        elif mode == SearchMode.SEMANTIC:
            return await self._semantic_only_search(
                query, organization_id, entity_type, limit
            )
        elif mode == SearchMode.GRAPH:
            return await self._graph_only_search(
                query, organization_id, entity_type, limit
            )
        elif mode == SearchMode.IMPACT:
            return await self._impact_analysis_search(
                query, limit
            )
        elif mode == SearchMode.DEPENDENCY:
            return await self._dependency_search(
                query, limit
            )
        else:  # HYBRID
            return await self._hybrid_search(
                query, organization_id, entity_type, limit, min_score
            )
    
    async def _hybrid_search(
        self,
        query: str,
        organization_id: Optional[str],
        entity_type: Optional[str],
        limit: int,
        min_score: float
    ) -> list[UnifiedSearchResult]:
        """Perform hybrid search combining all three systems."""
        
        # Run searches in parallel
        keyword_results = await self._get_keyword_results(
            query, organization_id, entity_type, limit * 2
        )
        
        semantic_results = await self._get_semantic_results(
            query, organization_id, entity_type, limit * 2
        )
        
        graph_results = await self._get_graph_results(
            query, organization_id, limit * 2
        )
        
        # Combine results
        combined = {}
        
        # Add keyword results
        for entity_id, score, data in keyword_results:
            combined[entity_id] = UnifiedSearchResult(
                id=entity_id,
                entity_id=entity_id,
                name=data.get("name", ""),
                entity_type=data.get("entity_type", ""),
                organization_id=data.get("organization_id"),
                total_score=score * self.keyword_weight,
                keyword_score=score,
                sources=["keyword"],
                payload=data
            )
        
        # Add/merge semantic results
        for entity_id, score, data in semantic_results:
            if entity_id in combined:
                result = combined[entity_id]
                result.semantic_score = score
                result.total_score += score * self.semantic_weight
                result.sources.append("semantic")
                result.payload.update(data)
            else:
                combined[entity_id] = UnifiedSearchResult(
                    id=entity_id,
                    entity_id=entity_id,
                    name=data.get("name", ""),
                    entity_type=data.get("entity_type", ""),
                    organization_id=data.get("organization_id"),
                    total_score=score * self.semantic_weight,
                    semantic_score=score,
                    sources=["semantic"],
                    payload=data
                )
        
        # Add/merge graph results
        for entity_id, score, relationships in graph_results:
            if entity_id in combined:
                result = combined[entity_id]
                result.graph_score = score
                result.total_score += score * self.graph_weight
                result.sources.append("graph")
                result.relationships = relationships
            else:
                # Fetch entity details for graph-only results
                entity_data = await self._fetch_entity_details(entity_id)
                if entity_data:
                    combined[entity_id] = UnifiedSearchResult(
                        id=entity_id,
                        entity_id=entity_id,
                        name=entity_data.get("name", ""),
                        entity_type=entity_data.get("entity_type", ""),
                        organization_id=entity_data.get("organization_id"),
                        total_score=score * self.graph_weight,
                        graph_score=score,
                        sources=["graph"],
                        relationships=relationships,
                        payload=entity_data
                    )
        
        # Filter and sort results
        results = [
            r for r in combined.values()
            if r.total_score >= min_score
        ]
        
        results.sort(key=lambda x: x.total_score, reverse=True)
        
        return results[:limit]
    
    async def _get_keyword_results(
        self,
        query: str,
        organization_id: Optional[str],
        entity_type: Optional[str],
        limit: int
    ) -> list[tuple[str, float, dict]]:
        """Get keyword search results from PostgreSQL."""
        try:
            async with db_manager.get_session() as session:
                uow = UnitOfWork(session)
                
                results = await uow.itglue.search(
                    query=query,
                    organization_id=organization_id,
                    entity_type=entity_type,
                    limit=limit
                )
                
                keyword_results = []
                query_lower = query.lower()
                query_terms = set(query_lower.split())
                
                for entity in results:
                    # Calculate relevance score
                    text = (entity.search_text or "").lower()
                    text_terms = set(text.split())
                    
                    overlap = len(query_terms & text_terms)
                    score = overlap / len(query_terms) if query_terms else 0
                    
                    # Boost for exact name match
                    if query_lower in (entity.name or "").lower():
                        score = min(1.0, score + 0.5)
                    
                    keyword_results.append((
                        str(entity.id),
                        score,
                        {
                            "entity_id": str(entity.id),
                            "itglue_id": entity.itglue_id,
                            "name": entity.name,
                            "entity_type": entity.entity_type,
                            "organization_id": entity.organization_id,
                            "attributes": entity.attributes
                        }
                    ))
                
                return keyword_results
                
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    async def _get_semantic_results(
        self,
        query: str,
        organization_id: Optional[str],
        entity_type: Optional[str],
        limit: int
    ) -> list[tuple[str, float, dict]]:
        """Get semantic search results from Qdrant."""
        try:
            # Generate embedding for query
            embedding = await self._generate_embedding(query)
            
            if not embedding:
                return []
            
            # Search in Qdrant
            results = self.qdrant_client.search(
                collection_name="itglue_entities",
                query_vector=embedding,
                limit=limit,
                score_threshold=0.3
            )
            
            semantic_results = []
            for result in results:
                payload = result.payload or {}
                
                # Apply filters if specified
                if organization_id and payload.get("organization_id") != organization_id:
                    continue
                if entity_type and payload.get("entity_type") != entity_type:
                    continue
                
                semantic_results.append((
                    payload.get("entity_id", str(result.id)),
                    result.score,
                    payload
                ))
            
            return semantic_results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    async def _get_graph_results(
        self,
        query: str,
        organization_id: Optional[str],
        limit: int
    ) -> list[tuple[str, float, list]]:
        """Get graph-based results from Neo4j."""
        try:
            async with self.neo4j_driver.session() as session:
                # Search for nodes matching the query
                cypher_query = """
                MATCH (n)
                WHERE toLower(n.name) CONTAINS toLower($search_query)
                %s
                
                // Find related nodes
                OPTIONAL MATCH (n)-[r]-(related)
                
                WITH n, collect(DISTINCT {
                    type: type(r),
                    direction: CASE WHEN startNode(r) = n THEN 'outgoing' ELSE 'incoming' END,
                    related_id: related.itglue_id,
                    related_name: related.name
                }) as relationships
                
                RETURN 
                    n.itglue_id as entity_id,
                    n.name as name,
                    labels(n) as labels,
                    size(relationships) as relationship_count,
                    relationships
                ORDER BY relationship_count DESC
                LIMIT $limit
                """ % ("AND n.organization_id = $org_id" if organization_id else "")
                
                params = {"search_query": query, "limit": limit}
                if organization_id:
                    params["org_id"] = organization_id
                
                result = await session.run(cypher_query, **params)
                
                graph_results = []
                async for record in result:
                    # Calculate graph relevance score
                    rel_count = record["relationship_count"]
                    score = min(1.0, rel_count / 10)  # Normalize by relationship count
                    
                    graph_results.append((
                        record["entity_id"],
                        score,
                        record["relationships"]
                    ))
                
                return graph_results
                
        except Exception as e:
            logger.error(f"Graph search failed: {e}")
            return []
    
    async def _impact_analysis_search(
        self,
        entity_name: str,
        limit: int
    ) -> list[UnifiedSearchResult]:
        """Perform impact analysis for an entity."""
        try:
            # First find the entity in Neo4j
            async with self.neo4j_driver.session() as session:
                result = await session.run("""
                    MATCH (n)
                    WHERE toLower(n.name) CONTAINS toLower($name)
                    RETURN n.itglue_id as entity_id, n.name as name
                    LIMIT 1
                """, name=entity_name)
                
                record = await result.single()
                if not record:
                    return []
                
                entity_id = record["entity_id"]
                
                # Perform impact analysis
                impact_result = await session.run("""
                    MATCH (source {itglue_id: $entity_id})
                    OPTIONAL MATCH (affected)-[:CONNECTS_TO|DEPENDS_ON|ROUTES_THROUGH*1..3]->(source)
                    
                    WITH source, affected
                    WHERE affected IS NOT NULL AND affected <> source
                    
                    RETURN 
                        affected.itglue_id as entity_id,
                        affected.name as name,
                        labels(affected) as labels,
                        size([(affected)-[]-(source) | 1]) as direct_connections,
                        size([(affected)-[*2]-(source) | 1]) as indirect_connections
                    ORDER BY direct_connections DESC, indirect_connections DESC
                    LIMIT $limit
                """, entity_id=entity_id, limit=limit)
                
                results = []
                async for affected in impact_result:
                    # Calculate impact score
                    score = min(1.0, (affected["direct_connections"] * 0.7 + 
                                     affected["indirect_connections"] * 0.3) / 5)
                    
                    # Fetch additional entity details
                    entity_data = await self._fetch_entity_details(affected["entity_id"])
                    
                    results.append(UnifiedSearchResult(
                        id=affected["entity_id"],
                        entity_id=affected["entity_id"],
                        name=affected["name"],
                        entity_type=affected["labels"][0] if affected["labels"] else "Unknown",
                        organization_id=entity_data.get("organization_id") if entity_data else None,
                        total_score=score,
                        graph_score=score,
                        sources=["graph", "impact"],
                        impact_analysis={
                            "source_entity": entity_name,
                            "direct_connections": affected["direct_connections"],
                            "indirect_connections": affected["indirect_connections"],
                            "impact_level": "high" if score > 0.7 else "medium" if score > 0.4 else "low"
                        },
                        payload=entity_data or {}
                    ))
                
                return results
                
        except Exception as e:
            logger.error(f"Impact analysis failed: {e}")
            return []
    
    async def _dependency_search(
        self,
        entity_name: str,
        limit: int
    ) -> list[UnifiedSearchResult]:
        """Find dependencies for an entity."""
        try:
            # Find entity and its dependencies
            async with self.neo4j_driver.session() as session:
                result = await session.run("""
                    MATCH (n)
                    WHERE toLower(n.name) CONTAINS toLower($name)
                    WITH n LIMIT 1
                    
                    MATCH (n)-[r:DEPENDS_ON|HOSTED_ON|CONNECTS_TO]->(dependency)
                    
                    RETURN 
                        dependency.itglue_id as entity_id,
                        dependency.name as name,
                        labels(dependency) as labels,
                        type(r) as relationship_type
                    LIMIT $limit
                """, name=entity_name, limit=limit)
                
                results = []
                async for record in result:
                    entity_data = await self._fetch_entity_details(record["entity_id"])
                    
                    results.append(UnifiedSearchResult(
                        id=record["entity_id"],
                        entity_id=record["entity_id"],
                        name=record["name"],
                        entity_type=record["labels"][0] if record["labels"] else "Unknown",
                        organization_id=entity_data.get("organization_id") if entity_data else None,
                        total_score=0.8,  # High score for direct dependencies
                        graph_score=0.8,
                        sources=["graph", "dependency"],
                        relationships=[{
                            "type": record["relationship_type"],
                            "direction": "depends_on"
                        }],
                        payload=entity_data or {}
                    ))
                
                return results
                
        except Exception as e:
            logger.error(f"Dependency search failed: {e}")
            return []
    
    async def _keyword_only_search(
        self,
        query: str,
        organization_id: Optional[str],
        entity_type: Optional[str],
        limit: int
    ) -> list[UnifiedSearchResult]:
        """Perform keyword-only search."""
        keyword_results = await self._get_keyword_results(
            query, organization_id, entity_type, limit
        )
        
        results = []
        for entity_id, score, data in keyword_results:
            results.append(UnifiedSearchResult(
                id=entity_id,
                entity_id=entity_id,
                name=data.get("name", ""),
                entity_type=data.get("entity_type", ""),
                organization_id=data.get("organization_id"),
                total_score=score,
                keyword_score=score,
                sources=["keyword"],
                payload=data
            ))
        
        return results
    
    async def _semantic_only_search(
        self,
        query: str,
        organization_id: Optional[str],
        entity_type: Optional[str],
        limit: int
    ) -> list[UnifiedSearchResult]:
        """Perform semantic-only search."""
        semantic_results = await self._get_semantic_results(
            query, organization_id, entity_type, limit
        )
        
        results = []
        for entity_id, score, data in semantic_results:
            results.append(UnifiedSearchResult(
                id=entity_id,
                entity_id=entity_id,
                name=data.get("name", ""),
                entity_type=data.get("entity_type", ""),
                organization_id=data.get("organization_id"),
                total_score=score,
                semantic_score=score,
                sources=["semantic"],
                payload=data
            ))
        
        return results
    
    async def _graph_only_search(
        self,
        query: str,
        organization_id: Optional[str],
        entity_type: Optional[str],
        limit: int
    ) -> list[UnifiedSearchResult]:
        """Perform graph-only search."""
        graph_results = await self._get_graph_results(
            query, organization_id, limit
        )
        
        results = []
        for entity_id, score, relationships in graph_results:
            entity_data = await self._fetch_entity_details(entity_id)
            if entity_data:
                results.append(UnifiedSearchResult(
                    id=entity_id,
                    entity_id=entity_id,
                    name=entity_data.get("name", ""),
                    entity_type=entity_data.get("entity_type", ""),
                    organization_id=entity_data.get("organization_id"),
                    total_score=score,
                    graph_score=score,
                    sources=["graph"],
                    relationships=relationships,
                    payload=entity_data
                ))
        
        return results
    
    async def _generate_embedding(self, text: str) -> Optional[list[float]]:
        """Generate embedding using Ollama."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{settings.ollama_url}/api/embeddings",
                    json={
                        "model": "nomic-embed-text",
                        "prompt": text
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["embedding"]
                    else:
                        logger.error(f"Ollama embedding failed: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    async def _fetch_entity_details(self, entity_id: str) -> Optional[dict]:
        """Fetch entity details from PostgreSQL."""
        try:
            async with db_manager.get_session() as session:
                uow = UnitOfWork(session)
                
                # Try to fetch by itglue_id
                entities = await uow.itglue.search(
                    query=entity_id,
                    limit=1
                )
                
                if entities:
                    entity = entities[0]
                    return {
                        "entity_id": str(entity.id),
                        "itglue_id": entity.itglue_id,
                        "name": entity.name,
                        "entity_type": entity.entity_type,
                        "organization_id": entity.organization_id,
                        "attributes": entity.attributes
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to fetch entity details: {e}")
            return None
    
    async def close(self):
        """Close all database connections."""
        try:
            if self.neo4j_driver:
                await self.neo4j_driver.close()
            
            if self.graph_traversal:
                await self.graph_traversal.disconnect()
            
            await db_manager.close()
            
            self._initialized = False
            logger.info("UnifiedHybridSearch connections closed")
            
        except Exception as e:
            logger.error(f"Error closing connections: {e}")


# Export main classes
__all__ = [
    'UnifiedHybridSearch',
    'UnifiedSearchResult',
    'SearchMode'
]