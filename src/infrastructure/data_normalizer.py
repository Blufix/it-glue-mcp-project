"""Normalizes IT Glue API responses into consistent structure for documentation."""

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from src.data import db_manager

logger = logging.getLogger(__name__)


class DataNormalizer:
    """Normalizes varying IT Glue API response formats."""

    def __init__(self):
        """Initialize the data normalizer."""
        self.resource_handlers = {
            'configurations': self._normalize_configuration,
            'flexible_assets': self._normalize_flexible_asset,
            'contacts': self._normalize_contact,
            'locations': self._normalize_location,
            'documents': self._normalize_document,
            'passwords': self._normalize_password,
            'domains': self._normalize_domain,
            'networks': self._normalize_network
        }

    async def normalize_and_store(
        self,
        raw_data: dict[str, Any],
        snapshot_id: str,
        organization_id: str,
        organization_name: str
    ) -> dict[str, Any]:
        """Normalize raw API data and store in PostgreSQL.

        Args:
            raw_data: Raw data from QueryOrchestrator
            snapshot_id: Snapshot ID for tracking
            organization_id: Organization ID
            organization_name: Organization name

        Returns:
            Normalized data with counts and summaries
        """
        normalized = {
            'organization': {
                'id': organization_id,
                'name': organization_name
            },
            'snapshot_id': snapshot_id,
            'timestamp': datetime.utcnow().isoformat(),
            'resources': [],
            'counts': {},
            'summaries': {}
        }

        # Process each resource type
        for resource_type, resource_data in raw_data.get('resources', {}).items():
            if 'error' in resource_data:
                logger.warning(f"Skipping {resource_type} due to error: {resource_data['error']}")
                continue

            handler = self.resource_handlers.get(resource_type)
            if not handler:
                logger.warning(f"No handler for resource type: {resource_type}")
                continue

            # Normalize each item
            normalized_items = []
            for item in resource_data.get('data', []):
                try:
                    normalized_item = handler(item)
                    normalized_items.append(normalized_item)
                    normalized['resources'].append({
                        'type': resource_type,
                        'data': normalized_item
                    })
                except Exception as e:
                    logger.error(f"Failed to normalize {resource_type} item: {e}")

            # Update counts
            normalized['counts'][resource_type] = len(normalized_items)

            # Generate summary
            normalized['summaries'][resource_type] = self._generate_summary(
                resource_type,
                normalized_items
            )

        # Store normalized data
        await self._store_normalized_data(normalized, snapshot_id)

        # Update snapshot with organization name
        await self._update_snapshot_org_name(snapshot_id, organization_name)

        return normalized

    def _normalize_configuration(self, config: dict) -> dict:
        """Normalize configuration data.

        Args:
            config: Raw configuration from IT Glue

        Returns:
            Normalized configuration
        """
        attributes = config.get('attributes', {})

        return {
            'id': config.get('id'),
            'name': attributes.get('name'),
            'type': attributes.get('configuration-type-name'),
            'status': attributes.get('configuration-status-name'),
            'serial_number': attributes.get('serial-number'),
            'asset_tag': attributes.get('asset-tag'),
            'primary_ip': attributes.get('primary-ip'),
            'hostname': attributes.get('hostname'),
            'operating_system': attributes.get('operating-system'),
            'manufacturer': attributes.get('manufacturer-name'),
            'model': attributes.get('model-name'),
            'location': attributes.get('location-name'),
            'contact': attributes.get('contact-name'),
            'warranty_expires': attributes.get('warranty-expires-at'),
            'installed_by': attributes.get('installed-by'),
            'notes': attributes.get('notes'),
            'created_at': attributes.get('created-at'),
            'updated_at': attributes.get('updated-at')
        }

    def _normalize_flexible_asset(self, asset: dict) -> dict:
        """Normalize flexible asset data.

        Args:
            asset: Raw flexible asset from IT Glue

        Returns:
            Normalized flexible asset
        """
        attributes = asset.get('attributes', {})

        return {
            'id': asset.get('id'),
            'type': attributes.get('flexible-asset-type-name'),
            'name': attributes.get('name'),
            'traits': attributes.get('traits', {}),  # Dynamic fields
            'created_at': attributes.get('created-at'),
            'updated_at': attributes.get('updated-at')
        }

    def _normalize_contact(self, contact: dict) -> dict:
        """Normalize contact data.

        Args:
            contact: Raw contact from IT Glue

        Returns:
            Normalized contact
        """
        attributes = contact.get('attributes', {})

        return {
            'id': contact.get('id'),
            'name': attributes.get('name'),
            'first_name': attributes.get('first-name'),
            'last_name': attributes.get('last-name'),
            'title': attributes.get('title'),
            'contact_type': attributes.get('contact-type-name'),
            'location': attributes.get('location-name'),
            'emails': [
                {
                    'primary': attributes.get('contact-emails', [{}])[0].get('primary'),
                    'value': attributes.get('contact-emails', [{}])[0].get('value')
                }
            ] if attributes.get('contact-emails') else [],
            'phones': [
                {
                    'label': phone.get('label'),
                    'value': phone.get('value')
                }
                for phone in attributes.get('contact-phones', [])
            ],
            'important': attributes.get('important'),
            'notes': attributes.get('notes'),
            'created_at': attributes.get('created-at'),
            'updated_at': attributes.get('updated-at')
        }

    def _normalize_location(self, location: dict) -> dict:
        """Normalize location data.

        Args:
            location: Raw location from IT Glue

        Returns:
            Normalized location
        """
        attributes = location.get('attributes', {})

        return {
            'id': location.get('id'),
            'name': attributes.get('name'),
            'address': attributes.get('address'),
            'address_2': attributes.get('address-2'),
            'city': attributes.get('city'),
            'region': attributes.get('region-name'),
            'country': attributes.get('country-name'),
            'postal_code': attributes.get('postal-code'),
            'phone': attributes.get('phone'),
            'fax': attributes.get('fax'),
            'notes': attributes.get('notes'),
            'primary': attributes.get('primary'),
            'created_at': attributes.get('created-at'),
            'updated_at': attributes.get('updated-at')
        }

    def _normalize_document(self, document: dict) -> dict:
        """Normalize document data.

        Args:
            document: Raw document from IT Glue

        Returns:
            Normalized document
        """
        attributes = document.get('attributes', {})

        return {
            'id': document.get('id'),
            'name': attributes.get('name'),
            'type': 'document',
            'published': attributes.get('published'),
            'created_at': attributes.get('created-at'),
            'updated_at': attributes.get('updated-at'),
            # Note: Document content requires separate API call
            'content_preview': attributes.get('parsed-content', '')[:500] if attributes.get('parsed-content') else ''
        }

    def _normalize_password(self, password: dict) -> dict:
        """Normalize password data (without actual password values).

        Args:
            password: Raw password from IT Glue

        Returns:
            Normalized password metadata
        """
        attributes = password.get('attributes', {})

        return {
            'id': password.get('id'),
            'name': attributes.get('name'),
            'username': attributes.get('username'),
            'url': attributes.get('url'),
            'category': attributes.get('password-category-name'),
            'resource_type': attributes.get('resource-type'),
            'notes': attributes.get('notes'),
            'created_at': attributes.get('created-at'),
            'updated_at': attributes.get('updated-at')
        }

    def _normalize_domain(self, domain: dict) -> dict:
        """Normalize domain data.

        Args:
            domain: Raw domain from IT Glue

        Returns:
            Normalized domain
        """
        attributes = domain.get('attributes', {})

        return {
            'id': domain.get('id'),
            'name': attributes.get('name'),
            'registrar': attributes.get('registrar-name'),
            'expires': attributes.get('expires-on'),
            'notes': attributes.get('notes'),
            'created_at': attributes.get('created-at'),
            'updated_at': attributes.get('updated-at')
        }

    def _normalize_network(self, network: dict) -> dict:
        """Normalize network data.

        Args:
            network: Raw network from IT Glue

        Returns:
            Normalized network
        """
        attributes = network.get('attributes', {})

        return {
            'id': network.get('id'),
            'name': attributes.get('name'),
            'network': attributes.get('network'),
            'description': attributes.get('description'),
            'location': attributes.get('location-name'),
            'created_at': attributes.get('created-at'),
            'updated_at': attributes.get('updated-at')
        }

    def _generate_summary(self, resource_type: str, items: list[dict]) -> dict:
        """Generate summary statistics for a resource type.

        Args:
            resource_type: Type of resource
            items: Normalized items

        Returns:
            Summary statistics
        """
        summary = {
            'total': len(items)
        }

        if resource_type == 'configurations':
            # Group by type and status
            types = {}
            statuses = {}
            for item in items:
                config_type = item.get('type', 'Unknown')
                status = item.get('status', 'Unknown')
                types[config_type] = types.get(config_type, 0) + 1
                statuses[status] = statuses.get(status, 0) + 1

            summary['by_type'] = types
            summary['by_status'] = statuses

        elif resource_type == 'flexible_assets':
            # Group by asset type
            asset_types = {}
            for item in items:
                asset_type = item.get('type', 'Unknown')
                asset_types[asset_type] = asset_types.get(asset_type, 0) + 1
            summary['by_type'] = asset_types

        elif resource_type == 'contacts':
            # Count important contacts
            important = sum(1 for item in items if item.get('important'))
            summary['important'] = important

        elif resource_type == 'locations':
            # Count primary locations
            primary = sum(1 for item in items if item.get('primary'))
            summary['primary'] = primary

        return summary

    async def _store_normalized_data(self, normalized: dict, snapshot_id: str):
        """Store normalized data in PostgreSQL.

        Args:
            normalized: Normalized data
            snapshot_id: Snapshot ID
        """
        # Update snapshot with normalized data
        query = """
            UPDATE infrastructure_snapshots
            SET snapshot_data = $2,
                resource_count = $3
            WHERE id = $1
        """

        try:
            async with db_manager.acquire() as conn:
                await conn.execute(
                    query,
                    uuid.UUID(snapshot_id),
                    json.dumps(normalized),
                    len(normalized.get('resources', []))
                )
                logger.info(f"Stored {len(normalized['resources'])} normalized resources")
        except Exception as e:
            logger.error(f"Failed to store normalized data: {e}")
            raise

    async def _update_snapshot_org_name(self, snapshot_id: str, organization_name: str):
        """Update snapshot with organization name.

        Args:
            snapshot_id: Snapshot ID
            organization_name: Organization name
        """
        query = """
            UPDATE infrastructure_snapshots
            SET organization_name = $2
            WHERE id = $1
        """

        try:
            async with db_manager.acquire() as conn:
                await conn.execute(
                    query,
                    uuid.UUID(snapshot_id),
                    organization_name
                )
        except Exception as e:
            logger.error(f"Failed to update organization name: {e}")
