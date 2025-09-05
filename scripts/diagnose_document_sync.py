#!/usr/bin/env python3
"""Diagnose document sync issues by comparing API vs Database."""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.itglue.client import ITGlueClient
from src.data import db_manager
from sqlalchemy import text


async def diagnose_document_sync():
    """Compare documents from IT Glue API vs what's in our database."""
    print("🔍 Document Sync Diagnosis: API vs Database")
    print("=" * 80)
    
    try:
        # Step 1: Get documents from IT Glue API
        print("📡 Step 1: Fetching documents from IT Glue API...")
        client = ITGlueClient()
        
        # Find Faucets organization first
        orgs = await client.get_organizations(filters={"name": "Faucets Limited"})
        if not orgs:
            print("❌ Faucets organization not found")
            return
            
        faucets_org = orgs[0]
        org_id = faucets_org.id
        print(f"✅ Found Faucets: {faucets_org.name} (ID: {org_id})")
        
        # Get documents from API
        api_documents = await client.get_documents(filters={"organization_id": org_id})
        print(f"📄 API returned {len(api_documents)} documents")
        
        # Show API documents
        if api_documents:
            print("\n📋 Documents from IT Glue API:")
            print("-" * 50)
            for i, doc in enumerate(api_documents, 1):
                print(f"  {i}. {doc.name} (ID: {doc.id})")
                if hasattr(doc, 'content') and doc.content:
                    content_preview = doc.content[:100] + "..." if len(doc.content) > 100 else doc.content
                    print(f"     Content: {content_preview}")
                else:
                    print(f"     Content: No content or content not loaded")
                print(f"     Created: {getattr(doc, 'created_at', 'Unknown')}")
                print(f"     Updated: {getattr(doc, 'updated_at', 'Unknown')}")
                print()
        
        # Step 2: Get documents from our database
        print("📊 Step 2: Checking documents in our database...")
        await db_manager.initialize()
        
        async with db_manager.get_session() as session:
            result = await session.execute(text("""
                SELECT itglue_id, name, attributes, last_synced,
                       length(attributes->>'content') as content_length,
                       attributes->>'created-at' as created_at,
                       attributes->>'updated-at' as updated_at
                FROM itglue_entities 
                WHERE organization_id = :org_id 
                AND entity_type = 'document'
                ORDER BY name
            """), {"org_id": str(org_id)})
            
            db_documents = result.fetchall()
            print(f"🗄️ Database has {len(db_documents)} documents")
            
            if db_documents:
                print("\n📋 Documents in our database:")
                print("-" * 50)
                for i, doc in enumerate(db_documents, 1):
                    print(f"  {i}. {doc.name} (ITG ID: {doc.itglue_id})")
                    print(f"     Content Length: {doc.content_length} chars")
                    print(f"     Last Synced: {doc.last_synced}")
                    print(f"     Created: {doc.created_at}")
                    print(f"     Updated: {doc.updated_at}")
                    print()
        
        # Step 3: Compare and identify gaps
        print("🔍 Step 3: Comparing API vs Database...")
        print("-" * 50)
        
        api_ids = {str(doc.id) for doc in api_documents}
        db_ids = {doc.itglue_id for doc in db_documents}
        
        missing_from_db = api_ids - db_ids
        missing_from_api = db_ids - api_ids
        
        print(f"📊 Comparison Results:")
        print(f"   API documents: {len(api_documents)}")
        print(f"   DB documents: {len(db_documents)}")
        print(f"   Missing from DB: {len(missing_from_db)}")
        print(f"   Extra in DB: {len(missing_from_api)}")
        
        if missing_from_db:
            print(f"\n❌ Documents in API but NOT in database:")
            for api_doc in api_documents:
                if str(api_doc.id) in missing_from_db:
                    print(f"   • {api_doc.name} (ID: {api_doc.id})")
        
        if missing_from_api:
            print(f"\n⚠️ Documents in database but NOT in current API response:")
            for db_doc in db_documents:
                if db_doc.itglue_id in missing_from_api:
                    print(f"   • {db_doc.name} (ID: {db_doc.itglue_id})")
        
        # Step 4: Check document content extraction
        print(f"\n📄 Step 4: Document Content Analysis...")
        print("-" * 50)
        
        if api_documents:
            sample_doc = api_documents[0]
            print(f"📋 Analyzing sample document: {sample_doc.name}")
            
            # Check if we have full document details
            print(f"   API Attributes available: {list(sample_doc.__dict__.keys())}")
            
            # Try to get full document details
            try:
                full_doc = await client.get_document(sample_doc.id)
                print(f"   ✅ Full document retrieved")
                print(f"   Content available: {'Yes' if hasattr(full_doc, 'content') and full_doc.content else 'No'}")
                if hasattr(full_doc, 'content') and full_doc.content:
                    print(f"   Content length: {len(full_doc.content)} characters")
                    print(f"   Content preview: {full_doc.content[:200]}...")
                
            except Exception as e:
                print(f"   ❌ Failed to get full document: {e}")
        
        # Step 5: Check specific O365 content
        print(f"\n🔍 Step 5: Looking for O365/Conditional Access content...")
        print("-" * 50)
        
        o365_found = False
        for doc in api_documents:
            try:
                # Get full document to check content
                full_doc = await client.get_document(doc.id)
                if hasattr(full_doc, 'content') and full_doc.content:
                    content_lower = full_doc.content.lower()
                    if any(term in content_lower for term in ['conditional access', 'o365', 'office 365', 'azure ad']):
                        print(f"   ✅ Found O365 content in: {doc.name}")
                        o365_found = True
                    else:
                        print(f"   ❌ No O365 content in: {doc.name}")
                else:
                    print(f"   ⚠️ No content available for: {doc.name}")
            except Exception as e:
                print(f"   ❌ Error checking {doc.name}: {e}")
        
        if not o365_found:
            print(f"\n💡 CONCLUSION: No O365/Conditional Access content found in any documents")
            print(f"   This means the conditional access policies are likely NOT stored")
            print(f"   as IT Glue documents, but might be:")
            print(f"   • In a different system (Azure Portal)")
            print(f"   • As configurations or flexible assets")
            print(f"   • Not documented in IT Glue at all")
        
    except Exception as e:
        print(f"❌ Diagnosis failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(diagnose_document_sync())