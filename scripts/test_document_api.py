#!/usr/bin/env python3
"""Test IT Glue document API directly to understand the issue."""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.itglue.client import ITGlueClient


async def test_document_api():
    """Test document API calls directly."""
    print("🔍 Testing IT Glue Document API")
    print("=" * 60)
    
    try:
        client = ITGlueClient()
        
        # Test 1: Get specific documents for Faucets Limited
        org_id = "3183713165639879"  # We know this from database
        print(f"📡 Testing documents for org {org_id}...")
        
        try:
            documents = await client.get_documents(filters={"organization_id": org_id})
            print(f"✅ API returned {len(documents)} documents")
            
            for i, doc in enumerate(documents, 1):
                print(f"\n📄 Document {i}: {doc.name}")
                print(f"   ID: {doc.id}")
                print(f"   Created: {getattr(doc, 'created_at', 'Unknown')}")
                
                # Try to get full document content
                try:
                    full_doc = await client.get_document(doc.id)
                    content = getattr(full_doc, 'content', None) or getattr(full_doc, 'body', None)
                    if content:
                        print(f"   Content: {len(content)} characters")
                        print(f"   Preview: {content[:150]}...")
                    else:
                        print("   Content: Not available or empty")
                        print(f"   Available attributes: {list(full_doc.__dict__.keys())}")
                        
                except Exception as e:
                    print(f"   ❌ Error getting full document: {e}")
                    
        except Exception as e:
            print(f"❌ Failed to get documents: {e}")
        
        # Test 2: Check if documents exist in other entity types
        print(f"\n🔍 Checking flexible assets for document-like content...")
        
        try:
            assets = await client.get_flexible_assets(filters={"organization_id": org_id})
            print(f"📦 Found {len(assets)} flexible assets")
            
            for asset in assets:
                if any(term in asset.name.lower() for term in ['policy', 'document', 'security', 'conditional', 'access']):
                    print(f"   📋 Potentially relevant: {asset.name}")
                    
        except Exception as e:
            print(f"❌ Failed to get flexible assets: {e}")
            
        # Test 3: Check configurations for O365 content
        print(f"\n🔍 Checking configurations for O365/Microsoft content...")
        
        try:
            configs = await client.get_configurations(filters={"organization_id": org_id})
            print(f"🖥️ Found {len(configs)} configurations")
            
            o365_configs = []
            for config in configs:
                if any(term in config.name.lower() for term in ['office', '365', 'o365', 'microsoft', 'azure', 'conditional']):
                    o365_configs.append(config)
                    
            if o365_configs:
                print(f"   ✅ Found {len(o365_configs)} O365-related configurations:")
                for config in o365_configs:
                    print(f"      • {config.name}")
            else:
                print("   ❌ No O365-related configurations found")
                    
        except Exception as e:
            print(f"❌ Failed to get configurations: {e}")
            
    except Exception as e:
        print(f"❌ API test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_document_api())