#!/usr/bin/env python3
"""Test script to find documents in the 'software' folder for Faucets Limited."""

import asyncio
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

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


async def test_software_folder_documents():
    """Test finding documents in the software folder."""
    
    logger.info("Testing software folder document discovery for Faucets Limited")
    
    try:
        # Create a mock client that simulates the IT Glue API behavior
        mock_client = AsyncMock(spec=ITGlueClient)
        
        # Mock organization lookup
        mock_org = MagicMock()
        mock_org.id = "3183713165639879"
        mock_org.name = "Faucets Limited"
        mock_client.get_organizations = AsyncMock(return_value=[mock_org])
        
        # Simulate different document scenarios
        # Root documents (what you currently see)
        root_documents = [
            {"id": "doc1", "name": "Disaster Recovery Plan", "document_folder_id": None},
            {"id": "doc2", "name": "Faucets Company Overview", "document_folder_id": None},
            {"id": "doc3", "name": "IT Infrastructure Documentation", "document_folder_id": None},
            {"id": "doc4", "name": "Security Policies and Compliance", "document_folder_id": None},
            {"id": "doc5", "name": "Standard Operating Procedures", "document_folder_id": None}
        ]
        
        # Documents in the software folder (what we're looking for)
        software_folder_documents = [
            {"id": "doc6", "name": "Software License Agreement", "document_folder_id": "folder_software_123"},
            {"id": "doc7", "name": "Software Installation Guide", "document_folder_id": "folder_software_123"}
        ]
        
        # All documents combined
        all_documents = root_documents + software_folder_documents
        
        # Create handler with mock client
        handler = DocumentsHandler(mock_client)
        
        # Test 1: Current behavior - root documents only
        logger.info("=== Test 1: Root documents only (current behavior) ===")
        mock_client.get_documents = AsyncMock(return_value=[
            MagicMock(**doc) for doc in root_documents
        ])
        
        result = await handler.list_all_documents(organization="Faucets Limited")
        
        if result.get("success"):
            docs = result.get("documents", [])
            logger.info(f"✅ Found {len(docs)} root documents")
            for doc in docs:
                logger.info(f"   - {doc['name']} (folder_id: {doc.get('document_folder_id', 'None')})")
        
        # Verify the correct API call was made
        mock_client.get_documents.assert_called_with(
            org_id="3183713165639879",
            include_folders=False,
            folder_id=None
        )
        
        # Test 2: Include all documents (root + folders)
        logger.info("\n=== Test 2: All documents including folders ===")
        mock_client.get_documents = AsyncMock(return_value=[
            MagicMock(**doc) for doc in all_documents
        ])
        
        result = await handler.list_all_documents(
            organization="Faucets Limited",
            include_folders=True
        )
        
        if result.get("success"):
            docs = result.get("documents", [])
            logger.info(f"✅ Found {len(docs)} total documents")
            
            root_docs = [d for d in docs if not d.get("document_folder_id")]
            folder_docs = [d for d in docs if d.get("document_folder_id")]
            
            logger.info(f"   📁 Root documents: {len(root_docs)}")
            logger.info(f"   📂 Documents in folders: {len(folder_docs)}")
            
            if folder_docs:
                logger.info("   📂 Folder documents found:")
                for doc in folder_docs:
                    logger.info(f"      - {doc['name']} (folder_id: {doc.get('document_folder_id')})")
        
        # Verify the correct API call was made
        mock_client.get_documents.assert_called_with(
            org_id="3183713165639879",
            include_folders=True,
            folder_id=None
        )
        
        # Test 3: Documents in specific software folder
        logger.info("\n=== Test 3: Documents in software folder specifically ===")
        mock_client.get_documents = AsyncMock(return_value=[
            MagicMock(**doc) for doc in software_folder_documents
        ])
        
        result = await handler.list_all_documents(
            organization="Faucets Limited",
            folder_id="folder_software_123"
        )
        
        if result.get("success"):
            docs = result.get("documents", [])
            logger.info(f"✅ Found {len(docs)} documents in software folder")
            for doc in docs:
                logger.info(f"   - {doc['name']} (folder_id: {doc.get('document_folder_id')})")
        
        # Verify the correct API call was made
        mock_client.get_documents.assert_called_with(
            org_id="3183713165639879",
            include_folders=False,
            folder_id="folder_software_123"
        )
        
        # Test 4: Show the actual API filters that would be used
        logger.info("\n=== Test 4: API Filter Construction ===")
        
        client = ITGlueClient()
        mock_get_all_pages = AsyncMock(return_value=[])
        client.get_all_pages = mock_get_all_pages
        
        # Test the actual filter construction for different scenarios
        scenarios = [
            ("Root only", {"include_folders": False}, "filter[document_folder_id]=null"),
            ("Include folders", {"include_folders": True}, "filter[document_folder_id]=!=null"),
            ("Specific folder", {"folder_id": "software_123"}, "filter[document_folder_id]=software_123")
        ]
        
        for desc, params, expected_filter in scenarios:
            mock_get_all_pages.reset_mock()
            await client.get_documents(org_id="3183713165639879", **params)
            
            call_args = mock_get_all_pages.call_args
            actual_params = call_args[0][1]  # Second argument is params
            actual_filter = actual_params.get("filter[document_folder_id]")
            
            logger.info(f"   {desc}: {expected_filter}")
            logger.info(f"      Actual filter sent: filter[document_folder_id]={actual_filter}")
            
        logger.info("\n🎯 Key Points for IT Glue Testing:")
        logger.info("   1. Use include_folders=True to see documents in folders")
        logger.info("   2. Use folder_id='<folder_id>' to see specific folder contents")
        logger.info("   3. Default behavior shows only root documents")
        logger.info("   4. API filters: null (root), !=null (all), <id> (specific)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


async def main():
    """Run the test."""
    success = await test_software_folder_documents()
    if success:
        logger.info("✅ Software folder document tests completed!")
        return 0
    else:
        logger.error("❌ Software folder document tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)