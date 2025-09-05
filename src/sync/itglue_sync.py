"""IT Glue API sync with rate limiting and full database population."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import aiohttp
from dataclasses import dataclass
import json

from src.config.settings import settings
from src.data import db_manager, UnitOfWork
from src.data.models import ITGlueEntity
from sqlalchemy import text

logger = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    """Rate limiter for IT Glue API compliance."""
    
    max_requests_per_minute: int = 100  # IT Glue's standard limit
    max_requests_per_10_seconds: int = 10  # Conservative burst limit
    request_times: List[datetime] = None
    
    def __post_init__(self):
        self.request_times = []
    
    async def wait_if_needed(self):
        """Wait if we're hitting rate limits."""
        now = datetime.now()
        
        # Clean old requests (older than 1 minute)
        self.request_times = [
            t for t in self.request_times 
            if now - t < timedelta(minutes=1)
        ]
        
        # Check 10-second window
        recent_10s = [
            t for t in self.request_times 
            if now - t < timedelta(seconds=10)
        ]
        
        if len(recent_10s) >= self.max_requests_per_10_seconds:
            wait_time = 10 - (now - recent_10s[0]).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit: waiting {wait_time:.1f}s (10s window)")
                await asyncio.sleep(wait_time)
        
        # Check 1-minute window
        if len(self.request_times) >= self.max_requests_per_minute:
            wait_time = 60 - (now - self.request_times[0]).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit: waiting {wait_time:.1f}s (60s window)")
                await asyncio.sleep(wait_time)
        
        # Record this request
        self.request_times.append(now)


class ITGlueAPIClient:
    """IT Glue API client with rate limiting."""
    
    def __init__(self):
        self.base_url = settings.itglue_api_url
        self.api_key = settings.itglue_api_key
        self.rate_limiter = RateLimiter(
            max_requests_per_minute=settings.itglue_rate_limit
        )
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/vnd.api+json"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a GET request with rate limiting."""
        await self.rate_limiter.wait_if_needed()
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                return data
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {e}")
            raise
    
    async def get_paginated(
        self, 
        endpoint: str, 
        params: Optional[Dict] = None,
        max_pages: Optional[int] = None
    ) -> List[Dict]:
        """Get all pages of results with rate limiting."""
        if params is None:
            params = {}
        
        params['page[size]'] = 50  # IT Glue max page size
        params['page[number]'] = 1
        
        all_data = []
        page_count = 0
        
        while True:
            logger.info(f"Fetching {endpoint} page {params['page[number]']}")
            
            response = await self.get(endpoint, params)
            
            # Extract data from response
            data = response.get('data', [])
            all_data.extend(data)
            
            # Check for more pages
            links = response.get('links', {})
            if not links.get('next'):
                break
            
            params['page[number]'] += 1
            page_count += 1
            
            if max_pages and page_count >= max_pages:
                logger.info(f"Reached max pages limit ({max_pages})")
                break
        
        return all_data


class ITGlueSyncManager:
    """Manages syncing IT Glue data to all databases."""
    
    def __init__(self):
        self.api_client = ITGlueAPIClient()
        self.stats = {
            'organizations': 0,
            'configurations': 0,
            'passwords': 0,
            'documents': 0,
            'flexible_assets': 0,
            'contacts': 0,
            'locations': 0,
            'errors': 0
        }
    
    async def sync_all(self, organization_ids: Optional[List[str]] = None):
        """Sync all IT Glue data with rate limiting."""
        logger.info("=" * 60)
        logger.info("Starting IT Glue sync with rate limiting")
        logger.info(f"Rate limit: {settings.itglue_rate_limit} requests/minute")
        logger.info("=" * 60)
        
        await db_manager.initialize()
        
        async with self.api_client as client:
            # 1. Sync Organizations
            if not organization_ids:
                await self.sync_organizations()
                # Get organization IDs from database
                organization_ids = await self.get_organization_ids()
            
            # 2. Sync data for each organization
            for org_id in organization_ids:
                logger.info(f"\n📁 Syncing organization {org_id}")
                
                # Sync various entity types
                await self.sync_configurations(org_id)
                await self.sync_passwords(org_id)
                await self.sync_documents(org_id)
                await self.sync_flexible_assets(org_id)
                await self.sync_contacts(org_id)
                await self.sync_locations(org_id)
                
                # Generate embeddings and update graphs periodically
                if self.stats['configurations'] % 50 == 0:
                    await self.generate_embeddings_batch()
                    await self.update_graph_relationships()
        
        # Final batch processing
        await self.generate_embeddings_batch()
        await self.update_graph_relationships()
        
        # Print summary
        self.print_summary()
    
    async def sync_organizations(self):
        """Sync organizations from IT Glue."""
        logger.info("\n🏢 Syncing organizations...")
        
        try:
            orgs = await self.api_client.get_paginated('organizations')
            
            async with db_manager.get_session() as session:
                uow = UnitOfWork(session)
                
                for org_data in orgs:
                    entity = ITGlueEntity(
                        itglue_id=str(org_data['id']),
                        entity_type='organization',
                        organization_id=None,  # Organizations don't have parent org
                        name=org_data['attributes'].get('name'),
                        attributes=org_data['attributes'],
                        relationships=org_data.get('relationships', {}),
                        search_text=self.build_search_text(org_data),
                        last_synced=datetime.utcnow()
                    )
                    
                    await uow.itglue.create_or_update(entity)
                    self.stats['organizations'] += 1
                
                await uow.commit()
                logger.info(f"✅ Synced {self.stats['organizations']} organizations")
                
        except Exception as e:
            logger.error(f"Failed to sync organizations: {e}")
            self.stats['errors'] += 1
    
    async def sync_configurations(self, org_id: str):
        """Sync configurations for an organization."""
        logger.info(f"  🖥️ Syncing configurations...")
        
        try:
            configs = await self.api_client.get_paginated(
                'configurations',
                params={'filter[organization_id]': org_id}
            )
            
            async with db_manager.get_session() as session:
                uow = UnitOfWork(session)
                count = 0
                
                for config_data in configs:
                    entity = ITGlueEntity(
                        itglue_id=str(config_data['id']),
                        entity_type='configuration',
                        organization_id=org_id,
                        name=config_data['attributes'].get('name'),
                        attributes=config_data['attributes'],
                        relationships=config_data.get('relationships', {}),
                        search_text=self.build_search_text(config_data),
                        last_synced=datetime.utcnow()
                    )
                    
                    await uow.itglue.create_or_update(entity)
                    count += 1
                
                await uow.commit()
                self.stats['configurations'] += count
                logger.info(f"    ✅ {count} configurations")
                
        except Exception as e:
            logger.error(f"Failed to sync configurations: {e}")
            self.stats['errors'] += 1
    
    async def sync_passwords(self, org_id: str):
        """Sync passwords for an organization (metadata only)."""
        logger.info(f"  🔑 Syncing passwords...")
        
        try:
            passwords = await self.api_client.get_paginated(
                'passwords',
                params={'filter[organization_id]': org_id}
            )
            
            async with db_manager.get_session() as session:
                uow = UnitOfWork(session)
                count = 0
                
                for pwd_data in passwords:
                    # Remove actual password from attributes for security
                    attrs = pwd_data['attributes'].copy()
                    attrs.pop('password', None)
                    
                    entity = ITGlueEntity(
                        itglue_id=str(pwd_data['id']),
                        entity_type='password',
                        organization_id=org_id,
                        name=pwd_data['attributes'].get('name'),
                        attributes=attrs,
                        relationships=pwd_data.get('relationships', {}),
                        search_text=self.build_search_text(pwd_data),
                        last_synced=datetime.utcnow()
                    )
                    
                    await uow.itglue.create_or_update(entity)
                    count += 1
                
                await uow.commit()
                self.stats['passwords'] += count
                logger.info(f"    ✅ {count} passwords")
                
        except Exception as e:
            logger.error(f"Failed to sync passwords: {e}")
            self.stats['errors'] += 1
    
    async def sync_documents(self, org_id: str):
        """Sync documents for an organization."""
        logger.info(f"  📄 Syncing documents...")
        
        try:
            documents = await self.api_client.get_paginated(
                'documents',
                params={'filter[organization_id]': org_id}
            )
            
            async with db_manager.get_session() as session:
                uow = UnitOfWork(session)
                count = 0
                
                for doc_data in documents:
                    entity = ITGlueEntity(
                        itglue_id=str(doc_data['id']),
                        entity_type='document',
                        organization_id=org_id,
                        name=doc_data['attributes'].get('name'),
                        attributes=doc_data['attributes'],
                        relationships=doc_data.get('relationships', {}),
                        search_text=self.build_search_text(doc_data),
                        last_synced=datetime.utcnow()
                    )
                    
                    await uow.itglue.create_or_update(entity)
                    count += 1
                
                await uow.commit()
                self.stats['documents'] += count
                logger.info(f"    ✅ {count} documents")
                
        except Exception as e:
            logger.error(f"Failed to sync documents: {e}")
            self.stats['errors'] += 1
    
    async def sync_flexible_assets(self, org_id: str):
        """Sync flexible assets for an organization."""
        logger.info(f"  📦 Syncing flexible assets...")
        
        try:
            assets = await self.api_client.get_paginated(
                'flexible_assets',
                params={'filter[organization_id]': org_id}
            )
            
            async with db_manager.get_session() as session:
                uow = UnitOfWork(session)
                count = 0
                
                for asset_data in assets:
                    entity = ITGlueEntity(
                        itglue_id=str(asset_data['id']),
                        entity_type='flexible_asset',
                        organization_id=org_id,
                        name=asset_data['attributes'].get('name'),
                        attributes=asset_data['attributes'],
                        relationships=asset_data.get('relationships', {}),
                        search_text=self.build_search_text(asset_data),
                        last_synced=datetime.utcnow()
                    )
                    
                    await uow.itglue.create_or_update(entity)
                    count += 1
                
                await uow.commit()
                self.stats['flexible_assets'] += count
                logger.info(f"    ✅ {count} flexible assets")
                
        except Exception as e:
            logger.error(f"Failed to sync flexible assets: {e}")
            self.stats['errors'] += 1
    
    async def sync_contacts(self, org_id: str):
        """Sync contacts for an organization."""
        logger.info(f"  👤 Syncing contacts...")
        
        try:
            contacts = await self.api_client.get_paginated(
                'contacts',
                params={'filter[organization_id]': org_id}
            )
            
            async with db_manager.get_session() as session:
                uow = UnitOfWork(session)
                count = 0
                
                for contact_data in contacts:
                    name = f"{contact_data['attributes'].get('first_name', '')} {contact_data['attributes'].get('last_name', '')}".strip()
                    
                    entity = ITGlueEntity(
                        itglue_id=str(contact_data['id']),
                        entity_type='contact',
                        organization_id=org_id,
                        name=name,
                        attributes=contact_data['attributes'],
                        relationships=contact_data.get('relationships', {}),
                        search_text=self.build_search_text(contact_data),
                        last_synced=datetime.utcnow()
                    )
                    
                    await uow.itglue.create_or_update(entity)
                    count += 1
                
                await uow.commit()
                self.stats['contacts'] += count
                logger.info(f"    ✅ {count} contacts")
                
        except Exception as e:
            logger.error(f"Failed to sync contacts: {e}")
            self.stats['errors'] += 1
    
    async def sync_locations(self, org_id: str):
        """Sync locations for an organization."""
        logger.info(f"  📍 Syncing locations...")
        
        try:
            locations = await self.api_client.get_paginated(
                'locations',
                params={'filter[organization_id]': org_id}
            )
            
            async with db_manager.get_session() as session:
                uow = UnitOfWork(session)
                count = 0
                
                for location_data in locations:
                    entity = ITGlueEntity(
                        itglue_id=str(location_data['id']),
                        entity_type='location',
                        organization_id=org_id,
                        name=location_data['attributes'].get('name'),
                        attributes=location_data['attributes'],
                        relationships=location_data.get('relationships', {}),
                        search_text=self.build_search_text(location_data),
                        last_synced=datetime.utcnow()
                    )
                    
                    await uow.itglue.create_or_update(entity)
                    count += 1
                
                await uow.commit()
                self.stats['locations'] += count
                logger.info(f"    ✅ {count} locations")
                
        except Exception as e:
            logger.error(f"Failed to sync locations: {e}")
            self.stats['errors'] += 1
    
    def build_search_text(self, data: Dict) -> str:
        """Build searchable text from entity data."""
        attrs = data.get('attributes', {})
        
        # Collect searchable fields
        searchable = []
        
        # Add name fields
        for field in ['name', 'hostname', 'title', 'subject']:
            if field in attrs and attrs[field]:
                searchable.append(str(attrs[field]))
        
        # Add description fields
        for field in ['description', 'notes', 'content']:
            if field in attrs and attrs[field]:
                searchable.append(str(attrs[field]))
        
        # Add identifiers
        for field in ['serial_number', 'asset_tag', 'mac_address', 'primary_ip']:
            if field in attrs and attrs[field]:
                searchable.append(str(attrs[field]))
        
        # Add type information
        for field in ['configuration_type', 'asset_type', 'kind']:
            if field in attrs and attrs[field]:
                searchable.append(str(attrs[field]))
        
        return ' '.join(searchable).lower()
    
    async def get_organization_ids(self) -> List[str]:
        """Get organization IDs from database."""
        async with db_manager.get_session() as session:
            result = await session.execute(text("""
                SELECT DISTINCT itglue_id 
                FROM itglue_entities 
                WHERE entity_type = 'organization'
            """))
            
            return [row[0] for row in result]
    
    async def generate_embeddings_batch(self):
        """Generate embeddings for entities without them."""
        logger.info("\n🔄 Generating embeddings for new entities...")
        
        # This would call the embedding generation logic
        # For now, we'll skip this as it was implemented separately
        pass
    
    async def update_graph_relationships(self):
        """Update Neo4j graph relationships."""
        logger.info("🔗 Updating graph relationships...")
        
        # This would call the graph update logic
        # For now, we'll skip this as it was implemented separately
        pass
    
    def print_summary(self):
        """Print sync summary."""
        print("\n" + "=" * 60)
        print("SYNC SUMMARY")
        print("=" * 60)
        
        total = sum(v for k, v in self.stats.items() if k != 'errors')
        
        print(f"""
📊 Entities Synced:
   Organizations:    {self.stats['organizations']:,}
   Configurations:   {self.stats['configurations']:,}
   Passwords:        {self.stats['passwords']:,}
   Documents:        {self.stats['documents']:,}
   Flexible Assets:  {self.stats['flexible_assets']:,}
   Contacts:         {self.stats['contacts']:,}
   Locations:        {self.stats['locations']:,}
   ─────────────────────────
   Total:            {total:,}
   
❌ Errors:           {self.stats['errors']}

✅ Next Steps:
   1. Run embedding generation for new entities
   2. Update Neo4j graph relationships
   3. Verify search functionality
""")
        print("=" * 60)


async def sync_single_organization(org_id: str):
    """Sync a single organization."""
    sync_manager = ITGlueSyncManager()
    await sync_manager.sync_all(organization_ids=[org_id])


async def sync_all_organizations():
    """Sync all organizations."""
    sync_manager = ITGlueSyncManager()
    await sync_manager.sync_all()


if __name__ == "__main__":
    # Example: Sync specific organization
    # asyncio.run(sync_single_organization("3208599755514479"))
    
    # Or sync all organizations
    asyncio.run(sync_all_organizations())