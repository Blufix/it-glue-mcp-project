#!/usr/bin/env python3
"""Unit test for document folder filtering parameters."""

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


async def test_folder_parameter_passing():
    """Test that folder parameters are correctly passed to the IT Glue client."""
    
    logger.info("Testing document folder parameter passing")
    
    # Create a mock client
    mock_client = AsyncMock(spec=ITGlueClient)
    mock_client.get_documents = AsyncMock(return_value=[])
    mock_client.get_organizations = AsyncMock(return_value=[
        MagicMock(id="123", name="Test Org")
    ])
    
    # Create handler with mock client
    handler = DocumentsHandler(mock_client)
    
    # Test 1: Default behavior (root documents only)
    logger.info("=== Test 1: Default behavior (root only) ===")
    await handler.list_all_documents(organization="Test Org")
    
    # Check that get_documents was called with correct parameters
    mock_client.get_documents.assert_called_with(
        org_id="123",
        include_folders=False,
        folder_id=None
    )
    logger.info("✅ Default parameters passed correctly")
    
    # Test 2: Include folders
    logger.info("=== Test 2: Include folders ===")
    mock_client.get_documents.reset_mock()
    await handler.list_all_documents(
        organization="Test Org",
        include_folders=True
    )
    
    mock_client.get_documents.assert_called_with(
        org_id="123",
        include_folders=True,
        folder_id=None
    )
    logger.info("✅ Include folders parameter passed correctly")
    
    # Test 3: Specific folder ID
    logger.info("=== Test 3: Specific folder ID ===")
    mock_client.get_documents.reset_mock()
    await handler.list_all_documents(
        organization="Test Org",
        folder_id="folder123"
    )
    
    mock_client.get_documents.assert_called_with(
        org_id="123",
        include_folders=False,
        folder_id="folder123"
    )
    logger.info("✅ Folder ID parameter passed correctly")
    
    # Test 4: Client get_documents with different filter combinations
    logger.info("=== Test 4: Client filter construction ===")
    
    # Create a real client instance to test parameter construction
    client = ITGlueClient()
    
    # Mock the get_all_pages method to capture parameters
    mock_get_all_pages = AsyncMock(return_value=[])
    client.get_all_pages = mock_get_all_pages
    
    # Test root documents only
    await client.get_documents(org_id="123", include_folders=False)
    
    # Check that the correct filter was applied
    call_args = mock_get_all_pages.call_args
    params = call_args[0][1]  # Second argument is params
    assert params["filter[document_folder_id]"] == "null"
    logger.info("✅ Root documents filter constructed correctly")
    
    # Test include folders
    mock_get_all_pages.reset_mock()
    await client.get_documents(org_id="123", include_folders=True)
    
    call_args = mock_get_all_pages.call_args
    params = call_args[0][1]
    assert params["filter[document_folder_id]"] == "!=null"
    logger.info("✅ Include folders filter constructed correctly")
    
    # Test specific folder
    mock_get_all_pages.reset_mock()
    await client.get_documents(org_id="123", folder_id="folder456")
    
    call_args = mock_get_all_pages.call_args
    params = call_args[0][1]
    assert params["filter[document_folder_id]"] == "folder456"
    logger.info("✅ Specific folder filter constructed correctly")
    
    logger.info("\n🎉 All parameter passing tests completed successfully!")
    return True


async def main():
    """Run the test."""
    try:
        success = await test_folder_parameter_passing()
        if success:
            logger.info("✅ Document folder parameter tests passed!")
            return 0
        else:
            logger.error("❌ Document folder parameter tests failed!")
            return 1
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)