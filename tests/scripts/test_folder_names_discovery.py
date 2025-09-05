#!/usr/bin/env python3
"""Test to discover actual folder names, not just IDs."""

import asyncio
import logging
import os
import sys
from pathlib import Path

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


async def discover_actual_folder_names():
    """Discover the actual folder names by examining document attributes."""
    
    # Check API key
    api_key = os.getenv('IT_GLUE_API_KEY') or os.getenv('ITGLUE_API_KEY')
    if not api_key:
        print("❌ API key not set")
        return False
    
    print("🔍 Discovering ACTUAL Folder Names")
    print("=" * 50)
    
    try:
        client = ITGlueClient()
        
        # Get organization
        orgs = await client.get_organizations(filters={"name": "Faucets Limited"})
        org = orgs[0]
        org_id = org.id
        
        print(f"✅ Organization: {org.name} (ID: {org_id})")
        
        # Get folder documents with full attribute inspection
        folder_documents = await client.get_documents(org_id=org_id, include_folders=True)
        
        # Remove root documents to focus on folder documents only
        root_documents = await client.get_documents(org_id=org_id)
        root_doc_ids = {doc.id for doc in root_documents if hasattr(doc, 'id')}
        folder_only_docs = [doc for doc in folder_documents if hasattr(doc, 'id') and doc.id not in root_doc_ids]
        
        print(f"\n📂 Found {len(folder_only_docs)} documents in folders")
        
        # Group by folder ID and examine attributes for folder names
        folders = {}
        for doc in folder_only_docs:
            folder_id = getattr(doc, 'document_folder_id', None) 
            if not folder_id and hasattr(doc, 'attributes'):
                folder_id = doc.attributes.get('document-folder-id')
            
            if folder_id:
                if folder_id not in folders:
                    folders[folder_id] = {
                        'documents': [],
                        'folder_name': None,
                        'sample_doc': doc
                    }
                folders[folder_id]['documents'].append(doc.name)
                
                # Try to extract folder name from document attributes
                if hasattr(doc, 'attributes'):
                    attrs = doc.attributes
                    # Look for folder-related attributes
                    for key, value in attrs.items():
                        if 'folder' in key.lower() and key != 'document-folder-id':
                            folders[folder_id]['folder_name'] = value
                            print(f"  🔍 Found folder attribute: {key} = {value}")
                
                # Check relationships for folder info
                if hasattr(doc, 'relationships'):
                    relationships = doc.relationships
                    if isinstance(relationships, dict) and 'document-folder' in relationships:
                        folder_info = relationships['document-folder']
                        print(f"  🔍 Found folder relationship: {folder_info}")
                
        print(f"\n📊 Folder Analysis:")
        for folder_id, folder_data in folders.items():
            doc_count = len(folder_data['documents'])
            folder_name = folder_data['folder_name'] or "Unknown Name"
            
            print(f"\n📂 Folder ID: {folder_id}")
            print(f"   Name: {folder_name}")
            print(f"   Documents: {doc_count}")
            
            # Check if this could be the "Software" folder
            software_indicators = ['software', 'access', 'dimensions', 'installation']
            is_software_candidate = any(
                indicator in doc_name.lower() 
                for doc_name in folder_data['documents'] 
                for indicator in software_indicators
            )
            
            if is_software_candidate:
                print(f"   🎯 **LIKELY SOFTWARE FOLDER** (contains software-related documents)")
            
            for i, doc_name in enumerate(folder_data['documents'][:5], 1):
                print(f"   {i:2d}. {doc_name}")
            if doc_count > 5:
                print(f"       ... and {doc_count - 5} more documents")
                
        # Try alternative approaches to get folder names
        print(f"\n🔍 Alternative Approach: Direct Folder Endpoint Test")
        try:
            # Try to get folder information directly
            folder_endpoints = [
                f"organizations/{org_id}/relationships/document_folders",
                f"document_folders?filter[organization_id]={org_id}"
            ]
            
            for endpoint in folder_endpoints:
                try:
                    result = await client.get_all_pages(endpoint, {})
                    if result:
                        print(f"✅ {endpoint} returned {len(result)} folders:")
                        for folder in result[:5]:
                            folder_name = folder.get('name', 'No name')
                            folder_id = folder.get('id', 'No ID')
                            print(f"  📂 {folder_name} (ID: {folder_id})")
                        break
                except Exception as e:
                    print(f"❌ {endpoint}: {str(e)[:50]}")
        except Exception as e:
            print(f"❌ Folder endpoint test failed: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    success = await discover_actual_folder_names()
    if success:
        print("\n✅ Folder name discovery completed!")
        return 0
    else:
        print("\n❌ Folder name discovery failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)