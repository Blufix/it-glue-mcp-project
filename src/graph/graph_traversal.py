"""Complex graph traversal queries for Neo4j with impact analysis and dependency mapping."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from neo4j import AsyncDriver, AsyncGraphDatabase

logger = logging.getLogger(__name__)


class TraversalType(Enum):
    """Types of graph traversal operations."""
    IMPACT_ANALYSIS = "impact"  # What breaks if X fails
    DEPENDENCY_TREE = "dependency"  # What does X depend on
    SERVICE_TOPOLOGY = "topology"  # Full service map
    ROOT_CAUSE = "root_cause"  # Find potential root causes
    BLAST_RADIUS = "blast_radius"  # What's affected by change


@dataclass
class TraversalConfig:
    """Configuration for graph traversal."""
    max_depth: int = 5
    detect_cycles: bool = True
    include_indirect: bool = True
    relationship_types: list[str] = field(default_factory=list)
    node_filters: dict[str, Any] = field(default_factory=dict)
    path_constraints: list[str] = field(default_factory=list)


@dataclass
class GraphNode:
    """Represents a node in the graph."""
    id: str
    labels: list[str]
    properties: dict[str, Any]
    depth: int = 0
    path_from_root: list[str] = field(default_factory=list)


@dataclass
class GraphRelationship:
    """Represents a relationship in the graph."""
    id: str
    type: str
    start_node_id: str
    end_node_id: str
    properties: dict[str, Any]


@dataclass
class TraversalResult:
    """Result of a graph traversal operation."""
    nodes: list[GraphNode]
    relationships: list[GraphRelationship]
    paths: list[list[str]]  # Node ID paths
    cycles_detected: list[list[str]]
    max_depth_reached: int
    traversal_type: TraversalType
    metadata: dict[str, Any]


class GraphTraversal:
    """Performs complex graph traversal queries on Neo4j."""

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """Initialize graph traversal engine.

        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.uri = neo4j_uri
        self.user = neo4j_user
        self.password = neo4j_password
        self.driver: Optional[AsyncDriver] = None

    async def connect(self) -> None:
        """Connect to Neo4j database."""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # Verify connectivity
            async with self.driver.session() as session:
                await session.run("RETURN 1")
            logger.info("Connected to Neo4j")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Neo4j database."""
        if self.driver:
            await self.driver.close()
            logger.info("Disconnected from Neo4j")

    async def impact_analysis(
        self,
        node_id: str,
        config: Optional[TraversalConfig] = None
    ) -> TraversalResult:
        """Analyze impact of a node failure - what breaks if this fails?

        Args:
            node_id: ID of the node to analyze
            config: Traversal configuration

        Returns:
            TraversalResult with affected nodes and paths
        """
        config = config or TraversalConfig()

        query = """
        MATCH (start)
        WHERE start.id = $node_id
        CALL apoc.path.subgraphAll(start, {
            relationshipFilter: $rel_filter,
            maxLevel: $max_depth,
            bfs: true
        })
        YIELD nodes, relationships

        // Find all paths from start node
        WITH start, nodes, relationships
        MATCH path = (start)-[*1..%d]->(affected)
        WHERE affected IN nodes
        AND ALL(r IN relationships(path) WHERE type(r) IN $rel_types)

        RETURN
            nodes,
            relationships,
            collect(DISTINCT path) as paths,
            max(length(path)) as max_depth
        """ % config.max_depth

        # Default to DEPENDS_ON relationships for impact
        rel_types = config.relationship_types or ['DEPENDS_ON', 'USES', 'REQUIRES']
        rel_filter = '|'.join(f'>{rt}' for rt in rel_types)

        async with self.driver.session() as session:
            result = await session.run(
                query,
                node_id=node_id,
                rel_filter=rel_filter,
                max_depth=config.max_depth,
                rel_types=rel_types
            )

            record = await result.single()

            if not record:
                return TraversalResult(
                    nodes=[],
                    relationships=[],
                    paths=[],
                    cycles_detected=[],
                    max_depth_reached=0,
                    traversal_type=TraversalType.IMPACT_ANALYSIS,
                    metadata={'node_id': node_id}
                )

            # Process results
            nodes = self._process_nodes(record['nodes'])
            relationships = self._process_relationships(record['relationships'])
            paths = self._extract_paths(record['paths'])

            # Detect cycles if enabled
            cycles = []
            if config.detect_cycles:
                cycles = await self._detect_cycles(node_id, paths)

            return TraversalResult(
                nodes=nodes,
                relationships=relationships,
                paths=paths,
                cycles_detected=cycles,
                max_depth_reached=record['max_depth'] or 0,
                traversal_type=TraversalType.IMPACT_ANALYSIS,
                metadata={
                    'node_id': node_id,
                    'affected_count': len(nodes),
                    'critical_paths': self._find_critical_paths(paths)
                }
            )

    async def dependency_tree(
        self,
        node_id: str,
        config: Optional[TraversalConfig] = None
    ) -> TraversalResult:
        """Build dependency tree - what does this node depend on?

        Args:
            node_id: ID of the node to analyze
            config: Traversal configuration

        Returns:
            TraversalResult with dependency tree
        """
        config = config or TraversalConfig()

        query = """
        MATCH (start)
        WHERE start.id = $node_id

        // Find all dependencies with depth tracking
        CALL apoc.path.expandConfig(start, {
            relationshipFilter: $rel_filter,
            maxLevel: $max_depth,
            uniqueness: 'NODE_PATH',
            bfs: false
        })
        YIELD path

        WITH path, length(path) as depth
        UNWIND nodes(path) as node
        WITH node, min(depth) as node_depth, collect(path) as paths

        // Get relationships
        MATCH ()-[r]->()
        WHERE startNode(r) IN [n IN paths | nodes(n)]
        AND endNode(r) IN [n IN paths | nodes(n)]

        RETURN
            collect(DISTINCT node) as nodes,
            collect(DISTINCT r) as relationships,
            paths,
            max(node_depth) as max_depth
        """

        # Reverse direction for dependencies (incoming relationships)
        rel_types = config.relationship_types or ['DEPENDS_ON', 'USES', 'REQUIRES']
        rel_filter = '|'.join(f'<{rt}' for rt in rel_types)

        async with self.driver.session() as session:
            result = await session.run(
                query,
                node_id=node_id,
                rel_filter=rel_filter,
                max_depth=config.max_depth
            )

            record = await result.single()

            if not record:
                return TraversalResult(
                    nodes=[],
                    relationships=[],
                    paths=[],
                    cycles_detected=[],
                    max_depth_reached=0,
                    traversal_type=TraversalType.DEPENDENCY_TREE,
                    metadata={'node_id': node_id}
                )

            nodes = self._process_nodes(record['nodes'])
            relationships = self._process_relationships(record['relationships'])
            paths = self._extract_paths(record['paths'])

            # Build hierarchical tree structure
            tree = self._build_tree_structure(node_id, nodes, relationships)

            return TraversalResult(
                nodes=nodes,
                relationships=relationships,
                paths=paths,
                cycles_detected=[],
                max_depth_reached=record['max_depth'] or 0,
                traversal_type=TraversalType.DEPENDENCY_TREE,
                metadata={
                    'node_id': node_id,
                    'dependency_count': len(nodes) - 1,
                    'tree_structure': tree
                }
            )

    async def service_topology(
        self,
        organization_id: Optional[str] = None,
        config: Optional[TraversalConfig] = None
    ) -> TraversalResult:
        """Map complete service topology for an organization.

        Args:
            organization_id: Optional organization filter
            config: Traversal configuration

        Returns:
            TraversalResult with complete topology
        """
        config = config or TraversalConfig()

        # Build WHERE clause
        where_clause = ""
        if organization_id:
            where_clause = "WHERE n.organization_id = $org_id"

        query = f"""
        // Find all service nodes
        MATCH (n:Configuration)
        {where_clause}

        // Find all connections between services
        OPTIONAL MATCH path = (n)-[r:CONNECTS_TO|DEPENDS_ON|USES|HOSTS*1..{config.max_depth}]-(m:Configuration)
        {where_clause.replace('n.', 'm.') if where_clause else ''}

        WITH collect(DISTINCT n) + collect(DISTINCT m) as all_nodes,
             collect(DISTINCT r) as all_relationships,
             collect(path) as all_paths

        UNWIND all_relationships as rel_list
        UNWIND rel_list as r

        RETURN
            all_nodes as nodes,
            collect(DISTINCT r) as relationships,
            all_paths as paths,
            size(all_nodes) as node_count
        """

        async with self.driver.session() as session:
            params = {}
            if organization_id:
                params['org_id'] = organization_id

            result = await session.run(query, **params)
            record = await result.single()

            if not record or not record['nodes']:
                return TraversalResult(
                    nodes=[],
                    relationships=[],
                    paths=[],
                    cycles_detected=[],
                    max_depth_reached=0,
                    traversal_type=TraversalType.SERVICE_TOPOLOGY,
                    metadata={'organization_id': organization_id}
                )

            nodes = self._process_nodes(record['nodes'])
            relationships = self._process_relationships(record['relationships'])
            paths = self._extract_paths(record['paths'])

            # Analyze topology
            topology_analysis = self._analyze_topology(nodes, relationships)

            return TraversalResult(
                nodes=nodes,
                relationships=relationships,
                paths=paths,
                cycles_detected=topology_analysis['cycles'],
                max_depth_reached=config.max_depth,
                traversal_type=TraversalType.SERVICE_TOPOLOGY,
                metadata={
                    'organization_id': organization_id,
                    'node_count': record['node_count'],
                    'topology_analysis': topology_analysis
                }
            )

    async def find_root_cause(
        self,
        symptom_nodes: list[str],
        config: Optional[TraversalConfig] = None
    ) -> TraversalResult:
        """Find potential root causes for observed symptoms.

        Args:
            symptom_nodes: List of node IDs showing symptoms
            config: Traversal configuration

        Returns:
            TraversalResult with potential root causes
        """
        config = config or TraversalConfig()

        query = """
        // Find all symptom nodes
        MATCH (symptom)
        WHERE symptom.id IN $symptom_ids

        // Trace back through dependencies
        MATCH path = (root)-[*1..%d]->(symptom)
        WHERE ALL(r IN relationships(path) WHERE
            type(r) IN ['DEPENDS_ON', 'USES', 'REQUIRES', 'AFFECTS'])

        // Find common ancestors
        WITH root, collect(DISTINCT symptom) as affected_symptoms,
             collect(path) as paths
        WHERE size(affected_symptoms) >= $min_symptoms

        // Calculate root cause score
        WITH root, affected_symptoms, paths,
             size(affected_symptoms) * 1.0 / $total_symptoms as coverage,
             avg([length(p) for p in paths]) as avg_distance

        RETURN
            root,
            affected_symptoms,
            paths,
            coverage,
            avg_distance,
            coverage / avg_distance as root_cause_score
        ORDER BY root_cause_score DESC
        LIMIT 10
        """ % config.max_depth

        async with self.driver.session() as session:
            result = await session.run(
                query,
                symptom_ids=symptom_nodes,
                min_symptoms=max(1, len(symptom_nodes) // 2),
                total_symptoms=len(symptom_nodes)
            )

            root_causes = []
            all_nodes = set()
            all_relationships = set()
            all_paths = []

            async for record in result:
                root = self._process_node(record['root'])
                root_causes.append({
                    'node': root,
                    'score': record['root_cause_score'],
                    'coverage': record['coverage'],
                    'avg_distance': record['avg_distance'],
                    'affected_symptoms': [
                        self._process_node(s) for s in record['affected_symptoms']
                    ]
                })

                all_nodes.add(root)
                all_nodes.update(record['affected_symptoms'])
                all_paths.extend(self._extract_paths(record['paths']))

            return TraversalResult(
                nodes=list(all_nodes),
                relationships=list(all_relationships),
                paths=all_paths,
                cycles_detected=[],
                max_depth_reached=config.max_depth,
                traversal_type=TraversalType.ROOT_CAUSE,
                metadata={
                    'symptom_nodes': symptom_nodes,
                    'root_causes': root_causes[:5]  # Top 5 root causes
                }
            )

    async def blast_radius(
        self,
        change_node_id: str,
        change_type: str = "update",
        config: Optional[TraversalConfig] = None
    ) -> TraversalResult:
        """Calculate blast radius of a change.

        Args:
            change_node_id: Node being changed
            change_type: Type of change (update, delete, restart)
            config: Traversal configuration

        Returns:
            TraversalResult with blast radius analysis
        """
        config = config or TraversalConfig()

        # Different relationship weights based on change type
        if change_type == "delete":
            rel_weights = {
                'DEPENDS_ON': 1.0,
                'USES': 0.8,
                'REQUIRES': 0.9,
                'CONNECTS_TO': 0.6
            }
        elif change_type == "restart":
            rel_weights = {
                'DEPENDS_ON': 0.7,
                'USES': 0.5,
                'REQUIRES': 0.6,
                'CONNECTS_TO': 0.4
            }
        else:  # update
            rel_weights = {
                'DEPENDS_ON': 0.5,
                'USES': 0.3,
                'REQUIRES': 0.4,
                'CONNECTS_TO': 0.2
            }

        query = """
        MATCH (change)
        WHERE change.id = $node_id

        // Find all potentially affected nodes
        MATCH path = (change)-[*1..%d]-(affected)
        WHERE ALL(r IN relationships(path) WHERE
            type(r) IN $rel_types)

        // Calculate impact score
        WITH affected, path, change,
             reduce(score = 1.0, r in relationships(path) |
                score * CASE type(r)
                    %s
                    ELSE 0.1
                END
             ) as impact_score,
             length(path) as distance

        // Aggregate results
        WITH affected, max(impact_score) as max_impact,
             min(distance) as min_distance,
             collect(path) as paths
        WHERE max_impact > $threshold

        RETURN
            collect(affected) as affected_nodes,
            collect({
                node: affected,
                impact: max_impact,
                distance: min_distance
            }) as impact_analysis,
            paths
        ORDER BY max_impact DESC
        """ % (
            config.max_depth,
            ' '.join([f"WHEN '{k}' THEN {v}" for k, v in rel_weights.items()])
        )

        async with self.driver.session() as session:
            result = await session.run(
                query,
                node_id=change_node_id,
                rel_types=list(rel_weights.keys()),
                threshold=0.1  # Minimum impact threshold
            )

            record = await result.single()

            if not record:
                return TraversalResult(
                    nodes=[],
                    relationships=[],
                    paths=[],
                    cycles_detected=[],
                    max_depth_reached=0,
                    traversal_type=TraversalType.BLAST_RADIUS,
                    metadata={'change_node_id': change_node_id, 'change_type': change_type}
                )

            nodes = self._process_nodes(record['affected_nodes'])
            paths = self._extract_paths(record['paths'])

            # Categorize impact
            impact_categories = {
                'critical': [],
                'high': [],
                'medium': [],
                'low': []
            }

            for item in record['impact_analysis']:
                impact = item['impact']
                if impact > 0.8:
                    impact_categories['critical'].append(item)
                elif impact > 0.6:
                    impact_categories['high'].append(item)
                elif impact > 0.3:
                    impact_categories['medium'].append(item)
                else:
                    impact_categories['low'].append(item)

            return TraversalResult(
                nodes=nodes,
                relationships=[],
                paths=paths,
                cycles_detected=[],
                max_depth_reached=config.max_depth,
                traversal_type=TraversalType.BLAST_RADIUS,
                metadata={
                    'change_node_id': change_node_id,
                    'change_type': change_type,
                    'total_affected': len(nodes),
                    'impact_categories': impact_categories
                }
            )

    async def _detect_cycles(
        self,
        start_node: str,
        paths: list[list[str]]
    ) -> list[list[str]]:
        """Detect cycles in graph paths.

        Args:
            start_node: Starting node ID
            paths: List of paths to check

        Returns:
            List of cycles found
        """
        cycles = []

        for path in paths:
            # Check if any node appears more than once
            seen = set()
            for node_id in path:
                if node_id in seen:
                    # Found a cycle
                    cycle_start = path.index(node_id)
                    cycle = path[cycle_start:]
                    cycles.append(cycle)
                    break
                seen.add(node_id)

        return cycles

    def _process_nodes(self, nodes: list[Any]) -> list[GraphNode]:
        """Process Neo4j nodes into GraphNode objects."""
        processed = []
        for node in nodes:
            if node:
                processed.append(self._process_node(node))
        return processed

    def _process_node(self, node: Any) -> GraphNode:
        """Process a single Neo4j node."""
        return GraphNode(
            id=node.get('id') or str(node.id),
            labels=list(node.labels) if hasattr(node, 'labels') else [],
            properties=dict(node) if node else {}
        )

    def _process_relationships(self, relationships: list[Any]) -> list[GraphRelationship]:
        """Process Neo4j relationships into GraphRelationship objects."""
        processed = []
        for rel in relationships:
            if rel:
                processed.append(GraphRelationship(
                    id=str(rel.id) if hasattr(rel, 'id') else '',
                    type=rel.type if hasattr(rel, 'type') else str(type(rel)),
                    start_node_id=str(rel.start_node.id) if hasattr(rel, 'start_node') else '',
                    end_node_id=str(rel.end_node.id) if hasattr(rel, 'end_node') else '',
                    properties=dict(rel) if rel else {}
                ))
        return processed

    def _extract_paths(self, paths: list[Any]) -> list[list[str]]:
        """Extract node ID paths from Neo4j path objects."""
        extracted = []
        for path in paths:
            if path:
                node_ids = []
                if hasattr(path, 'nodes'):
                    for node in path.nodes:
                        node_ids.append(node.get('id') or str(node.id))
                extracted.append(node_ids)
        return extracted

    def _build_tree_structure(
        self,
        root_id: str,
        nodes: list[GraphNode],
        relationships: list[GraphRelationship]
    ) -> dict[str, Any]:
        """Build hierarchical tree structure from nodes and relationships."""
        # Create adjacency list
        children_map = {}
        for rel in relationships:
            if rel.end_node_id not in children_map:
                children_map[rel.end_node_id] = []
            children_map[rel.end_node_id].append(rel.start_node_id)

        # Build tree recursively
        def build_subtree(node_id: str, visited: set[str]) -> dict[str, Any]:
            if node_id in visited:
                return {'id': node_id, 'cycle_detected': True}

            visited.add(node_id)
            node = next((n for n in nodes if n.id == node_id), None)

            subtree = {
                'id': node_id,
                'labels': node.labels if node else [],
                'properties': node.properties if node else {},
                'children': []
            }

            if node_id in children_map:
                for child_id in children_map[node_id]:
                    subtree['children'].append(build_subtree(child_id, visited.copy()))

            return subtree

        return build_subtree(root_id, set())

    def _find_critical_paths(self, paths: list[list[str]]) -> list[list[str]]:
        """Identify critical paths (shortest paths to important nodes)."""
        # Simple heuristic: shortest paths are often most critical
        if not paths:
            return []

        sorted_paths = sorted(paths, key=len)
        return sorted_paths[:5]  # Return top 5 shortest paths

    def _analyze_topology(
        self,
        nodes: list[GraphNode],
        relationships: list[GraphRelationship]
    ) -> dict[str, Any]:
        """Analyze topology characteristics."""
        # Build adjacency lists
        outgoing = {}
        incoming = {}

        for rel in relationships:
            if rel.start_node_id not in outgoing:
                outgoing[rel.start_node_id] = []
            outgoing[rel.start_node_id].append(rel.end_node_id)

            if rel.end_node_id not in incoming:
                incoming[rel.end_node_id] = []
            incoming[rel.end_node_id].append(rel.start_node_id)

        # Find hubs (nodes with many connections)
        hubs = []
        for node in nodes:
            out_degree = len(outgoing.get(node.id, []))
            in_degree = len(incoming.get(node.id, []))
            total_degree = out_degree + in_degree

            if total_degree > 5:  # Threshold for hub
                hubs.append({
                    'node_id': node.id,
                    'out_degree': out_degree,
                    'in_degree': in_degree,
                    'total_degree': total_degree
                })

        # Sort hubs by degree
        hubs.sort(key=lambda x: x['total_degree'], reverse=True)

        # Detect cycles using DFS
        cycles = self._detect_cycles_dfs(nodes, outgoing)

        # Find isolated nodes
        isolated = []
        for node in nodes:
            if node.id not in outgoing and node.id not in incoming:
                isolated.append(node.id)

        return {
            'hubs': hubs[:10],  # Top 10 hubs
            'cycles': cycles,
            'isolated_nodes': isolated,
            'total_nodes': len(nodes),
            'total_relationships': len(relationships),
            'avg_degree': len(relationships) * 2 / len(nodes) if nodes else 0
        }

    def _detect_cycles_dfs(
        self,
        nodes: list[GraphNode],
        adjacency: dict[str, list[str]]
    ) -> list[list[str]]:
        """Detect cycles using depth-first search."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node_id: str, path: list[str]) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for neighbor in adjacency.get(node_id, []):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)

            rec_stack.remove(node_id)

        for node in nodes:
            if node.id not in visited:
                dfs(node.id, [])

        return cycles[:10]  # Return up to 10 cycles


# Export main classes
__all__ = [
    'GraphTraversal',
    'TraversalType',
    'TraversalConfig',
    'TraversalResult',
    'GraphNode',
    'GraphRelationship'
]
