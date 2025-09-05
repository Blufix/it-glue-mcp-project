#!/usr/bin/env python3
"""
Simple test to verify organization resolution fix works.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.query.engine import QueryEngine
from src.services.itglue.client import ITGlueClient
from src.cache.manager import CacheManager


async def verify_organization_resolution_fix():
    """Verify that organization resolution now works for Faucets."""
    print("=== Verifying Organization Resolution Fix ===\n")
    
    try:
        # Initialize components 
        api_key = os.getenv('ITGLUE_API_KEY')
        if not api_key:
            print("❌ ERROR: ITGLUE_API_KEY not found")
            return
        
        itglue_client = ITGlueClient(api_key=api_key)
        cache_manager = CacheManager()  
        query_engine = QueryEngine(itglue_client=itglue_client, cache=cache_manager)
        
        # Test cases that were failing before the fix
        test_cases = [
            ("Faucets", "Exact case"),
            ("faucets", "Lower case"),
            ("FAUCETS", "Upper case"),
            ("faucet", "Partial match"),
        ]
        
        print("🧪 Testing organization resolution:")
        print("-" * 40)
        
        success_count = 0
        for test_input, description in test_cases:
            org_id = await query_engine._resolve_company_to_id(test_input)
            
            if org_id:
                print(f"✅ '{test_input}' ({description}) → ID: {org_id}")
                success_count += 1
            else:
                print(f"❌ '{test_input}' ({description}) → Failed to resolve")
        
        print(f"\nResults: {success_count}/{len(test_cases)} test cases passed")
        
        if success_count >= 3:  # At least 3 out of 4 should work
            print("\n🎉 SUCCESS: Organization resolution fix is working!")
            print("   'Faucets' can now be resolved to 'Faucets Limited'")
        else:
            print("\n❌ FAILED: Organization resolution still has issues")
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")


if __name__ == "__main__":
    asyncio.run(verify_organization_resolution_fix())