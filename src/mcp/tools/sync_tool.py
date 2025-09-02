"""Sync tool for IT Glue data synchronization."""

from datetime import datetime
from typing import Any, Optional

from src.services.sync import SyncService

from .base import BaseTool


class SyncTool(BaseTool):
    """Tool for managing IT Glue data synchronization."""

    def __init__(self, sync_service: SyncService):
        """Initialize sync tool.

        Args:
            sync_service: Sync service instance
        """
        super().__init__(
            name="sync",
            description="Manage IT Glue data synchronization"
        )
        self.sync_service = sync_service

    async def execute(
        self,
        action: str,
        entity_type: Optional[str] = None,
        company_id: Optional[str] = None,
        force: bool = False,
        **kwargs
    ) -> dict[str, Any]:
        """Execute sync operation.

        Args:
            action: Sync action (status, start, stop, force)
            entity_type: Type of entity to sync
            company_id: Specific company to sync
            force: Force full sync
            **kwargs: Additional parameters

        Returns:
            Sync operation result
        """
        try:
            if action == "status":
                return await self._get_status()

            elif action == "start":
                return await self._start_sync(
                    entity_type=entity_type,
                    company_id=company_id,
                    force=force
                )

            elif action == "stop":
                return await self._stop_sync()

            elif action == "history":
                return await self._get_history(
                    limit=kwargs.get("limit", 10)
                )

            else:
                return self.format_error(f"Unknown action: {action}")

        except Exception as e:
            self.logger.error(f"Sync operation error: {e}", exc_info=True)
            return self.format_error(f"Sync failed: {str(e)}")

    async def _get_status(self) -> dict[str, Any]:
        """Get current sync status.

        Returns:
            Sync status information
        """
        status = await self.sync_service.get_status()

        return self.format_success({
            "active": status.is_active,
            "current_task": status.current_task,
            "last_sync": status.last_sync.isoformat() if status.last_sync else None,
            "next_sync": status.next_sync.isoformat() if status.next_sync else None,
            "statistics": {
                "organizations": status.org_count,
                "configurations": status.config_count,
                "documents": status.doc_count,
                "last_error": status.last_error
            }
        })

    async def _start_sync(
        self,
        entity_type: Optional[str],
        company_id: Optional[str],
        force: bool
    ) -> dict[str, Any]:
        """Start sync operation.

        Args:
            entity_type: Type of entity to sync
            company_id: Specific company to sync
            force: Force full sync

        Returns:
            Sync start result
        """
        # Check if sync is already running
        status = await self.sync_service.get_status()
        if status.is_active:
            return self.format_error(
                "Sync already in progress",
                current_task=status.current_task
            )

        # Start sync
        task_id = await self.sync_service.start_sync(
            entity_type=entity_type,
            company_id=company_id,
            full_sync=force
        )

        return self.format_success({
            "task_id": task_id,
            "entity_type": entity_type or "all",
            "company_id": company_id or "all",
            "full_sync": force,
            "started_at": datetime.utcnow().isoformat()
        })

    async def _stop_sync(self) -> dict[str, Any]:
        """Stop current sync operation.

        Returns:
            Sync stop result
        """
        result = await self.sync_service.stop_sync()

        if result:
            return self.format_success({
                "message": "Sync stopped successfully"
            })
        else:
            return self.format_error("No active sync to stop")

    async def _get_history(self, limit: int) -> dict[str, Any]:
        """Get sync history.

        Args:
            limit: Number of history entries to return

        Returns:
            Sync history
        """
        history = await self.sync_service.get_history(limit=limit)

        return self.format_success({
            "count": len(history),
            "history": [
                {
                    "id": entry.id,
                    "started_at": entry.started_at.isoformat(),
                    "completed_at": entry.completed_at.isoformat() if entry.completed_at else None,
                    "status": entry.status,
                    "entity_type": entry.entity_type,
                    "records_processed": entry.records_processed,
                    "errors": entry.errors
                }
                for entry in history
            ]
        })
