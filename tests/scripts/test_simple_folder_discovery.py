#!/usr/bin/env python3
"""Simple test to discover document folder structure."""

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


async def simple_folder_test():
    """Simple test to understand folder structure."""
    
    # Check API key
    api_key = os.getenv('IT_GLUE_API_KEY') or os.getenv('ITGLUE_API_KEY')
    if not api_key:
        print("❌ API key not set")
        return False
    
    print("🔍 Simple Folder Discovery Test")
    print("=" * 40)
    
    try:
        client = ITGlueClient()
        
        # Get organizations with filter
        orgs = await client.get_organizations(
            filters={"name": "Faucets Limited"}
        )
        
        if not orgs:
            print("❌ No organizations found")
            return False
            
        org = orgs[0]
        org_id = org.id
        print(f"✅ Organization: {org.name} (ID: {org_id})")
        
        # Get all documents and examine their folder properties
        print(f"\n📄 Getting all documents...")
        docs = await client.get_documents(org_id=org_id)
        
        print(f"✅ Found {len(docs)} total documents")
        
        # Analyze document structure
        root_docs = []
        folder_docs = []
        folder_ids = set()
        
        for doc in docs:
            folder_id = getattr(doc, 'document_folder_id', None)
            
            if folder_id:
                folder_docs.append(doc)
                folder_ids.add(folder_id)
                print(f"  📁 Folder Document: '{doc.name}' (folder_id: {folder_id})")
            else:
                root_docs.append(doc)
                print(f"  📄 Root Document: '{doc.name}'")
        
        print(f"\n📊 Summary:")
        print(f"  • Root documents: {len(root_docs)}")
        print(f"  • Folder documents: {len(folder_docs)}")
        print(f"  • Unique folder IDs: {len(folder_ids)}")
        
        if folder_ids:
            print(f"\n🎯 Testing access to specific folders...")
            for folder_id in folder_ids:
                try:
                    print(f"\n📂 Testing folder ID: {folder_id}")
                    folder_docs = await client.get_documents(
                        org_id=org_id,
                        folder_id=folder_id
                    )
                    print(f"✅ Folder {folder_id} contains {len(folder_docs)} documents:")
                    for doc in folder_docs:
                        print(f"  • {doc.name}")
                        
                except Exception as e:
                    print(f"❌ Error accessing folder {folder_id}: {e}")
        
        # Verify the expected counts
        print(f"\n🔍 Validation:")
        if len(root_docs) == 4:
            print(f"✅ Root documents: {len(root_docs)} (matches expected)")
        else:
            print(f"⚠️  Root documents: {len(root_docs)} (expected 4)")
            
        if len(folder_docs) == 3:
            print(f"✅ Folder documents: {len(folder_docs)} (matches expected)")
        elif len(folder_docs) > 0:
            print(f"⚠️  Folder documents: {len(folder_docs)} (expected 3)")
        else:
            print(f"❌ No folder documents found (expected 3)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the test."""
    success = await simple_folder_test()
    if success:
        print("\n✅ Simple folder discovery completed!")
        return 0
    else:
        print("\n❌ Simple folder discovery failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)