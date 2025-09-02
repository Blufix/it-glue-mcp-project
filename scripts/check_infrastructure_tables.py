"""Script to check if infrastructure documentation tables exist in PostgreSQL."""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_tables():
    """Check if infrastructure tables exist in the database."""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:Dfgytw6745g@localhost:5434/itglue')
    
    # Parse the URL for asyncpg - handle both formats
    if database_url.startswith('postgresql+asyncpg://'):
        database_url = database_url.replace('postgresql+asyncpg://', '')
    elif database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', '')
    
    # Connect to database
    try:
        conn = await asyncpg.connect(f'postgresql://{database_url}')
        
        print("✅ Connected to PostgreSQL database")
        print("-" * 50)
        
        # List of infrastructure tables to check
        infrastructure_tables = [
            'infrastructure_snapshots',
            'api_queries', 
            'infrastructure_embeddings',
            'infrastructure_documents',
            'infrastructure_progress'
        ]
        
        # Check each table
        for table_name in infrastructure_tables:
            query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = $1
                );
            """
            exists = await conn.fetchval(query, table_name)
            
            if exists:
                # Get row count
                count_query = f"SELECT COUNT(*) FROM {table_name}"
                count = await conn.fetchval(count_query)
                
                # Get column information
                column_query = """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = $1
                    ORDER BY ordinal_position;
                """
                columns = await conn.fetch(column_query, table_name)
                
                print(f"✅ Table '{table_name}' exists")
                print(f"   - Rows: {count}")
                print(f"   - Columns: {len(columns)}")
                
                if table_name == 'infrastructure_snapshots':
                    print("   - Key columns:")
                    for col in columns[:5]:  # Show first 5 columns
                        print(f"     • {col['column_name']} ({col['data_type']})")
            else:
                print(f"❌ Table '{table_name}' does NOT exist")
        
        print("-" * 50)
        
        # Check if pgvector extension is available
        ext_query = """
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            );
        """
        has_vector = await conn.fetchval(ext_query)
        
        if has_vector:
            print("✅ pgvector extension is installed")
        else:
            print("⚠️  pgvector extension is NOT installed (embeddings will use arrays)")
        
        # Check alembic version
        version_query = """
            SELECT version_num FROM alembic_version;
        """
        try:
            version = await conn.fetchval(version_query)
            print(f"✅ Current migration version: {version}")
        except:
            print("❌ No alembic_version table found")
        
        await conn.close()
        print("-" * 50)
        print("✅ Database check complete!")
        
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print(f"   Database URL: {database_url}")

if __name__ == "__main__":
    asyncio.run(check_tables())