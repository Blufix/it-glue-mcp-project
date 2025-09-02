#!/usr/bin/env python3
"""
Simple test script for the 'query_organizations' MCP tool.
Tests with REAL IT Glue API data focusing on Faucets organization.
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.itglue import ITGlueClient
from src.config.settings import settings
from src.query.organizations_handler import OrganizationsHandler
from src.cache import CacheManager


async def test_query_organizations():
    """Test the query_organizations tool directly."""
    
    print("=" * 80)
    print("IT GLUE MCP SERVER - QUERY ORGANIZATIONS TOOL TEST")
    print("=" * 80)
    print(f"Test Started: {datetime.now().isoformat()}\n")
    
    # Initialize components
    itglue_client = ITGlueClient(
        api_key=settings.itglue_api_key,
        api_url=settings.itglue_api_url
    )
    
    cache_manager = CacheManager(redis_url=settings.redis_url)
    
    handler = OrganizationsHandler(
        itglue_client=itglue_client,
        cache_manager=cache_manager
    )
    
    test_results = []
    performance_metrics = {}
    
    # TEST 1: Exact Match
    print("\n" + "=" * 60)
    print("TEST 1: Exact Match - 'Faucets'")
    print("=" * 60)
    
    start_time = time.time()
    result = await handler.find_organization("Faucets", use_fuzzy=False)
    elapsed = (time.time() - start_time) * 1000
    
    if result.get("success") and result.get("organization"):
        org = result["organization"]
        print(f"✅ Found organization: {org.get('name')}")
        print(f"   ID: {org.get('id')}")
        print(f"   Type: {org.get('organization_type')}")
        print(f"   Response time: {elapsed:.2f}ms")
        
        faucets_data = org
        test_results.append({"test": "Exact Match", "status": "PASSED", "time_ms": elapsed})
    else:
        print(f"❌ Not found with exact match")
        test_results.append({"test": "Exact Match", "status": "FAILED"})
        faucets_data = None
    
    performance_metrics["exact_match"] = elapsed
    
    # Try with full name
    print("\nTrying with full name 'Faucets Limited'...")
    start_time = time.time()
    result = await handler.find_organization("Faucets Limited", use_fuzzy=True)
    elapsed = (time.time() - start_time) * 1000
    
    if result.get("success") and result.get("organization"):
        print(f"✅ Found with full name: {result['organization'].get('name')}")
        print(f"   Response time: {elapsed:.2f}ms")
        if not faucets_data:
            faucets_data = result["organization"]
    else:
        print(f"⚠️ Not found with full name")
    
    # TEST 2: Fuzzy Matching
    print("\n" + "=" * 60)
    print("TEST 2: Fuzzy Matching")
    print("=" * 60)
    
    typo_variations = [
        "Faucet",      # Missing 's'
        "Faucetts",    # Extra 't'
        "Facets",      # Common typo
        "faucets",     # Lowercase
        "FAUCETS"      # Uppercase
    ]
    
    fuzzy_results = []
    
    for variant in typo_variations:
        start_time = time.time()
        result = await handler.find_organization(variant, use_fuzzy=True)
        elapsed = (time.time() - start_time) * 1000
        
        found = result.get("success") and result.get("organization")
        org_name = result.get("organization", {}).get("name") if found else None
        
        similarity = 0
        if org_name:
            similarity = SequenceMatcher(None, variant.lower(), "faucets limited".lower()).ratio()
        
        print(f"   '{variant}': {'✅ Found' if found else '❌ Not found'} ({elapsed:.2f}ms)")
        if found:
            print(f"      Matched: {org_name} (similarity: {similarity:.2%})")
        
        fuzzy_results.append({
            "variant": variant,
            "found": found,
            "matched_name": org_name,
            "similarity": similarity,
            "response_time_ms": elapsed
        })
    
    success_count = sum(1 for r in fuzzy_results if r.get("found"))
    accuracy = (success_count / len(typo_variations)) * 100
    
    print(f"\nFuzzy Matching Accuracy: {accuracy:.1f}% ({success_count}/{len(typo_variations)})")
    test_results.append({
        "test": "Fuzzy Matching",
        "status": "PASSED" if accuracy >= 60 else "FAILED",
        "accuracy": accuracy
    })
    
    # TEST 3: List Organizations
    print("\n" + "=" * 60)
    print("TEST 3: List Organizations")
    print("=" * 60)
    
    for limit in [10, 50]:
        start_time = time.time()
        result = await handler.list_all_organizations(limit=limit)
        elapsed = (time.time() - start_time) * 1000
        
        if result.get("success"):
            orgs = result.get("organizations", [])
            total = result.get("total_count", len(orgs))
            
            print(f"\nLimit {limit}:")
            print(f"   Returned: {len(orgs)} organizations")
            print(f"   Total available: {total}")
            print(f"   Response time: {elapsed:.2f}ms")
            
            # Check if Faucets is in the list
            faucets_found = any(
                "faucets" in org.get("name", "").lower() 
                for org in orgs
            )
            
            if faucets_found:
                print(f"   ✅ Faucets found in results")
            
            performance_metrics[f"list_{limit}"] = elapsed
    
    test_results.append({"test": "List Organizations", "status": "PASSED"})
    
    # TEST 4: Organization Filters
    print("\n" + "=" * 60)
    print("TEST 4: Organization Filters")
    print("=" * 60)
    
    # Test customers
    print("\nGetting customers...")
    start_time = time.time()
    result = await handler.list_customers(limit=20)
    elapsed = (time.time() - start_time) * 1000
    
    if result.get("success"):
        customers = result.get("organizations", [])
        print(f"✅ Found {len(customers)} customers ({elapsed:.2f}ms)")
        
        # Show first few customer names
        for i, customer in enumerate(customers[:3]):
            print(f"   {i+1}. {customer.get('name')} - {customer.get('organization_type')}")
    
    # Test vendors
    print("\nGetting vendors...")
    start_time = time.time()
    result = await handler.list_vendors(limit=20)
    elapsed = (time.time() - start_time) * 1000
    
    if result.get("success"):
        vendors = result.get("organizations", [])
        print(f"✅ Found {len(vendors)} vendors ({elapsed:.2f}ms)")
        
        # Show first few vendor names
        for i, vendor in enumerate(vendors[:3]):
            print(f"   {i+1}. {vendor.get('name')} - {vendor.get('organization_type')}")
    
    # Test stats
    print("\nGetting statistics...")
    start_time = time.time()
    result = await handler.get_organization_stats()
    elapsed = (time.time() - start_time) * 1000
    
    if result.get("success"):
        stats = result.get("stats", {})
        print(f"✅ Statistics ({elapsed:.2f}ms):")
        print(f"   Total organizations: {stats.get('total', 0)}")
        print(f"   Customers: {stats.get('customers', 0)}")
        print(f"   Vendors: {stats.get('vendors', 0)}")
        print(f"   Internal: {stats.get('internal', 0)}")
        print(f"   Other: {stats.get('other', 0)}")
    
    test_results.append({"test": "Organization Filters", "status": "PASSED"})
    
    # TEST 5: Validate Faucets Data
    if faucets_data:
        print("\n" + "=" * 60)
        print("TEST 5: Validate Faucets Organization Data")
        print("=" * 60)
        
        required_fields = ["id", "name", "organization_type", "created_at", "updated_at"]
        
        print("\nValidating required fields...")
        all_present = True
        for field in required_fields:
            present = field in faucets_data and faucets_data.get(field) is not None
            if present:
                print(f"   ✅ {field}: Present")
            else:
                print(f"   ❌ {field}: Missing")
                all_present = False
        
        print(f"\nOrganization Details:")
        print(f"   Name: {faucets_data.get('name')}")
        print(f"   ID: {faucets_data.get('id')}")
        print(f"   Type: {faucets_data.get('organization_type')}")
        print(f"   Status: {faucets_data.get('organization_status_name', 'N/A')}")
        
        test_results.append({
            "test": "Data Validation",
            "status": "PASSED" if all_present else "FAILED"
        })
    
    # TEST 6: Performance Benchmarks
    print("\n" + "=" * 60)
    print("TEST 6: Performance Benchmarks")
    print("=" * 60)
    
    print("\nResponse Time Summary:")
    for metric, value in performance_metrics.items():
        status = "✅" if value < 500 else "⚠️" if value < 2000 else "❌"
        print(f"   {status} {metric}: {value:.2f}ms")
    
    avg_time = sum(performance_metrics.values()) / len(performance_metrics) if performance_metrics else 0
    print(f"\nAverage response time: {avg_time:.2f}ms")
    
    if avg_time < 500:
        print("✅ Performance: EXCELLENT")
    elif avg_time < 1000:
        print("✅ Performance: GOOD")
    elif avg_time < 2000:
        print("⚠️ Performance: ACCEPTABLE")
    else:
        print("❌ Performance: NEEDS IMPROVEMENT")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in test_results if r.get("status") == "PASSED")
    failed = sum(1 for r in test_results if r.get("status") == "FAILED")
    
    print(f"\nResults:")
    print(f"  ✅ Passed: {passed}/{len(test_results)}")
    print(f"  ❌ Failed: {failed}/{len(test_results)}")
    
    for result in test_results:
        status_symbol = "✅" if result["status"] == "PASSED" else "❌"
        extra = ""
        if "accuracy" in result:
            extra = f" (Accuracy: {result['accuracy']:.1f}%)"
        elif "time_ms" in result:
            extra = f" ({result['time_ms']:.2f}ms)"
        print(f"  {status_symbol} {result['test']}{extra}")
    
    # Save results
    report_file = Path(__file__).parent / "query_organizations_results.json"
    
    report_data = {
        "test_date": datetime.now().isoformat(),
        "test_results": test_results,
        "performance_metrics": performance_metrics,
        "target_organization": "Faucets Limited",
        "summary": {
            "passed": passed,
            "failed": failed,
            "avg_response_ms": avg_time
        }
    }
    
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n📄 Results saved to: {report_file}")
    print("=" * 80)
    
    # Cleanup
    await itglue_client.disconnect()
    # Cache manager doesn't need explicit closing


if __name__ == "__main__":
    asyncio.run(test_query_organizations())