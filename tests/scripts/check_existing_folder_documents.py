#!/usr/bin/env python3
"""Check if there are any documents with folder IDs in the existing database."""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data import db_manager
from sqlalchemy import text


async def check_folder_documents():
    """Check for documents with folder IDs in the database."""
    
    print("🔍 Checking for Documents in Folders")
    print("=" * 45)
    
    await db_manager.initialize()
    
    async with db_manager.get_session() as session:
        # Check all documents and their folder status
        result = await session.execute(text("""
            SELECT 
                name,
                id,
                organization_id,
                attributes->>'document-folder-id' as folder_id,
                CASE 
                    WHEN attributes->>'document-folder-id' IS NULL OR attributes->>'document-folder-id' = '' 
                    THEN 'Root' 
                    ELSE 'In Folder' 
                END as location,
                last_synced
            FROM itglue_entities 
            WHERE entity_type = 'document'
            ORDER BY 
                organization_id, 
                CASE WHEN attributes->>'document-folder-id' IS NULL THEN 0 ELSE 1 END,
                name
        """))
        
        docs = result.fetchall()
        
        if not docs:
            print("❌ No documents found in database")
            return
            
        # Group by organization
        orgs = {}
        for doc in docs:
            org_id = doc.organization_id
            if org_id not in orgs:
                orgs[org_id] = {'root': [], 'folders': []}
            
            if doc.location == 'Root':
                orgs[org_id]['root'].append(doc)
            else:
                orgs[org_id]['folders'].append(doc)
        
        # Display results
        for org_id, org_docs in orgs.items():
            # Get organization name if it's Faucets
            org_name = "Faucets Limited" if org_id == "3183713165639879" else f"Org {org_id[:8]}..."
            
            print(f"\n🏢 {org_name} ({org_id})")
            print("-" * 50)
            
            print(f"📁 Root Documents: {len(org_docs['root'])}")
            for doc in org_docs['root']:
                print(f"   • {doc.name}")
            
            print(f"📂 Documents in Folders: {len(org_docs['folders'])}")
            if org_docs['folders']:
                # Group by folder ID
                folders = {}
                for doc in org_docs['folders']:
                    folder_id = doc.folder_id
                    if folder_id not in folders:
                        folders[folder_id] = []
                    folders[folder_id].append(doc)
                
                for folder_id, folder_docs in folders.items():
                    print(f"   📂 Folder {folder_id}:")
                    for doc in folder_docs:
                        print(f"      • {doc.name}")
            else:
                print("   (No documents in folders found)")
        
        # Summary
        total_docs = len(docs)
        folder_docs = [d for d in docs if d.location == 'In Folder']
        
        print(f"\n📊 Summary:")
        print(f"   Total documents: {total_docs}")
        print(f"   Root documents: {total_docs - len(folder_docs)}")
        print(f"   Documents in folders: {len(folder_docs)}")
        
        if folder_docs:
            print(f"\n✅ Found {len(folder_docs)} documents in folders!")
            print("🎯 Your folder filtering implementation will work with these documents")
            
            # Show unique folder IDs
            folder_ids = set(doc.folder_id for doc in folder_docs)
            print(f"\n📁 Folder IDs found:")
            for folder_id in folder_ids:
                count = len([d for d in folder_docs if d.folder_id == folder_id])
                print(f"   • {folder_id} ({count} documents)")
                
        else:
            print(f"\n ℹ️  No documents in folders found in current database")
            print("   This could mean:")
            print("   • Documents are all at root level")
            print("   • Folder documents haven't been synced yet") 
            print("   • Folder documents are file uploads (not accessible via API)")
            
        print(f"\n🔗 Next steps:")
        if folder_docs:
            print("   • Use folder_id values above to test specific folder queries")
            print("   • Try: query_documents(action='in_folder', folder_id='<folder_id>')")
        else:
            print("   • Try: query_documents(action='folders') to check for new folder documents")
            print("   • Verify if software folder documents are API-accessible")


async def main():
    """Run the check."""
    try:
        await check_folder_documents()
        return 0
    except Exception as e:
        print(f"❌ Error checking folder documents: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)