"""Unit tests for complex graph traversal queries."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.graph.graph_traversal import (
    GraphTraversal,
    TraversalType,
    TraversalConfig,
    TraversalResult,
    GraphNode,
    GraphRelationship
)


class TestTraversalConfig:
    """Test suite for TraversalConfig."""
    
    def test_default_config(self):
        """Test default traversal configuration."""
        config = TraversalConfig()
        
        assert config.max_depth == 5
        assert config.detect_cycles is True
        assert config.include_indirect is True
        assert config.relationship_types == []
        assert config.node_filters == {}
        
    def test_custom_config(self):
        """Test custom traversal configuration."""
        config = TraversalConfig(
            max_depth=3,
            detect_cycles=False,
            relationship_types=['DEPENDS_ON', 'USES'],
            node_filters={'status': 'active'}
        )
        
        assert config.max_depth == 3
        assert config.detect_cycles is False
        assert 'DEPENDS_ON' in config.relationship_types
        assert config.node_filters['status'] == 'active'


class TestGraphTraversal:
    """Test suite for GraphTraversal."""
    
    @pytest.fixture
    async def mock_driver(self):
        """Create mock Neo4j driver."""
        driver = AsyncMock()
        session = AsyncMock()
        driver.session.return_value.__aenter__.return_value = session
        driver.session.return_value.__aexit__.return_value = None
        return driver, session
    
    @pytest.fixture
    async def traversal(self, mock_driver):
        """Create graph traversal instance."""
        driver, session = mock_driver
        
        traversal = GraphTraversal(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password"
        )
        traversal.driver = driver
        
        return traversal, session
    
    @pytest.mark.asyncio
    async def test_connect(self):
        """Test Neo4j connection."""
        with patch('neo4j.AsyncGraphDatabase.driver') as mock_driver_class:
            mock_driver = AsyncMock()
            mock_session = AsyncMock()
            mock_driver.session.return_value.__aenter__.return_value = mock_session
            mock_driver.session.return_value.__aexit__.return_value = None
            mock_driver_class.return_value = mock_driver
            
            traversal = GraphTraversal(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="password"
            )
            
            await traversal.connect()
            
            assert traversal.driver is not None
            mock_driver_class.assert_called_once()
            mock_session.run.assert_called_with("RETURN 1")
    
    @pytest.mark.asyncio
    async def test_impact_analysis(self, traversal):
        """Test impact analysis traversal."""
        graph_traversal, session = traversal
        
        # Mock Neo4j response
        mock_record = {
            'nodes': [
                {'id': 'node1', 'labels': ['Configuration'], 'name': 'Server1'},
                {'id': 'node2', 'labels': ['Configuration'], 'name': 'Server2'},
                {'id': 'node3', 'labels': ['Application'], 'name': 'App1'}
            ],
            'relationships': [
                Mock(id=1, type='DEPENDS_ON', start_node=Mock(id='node1'), end_node=Mock(id='node2')),
                Mock(id=2, type='USES', start_node=Mock(id='node2'), end_node=Mock(id='node3'))
            ],
            'paths': [
                Mock(nodes=[{'id': 'node1'}, {'id': 'node2'}]),
                Mock(nodes=[{'id': 'node1'}, {'id': 'node2'}, {'id': 'node3'}])
            ],
            'max_depth': 2
        }
        
        mock_result = AsyncMock()
        mock_result.single.return_value = mock_record
        session.run.return_value = mock_result
        
        # Perform impact analysis
        result = await graph_traversal.impact_analysis('node1')
        
        assert isinstance(result, TraversalResult)
        assert result.traversal_type == TraversalType.IMPACT_ANALYSIS
        assert len(result.nodes) == 3
        assert len(result.relationships) == 2
        assert len(result.paths) == 2
        assert result.max_depth_reached == 2
        assert result.metadata['node_id'] == 'node1'
        assert result.metadata['affected_count'] == 3
    
    @pytest.mark.asyncio
    async def test_impact_analysis_with_cycles(self, traversal):
        """Test impact analysis with cycle detection."""
        graph_traversal, session = traversal
        
        # Create circular dependency
        mock_record = {
            'nodes': [
                {'id': 'node1', 'labels': ['Configuration']},
                {'id': 'node2', 'labels': ['Configuration']},
                {'id': 'node3', 'labels': ['Configuration']}
            ],
            'relationships': [],
            'paths': [
                Mock(nodes=[{'id': 'node1'}, {'id': 'node2'}, {'id': 'node3'}, {'id': 'node1'}])
            ],
            'max_depth': 3
        }
        
        mock_result = AsyncMock()
        mock_result.single.return_value = mock_record
        session.run.return_value = mock_result
        
        config = TraversalConfig(detect_cycles=True)
        result = await graph_traversal.impact_analysis('node1', config)
        
        # Should detect the cycle
        assert len(result.cycles_detected) > 0
        assert 'node1' in result.cycles_detected[0]
    
    @pytest.mark.asyncio
    async def test_dependency_tree(self, traversal):
        """Test dependency tree traversal."""
        graph_traversal, session = traversal
        
        mock_record = {
            'nodes': [
                {'id': 'app1', 'labels': ['Application']},
                {'id': 'db1', 'labels': ['Database']},
                {'id': 'cache1', 'labels': ['Cache']},
                {'id': 'network1', 'labels': ['Network']}
            ],
            'relationships': [
                Mock(id=1, type='DEPENDS_ON', start_node=Mock(id='app1'), end_node=Mock(id='db1')),
                Mock(id=2, type='DEPENDS_ON', start_node=Mock(id='app1'), end_node=Mock(id='cache1')),
                Mock(id=3, type='DEPENDS_ON', start_node=Mock(id='db1'), end_node=Mock(id='network1'))
            ],
            'paths': [],
            'max_depth': 2
        }
        
        mock_result = AsyncMock()
        mock_result.single.return_value = mock_record
        session.run.return_value = mock_result
        
        result = await graph_traversal.dependency_tree('app1')
        
        assert result.traversal_type == TraversalType.DEPENDENCY_TREE
        assert len(result.nodes) == 4
        assert result.metadata['node_id'] == 'app1'
        assert result.metadata['dependency_count'] == 3  # All nodes except root
        assert 'tree_structure' in result.metadata
    
    @pytest.mark.asyncio
    async def test_service_topology(self, traversal):
        """Test service topology mapping."""
        graph_traversal, session = traversal
        
        mock_record = {
            'nodes': [
                {'id': 'web1', 'labels': ['Configuration'], 'type': 'webserver'},
                {'id': 'app1', 'labels': ['Configuration'], 'type': 'appserver'},
                {'id': 'db1', 'labels': ['Configuration'], 'type': 'database'},
                {'id': 'lb1', 'labels': ['Configuration'], 'type': 'loadbalancer'}
            ],
            'relationships': [
                Mock(id=1, type='CONNECTS_TO', start_node=Mock(id='lb1'), end_node=Mock(id='web1')),
                Mock(id=2, type='CONNECTS_TO', start_node=Mock(id='web1'), end_node=Mock(id='app1')),
                Mock(id=3, type='CONNECTS_TO', start_node=Mock(id='app1'), end_node=Mock(id='db1'))
            ],
            'paths': [],
            'node_count': 4
        }
        
        mock_result = AsyncMock()
        mock_result.single.return_value = mock_record
        session.run.return_value = mock_result
        
        result = await graph_traversal.service_topology('org123')
        
        assert result.traversal_type == TraversalType.SERVICE_TOPOLOGY
        assert len(result.nodes) == 4
        assert result.metadata['organization_id'] == 'org123'
        assert result.metadata['node_count'] == 4
        assert 'topology_analysis' in result.metadata
        
        topology = result.metadata['topology_analysis']
        assert 'hubs' in topology
        assert 'cycles' in topology
        assert 'isolated_nodes' in topology
        assert topology['total_nodes'] == 4
    
    @pytest.mark.asyncio
    async def test_find_root_cause(self, traversal):
        """Test root cause analysis."""
        graph_traversal, session = traversal
        
        # Mock multiple async results
        mock_records = [
            {
                'root': {'id': 'network_issue', 'labels': ['Problem']},
                'affected_symptoms': [
                    {'id': 'app_slow', 'labels': ['Symptom']},
                    {'id': 'timeout_errors', 'labels': ['Symptom']}
                ],
                'paths': [],
                'coverage': 1.0,
                'avg_distance': 2.0,
                'root_cause_score': 0.5
            },
            {
                'root': {'id': 'db_lock', 'labels': ['Problem']},
                'affected_symptoms': [
                    {'id': 'app_slow', 'labels': ['Symptom']}
                ],
                'paths': [],
                'coverage': 0.5,
                'avg_distance': 1.0,
                'root_cause_score': 0.5
            }
        ]
        
        # Create async iterator
        async def async_iter():
            for record in mock_records:
                yield record
        
        mock_result = AsyncMock()
        mock_result.__aiter__ = async_iter
        session.run.return_value = mock_result
        
        symptom_nodes = ['app_slow', 'timeout_errors']
        result = await graph_traversal.find_root_cause(symptom_nodes)
        
        assert result.traversal_type == TraversalType.ROOT_CAUSE
        assert result.metadata['symptom_nodes'] == symptom_nodes
        assert 'root_causes' in result.metadata
        assert len(result.metadata['root_causes']) <= 5
        
        # Check root cause scoring
        if result.metadata['root_causes']:
            first_cause = result.metadata['root_causes'][0]
            assert 'node' in first_cause
            assert 'score' in first_cause
            assert 'coverage' in first_cause
    
    @pytest.mark.asyncio
    async def test_blast_radius(self, traversal):
        """Test blast radius calculation."""
        graph_traversal, session = traversal
        
        mock_record = {
            'affected_nodes': [
                {'id': 'app1', 'labels': ['Application']},
                {'id': 'app2', 'labels': ['Application']},
                {'id': 'db1', 'labels': ['Database']}
            ],
            'impact_analysis': [
                {'node': {'id': 'app1'}, 'impact': 0.9, 'distance': 1},
                {'node': {'id': 'app2'}, 'impact': 0.7, 'distance': 2},
                {'node': {'id': 'db1'}, 'impact': 0.4, 'distance': 1}
            ],
            'paths': []
        }
        
        mock_result = AsyncMock()
        mock_result.single.return_value = mock_record
        session.run.return_value = mock_result
        
        result = await graph_traversal.blast_radius('server1', 'restart')
        
        assert result.traversal_type == TraversalType.BLAST_RADIUS
        assert result.metadata['change_node_id'] == 'server1'
        assert result.metadata['change_type'] == 'restart'
        assert result.metadata['total_affected'] == 3
        
        # Check impact categorization
        categories = result.metadata['impact_categories']
        assert 'critical' in categories
        assert 'high' in categories
        assert 'medium' in categories
        assert 'low' in categories
    
    @pytest.mark.asyncio
    async def test_cycle_detection(self, traversal):
        """Test cycle detection in paths."""
        graph_traversal, _ = traversal
        
        paths = [
            ['node1', 'node2', 'node3'],
            ['node1', 'node2', 'node3', 'node1'],  # Cycle
            ['node4', 'node5', 'node4']  # Another cycle
        ]
        
        cycles = await graph_traversal._detect_cycles('node1', paths)
        
        assert len(cycles) == 2
        assert ['node3', 'node1'] in cycles or ['node1'] in cycles
        assert ['node4'] in cycles
    
    def test_process_nodes(self, traversal):
        """Test node processing."""
        graph_traversal, _ = traversal
        
        neo4j_nodes = [
            {'id': '1', 'name': 'Server1', 'type': 'server'},
            {'id': '2', 'name': 'App1', 'type': 'application'}
        ]
        
        processed = graph_traversal._process_nodes(neo4j_nodes)
        
        assert len(processed) == 2
        assert all(isinstance(n, GraphNode) for n in processed)
        assert processed[0].id == '1'
        assert processed[0].properties['name'] == 'Server1'
    
    def test_build_tree_structure(self, traversal):
        """Test tree structure building."""
        graph_traversal, _ = traversal
        
        nodes = [
            GraphNode(id='root', labels=['Root'], properties={}),
            GraphNode(id='child1', labels=['Child'], properties={}),
            GraphNode(id='child2', labels=['Child'], properties={}),
            GraphNode(id='grandchild', labels=['GrandChild'], properties={})
        ]
        
        relationships = [
            GraphRelationship(
                id='1', type='PARENT_OF',
                start_node_id='child1', end_node_id='root',
                properties={}
            ),
            GraphRelationship(
                id='2', type='PARENT_OF',
                start_node_id='child2', end_node_id='root',
                properties={}
            ),
            GraphRelationship(
                id='3', type='PARENT_OF',
                start_node_id='grandchild', end_node_id='child1',
                properties={}
            )
        ]
        
        tree = graph_traversal._build_tree_structure('root', nodes, relationships)
        
        assert tree['id'] == 'root'
        assert len(tree['children']) == 2
        assert any(child['id'] == 'child1' for child in tree['children'])
        assert any(child['id'] == 'child2' for child in tree['children'])
        
        # Check grandchild
        child1 = next(c for c in tree['children'] if c['id'] == 'child1')
        assert len(child1['children']) == 1
        assert child1['children'][0]['id'] == 'grandchild'
    
    def test_analyze_topology(self, traversal):
        """Test topology analysis."""
        graph_traversal, _ = traversal
        
        nodes = [
            GraphNode(id=f'node{i}', labels=['Node'], properties={})
            for i in range(10)
        ]
        
        # Create hub node (node0 connects to many)
        relationships = []
        for i in range(1, 7):
            relationships.append(
                GraphRelationship(
                    id=str(i), type='CONNECTS',
                    start_node_id='node0', end_node_id=f'node{i}',
                    properties={}
                )
            )
        
        # Create cycle
        relationships.extend([
            GraphRelationship(
                id='c1', type='CONNECTS',
                start_node_id='node7', end_node_id='node8',
                properties={}
            ),
            GraphRelationship(
                id='c2', type='CONNECTS',
                start_node_id='node8', end_node_id='node7',
                properties={}
            )
        ])
        
        analysis = graph_traversal._analyze_topology(nodes, relationships)
        
        assert 'hubs' in analysis
        assert len(analysis['hubs']) > 0
        assert analysis['hubs'][0]['node_id'] == 'node0'
        assert analysis['hubs'][0]['total_degree'] > 5
        
        assert 'isolated_nodes' in analysis
        assert 'node9' in analysis['isolated_nodes']
        
        assert analysis['total_nodes'] == 10
        assert analysis['total_relationships'] == 8


class TestIntegrationScenarios:
    """Integration tests for complex traversal scenarios."""
    
    @pytest.mark.asyncio
    async def test_cascading_failure_analysis(self):
        """Test analyzing cascading failures."""
        traversal = GraphTraversal(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password"
        )
        
        # Mock driver
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = None
        traversal.driver = mock_driver
        
        # Simulate cascading failure scenario
        mock_record = {
            'nodes': [
                {'id': 'database', 'labels': ['Database'], 'critical': True},
                {'id': 'app_server_1', 'labels': ['Application']},
                {'id': 'app_server_2', 'labels': ['Application']},
                {'id': 'web_server_1', 'labels': ['WebServer']},
                {'id': 'web_server_2', 'labels': ['WebServer']},
                {'id': 'load_balancer', 'labels': ['LoadBalancer']}
            ],
            'relationships': [],
            'paths': [
                Mock(nodes=[{'id': 'database'}, {'id': 'app_server_1'}, {'id': 'web_server_1'}]),
                Mock(nodes=[{'id': 'database'}, {'id': 'app_server_2'}, {'id': 'web_server_2'}])
            ],
            'max_depth': 3
        }
        
        mock_result = AsyncMock()
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        
        # Analyze impact of database failure
        result = await traversal.impact_analysis('database')
        
        assert len(result.nodes) == 6
        assert result.metadata['affected_count'] == 6
        
        # All application and web servers should be affected
        affected_ids = [n.id for n in result.nodes]
        assert 'app_server_1' in affected_ids
        assert 'app_server_2' in affected_ids
        assert 'web_server_1' in affected_ids
        assert 'web_server_2' in affected_ids