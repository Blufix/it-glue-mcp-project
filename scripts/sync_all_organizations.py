#!/usr/bin/env python3
"""Sync all IT Glue organizations to local database."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sync.itglue_sync import sync_all_organizations
from src.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main sync function."""
    print("🚀 Starting IT Glue Full Organization Sync...")
    print("=" * 60)
    
    # Verify configuration
    if not settings.itglue_api_key:
        print("❌ ERROR: IT_GLUE_API_KEY not configured in environment")
        print("Please set your IT Glue API key in .env file")
        return
    
    if not settings.database_url:
        print("❌ ERROR: DATABASE_URL not configured")
        print("Please set your PostgreSQL connection in .env file")
        return
    
    print(f"✅ API Key configured: {settings.itglue_api_key[:10]}...")
    print(f"✅ Database configured: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'local'}")
    print(f"✅ Rate limit: {settings.itglue_rate_limit} requests/minute")
    print()
    
    try:
        # Run the full sync
        await sync_all_organizations()
        
        print("\n🎉 SYNC COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("✅ All organizations and their data have been synced")
        print("✅ Data is now available in your local PostgreSQL database")
        print("✅ You can now use the query tools for fast local searches")
        
    except KeyboardInterrupt:
        print("\n⚠️ Sync interrupted by user")
        print("Partial data may have been synced")
        
    except Exception as e:
        print(f"\n❌ Sync failed: {e}")
        logger.error(f"Sync error: {e}", exc_info=True)
        
        print("\n🔧 Troubleshooting:")
        print("1. Check your IT Glue API key is valid")
        print("2. Verify database connection settings")
        print("3. Ensure you have network connectivity")
        print("4. Check the logs above for specific errors")


if __name__ == "__main__":
    asyncio.run(main())