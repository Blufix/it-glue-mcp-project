#!/usr/bin/env python3
"""Search all Faucets documents for O365/Microsoft 365 content."""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import db_manager
from sqlalchemy import text


async def search_all_documents():
    """Search all Faucets documents for O365/Microsoft content."""
    print("🔍 Searching All Faucets Documents for O365/Microsoft Content")
    print("=" * 80)
    
    try:
        # Initialize database
        await db_manager.initialize()
        
        async with db_manager.get_session() as session:
            # Get all documents for Faucets
            result = await session.execute(text("""
                SELECT id, name, attributes->>'content' as content, 
                       search_text, length(attributes->>'content') as content_length
                FROM itglue_entities 
                WHERE organization_id = '3183713165639879' 
                AND entity_type = 'document'
                ORDER BY name
            """))
            
            docs = result.fetchall()
            
            print(f"📚 Found {len(docs)} documents to analyze\n")
            
            # O365 and Microsoft keywords to search for
            o365_keywords = [
                'office 365', 'o365', 'microsoft 365', 'm365',
                'conditional access', 'azure ad', 'azure active directory',
                'sharepoint', 'onedrive', 'teams', 'outlook', 'exchange',
                'intune', 'defender', 'security center',
                'tenant', 'subscription', 'license'
            ]
            
            documents_with_o365 = []
            
            for doc in docs:
                print(f"📄 Analyzing: {doc.name}")
                print(f"   Length: {doc.content_length} characters")
                
                content = (doc.content or "").lower()
                search_text = (doc.search_text or "").lower()
                
                # Check both content and search_text
                found_keywords = []
                keyword_contexts = {}
                
                for keyword in o365_keywords:
                    if keyword in content or keyword in search_text:
                        found_keywords.append(keyword)
                        
                        # Get context from content if available
                        if keyword in content and doc.content:
                            pos = content.find(keyword)
                            context_start = max(0, pos - 50)
                            context_end = min(len(doc.content), pos + len(keyword) + 100)
                            context = doc.content[context_start:context_end].strip()
                            keyword_contexts[keyword] = context
                
                if found_keywords:
                    print(f"   ✅ FOUND O365 keywords: {', '.join(found_keywords)}")
                    documents_with_o365.append({
                        'name': doc.name,
                        'keywords': found_keywords,
                        'contexts': keyword_contexts,
                        'content_length': doc.content_length
                    })
                    
                    # Show contexts
                    for keyword, context in keyword_contexts.items():
                        print(f"      '{keyword}': ...{context}...")
                else:
                    print("   ❌ No O365 keywords found")
                
                print()
            
            # Summary
            print("=" * 80)
            print("📊 SEARCH SUMMARY")
            print("=" * 80)
            
            if documents_with_o365:
                print(f"✅ Found O365 content in {len(documents_with_o365)} documents:")
                for doc_info in documents_with_o365:
                    print(f"   • {doc_info['name']}: {', '.join(doc_info['keywords'])}")
            else:
                print("❌ No O365/Microsoft 365 content found in any documents")
                print("\n💡 This explains why the RAG query about O365 conditional access")
                print("   policies returned low confidence - there is no specific O365")
                print("   configuration information in the Faucets documentation.")
            
            print(f"\n📈 Analysis complete: {len(docs)} documents searched")
            
    except Exception as e:
        print(f"❌ Document search failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(search_all_documents())