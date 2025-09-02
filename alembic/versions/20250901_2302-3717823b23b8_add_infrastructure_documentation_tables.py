"""add_infrastructure_documentation_tables

Revision ID: 3717823b23b8
Revises: 23ad7dcf2579
Create Date: 2025-09-01 23:02:50.044814

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3717823b23b8'
down_revision: Union[str, None] = '23ad7dcf2579'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Skip pgvector for now - will use regular arrays instead
    # op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Create infrastructure_snapshots table
    op.create_table('infrastructure_snapshots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('organization_name', sa.String(), nullable=False),
        sa.Column('snapshot_type', sa.String(), nullable=False),  # 'full' or 'partial'
        sa.Column('snapshot_data', sa.JSON(), nullable=False),
        sa.Column('resource_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),  # 'in_progress', 'completed', 'failed'
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('document_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_infra_org_created', 'infrastructure_snapshots', ['organization_id', 'created_at'], unique=False)
    op.create_index('idx_infra_status', 'infrastructure_snapshots', ['status'], unique=False)
    
    # Create api_queries table for tracking infrastructure documentation queries
    op.create_table('api_queries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('snapshot_id', sa.UUID(), nullable=False),
        sa.Column('endpoint', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('query_params', sa.JSON(), nullable=True),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['snapshot_id'], ['infrastructure_snapshots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_api_snapshot', 'api_queries', ['snapshot_id'], unique=False)
    op.create_index('idx_api_resource', 'api_queries', ['resource_type', 'created_at'], unique=False)
    
    # Create infrastructure_embeddings table with pgvector support
    op.create_table('infrastructure_embeddings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('snapshot_id', sa.UUID(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=False),
        sa.Column('resource_name', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),  # For pgvector
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['snapshot_id'], ['infrastructure_snapshots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_embed_snapshot', 'infrastructure_embeddings', ['snapshot_id'], unique=False)
    op.create_index('idx_embed_resource', 'infrastructure_embeddings', ['resource_type', 'resource_id'], unique=False)
    
    # Create infrastructure_documents table for generated documentation
    op.create_table('infrastructure_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('snapshot_id', sa.UUID(), nullable=False),
        sa.Column('document_type', sa.String(), nullable=False),  # 'markdown', 'html', 'pdf'
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('itglue_document_id', sa.String(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['snapshot_id'], ['infrastructure_snapshots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_doc_snapshot', 'infrastructure_documents', ['snapshot_id'], unique=False)
    
    # Create infrastructure_progress table for tracking progress
    op.create_table('infrastructure_progress',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('snapshot_id', sa.UUID(), nullable=False),
        sa.Column('operation', sa.String(), nullable=False),
        sa.Column('total_items', sa.Integer(), nullable=True),
        sa.Column('completed_items', sa.Integer(), nullable=True),
        sa.Column('current_item', sa.String(), nullable=True),
        sa.Column('status_message', sa.String(), nullable=True),
        sa.Column('error_count', sa.Integer(), default=0),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['snapshot_id'], ['infrastructure_snapshots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_progress_snapshot', 'infrastructure_progress', ['snapshot_id'], unique=False)
    
    # Add column to existing itglue_entities table to track if included in infrastructure doc
    op.add_column('itglue_entities', sa.Column('included_in_infra_doc', sa.Boolean(), nullable=True, default=False))
    
    # Create indexes for vector similarity search (if using pgvector)
    # Skip vector index for now - pgvector not available
    # op.execute("""
    #     CREATE INDEX IF NOT EXISTS idx_embedding_vector 
    #     ON infrastructure_embeddings 
    #     USING ivfflat (embedding vector_l2_ops)
    #     WITH (lists = 100)
    # """)


def downgrade() -> None:
    # Drop indexes first
    # op.execute("DROP INDEX IF EXISTS idx_embedding_vector")  # Skip - pgvector not available
    
    # Remove column from existing table
    op.drop_column('itglue_entities', 'included_in_infra_doc')
    
    # Drop tables in reverse order of creation (due to foreign keys)
    op.drop_index('idx_progress_snapshot', table_name='infrastructure_progress')
    op.drop_table('infrastructure_progress')
    
    op.drop_index('idx_doc_snapshot', table_name='infrastructure_documents')
    op.drop_table('infrastructure_documents')
    
    op.drop_index('idx_embed_resource', table_name='infrastructure_embeddings')
    op.drop_index('idx_embed_snapshot', table_name='infrastructure_embeddings')
    op.drop_table('infrastructure_embeddings')
    
    op.drop_index('idx_api_resource', table_name='api_queries')
    op.drop_index('idx_api_snapshot', table_name='api_queries')
    op.drop_table('api_queries')
    
    op.drop_index('idx_infra_status', table_name='infrastructure_snapshots')
    op.drop_index('idx_infra_org_created', table_name='infrastructure_snapshots')
    op.drop_table('infrastructure_snapshots')
    
    # Note: We don't drop the pgvector extension as it might be used elsewhere