#!/usr/bin/env python3
"""List all IT Glue organizations to find the correct name."""

import os
import httpx
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def list_all_organizations():
    """List all organizations from IT Glue."""
    
    api_key = os.getenv("ITGLUE_API_KEY")
    api_url = os.getenv("ITGLUE_API_URL", "https://api.eu.itglue.com")
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/vnd.api+json"
    }
    
    print("=" * 60)
    print("ALL IT GLUE ORGANIZATIONS")
    print("=" * 60)
    
    all_orgs = []
    page = 1
    
    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                f"{api_url}/organizations",
                headers=headers,
                params={
                    "page[number]": page,
                    "page[size]": 50
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                organizations = data.get("data", [])
                
                if not organizations:
                    break
                
                all_orgs.extend(organizations)
                
                # Check if there are more pages
                meta = data.get("meta", {})
                if not meta.get("next-page"):
                    break
                    
                page += 1
            else:
                print(f"Error fetching page {page}: {response.status_code}")
                break
    
    # Display all organizations
    print(f"\nFound {len(all_orgs)} total organizations:\n")
    
    # Look for anything that might be "faucets"
    faucet_related = []
    
    for org in all_orgs:
        name = org.get("attributes", {}).get("name", "Unknown")
        org_id = org.get("id")
        org_type = org.get("attributes", {}).get("organization-type-name", "")
        
        print(f"  [{org_id}] {name}")
        if org_type:
            print(f"       Type: {org_type}")
        
        # Check if name contains "faucet" in any form
        if "faucet" in name.lower() or "tap" in name.lower() or "plumb" in name.lower():
            faucet_related.append((org_id, name, org_type))
    
    if faucet_related:
        print("\n" + "=" * 60)
        print("POTENTIALLY RELATED TO 'FAUCETS':")
        print("=" * 60)
        for org_id, name, org_type in faucet_related:
            print(f"  [{org_id}] {name}")
            if org_type:
                print(f"       Type: {org_type}")
    
    return all_orgs

if __name__ == "__main__":
    orgs = asyncio.run(list_all_organizations())
    print(f"\n✅ Listed {len(orgs)} organizations")