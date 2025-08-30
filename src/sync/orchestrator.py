"""Sync orchestration for IT Glue data."""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from src.services.itglue.client import ITGlueClient
from src.data import db_manager, UnitOfWork
from src.data.models import ITGlueEntity
from .incremental import IncrementalSync

logger = logging.getLogger(__name__)


class SyncOrchestrator:
    """Orchestrates data synchronization from IT Glue."""
    
    def __init__(
        self,
        itglue_client: Optional[ITGlueClient] = None,
        batch_size: int = 100
    ):
        """Initialize sync orchestrator.
        
        Args:
            itglue_client: IT Glue API client
            batch_size: Number of entities to process in each batch
        """
        self.client = itglue_client or ITGlueClient()
        self.batch_size = batch_size
        self.incremental_sync = IncrementalSync(self.client, batch_size)
        
    async def sync_all(self, full_sync: bool = False) -> Dict[str, Any]:
        """Sync all entity types from IT Glue.
        
        Args:
            full_sync: If True, ignore last sync timestamps
            
        Returns:
            Sync statistics
        """
        logger.info(f"Starting {'full' if full_sync else 'incremental'} sync")
        
        stats = {
            "started_at": datetime.utcnow(),
            "entity_types": {},
            "total_synced": 0,
            "errors": []
        }
        
        entity_types = [
            "organizations",
            "configurations",
            "flexible_assets",
            "passwords",
            "documents",
            "contacts",
            "locations"
        ]
        
        async with self.client:
            for entity_type in entity_types:
                try:
                    result = await self._sync_entity_type(
                        entity_type,
                        full_sync=full_sync
                    )
                    stats["entity_types"][entity_type] = result
                    stats["total_synced"] += result.get("synced", 0)
                    
                except Exception as e:
                    logger.error(f"Failed to sync {entity_type}: {e}")
                    stats["errors"].append({
                        "entity_type": entity_type,
                        "error": str(e)
                    })
                    
        stats["completed_at"] = datetime.utcnow()
        stats["duration_seconds"] = (
            stats["completed_at"] - stats["started_at"]
        ).total_seconds()
        
        logger.info(
            f"Sync completed: {stats['total_synced']} entities synced in "
            f"{stats['duration_seconds']:.2f} seconds"
        )
        
        return stats
        
    async def _sync_entity_type(
        self,
        entity_type: str,
        full_sync: bool = False
    ) -> Dict[str, Any]:
        """Sync a specific entity type.
        
        Args:
            entity_type: Type of entity to sync
            full_sync: If True, ignore last sync timestamp
            
        Returns:
            Sync statistics for this entity type
        """
        logger.info(f"Syncing {entity_type}")
        
        async with db_manager.get_session() as session:
            uow = UnitOfWork(session)
            
            # Update sync status to started
            await uow.sync_status.update_sync_status(
                entity_type=entity_type,
                status="started"
            )
            
            try:
                # Get last sync timestamp if not full sync
                last_sync = None
                if not full_sync:
                    status = await uow.sync_status.get_by_entity_type(entity_type)
                    if status and status.last_sync_completed:
                        last_sync = status.last_sync_completed
                        
                # Fetch entities from IT Glue
                entities = await self._fetch_entities(entity_type, last_sync)
                
                # Process entities in batches
                synced_count = 0
                for i in range(0, len(entities), self.batch_size):
                    batch = entities[i:i + self.batch_size]
                    await self._process_batch(uow, entity_type, batch)
                    synced_count += len(batch)
                    
                    # Commit batch
                    await uow.commit()
                    
                    logger.debug(
                        f"Processed batch {i // self.batch_size + 1} for {entity_type}: "
                        f"{len(batch)} entities"
                    )
                    
                # Update sync status to completed
                await uow.sync_status.update_sync_status(
                    entity_type=entity_type,
                    status="completed",
                    records_synced=synced_count
                )
                
                await uow.commit()
                
                logger.info(f"Successfully synced {synced_count} {entity_type}")
                
                return {
                    "synced": synced_count,
                    "status": "completed"
                }
                
            except Exception as e:
                # Update sync status to failed
                await uow.sync_status.update_sync_status(
                    entity_type=entity_type,
                    status="failed",
                    error_message=str(e)
                )
                await uow.commit()
                
                logger.error(f"Failed to sync {entity_type}: {e}")
                raise
                
    async def _fetch_entities(
        self,
        entity_type: str,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch entities from IT Glue API.
        
        Args:
            entity_type: Type of entity to fetch
            since: Only fetch entities updated after this timestamp
            
        Returns:
            List of entity data from API
        """
        filters = {}
        if since:
            filters["updated_at"] = since.isoformat()
            
        if entity_type == "organizations":
            entities = await self.client.get_organizations(filters)
        elif entity_type == "configurations":
            entities = await self.client.get_configurations(filters=filters)
        elif entity_type == "flexible_assets":
            entities = await self.client.get_flexible_assets(filters=filters)
        elif entity_type == "passwords":
            entities = await self.client.get_passwords(filters=filters)
        elif entity_type == "documents":
            entities = await self.client.get_documents(filters=filters)
        elif entity_type == "contacts":
            entities = await self.client.get_contacts(filters=filters)
        elif entity_type == "locations":
            entities = await self.client.get_locations(filters=filters)
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")
            
        # Convert models to dicts
        return [entity.dict() for entity in entities]
        
    async def _process_batch(
        self,
        uow: UnitOfWork,
        entity_type: str,
        batch: List[Dict[str, Any]]
    ):
        """Process a batch of entities.
        
        Args:
            uow: Unit of work for database operations
            entity_type: Type of entities
            batch: Batch of entity data
        """
        for entity_data in batch:
            try:
                # Extract searchable text
                search_text = self._extract_search_text(entity_data)
                
                # Prepare entity for storage
                entity_dict = {
                    "itglue_id": entity_data["id"],
                    "entity_type": entity_type.rstrip('s'),  # Remove plural
                    "organization_id": entity_data.get("relationships", {}).get(
                        "organization", {}
                    ).get("data", {}).get("id"),
                    "name": entity_data.get("attributes", {}).get("name", ""),
                    "attributes": entity_data.get("attributes", {}),
                    "relationships": entity_data.get("relationships", {}),
                    "search_text": search_text,
                    "last_synced": datetime.utcnow()
                }
                
                # Upsert entity
                entity = await uow.itglue.upsert(**entity_dict)
                
                # Add to embedding queue
                await uow.embedding_queue.add_to_queue(
                    entity_id=str(entity.id),
                    entity_type=entity_type
                )
                
            except Exception as e:
                logger.error(
                    f"Failed to process entity {entity_data.get('id')}: {e}"
                )
                
    def _extract_search_text(self, entity_data: Dict[str, Any]) -> str:
        """Extract searchable text from entity data.
        
        Args:
            entity_data: Entity data from API
            
        Returns:
            Concatenated searchable text
        """
        attributes = entity_data.get("attributes", {})
        
        # Extract relevant text fields
        text_fields = []
        
        # Common fields
        for field in ["name", "description", "notes", "content"]:
            if field in attributes and attributes[field]:
                text_fields.append(str(attributes[field]))
                
        # Configuration specific
        if "hostname" in attributes:
            text_fields.append(attributes["hostname"])
        if "primary_ip" in attributes:
            text_fields.append(attributes["primary_ip"])
            
        # Password specific
        if "username" in attributes:
            text_fields.append(attributes["username"])
        if "url" in attributes:
            text_fields.append(attributes["url"])
            
        # Contact specific
        if "first_name" in attributes and "last_name" in attributes:
            text_fields.append(
                f"{attributes.get('first_name', '')} {attributes.get('last_name', '')}"
            )
        if "title" in attributes:
            text_fields.append(attributes["title"])
            
        return " ".join(text_fields).lower()
        
    async def sync_organization(self, organization_id: str) -> Dict[str, Any]:
        """Sync a specific organization and all its entities.
        
        Args:
            organization_id: IT Glue organization ID
            
        Returns:
            Sync statistics
        """
        logger.info(f"Syncing organization {organization_id}")
        
        stats = {
            "organization_id": organization_id,
            "started_at": datetime.utcnow(),
            "entities": {},
            "total_synced": 0
        }
        
        async with self.client:
            # Sync organization details
            org = await self.client.get_organization(organization_id)
            
            async with db_manager.get_session() as session:
                uow = UnitOfWork(session)
                
                # Store organization
                await uow.itglue.upsert(
                    itglue_id=org.id,
                    entity_type="organization",
                    name=org.attributes.get("name", ""),
                    attributes=org.attributes,
                    relationships=org.relationships,
                    last_synced=datetime.utcnow()
                )
                
                await uow.commit()
                
            # Sync related entities
            entity_types = [
                "configurations",
                "flexible_assets",
                "passwords",
                "documents",
                "contacts",
                "locations"
            ]
            
            for entity_type in entity_types:
                try:
                    count = await self._sync_organization_entities(
                        organization_id,
                        entity_type
                    )
                    stats["entities"][entity_type] = count
                    stats["total_synced"] += count
                    
                except Exception as e:
                    logger.error(
                        f"Failed to sync {entity_type} for org {organization_id}: {e}"
                    )
                    
        stats["completed_at"] = datetime.utcnow()
        stats["duration_seconds"] = (
            stats["completed_at"] - stats["started_at"]
        ).total_seconds()
        
        logger.info(
            f"Organization sync completed: {stats['total_synced']} entities synced"
        )
        
        return stats
        
    async def _sync_organization_entities(
        self,
        organization_id: str,
        entity_type: str
    ) -> int:
        """Sync entities for a specific organization.
        
        Args:
            organization_id: IT Glue organization ID
            entity_type: Type of entities to sync
            
        Returns:
            Number of entities synced
        """
        # Fetch entities for organization
        if entity_type == "configurations":
            entities = await self.client.get_configurations(org_id=organization_id)
        elif entity_type == "flexible_assets":
            entities = await self.client.get_flexible_assets(org_id=organization_id)
        elif entity_type == "passwords":
            entities = await self.client.get_passwords(org_id=organization_id)
        elif entity_type == "documents":
            entities = await self.client.get_documents(org_id=organization_id)
        elif entity_type == "contacts":
            entities = await self.client.get_contacts(org_id=organization_id)
        elif entity_type == "locations":
            entities = await self.client.get_locations(org_id=organization_id)
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")
            
        # Convert to dicts
        entity_dicts = [entity.dict() for entity in entities]
        
        # Process in batches
        async with db_manager.get_session() as session:
            uow = UnitOfWork(session)
            
            for i in range(0, len(entity_dicts), self.batch_size):
                batch = entity_dicts[i:i + self.batch_size]
                await self._process_batch(uow, entity_type, batch)
                await uow.commit()
                
        return len(entity_dicts)