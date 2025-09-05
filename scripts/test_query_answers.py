#!/usr/bin/env python3
"""Test and extract actual answers from successful RAG queries."""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import db_manager
from src.query.engine import QueryEngine
from src.services.itglue.client import ITGlueClient


async def test_query_answers():
    """Test RAG queries and extract actual answers."""
    print("🎯 Testing RAG Query Answers")
    print("=" * 50)
    
    try:
        # Initialize
        await db_manager.initialize()
        client = ITGlueClient()
        query_engine = QueryEngine(itglue_client=client)
        
        # Test query
        query = "What compliance standards does Faucets follow?"
        company = "Faucets Limited"
        
        print(f"🔍 Query: {query}")
        print(f"🏢 Company: {company}")
        
        result = await query_engine.process_query(
            query=query,
            company=company
        )
        
        print(f"\n📋 Full Result Structure:")
        print("=" * 40)
        print(json.dumps(result, indent=2, default=str))
        
        # Check the data field specifically
        if 'data' in result and result['data']:
            data = result['data']
            print(f"\n📄 Data Field Contents:")
            print("-" * 30)
            
            for key, value in data.items():
                if key == 'content' and isinstance(value, str) and len(value) > 200:
                    print(f"{key}: {value[:200]}...")
                else:
                    print(f"{key}: {value}")
            
            # Try to extract answer from content
            content = data.get('content', '')
            if content:
                print(f"\n🔍 Found content in data field!")
                print(f"📝 Content preview: {content[:500]}...")
                
                # Look for compliance standards specifically
                content_lower = content.lower()
                if 'gdpr' in content_lower or 'iso' in content_lower or 'pci' in content_lower:
                    print(f"\n✅ FOUND COMPLIANCE STANDARDS!")
                    
                    # Extract compliance-related sections
                    lines = content.split('\n')
                    compliance_lines = []
                    
                    for line in lines:
                        if any(term in line.lower() for term in ['gdpr', 'iso', 'pci', 'compliance']):
                            compliance_lines.append(line.strip())
                    
                    if compliance_lines:
                        print(f"📋 Compliance information found:")
                        for line in compliance_lines:
                            if line:  # Skip empty lines
                                print(f"   • {line}")
        
        # Test a more direct query
        print(f"\n🎯 Testing direct GDPR query...")
        result2 = await query_engine.process_query(
            query="What does Faucets' GDPR policy say?",
            company=company
        )
        
        if result2.get('success') and result2.get('data'):
            data2 = result2['data']
            content2 = data2.get('content', '')
            print(f"✅ GDPR query successful!")
            if content2:
                # Look for GDPR content
                if 'gdpr' in content2.lower():
                    gdpr_context = []
                    lines = content2.split('\n')
                    for i, line in enumerate(lines):
                        if 'gdpr' in line.lower():
                            # Get context around GDPR mention
                            start = max(0, i-2)
                            end = min(len(lines), i+3)
                            context = '\n'.join(lines[start:end])
                            gdpr_context.append(context)
                    
                    print(f"📋 GDPR Context:")
                    for ctx in gdpr_context:
                        print(f"   {ctx}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_query_answers())