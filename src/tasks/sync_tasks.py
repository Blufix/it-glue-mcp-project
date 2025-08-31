"""Celery tasks for IT Glue data synchronization."""

from celery import Task, current_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import asyncio

from src.celery_app import app
from src.services.itglue.client import ITGlueClient
from src.sync.orchestrator import SyncOrchestrator
from src.sync.incremental import IncrementalSync
from src.monitoring.metrics import (
    track_sync_metrics,
    itglue_entities_total,
    itglue_sync_failures_total
)
from src.config.settings import settings

logger = get_task_logger(__name__)


class SyncTask(Task):
    """Base class for sync tasks with error handling."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Task {task_id} failed: {exc}")
        itglue_sync_failures_total.labels(
            sync_type=self.name.split('.')[-1],
            error_type=type(exc).__name__
        ).inc()
        
        # Send notification about sync failure
        app.send_task(
            'src.tasks.notification_tasks.send_sync_failure_notification',
            kwargs={
                'task_name': self.name,
                'error': str(exc),
                'task_id': task_id
            }
        )


@app.task(base=SyncTask, bind=True, name='src.tasks.sync_tasks.full_sync')
def full_sync(self, organization_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Perform a full synchronization of IT Glue data.
    
    Args:
        organization_id: Optional specific organization to sync
        
    Returns:
        Dictionary with sync results
    """
    start_time = datetime.utcnow()
    logger.info(f"Starting full sync for organization: {organization_id or 'all'}")
    
    try:
        # Update task state
        current_task.update_state(
            state='PROGRESS',
            meta={'status': 'Initializing sync orchestrator'}
        )
        
        # Run async sync in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            orchestrator = loop.run_until_complete(
                _initialize_orchestrator()
            )
            
            # Perform full sync
            current_task.update_state(
                state='PROGRESS',
                meta={'status': 'Syncing organizations'}
            )
            
            result = loop.run_until_complete(
                orchestrator.sync_all(organization_id=organization_id)
            )
            
            # Update metrics
            duration = (datetime.utcnow() - start_time).total_seconds()
            track_sync_metrics('full', 'success', duration)
            
            # Update entity counts
            for entity_type, count in result.get('entity_counts', {}).items():
                itglue_entities_total.labels(entity_type=entity_type).set(count)
            
            logger.info(f"Full sync completed successfully in {duration:.2f} seconds")
            
            return {
                'status': 'success',
                'duration': duration,
                'synced_at': datetime.utcnow().isoformat(),
                'results': result
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Full sync failed: {str(e)}")
        track_sync_metrics('full', 'failure')
        raise


@app.task(base=SyncTask, bind=True, name='src.tasks.sync_tasks.incremental_sync')
def incremental_sync(self, since_minutes: int = 30) -> Dict[str, Any]:
    """
    Perform incremental synchronization of recently updated data.
    
    Args:
        since_minutes: Sync data updated in the last N minutes
        
    Returns:
        Dictionary with sync results
    """
    start_time = datetime.utcnow()
    since_timestamp = datetime.utcnow() - timedelta(minutes=since_minutes)
    
    logger.info(f"Starting incremental sync for updates since {since_timestamp}")
    
    try:
        current_task.update_state(
            state='PROGRESS',
            meta={'status': 'Initializing incremental sync'}
        )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            sync = loop.run_until_complete(
                _initialize_incremental_sync()
            )
            
            # Perform incremental sync
            current_task.update_state(
                state='PROGRESS',
                meta={'status': 'Syncing recent updates'}
            )
            
            result = loop.run_until_complete(
                sync.sync_updates(since=since_timestamp)
            )
            
            # Update metrics
            duration = (datetime.utcnow() - start_time).total_seconds()
            track_sync_metrics('incremental', 'success', duration)
            
            logger.info(f"Incremental sync completed in {duration:.2f} seconds")
            
            return {
                'status': 'success',
                'duration': duration,
                'synced_at': datetime.utcnow().isoformat(),
                'since': since_timestamp.isoformat(),
                'results': result
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Incremental sync failed: {str(e)}")
        track_sync_metrics('incremental', 'failure')
        raise


@app.task(base=SyncTask, bind=True, name='src.tasks.sync_tasks.sync_organization')
def sync_organization(self, organization_id: str) -> Dict[str, Any]:
    """
    Sync a specific organization.
    
    Args:
        organization_id: IT Glue organization ID
        
    Returns:
        Dictionary with sync results
    """
    logger.info(f"Syncing organization: {organization_id}")
    
    try:
        current_task.update_state(
            state='PROGRESS',
            meta={'status': f'Syncing organization {organization_id}'}
        )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            orchestrator = loop.run_until_complete(
                _initialize_orchestrator()
            )
            
            result = loop.run_until_complete(
                orchestrator.sync_organization(organization_id)
            )
            
            track_sync_metrics('organization', 'success')
            
            return {
                'status': 'success',
                'organization_id': organization_id,
                'synced_at': datetime.utcnow().isoformat(),
                'results': result
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Organization sync failed: {str(e)}")
        track_sync_metrics('organization', 'failure')
        raise


@app.task(base=SyncTask, bind=True, name='src.tasks.sync_tasks.sync_entity_type')
def sync_entity_type(
    self,
    entity_type: str,
    organization_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sync a specific entity type.
    
    Args:
        entity_type: Type of entity to sync (configurations, passwords, etc.)
        organization_id: Optional organization filter
        
    Returns:
        Dictionary with sync results
    """
    logger.info(f"Syncing entity type: {entity_type}")
    
    try:
        current_task.update_state(
            state='PROGRESS',
            meta={'status': f'Syncing {entity_type}'}
        )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            orchestrator = loop.run_until_complete(
                _initialize_orchestrator()
            )
            
            result = loop.run_until_complete(
                orchestrator.sync_entity_type(entity_type, organization_id)
            )
            
            track_sync_metrics(f'entity_{entity_type}', 'success')
            
            # Update entity count
            if 'count' in result:
                itglue_entities_total.labels(entity_type=entity_type).set(result['count'])
            
            return {
                'status': 'success',
                'entity_type': entity_type,
                'synced_at': datetime.utcnow().isoformat(),
                'results': result
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Entity type sync failed: {str(e)}")
        track_sync_metrics(f'entity_{entity_type}', 'failure')
        raise


@app.task(bind=True, name='src.tasks.sync_tasks.validate_sync')
def validate_sync(self) -> Dict[str, Any]:
    """
    Validate sync data integrity.
    
    Returns:
        Dictionary with validation results
    """
    logger.info("Starting sync validation")
    
    try:
        current_task.update_state(
            state='PROGRESS',
            meta={'status': 'Validating sync data'}
        )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            orchestrator = loop.run_until_complete(
                _initialize_orchestrator()
            )
            
            # Validate data integrity
            validation_results = loop.run_until_complete(
                orchestrator.validate_data()
            )
            
            # Check for issues
            has_issues = any(
                not result['valid']
                for result in validation_results.values()
            )
            
            if has_issues:
                logger.warning("Sync validation found issues")
                # Send notification about validation issues
                app.send_task(
                    'src.tasks.notification_tasks.send_validation_issues_notification',
                    kwargs={'issues': validation_results}
                )
            
            return {
                'status': 'completed',
                'has_issues': has_issues,
                'validated_at': datetime.utcnow().isoformat(),
                'results': validation_results
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Sync validation failed: {str(e)}")
        raise


async def _initialize_orchestrator() -> SyncOrchestrator:
    """Initialize sync orchestrator with dependencies."""
    from src.data.repositories import ITGlueRepository
    from src.embeddings.generator import EmbeddingGenerator
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    # Create database session
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Initialize components
        client = ITGlueClient(
            api_key=settings.ITGLUE_API_KEY,
            subdomain=settings.ITGLUE_SUBDOMAIN
        )
        
        repository = ITGlueRepository(session)
        embedding_generator = EmbeddingGenerator()
        
        return SyncOrchestrator(
            client=client,
            repository=repository,
            embedding_generator=embedding_generator
        )


async def _initialize_incremental_sync() -> IncrementalSync:
    """Initialize incremental sync with dependencies."""
    from src.data.repositories import ITGlueRepository
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    # Create database session
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Initialize components
        client = ITGlueClient(
            api_key=settings.ITGLUE_API_KEY,
            subdomain=settings.ITGLUE_SUBDOMAIN
        )
        
        repository = ITGlueRepository(session)
        
        return IncrementalSync(
            client=client,
            repository=repository
        )