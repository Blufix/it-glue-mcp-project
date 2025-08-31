"""Neo4j query builder with fuzzy matching integration."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from src.query.fuzzy_matcher import FuzzyMatcher, MatchResult

logger = logging.getLogger(__name__)


class RelationshipType(Enum):
    """IT Glue relationship types in Neo4j."""
    # Organizational
    BELONGS_TO = "BELONGS_TO"
    OWNS = "OWNS"
    MANAGES = "MANAGES"

    # Technical
    DEPENDS_ON = "DEPENDS_ON"
    CONNECTS_TO = "CONNECTS_TO"
    HOSTED_ON = "HOSTED_ON"
    RUNS_ON = "RUNS_ON"
    USES = "USES"

    # Service
    PROVIDES = "PROVIDES"
    REQUIRES = "REQUIRES"
    BACKS_UP = "BACKS_UP"
    MONITORS = "MONITORS"

    # Documentation
    DOCUMENTS = "DOCUMENTS"
    REFERENCES = "REFERENCES"

    # Support
    AFFECTS = "AFFECTS"
    RESOLVES = "RESOLVES"
    RELATED_TO = "RELATED_TO"

    # Security
    AUTHENTICATES = "AUTHENTICATES"
    AUTHORIZES = "AUTHORIZES"
    SECURES = "SECURES"


@dataclass
class Neo4jQuery:
    """Structured Neo4j query with metadata."""
    cypher: str
    parameters: dict[str, Any]
    description: str
    expected_return_type: str
    fuzzy_matched_entities: list[MatchResult]
    confidence: float


class Neo4jQueryBuilder:
    """Build Neo4j queries with fuzzy matching support."""

    def __init__(self, fuzzy_matcher: Optional[FuzzyMatcher] = None):
        """Initialize query builder."""
        self.fuzzy_matcher = fuzzy_matcher or FuzzyMatcher()
        self.query_templates = self._build_query_templates()

    def _build_query_templates(self) -> dict[str, str]:
        """Build reusable Cypher query templates."""
        return {
            # Basic entity queries
            'find_organization': """
                MATCH (o:Organization)
                WHERE o.name =~ $org_pattern OR o.id = $org_id
                RETURN o
                LIMIT 10
            """,

            'find_configurations': """
                MATCH (c:Configuration)-[:BELONGS_TO]->(o:Organization)
                WHERE o.name =~ $org_pattern
                AND ($config_type IS NULL OR c.type = $config_type)
                AND ($os IS NULL OR c.os =~ $os)
                RETURN c, o
                ORDER BY c.updated_at DESC
                LIMIT 50
            """,

            # Relationship queries
            'find_dependencies': """
                MATCH path = (start:Configuration {name: $config_name})-[:DEPENDS_ON*1..3]-(dep)
                RETURN
                    start.name as source,
                    [node in nodes(path) | {name: node.name, type: labels(node)[0]}] as dependency_path,
                    length(path) as depth
                ORDER BY depth
            """,

            'impact_analysis': """
                MATCH path = (start:Configuration)-[:DEPENDS_ON*1..5]-(affected)
                WHERE start.name =~ $config_pattern
                WITH affected, min(length(path)) as min_distance
                RETURN
                    affected.name as affected_system,
                    affected.type as system_type,
                    affected.criticality as criticality,
                    min_distance as impact_distance
                ORDER BY impact_distance, criticality DESC
            """,

            'find_related_passwords': """
                MATCH (c:Configuration)-[:BELONGS_TO]->(o:Organization)
                WHERE c.name =~ $config_pattern AND o.name =~ $org_pattern
                MATCH (p:Password)-[:BELONGS_TO]->(o)
                WHERE p.url CONTAINS c.hostname OR p.name CONTAINS c.name
                RETURN p.name, p.username, p.category, p.url, p.updated_at
                ORDER BY p.updated_at DESC
            """,

            'service_map': """
                MATCH (c:Configuration {type: 'Application'})-[r:CONNECTS_TO|DEPENDS_ON|USES*1..3]-(related)
                WHERE c.name =~ $app_pattern
                RETURN c, r, related
            """,

            'recent_changes': """
                MATCH (c:Configuration)-[ch:CHANGED]->(e:ChangeEvent)
                WHERE c.name =~ $config_pattern
                AND e.timestamp > datetime() - duration('P7D')
                RETURN
                    c.name as configuration,
                    e.description as change_description,
                    e.changed_by as changed_by,
                    e.timestamp as when
                ORDER BY e.timestamp DESC
                LIMIT 20
            """,

            'find_similar_configs': """
                MATCH (source:Configuration {name: $config_name})
                MATCH (similar:Configuration)
                WHERE similar.id <> source.id
                AND similar.type = source.type
                AND similar.os = source.os
                WITH source, similar,
                     [
                         CASE WHEN similar.type = source.type THEN 1 ELSE 0 END,
                         CASE WHEN similar.os = source.os THEN 1 ELSE 0 END,
                         CASE WHEN similar.version = source.version THEN 1 ELSE 0 END
                     ] as similarities
                WITH source, similar, reduce(s = 0, x IN similarities | s + x) as similarity_score
                WHERE similarity_score >= 2
                RETURN similar, similarity_score
                ORDER BY similarity_score DESC
                LIMIT 10
            """,

            'network_topology': """
                MATCH path = (device:Configuration {type: 'Network Device'})-[:CONNECTS_TO*1..3]-(connected)
                WHERE device.location = $location OR $location IS NULL
                RETURN
                    device.name as device,
                    device.ip_address as ip,
                    [n in nodes(path) WHERE n <> device | {name: n.name, ip: n.ip_address}] as connected_devices
            """,

            'credential_audit': """
                MATCH (p:Password)-[:BELONGS_TO]->(o:Organization)
                WHERE o.name =~ $org_pattern
                AND datetime(p.password_updated_at) < datetime() - duration('P90D')
                RETURN
                    p.name as password_name,
                    p.username as username,
                    p.category as category,
                    p.password_updated_at as last_updated,
                    duration.between(datetime(p.password_updated_at), datetime()).days as days_old
                ORDER BY days_old DESC
            """,

            'cross_reference_documentation': """
                MATCH (c:Configuration)-[:BELONGS_TO]->(o:Organization)
                WHERE c.name =~ $config_pattern AND o.name =~ $org_pattern
                MATCH (d:Document)-[:REFERENCES]->(c)
                RETURN
                    c.name as configuration,
                    collect(DISTINCT {
                        title: d.name,
                        folder: d.folder,
                        updated: d.updated_at
                    }) as documentation
            """
        }

    def build_query(
        self,
        intent: str,
        entities: dict[str, Any],
        organizations: list[dict[str, str]]
    ) -> Neo4jQuery:
        """
        Build Neo4j query based on intent and entities.

        Args:
            intent: Query intent (e.g., 'find_dependencies', 'impact_analysis')
            entities: Extracted entities from query
            organizations: Known organizations for fuzzy matching

        Returns:
            Neo4j query object
        """
        # Fuzzy match organization if present
        fuzzy_matches = []
        parameters = {}

        if 'organization' in entities:
            org_input = entities['organization']
            matches = self.fuzzy_matcher.match_organization(
                org_input,
                organizations
            )

            if matches:
                best_match = matches[0]
                fuzzy_matches.append(best_match)
                # Use regex pattern for flexible matching in Neo4j
                parameters['org_pattern'] = f"(?i).*{best_match.matched}.*"
                parameters['org_id'] = best_match.entity_id
            else:
                parameters['org_pattern'] = f"(?i).*{org_input}.*"
                parameters['org_id'] = None

        # Build query based on intent
        query_builder_map = {
            'find_dependencies': self._build_dependency_query,
            'impact_analysis': self._build_impact_query,
            'service_map': self._build_service_map_query,
            'recent_changes': self._build_recent_changes_query,
            'credential_audit': self._build_credential_audit_query,
            'network_topology': self._build_network_topology_query
        }

        builder_func = query_builder_map.get(intent, self._build_default_query)
        cypher, params, description = builder_func(entities, parameters)

        return Neo4jQuery(
            cypher=cypher,
            parameters=params,
            description=description,
            expected_return_type=self._get_return_type(intent),
            fuzzy_matched_entities=fuzzy_matches,
            confidence=fuzzy_matches[0].confidence if fuzzy_matches else 0.5
        )

    def _build_dependency_query(
        self,
        entities: dict[str, Any],
        parameters: dict[str, Any]
    ) -> tuple[str, dict[str, Any], str]:
        """Build dependency analysis query."""
        config_name = entities.get('configuration', entities.get('system', ''))

        # Apply fuzzy matching to configuration name
        if config_name:
            # Simple fuzzy pattern for Neo4j regex
            parameters['config_name'] = config_name
            parameters['config_pattern'] = f"(?i).*{config_name}.*"

        cypher = self.query_templates['find_dependencies']
        description = f"Finding dependencies for {config_name}"

        return cypher, parameters, description

    def _build_impact_query(
        self,
        entities: dict[str, Any],
        parameters: dict[str, Any]
    ) -> tuple[str, dict[str, Any], str]:
        """Build impact analysis query."""
        config_name = entities.get('configuration', entities.get('system', ''))
        parameters['config_pattern'] = f"(?i).*{config_name}.*"

        cypher = self.query_templates['impact_analysis']
        description = f"Analyzing impact if {config_name} fails"

        return cypher, parameters, description

    def _build_service_map_query(
        self,
        entities: dict[str, Any],
        parameters: dict[str, Any]
    ) -> tuple[str, dict[str, Any], str]:
        """Build service map query."""
        app_name = entities.get('application', entities.get('service', ''))
        parameters['app_pattern'] = f"(?i).*{app_name}.*"

        cypher = self.query_templates['service_map']
        description = f"Mapping service connections for {app_name}"

        return cypher, parameters, description

    def _build_recent_changes_query(
        self,
        entities: dict[str, Any],
        parameters: dict[str, Any]
    ) -> tuple[str, dict[str, Any], str]:
        """Build recent changes query."""
        config_name = entities.get('configuration', entities.get('system', '.*'))
        parameters['config_pattern'] = f"(?i).*{config_name}.*"

        cypher = self.query_templates['recent_changes']
        description = f"Finding recent changes for {config_name}"

        return cypher, parameters, description

    def _build_credential_audit_query(
        self,
        entities: dict[str, Any],
        parameters: dict[str, Any]
    ) -> tuple[str, dict[str, Any], str]:
        """Build credential audit query."""
        if 'org_pattern' not in parameters:
            parameters['org_pattern'] = '.*'  # Match all if no org specified

        cypher = self.query_templates['credential_audit']
        description = "Auditing old passwords"

        return cypher, parameters, description

    def _build_network_topology_query(
        self,
        entities: dict[str, Any],
        parameters: dict[str, Any]
    ) -> tuple[str, dict[str, Any], str]:
        """Build network topology query."""
        location = entities.get('location')
        parameters['location'] = location

        cypher = self.query_templates['network_topology']
        description = f"Mapping network topology{' for ' + location if location else ''}"

        return cypher, parameters, description

    def _build_default_query(
        self,
        entities: dict[str, Any],
        parameters: dict[str, Any]
    ) -> tuple[str, dict[str, Any], str]:
        """Build default configuration search query."""
        parameters['config_type'] = entities.get('type')
        parameters['os'] = entities.get('os')

        if 'org_pattern' not in parameters:
            parameters['org_pattern'] = '.*'

        cypher = self.query_templates['find_configurations']
        description = "Finding configurations"

        return cypher, parameters, description

    def _get_return_type(self, intent: str) -> str:
        """Get expected return type for intent."""
        return_types = {
            'find_dependencies': 'dependency_tree',
            'impact_analysis': 'impact_list',
            'service_map': 'graph',
            'recent_changes': 'change_list',
            'credential_audit': 'audit_report',
            'network_topology': 'topology_map'
        }
        return return_types.get(intent, 'entity_list')

    def build_relationship_query(
        self,
        source_type: str,
        source_id: str,
        relationship: RelationshipType,
        target_type: Optional[str] = None,
        max_depth: int = 3
    ) -> Neo4jQuery:
        """
        Build query to find relationships.

        Args:
            source_type: Source node type
            source_id: Source node ID
            relationship: Relationship type to traverse
            target_type: Optional target node type filter
            max_depth: Maximum traversal depth

        Returns:
            Neo4j query object
        """
        target_filter = f":{target_type}" if target_type else ""

        cypher = f"""
            MATCH path = (source:{source_type} {{id: $source_id}})-[:{relationship.value}*1..{max_depth}]->(target{target_filter})
            RETURN
                source,
                [r in relationships(path) | type(r)] as relationship_types,
                target,
                length(path) as distance
            ORDER BY distance
            LIMIT 25
        """

        parameters = {
            'source_id': source_id,
            'max_depth': max_depth
        }

        description = f"Finding {relationship.value} relationships from {source_type}:{source_id}"

        return Neo4jQuery(
            cypher=cypher,
            parameters=parameters,
            description=description,
            expected_return_type='relationship_graph',
            fuzzy_matched_entities=[],
            confidence=1.0  # Direct ID query, high confidence
        )
