#!/usr/bin/env python3
"""Test discovering document folders through IT Glue API."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.itglue.client import ITGlueClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def discover_document_folders():
    """Discover available document folders."""
    
    # Check API key
    api_key = os.getenv('IT_GLUE_API_KEY') or os.getenv('ITGLUE_API_KEY')
    if not api_key:
        print("❌ API key not set")
        return False
    
    print("🔍 Discovering Document Folders")
    print("=" * 40)
    
    try:
        client = ITGlueClient()
        org_name = "Faucets Limited"
        
        # First get the organization ID
        orgs = await client.get_organizations(name=org_name)
        if not orgs:
            print(f"❌ Organization '{org_name}' not found")
            return False
            
        org_id = orgs[0]["id"]
        print(f"✅ Found organization: {org_name} (ID: {org_id})")
        
        # Try to get document folders endpoint
        try:
            print(f"\n📂 Attempting to fetch document folders...")
            
            # Try different endpoints to discover folders
            endpoints_to_try = [
                f"organizations/{org_id}/relationships/document_folders",
                f"document_folders?filter[organization_id]={org_id}",
                f"organizations/{org_id}/document_folders"
            ]
            
            for endpoint in endpoints_to_try:
                print(f"\n🔗 Trying endpoint: {endpoint}")
                try:
                    result = await client.get_all_pages(endpoint, {})
                    print(f"✅ Success! Found {len(result)} items")
                    
                    if result:
                        for item in result:
                            print(f"  📁 Folder: {item.get('name', 'Unknown')} (ID: {item.get('id', 'Unknown')})")
                        
                        # If we found folders, try to get documents in the first folder
                        if result:
                            folder_id = result[0]["id"]
                            folder_name = result[0].get("name", "Unknown")
                            print(f"\n🎯 Testing documents in folder '{folder_name}' (ID: {folder_id})")
                            
                            docs = await client.get_documents(
                                org_id=org_id, 
                                folder_id=folder_id
                            )
                            print(f"✅ Found {len(docs)} documents in folder")
                            for doc in docs:
                                print(f"  📄 Document: {doc.get('name', 'Unknown')}")
                        
                        return True
                        
                except Exception as e:
                    print(f"❌ Failed: {e}")
                    continue
            
            print(f"\n⚠️  No document folder endpoints worked")
            
        except Exception as e:
            print(f"❌ Error fetching document folders: {e}")
            
        # Alternative: Try to get all documents and look for folder_id fields
        print(f"\n🔍 Alternative: Looking for folder_id in existing documents...")
        docs = await client.get_documents(org_id=org_id)
        
        folder_ids = set()
        for doc in docs:
            folder_id = doc.get("document_folder_id")
            if folder_id:
                folder_ids.add(folder_id)
                print(f"📄 Document '{doc.get('name')}' has folder_id: {folder_id}")
        
        if folder_ids:
            print(f"\n🎯 Found folder IDs: {list(folder_ids)}")
            
            # Test accessing documents by specific folder ID
            for folder_id in folder_ids:
                print(f"\n📂 Testing folder ID: {folder_id}")
                try:
                    folder_docs = await client.get_documents(
                        org_id=org_id,
                        folder_id=folder_id
                    )
                    print(f"✅ Found {len(folder_docs)} documents in folder {folder_id}")
                    for doc in folder_docs:
                        print(f"  📄 {doc.get('name', 'Unknown')}")
                except Exception as e:
                    print(f"❌ Error accessing folder {folder_id}: {e}")
        else:
            print("ℹ️  No documents have folder_id set")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the discovery."""
    success = await discover_document_folders()
    if success:
        print("\n✅ Document folder discovery completed!")
        return 0
    else:
        print("\n❌ Document folder discovery failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)