#!/usr/bin/env python3
"""Test flexible assets integration with Streamlit query system."""

import asyncio
from src.ui.streamlit_app import search_itglue_data

async def test_streamlit_flexible_assets():
    """Test flexible assets integration in Streamlit."""
    
    print("🧪 Testing Streamlit Flexible Assets Integration")
    print("=" * 60)
    
    # Test 1: List all flexible assets
    print("\n1️⃣ Testing 'list flexible assets' query...")
    try:
        result = await search_itglue_data("list flexible assets", "3183713165639879")
        print(f"✅ Query successful!")
        print(f"📊 Sources found: {len(result.get('sources', []))}")
        print(f"🎯 Confidence: {result.get('confidence', 0):.2f}")
        
        content = result.get('content', '')
        if "Office 365" in content:
            print("✅ Found Office 365 Email asset!")
        
        if len(result.get('sources', [])) > 0:
            print(f"✅ Found {len(result.get('sources', []))} flexible assets")
            for source in result.get('sources', [])[:3]:
                print(f"   • {source.get('name', 'Unknown')}")
        else:
            print("ℹ️ No flexible assets found (might be expected if none match)")
            
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 2: Email-specific search
    print("\n2️⃣ Testing 'email' search...")
    try:
        result = await search_itglue_data("email", "3183713165639879")
        print(f"✅ Email query successful!")
        print(f"📊 Sources found: {len(result.get('sources', []))}")
        
        content = result.get('content', '')
        if "Office 365" in content:
            print("✅ Found Office 365 Email asset in email search!")
        if "faucets.co.uk" in content or "domain" in content.lower():
            print("✅ Found domain information!")
            
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 3: Office 365 specific search
    print("\n3️⃣ Testing 'Office 365' search...")
    try:
        result = await search_itglue_data("Office 365", "3183713165639879")
        print(f"✅ Office 365 query successful!")
        print(f"📊 Sources found: {len(result.get('sources', []))}")
        
        if "Office 365" in result.get('content', ''):
            print("✅ Found Office 365 asset!")
            
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Streamlit Flexible Assets Integration Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_streamlit_flexible_assets())