"""Database indexing configuration for performance optimization."""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class IndexDefinition:
    """Definition of a database index."""
    name: str
    table: str
    columns: list[str]
    unique: bool = False
    partial: str = None  # Partial index condition
    include: list[str] = None  # Additional columns to include
    method: str = "btree"  # btree, hash, gin, gist, etc.


class DatabaseIndexManager:
    """Manage database indexes for optimal query performance."""

    def __init__(self):
        """Initialize index manager."""
        self.postgresql_indexes = self._define_postgresql_indexes()
        self.neo4j_indexes = self._define_neo4j_indexes()
        self.index_statistics = {}

    def _define_postgresql_indexes(self) -> list[IndexDefinition]:
        """Define PostgreSQL indexes for optimal performance."""
        return [
            # Organizations table indexes
            IndexDefinition(
                name="idx_organizations_name_trgm",
                table="organizations",
                columns=["name"],
                method="gin",  # For fuzzy text search
                include=["id", "organization_type_id"]
            ),
            IndexDefinition(
                name="idx_organizations_id",
                table="organizations",
                columns=["id"],
                unique=True,
                method="btree"
            ),
            IndexDefinition(
                name="idx_organizations_updated_at",
                table="organizations",
                columns=["updated_at"],
                method="btree"
            ),

            # Configurations table indexes
            IndexDefinition(
                name="idx_configurations_org_id",
                table="configurations",
                columns=["organization_id"],
                method="btree",
                include=["name", "configuration_type_id"]
            ),
            IndexDefinition(
                name="idx_configurations_name_trgm",
                table="configurations",
                columns=["name"],
                method="gin"
            ),
            IndexDefinition(
                name="idx_configurations_type_org",
                table="configurations",
                columns=["configuration_type_id", "organization_id"],
                method="btree"
            ),
            IndexDefinition(
                name="idx_configurations_updated_at",
                table="configurations",
                columns=["updated_at"],
                method="btree",
                partial="archived = false"  # Only index active configurations
            ),

            # Passwords table indexes
            IndexDefinition(
                name="idx_passwords_org_id",
                table="passwords",
                columns=["organization_id"],
                method="btree"
            ),
            IndexDefinition(
                name="idx_passwords_resource_id",
                table="passwords",
                columns=["resource_id", "resource_type"],
                method="btree"
            ),
            IndexDefinition(
                name="idx_passwords_name_search",
                table="passwords",
                columns=["name"],
                method="gin"
            ),

            # Flexible assets table indexes
            IndexDefinition(
                name="idx_flexible_assets_org_id",
                table="flexible_assets",
                columns=["organization_id"],
                method="btree"
            ),
            IndexDefinition(
                name="idx_flexible_assets_type_id",
                table="flexible_assets",
                columns=["flexible_asset_type_id"],
                method="btree"
            ),
            IndexDefinition(
                name="idx_flexible_assets_traits",
                table="flexible_assets",
                columns=["traits"],
                method="gin"  # For JSONB queries
            ),

            # Query cache table indexes
            IndexDefinition(
                name="idx_query_cache_key",
                table="query_cache",
                columns=["cache_key"],
                unique=True,
                method="hash"  # Fast exact match lookups
            ),
            IndexDefinition(
                name="idx_query_cache_expires",
                table="query_cache",
                columns=["expires_at"],
                method="btree",
                partial="expires_at > NOW()"
            ),

            # Audit log indexes
            IndexDefinition(
                name="idx_audit_log_timestamp",
                table="audit_log",
                columns=["created_at"],
                method="brin"  # Block range index for time-series data
            ),
            IndexDefinition(
                name="idx_audit_log_user_action",
                table="audit_log",
                columns=["user_id", "action"],
                method="btree"
            ),

            # Search history indexes for query learning
            IndexDefinition(
                name="idx_search_history_user",
                table="search_history",
                columns=["user_id", "created_at"],
                method="btree"
            ),
            IndexDefinition(
                name="idx_search_history_query_hash",
                table="search_history",
                columns=["query_hash"],
                method="hash"
            ),

            # Performance metrics table
            IndexDefinition(
                name="idx_performance_metrics_timestamp",
                table="performance_metrics",
                columns=["timestamp"],
                method="brin"
            ),
            IndexDefinition(
                name="idx_performance_metrics_query_type",
                table="performance_metrics",
                columns=["query_type", "timestamp"],
                method="btree"
            )
        ]

    def _define_neo4j_indexes(self) -> list[dict[str, Any]]:
        """Define Neo4j indexes and constraints for optimal performance."""
        return [
            # Node indexes
            {
                "type": "index",
                "label": "Organization",
                "properties": ["id"],
                "name": "organization_id_index",
                "unique": True
            },
            {
                "type": "index",
                "label": "Organization",
                "properties": ["name"],
                "name": "organization_name_index",
                "fulltext": True  # For fuzzy search
            },
            {
                "type": "index",
                "label": "Configuration",
                "properties": ["id"],
                "name": "configuration_id_index",
                "unique": True
            },
            {
                "type": "index",
                "label": "Configuration",
                "properties": ["name", "type"],
                "name": "configuration_name_type_index",
                "composite": True
            },
            {
                "type": "index",
                "label": "Password",
                "properties": ["id"],
                "name": "password_id_index",
                "unique": True
            },
            {
                "type": "index",
                "label": "Asset",
                "properties": ["id"],
                "name": "asset_id_index",
                "unique": True
            },
            {
                "type": "index",
                "label": "Asset",
                "properties": ["type", "organization_id"],
                "name": "asset_type_org_index",
                "composite": True
            },

            # Relationship indexes
            {
                "type": "relationship_index",
                "relationship": "DEPENDS_ON",
                "properties": ["created_at"],
                "name": "depends_on_timestamp_index"
            },
            {
                "type": "relationship_index",
                "relationship": "BELONGS_TO",
                "properties": ["role"],
                "name": "belongs_to_role_index"
            },
            {
                "type": "relationship_index",
                "relationship": "CONNECTS_TO",
                "properties": ["port", "protocol"],
                "name": "connects_to_port_protocol_index"
            },

            # Constraints
            {
                "type": "constraint",
                "label": "Organization",
                "properties": ["id"],
                "constraint_type": "uniqueness"
            },
            {
                "type": "constraint",
                "label": "Configuration",
                "properties": ["id"],
                "constraint_type": "uniqueness"
            },
            {
                "type": "constraint",
                "label": "Password",
                "properties": ["id"],
                "constraint_type": "uniqueness"
            }
        ]

    def generate_postgresql_ddl(self) -> list[str]:
        """Generate PostgreSQL DDL statements for creating indexes."""
        ddl_statements = []

        # Enable required extensions
        ddl_statements.extend([
            "-- Enable required PostgreSQL extensions",
            "CREATE EXTENSION IF NOT EXISTS pg_trgm;",  # For trigram similarity
            "CREATE EXTENSION IF NOT EXISTS btree_gin;",  # For multi-column GIN indexes
            "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;",  # For query analysis
            ""
        ])

        for index in self.postgresql_indexes:
            # Build CREATE INDEX statement
            stmt = "CREATE"

            if index.unique:
                stmt += " UNIQUE"

            stmt += f" INDEX IF NOT EXISTS {index.name}"
            stmt += f" ON {index.table}"

            # Add method
            stmt += f" USING {index.method}"

            # Add columns
            if index.method == "gin" and len(index.columns) == 1:
                # For text search indexes
                stmt += f" ({index.columns[0]} gin_trgm_ops)"
            else:
                stmt += f" ({', '.join(index.columns)})"

            # Add INCLUDE clause if specified
            if index.include:
                stmt += f" INCLUDE ({', '.join(index.include)})"

            # Add WHERE clause for partial indexes
            if index.partial:
                stmt += f" WHERE {index.partial}"

            stmt += ";"
            ddl_statements.append(stmt)

        # Add comments
        ddl_statements.extend([
            "",
            "-- Analyze tables to update statistics",
            "ANALYZE organizations;",
            "ANALYZE configurations;",
            "ANALYZE passwords;",
            "ANALYZE flexible_assets;",
            ""
        ])

        return ddl_statements

    def generate_neo4j_cypher(self) -> list[str]:
        """Generate Neo4j Cypher statements for creating indexes."""
        cypher_statements = []

        for index_def in self.neo4j_indexes:
            if index_def["type"] == "index":
                if index_def.get("unique"):
                    # Create unique constraint (which also creates an index)
                    stmt = f"CREATE CONSTRAINT {index_def['name']} IF NOT EXISTS"
                    stmt += f" FOR (n:{index_def['label']})"
                    stmt += f" REQUIRE n.{index_def['properties'][0]} IS UNIQUE"
                elif index_def.get("fulltext"):
                    # Create fulltext index
                    props = ", ".join([f"n.{p}" for p in index_def['properties']])
                    stmt = f"CREATE FULLTEXT INDEX {index_def['name']} IF NOT EXISTS"
                    stmt += f" FOR (n:{index_def['label']}) ON EACH [{props}]"
                elif index_def.get("composite"):
                    # Create composite index
                    props = ", ".join([f"n.{p}" for p in index_def['properties']])
                    stmt = f"CREATE INDEX {index_def['name']} IF NOT EXISTS"
                    stmt += f" FOR (n:{index_def['label']}) ON ({props})"
                else:
                    # Create single property index
                    stmt = f"CREATE INDEX {index_def['name']} IF NOT EXISTS"
                    stmt += f" FOR (n:{index_def['label']})"
                    stmt += f" ON (n.{index_def['properties'][0]})"

                cypher_statements.append(stmt + ";")

            elif index_def["type"] == "relationship_index":
                # Create relationship index
                props = ", ".join([f"r.{p}" for p in index_def['properties']])
                stmt = f"CREATE INDEX {index_def['name']} IF NOT EXISTS"
                stmt += f" FOR ()-[r:{index_def['relationship']}]-()"
                stmt += f" ON ({props})"
                cypher_statements.append(stmt + ";")

            elif index_def["type"] == "constraint":
                # Already handled in unique index creation
                pass

        return cypher_statements

    def get_index_optimization_queries(self) -> dict[str, list[str]]:
        """Get database-specific queries for index optimization."""
        return {
            "postgresql": [
                # Update table statistics
                "VACUUM ANALYZE;",

                # Reindex tables periodically
                "REINDEX TABLE CONCURRENTLY organizations;",
                "REINDEX TABLE CONCURRENTLY configurations;",

                # Monitor index usage
                """
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan as index_scans,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
                    CASE
                        WHEN idx_scan = 0 THEN 'UNUSED'
                        WHEN idx_scan < 100 THEN 'RARELY_USED'
                        ELSE 'ACTIVE'
                    END as usage_status
                FROM pg_stat_user_indexes
                ORDER BY idx_scan DESC;
                """,

                # Find missing indexes
                """
                SELECT
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    correlation
                FROM pg_stats
                WHERE
                    schemaname = 'public'
                    AND n_distinct > 100
                    AND correlation < 0.1
                ORDER BY n_distinct DESC;
                """,

                # Monitor slow queries
                """
                SELECT
                    query,
                    calls,
                    mean_exec_time,
                    total_exec_time,
                    rows
                FROM pg_stat_statements
                WHERE mean_exec_time > 200  -- Queries slower than 200ms
                ORDER BY mean_exec_time DESC
                LIMIT 20;
                """
            ],

            "neo4j": [
                # Show index status
                "SHOW INDEXES;",

                # Show constraints
                "SHOW CONSTRAINTS;",

                # Analyze query execution plan
                "EXPLAIN MATCH (n:Organization)-[:OWNS]->(c:Configuration) RETURN n, c;",

                # Profile query performance
                "PROFILE MATCH (n:Organization)-[:OWNS]->(c:Configuration) RETURN n, c;",

                # Database statistics
                "CALL db.stats.retrieve('GRAPH COUNTS');",

                # Index usage statistics
                "CALL db.index.usage('organization_name_index');"
            ]
        }

    def get_monitoring_queries(self) -> dict[str, str]:
        """Get queries for monitoring index performance."""
        return {
            "postgresql_cache_hit_ratio": """
                SELECT
                    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as cache_hit_ratio
                FROM pg_statio_user_tables;
            """,

            "postgresql_index_hit_ratio": """
                SELECT
                    sum(idx_blks_hit) / (sum(idx_blks_hit) + sum(idx_blks_read)) as index_hit_ratio
                FROM pg_statio_user_indexes;
            """,

            "postgresql_table_bloat": """
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
            """,

            "neo4j_db_size": """
                CALL apoc.meta.stats() YIELD nodeCount, relCount, propertyKeyCount
                RETURN nodeCount, relCount, propertyKeyCount;
            """,

            "neo4j_index_population": """
                SHOW INDEXES YIELD name, state, populationPercent
                WHERE state <> 'ONLINE'
                RETURN name, state, populationPercent;
            """
        }


# Export main class
__all__ = ["DatabaseIndexManager", "IndexDefinition"]
