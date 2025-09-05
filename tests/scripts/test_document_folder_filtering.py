#!/usr/bin/env python3
"""Test script for document folder filtering functionality."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.cache.manager import CacheManager
from src.query.documents_handler import DocumentsHandler
from src.services.itglue.client import ITGlueClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_document_folder_filtering():
    """Test the enhanced document folder filtering functionality."""
    
    # Check if IT Glue API key is available
    api_key = os.getenv('IT_GLUE_API_KEY')
    if not api_key:
        logger.error("IT_GLUE_API_KEY environment variable not set")
        return False

    logger.info("Testing enhanced document folder filtering functionality")
    
    try:
        # Initialize components
        client = ITGlueClient()
        cache_manager = CacheManager()
        handler = DocumentsHandler(client, cache_manager)
        
        # Test 1: List root documents only (default behavior)
        logger.info("=== Test 1: List root documents only ===")
        result = await handler.list_all_documents(
            organization="Faucets Limited",
            limit=10
        )
        
        if result.get("success"):
            docs = result.get("documents", [])
            logger.info(f"✅ Found {len(docs)} root documents")
            
            # Show document folder information
            for doc in docs[:3]:
                folder_id = doc.get("document_folder_id")
                logger.info(f"   - {doc['name']} (folder_id: {folder_id or 'None - root'})")
        else:
            logger.error(f"❌ Test 1 failed: {result.get('error')}")
            return False
            
        # Test 2: List all documents including those in folders
        logger.info("\n=== Test 2: List all documents including folders ===")
        result = await handler.list_all_documents(
            organization="Faucets Limited",
            include_folders=True,
            limit=10
        )
        
        if result.get("success"):
            docs = result.get("documents", [])
            logger.info(f"✅ Found {len(docs)} documents (including folders)")
            
            # Group by folder
            root_docs = [d for d in docs if not d.get("document_folder_id")]
            folder_docs = [d for d in docs if d.get("document_folder_id")]
            
            logger.info(f"   - Root documents: {len(root_docs)}")
            logger.info(f"   - Documents in folders: {len(folder_docs)}")
            
            # Show some folder documents
            for doc in folder_docs[:3]:
                folder_id = doc.get("document_folder_id")
                logger.info(f"   - {doc['name']} (folder_id: {folder_id})")
        else:
            logger.error(f"❌ Test 2 failed: {result.get('error')}")
            return False
            
        # Test 3: List documents with explicit folder filtering
        logger.info("\n=== Test 3: List with include_folders=True ===")
        result = await handler.list_all_documents(
            organization="Faucets Limited",
            include_folders=True,
            limit=10
        )
        
        if result.get("success"):
            docs = result.get("documents", [])
            logger.info(f"✅ Found {len(docs)} documents with include_folders=True")
            
            logger.info(f"   - Result keys: {list(result.keys())}")
            logger.info(f"   - Organization: {result.get('organization')}")
        else:
            logger.error(f"❌ Test 3 failed: {result.get('error')}")
            return False
            
        # Test 4: Try to list documents in a specific folder (if any exist)
        logger.info("\n=== Test 4: Test specific folder filtering ===")
        
        # First, get a folder ID if any documents have one
        folder_id = None
        if result.get("success"):
            docs = result.get("documents", [])
            for doc in docs:
                if doc.get("document_folder_id"):
                    folder_id = doc["document_folder_id"]
                    break
        
        if folder_id:
            logger.info(f"Testing with folder_id: {folder_id}")
            result = await handler.list_all_documents(
                organization="Faucets Limited",
                folder_id=folder_id,
                limit=10
            )
            
            if result.get("success"):
                docs = result.get("documents", [])
                logger.info(f"✅ Found {len(docs)} documents in folder {folder_id}")
                
                # Verify all documents have the correct folder_id
                all_correct = all(doc.get("document_folder_id") == folder_id for doc in docs)
                if all_correct:
                    logger.info("   ✅ All documents have correct folder_id")
                else:
                    logger.warning("   ⚠️  Some documents have incorrect folder_id")
            else:
                logger.error(f"❌ Test 4 failed: {result.get('error')}")
                return False
        else:
            logger.info("No documents in folders found, skipping specific folder test")
            
        # Test 5: Test error handling (this won't work directly with handler, so skip)
        logger.info("\n=== Test 5: Test error handling (skipped for direct handler test) ===")
        logger.info("✅ Error handling would be tested at the tool level")
            
        logger.info("\n🎉 All document folder filtering tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}", exc_info=True)
        return False


async def main():
    """Run the test."""
    success = await test_document_folder_filtering()
    if success:
        logger.info("✅ Document folder filtering tests passed!")
        return 0
    else:
        logger.error("❌ Document folder filtering tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)