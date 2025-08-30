"""Embedding lifecycle management."""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import uuid

from src.data import db_manager, UnitOfWork
from src.data.models import ITGlueEntity, EmbeddingQueue
from .generator import EmbeddingGenerator, ChunkProcessor

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manages embedding generation and storage."""
    
    def __init__(
        self,
        generator: Optional[EmbeddingGenerator] = None,
        chunk_processor: Optional[ChunkProcessor] = None,
        batch_size: int = 50
    ):
        """Initialize embedding manager.
        
        Args:
            generator: Embedding generator
            chunk_processor: Text chunk processor
            batch_size: Batch size for processing
        """
        self.generator = generator or EmbeddingGenerator()
        self.chunk_processor = chunk_processor or ChunkProcessor()
        self.batch_size = batch_size
        
    async def process_queue(self, limit: int = 100) -> Dict[str, Any]:
        """Process pending items in embedding queue.
        
        Args:
            limit: Maximum items to process
            
        Returns:
            Processing statistics
        """
        logger.info(f"Processing embedding queue (limit: {limit})")
        
        stats = {
            "started_at": datetime.utcnow(),
            "processed": 0,
            "failed": 0,
            "skipped": 0
        }
        
        async with db_manager.get_session() as session:
            uow = UnitOfWork(session)
            
            # Get pending items
            pending = await uow.embedding_queue.get_pending(limit)
            
            if not pending:
                logger.info("No pending embeddings in queue")
                return stats
                
            logger.info(f"Found {len(pending)} pending embeddings")
            
            # Process in batches
            for i in range(0, len(pending), self.batch_size):
                batch = pending[i:i + self.batch_size]
                
                # Get entities for batch
                entity_ids = [item.entity_id for item in batch]
                entities = await uow.itglue.get_by_ids(entity_ids)
                
                if not entities:
                    logger.warning(f"No entities found for batch {i // self.batch_size + 1}")
                    stats["skipped"] += len(batch)
                    continue
                    
                # Generate embeddings
                try:
                    embeddings = await self._generate_entity_embeddings(entities)
                    
                    # Store embeddings (would go to Qdrant)
                    for entity, embedding_data in zip(entities, embeddings):
                        entity.embedding_id = embedding_data["id"]
                        
                    await uow.commit()
                    
                    # Mark items as processed
                    for item in batch:
                        await uow.embedding_queue.mark_processed(str(item.id))
                        
                    await uow.commit()
                    
                    stats["processed"] += len(batch)
                    logger.debug(f"Processed batch {i // self.batch_size + 1}")
                    
                except Exception as e:
                    logger.error(f"Failed to process batch: {e}")
                    
                    # Mark items as failed
                    for item in batch:
                        await uow.embedding_queue.mark_processed(
                            str(item.id),
                            error_message=str(e)
                        )
                        
                    await uow.commit()
                    stats["failed"] += len(batch)
                    
        stats["completed_at"] = datetime.utcnow()
        stats["duration_seconds"] = (
            stats["completed_at"] - stats["started_at"]
        ).total_seconds()
        
        logger.info(
            f"Embedding queue processing completed: "
            f"{stats['processed']} processed, "
            f"{stats['failed']} failed, "
            f"{stats['skipped']} skipped"
        )
        
        return stats
        
    async def _generate_entity_embeddings(
        self,
        entities: List[ITGlueEntity]
    ) -> List[Dict[str, Any]]:
        """Generate embeddings for entities.
        
        Args:
            entities: List of entities
            
        Returns:
            List of embedding data with IDs
        """
        embeddings_data = []
        
        for entity in entities:
            # Prepare text for embedding
            text = self._prepare_entity_text(entity)
            
            # Chunk text if needed
            chunks = self.chunk_processor.chunk_text(text)
            
            if not chunks:
                logger.warning(f"No text to embed for entity {entity.id}")
                embeddings_data.append({
                    "id": str(uuid.uuid4()),
                    "embeddings": [],
                    "chunks": []
                })
                continue
                
            # Generate embeddings for chunks
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = await self.generator.generate_embeddings(chunk_texts)
            
            # Combine chunks and embeddings
            embedding_id = str(uuid.uuid4())
            
            embeddings_data.append({
                "id": embedding_id,
                "entity_id": str(entity.id),
                "embeddings": embeddings,
                "chunks": chunks,
                "metadata": {
                    "entity_type": entity.entity_type,
                    "organization_id": entity.organization_id,
                    "name": entity.name
                }
            })
            
        return embeddings_data
        
    def _prepare_entity_text(self, entity: ITGlueEntity) -> str:
        """Prepare entity text for embedding.
        
        Args:
            entity: Entity to prepare
            
        Returns:
            Combined text for embedding
        """
        text_parts = []
        
        # Add name
        if entity.name:
            text_parts.append(f"Name: {entity.name}")
            
        # Add entity type
        text_parts.append(f"Type: {entity.entity_type}")
        
        # Add attributes
        if entity.attributes:
            for key, value in entity.attributes.items():
                if value and key not in ["id", "created_at", "updated_at"]:
                    if isinstance(value, str):
                        text_parts.append(f"{key}: {value}")
                        
        # Add search text if available
        if entity.search_text:
            text_parts.append(entity.search_text)
            
        return " ".join(text_parts)
        
    async def regenerate_entity_embeddings(
        self,
        entity_id: str
    ) -> bool:
        """Regenerate embeddings for a specific entity.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Success status
        """
        logger.info(f"Regenerating embeddings for entity {entity_id}")
        
        async with db_manager.get_session() as session:
            uow = UnitOfWork(session)
            
            # Get entity
            entity = await uow.itglue.get_by_id(entity_id)
            
            if not entity:
                logger.error(f"Entity {entity_id} not found")
                return False
                
            try:
                # Generate new embeddings
                embeddings_data = await self._generate_entity_embeddings([entity])
                
                if embeddings_data:
                    # Update entity with new embedding ID
                    entity.embedding_id = embeddings_data[0]["id"]
                    await uow.commit()
                    
                    logger.info(f"Regenerated embeddings for entity {entity_id}")
                    return True
                    
            except Exception as e:
                logger.error(f"Failed to regenerate embeddings: {e}")
                
        return False
        
    async def bulk_regenerate(
        self,
        entity_type: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Bulk regenerate embeddings.
        
        Args:
            entity_type: Filter by entity type
            organization_id: Filter by organization
            
        Returns:
            Regeneration statistics
        """
        logger.info("Starting bulk embedding regeneration")
        
        stats = {
            "started_at": datetime.utcnow(),
            "queued": 0,
            "filters": {
                "entity_type": entity_type,
                "organization_id": organization_id
            }
        }
        
        async with db_manager.get_session() as session:
            uow = UnitOfWork(session)
            
            # Get entities to regenerate
            if organization_id:
                entities = await uow.itglue.get_by_organization(
                    organization_id,
                    entity_type
                )
            elif entity_type:
                entities = await uow.itglue.search(
                    query="",
                    entity_type=entity_type,
                    limit=10000
                )
            else:
                entities = await uow.itglue.get_all(limit=10000)
                
            # Add to queue
            for entity in entities:
                await uow.embedding_queue.add_to_queue(
                    entity_id=str(entity.id),
                    entity_type=entity.entity_type
                )
                stats["queued"] += 1
                
            await uow.commit()
            
        stats["completed_at"] = datetime.utcnow()
        stats["duration_seconds"] = (
            stats["completed_at"] - stats["started_at"]
        ).total_seconds()
        
        logger.info(f"Queued {stats['queued']} entities for embedding regeneration")
        
        return stats
        
    async def continuous_processing(
        self,
        interval_seconds: int = 60,
        batch_limit: int = 100,
        stop_event: Optional[asyncio.Event] = None
    ):
        """Continuously process embedding queue.
        
        Args:
            interval_seconds: Seconds between processing runs
            batch_limit: Max items per run
            stop_event: Event to signal stop
        """
        logger.info(
            f"Starting continuous embedding processing "
            f"(interval: {interval_seconds}s, batch: {batch_limit})"
        )
        
        if not stop_event:
            stop_event = asyncio.Event()
            
        while not stop_event.is_set():
            try:
                stats = await self.process_queue(batch_limit)
                
                if stats["processed"] > 0:
                    logger.info(
                        f"Processed {stats['processed']} embeddings"
                    )
                    
            except Exception as e:
                logger.error(f"Embedding processing error: {e}")
                
            # Wait for next iteration
            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=interval_seconds
                )
            except asyncio.TimeoutError:
                continue
                
        logger.info("Continuous embedding processing stopped")