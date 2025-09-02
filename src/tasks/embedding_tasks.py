"""Celery tasks for embedding generation and management."""

import asyncio
from datetime import datetime
from typing import Any, Optional

from celery import Task, current_task
from celery.utils.log import get_task_logger

from src.celery_app import app
from src.config.settings import settings
from src.embeddings.generator import EmbeddingGenerator
from src.embeddings.manager import EmbeddingManager

logger = get_task_logger(__name__)


class EmbeddingTask(Task):
    """Base class for embedding tasks."""

    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 30}


@app.task(base=EmbeddingTask, bind=True, name='src.tasks.embedding_tasks.update_embeddings')
def update_embeddings(self, entity_ids: Optional[list[str]] = None) -> dict[str, Any]:
    """
    Update embeddings for entities.

    Args:
        entity_ids: Optional list of specific entity IDs to update

    Returns:
        Dictionary with update results
    """
    logger.info(f"Updating embeddings for {len(entity_ids) if entity_ids else 'all'} entities")

    try:
        current_task.update_state(
            state='PROGRESS',
            meta={'status': 'Initializing embedding generator'}
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            generator = EmbeddingGenerator()
            manager = loop.run_until_complete(_initialize_embedding_manager())

            if entity_ids:
                # Update specific entities
                results = loop.run_until_complete(
                    manager.update_entity_embeddings(entity_ids)
                )
            else:
                # Update all entities without embeddings
                results = loop.run_until_complete(
                    manager.update_all_embeddings()
                )

            logger.info(f"Successfully updated {results['updated_count']} embeddings")

            return {
                'status': 'success',
                'updated_count': results['updated_count'],
                'failed_count': results.get('failed_count', 0),
                'updated_at': datetime.utcnow().isoformat()
            }

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Embedding update failed: {str(e)}")
        raise


@app.task(base=EmbeddingTask, bind=True, name='src.tasks.embedding_tasks.generate_entity_embedding')
def generate_entity_embedding(self, entity_id: str, entity_data: dict[str, Any]) -> dict[str, Any]:
    """
    Generate embedding for a single entity.

    Args:
        entity_id: Entity ID
        entity_data: Entity data dictionary

    Returns:
        Dictionary with embedding result
    """
    logger.info(f"Generating embedding for entity: {entity_id}")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            generator = EmbeddingGenerator()

            # Generate text representation
            text = loop.run_until_complete(
                generator.create_text_representation(entity_data)
            )

            # Generate embedding
            embedding = loop.run_until_complete(
                generator.generate_embedding(text)
            )

            # Store in Qdrant
            manager = loop.run_until_complete(_initialize_embedding_manager())
            result = loop.run_until_complete(
                manager.store_embedding(entity_id, embedding, entity_data)
            )

            return {
                'status': 'success',
                'entity_id': entity_id,
                'embedding_dim': len(embedding),
                'stored': result
            }

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Embedding generation failed for {entity_id}: {str(e)}")
        raise


@app.task(base=EmbeddingTask, bind=True, name='src.tasks.embedding_tasks.rebuild_vector_index')
def rebuild_vector_index(self, collection_name: str = 'itglue_entities') -> dict[str, Any]:
    """
    Rebuild the vector search index.

    Args:
        collection_name: Name of the Qdrant collection

    Returns:
        Dictionary with rebuild results
    """
    logger.info(f"Rebuilding vector index for collection: {collection_name}")

    try:
        current_task.update_state(
            state='PROGRESS',
            meta={'status': 'Rebuilding vector index'}
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            manager = loop.run_until_complete(_initialize_embedding_manager())

            # Rebuild index
            result = loop.run_until_complete(
                manager.rebuild_index(collection_name)
            )

            logger.info("Vector index rebuilt successfully")

            return {
                'status': 'success',
                'collection': collection_name,
                'vector_count': result['vector_count'],
                'index_time': result['index_time'],
                'rebuilt_at': datetime.utcnow().isoformat()
            }

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Vector index rebuild failed: {str(e)}")
        raise


@app.task(base=EmbeddingTask, bind=True, name='src.tasks.embedding_tasks.cleanup_orphaned_embeddings')
def cleanup_orphaned_embeddings(self) -> dict[str, Any]:
    """
    Clean up embeddings for deleted entities.

    Returns:
        Dictionary with cleanup results
    """
    logger.info("Cleaning up orphaned embeddings")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            manager = loop.run_until_complete(_initialize_embedding_manager())

            # Find and remove orphaned embeddings
            result = loop.run_until_complete(
                manager.cleanup_orphaned_embeddings()
            )

            logger.info(f"Cleaned up {result['removed_count']} orphaned embeddings")

            return {
                'status': 'success',
                'removed_count': result['removed_count'],
                'cleaned_at': datetime.utcnow().isoformat()
            }

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Embedding cleanup failed: {str(e)}")
        raise


async def _initialize_embedding_manager() -> EmbeddingManager:
    """Initialize embedding manager with dependencies."""
    from qdrant_client import QdrantClient
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from src.data.repositories import ITGlueRepository

    # Create database session
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Initialize Qdrant client
    qdrant_client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT
    )

    async with async_session() as session:
        repository = ITGlueRepository(session)

        return EmbeddingManager(
            qdrant_client=qdrant_client,
            repository=repository,
            embedding_generator=EmbeddingGenerator()
        )
