"""Incremental sync logic for IT Glue data."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from src.data import UnitOfWork, db_manager
from src.services.itglue.client import ITGlueClient

logger = logging.getLogger(__name__)


class IncrementalSync:
    """Handles incremental synchronization of IT Glue data."""

    def __init__(
        self,
        itglue_client: ITGlueClient,
        batch_size: int = 100,
        lookback_minutes: int = 30
    ):
        """Initialize incremental sync.

        Args:
            itglue_client: IT Glue API client
            batch_size: Number of entities to process in each batch
            lookback_minutes: Extra minutes to look back for changes
        """
        self.client = itglue_client
        self.batch_size = batch_size
        self.lookback_minutes = lookback_minutes

    async def sync_changes(self) -> dict[str, Any]:
        """Sync only changed entities since last sync.

        Returns:
            Sync statistics
        """
        logger.info("Starting incremental sync")

        stats = {
            "started_at": datetime.utcnow(),
            "entity_types": {},
            "total_changed": 0,
            "total_deleted": 0,
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

        for entity_type in entity_types:
            try:
                result = await self._sync_entity_changes(entity_type)
                stats["entity_types"][entity_type] = result
                stats["total_changed"] += result.get("changed", 0)
                stats["total_deleted"] += result.get("deleted", 0)

            except Exception as e:
                logger.error(f"Failed to sync changes for {entity_type}: {e}")
                stats["errors"].append({
                    "entity_type": entity_type,
                    "error": str(e)
                })

        stats["completed_at"] = datetime.utcnow()
        stats["duration_seconds"] = (
            stats["completed_at"] - stats["started_at"]
        ).total_seconds()

        logger.info(
            f"Incremental sync completed: {stats['total_changed']} changed, "
            f"{stats['total_deleted']} deleted in {stats['duration_seconds']:.2f}s"
        )

        return stats

    async def _sync_entity_changes(self, entity_type: str) -> dict[str, Any]:
        """Sync changes for a specific entity type.

        Args:
            entity_type: Type of entity to sync

        Returns:
            Sync statistics for this entity type
        """
        async with db_manager.get_session() as session:
            uow = UnitOfWork(session)

            # Get last sync time
            status = await uow.sync_status.get_by_entity_type(entity_type)

            if not status or not status.last_sync_completed:
                logger.warning(
                    f"No previous sync found for {entity_type}, running full sync"
                )
                return {"changed": 0, "deleted": 0, "skipped": True}

            # Add lookback buffer
            since = status.last_sync_completed - timedelta(
                minutes=self.lookback_minutes
            )

            logger.info(
                f"Syncing {entity_type} changes since {since.isoformat()}"
            )

            # Update sync status
            await uow.sync_status.update_sync_status(
                entity_type=entity_type,
                status="started"
            )
            await uow.commit()

            try:
                # Fetch changed entities
                changed_entities = await self._fetch_changed_entities(
                    entity_type,
                    since
                )

                # Detect deletions
                deleted_ids = await self._detect_deletions(
                    uow,
                    entity_type,
                    changed_entities
                )

                # Process changes
                changed_count = await self._process_changes(
                    uow,
                    entity_type,
                    changed_entities
                )

                # Process deletions
                deleted_count = await self._process_deletions(
                    uow,
                    deleted_ids
                )

                # Update sync status
                await uow.sync_status.update_sync_status(
                    entity_type=entity_type,
                    status="completed",
                    records_synced=changed_count
                )
                await uow.commit()

                return {
                    "changed": changed_count,
                    "deleted": deleted_count
                }

            except Exception as e:
                await uow.sync_status.update_sync_status(
                    entity_type=entity_type,
                    status="failed",
                    error_message=str(e)
                )
                await uow.commit()
                raise

    async def _fetch_changed_entities(
        self,
        entity_type: str,
        since: datetime
    ) -> list[dict[str, Any]]:
        """Fetch entities changed since timestamp.

        Args:
            entity_type: Type of entity
            since: Timestamp to check changes from

        Returns:
            List of changed entities
        """
        filters = {"updated_at": f">={since.isoformat()}"}

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

        return [entity.dict() for entity in entities]

    async def _detect_deletions(
        self,
        uow: UnitOfWork,
        entity_type: str,
        current_entities: list[dict[str, Any]]
    ) -> set[str]:
        """Detect deleted entities.

        Args:
            uow: Unit of work
            entity_type: Type of entity
            current_entities: Currently existing entities from API

        Returns:
            Set of deleted entity IDs
        """
        # Get all stored entity IDs for this type
        stored_entities = await uow.itglue.search(
            query="",
            entity_type=entity_type.rstrip('s'),
            limit=10000  # Get all
        )

        stored_ids = {e.itglue_id for e in stored_entities}
        current_ids = {e["id"] for e in current_entities}

        # Find deletions
        deleted_ids = stored_ids - current_ids

        if deleted_ids:
            logger.info(
                f"Detected {len(deleted_ids)} deleted {entity_type}"
            )

        return deleted_ids

    async def _process_changes(
        self,
        uow: UnitOfWork,
        entity_type: str,
        changed_entities: list[dict[str, Any]]
    ) -> int:
        """Process changed entities.

        Args:
            uow: Unit of work
            entity_type: Type of entity
            changed_entities: List of changed entities

        Returns:
            Number of entities processed
        """
        count = 0

        for i in range(0, len(changed_entities), self.batch_size):
            batch = changed_entities[i:i + self.batch_size]

            for entity_data in batch:
                try:
                    # Extract searchable text
                    search_text = self._extract_search_text(entity_data)

                    # Prepare entity
                    entity_dict = {
                        "itglue_id": entity_data["id"],
                        "entity_type": entity_type.rstrip('s'),
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

                    # Add to embedding queue for re-generation
                    await uow.embedding_queue.add_to_queue(
                        entity_id=str(entity.id),
                        entity_type=entity_type
                    )

                    count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to process changed entity {entity_data.get('id')}: {e}"
                    )

            # Commit batch
            await uow.commit()

        logger.info(f"Processed {count} changed {entity_type}")
        return count

    async def _process_deletions(
        self,
        uow: UnitOfWork,
        deleted_ids: set[str]
    ) -> int:
        """Process deleted entities.

        Args:
            uow: Unit of work
            deleted_ids: Set of deleted entity IDs

        Returns:
            Number of entities deleted
        """
        count = 0

        for itglue_id in deleted_ids:
            try:
                entity = await uow.itglue.get_by_itglue_id(itglue_id)

                if entity:
                    await uow.itglue.delete(str(entity.id))
                    count += 1

            except Exception as e:
                logger.error(f"Failed to delete entity {itglue_id}: {e}")

        await uow.commit()

        if count > 0:
            logger.info(f"Deleted {count} entities")

        return count

    def _extract_search_text(self, entity_data: dict[str, Any]) -> str:
        """Extract searchable text from entity data.

        Args:
            entity_data: Entity data from API

        Returns:
            Concatenated searchable text
        """
        attributes = entity_data.get("attributes", {})
        text_fields = []

        # Common fields
        for field in ["name", "description", "notes", "content"]:
            if field in attributes and attributes[field]:
                text_fields.append(str(attributes[field]))

        # Type-specific fields
        if "hostname" in attributes:
            text_fields.append(attributes["hostname"])
        if "primary_ip" in attributes:
            text_fields.append(attributes["primary_ip"])
        if "username" in attributes:
            text_fields.append(attributes["username"])
        if "url" in attributes:
            text_fields.append(attributes["url"])
        if "first_name" in attributes and "last_name" in attributes:
            text_fields.append(
                f"{attributes.get('first_name', '')} {attributes.get('last_name', '')}"
            )
        if "title" in attributes:
            text_fields.append(attributes["title"])

        return " ".join(text_fields).lower()

    async def continuous_sync(
        self,
        interval_seconds: int = 300,
        stop_event: Optional[asyncio.Event] = None
    ):
        """Run continuous incremental sync.

        Args:
            interval_seconds: Seconds between sync runs
            stop_event: Event to signal stop
        """
        logger.info(
            f"Starting continuous sync with {interval_seconds}s interval"
        )

        if not stop_event:
            stop_event = asyncio.Event()

        while not stop_event.is_set():
            try:
                stats = await self.sync_changes()
                logger.info(
                    f"Continuous sync iteration completed: "
                    f"{stats['total_changed']} changed, "
                    f"{stats['total_deleted']} deleted"
                )

            except Exception as e:
                logger.error(f"Continuous sync iteration failed: {e}")

            # Wait for next iteration
            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=interval_seconds
                )
            except asyncio.TimeoutError:
                continue

        logger.info("Continuous sync stopped")
