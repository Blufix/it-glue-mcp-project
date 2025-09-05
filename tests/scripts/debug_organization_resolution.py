#!/usr/bin/env python3
"""
Debug script to test organization name resolution.

This script tests the organization resolution logic that has been failing
in the Query and Search tools, specifically for "Faucets" organization.
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


async def debug_organization_resolution():
    """Debug organization name resolution."""
    print("=== Organization Resolution Debug ===\n")
    
    try:
        # Initialize IT Glue client
        api_key = os.getenv('ITGLUE_API_KEY') or os.getenv('IT_GLUE_API_KEY')
        if not api_key:
            print("❌ ERROR: ITGLUE_API_KEY or IT_GLUE_API_KEY environment variable not set")
            return
            
        print("✅ IT Glue API key found")
        
        # Create client and query engine
        itglue_client = ITGlueClient(api_key=api_key)
        cache_manager = CacheManager()
        query_engine = QueryEngine(itglue_client=itglue_client, cache=cache_manager)
        
        print("✅ QueryEngine initialized\n")
        
        # Test 1: Direct organization listing
        print("📋 Test 1: List all organizations")
        print("-" * 40)
        orgs = await itglue_client.get_organizations()
        print(f"Total organizations found: {len(orgs)}")
        
        for i, org in enumerate(orgs[:10], 1):  # Show first 10
            org_id = org.id if hasattr(org, 'id') else org.get('id', 'unknown')
            org_name = org.name if hasattr(org, 'name') else org.get('name', 'unknown')
            print(f"  {i}. ID: {org_id}, Name: '{org_name}'")
        
        if len(orgs) > 10:
            print(f"  ... and {len(orgs) - 10} more organizations")
            
        print()
        
        # Test 2: Search for "Faucets" specifically  
        print("🔍 Test 2: Search for 'Faucets' organization")
        print("-" * 40)
        
        # Search with filters
        faucets_orgs = await itglue_client.get_organizations(filters={"name": "Faucets"})
        print(f"Organizations matching 'Faucets' filter: {len(faucets_orgs)}")
        
        for org in faucets_orgs:
            org_id = org.id if hasattr(org, 'id') else org.get('id', 'unknown')
            org_name = org.name if hasattr(org, 'name') else org.get('name', 'unknown')
            print(f"  - ID: {org_id}, Name: '{org_name}'")
        print()
        
        # Test 3: Manual fuzzy search in all organizations
        print("🔍 Test 3: Manual fuzzy search for 'Faucets'")
        print("-" * 40)
        
        query_term = "faucets"
        matches = []
        
        for org in orgs:
            org_id = org.id if hasattr(org, 'id') else org.get('id', 'unknown')
            org_name = org.name if hasattr(org, 'name') else org.get('name', 'unknown')
            
            if org_name and isinstance(org_name, str):
                # Exact match
                if org_name.lower() == query_term.lower():
                    matches.append(('exact', org_id, org_name))
                # Contains match
                elif query_term.lower() in org_name.lower():
                    matches.append(('contains', org_id, org_name))
                # Reverse contains (for partial matches)
                elif org_name.lower() in query_term.lower():
                    matches.append(('reverse', org_id, org_name))
        
        print(f"Manual search results for '{query_term}':")
        if matches:
            for match_type, org_id, org_name in matches:
                print(f"  [{match_type:8}] ID: {org_id}, Name: '{org_name}'")
        else:
            print("  No matches found")
        print()
        
        # Test 4: Test QueryEngine resolution method
        print("🧪 Test 4: Test QueryEngine._resolve_company_to_id")
        print("-" * 50)
        
        test_names = ["Faucets", "faucets", "FAUCETS"]
        
        for test_name in test_names:
            print(f"Testing resolution for: '{test_name}'")
            resolved_id = await query_engine._resolve_company_to_id(test_name)
            
            if resolved_id:
                print(f"  ✅ Resolved to ID: {resolved_id}")
            else:
                print(f"  ❌ Failed to resolve")
        print()
        
        # Test 5: Show potential organization name variations
        print("💡 Test 5: Show organization names that might be related")
        print("-" * 55)
        
        potential_matches = []
        for org in orgs:
            org_name = org.name if hasattr(org, 'name') else org.get('name', 'unknown')
            if org_name and isinstance(org_name, str):
                name_lower = org_name.lower()
                # Look for names containing partial matches
                if any(term in name_lower for term in ['faucet', 'tap', 'water', 'valve']):
                    org_id = org.id if hasattr(org, 'id') else org.get('id', 'unknown')
                    potential_matches.append((org_id, org_name))
        
        if potential_matches:
            print("Organizations that might be related:")
            for org_id, org_name in potential_matches[:5]:
                print(f"  - ID: {org_id}, Name: '{org_name}'")
        else:
            print("No potentially related organizations found")
            
        print("\n=== Debug Complete ===")
        
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_organization_resolution())