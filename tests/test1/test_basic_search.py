#!/usr/bin/env python3
"""Test basic search functionality."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.data import db_manager
from sqlalchemy import text

async def test_basic_search():
    """Test basic database search."""
    print("🔍 Testing Basic Database Search")
    print("=" * 40)
    
    await db_manager.initialize()
    
    try:
        async with db_manager.acquire() as conn:
            # Check what entities we have
            result = await conn.execute(text("""
                SELECT 
                    entity_type,
                    COUNT(*) as count,
                    array_agg(name ORDER BY name LIMIT 5) as sample_names
                FROM itglue_entities 
                WHERE organization_id = '12345'
                GROUP BY entity_type
                ORDER BY count DESC
            """))
            
            print("📊 Entity counts by type:")
            for row in result:
                print(f"  {row.entity_type}: {row.count} items")
                print(f"    Samples: {', '.join(row.sample_names[:3])}")
            
            # Test simple search
            print("\n🔍 Testing simple name search:")
            result = await conn.execute(text("""
                SELECT name, entity_type, embedding_id IS NOT NULL as has_embedding
                FROM itglue_entities 
                WHERE organization_id = '12345'
                AND name ILIKE '%server%'
                LIMIT 5
            """))
            
            for row in result:
                print(f"  • {row.name} ({row.entity_type}) - Embedding: {row.has_embedding}")
                
            # Check embedding status
            print("\n📈 Embedding status:")
            result = await conn.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(embedding_id) as with_embeddings
                FROM itglue_entities 
                WHERE organization_id = '12345'
            """))
            
            row = result.first()
            print(f"  Total entities: {row.total}")
            print(f"  With embeddings: {row.with_embeddings}")
            print(f"  Coverage: {row.with_embeddings/row.total*100:.1f}%")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(test_basic_search())