#!/usr/bin/env python3
"""List documents in Faucets Limited organization."""

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


async def list_faucets_documents():
    """List documents in the Faucets Limited organization."""
    
    # Check if IT Glue API key is available
    api_key = os.getenv('IT_GLUE_API_KEY')
    if not api_key:
        logger.error("IT_GLUE_API_KEY environment variable not set")
        return False

    logger.info("Listing documents in Faucets Limited organization")
    
    try:
        # Initialize components
        client = ITGlueClient()
        cache_manager = CacheManager()
        handler = DocumentsHandler(client, cache_manager)
        
        # List root documents only
        logger.info("=== Root Documents (not in folders) ===")
        result = await handler.list_all_documents(
            organization="Faucets Limited",
            limit=50
        )
        
        if result.get("success"):
            docs = result.get("documents", [])
            logger.info(f"Found {len(docs)} root documents")
            
            for i, doc in enumerate(docs, 1):
                name = doc.get("name", "Untitled")
                doc_id = doc.get("id")
                folder_id = doc.get("document_folder_id")
                created = doc.get("created_at", "Unknown")
                updated = doc.get("updated_at", "Unknown")
                
                print(f"\n{i}. {name}")
                print(f"   ID: {doc_id}")
                print(f"   Folder ID: {folder_id or 'None (root)'}")
                print(f"   Created: {created}")
                print(f"   Updated: {updated}")
                
                # Show content preview
                content = doc.get("content_preview", "")
                if content:
                    preview = content[:200].replace('\n', ' ')
                    print(f"   Preview: {preview}...")
        else:
            logger.error(f"❌ Failed to get root documents: {result.get('error')}")
            
        # List all documents including those in folders
        logger.info("\n=== All Documents (including those in folders) ===")
        result = await handler.list_all_documents(
            organization="Faucets Limited",
            include_folders=True,
            limit=50
        )
        
        if result.get("success"):
            docs = result.get("documents", [])
            logger.info(f"Found {len(docs)} total documents")
            
            # Separate root and folder documents
            root_docs = [d for d in docs if not d.get("document_folder_id")]
            folder_docs = [d for d in docs if d.get("document_folder_id")]
            
            print(f"\n📊 Summary:")
            print(f"   Root documents: {len(root_docs)}")
            print(f"   Documents in folders: {len(folder_docs)}")
            
            if folder_docs:
                print(f"\n📁 Documents in Folders:")
                for i, doc in enumerate(folder_docs, 1):
                    name = doc.get("name", "Untitled")
                    doc_id = doc.get("id")
                    folder_id = doc.get("document_folder_id")
                    
                    print(f"\n{i}. {name}")
                    print(f"   ID: {doc_id}")
                    print(f"   Folder ID: {folder_id}")
                    
                    # Show content preview
                    content = doc.get("content_preview", "")
                    if content:
                        preview = content[:200].replace('\n', ' ')
                        print(f"   Preview: {preview}...")
            else:
                print("\n📁 No documents found in folders")
                
        else:
            logger.error(f"❌ Failed to get all documents: {result.get('error')}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to list documents: {e}", exc_info=True)
        return False


async def main():
    """Run the document listing."""
    success = await list_faucets_documents()
    if success:
        logger.info("✅ Document listing completed!")
        return 0
    else:
        logger.error("❌ Document listing failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)