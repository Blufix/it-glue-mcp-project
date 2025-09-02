"""Semantic search with Qdrant vector database."""

import logging
import uuid
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from src.config.settings import settings
from src.embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


class SearchResult:
    """Semantic search result."""

    def __init__(
        self,
        id: str,
        score: float,
        payload: dict[str, Any],
        source_id: Optional[str] = None
    ):
        self.id = id
        self.score = score
        self.payload = payload
        self.source_id = source_id or payload.get("itglue_id")


class SemanticSearch:
    """Handles semantic search using Qdrant."""

    def __init__(
        self,
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
        collection_name: str = "itglue_entities",
        embedding_generator: Optional[EmbeddingGenerator] = None
    ):
        """Initialize semantic search.

        Args:
            qdrant_url: Qdrant server URL
            qdrant_api_key: Qdrant API key (optional)
            collection_name: Name of the collection
            embedding_generator: Embedding generator
        """
        self.qdrant_url = qdrant_url or settings.qdrant_url or "http://localhost:6333"
        self.qdrant_api_key = qdrant_api_key or settings.qdrant_api_key
        self.collection_name = collection_name

        # Initialize Qdrant client
        self.client = QdrantClient(
            url=self.qdrant_url,
            api_key=self.qdrant_api_key
        )

        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.dimension = self.embedding_generator.get_dimension()

    async def initialize_collection(self, recreate: bool = False):
        """Initialize Qdrant collection.

        Args:
            recreate: Whether to recreate the collection
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if exists and recreate:
                logger.info(f"Deleting existing collection: {self.collection_name}")
                self.client.delete_collection(self.collection_name)
                exists = False

            if not exists:
                logger.info(f"Creating collection: {self.collection_name}")

                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=Distance.COSINE
                    )
                )

                logger.info(f"Collection created with dimension {self.dimension}")

            else:
                logger.info(f"Collection {self.collection_name} already exists")

        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise

    async def index_entity(
        self,
        entity_id: str,
        text: str,
        metadata: dict[str, Any]
    ) -> str:
        """Index a single entity.

        Args:
            entity_id: Entity ID
            text: Text to embed and index
            metadata: Entity metadata

        Returns:
            Point ID in Qdrant
        """
        try:
            # Generate embedding
            embeddings = await self.embedding_generator.generate_embeddings([text])

            if not embeddings:
                raise ValueError("Failed to generate embedding")

            # Create point ID
            point_id = str(uuid.uuid4())

            # Create point
            point = PointStruct(
                id=point_id,
                vector=embeddings[0],
                payload={
                    "entity_id": entity_id,
                    "text": text[:1000],  # Store first 1000 chars
                    **metadata
                }
            )

            # Upsert to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )

            logger.debug(f"Indexed entity {entity_id} with point {point_id}")

            return point_id

        except Exception as e:
            logger.error(f"Failed to index entity {entity_id}: {e}")
            raise

    async def index_batch(
        self,
        entities: list[dict[str, Any]]
    ) -> list[str]:
        """Index multiple entities.

        Args:
            entities: List of entities with 'id', 'text', and 'metadata'

        Returns:
            List of point IDs
        """
        if not entities:
            return []

        try:
            # Extract texts for embedding
            texts = [e["text"] for e in entities]

            # Generate embeddings
            embeddings = await self.embedding_generator.generate_batch(
                texts,
                batch_size=50
            )

            # Create points
            points = []
            point_ids = []

            for entity, embedding in zip(entities, embeddings, strict=False):
                point_id = str(uuid.uuid4())
                point_ids.append(point_id)

                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "entity_id": entity["id"],
                            "text": entity["text"][:1000],
                            **entity.get("metadata", {})
                        }
                    )
                )

            # Batch upsert to Qdrant
            for i in range(0, len(points), 100):
                batch = points[i:i + 100]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )

            logger.info(f"Indexed {len(points)} entities")

            return point_ids

        except Exception as e:
            logger.error(f"Failed to index batch: {e}")
            raise

    async def search(
        self,
        query: str,
        company_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 10,
        score_threshold: float = 0.7
    ) -> list[SearchResult]:
        """Search for similar entities.

        Args:
            query: Search query
            company_id: Filter by company/organization
            entity_type: Filter by entity type
            limit: Maximum results
            score_threshold: Minimum similarity score

        Returns:
            List of search results
        """
        try:
            # Generate query embedding
            embeddings = await self.embedding_generator.generate_embeddings([query])

            if not embeddings:
                logger.warning("Failed to generate query embedding")
                return []

            query_vector = embeddings[0]

            # Build filter conditions
            filter_conditions = []

            if company_id:
                filter_conditions.append(
                    FieldCondition(
                        key="organization_id",
                        match=MatchValue(value=company_id)
                    )
                )

            if entity_type:
                filter_conditions.append(
                    FieldCondition(
                        key="entity_type",
                        match=MatchValue(value=entity_type)
                    )
                )

            # Create filter if conditions exist
            search_filter = None
            if filter_conditions:
                search_filter = Filter(must=filter_conditions)

            # Perform search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold
            )

            # Convert to SearchResult objects
            search_results = []
            for hit in results:
                search_results.append(
                    SearchResult(
                        id=hit.id,
                        score=hit.score,
                        payload=hit.payload,
                        source_id=hit.payload.get("itglue_id")
                    )
                )

            logger.debug(f"Found {len(search_results)} results for query: {query}")

            return search_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    async def search_by_vector(
        self,
        vector: list[float],
        filters: Optional[dict[str, Any]] = None,
        limit: int = 10,
        score_threshold: float = 0.7
    ) -> list[SearchResult]:
        """Search using a pre-computed vector.

        Args:
            vector: Query vector
            filters: Optional filters
            limit: Maximum results
            score_threshold: Minimum similarity score

        Returns:
            List of search results
        """
        try:
            # Build filter
            search_filter = None
            if filters:
                filter_conditions = [
                    FieldCondition(key=k, match=MatchValue(value=v))
                    for k, v in filters.items()
                ]
                search_filter = Filter(must=filter_conditions)

            # Search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold
            )

            # Convert results
            return [
                SearchResult(
                    id=hit.id,
                    score=hit.score,
                    payload=hit.payload,
                    source_id=hit.payload.get("itglue_id")
                )
                for hit in results
            ]

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise

    async def delete_entity(self, entity_id: str) -> bool:
        """Delete entity from index.

        Args:
            entity_id: Entity ID to delete

        Returns:
            Success status
        """
        try:
            # Find points with this entity ID
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="entity_id",
                            match=MatchValue(value=entity_id)
                        )
                    ]
                ),
                limit=100
            )

            point_ids = [point.id for point in results[0]]

            if point_ids:
                # Delete points
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids
                )

                logger.debug(f"Deleted {len(point_ids)} points for entity {entity_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete entity {entity_id}: {e}")
            raise

    async def update_entity(
        self,
        entity_id: str,
        text: str,
        metadata: dict[str, Any]
    ) -> bool:
        """Update entity in index.

        Args:
            entity_id: Entity ID
            text: New text
            metadata: New metadata

        Returns:
            Success status
        """
        try:
            # Delete old entries
            await self.delete_entity(entity_id)

            # Index new version
            await self.index_entity(entity_id, text, metadata)

            logger.debug(f"Updated entity {entity_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update entity {entity_id}: {e}")
            raise

    async def get_collection_stats(self) -> dict[str, Any]:
        """Get collection statistics.

        Returns:
            Collection statistics
        """
        try:
            info = self.client.get_collection(self.collection_name)

            return {
                "name": info.config.params.vectors.size,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "status": info.status
            }

        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            raise
