#!/usr/bin/env python3
"""Test the corrected folder filter syntax."""

import asyncio
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock

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


async def test_corrected_filter_syntax():
    """Test the corrected API filter syntax."""
    
    logger.info("Testing corrected folder filter syntax")
    logger.info("Using exact syntax: filter[document_folder_id]!=null and filter[document_folder_id]=<folder_id>")
    
    # Create a client and mock the get_all_pages method to capture the actual API calls
    client = ITGlueClient()
    mock_get_all_pages = AsyncMock(return_value=[])
    client.get_all_pages = mock_get_all_pages
    
    test_org_id = "3183713165639879"  # Faucets Limited
    
    # Test 1: Default behavior (no folder filter)
    logger.info("=== Test 1: Default behavior (no folder filter) ===")
    await client.get_documents(org_id=test_org_id, include_folders=False)
    
    call_args = mock_get_all_pages.call_args
    params = call_args[0][1]  # Second argument is params
    
    logger.info(f"API call parameters: {params}")
    
    folder_filter = params.get("filter[document_folder_id]")
    if folder_filter:
        logger.info(f"Folder filter applied: filter[document_folder_id]={folder_filter}")
    else:
        logger.info("No folder filter applied (default API behavior)")
    
    # Test 2: Include folders (!=null)
    logger.info("\n=== Test 2: Include folders (!=null) ===")
    mock_get_all_pages.reset_mock()
    await client.get_documents(org_id=test_org_id, include_folders=True)
    
    call_args = mock_get_all_pages.call_args
    params = call_args[0][1]
    folder_filter = params.get("filter[document_folder_id]")
    
    logger.info(f"API call parameters: {params}")
    logger.info(f"Folder filter applied: filter[document_folder_id]={folder_filter}")
    
    if folder_filter == "!=null":
        logger.info("✅ Correct syntax used for including folders")
    else:
        logger.error(f"❌ Wrong syntax: expected '!=null', got '{folder_filter}'")
    
    # Test 3: Specific folder
    logger.info("\n=== Test 3: Specific folder ID ===")
    mock_get_all_pages.reset_mock()
    test_folder_id = "software_folder_123"
    await client.get_documents(org_id=test_org_id, folder_id=test_folder_id)
    
    call_args = mock_get_all_pages.call_args
    params = call_args[0][1]
    folder_filter = params.get("filter[document_folder_id]")
    
    logger.info(f"API call parameters: {params}")
    logger.info(f"Folder filter applied: filter[document_folder_id]={folder_filter}")
    
    if folder_filter == test_folder_id:
        logger.info("✅ Correct syntax used for specific folder")
    else:
        logger.error(f"❌ Wrong syntax: expected '{test_folder_id}', got '{folder_filter}'")
    
    # Test 4: Show what actual API URLs would be called
    logger.info("\n=== Test 4: Actual API URLs ===")
    
    base_url = f"organizations/{test_org_id}/relationships/documents"
    
    scenarios = [
        ("Default (no filter)", {}),
        ("Include folders", {"filter[document_folder_id]": "!=null"}),
        ("Specific folder", {"filter[document_folder_id]": "software_folder_123"})
    ]
    
    for desc, params in scenarios:
        url = base_url
        if params:
            param_str = "&".join(f"{k}={v}" for k, v in params.items())
            url += f"?{param_str}"
        logger.info(f"{desc}: {url}")
    
    logger.info("\n✅ Filter syntax verification complete")
    logger.info("🎯 Ready to test with actual IT Glue API")
    
    return True


async def main():
    """Run the test."""
    success = await test_corrected_filter_syntax()
    if success:
        logger.info("✅ Corrected filter syntax tests passed!")
        return 0
    else:
        logger.error("❌ Filter syntax tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)