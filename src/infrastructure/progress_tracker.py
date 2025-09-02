"""Progress tracking and feedback for infrastructure documentation generation."""

import asyncio
import logging
import uuid
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from src.data import db_manager

logger = logging.getLogger(__name__)


class ProgressStatus(Enum):
    """Progress status enumeration."""
    INITIALIZING = "initializing"
    QUERYING = "querying"
    NORMALIZING = "normalizing"
    GENERATING_EMBEDDINGS = "generating_embeddings"
    GENERATING_DOCUMENT = "generating_document"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"


class ProgressTracker:
    """Tracks and reports progress for infrastructure documentation generation."""

    def __init__(self, snapshot_id: str, total_steps: int = 6):
        """Initialize progress tracker.

        Args:
            snapshot_id: Snapshot ID for tracking
            total_steps: Total number of major steps
        """
        self.snapshot_id = snapshot_id
        self.progress_id = str(uuid.uuid4())
        self.total_steps = total_steps
        self.current_step = 0
        self.status = ProgressStatus.INITIALIZING
        self.start_time = datetime.utcnow()
        self.callbacks: list[Callable] = []

    async def initialize(self, operation: str):
        """Initialize progress tracking in database.

        Args:
            operation: Operation description
        """
        query = """
            INSERT INTO infrastructure_progress
            (id, snapshot_id, operation, total_items, completed_items,
             current_item, status_message, error_count, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """

        try:
            async with db_manager.acquire() as conn:
                await conn.execute(
                    query,
                    uuid.UUID(self.progress_id),
                    uuid.UUID(self.snapshot_id),
                    operation,
                    self.total_steps,
                    0,
                    None,
                    "Starting infrastructure documentation generation",
                    0,
                    datetime.utcnow()
                )
                logger.info(f"Progress tracking initialized for {operation}")
        except Exception as e:
            logger.error(f"Failed to initialize progress tracking: {e}")

    async def update(
        self,
        status: ProgressStatus,
        current_item: Optional[str] = None,
        completed_items: Optional[int] = None,
        total_items: Optional[int] = None,
        message: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Update progress status.

        Args:
            status: Current status
            current_item: Current item being processed
            completed_items: Number of completed items
            total_items: Total items to process
            message: Status message
            error: Error message if any
        """
        self.status = status

        # Calculate percentage
        if completed_items is not None and total_items:
            percentage = int((completed_items / total_items) * 100)
        else:
            percentage = int((self.current_step / self.total_steps) * 100)

        # Build status message
        if not message:
            message = self._get_default_message(status)

        # Update database
        await self._update_database(
            current_item=current_item,
            completed_items=completed_items or self.current_step,
            total_items=total_items or self.total_steps,
            status_message=message,
            error_message=error
        )

        # Notify callbacks
        progress_data = {
            "snapshot_id": self.snapshot_id,
            "status": status.value,
            "percentage": percentage,
            "current_item": current_item,
            "message": message,
            "elapsed_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            "error": error
        }

        await self._notify_callbacks(progress_data)

        # Log progress
        if error:
            logger.error(f"Progress error: {error}")
        else:
            logger.info(f"Progress: {status.value} - {percentage}% - {message}")

    async def step_completed(self, step_name: str):
        """Mark a major step as completed.

        Args:
            step_name: Name of the completed step
        """
        self.current_step += 1
        await self.update(
            status=self.status,
            completed_items=self.current_step,
            message=f"Completed: {step_name}"
        )

    async def report_error(self, error: str, fatal: bool = False):
        """Report an error during processing.

        Args:
            error: Error message
            fatal: Whether the error is fatal
        """
        # Increment error count
        await self._increment_error_count()

        if fatal:
            await self.update(
                status=ProgressStatus.FAILED,
                error=error,
                message=f"Fatal error: {error}"
            )
        else:
            await self.update(
                status=self.status,
                error=error,
                message=f"Error (continuing): {error}"
            )

    async def complete(self, summary: dict[str, Any]):
        """Mark the process as completed.

        Args:
            summary: Summary of the completed process
        """
        duration = (datetime.utcnow() - self.start_time).total_seconds()

        message = (
            f"Infrastructure documentation completed in {duration:.1f} seconds. "
            f"Processed {summary.get('total_resources', 0)} resources."
        )

        await self.update(
            status=ProgressStatus.COMPLETED,
            completed_items=self.total_steps,
            message=message
        )

    def add_callback(self, callback: Callable):
        """Add a progress callback.

        Args:
            callback: Async callback function to receive progress updates
        """
        self.callbacks.append(callback)

    async def _update_database(
        self,
        current_item: Optional[str],
        completed_items: int,
        total_items: int,
        status_message: str,
        error_message: Optional[str]
    ):
        """Update progress in database.

        Args:
            current_item: Current item being processed
            completed_items: Number of completed items
            total_items: Total items
            status_message: Status message
            error_message: Error message if any
        """
        query = """
            UPDATE infrastructure_progress
            SET completed_items = $2,
                total_items = $3,
                current_item = $4,
                status_message = $5,
                updated_at = $6
            WHERE id = $1
        """

        try:
            async with db_manager.acquire() as conn:
                await conn.execute(
                    query,
                    uuid.UUID(self.progress_id),
                    completed_items,
                    total_items,
                    current_item,
                    status_message,
                    datetime.utcnow()
                )

                # Update error if provided
                if error_message:
                    error_query = """
                        UPDATE infrastructure_snapshots
                        SET error_message = $2
                        WHERE id = $1
                    """
                    await conn.execute(
                        error_query,
                        uuid.UUID(self.snapshot_id),
                        error_message
                    )
        except Exception as e:
            logger.error(f"Failed to update progress: {e}")

    async def _increment_error_count(self):
        """Increment the error count in database."""
        query = """
            UPDATE infrastructure_progress
            SET error_count = error_count + 1
            WHERE id = $1
        """

        try:
            async with db_manager.acquire() as conn:
                await conn.execute(query, uuid.UUID(self.progress_id))
        except Exception as e:
            logger.error(f"Failed to increment error count: {e}")

    async def _notify_callbacks(self, progress_data: dict[str, Any]):
        """Notify all registered callbacks with progress data.

        Args:
            progress_data: Progress information to send
        """
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress_data)
                else:
                    callback(progress_data)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def _get_default_message(self, status: ProgressStatus) -> str:
        """Get default message for a status.

        Args:
            status: Progress status

        Returns:
            Default status message
        """
        messages = {
            ProgressStatus.INITIALIZING: "Initializing infrastructure documentation",
            ProgressStatus.QUERYING: "Querying IT Glue resources",
            ProgressStatus.NORMALIZING: "Processing and normalizing data",
            ProgressStatus.GENERATING_EMBEDDINGS: "Generating embeddings for search",
            ProgressStatus.GENERATING_DOCUMENT: "Creating documentation",
            ProgressStatus.UPLOADING: "Uploading to IT Glue",
            ProgressStatus.COMPLETED: "Documentation generation completed",
            ProgressStatus.FAILED: "Documentation generation failed"
        }
        return messages.get(status, "Processing...")

    async def get_current_progress(self) -> dict[str, Any]:
        """Get current progress information.

        Returns:
            Current progress data
        """
        query = """
            SELECT * FROM infrastructure_progress
            WHERE id = $1
        """

        try:
            async with db_manager.acquire() as conn:
                row = await conn.fetchrow(query, uuid.UUID(self.progress_id))
                if row:
                    return {
                        "progress_id": str(row['id']),
                        "snapshot_id": str(row['snapshot_id']),
                        "operation": row['operation'],
                        "completed_items": row['completed_items'],
                        "total_items": row['total_items'],
                        "current_item": row['current_item'],
                        "status_message": row['status_message'],
                        "error_count": row['error_count'],
                        "percentage": int((row['completed_items'] / row['total_items']) * 100)
                                     if row['total_items'] else 0,
                        "elapsed_seconds": (datetime.utcnow() - self.start_time).total_seconds()
                    }
        except Exception as e:
            logger.error(f"Failed to get current progress: {e}")

        return {}


class ProgressReporter:
    """Reports progress to external systems (WebSocket, SSE, etc.)."""

    def __init__(self):
        """Initialize progress reporter."""
        self.active_trackers: dict[str, ProgressTracker] = {}

    def register_tracker(self, snapshot_id: str, tracker: ProgressTracker):
        """Register a progress tracker.

        Args:
            snapshot_id: Snapshot ID
            tracker: Progress tracker instance
        """
        self.active_trackers[snapshot_id] = tracker
        tracker.add_callback(self.broadcast_progress)

    async def broadcast_progress(self, progress_data: dict[str, Any]):
        """Broadcast progress to all connected clients.

        Args:
            progress_data: Progress information to broadcast
        """
        # This would integrate with WebSocket/SSE for real-time updates
        # For now, just log the progress
        logger.debug(f"Broadcasting progress: {progress_data}")

        # In production, this would send to:
        # - WebSocket connections
        # - Server-Sent Events stream
        # - Message queue for other services
        # - Monitoring/metrics systems

    async def get_active_operations(self) -> list[dict[str, Any]]:
        """Get all active operations.

        Returns:
            List of active operation progress data
        """
        active = []
        for snapshot_id, tracker in self.active_trackers.items():
            progress = await tracker.get_current_progress()
            if progress and tracker.status not in (ProgressStatus.COMPLETED, ProgressStatus.FAILED):
                active.append(progress)
        return active

    def cleanup_completed(self):
        """Remove completed trackers from memory."""
        completed = [
            sid for sid, tracker in self.active_trackers.items()
            if tracker.status in (ProgressStatus.COMPLETED, ProgressStatus.FAILED)
        ]
        for sid in completed:
            del self.active_trackers[sid]


# Global progress reporter instance
progress_reporter = ProgressReporter()
