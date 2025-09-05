#!/usr/bin/env python3
"""Search for specific conditional access policy information in Faucets database."""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import db_manager
from sqlalchemy import text


async def search_conditional_access_policies():
    """Search for the specific conditional access policies mentioned by user."""
    print("🔍 Searching for Conditional Access Policies in Faucets Database")
    print("=" * 80)
    
    # Policy names from user's document
    policy_names = [
        "Block legacy authentication",
        "CA03 Block Windows 10 Devices", 
        "CA05-Require-MFA- Guest-Access",
        "CA06-Require-MDM-Devices-Compliant-ZT",
        "CA07-UK-Sign-In-Restriction",
        "Require multifactor authentication for admins",
        "Require multifactor authentication for all users",
        "Require multifactor authentication for Azure management"
    ]
    
    # Microsoft Graph and conditional access terms
    search_terms = [
        "microsoft.graph.conditionalAccessPolicy",
        "conditional access",
        "azure management",
        "Windows Azure Service Management API",
        "multifactor authentication",
        "legacy authentication",
        "guest access",
        "MDM devices",
        "sign-in restriction"
    ]
    
    try:
        await db_manager.initialize()
        
        async with db_manager.get_session() as session:
            print("📋 Searching for specific policy names...")
            print("-" * 50)
            
            # Search for exact policy names
            found_policies = []
            for policy_name in policy_names:
                result = await session.execute(text("""
                    SELECT name, entity_type, attributes->>'content' as content, search_text
                    FROM itglue_entities 
                    WHERE organization_id = '3183713165639879'
                    AND (
                        LOWER(name) LIKE :policy_pattern OR
                        LOWER(search_text) LIKE :policy_pattern OR
                        LOWER(attributes->>'content') LIKE :policy_pattern
                    )
                """), {"policy_pattern": f"%{policy_name.lower()}%"})
                
                matches = result.fetchall()
                if matches:
                    found_policies.extend(matches)
                    print(f"✅ Found references to: {policy_name}")
                    for match in matches:
                        print(f"   📄 {match.name} ({match.entity_type})")
                else:
                    print(f"❌ Not found: {policy_name}")
            
            print(f"\n📋 Searching for Microsoft Graph/Conditional Access terms...")
            print("-" * 50)
            
            # Search for conditional access terms
            found_terms = []
            for term in search_terms:
                result = await session.execute(text("""
                    SELECT name, entity_type, 
                           CASE 
                               WHEN LOWER(name) LIKE :term_pattern THEN 'name'
                               WHEN LOWER(search_text) LIKE :term_pattern THEN 'search_text' 
                               WHEN LOWER(attributes->>'content') LIKE :term_pattern THEN 'content'
                           END as found_in
                    FROM itglue_entities 
                    WHERE organization_id = '3183713165639879'
                    AND (
                        LOWER(name) LIKE :term_pattern OR
                        LOWER(search_text) LIKE :term_pattern OR
                        LOWER(attributes->>'content') LIKE :term_pattern
                    )
                    LIMIT 5
                """), {"term_pattern": f"%{term.lower()}%"})
                
                matches = result.fetchall()
                if matches:
                    found_terms.append((term, matches))
                    print(f"✅ Found '{term}' in {len(matches)} items:")
                    for match in matches:
                        print(f"   📄 {match.name} ({match.entity_type}) - found in {match.found_in}")
                else:
                    print(f"❌ Not found: {term}")
            
            # Check if there are any documents that might contain this type of data
            print(f"\n📋 Checking for any Azure/Microsoft configuration documents...")
            print("-" * 50)
            
            result = await session.execute(text("""
                SELECT name, entity_type, length(attributes->>'content') as content_length,
                       CASE 
                           WHEN LOWER(name) LIKE '%azure%' THEN 'azure'
                           WHEN LOWER(name) LIKE '%office%' THEN 'office'
                           WHEN LOWER(name) LIKE '%microsoft%' THEN 'microsoft'
                           WHEN LOWER(name) LIKE '%365%' THEN '365'
                           WHEN LOWER(name) LIKE '%conditional%' THEN 'conditional'
                           WHEN LOWER(name) LIKE '%policy%' THEN 'policy'
                           ELSE 'other'
                       END as match_type
                FROM itglue_entities 
                WHERE organization_id = '3183713165639879'
                AND (
                    LOWER(name) LIKE '%azure%' OR
                    LOWER(name) LIKE '%office%' OR
                    LOWER(name) LIKE '%microsoft%' OR
                    LOWER(name) LIKE '%365%' OR
                    LOWER(name) LIKE '%conditional%' OR
                    LOWER(name) LIKE '%policy%'
                )
                ORDER BY match_type, name
            """))
            
            azure_docs = result.fetchall()
            if azure_docs:
                print(f"✅ Found {len(azure_docs)} Azure/Microsoft related items:")
                for doc in azure_docs:
                    print(f"   📄 {doc.name} ({doc.entity_type}) - {doc.content_length} chars - matched: {doc.match_type}")
            else:
                print("❌ No Azure/Microsoft/Policy related items found")
            
            # Summary
            print("\n" + "=" * 80)
            print("📊 SEARCH RESULTS SUMMARY")
            print("=" * 80)
            
            if found_policies:
                print(f"✅ Found {len(found_policies)} items matching specific policy names")
            else:
                print("❌ No specific conditional access policy names found")
            
            if found_terms:
                total_term_matches = sum(len(matches) for _, matches in found_terms)
                print(f"✅ Found {len(found_terms)} different terms in {total_term_matches} total items")
            else:
                print("❌ No conditional access terminology found")
            
            if azure_docs:
                print(f"✅ Found {len(azure_docs)} Azure/Microsoft related items")
            else:
                print("❌ No Azure/Microsoft items found")
            
            print(f"\n💡 CONCLUSION:")
            if not found_policies and not found_terms and not azure_docs:
                print("❌ The conditional access policies you provided are NOT in the database.")
                print("   This confirms why the RAG query failed - this specific O365")
                print("   conditional access configuration data has not been synced to IT Glue.")
            else:
                print("✅ Some related content found - investigating further...")
                
    except Exception as e:
        print(f"❌ Search failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(search_conditional_access_policies())