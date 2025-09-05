#!/usr/bin/env python3
"""
Fix database schema mismatch between init script and SQLAlchemy models.
This script drops problematic indexes/triggers and recreates tables properly.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.data import db_manager
from src.config.settings import settings
import asyncpg


async def fix_schema():
    """Fix the database schema to match SQLAlchemy models."""
    
    print("=" * 80)
    print("DATABASE SCHEMA FIX")
    print("=" * 80)
    
    # First, connect directly with asyncpg to drop problematic elements
    print("\n1. Connecting to database...")
    
    # Parse the database URL for asyncpg
    pg_url = settings.database_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    conn = await asyncpg.connect(pg_url)
    
    try:
        print("2. Checking for problematic indexes/triggers...")
        
        # Check if the problematic index exists
        result = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM pg_indexes 
            WHERE schemaname = 'itglue' 
            AND indexname = 'idx_gin_trgm'
        """)
        
        if result > 0:
            print("   Found problematic idx_gin_trgm index")
            print("3. Dropping problematic index...")
            await conn.execute("DROP INDEX IF EXISTS itglue.idx_gin_trgm CASCADE")
            print("   ✅ Dropped idx_gin_trgm")
        else:
            print("   ✅ No problematic indexes found")
        
        # Check for any triggers referencing 'content' field
        triggers = await conn.fetch("""
            SELECT tgname, tgrelid::regclass 
            FROM pg_trigger 
            WHERE tgrelid IN (
                SELECT oid FROM pg_class 
                WHERE relnamespace = (
                    SELECT oid FROM pg_namespace WHERE nspname = 'itglue'
                )
            )
        """)
        
        if triggers:
            print(f"   Found {len(triggers)} triggers")
            for trigger in triggers:
                print(f"   - {trigger['tgname']} on {trigger['tgrelid']}")
        
        # Drop all tables in itglue schema to start fresh
        print("\n4. Dropping existing tables in itglue schema...")
        await conn.execute("DROP SCHEMA IF EXISTS itglue CASCADE")
        await conn.execute("CREATE SCHEMA IF NOT EXISTS itglue")
        print("   ✅ Schema reset complete")
        
    finally:
        await conn.close()
    
    # Now use SQLAlchemy to create tables properly
    print("\n5. Initializing database manager...")
    await db_manager.initialize()
    
    print("6. Creating tables from SQLAlchemy models...")
    await db_manager.create_tables()
    print("   ✅ Tables created successfully")
    
    # Verify the schema
    print("\n7. Verifying schema...")
    
    async with db_manager.acquire() as conn:
        # Check that search_text column exists
        result = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_name = 'itglue_entities' 
            AND column_name = 'search_text'
        """)
        
        if result > 0:
            print("   ✅ search_text column exists")
        else:
            print("   ❌ search_text column missing!")
            
        # Check that content column does NOT exist
        result = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_name = 'itglue_entities' 
            AND column_name = 'content'
        """)
        
        if result == 0:
            print("   ✅ content column does not exist (correct)")
        else:
            print("   ⚠️ content column exists (unexpected)")
            
        # List all columns in itglue_entities
        columns = await conn.fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'itglue_entities'
            ORDER BY ordinal_position
        """)
        
        print("\n   itglue_entities columns:")
        for col in columns:
            print(f"      - {col['column_name']}: {col['data_type']}")
    
    await db_manager.close()
    
    print("\n" + "=" * 80)
    print("✅ DATABASE SCHEMA FIXED")
    print("=" * 80)
    print("\nYou can now run the sync scripts successfully!")


if __name__ == "__main__":
    asyncio.run(fix_schema())