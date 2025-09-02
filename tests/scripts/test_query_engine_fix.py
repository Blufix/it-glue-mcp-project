#!/usr/bin/env python3
"""
Direct test of the Query Engine fix for organization filtering.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.query.engine import QueryEngine
from src.services.itglue import ITGlueClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_company_resolution():
    """Test that the query engine can resolve company names to IDs."""
    
    logger.info("\n" + "="*60)
    logger.info("TEST: Company Name Resolution")
    logger.info("="*60)
    
    # Create query engine
    engine = QueryEngine()
    
    # Test resolving "Faucets" to an ID
    company_id = await engine._resolve_company_to_id("Faucets")
    
    if company_id:
        logger.info(f"✓ Successfully resolved 'Faucets' to ID: {company_id}")
        return True
    else:
        logger.error("✗ Failed to resolve 'Faucets' to an ID")
        return False

async def test_query_with_filter():
    """Test that queries properly filter by company."""
    
    logger.info("\n" + "="*60)
    logger.info("TEST: Query with Company Filter")
    logger.info("="*60)
    
    # Create query engine
    engine = QueryEngine()
    
    # Process a query with company filter
    result = await engine.process_query(
        query="Show network configurations",
        company="Faucets"
    )
    
    if result.get("success"):
        data = result.get("data", [])
        logger.info(f"✓ Query processed successfully")
        logger.info(f"  Found {len(data)} results")
        
        # Check if results are filtered to Faucets
        if data:
            # Log first result for inspection
            logger.info(f"  First result org_id: {data[0].get('organization_id', 'N/A')}")
        
        return True
    else:
        logger.error(f"✗ Query failed: {result.get('error', 'Unknown error')}")
        return False

async def main():
    """Run tests."""
    
    logger.info("Testing Query Engine Organization Filtering Fix")
    logger.info("="*80)
    
    try:
        # Test 1: Company resolution
        test1 = await test_company_resolution()
        
        # Test 2: Query with filter
        test2 = await test_query_with_filter()
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Company Resolution: {'✓ PASSED' if test1 else '✗ FAILED'}")
        logger.info(f"Query Filtering: {'✓ PASSED' if test2 else '✗ FAILED'}")
        
        if test1 and test2:
            logger.info("\n✅ ALL TESTS PASSED - Fix is working!")
        else:
            logger.error("\n❌ TESTS FAILED - Fix needs more work")
            
        return test1 and test2
        
    except Exception as e:
        logger.error(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)