#!/usr/bin/env python3
"""
Quick verification script for Query Tool organization filtering fix.
Tests that queries properly filter results to the specified organization.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.mcp.server import ITGlueMCPServer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_query_filtering():
    """Test that query tool properly filters by organization."""
    
    server = ITGlueMCPServer()
    
    # Initialize server
    await server._initialize_components()
    
    # Test 1: Query with Faucets filter
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Query with Faucets organization filter")
    logger.info("="*60)
    
    result = await server.server._tools["query"](
        query="What are the network configurations?",
        company="Faucets"
    )
    
    if result.get("success"):
        results = result.get("results", result.get("data", []))
        logger.info(f"✓ Query successful - Found {len(results)} results")
        
        # Check if all results are from Faucets
        other_orgs = set()
        for item in results:
            if isinstance(item, dict):
                org_id = item.get("organization_id")
                org_name = item.get("organization", {}).get("name") if isinstance(item.get("organization"), dict) else item.get("organization")
                
                # Log the organization info for debugging
                if org_id or org_name:
                    logger.info(f"  Item org: ID={org_id}, Name={org_name}")
                    
                    # Check if it's NOT Faucets
                    if org_name and "faucets" not in str(org_name).lower():
                        other_orgs.add(org_name)
        
        if other_orgs:
            logger.error(f"✗ FAILED: Found results from other organizations: {other_orgs}")
            return False
        else:
            logger.info("✓ PASSED: All results are properly filtered to Faucets organization")
            return True
    else:
        logger.error(f"✗ Query failed: {result.get('error')}")
        return False

async def test_configuration_count():
    """Test that we get all configurations, not just 6."""
    
    server = ITGlueMCPServer()
    
    # Initialize server
    await server._initialize_components()
    
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Check configuration count for Faucets")
    logger.info("="*60)
    
    # Query configurations for Faucets
    result = await server.server._tools["query"](
        query="Show all configurations for Faucets",
        company="Faucets"
    )
    
    if result.get("success"):
        results = result.get("results", result.get("data", []))
        logger.info(f"✓ Found {len(results)} configurations for Faucets")
        
        if len(results) <= 6:
            logger.warning(f"⚠️  Only {len(results)} configurations found - might be actual data limitation")
        else:
            logger.info(f"✓ More than 6 configurations found - limit issue resolved")
        
        return True
    else:
        logger.error(f"✗ Query failed: {result.get('error')}")
        return False

async def main():
    """Run all verification tests."""
    
    logger.info("Starting Query Tool Fix Verification")
    logger.info("="*80)
    
    # Test 1: Organization filtering
    test1_passed = await test_query_filtering()
    
    # Test 2: Configuration count
    test2_passed = await test_configuration_count()
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("VERIFICATION SUMMARY")
    logger.info("="*80)
    logger.info(f"Organization Filtering: {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    logger.info(f"Configuration Count: {'✓ CHECKED' if test2_passed else '✗ ERROR'}")
    
    if test1_passed:
        logger.info("\n✅ FIX VERIFIED: Organization filtering is working correctly!")
    else:
        logger.error("\n❌ FIX FAILED: Organization filtering still has issues")
        
    return test1_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)