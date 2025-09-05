#!/usr/bin/env python3
"""Exhaustive test of all possible folder document access methods."""

import asyncio
import logging
import os
import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.itglue.client import ITGlueClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_all_document_endpoints():
    """Test every possible way to access document folders."""
    
    # Check API key
    api_key = os.getenv('IT_GLUE_API_KEY') or os.getenv('ITGLUE_API_KEY')
    if not api_key:
        print("❌ API key not set")
        return False
    
    print("🔍 EXHAUSTIVE Document Folder Discovery")
    print("=" * 60)
    
    try:
        client = ITGlueClient()
        
        # Get organization
        orgs = await client.get_organizations(filters={"name": "Faucets Limited"})
        if not orgs:
            print("❌ No organizations found")
            return False
            
        org = orgs[0]
        org_id = org.id
        print(f"✅ Organization: {org.name} (ID: {org_id})")
        
        # Test 1: Standard documents endpoint variations
        document_endpoints = [
            f"organizations/{org_id}/relationships/documents",
            f"organizations/{org_id}/documents", 
            f"documents?filter[organization_id]={org_id}",
            f"documents"
        ]
        
        print(f"\n📄 Testing Document Endpoints:")
        for endpoint in document_endpoints:
            try:
                print(f"\n🔗 Testing: {endpoint}")
                result = await client.get_all_pages(endpoint, {})
                print(f"✅ Success: {len(result)} items")
                
                if result and len(result) > 0:
                    sample = result[0]
                    print(f"  Sample fields: {list(sample.keys())}")
                    if hasattr(sample, 'document_folder_id') or 'document_folder_id' in sample:
                        print(f"  📁 Has folder_id field!")
                        
            except Exception as e:
                print(f"❌ Failed: {str(e)[:100]}")
        
        # Test 2: Document folder specific endpoints
        folder_endpoints = [
            f"organizations/{org_id}/relationships/document_folders",
            f"organizations/{org_id}/document_folders",
            f"document_folders?filter[organization_id]={org_id}",
            f"document_folders",
            f"folders?filter[organization_id]={org_id}",
            f"folders"
        ]
        
        print(f"\n📂 Testing Document Folder Endpoints:")
        for endpoint in folder_endpoints:
            try:
                print(f"\n🔗 Testing: {endpoint}")
                result = await client.get_all_pages(endpoint, {})
                print(f"✅ Success: {len(result)} folders")
                
                if result and len(result) > 0:
                    for folder in result[:3]:
                        folder_id = folder.get('id', 'Unknown')
                        folder_name = folder.get('name', 'Unknown')
                        print(f"  📁 Folder: '{folder_name}' (ID: {folder_id})")
                        
                        # Test documents in this folder
                        try:
                            folder_docs = await client.get_documents(org_id=org_id, folder_id=folder_id)
                            print(f"    📄 Contains {len(folder_docs)} documents")
                            for doc in folder_docs[:2]:
                                print(f"      • {doc.get('name', 'Unknown')}")
                        except Exception as e:
                            print(f"    ❌ Error accessing folder docs: {str(e)[:50]}")
                        
            except Exception as e:
                print(f"❌ Failed: {str(e)[:100]}")
        
        # Test 3: Different filter approaches on documents
        filter_tests = [
            {"filter[document_folder_id]": "null"},
            {"filter[document_folder_id][eq]": "null"},
            {"filter[document_folder_id][ne]": "null"},
            {"filter[document_folder_id][not_null]": "true"},
            {"filter[document_folder_id][present]": "true"},
            {"include": "document_folder"},
            {"include": "folder"},
            {"include": "document_folders"},
            {"expand": "document_folder"},
            {"with": "folder"}
        ]
        
        print(f"\n🎯 Testing Document Filters:")
        for filters in filter_tests:
            try:
                print(f"\n🔧 Filter: {filters}")
                endpoint = f"organizations/{org_id}/relationships/documents"
                result = await client.get_all_pages(endpoint, filters)
                print(f"✅ Success: {len(result)} documents")
                
                if result:
                    for doc in result[:2]:
                        folder_id = doc.get('document_folder_id', 'root')
                        name = doc.get('name', 'Unknown')
                        print(f"  📄 '{name}' (folder: {folder_id})")
                        
            except Exception as e:
                print(f"❌ Failed: {str(e)[:100]}")
        
        # Test 4: Raw API exploration - different base paths
        base_paths = [
            "documents",
            "document_folders", 
            "folders",
            "files",
            "attachments"
        ]
        
        print(f"\n🌐 Testing Raw API Paths:")
        for base_path in base_paths:
            try:
                print(f"\n🔗 Testing base path: {base_path}")
                result = await client.get_all_pages(base_path, {"page[size]": "1"})
                print(f"✅ Success: {len(result)} items")
                
                if result and len(result) > 0:
                    sample = result[0]
                    print(f"  Sample fields: {list(sample.keys())[:10]}")
                    
            except Exception as e:
                print(f"❌ Failed: {str(e)[:100]}")
        
        # Test 5: Try accessing known document by ID with includes
        print(f"\n🎯 Testing Document by ID with Includes:")
        try:
            # Get first document
            docs = await client.get_documents(org_id=org_id)
            if docs:
                doc_id = docs[0].id if hasattr(docs[0], 'id') else docs[0].get('id')
                if doc_id:
                    include_tests = [
                        {"include": "document_folder"},
                        {"include": "folder"},
                        {"include": "parent"},
                        {"expand": "all"}
                    ]
                    
                    for include_params in include_tests:
                        try:
                            print(f"\n🔧 Include test: {include_params}")
                            endpoint = f"documents/{doc_id}"
                            result = await client.get_all_pages(endpoint, include_params)
                            print(f"✅ Success: Got document with includes")
                            
                            if result and len(result) > 0:
                                doc = result[0]
                                print(f"  Fields: {list(doc.keys())}")
                                
                        except Exception as e:
                            print(f"❌ Include failed: {str(e)[:100]}")
        except Exception as e:
            print(f"❌ Document ID test failed: {str(e)[:100]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run exhaustive folder discovery."""
    success = await test_all_document_endpoints()
    if success:
        print("\n✅ Exhaustive folder discovery completed!")
        return 0
    else:
        print("\n❌ Exhaustive folder discovery failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)