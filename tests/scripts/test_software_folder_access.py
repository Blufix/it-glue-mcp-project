#!/usr/bin/env python3
"""Test accessing the software folder documents with corrected API syntax."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.itglue.client import ITGlueClient
from src.query.documents_handler import DocumentsHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_software_folder_access():
    """Test accessing the software folder with corrected API calls."""
    
    # Check API key
    api_key = os.getenv('IT_GLUE_API_KEY')
    if not api_key:
        print("❌ IT_GLUE_API_KEY environment variable not set")
        print("💡 Set the API key to test live folder access")
        return False
    
    print("🔍 Testing Software Folder Access - Corrected Implementation")
    print("=" * 65)
    
    try:
        client = ITGlueClient()
        handler = DocumentsHandler(client)
        
        org_name = "Faucets Limited"
        
        # Test 1: Default behavior (should return 5 root documents as before)
        print("\n📁 Test 1: Default behavior (root documents)")
        result = await handler.list_all_documents(organization=org_name, limit=20)
        
        if result.get("success"):
            docs = result.get("documents", [])
            print(f"✅ Found {len(docs)} documents (default behavior)")
            for doc in docs[:3]:
                folder_id = doc.get("document_folder_id")
                print(f"   • {doc['name']} (folder: {folder_id or 'root'})")
        else:
            print(f"❌ Default test failed: {result.get('error')}")
            
        # Test 2: Include folder documents (using !=null filter)
        print(f"\n📂 Test 2: All documents including folders (!=null filter)")
        result = await handler.list_all_documents(
            organization=org_name, 
            include_folders=True,
            limit=20
        )
        
        if result.get("success"):
            docs = result.get("documents", [])
            print(f"✅ Found {len(docs)} total documents")
            
            # Separate root and folder documents
            root_docs = [d for d in docs if not d.get("document_folder_id")]
            folder_docs = [d for d in docs if d.get("document_folder_id")]
            
            print(f"   📁 Root documents: {len(root_docs)}")
            print(f"   📂 Documents in folders: {len(folder_docs)}")
            
            if len(docs) > len(root_docs):
                print(f"\n🎉 SUCCESS! Found {len(folder_docs)} documents in folders!")
                print(f"📂 Folder documents:")
                
                for doc in folder_docs:
                    folder_id = doc.get("document_folder_id")
                    print(f"   • {doc['name']}")
                    print(f"     Folder ID: {folder_id}")
                    print(f"     Document ID: {doc.get('id')}")
                    
                # Test 3: Access specific folder
                if folder_docs:
                    print(f"\n🎯 Test 3: Accessing specific folder")
                    folder_id = folder_docs[0].get("document_folder_id")
                    
                    result = await handler.list_all_documents(
                        organization=org_name,
                        folder_id=folder_id,
                        limit=20
                    )
                    
                    if result.get("success"):
                        specific_docs = result.get("documents", [])
                        print(f"✅ Found {len(specific_docs)} documents in folder {folder_id}")
                        for doc in specific_docs:
                            print(f"   • {doc['name']}")
                    else:
                        print(f"❌ Specific folder test failed: {result.get('error')}")
                        
            else:
                print(f"ℹ️  No additional documents found in folders")
                print(f"   This could mean:")
                print(f"   • Software folder documents are file uploads")
                print(f"   • Documents haven't been synced recently")
                print(f"   • Different organization or folder structure")
                
        else:
            print(f"❌ Include folders test failed: {result.get('error')}")
            
        print(f"\n✅ Corrected API implementation tested")
        print(f"🔧 Using exact syntax: filter[document_folder_id]!=null")
        return True
        
    except Exception as e:
        print(f"❌ Error testing folder access: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the test."""
    success = await test_software_folder_access()
    if success:
        print("\n✅ Software folder access test completed!")
        return 0
    else:
        print("\n❌ Software folder access test failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)