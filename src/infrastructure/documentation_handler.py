"""Main handler for infrastructure documentation generation."""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from src.cache import CacheManager
from src.data import db_manager
from src.services.itglue import ITGlueClient

from .data_normalizer import DataNormalizer
from .document_generator import DocumentGenerator
from .progress_tracker import ProgressStatus, ProgressTracker, progress_reporter
from .query_orchestrator import QueryOrchestrator

logger = logging.getLogger(__name__)


class InfrastructureDocumentationHandler:
    """Handles the complete infrastructure documentation workflow."""

    def __init__(
        self,
        itglue_client: ITGlueClient,
        cache_manager: CacheManager,
        db_manager: Any
    ):
        """Initialize the infrastructure documentation handler.

        Args:
            itglue_client: IT Glue API client
            cache_manager: Cache manager for performance
            db_manager: Database manager for storage
        """
        self.itglue_client = itglue_client
        self.cache_manager = cache_manager
        self.db_manager = db_manager
        self.query_orchestrator = QueryOrchestrator(itglue_client, cache_manager)
        self.data_normalizer = DataNormalizer()
        self.document_generator = DocumentGenerator()

    async def generate_infrastructure_documentation(
        self,
        organization_id: str,
        include_embeddings: bool = True,
        upload_to_itglue: bool = False
    ) -> dict[str, Any]:
        """Generate comprehensive infrastructure documentation for an organization.

        Args:
            organization_id: IT Glue organization ID
            include_embeddings: Whether to generate and store embeddings
            upload_to_itglue: Whether to upload the document to IT Glue

        Returns:
            Documentation generation results with status and metadata
        """
        snapshot_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        # Initialize progress tracker
        progress_tracker = ProgressTracker(snapshot_id, total_steps=6)
        progress_reporter.register_tracker(snapshot_id, progress_tracker)
        await progress_tracker.initialize(f"Infrastructure documentation for organization {organization_id}")

        try:
            # Create initial snapshot record
            await progress_tracker.update(
                status=ProgressStatus.INITIALIZING,
                message="Creating snapshot record"
            )
            snapshot = await self._create_snapshot_record(
                snapshot_id=snapshot_id,
                organization_id=organization_id
            )

            # Step 1: Get organization details
            logger.info(f"Fetching organization details for {organization_id}")
            await progress_tracker.update(
                status=ProgressStatus.QUERYING,
                message="Fetching organization details"
            )
            org_details = await self._get_organization_details(organization_id)

            if not org_details:
                await progress_tracker.report_error(
                    f"Organization {organization_id} not found",
                    fatal=True
                )
                return {
                    "success": False,
                    "error": f"Organization {organization_id} not found"
                }

            await progress_tracker.step_completed("Organization details retrieved")

            # Step 2: Query all IT Glue resources
            logger.info(f"Querying all resources for {org_details['name']}")
            await progress_tracker.update(
                status=ProgressStatus.QUERYING,
                message=f"Querying IT Glue resources for {org_details['name']}"
            )

            # Create progress callback for query orchestrator
            async def query_progress(current, total, message):
                await progress_tracker.update(
                    status=ProgressStatus.QUERYING,
                    current_item=message,
                    completed_items=current,
                    total_items=total,
                    message=f"Querying resources: {message}"
                )

            raw_data = await self.query_orchestrator.query_all_resources(
                organization_id=organization_id,
                snapshot_id=snapshot_id,
                progress_callback=query_progress
            )

            await progress_tracker.step_completed("All resources queried")

            # Step 3: Normalize and store data
            logger.info("Normalizing and storing data")
            await progress_tracker.update(
                status=ProgressStatus.NORMALIZING,
                message="Processing and normalizing data"
            )

            normalized_data = await self.data_normalizer.normalize_and_store(
                raw_data=raw_data,
                snapshot_id=snapshot_id,
                organization_id=organization_id,
                organization_name=org_details['name']
            )

            await progress_tracker.step_completed("Data normalized and stored")

            # Step 4: Generate embeddings if requested
            if include_embeddings:
                logger.info("Generating embeddings for semantic search")
                await progress_tracker.update(
                    status=ProgressStatus.GENERATING_EMBEDDINGS,
                    message="Generating embeddings for semantic search"
                )

                await self._generate_embeddings(
                    normalized_data=normalized_data,
                    snapshot_id=snapshot_id
                )

                await progress_tracker.step_completed("Embeddings generated")

            # Step 5: Generate documentation
            logger.info("Generating infrastructure documentation")
            await progress_tracker.update(
                status=ProgressStatus.GENERATING_DOCUMENT,
                message="Creating infrastructure documentation"
            )

            document = await self.document_generator.generate(
                normalized_data=normalized_data,
                organization_name=org_details['name'],
                snapshot_id=snapshot_id
            )

            await progress_tracker.step_completed("Documentation generated")

            # Step 6: Upload to IT Glue if requested
            document_url = None
            if upload_to_itglue:
                logger.info("Uploading document to IT Glue")
                await progress_tracker.update(
                    status=ProgressStatus.UPLOADING,
                    message="Uploading document to IT Glue"
                )

                document_url = await self._upload_to_itglue(
                    document=document,
                    organization_id=organization_id,
                    organization_name=org_details['name']
                )

                await progress_tracker.step_completed("Document uploaded")

            # Step 7: Update snapshot record
            await self._update_snapshot_record(
                snapshot_id=snapshot_id,
                status="completed",
                document_url=document_url,
                resource_count=len(normalized_data.get('resources', []))
            )

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Mark progress as completed
            summary = {
                "total_resources": len(normalized_data.get('resources', [])),
                "duration": duration
            }
            await progress_tracker.complete(summary)

            return {
                "success": True,
                "snapshot_id": snapshot_id,
                "organization": {
                    "id": organization_id,
                    "name": org_details['name']
                },
                "statistics": {
                    "total_resources": len(normalized_data.get('resources', [])),
                    "configurations": normalized_data.get('counts', {}).get('configurations', 0),
                    "flexible_assets": normalized_data.get('counts', {}).get('flexible_assets', 0),
                    "contacts": normalized_data.get('counts', {}).get('contacts', 0),
                    "locations": normalized_data.get('counts', {}).get('locations', 0),
                    "documents": normalized_data.get('counts', {}).get('documents', 0)
                },
                "document": {
                    "content": document.get('content', ''),
                    "size_bytes": len(document.get('content', '').encode('utf-8')),
                    "url": document_url
                },
                "duration_seconds": duration,
                "embeddings_generated": include_embeddings,
                "uploaded_to_itglue": upload_to_itglue
            }

        except Exception as e:
            logger.error(f"Infrastructure documentation generation failed: {e}", exc_info=True)

            # Report error to progress tracker
            await progress_tracker.report_error(str(e), fatal=True)

            # Update snapshot record with failure
            await self._update_snapshot_record(
                snapshot_id=snapshot_id,
                status="failed",
                error_message=str(e)
            )

            return {
                "success": False,
                "snapshot_id": snapshot_id,
                "error": str(e),
                "duration_seconds": (datetime.utcnow() - start_time).total_seconds()
            }

    async def _get_organization_details(self, organization_id: str) -> Optional[dict]:
        """Get organization details from IT Glue.

        Args:
            organization_id: Organization ID

        Returns:
            Organization details or None if not found
        """
        try:
            response = await self.itglue_client.get_organization(organization_id)
            if response and response.get('data'):
                org_data = response['data']
                return {
                    'id': org_data.get('id'),
                    'name': org_data.get('attributes', {}).get('name'),
                    'type': org_data.get('attributes', {}).get('organization-type-name')
                }
        except Exception as e:
            logger.error(f"Failed to get organization details: {e}")
        return None

    async def _create_snapshot_record(
        self,
        snapshot_id: str,
        organization_id: str
    ) -> dict:
        """Create initial snapshot record in database.

        Args:
            snapshot_id: Unique snapshot ID
            organization_id: Organization ID

        Returns:
            Created snapshot record
        """
        query = """
            INSERT INTO infrastructure_snapshots
            (id, organization_id, organization_name, snapshot_type,
             snapshot_data, status, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """

        async with db_manager.acquire() as conn:
            record = await conn.fetchrow(
                query,
                uuid.UUID(snapshot_id),
                organization_id,
                'pending',  # Will be updated with org name
                'full',
                json.dumps({}),
                'in_progress',
                datetime.utcnow()
            )
            return dict(record)

    async def _update_snapshot_record(
        self,
        snapshot_id: str,
        status: str,
        document_url: Optional[str] = None,
        resource_count: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """Update snapshot record with results.

        Args:
            snapshot_id: Snapshot ID to update
            status: New status
            document_url: Generated document URL
            resource_count: Number of resources documented
            error_message: Error message if failed
        """
        query = """
            UPDATE infrastructure_snapshots
            SET status = $2,
                document_url = $3,
                resource_count = $4,
                error_message = $5,
                completed_at = $6
            WHERE id = $1
        """

        async with db_manager.acquire() as conn:
            await conn.execute(
                query,
                uuid.UUID(snapshot_id),
                status,
                document_url,
                resource_count,
                error_message,
                datetime.utcnow() if status in ('completed', 'failed') else None
            )

    async def _generate_embeddings(
        self,
        normalized_data: dict,
        snapshot_id: str
    ):
        """Generate embeddings for normalized data.

        Args:
            normalized_data: Normalized infrastructure data
            snapshot_id: Snapshot ID for tracking
        """
        # This will be implemented to use OpenAI embeddings
        # and store them in the infrastructure_embeddings table
        logger.info(f"Embedding generation for {len(normalized_data.get('resources', []))} resources")
        # Implementation will be added when working on the embeddings task
        pass

    async def _upload_to_itglue(
        self,
        document: dict,
        organization_id: str,
        organization_name: str
    ) -> Optional[str]:
        """Upload generated document to IT Glue.

        Args:
            document: Generated document content
            organization_id: Organization ID
            organization_name: Organization name

        Returns:
            Document URL if successful
        """
        try:
            logger.info(f"Uploading infrastructure document for {organization_name}")

            # Prepare document data for IT Glue
            document_data = {
                "data": {
                    "type": "documents",
                    "attributes": {
                        "organization-id": int(organization_id),
                        "name": f"Infrastructure Documentation - {organization_name}",
                        "content": document.get('content', ''),
                        "published": True,
                        "restricted": False,
                        "document-folder-id": None,  # Can be set to specific folder
                        "enable-password-protection": False,
                        "password": None
                    }
                }
            }

            # Make API call to create document
            response = await self.itglue_client.create_document(document_data)

            if response and response.get('data'):
                doc_id = response['data'].get('id')
                doc_url = f"https://yourdomain.itglue.com/organizations/{organization_id}/docs/{doc_id}"
                logger.info(f"Document uploaded successfully: {doc_url}")
                return doc_url
            else:
                logger.error("Failed to upload document: No response data")
                return None

        except Exception as e:
            logger.error(f"Document upload failed: {e}")
            # Non-fatal error - document generation succeeded even if upload failed
            return None

    def _update_progress(self, current: int, total: int, message: str):
        """Progress callback for tracking.

        Args:
            current: Current item being processed
            total: Total items to process
            message: Progress message
        """
        percentage = int((current / total) * 100) if total > 0 else 0
        logger.debug(f"Progress: {percentage}% - {message}")
