#!/usr/bin/env python3
"""Test exact Streamlit flow to find where it breaks."""

import asyncio
from src.services.itglue.client import ITGlueClient

async def test_exact_streamlit_flow():
    """Test the exact flow that Streamlit search_itglue_data uses."""
    
    print("🧪 Testing Exact Streamlit Flow")
    print("=" * 50)
    
    query = "list flexible assets"
    org_id = "3183713165639879"  # Faucets
    query_lower = query.lower()
    
    results = []
    sources = []
    
    async with ITGlueClient() as client:
        print(f"\n🔍 Query: '{query}'")
        print(f"🏢 Org ID: {org_id}")
        
        # This is the exact condition from Streamlit
        if "list flexible" in query_lower or "list asset" in query_lower or any(word in query_lower for word in ["flexible asset", "ssl certificate", "ssl", "warranty", "license", "contract", "asset", "certificate", "cert"]):
            print("✅ Query matches flexible assets condition")
            
            try:
                print("\n📋 Getting flexible assets...")
                
                # This is exactly what Streamlit does
                if org_id:  # We have an org_id
                    flexible_assets = await client.get_all_flexible_assets_for_org(org_id)
                else:
                    # Fallback logic (shouldn't happen in our test)
                    orgs = await client.get_organizations()
                    if orgs:
                        flexible_assets = await client.get_all_flexible_assets_for_org(orgs[0].id)
                    else:
                        flexible_assets = []
                
                print(f"✅ Retrieved {len(flexible_assets)} flexible assets")
                
                # Process the assets exactly like Streamlit
                print("\n🔄 Processing assets...")
                for i, asset in enumerate(flexible_assets[:5]):  # Limit for testing
                    print(f"   Processing asset {i+1}: {asset.name}")
                    
                    asset_name_lower = asset.name.lower()
                    match_found = False

                    # This is the exact matching logic from Streamlit
                    if "list flexible" in query_lower or "list asset" in query_lower or "list all asset" in query_lower:
                        match_found = True
                        print(f"     ✅ Match found (list all)")
                    else:
                        # Other matching logic would go here
                        pass

                    if match_found:
                        print(f"     📝 Adding to results...")
                        
                        sources.append({
                            "type": "Flexible Asset",
                            "name": asset.name,
                            "confidence": 0.9
                        })

                        asset_details = []
                        asset_details.append(f"**{asset.name}** (Flexible Asset)")

                        # Add organization info
                        if hasattr(asset, 'organization_id'):
                            asset_details.append(f"  • Organization ID: {asset.organization_id}")

                        # Add traits
                        if hasattr(asset, 'traits') and asset.traits:
                            trait_count = len(asset.traits)
                            asset_details.append(f"  • Configuration Fields: {trait_count} fields")
                            
                            # Show key traits
                            interesting_traits = {}
                            for key, value in asset.traits.items():
                                if value and str(value).strip():
                                    key_lower = key.lower()
                                    if any(term in key_lower for term in ['domain', 'email', 'url', 'server', 'location', 'enabled', 'ip', 'address', 'spf', 'dkim', 'dmarc', 'mfa']):
                                        interesting_traits[key] = value
                            
                            # Display up to 3 most interesting traits  
                            for trait_name, trait_value in list(interesting_traits.items())[:3]:
                                if isinstance(trait_value, dict):
                                    if 'values' in trait_value and trait_value['values']:
                                        if isinstance(trait_value['values'][0], dict):
                                            display_value = trait_value['values'][0].get('name', str(trait_value))
                                        else:
                                            display_value = str(trait_value['values'][0])
                                    else:
                                        display_value = str(trait_value)[:50] + "..." if len(str(trait_value)) > 50 else str(trait_value)
                                else:
                                    display_value = str(trait_value)[:80] + "..." if len(str(trait_value)) > 80 else str(trait_value)
                                
                                asset_details.append(f"    • {trait_name}: {display_value}")

                        asset_details.append("  • 📦 Full asset details available in IT Glue")
                        results.append("\n".join(asset_details))
                        
                        print(f"     ✅ Added to results (now {len(results)} items)")
                
                print(f"\n📊 Final Results:")
                print(f"   • Results count: {len(results)}")
                print(f"   • Sources count: {len(sources)}")
                
                if results:
                    print(f"\n✅ SUCCESS: Would show actual results!")
                    print("📄 Sample result:")
                    print(results[0][:200] + "..." if len(results[0]) > 200 else results[0])
                else:
                    print(f"\n❌ PROBLEM: No results created, would show fallback!")
                    
            except Exception as e:
                print(f"❌ Exception in flexible assets processing: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("❌ Query doesn't match flexible assets condition")

if __name__ == "__main__":
    asyncio.run(test_exact_streamlit_flow())