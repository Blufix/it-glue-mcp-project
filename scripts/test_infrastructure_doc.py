"""Test script to verify infrastructure documentation generation with organization name resolution."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.itglue import ITGlueClient
from src.cache import CacheManager
from src.data import db_manager
from src.infrastructure.documentation_handler import InfrastructureDocumentationHandler
from src.query.organizations_handler import OrganizationsHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_organization_resolution():
    """Test that we can resolve organization names to IDs."""
    
    print("\n" + "="*60)
    print("🔍 TESTING ORGANIZATION NAME RESOLUTION")
    print("="*60)
    
    try:
        # Initialize components
        await db_manager.initialize()
        
        itglue_client = ITGlueClient()
        cache_manager = CacheManager()
        await cache_manager.connect()
        
        # Create organizations handler
        org_handler = OrganizationsHandler(
            itglue_client=itglue_client,
            cache_manager=cache_manager
        )
        
        # Test 1: List all organizations
        print("\n📋 Fetching all organizations...")
        all_orgs = await org_handler.list_all_organizations(limit=10)
        
        if all_orgs.get('success'):
            print(f"✅ Found {all_orgs.get('count', 0)} organizations")
            
            # Display first few organizations  
            print("\nAvailable organizations:")
            orgs_data = all_orgs.get('data', [])
            if not orgs_data:
                orgs_data = all_orgs.get('organizations', [])
            
            for org in orgs_data[:10]:
                if isinstance(org, dict):
                    org_name = org.get('attributes', {}).get('name') if 'attributes' in org else org.get('name')
                    org_id = org.get('id')
                    if org_name:
                        print(f"   - {org_name} (ID: {org_id})")
        else:
            print(f"❌ Failed to list organizations: {all_orgs.get('error')}")
            return
        
        # Test 2: Try to find "bawso" or similar
        print("\n🔍 Searching for 'bawso' organization...")
        test_names = ['bawso', 'Bawso', 'BAWSO']
        
        found_org = None
        for name in test_names:
            result = await org_handler.find_organization(name, use_fuzzy=True)
            if result.get('success'):
                found_org = result.get('organization') or result.get('data')
                if found_org:
                    if isinstance(found_org, list) and len(found_org) > 0:
                        found_org = found_org[0]
                    print(f"✅ Found organization '{name}':")
                    print(f"   - Name: {found_org.get('name') or found_org.get('attributes', {}).get('name')}")
                    print(f"   - ID: {found_org.get('id')}")
                    print(f"   - Type: {found_org.get('type') or found_org.get('attributes', {}).get('organization-type-name')}")
                    break
        
        if not found_org:
            print("⚠️  'bawso' not found. Using first available organization for testing...")
            
            # Let's use the first organization for testing
            orgs_data = all_orgs.get('data', []) or all_orgs.get('organizations', [])
            if orgs_data:
                found_org = orgs_data[0]
                org_name = found_org.get('attributes', {}).get('name') if 'attributes' in found_org else found_org.get('name')
                print(f"\n📌 Using '{org_name}' (ID: {found_org.get('id')}) for testing instead")
        
        return found_org
        
    except Exception as e:
        print(f"❌ Error during organization resolution: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if 'cache_manager' in locals():
            await cache_manager.disconnect()


async def test_infrastructure_documentation(org_name_or_id: str):
    """Test infrastructure documentation generation."""
    
    print("\n" + "="*60)
    print("📚 TESTING INFRASTRUCTURE DOCUMENTATION GENERATION")
    print("="*60)
    print(f"Organization: {org_name_or_id}")
    print("-"*60)
    
    try:
        # Initialize components
        await db_manager.initialize()
        
        itglue_client = ITGlueClient()
        cache_manager = CacheManager()
        await cache_manager.connect()
        
        # Create handler
        handler = InfrastructureDocumentationHandler(
            itglue_client=itglue_client,
            cache_manager=cache_manager,
            db_manager=db_manager
        )
        
        # First resolve the organization name if needed
        org_id = None
        try:
            org_id = str(int(org_name_or_id))
            print(f"✅ Using organization ID: {org_id}")
        except ValueError:
            print(f"🔍 Resolving organization name: {org_name_or_id}")
            
            org_handler = OrganizationsHandler(
                itglue_client=itglue_client,
                cache_manager=cache_manager
            )
            
            result = await org_handler.find_organization(org_name_or_id, use_fuzzy=True)
            if result.get('success'):
                org_data = result.get('organization') or result.get('data')
                if org_data:
                    if isinstance(org_data, list) and len(org_data) > 0:
                        org_id = str(org_data[0].get('id'))
                        print(f"✅ Resolved to organization ID: {org_id}")
                    elif isinstance(org_data, dict):
                        org_id = str(org_data.get('id'))
                        print(f"✅ Resolved to organization ID: {org_id}")
            
            if not org_id:
                print(f"❌ Could not resolve organization: {org_name_or_id}")
                return
        
        # Generate documentation (without embeddings or upload for testing)
        print("\n⚙️  Starting documentation generation...")
        print("   - Querying IT Glue resources...")
        print("   - This may take 30-90 seconds depending on organization size")
        
        result = await handler.generate_infrastructure_documentation(
            organization_id=org_id,
            include_embeddings=False,  # Skip embeddings for faster testing
            upload_to_itglue=False      # Don't upload during testing
        )
        
        if result.get('success'):
            print("\n✅ Infrastructure documentation generated successfully!")
            print("\n📊 Statistics:")
            print(f"   - Snapshot ID: {result.get('snapshot_id')}")
            print(f"   - Organization: {result.get('organization', {}).get('name')}")
            print(f"   - Total Resources: {result.get('statistics', {}).get('total_resources', 0)}")
            
            stats = result.get('statistics', {})
            for key, value in stats.items():
                if key != 'total_resources':
                    print(f"   - {key.replace('_', ' ').title()}: {value}")
            
            print(f"\n⏱️  Duration: {result.get('duration_seconds', 0):.2f} seconds")
            print(f"📄 Document Size: {result.get('document', {}).get('size_bytes', 0):,} bytes")
            
            # Save the markdown document to a file
            if result.get('document', {}).get('content'):
                org_name_safe = result.get('organization', {}).get('name', 'unknown').replace(' ', '_').replace('/', '_')
                filename = f"infrastructure_doc_{org_name_safe}.md"
                with open(filename, 'w') as f:
                    f.write(result.get('document', {}).get('content', ''))
                print(f"\n📝 Document saved to: {filename}")
            
            # Check database for the snapshot
            print("\n🔍 Verifying database record...")
            async with db_manager.acquire() as conn:
                snapshot = await conn.fetchrow(
                    "SELECT * FROM infrastructure_snapshots WHERE id = $1",
                    result.get('snapshot_id')
                )
                if snapshot:
                    print(f"✅ Snapshot record found in database")
                    print(f"   - Status: {snapshot['status']}")
                    print(f"   - Resource Count: {snapshot['resource_count']}")
        else:
            print(f"\n❌ Documentation generation failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error during documentation generation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'cache_manager' in locals():
            await cache_manager.disconnect()
        await db_manager.close()


async def main():
    """Main test function."""
    
    print("\n" + "🚀 IT GLUE MCP SERVER - INFRASTRUCTURE DOCUMENTATION TEST")
    print("="*60)
    
    # Test 1: Organization resolution
    org = await test_organization_resolution()
    
    if org:
        # Test 2: Try with organization name
        org_name = org.get('attributes', {}).get('name') if 'attributes' in org else org.get('name')
        if org_name:
            print(f"\n💡 Testing with organization name: '{org_name}'")
            await test_infrastructure_documentation(org_name)
        
        # Could also test with ID
        # org_id = org.get('id')
        # if org_id:
        #     print(f"\n💡 Testing with organization ID: {org_id}")
        #     await test_infrastructure_documentation(str(org_id))
    else:
        print("\n⚠️  No organization found for testing")
        print("Please ensure:")
        print("1. IT Glue API credentials are configured in .env")
        print("2. The API key has access to at least one organization")
        print("3. The database is running and accessible")


if __name__ == "__main__":
    asyncio.run(main())