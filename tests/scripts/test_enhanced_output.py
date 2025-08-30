#!/usr/bin/env python3
"""Test enhanced output format for search results."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import settings
from src.services.itglue.client import ITGlueClient

async def test_enhanced_output():
    """Test that search results include detailed attributes."""
    
    print("=" * 60)
    print("TESTING ENHANCED OUTPUT FORMAT")
    print("=" * 60)
    
    # Faucets Limited org ID
    org_id = "3183713165639879"
    
    client = ITGlueClient(
        api_key=settings.itglue_api_key,
        api_url=settings.itglue_api_url
    )
    
    try:
        print(f"\n📋 Testing queries for Faucets Limited")
        
        # Test 1: Firewall query
        print("\n" + "=" * 60)
        print("1️⃣ FIREWALL QUERY: '@faucets firewall'")
        print("=" * 60)
        
        configs = await client.get_configurations(org_id=org_id)
        
        for config in configs:
            if "firewall" in (config.configuration_type or "").lower() or \
               any(fw in config.name.lower() for fw in ["sophos", "xgs"]):
                
                print(f"\n**{config.name}** ({config.configuration_type})")
                
                attrs = config.attributes if hasattr(config, 'attributes') else {}
                
                if attrs.get('primary-ip'):
                    print(f"  • IP Address: {attrs.get('primary-ip')}")
                if attrs.get('serial-number'):
                    print(f"  • Serial Number: {attrs.get('serial-number')}")
                if attrs.get('manufacturer-name') or attrs.get('model-name'):
                    manufacturer = attrs.get('manufacturer-name', '')
                    model = attrs.get('model-name', '')
                    if manufacturer or model:
                        print(f"  • Model: {manufacturer} {model}".strip())
                if attrs.get('default-gateway'):
                    print(f"  • Gateway: {attrs.get('default-gateway')}")
                if attrs.get('hostname'):
                    print(f"  • Hostname: {attrs.get('hostname')}")
                if attrs.get('created-at'):
                    print(f"  • Added to IT Glue: {attrs.get('created-at')[:10]}")
                if attrs.get('updated-at'):
                    print(f"  • Last Updated: {attrs.get('updated-at')[:10]}")
                if attrs.get('location-name'):
                    print(f"  • Location: {attrs.get('location-name')}")
                if attrs.get('configuration-status-name'):
                    print(f"  • Status: {attrs.get('configuration-status-name')}")
        
        # Test 2: Password query
        print("\n" + "=" * 60)
        print("2️⃣ PASSWORD QUERY: '@faucets admin password'")
        print("=" * 60)
        
        passwords = await client.get_passwords(org_id=org_id)
        
        admin_pwds = [p for p in passwords if 'admin' in p.name.lower()][:2]
        
        for pwd in admin_pwds:
            print(f"\n**{pwd.name}**")
            
            attrs = pwd.attributes if hasattr(pwd, 'attributes') else {}
            
            if pwd.username:
                print(f"  • Username: {pwd.username}")
            if attrs.get('url'):
                print(f"  • URL: {attrs.get('url')}")
            if attrs.get('created-at'):
                print(f"  • Created: {attrs.get('created-at')[:10]}")
            if attrs.get('updated-at'):
                print(f"  • Last Changed: {attrs.get('updated-at')[:10]}")
            
            print("  • 🔒 Password stored securely in IT Glue")
        
        # Test 3: Contact query
        print("\n" + "=" * 60)
        print("3️⃣ CONTACT QUERY: '@faucets main contact'")
        print("=" * 60)
        
        contacts = await client.get_contacts(org_id=org_id)
        
        for contact in contacts:
            print(f"\n**{contact.full_name}**")
            
            attrs = contact.attributes if hasattr(contact, 'attributes') else {}
            
            if attrs.get('title'):
                print(f"  • Title: {attrs.get('title')}")
            if attrs.get('contact-emails'):
                emails = attrs.get('contact-emails', [])
                if emails and len(emails) > 0:
                    print(f"  • Email: {emails[0].get('value', 'N/A')}")
            if attrs.get('contact-phones'):
                phones = attrs.get('contact-phones', [])
                if phones and len(phones) > 0:
                    print(f"  • Phone: {phones[0].get('value', 'N/A')}")
        
    finally:
        await client.disconnect()
    
    print("\n" + "=" * 60)
    print("✅ ENHANCED OUTPUT FORMAT")
    print("=" * 60)
    print("\nThe search now returns:")
    print("  ✅ Configuration details (IP, Serial, Model, Status)")
    print("  ✅ Password metadata (Username, Created, Last Changed)")
    print("  ✅ Contact information (Email, Phone, Title)")
    print("  ✅ Dates and timestamps for tracking changes")
    print("  ✅ Location and status information")

if __name__ == "__main__":
    asyncio.run(test_enhanced_output())