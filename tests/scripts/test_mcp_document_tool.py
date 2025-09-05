#!/usr/bin/env python3
"""Test the MCP document tool with folder functionality."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.mcp.tools.query_documents_tool import QueryDocumentsTool
from src.services.itglue.client import ITGlueClient
from src.query.documents_handler import DocumentsHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_mcp_document_tool():
    """Test MCP document tool with folder actions."""
    
    # Check API key
    api_key = os.getenv('IT_GLUE_API_KEY') or os.getenv('ITGLUE_API_KEY')
    if not api_key:
        print("❌ API key not set")
        return False
    
    print("🔍 Testing MCP Document Tool with Folders")
    print("=" * 50)
    
    try:
        # Initialize components
        client = ITGlueClient()
        handler = DocumentsHandler(client)
        tool = QueryDocumentsTool(handler)
        
        org_name = "Faucets Limited"
        
        # Test 1: Default document listing (should show 4 root documents)
        print(f"\n📁 Test 1: Default document listing")
        result = await tool.query_documents(
            action="list_all",
            organization=org_name,
            limit=20
        )
        
        if result.get("success"):
            docs = result.get("documents", [])
            count = result.get("count", 0)
            print(f"✅ Found {count} documents")
            for doc in docs[:5]:
                print(f"  📄 {doc.get('name', 'Unknown')}")
        else:
            print(f"❌ Test 1 failed: {result.get('error')}")
        
        # Test 2: Try folder action (even though API might not support it)
        print(f"\n📂 Test 2: Folder document listing")
        result = await tool.query_documents(
            action="folders", 
            organization=org_name,
            limit=20
        )
        
        if result.get("success"):
            docs = result.get("documents", [])
            count = result.get("count", 0)
            print(f"✅ Found {count} documents with folder action")
            for doc in docs[:5]:
                folder_id = doc.get("document_folder_id", "root")
                print(f"  📄 {doc.get('name', 'Unknown')} (folder: {folder_id})")
        else:
            print(f"❌ Test 2 failed: {result.get('error')}")
        
        # Test 3: Try with_folders action
        print(f"\n📂 Test 3: With folders action")
        result = await tool.query_documents(
            action="with_folders",
            organization=org_name,
            limit=20
        )
        
        if result.get("success"):
            docs = result.get("documents", [])
            count = result.get("count", 0)
            print(f"✅ Found {count} documents with 'with_folders' action")
            for doc in docs[:5]:
                folder_id = doc.get("document_folder_id", "root")
                print(f"  📄 {doc.get('name', 'Unknown')} (folder: {folder_id})")
        else:
            print(f"❌ Test 3 failed: {result.get('error')}")
            
        # Test 4: Direct handler test with include_folders
        print(f"\n🔧 Test 4: Direct handler with include_folders=True")
        result = await handler.list_all_documents(
            organization=org_name,
            include_folders=True,
            limit=20
        )
        
        if result.get("success"):
            docs = result.get("documents", [])
            count = len(docs)
            print(f"✅ Handler found {count} documents")
            
            # Analyze folder structure
            root_docs = [d for d in docs if not d.get("document_folder_id")]
            folder_docs = [d for d in docs if d.get("document_folder_id")]
            
            print(f"  📁 Root documents: {len(root_docs)}")
            print(f"  📂 Folder documents: {len(folder_docs)}")
            
            if folder_docs:
                print(f"  🎯 Documents in folders:")
                for doc in folder_docs:
                    print(f"    • {doc.get('name')} (folder: {doc.get('document_folder_id')})")
        else:
            print(f"❌ Test 4 failed: {result.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the test."""
    success = await test_mcp_document_tool()
    if success:
        print("\n✅ MCP document tool test completed!")
        return 0
    else:
        print("\n❌ MCP document tool test failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)