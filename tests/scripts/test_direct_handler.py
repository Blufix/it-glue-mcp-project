#!/usr/bin/env python3
"""Test the documents handler directly."""

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


async def test_direct_handler():
    """Test documents handler directly."""
    
    # Check API key
    api_key = os.getenv('IT_GLUE_API_KEY') or os.getenv('ITGLUE_API_KEY')
    if not api_key:
        print("❌ API key not set")
        return False
    
    print("🔍 Testing Documents Handler Directly")
    print("=" * 45)
    
    try:
        # Initialize components
        client = ITGlueClient()
        handler = DocumentsHandler(client)
        
        org_name = "Faucets Limited"
        
        # Test 1: Normal document listing
        print(f"\n📁 Test 1: Normal document listing")
        result = await handler.list_all_documents(
            organization=org_name,
            limit=20
        )
        
        if result.get("success"):
            docs = result.get("documents", [])
            print(f"✅ Found {len(docs)} documents (normal)")
            for doc in docs:
                print(f"  📄 {doc.get('name')}")
        else:
            print(f"❌ Normal listing failed: {result.get('error')}")
        
        # Test 2: With include_folders=True 
        print(f"\n📂 Test 2: With include_folders=True")
        result = await handler.list_all_documents(
            organization=org_name,
            include_folders=True,
            limit=20
        )
        
        if result.get("success"):
            docs = result.get("documents", [])
            print(f"✅ Found {len(docs)} documents (with folders)")
            
            root_count = 0
            folder_count = 0
            
            for doc in docs:
                folder_id = doc.get("document_folder_id")
                name = doc.get('name')
                if folder_id:
                    folder_count += 1
                    print(f"  📂 {name} (folder: {folder_id})")
                else:
                    root_count += 1
                    print(f"  📄 {name} (root)")
            
            print(f"\n📊 Summary:")
            print(f"  • Root documents: {root_count}")
            print(f"  • Folder documents: {folder_count}")
            print(f"  • Total: {len(docs)}")
            
        else:
            print(f"❌ Include folders failed: {result.get('error')}")
        
        # Test 3: Try with a fake folder_id to see what happens
        print(f"\n🎯 Test 3: Test with specific folder_id")
        result = await handler.list_all_documents(
            organization=org_name,
            folder_id="123456",  # Fake folder ID
            limit=20
        )
        
        if result.get("success"):
            docs = result.get("documents", [])
            print(f"✅ Found {len(docs)} documents in fake folder")
        else:
            print(f"❌ Fake folder test failed: {result.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the test."""
    success = await test_direct_handler()
    if success:
        print("\n✅ Direct handler test completed!")
        return 0
    else:
        print("\n❌ Direct handler test failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)