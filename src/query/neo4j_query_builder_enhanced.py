"""Enhanced Neo4j query builder with advanced fuzzy matching support."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import re

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
class FuzzyQueryPattern:
    """Pattern for fuzzy matching in Cypher."""
    field: str
    pattern: str
    confidence_threshold: float = 0.7
    use_index: bool = False


@dataclass
class Neo4jQuery:
    """Structured Neo4j query with metadata."""
    cypher: str
    parameters: Dict[str, Any]
    description: str
    expected_return_type: str
    fuzzy_matched_entities: List[MatchResult]
    confidence: float
    index_hints: List[str] = field(default_factory=list)
    traversal_depth: int = 5
    ranking_expression: Optional[str] = None


class EnhancedNeo4jQueryBuilder:
    """Build Neo4j queries with advanced fuzzy matching support."""
    
    def __init__(
        self,
        fuzzy_matcher: Optional[FuzzyMatcher] = None,
        enable_fuzzy: bool = True,
        fuzzy_threshold: float = 0.7,
        max_traversal_depth: int = 5
    ):
        """
        Initialize enhanced query builder.
        
        Args:
            fuzzy_matcher: Fuzzy matcher instance
            enable_fuzzy: Enable fuzzy matching in queries
            fuzzy_threshold: Minimum confidence for fuzzy matches
            max_traversal_depth: Maximum graph traversal depth
        """
        self.fuzzy_matcher = fuzzy_matcher or FuzzyMatcher()
        self.enable_fuzzy = enable_fuzzy
        self.fuzzy_threshold = fuzzy_threshold
        self.max_traversal_depth = max_traversal_depth
        self.query_templates = self._build_query_templates()
    
    def _build_query_templates(self) -> Dict[str, str]:
        """Build reusable Cypher query templates with fuzzy support."""
        return {
            # Basic entity queries with fuzzy support
            'find_organization_fuzzy': """
                // Use index hint for performance
                USING INDEX o:Organization(name)
                MATCH (o:Organization)
                WHERE o.name =~ $org_pattern
                   OR toLower(o.name) CONTAINS toLower($org_substring)
                   OR o.alternative_names =~ $org_pattern
                WITH o, 
                     CASE 
                        WHEN o.name = $org_exact THEN 1.0
                        WHEN toLower(o.name) = toLower($org_exact) THEN 0.95
                        WHEN o.name =~ $org_pattern THEN $fuzzy_confidence
                        ELSE 0.7
                     END as match_confidence
                WHERE match_confidence >= $min_confidence
                RETURN o, match_confidence
                ORDER BY match_confidence DESC
                LIMIT 10
            """,
            
            'find_configurations_fuzzy': """
                // Use composite index for performance
                USING INDEX c:Configuration(name, type)
                MATCH (c:Configuration)-[:BELONGS_TO]->(o:Organization)
                WHERE (o.name =~ $org_pattern OR o.id = $org_id)
                  AND ($config_pattern IS NULL OR c.name =~ $config_pattern)
                  AND ($config_type IS NULL OR c.type = $config_type)
                  AND ($os IS NULL OR c.os =~ $os)
                WITH c, o,
                     CASE
                        WHEN c.name = $config_exact THEN 1.0
                        WHEN c.name =~ $config_pattern THEN $fuzzy_confidence
                        ELSE 0.7
                     END as match_confidence
                WHERE match_confidence >= $min_confidence
                RETURN c, o, match_confidence
                ORDER BY match_confidence DESC, c.updated_at DESC
                LIMIT 50
            """,
            
            # Dependency queries with cycle detection
            'find_dependencies_safe': """
                MATCH path = (start:Configuration {name: $config_name})-[:DEPENDS_ON*1..$max_depth]-(dep)
                WHERE NOT (dep)-[:DEPENDS_ON]->(start)  // Prevent cycles
                  AND all(r in relationships(path) WHERE r.active = true)
                WITH path, dep,
                     reduce(conf = 1.0, r in relationships(path) | 
                            conf * coalesce(r.confidence, 0.9)) as path_confidence
                WHERE path_confidence >= $min_confidence
                RETURN
                    start.name as source,
                    [node in nodes(path) | {
                        name: node.name,
                        type: labels(node)[0],
                        critical: node.critical
                    }] as dependency_path,
                    length(path) as depth,
                    path_confidence
                ORDER BY path_confidence DESC, depth
                LIMIT 100
            """,
            
            # Impact analysis with ranking
            'impact_analysis_ranked': """
                MATCH path = (start:Configuration)-[:DEPENDS_ON|HOSTED_ON|RUNS_ON*1..$max_depth]-(affected)
                WHERE start.name =~ $config_pattern
                  AND NOT (affected)-[:DEPENDS_ON*1..2]->(start)  // Avoid circular dependencies
                WITH path, affected,
                     length(path) as impact_distance,
                     reduce(criticality = 0, n in nodes(path) | 
                            criticality + coalesce(n.criticality_score, 1)) as total_criticality
                WITH affected, 
                     min(impact_distance) as min_distance,
                     max(total_criticality) as max_criticality,
                     collect(path) as paths
                RETURN
                    affected.name as affected_component,
                    affected.type as component_type,
                    affected.critical as is_critical,
                    min_distance as proximity,
                    max_criticality as criticality_score,
                    size(paths) as path_count
                ORDER BY criticality_score DESC, proximity
                LIMIT 50
            """,
            
            # Password queries with age ranking
            'find_passwords_ranked': """
                MATCH (p:Password)-[:AUTHENTICATES]->(target)
                WHERE target.name =~ $target_pattern
                   OR target.id = $target_id
                WITH p, target,
                     duration.between(p.last_changed, datetime()).days as password_age,
                     CASE
                        WHEN p.type = 'admin' THEN 2.0
                        WHEN p.type = 'service' THEN 1.5
                        ELSE 1.0
                     END as importance_factor
                WHERE ($max_age IS NULL OR password_age <= $max_age)
                RETURN p, target, password_age,
                       password_age * importance_factor as risk_score
                ORDER BY risk_score DESC
                LIMIT 20
            """,
            
            # Service topology with fuzzy matching
            'service_topology_fuzzy': """
                MATCH (s:Service)
                WHERE s.name =~ $service_pattern
                   OR ANY(alias IN s.aliases WHERE alias =~ $service_pattern)
                OPTIONAL MATCH (s)-[r:DEPENDS_ON|CONNECTS_TO|USES]-(related)
                WITH s, type(r) as rel_type, collect(related) as related_nodes
                RETURN s as service,
                       collect({
                           type: rel_type,
                           nodes: [n in related_nodes | {
                               name: n.name,
                               type: labels(n)[0],
                               status: n.status
                           }]
                       }) as connections
                ORDER BY s.criticality_score DESC
                LIMIT 25
            """,
            
            # Recent changes with fuzzy entity matching
            'recent_changes_fuzzy': """
                MATCH (change:Change)-[:AFFECTS]->(target)
                WHERE target.name =~ $target_pattern
                  AND change.timestamp >= datetime() - duration({days: $days_back})
                WITH change, target
                ORDER BY change.timestamp DESC
                RETURN change, target,
                       duration.between(change.timestamp, datetime()).hours as hours_ago
                LIMIT 50
            """,
            
            # Cross-organization search with fuzzy
            'cross_org_search': """
                MATCH (entity)
                WHERE ANY(label in labels(entity) WHERE label IN $entity_types)
                  AND (entity.name =~ $search_pattern
                       OR ANY(prop in keys(entity) WHERE 
                              toString(entity[prop]) =~ $search_pattern))
                OPTIONAL MATCH (entity)-[:BELONGS_TO]->(org:Organization)
                WITH entity, org,
                     CASE
                        WHEN entity.name = $search_exact THEN 1.0
                        WHEN entity.name =~ $search_pattern THEN 0.8
                        ELSE 0.6
                     END as relevance
                WHERE relevance >= $min_relevance
                RETURN entity, org, relevance,
                       labels(entity) as entity_types
                ORDER BY relevance DESC, entity.updated_at DESC
                LIMIT 100
            """
        }
    
    def build_fuzzy_pattern(self, input_str: str, exact: bool = False) -> str:
        """
        Build a case-insensitive regex pattern for fuzzy matching.
        
        Args:
            input_str: Input string
            exact: Whether to match exactly
            
        Returns:
            Regex pattern for Neo4j
        """
        if exact:
            return f"(?i)^{re.escape(input_str)}$"
        
        # Allow fuzzy matching with common variations
        escaped = re.escape(input_str)
        
        # Allow common substitutions
        pattern = escaped
        pattern = pattern.replace(r"\ ", r"\s*")  # Flexible whitespace
        pattern = pattern.replace("s", "[sz]?")   # Optional 's'
        
        return f"(?i).*{pattern}.*"
    
    def build_query(
        self,
        intent: str,
        entities: Dict[str, Any],
        available_orgs: Optional[List[str]] = None
    ) -> Neo4jQuery:
        """
        Build a Neo4j query based on intent and entities.
        
        Args:
            intent: Query intent
            entities: Extracted entities
            available_orgs: Available organizations for fuzzy matching
            
        Returns:
            Neo4jQuery object with fuzzy support
        """
        fuzzy_matches = []
        confidence = 1.0
        
        # Apply fuzzy matching to organization names
        if self.enable_fuzzy and 'organization' in entities and available_orgs:
            org_input = entities['organization']
            matches = self.fuzzy_matcher.fuzzy_match(
                org_input,
                available_orgs,
                threshold=self.fuzzy_threshold
            )
            
            if matches:
                best_match = matches[0]
                entities['organization'] = best_match['match']
                fuzzy_matches.append(MatchResult(
                    input=org_input,
                    matched=best_match['match'],
                    score=best_match['score'],
                    method='fuzzy'
                ))
                confidence *= best_match['score']
        
        # Build query based on intent
        if intent == 'find_configurations':
            return self._build_configuration_query(entities, fuzzy_matches, confidence)
        elif intent == 'find_dependencies':
            return self._build_dependency_query(entities, fuzzy_matches, confidence)
        elif intent == 'impact_analysis':
            return self._build_impact_query(entities, fuzzy_matches, confidence)
        elif intent == 'find_passwords':
            return self._build_password_query(entities, fuzzy_matches, confidence)
        elif intent == 'recent_changes':
            return self._build_changes_query(entities, fuzzy_matches, confidence)
        elif intent == 'service_map':
            return self._build_service_topology_query(entities, fuzzy_matches, confidence)
        else:
            return self._build_general_search_query(entities, fuzzy_matches, confidence)
    
    def _build_configuration_query(
        self,
        entities: Dict[str, Any],
        fuzzy_matches: List[MatchResult],
        confidence: float
    ) -> Neo4jQuery:
        """Build configuration search query with fuzzy support."""
        org_name = entities.get('organization', '')
        config_name = entities.get('configuration', '')
        config_type = entities.get('type')
        os = entities.get('os')
        
        # Build patterns
        org_pattern = self.build_fuzzy_pattern(org_name) if org_name else '.*'
        config_pattern = self.build_fuzzy_pattern(config_name) if config_name else None
        
        parameters = {
            'org_pattern': org_pattern,
            'org_id': None,
            'org_exact': org_name,
            'config_pattern': config_pattern,
            'config_exact': config_name,
            'config_type': config_type,
            'os': os,
            'min_confidence': self.fuzzy_threshold,
            'fuzzy_confidence': confidence
        }
        
        query = Neo4jQuery(
            cypher=self.query_templates['find_configurations_fuzzy'],
            parameters=parameters,
            description=f"Find configurations for {org_name}",
            expected_return_type='Configuration',
            fuzzy_matched_entities=fuzzy_matches,
            confidence=confidence,
            index_hints=['c:Configuration(name, type)', 'o:Organization(name)'],
            ranking_expression='match_confidence'
        )
        
        return query
    
    def _build_dependency_query(
        self,
        entities: Dict[str, Any],
        fuzzy_matches: List[MatchResult],
        confidence: float
    ) -> Neo4jQuery:
        """Build dependency query with cycle detection."""
        config_name = entities.get('configuration', '')
        
        parameters = {
            'config_name': config_name,
            'max_depth': min(self.max_traversal_depth, 5),
            'min_confidence': self.fuzzy_threshold
        }
        
        query = Neo4jQuery(
            cypher=self.query_templates['find_dependencies_safe'],
            parameters=parameters,
            description=f"Find dependencies for {config_name}",
            expected_return_type='Path',
            fuzzy_matched_entities=fuzzy_matches,
            confidence=confidence,
            traversal_depth=parameters['max_depth'],
            ranking_expression='path_confidence'
        )
        
        return query
    
    def _build_impact_query(
        self,
        entities: Dict[str, Any],
        fuzzy_matches: List[MatchResult],
        confidence: float
    ) -> Neo4jQuery:
        """Build impact analysis query with criticality ranking."""
        config_name = entities.get('configuration', '')
        config_pattern = self.build_fuzzy_pattern(config_name)
        
        parameters = {
            'config_pattern': config_pattern,
            'max_depth': min(self.max_traversal_depth, 5)
        }
        
        query = Neo4jQuery(
            cypher=self.query_templates['impact_analysis_ranked'],
            parameters=parameters,
            description=f"Analyze impact of {config_name} failure",
            expected_return_type='Impact',
            fuzzy_matched_entities=fuzzy_matches,
            confidence=confidence,
            traversal_depth=parameters['max_depth'],
            ranking_expression='criticality_score DESC, proximity'
        )
        
        return query
    
    def _build_password_query(
        self,
        entities: Dict[str, Any],
        fuzzy_matches: List[MatchResult],
        confidence: float
    ) -> Neo4jQuery:
        """Build password query with age-based ranking."""
        target = entities.get('configuration', entities.get('organization', ''))
        target_pattern = self.build_fuzzy_pattern(target)
        
        parameters = {
            'target_pattern': target_pattern,
            'target_id': None,
            'max_age': 365  # Default to passwords changed within a year
        }
        
        query = Neo4jQuery(
            cypher=self.query_templates['find_passwords_ranked'],
            parameters=parameters,
            description=f"Find passwords for {target}",
            expected_return_type='Password',
            fuzzy_matched_entities=fuzzy_matches,
            confidence=confidence,
            ranking_expression='risk_score'
        )
        
        return query
    
    def _build_changes_query(
        self,
        entities: Dict[str, Any],
        fuzzy_matches: List[MatchResult],
        confidence: float
    ) -> Neo4jQuery:
        """Build recent changes query."""
        target = entities.get('configuration', entities.get('organization', ''))
        target_pattern = self.build_fuzzy_pattern(target)
        time_range = entities.get('time_range', 'recent')
        
        # Map time range to days
        days_map = {
            'today': 1,
            'yesterday': 2,
            'this_week': 7,
            'recent': 30
        }
        days_back = days_map.get(time_range, 7)
        
        parameters = {
            'target_pattern': target_pattern,
            'days_back': days_back
        }
        
        query = Neo4jQuery(
            cypher=self.query_templates['recent_changes_fuzzy'],
            parameters=parameters,
            description=f"Find recent changes for {target}",
            expected_return_type='Change',
            fuzzy_matched_entities=fuzzy_matches,
            confidence=confidence,
            ranking_expression='hours_ago'
        )
        
        return query
    
    def _build_service_topology_query(
        self,
        entities: Dict[str, Any],
        fuzzy_matches: List[MatchResult],
        confidence: float
    ) -> Neo4jQuery:
        """Build service topology query."""
        service = entities.get('configuration', entities.get('service', ''))
        service_pattern = self.build_fuzzy_pattern(service)
        
        parameters = {
            'service_pattern': service_pattern
        }
        
        query = Neo4jQuery(
            cypher=self.query_templates['service_topology_fuzzy'],
            parameters=parameters,
            description=f"Map service topology for {service}",
            expected_return_type='ServiceTopology',
            fuzzy_matched_entities=fuzzy_matches,
            confidence=confidence,
            ranking_expression='criticality_score'
        )
        
        return query
    
    def _build_general_search_query(
        self,
        entities: Dict[str, Any],
        fuzzy_matches: List[MatchResult],
        confidence: float
    ) -> Neo4jQuery:
        """Build general cross-entity search query."""
        search_term = entities.get('query', '')
        search_pattern = self.build_fuzzy_pattern(search_term)
        
        # Default entity types to search
        entity_types = entities.get('entity_types', [
            'Configuration',
            'Organization', 
            'Service',
            'Password',
            'Document'
        ])
        
        parameters = {
            'search_pattern': search_pattern,
            'search_exact': search_term,
            'entity_types': entity_types,
            'min_relevance': self.fuzzy_threshold
        }
        
        query = Neo4jQuery(
            cypher=self.query_templates['cross_org_search'],
            parameters=parameters,
            description=f"Search for {search_term}",
            expected_return_type='Mixed',
            fuzzy_matched_entities=fuzzy_matches,
            confidence=confidence,
            ranking_expression='relevance'
        )
        
        return query
    
    def optimize_query(self, query: Neo4jQuery) -> Neo4jQuery:
        """
        Optimize a query for performance.
        
        Args:
            query: Query to optimize
            
        Returns:
            Optimized query
        """
        optimized_cypher = query.cypher
        
        # Add index hints if not present
        for hint in query.index_hints:
            if f"USING INDEX {hint}" not in optimized_cypher:
                optimized_cypher = f"// Optimization hint\nUSING INDEX {hint}\n" + optimized_cypher
        
        # Add query planner hints for large traversals
        if query.traversal_depth > 3:
            optimized_cypher = "// Use BFS for deep traversals\nCYPHER planner=cost\n" + optimized_cypher
        
        # Add result limiting if not present
        if "LIMIT" not in optimized_cypher:
            optimized_cypher += "\nLIMIT 100"
        
        query.cypher = optimized_cypher
        return query