"""Hybrid search combining semantic and keyword search."""

import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from src.data import db_manager, UnitOfWork
from .semantic import SemanticSearch, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class HybridSearchResult:
    """Combined search result from multiple sources."""
    
    id: str
    entity_id: str
    score: float
    semantic_score: Optional[float] = None
    keyword_score: Optional[float] = None
    source: str = "hybrid"
    payload: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "score": self.score,
            "semantic_score": self.semantic_score,
            "keyword_score": self.keyword_score,
            "source": self.source,
            "payload": self.payload
        }


class HybridSearch:
    """Combines semantic and keyword search for better results."""
    
    def __init__(
        self,
        semantic_search: Optional[SemanticSearch] = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ):
        """Initialize hybrid search.
        
        Args:
            semantic_search: Semantic search instance
            semantic_weight: Weight for semantic scores
            keyword_weight: Weight for keyword scores
        """
        self.semantic_search = semantic_search or SemanticSearch()
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
        
        # Ensure weights sum to 1
        total_weight = semantic_weight + keyword_weight
        if total_weight != 1.0:
            self.semantic_weight = semantic_weight / total_weight
            self.keyword_weight = keyword_weight / total_weight
            
    async def search(
        self,
        query: str,
        company_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 10,
        min_score: float = 0.5
    ) -> List[HybridSearchResult]:
        """Perform hybrid search.
        
        Args:
            query: Search query
            company_id: Filter by company
            entity_type: Filter by entity type
            limit: Maximum results
            min_score: Minimum combined score
            
        Returns:
            List of hybrid search results
        """
        logger.debug(f"Hybrid search for: {query}")
        
        # Perform semantic search
        semantic_results = await self._semantic_search(
            query,
            company_id,
            entity_type,
            limit * 2  # Get more for re-ranking
        )
        
        # Perform keyword search
        keyword_results = await self._keyword_search(
            query,
            company_id,
            entity_type,
            limit * 2
        )
        
        # Combine and re-rank results
        combined_results = self._combine_results(
            semantic_results,
            keyword_results
        )
        
        # Filter by minimum score
        filtered = [
            r for r in combined_results
            if r.score >= min_score
        ]
        
        # Sort by combined score
        filtered.sort(key=lambda x: x.score, reverse=True)
        
        # Limit results
        results = filtered[:limit]
        
        logger.debug(f"Hybrid search found {len(results)} results")
        
        return results
        
    async def _semantic_search(
        self,
        query: str,
        company_id: Optional[str],
        entity_type: Optional[str],
        limit: int
    ) -> List[Tuple[str, float, Dict]]:
        """Perform semantic search.
        
        Returns:
            List of (entity_id, score, payload) tuples
        """
        try:
            results = await self.semantic_search.search(
                query=query,
                company_id=company_id,
                entity_type=entity_type,
                limit=limit,
                score_threshold=0.5
            )
            
            return [
                (
                    r.payload.get("entity_id"),
                    r.score,
                    r.payload
                )
                for r in results
            ]
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
            
    async def _keyword_search(
        self,
        query: str,
        company_id: Optional[str],
        entity_type: Optional[str],
        limit: int
    ) -> List[Tuple[str, float, Dict]]:
        """Perform keyword search.
        
        Returns:
            List of (entity_id, score, payload) tuples
        """
        try:
            async with db_manager.get_session() as session:
                uow = UnitOfWork(session)
                
                # Search in database
                results = await uow.itglue.search(
                    query=query,
                    organization_id=company_id,
                    entity_type=entity_type,
                    limit=limit
                )
                
                # Calculate simple keyword scores
                keyword_results = []
                query_lower = query.lower()
                query_terms = set(query_lower.split())
                
                for entity in results:
                    # Calculate score based on term overlap
                    text = (entity.search_text or "").lower()
                    text_terms = set(text.split())
                    
                    overlap = len(query_terms & text_terms)
                    score = overlap / len(query_terms) if query_terms else 0
                    
                    # Boost if exact match in name
                    if query_lower in (entity.name or "").lower():
                        score = min(1.0, score + 0.5)
                        
                    keyword_results.append(
                        (
                            str(entity.id),
                            score,
                            {
                                "entity_id": str(entity.id),
                                "itglue_id": entity.itglue_id,
                                "name": entity.name,
                                "entity_type": entity.entity_type,
                                "organization_id": entity.organization_id
                            }
                        )
                    )
                    
                return keyword_results
                
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
            
    def _combine_results(
        self,
        semantic_results: List[Tuple[str, float, Dict]],
        keyword_results: List[Tuple[str, float, Dict]]
    ) -> List[HybridSearchResult]:
        """Combine semantic and keyword search results.
        
        Args:
            semantic_results: Semantic search results
            keyword_results: Keyword search results
            
        Returns:
            Combined and re-ranked results
        """
        combined = {}
        
        # Add semantic results
        for entity_id, score, payload in semantic_results:
            if entity_id:
                combined[entity_id] = HybridSearchResult(
                    id=entity_id,
                    entity_id=entity_id,
                    score=score * self.semantic_weight,
                    semantic_score=score,
                    payload=payload
                )
                
        # Add/update with keyword results
        for entity_id, score, payload in keyword_results:
            if entity_id:
                if entity_id in combined:
                    # Update existing result
                    result = combined[entity_id]
                    result.keyword_score = score
                    result.score += score * self.keyword_weight
                    
                    # Merge payload
                    if payload:
                        result.payload.update(payload)
                else:
                    # Add new result
                    combined[entity_id] = HybridSearchResult(
                        id=entity_id,
                        entity_id=entity_id,
                        score=score * self.keyword_weight,
                        keyword_score=score,
                        payload=payload
                    )
                    
        return list(combined.values())
        
    async def search_with_context(
        self,
        query: str,
        context: Dict[str, Any],
        limit: int = 10
    ) -> List[HybridSearchResult]:
        """Search with additional context.
        
        Args:
            query: Search query
            context: Additional context (company, recent queries, etc.)
            limit: Maximum results
            
        Returns:
            Context-aware search results
        """
        # Extract context parameters
        company_id = context.get("company_id")
        entity_type = context.get("entity_type")
        boost_recent = context.get("boost_recent", False)
        
        # Perform base search
        results = await self.search(
            query=query,
            company_id=company_id,
            entity_type=entity_type,
            limit=limit * 2  # Get more for re-ranking
        )
        
        # Apply context-based re-ranking
        if boost_recent and "recent_entities" in context:
            recent_ids = set(context["recent_entities"])
            
            for result in results:
                if result.entity_id in recent_ids:
                    # Boost recently accessed entities
                    result.score *= 1.2
                    
        # Re-sort and limit
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:limit]