#!/usr/bin/env python3
"""Quick test to create a document with the fixed upload method."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_document_upload():
    print("🏗️ Testing Document Upload Fix for Faucets Limited")
    
    try:
        from src.services.itglue.client import ITGlueClient
        from src.data import db_manager
        
        # Initialize database
        await db_manager.initialize()
        
        # Initialize IT Glue client
        client = ITGlueClient()
        
        # Create a simple test document
        document_content = f"""# Infrastructure Documentation Test
## Faucets Limited

**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
**Document Type:** Infrastructure Audit Test
**Test Purpose:** Verify IT Glue document upload functionality

---

## Executive Summary

This is a test document to verify that the IT Glue document upload functionality
is working correctly for the infrastructure documentation tool.

### Test Information

- **Organization**: Faucets Limited
- **Test Date**: {datetime.utcnow().isoformat()}
- **Document Size**: Small test document
- **Upload Method**: Direct API call

---

## Test Results

If you can see this document in IT Glue, the upload functionality is working correctly!

---

*End of Test Document*
"""
        
        # Prepare document data for IT Glue API
        document_data = {
            "data": {
                "type": "documents",
                "attributes": {
                    "organization-id": 3183713165639879,  # Faucets Limited
                    "name": f"Infrastructure Documentation Test - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    "content": document_content,
                    "published": True,
                    "restricted": False,
                    "enable-password-protection": False
                }
            }
        }
        
        print("📋 Document prepared:")
        print(f"   Organization ID: 3183713165639879 (Faucets Limited)")
        print(f"   Document Name: {document_data['data']['attributes']['name']}")
        print(f"   Content Size: {len(document_content)} characters")
        print(f"   Published: {document_data['data']['attributes']['published']}")
        
        print("\n🚀 Attempting upload to IT Glue...")
        
        # Fix the create_document method by using 'data' instead of 'json'
        endpoint = "documents"
        
        try:
            # Call _request with correct parameter name
            response = await client._request(
                "POST",
                endpoint,
                data=document_data  # Use 'data' not 'json'
            )
            
            print("📊 Upload Results:")
            print("=" * 50)
            
            if response and response.get('data'):
                doc_data = response['data']
                doc_id = doc_data.get('id')
                doc_attributes = doc_data.get('attributes', {})
                
                print("✅ SUCCESS! Document uploaded to IT Glue!")
                print(f"   📄 Document ID: {doc_id}")
                print(f"   📝 Document Name: {doc_attributes.get('name', 'Unknown')}")
                print(f"   🔗 Resource URL: {doc_attributes.get('resource-url', 'Not available')}")
                print(f"   📅 Created: {doc_attributes.get('created-at', 'Unknown')}")
                print(f"   🏢 Organization: {doc_attributes.get('organization-name', 'Unknown')}")
                
                # Construct the likely IT Glue URL
                if doc_id:
                    itglue_url = f"https://yourdomain.itglue.com/3183713165639879/docs/{doc_id}"
                    print(f"   🌐 Likely IT Glue URL: {itglue_url}")
                
                return True
                
            else:
                print("❌ UPLOAD FAILED!")
                print("   No response data received from IT Glue")
                print(f"   Response: {response}")
                return False
                
        except Exception as e:
            print(f"❌ UPLOAD ERROR: {e}")
            print(f"   Exception type: {type(e).__name__}")
            return False
            
    except Exception as e:
        print(f"💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

# Run the test
if __name__ == "__main__":
    success = asyncio.run(test_document_upload())
    if success:
        print("\n🎉 Test completed successfully!")
        print("✅ Document upload functionality is working!")
    else:
        print("\n⚠️ Test failed - upload functionality needs attention")