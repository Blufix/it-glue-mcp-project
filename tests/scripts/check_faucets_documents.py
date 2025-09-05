#!/usr/bin/env python3
"""Check for Faucets documents in the database and IT Glue API."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.config.settings import settings
from src.data import db_manager
from sqlalchemy import text
import aiohttp


async def check_faucets_documents():
    """Check for Faucets documents in database and API."""
    
    print("=" * 80)
    print("FAUCETS DOCUMENTS CHECK")
    print("=" * 80)
    
    await db_manager.initialize()
    
    # 1. Check database for existing documents
    print("\n📊 DATABASE CHECK")
    print("-" * 40)
    
    async with db_manager.get_session() as session:
        # Get Faucets organization ID
        result = await session.execute(text("""
            SELECT itglue_id, name
            FROM itglue_entities
            WHERE entity_type = 'organization'
            AND name LIKE '%Faucet%'
        """))
        
        org_row = result.first()
        if not org_row:
            print("❌ Faucets organization not found in database")
            return
        
        org_id = org_row.itglue_id
        org_name = org_row.name
        print(f"Found organization: {org_name}")
        print(f"Organization ID: {org_id}")
        
        # Check for documents
        result = await session.execute(text("""
            SELECT itglue_id, name, entity_type, attributes
            FROM itglue_entities
            WHERE organization_id = :org_id
            AND entity_type = 'document'
        """), {"org_id": org_id})
        
        docs = result.fetchall()
        print(f"\nDocuments in database: {len(docs)}")
        for doc in docs:
            print(f"  - {doc.name} (ID: {doc.itglue_id})")
    
    # 2. Check IT Glue API for documents
    print("\n🌐 IT GLUE API CHECK")
    print("-" * 40)
    
    headers = {
        "x-api-key": settings.itglue_api_key,
        "Content-Type": "application/vnd.api+json"
    }
    
    # Try to fetch documents from API
    async with aiohttp.ClientSession(headers=headers) as session:
        # First try the standard documents endpoint
        url = f"{settings.itglue_api_url}/organizations/{org_id}/relationships/documents"
        
        print(f"Checking: {url}")
        
        try:
            async with session.get(url) as response:
                print(f"Response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    docs = data.get('data', [])
                    print(f"\nDocuments found via relationships: {len(docs)}")
                    for doc in docs[:5]:
                        print(f"  - ID: {doc.get('id')}")
                else:
                    error_text = await response.text()
                    print(f"Error: {error_text[:200]}")
        except Exception as e:
            print(f"Request failed: {e}")
        
        # Try alternative endpoints
        print("\n🔍 Trying alternative document endpoints...")
        
        # Try knowledge base articles
        url = f"{settings.itglue_api_url}/knowledge_base_articles"
        params = {
            "filter[organization_id]": org_id,
            "page[size]": 10
        }
        
        print(f"Checking knowledge base articles...")
        
        try:
            async with session.get(url, params=params) as response:
                print(f"Response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    articles = data.get('data', [])
                    print(f"Knowledge base articles found: {len(articles)}")
                    for article in articles[:5]:
                        attrs = article.get('attributes', {})
                        print(f"  - {attrs.get('name', 'Unnamed')} (ID: {article.get('id')})")
                        print(f"    Subject: {attrs.get('subject', 'N/A')}")
                else:
                    print(f"Knowledge base endpoint not available")
        except Exception as e:
            print(f"Request failed: {e}")
        
        # Try documents directly with filter
        url = f"{settings.itglue_api_url}/documents"
        params = {
            "filter[organization_id]": org_id,
            "page[size]": 10
        }
        
        print(f"\nChecking documents with filter...")
        
        try:
            async with session.get(url, params=params) as response:
                print(f"Response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    docs = data.get('data', [])
                    print(f"Documents found: {len(docs)}")
                    for doc in docs[:5]:
                        attrs = doc.get('attributes', {})
                        print(f"  - {attrs.get('name', 'Unnamed')} (ID: {doc.get('id')})")
                else:
                    print(f"Documents endpoint not available with this filter")
        except Exception as e:
            print(f"Request failed: {e}")
    
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print("""
Based on the API responses:
1. Documents may not be available via the standard API
2. They might be stored as Knowledge Base Articles
3. Or they might require different permissions/endpoints

To add your 5 markdown documents:
1. We can import them directly into the database
2. Generate embeddings for semantic search
3. Create graph relationships
4. Make them searchable through the unified interface

Would you like to proceed with direct import of your markdown files?
""")


if __name__ == "__main__":
    asyncio.run(check_faucets_documents())