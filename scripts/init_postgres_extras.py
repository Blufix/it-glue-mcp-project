#!/usr/bin/env python3
"""Initialize additional PostgreSQL functions, indexes and triggers."""

import asyncio
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings


async def init_postgres_extras():
    """Initialize PostgreSQL with additional functions and indexes."""
    
    print("Initializing PostgreSQL extras...")
    print("-" * 50)
    
    # Create async engine
    engine = create_async_engine(settings.database_url)
    
    async with engine.connect() as conn:
        # Create additional indexes for performance
        indexes = [
            # Composite indexes for common queries
            ("CREATE INDEX IF NOT EXISTS idx_entity_org_type_updated ON itglue_entities(organization_id, entity_type, updated_at DESC)", 
             "Composite index for org queries"),
            
            ("CREATE INDEX IF NOT EXISTS idx_entity_search_gin ON itglue_entities USING gin(to_tsvector('english', search_text))",
             "GIN index for full-text search"),
            
            ("CREATE INDEX IF NOT EXISTS idx_sync_status_composite ON sync_status(entity_type, status, next_sync)",
             "Composite index for sync scheduling"),
            
            ("CREATE INDEX IF NOT EXISTS idx_query_log_user_time ON query_logs(user_id, created_at DESC)",
             "User query history index"),
            
            ("CREATE INDEX IF NOT EXISTS idx_cache_key_hash ON cache_entries USING hash(cache_key)",
             "Hash index for cache lookups"),
            
            # Partial indexes for specific conditions
            ("CREATE INDEX IF NOT EXISTS idx_active_embeddings ON embedding_queue(status) WHERE status IN ('pending', 'processing')",
             "Partial index for active embeddings"),
             
            ("CREATE INDEX IF NOT EXISTS idx_failed_syncs ON sync_status(entity_type, last_error) WHERE status = 'failed'",
             "Partial index for failed syncs"),
        ]
        
        for query, description in indexes:
            try:
                await conn.execute(text(query))
                await conn.commit()
                print(f"✅ Created: {description}")
            except Exception as e:
                await conn.rollback()
                if "already exists" in str(e).lower():
                    print(f"✓ Exists: {description}")
                else:
                    print(f"❌ Failed: {description} - {e}")
        
        # Create utility functions
        print("\nCreating utility functions...")
        
        functions = [
            # Function to update search_text automatically
            ("""
            CREATE OR REPLACE FUNCTION update_search_text()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_text = to_tsvector('english',
                    COALESCE(NEW.name, '') || ' ' ||
                    COALESCE(NEW.content::text, '') || ' ' ||
                    COALESCE((NEW.attributes->>'description')::text, '') || ' ' ||
                    COALESCE((NEW.attributes->>'notes')::text, '')
                );
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """, "Search text update function"),
            
            # Function to clean expired cache entries
            ("""
            CREATE OR REPLACE FUNCTION clean_expired_cache()
            RETURNS INTEGER AS $$
            DECLARE
                deleted_count INTEGER;
            BEGIN
                DELETE FROM cache_entries 
                WHERE expires_at < NOW()
                AND expires_at IS NOT NULL;
                
                GET DIAGNOSTICS deleted_count = ROW_COUNT;
                RETURN deleted_count;
            END;
            $$ LANGUAGE plpgsql;
            """, "Cache cleanup function"),
            
            # Function to get entity statistics
            ("""
            CREATE OR REPLACE FUNCTION get_entity_stats(org_id INTEGER DEFAULT NULL)
            RETURNS TABLE(
                entity_type VARCHAR,
                total_count BIGINT,
                synced_today BIGINT,
                with_embeddings BIGINT
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    e.entity_type::VARCHAR,
                    COUNT(*)::BIGINT as total_count,
                    COUNT(CASE WHEN e.updated_at > NOW() - INTERVAL '24 hours' THEN 1 END)::BIGINT as synced_today,
                    COUNT(e.embedding_id)::BIGINT as with_embeddings
                FROM itglue_entities e
                WHERE (org_id IS NULL OR e.organization_id = org_id)
                GROUP BY e.entity_type
                ORDER BY total_count DESC;
            END;
            $$ LANGUAGE plpgsql;
            """, "Entity statistics function"),
            
            # Function to find similar entities
            ("""
            CREATE OR REPLACE FUNCTION find_similar_entities(
                search_term TEXT,
                limit_count INTEGER DEFAULT 10
            )
            RETURNS TABLE(
                entity_id UUID,
                entity_name VARCHAR,
                entity_type VARCHAR,
                similarity REAL
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    e.id as entity_id,
                    e.name as entity_name,
                    e.entity_type::VARCHAR,
                    similarity(e.name, search_term) as similarity
                FROM itglue_entities e
                WHERE e.name % search_term  -- Uses trigram similarity
                ORDER BY similarity DESC
                LIMIT limit_count;
            END;
            $$ LANGUAGE plpgsql;
            """, "Similar entity search function"),
        ]
        
        for query, description in functions:
            try:
                await conn.execute(text(query))
                await conn.commit()
                print(f"✅ Created: {description}")
            except Exception as e:
                await conn.rollback()
                if "already exists" in str(e).lower():
                    print(f"✓ Exists: {description}")
                else:
                    print(f"❌ Failed: {description} - {e}")
        
        # Create triggers
        print("\nCreating triggers...")
        
        triggers = [
            # Function for sync completion
            ("""
            CREATE OR REPLACE FUNCTION log_sync_completion()
            RETURNS TRIGGER AS $$
            BEGIN
                IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
                    NEW.completed_at = NOW();
                    NEW.next_sync = NOW() + INTERVAL '15 minutes';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """, "Sync completion function"),
            
            # Trigger to update search_text on insert/update
            ("""
            DROP TRIGGER IF EXISTS update_entity_search_text ON itglue_entities;
            """, "Drop existing search trigger"),
            
            ("""
            CREATE TRIGGER update_entity_search_text
            BEFORE INSERT OR UPDATE ON itglue_entities
            FOR EACH ROW
            EXECUTE FUNCTION update_search_text();
            """, "Search text update trigger"),
            
            # Trigger to log sync completion
            ("""
            DROP TRIGGER IF EXISTS sync_completion_trigger ON sync_status;
            """, "Drop existing sync trigger"),
            
            ("""
            CREATE TRIGGER sync_completion_trigger
            BEFORE UPDATE ON sync_status
            FOR EACH ROW
            EXECUTE FUNCTION log_sync_completion();
            """, "Sync completion trigger"),
        ]
        
        for query, description in triggers:
            try:
                await conn.execute(text(query))
                await conn.commit()
                print(f"✅ Created: {description}")
            except Exception as e:
                await conn.rollback()
                if "already exists" in str(e).lower() or "does not exist" in str(e).lower():
                    print(f"✓ OK: {description}")
                else:
                    print(f"❌ Failed: {description} - {e}")
        
        # Create materialized views for performance
        print("\nCreating materialized views...")
        
        views = [
            ("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS entity_summary AS
            SELECT 
                organization_id,
                entity_type,
                COUNT(*) as count,
                MAX(updated_at) as last_updated,
                COUNT(embedding_id) as embedded_count
            FROM itglue_entities
            GROUP BY organization_id, entity_type
            WITH DATA;
            """, "Entity summary view"),
            
            ("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_entity_summary_pk 
            ON entity_summary(organization_id, entity_type);
            """, "Entity summary view index"),
            
            ("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS sync_health AS
            SELECT 
                entity_type,
                status,
                COUNT(*) as count,
                AVG(EXTRACT(EPOCH FROM (NOW() - last_sync))/3600)::NUMERIC(10,2) as avg_hours_since_sync,
                MAX(last_sync) as most_recent_sync
            FROM sync_status
            GROUP BY entity_type, status
            WITH DATA;
            """, "Sync health view"),
            
            ("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_sync_health_pk 
            ON sync_health(entity_type, status);
            """, "Sync health view index"),
        ]
        
        for query, description in views:
            try:
                await conn.execute(text(query))
                await conn.commit()
                print(f"✅ Created: {description}")
            except Exception as e:
                await conn.rollback()
                if "already exists" in str(e).lower():
                    print(f"✓ Exists: {description}")
                else:
                    print(f"❌ Failed: {description} - {e}")
        
        # Display database statistics
        print("\n" + "=" * 50)
        print("PostgreSQL Statistics:")
        
        # Get table sizes
        size_query = """
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
            n_live_tup as row_estimate
        FROM pg_stat_user_tables
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        """
        
        result = await conn.execute(text(size_query))
        rows = result.fetchall()
        
        print("\nTable sizes:")
        for row in rows:
            print(f"  • {row[0]}.{row[1]}: {row[2]} (~{row[3]} rows)")
        
        # Get index information
        index_query = """
        SELECT 
            schemaname,
            tablename,
            indexname,
            pg_size_pretty(pg_relation_size(indexrelid)) as size
        FROM pg_stat_user_indexes
        ORDER BY pg_relation_size(indexrelid) DESC
        LIMIT 10;
        """
        
        result = await conn.execute(text(index_query))
        rows = result.fetchall()
        
        if rows:
            print("\nTop indexes by size:")
            for row in rows:
                print(f"  • {row[2]}: {row[3]}")
    
    await engine.dispose()
    
    print("-" * 50)
    print("PostgreSQL extras initialization complete!")


if __name__ == "__main__":
    asyncio.run(init_postgres_extras())