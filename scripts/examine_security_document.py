#!/usr/bin/env python3
"""Examine the full Security Policies document to understand O365 content."""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import db_manager
from sqlalchemy import text


async def examine_security_document():
    """Examine the complete Security Policies document content."""
    print("🔍 Full Security Policies Document Analysis")
    print("=" * 80)
    
    try:
        # Initialize database
        await db_manager.initialize()
        
        async with db_manager.get_session() as session:
            # Get the security document
            result = await session.execute(text("""
                SELECT name, attributes->>'content' as content, 
                       search_text, length(attributes->>'content') as content_length
                FROM itglue_entities 
                WHERE organization_id = '3183713165639879' 
                AND entity_type = 'document' 
                AND name ILIKE '%security%'
                LIMIT 1
            """))
            
            doc = result.fetchone()
            
            if doc:
                print(f"📄 Document: {doc.name}")
                print(f"📏 Content Length: {doc.content_length} characters")
                print(f"🔍 Search Text Length: {len(doc.search_text) if doc.search_text else 0} characters")
                print("-" * 80)
                
                content = doc.content or ""
                
                # Split into sections for analysis
                print("📋 FULL DOCUMENT CONTENT:")
                print("=" * 80)
                print(content)
                print("=" * 80)
                
                # Analyze for O365 keywords with context
                o365_keywords = [
                    'office 365', 'o365', 'microsoft 365', 'm365',
                    'conditional access', 'azure ad', 'azure active directory',
                    'multifactor', 'mfa', 'multi-factor authentication',
                    'sharepoint', 'onedrive', 'teams', 'outlook',
                    'intune', 'compliance', 'dlp', 'data loss prevention'
                ]
                
                print("\n🔎 KEYWORD ANALYSIS:")
                print("-" * 40)
                
                content_lower = content.lower()
                found_keywords = []
                
                for keyword in o365_keywords:
                    if keyword in content_lower:
                        found_keywords.append(keyword)
                        # Find all occurrences with context
                        start = 0
                        occurrences = []
                        while True:
                            pos = content_lower.find(keyword, start)
                            if pos == -1:
                                break
                            # Get surrounding context (50 chars before and after)
                            context_start = max(0, pos - 50)
                            context_end = min(len(content), pos + len(keyword) + 50)
                            context = content[context_start:context_end].strip()
                            occurrences.append(context)
                            start = pos + 1
                        
                        print(f"\n✅ Found '{keyword}' ({len(occurrences)} times):")
                        for i, context in enumerate(occurrences, 1):
                            print(f"   {i}. ...{context}...")
                
                if not found_keywords:
                    print("❌ No Microsoft 365 / O365 keywords found")
                    
                    # Check for generic security terms that might be relevant
                    generic_terms = [
                        'access control', 'authentication', 'authorization',
                        'password policy', 'user access', 'permissions',
                        'security policy', 'compliance', 'audit'
                    ]
                    
                    print("\n🔍 GENERIC SECURITY TERMS:")
                    print("-" * 30)
                    
                    for term in generic_terms:
                        if term in content_lower:
                            print(f"✅ Found: {term}")
                        else:
                            print(f"❌ Not found: {term}")
                
                # Check the search_text field specifically
                if doc.search_text:
                    print(f"\n📝 SEARCH TEXT FIELD ({len(doc.search_text)} chars):")
                    print("-" * 50)
                    print(doc.search_text[:1000] + "..." if len(doc.search_text) > 1000 else doc.search_text)
                
            else:
                print("❌ No security policy document found")
                
                # List all documents to see what we have
                result = await session.execute(text("""
                    SELECT name, entity_type, length(attributes->>'content') as content_length
                    FROM itglue_entities 
                    WHERE organization_id = '3183713165639879' 
                    AND entity_type = 'document'
                    ORDER BY name
                """))
                
                docs = result.fetchall()
                print(f"\n📚 Available documents ({len(docs)}):")
                for doc in docs:
                    print(f"  - {doc.name} ({doc.content_length} chars)")
        
    except Exception as e:
        print(f"❌ Document analysis failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(examine_security_document())