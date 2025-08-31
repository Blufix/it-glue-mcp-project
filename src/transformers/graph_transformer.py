"""Transform IT Glue data into Neo4j graph relationships."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from neo4j import AsyncGraphDatabase
from src.config.settings import settings

logger = logging.getLogger(__name__)


class GraphTransformer:
    """Transform IT Glue entities into graph relationships."""
    
    def __init__(self, neo4j_uri: Optional[str] = None):
        """Initialize graph transformer.
        
        Args:
            neo4j_uri: Neo4j connection URI
        """
        self.neo4j_uri = neo4j_uri or settings.NEO4J_URI
        self.driver = None
        
    async def connect(self):
        """Connect to Neo4j."""
        if not self.driver:
            self.driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            logger.info("Connected to Neo4j")
    
    async def disconnect(self):
        """Disconnect from Neo4j."""
        if self.driver:
            await self.driver.close()
            self.driver = None
            logger.info("Disconnected from Neo4j")
    
    async def create_organization_node(self, org: Dict[str, Any]) -> bool:
        """Create organization node in graph.
        
        Args:
            org: Organization data
            
        Returns:
            Success status
        """
        async with self.driver.session() as session:
            query = """
                MERGE (o:Organization {id: $id})
                SET o.name = $name,
                    o.type = $type,
                    o.status = $status,
                    o.updated_at = $updated_at
                RETURN o
            """
            
            try:
                await session.run(
                    query,
                    id=org["id"],
                    name=org.get("name", ""),
                    type=org.get("organization_type", ""),
                    status=org.get("organization_status", ""),
                    updated_at=datetime.utcnow().isoformat()
                )
                return True
            except Exception as e:
                logger.error(f"Failed to create organization node: {e}")
                return False
    
    async def create_configuration_node(self, config: Dict[str, Any]) -> bool:
        """Create configuration node and relationships.
        
        Args:
            config: Configuration data
            
        Returns:
            Success status
        """
        async with self.driver.session() as session:
            # Create configuration node
            create_query = """
                MERGE (c:Configuration {id: $id})
                SET c.name = $name,
                    c.hostname = $hostname,
                    c.type = $type,
                    c.status = $status,
                    c.os = $os,
                    c.ip_address = $ip,
                    c.updated_at = $updated_at
                RETURN c
            """
            
            # Create relationship to organization
            relate_query = """
                MATCH (o:Organization {id: $org_id})
                MATCH (c:Configuration {id: $config_id})
                MERGE (o)-[r:HAS_CONFIGURATION]->(c)
                SET r.updated_at = $updated_at
                RETURN r
            """
            
            try:
                # Create node
                await session.run(
                    create_query,
                    id=config["id"],
                    name=config.get("name", ""),
                    hostname=config.get("hostname", ""),
                    type=config.get("configuration_type", ""),
                    status=config.get("configuration_status", ""),
                    os=config.get("operating_system", ""),
                    ip=config.get("ip_address", ""),
                    updated_at=datetime.utcnow().isoformat()
                )
                
                # Create relationship if organization exists
                if config.get("organization_id"):
                    await session.run(
                        relate_query,
                        org_id=config["organization_id"],
                        config_id=config["id"],
                        updated_at=datetime.utcnow().isoformat()
                    )
                
                return True
            except Exception as e:
                logger.error(f"Failed to create configuration node: {e}")
                return False
    
    async def create_asset_relationships(self, asset: Dict[str, Any]) -> bool:
        """Create flexible asset node and relationships.
        
        Args:
            asset: Flexible asset data
            
        Returns:
            Success status
        """
        async with self.driver.session() as session:
            # Create asset node
            create_query = """
                MERGE (a:Asset {id: $id})
                SET a.name = $name,
                    a.type_id = $type_id,
                    a.traits = $traits,
                    a.updated_at = $updated_at
                RETURN a
            """
            
            # Relate to organization
            org_relate_query = """
                MATCH (o:Organization {id: $org_id})
                MATCH (a:Asset {id: $asset_id})
                MERGE (o)-[r:OWNS_ASSET]->(a)
                SET r.updated_at = $updated_at
                RETURN r
            """
            
            try:
                # Create node
                await session.run(
                    create_query,
                    id=asset["id"],
                    name=asset.get("name", ""),
                    type_id=asset.get("flexible_asset_type_id", ""),
                    traits=str(asset.get("traits", {})),
                    updated_at=datetime.utcnow().isoformat()
                )
                
                # Create organization relationship
                if asset.get("organization_id"):
                    await session.run(
                        org_relate_query,
                        org_id=asset["organization_id"],
                        asset_id=asset["id"],
                        updated_at=datetime.utcnow().isoformat()
                    )
                
                # Parse traits for additional relationships
                await self._create_trait_relationships(session, asset)
                
                return True
            except Exception as e:
                logger.error(f"Failed to create asset relationships: {e}")
                return False
    
    async def _create_trait_relationships(self, session, asset: Dict[str, Any]):
        """Create relationships based on asset traits.
        
        Args:
            session: Neo4j session
            asset: Asset data with traits
        """
        traits = asset.get("traits", {})
        
        # Look for configuration references
        for key, value in traits.items():
            if "configuration" in key.lower() and value:
                # Try to create relationship to configuration
                query = """
                    MATCH (a:Asset {id: $asset_id})
                    MATCH (c:Configuration {id: $config_id})
                    MERGE (a)-[r:RELATES_TO]->(c)
                    SET r.trait_name = $trait_name,
                        r.updated_at = $updated_at
                    RETURN r
                """
                
                try:
                    await session.run(
                        query,
                        asset_id=asset["id"],
                        config_id=str(value),
                        trait_name=key,
                        updated_at=datetime.utcnow().isoformat()
                    )
                except:
                    pass  # Ignore if configuration doesn't exist
    
    async def create_password_relationships(self, password: Dict[str, Any]) -> bool:
        """Create password node with security constraints.
        
        Args:
            password: Password data (without actual password)
            
        Returns:
            Success status
        """
        async with self.driver.session() as session:
            # Create password node (no actual password stored)
            create_query = """
                MERGE (p:Password {id: $id})
                SET p.name = $name,
                    p.username = $username,
                    p.category = $category,
                    p.url = $url,
                    p.updated_at = $updated_at
                RETURN p
            """
            
            # Relate to organization
            relate_query = """
                MATCH (o:Organization {id: $org_id})
                MATCH (p:Password {id: $pwd_id})
                MERGE (o)-[r:HAS_PASSWORD]->(p)
                SET r.updated_at = $updated_at
                RETURN r
            """
            
            try:
                await session.run(
                    create_query,
                    id=password["id"],
                    name=password.get("name", ""),
                    username=password.get("username", ""),
                    category=password.get("password_category", ""),
                    url=password.get("url", ""),
                    updated_at=datetime.utcnow().isoformat()
                )
                
                if password.get("organization_id"):
                    await session.run(
                        relate_query,
                        org_id=password["organization_id"],
                        pwd_id=password["id"],
                        updated_at=datetime.utcnow().isoformat()
                    )
                
                return True
            except Exception as e:
                logger.error(f"Failed to create password relationships: {e}")
                return False
    
    async def create_document_relationships(self, document: Dict[str, Any]) -> bool:
        """Create document node and relationships.
        
        Args:
            document: Document data
            
        Returns:
            Success status
        """
        async with self.driver.session() as session:
            create_query = """
                MERGE (d:Document {id: $id})
                SET d.name = $name,
                    d.folder = $folder,
                    d.created_by = $created_by,
                    d.updated_at = $updated_at
                RETURN d
            """
            
            relate_query = """
                MATCH (o:Organization {id: $org_id})
                MATCH (d:Document {id: $doc_id})
                MERGE (o)-[r:HAS_DOCUMENT]->(d)
                SET r.updated_at = $updated_at
                RETURN r
            """
            
            try:
                await session.run(
                    create_query,
                    id=document["id"],
                    name=document.get("name", ""),
                    folder=document.get("folder_name", ""),
                    created_by=document.get("created_by", ""),
                    updated_at=datetime.utcnow().isoformat()
                )
                
                if document.get("organization_id"):
                    await session.run(
                        relate_query,
                        org_id=document["organization_id"],
                        doc_id=document["id"],
                        updated_at=datetime.utcnow().isoformat()
                    )
                
                return True
            except Exception as e:
                logger.error(f"Failed to create document relationships: {e}")
                return False
    
    async def find_relationships(
        self,
        entity_id: str,
        depth: int = 2
    ) -> List[Dict[str, Any]]:
        """Find all relationships for an entity.
        
        Args:
            entity_id: Entity ID to search from
            depth: Maximum traversal depth
            
        Returns:
            List of related entities
        """
        async with self.driver.session() as session:
            query = f"""
                MATCH path = (start {{id: $id}})-[*1..{depth}]-(related)
                RETURN DISTINCT 
                    related.id as id,
                    related.name as name,
                    labels(related)[0] as type,
                    length(path) as distance
                ORDER BY distance
                LIMIT 100
            """
            
            try:
                result = await session.run(query, id=entity_id)
                relationships = []
                
                async for record in result:
                    relationships.append({
                        "id": record["id"],
                        "name": record["name"],
                        "type": record["type"],
                        "distance": record["distance"]
                    })
                
                return relationships
            except Exception as e:
                logger.error(f"Failed to find relationships: {e}")
                return []
    
    async def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """Find shortest path between two entities.
        
        Args:
            start_id: Starting entity ID
            end_id: Ending entity ID
            max_depth: Maximum path length
            
        Returns:
            Path as list of nodes, or None if no path exists
        """
        async with self.driver.session() as session:
            query = f"""
                MATCH path = shortestPath(
                    (start {{id: $start_id}})-[*..{max_depth}]-(end {{id: $end_id}})
                )
                RETURN [node in nodes(path) | {{
                    id: node.id,
                    name: node.name,
                    type: labels(node)[0]
                }}] as path
            """
            
            try:
                result = await session.run(
                    query,
                    start_id=start_id,
                    end_id=end_id
                )
                
                record = await result.single()
                if record:
                    return record["path"]
                
                return None
            except Exception as e:
                logger.error(f"Failed to find path: {e}")
                return None