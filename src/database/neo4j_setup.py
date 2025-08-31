"""Neo4j database setup and schema initialization."""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, SessionExpired

logger = logging.getLogger(__name__)


@dataclass
class Neo4jConfig:
    """Neo4j connection configuration."""
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "itglue"
    max_connection_lifetime: int = 3600
    max_connection_pool_size: int = 50
    connection_acquisition_timeout: int = 60
    

class Neo4jSchemaManager:
    """Manages Neo4j database schema and initialization."""
    
    def __init__(self, config: Neo4jConfig):
        """Initialize schema manager."""
        self.config = config
        self.driver: Optional[Driver] = None
        self._connect()
        
    def _connect(self):
        """Establish connection to Neo4j."""
        try:
            self.driver = GraphDatabase.driver(
                self.config.uri,
                auth=(self.config.username, self.config.password),
                max_connection_lifetime=self.config.max_connection_lifetime,
                max_connection_pool_size=self.config.max_connection_pool_size,
                connection_acquisition_timeout=self.config.connection_acquisition_timeout
            )
            # Verify connectivity
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.config.uri}")
        except ServiceUnavailable as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
            
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Closed Neo4j connection")
            
    def initialize_schema(self):
        """Initialize the complete Neo4j schema."""
        logger.info("Initializing Neo4j schema...")
        
        with self.driver.session(database=self.config.database) as session:
            # Create constraints
            self._create_constraints(session)
            
            # Create indexes
            self._create_indexes(session)
            
            # Create node labels
            self._create_node_labels(session)
            
            # Initialize relationship types
            self._initialize_relationships(session)
            
        logger.info("Neo4j schema initialization complete")
        
    def _create_constraints(self, session: Session):
        """Create uniqueness constraints."""
        constraints = [
            # Organization constraints
            "CREATE CONSTRAINT org_id_unique IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
            "CREATE CONSTRAINT org_name_unique IF NOT EXISTS FOR (o:Organization) REQUIRE o.name IS UNIQUE",
            
            # Configuration constraints  
            "CREATE CONSTRAINT config_id_unique IF NOT EXISTS FOR (c:Configuration) REQUIRE c.id IS UNIQUE",
            
            # Password constraints
            "CREATE CONSTRAINT password_id_unique IF NOT EXISTS FOR (p:Password) REQUIRE p.id IS UNIQUE",
            
            # Document constraints
            "CREATE CONSTRAINT doc_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            
            # Asset constraints
            "CREATE CONSTRAINT asset_id_unique IF NOT EXISTS FOR (a:Asset) REQUIRE a.id IS UNIQUE",
            
            # Service constraints
            "CREATE CONSTRAINT service_id_unique IF NOT EXISTS FOR (s:Service) REQUIRE s.id IS UNIQUE",
            
            # User constraints
            "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            
            # Network constraints
            "CREATE CONSTRAINT network_id_unique IF NOT EXISTS FOR (n:Network) REQUIRE n.id IS UNIQUE"
        ]
        
        for constraint in constraints:
            try:
                session.run(constraint)
                logger.debug(f"Created constraint: {constraint.split('CONSTRAINT')[1].split('IF')[0].strip()}")
            except Exception as e:
                # Constraint might already exist
                logger.debug(f"Constraint creation skipped: {e}")
                
    def _create_indexes(self, session: Session):
        """Create performance indexes."""
        indexes = [
            # Organization indexes
            "CREATE INDEX org_name_idx IF NOT EXISTS FOR (o:Organization) ON (o.name)",
            "CREATE INDEX org_created_idx IF NOT EXISTS FOR (o:Organization) ON (o.created_at)",
            
            # Configuration indexes
            "CREATE INDEX config_name_idx IF NOT EXISTS FOR (c:Configuration) ON (c.name)",
            "CREATE INDEX config_hostname_idx IF NOT EXISTS FOR (c:Configuration) ON (c.hostname)",
            "CREATE INDEX config_ip_idx IF NOT EXISTS FOR (c:Configuration) ON (c.primary_ip)",
            "CREATE INDEX config_type_idx IF NOT EXISTS FOR (c:Configuration) ON (c.type)",
            "CREATE INDEX config_status_idx IF NOT EXISTS FOR (c:Configuration) ON (c.status)",
            "CREATE INDEX config_org_idx IF NOT EXISTS FOR (c:Configuration) ON (c.organization_id)",
            "CREATE INDEX config_updated_idx IF NOT EXISTS FOR (c:Configuration) ON (c.updated_at)",
            
            # Password indexes
            "CREATE INDEX password_name_idx IF NOT EXISTS FOR (p:Password) ON (p.name)",
            "CREATE INDEX password_username_idx IF NOT EXISTS FOR (p:Password) ON (p.username)",
            "CREATE INDEX password_category_idx IF NOT EXISTS FOR (p:Password) ON (p.category)",
            "CREATE INDEX password_url_idx IF NOT EXISTS FOR (p:Password) ON (p.url)",
            "CREATE INDEX password_updated_idx IF NOT EXISTS FOR (p:Password) ON (p.password_updated_at)",
            
            # Document indexes
            "CREATE INDEX doc_name_idx IF NOT EXISTS FOR (d:Document) ON (d.name)",
            "CREATE INDEX doc_folder_idx IF NOT EXISTS FOR (d:Document) ON (d.folder)",
            "CREATE INDEX doc_type_idx IF NOT EXISTS FOR (d:Document) ON (d.type)",
            "CREATE INDEX doc_updated_idx IF NOT EXISTS FOR (d:Document) ON (d.updated_at)",
            
            # Asset indexes
            "CREATE INDEX asset_name_idx IF NOT EXISTS FOR (a:Asset) ON (a.name)",
            "CREATE INDEX asset_tag_idx IF NOT EXISTS FOR (a:Asset) ON (a.asset_tag)",
            "CREATE INDEX asset_serial_idx IF NOT EXISTS FOR (a:Asset) ON (a.serial_number)",
            
            # Service indexes
            "CREATE INDEX service_name_idx IF NOT EXISTS FOR (s:Service) ON (s.name)",
            "CREATE INDEX service_status_idx IF NOT EXISTS FOR (s:Service) ON (s.status)",
            "CREATE INDEX service_criticality_idx IF NOT EXISTS FOR (s:Service) ON (s.criticality)",
            
            # Composite indexes for common queries
            "CREATE INDEX config_org_type_idx IF NOT EXISTS FOR (c:Configuration) ON (c.organization_id, c.type)",
            "CREATE INDEX password_org_cat_idx IF NOT EXISTS FOR (p:Password) ON (p.organization_id, p.category)",
            
            # Full-text search indexes
            "CREATE FULLTEXT INDEX org_search_idx IF NOT EXISTS FOR (o:Organization) ON EACH [o.name, o.description]",
            "CREATE FULLTEXT INDEX config_search_idx IF NOT EXISTS FOR (c:Configuration) ON EACH [c.name, c.hostname, c.notes]",
            "CREATE FULLTEXT INDEX doc_search_idx IF NOT EXISTS FOR (d:Document) ON EACH [d.name, d.content, d.folder]"
        ]
        
        for index in indexes:
            try:
                session.run(index)
                logger.debug(f"Created index: {index.split('INDEX')[1].split('IF')[0].strip()}")
            except Exception as e:
                logger.debug(f"Index creation skipped: {e}")
                
    def _create_node_labels(self, session: Session):
        """Ensure all node labels exist with sample nodes."""
        # This creates the labels if they don't exist
        node_types = [
            ("Organization", {"id": "sample-org", "name": "Sample Organization", "created_at": "2024-01-01"}),
            ("Configuration", {"id": "sample-config", "name": "Sample Server", "type": "Server"}),
            ("Password", {"id": "sample-pwd", "name": "Sample Password", "category": "System"}),
            ("Document", {"id": "sample-doc", "name": "Sample Document", "type": "Manual"}),
            ("Asset", {"id": "sample-asset", "name": "Sample Asset", "asset_tag": "A001"}),
            ("Service", {"id": "sample-svc", "name": "Sample Service", "status": "active"}),
            ("User", {"id": "sample-user", "name": "Sample User", "email": "user@example.com"}),
            ("Network", {"id": "sample-net", "name": "Sample Network", "cidr": "10.0.0.0/24"}),
            ("Application", {"id": "sample-app", "name": "Sample Application", "version": "1.0"}),
            ("Database", {"id": "sample-db", "name": "Sample Database", "engine": "PostgreSQL"})
        ]
        
        for label, properties in node_types:
            # Create or merge sample node to ensure label exists
            query = f"""
                MERGE (n:{label} {{id: $id}})
                ON CREATE SET n += $properties
                RETURN n
            """
            session.run(query, id=properties["id"], properties=properties)
            logger.debug(f"Ensured node label exists: {label}")
            
    def _initialize_relationships(self, session: Session):
        """Initialize relationship types with sample relationships."""
        relationships = [
            ("Configuration", "sample-config", "BELONGS_TO", "Organization", "sample-org"),
            ("Password", "sample-pwd", "BELONGS_TO", "Organization", "sample-org"),
            ("Document", "sample-doc", "BELONGS_TO", "Organization", "sample-org"),
            ("Asset", "sample-asset", "BELONGS_TO", "Organization", "sample-org"),
            ("Service", "sample-svc", "DEPENDS_ON", "Configuration", "sample-config"),
            ("Configuration", "sample-config", "HOSTED_ON", "Asset", "sample-asset"),
            ("Application", "sample-app", "CONNECTS_TO", "Database", "sample-db"),
            ("User", "sample-user", "AUTHENTICATES", "Application", "sample-app"),
            ("Service", "sample-svc", "USES", "Database", "sample-db"),
            ("Network", "sample-net", "CONTAINS", "Configuration", "sample-config")
        ]
        
        for source_label, source_id, rel_type, target_label, target_id in relationships:
            query = f"""
                MATCH (source:{source_label} {{id: $source_id}})
                MATCH (target:{target_label} {{id: $target_id}})
                MERGE (source)-[r:{rel_type}]->(target)
                ON CREATE SET r.created_at = datetime()
                RETURN type(r) as relationship
            """
            try:
                result = session.run(
                    query,
                    source_id=source_id,
                    target_id=target_id
                )
                logger.debug(f"Ensured relationship exists: {rel_type}")
            except Exception as e:
                logger.debug(f"Relationship creation skipped: {e}")
                
    def import_data(self, data: Dict[str, List[Dict[str, Any]]]):
        """Import IT Glue data into Neo4j."""
        logger.info("Starting data import to Neo4j...")
        
        with self.driver.session(database=self.config.database) as session:
            # Import organizations
            if "organizations" in data:
                self._import_organizations(session, data["organizations"])
                
            # Import configurations
            if "configurations" in data:
                self._import_configurations(session, data["configurations"])
                
            # Import passwords
            if "passwords" in data:
                self._import_passwords(session, data["passwords"])
                
            # Import documents
            if "documents" in data:
                self._import_documents(session, data["documents"])
                
            # Create relationships
            self._create_relationships(session, data)
            
        logger.info("Data import complete")
        
    def _import_organizations(self, session: Session, organizations: List[Dict[str, Any]]):
        """Import organization nodes."""
        query = """
            UNWIND $organizations as org
            MERGE (o:Organization {id: org.id})
            SET o += org
            RETURN count(o) as imported
        """
        
        result = session.run(query, organizations=organizations)
        count = result.single()["imported"]
        logger.info(f"Imported {count} organizations")
        
    def _import_configurations(self, session: Session, configurations: List[Dict[str, Any]]):
        """Import configuration nodes."""
        query = """
            UNWIND $configurations as config
            MERGE (c:Configuration {id: config.id})
            SET c += config
            WITH c, config
            MATCH (o:Organization {id: config.organization_id})
            MERGE (c)-[:BELONGS_TO]->(o)
            RETURN count(c) as imported
        """
        
        result = session.run(query, configurations=configurations)
        count = result.single()["imported"]
        logger.info(f"Imported {count} configurations")
        
    def _import_passwords(self, session: Session, passwords: List[Dict[str, Any]]):
        """Import password nodes."""
        query = """
            UNWIND $passwords as pwd
            MERGE (p:Password {id: pwd.id})
            SET p += pwd
            WITH p, pwd
            MATCH (o:Organization {id: pwd.organization_id})
            MERGE (p)-[:BELONGS_TO]->(o)
            RETURN count(p) as imported
        """
        
        result = session.run(query, passwords=passwords)
        count = result.single()["imported"]
        logger.info(f"Imported {count} passwords")
        
    def _import_documents(self, session: Session, documents: List[Dict[str, Any]]):
        """Import document nodes."""
        query = """
            UNWIND $documents as doc
            MERGE (d:Document {id: doc.id})
            SET d += doc
            WITH d, doc
            MATCH (o:Organization {id: doc.organization_id})
            MERGE (d)-[:BELONGS_TO]->(o)
            RETURN count(d) as imported
        """
        
        result = session.run(query, documents=documents)
        count = result.single()["imported"]
        logger.info(f"Imported {count} documents")
        
    def _create_relationships(self, session: Session, data: Dict[str, Any]):
        """Create relationships between nodes."""
        # Create DEPENDS_ON relationships based on configuration dependencies
        if "dependencies" in data:
            query = """
                UNWIND $deps as dep
                MATCH (source:Configuration {id: dep.source_id})
                MATCH (target:Configuration {id: dep.target_id})
                MERGE (source)-[r:DEPENDS_ON]->(target)
                SET r.created_at = datetime()
                RETURN count(r) as created
            """
            result = session.run(query, deps=data["dependencies"])
            count = result.single()["created"]
            logger.info(f"Created {count} dependency relationships")
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.driver.session(database=self.config.database) as session:
            # Count nodes by label
            node_counts = {}
            labels = ["Organization", "Configuration", "Password", "Document", 
                     "Asset", "Service", "User", "Network", "Application", "Database"]
            
            for label in labels:
                query = f"MATCH (n:{label}) RETURN count(n) as count"
                result = session.run(query)
                node_counts[label] = result.single()["count"]
                
            # Count relationships
            rel_query = """
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
            """
            result = session.run(rel_query)
            rel_counts = {record["type"]: record["count"] for record in result}
            
            # Get database size
            size_query = """
                CALL apoc.meta.stats()
                YIELD nodeCount, relCount, propertyKeyCount
                RETURN nodeCount, relCount, propertyKeyCount
            """
            try:
                result = session.run(size_query)
                stats = result.single()
                total_stats = {
                    "total_nodes": stats["nodeCount"],
                    "total_relationships": stats["relCount"],
                    "property_keys": stats["propertyKeyCount"]
                }
            except:
                # APOC might not be installed
                total_stats = {
                    "total_nodes": sum(node_counts.values()),
                    "total_relationships": sum(rel_counts.values())
                }
                
            return {
                "nodes": node_counts,
                "relationships": rel_counts,
                "totals": total_stats
            }
            
    def clear_database(self):
        """Clear all data from the database (use with caution!)."""
        with self.driver.session(database=self.config.database) as session:
            # Delete all relationships first
            session.run("MATCH ()-[r]->() DELETE r")
            
            # Then delete all nodes
            session.run("MATCH (n) DELETE n")
            
            logger.warning("Cleared all data from Neo4j database")
            
    def create_backup(self, backup_path: str):
        """Create a backup of the database."""
        # This would typically be done via neo4j-admin tool
        logger.info(f"Backup functionality should be implemented via neo4j-admin dump")
        
    def health_check(self) -> bool:
        """Check if Neo4j is healthy and accessible."""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as health")
                return result.single()["health"] == 1
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return False