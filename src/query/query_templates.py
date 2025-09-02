"""Query templates for common IT support scenarios."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional


class TemplateCategory(Enum):
    """Categories of query templates."""
    EMERGENCY = "emergency"
    RECOVERY = "recovery"
    INVESTIGATION = "investigation"
    ASSESSMENT = "assessment"
    MAINTENANCE = "maintenance"
    MONITORING = "monitoring"
    COMPLIANCE = "compliance"
    DOCUMENTATION = "documentation"


class QueryPriority(Enum):
    """Priority levels for queries."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class QueryParameter:
    """Parameter for a query template."""
    name: str
    description: str
    required: bool
    default_value: Optional[Any] = None
    value_type: type = str
    validator: Optional[Callable] = None


@dataclass
class SubQuery:
    """A sub-query within a template."""
    query: str
    purpose: str
    priority: QueryPriority
    parameters: dict[str, Any] = field(default_factory=dict)
    depends_on: Optional[str] = None


@dataclass
class QueryTemplate:
    """Template for common query patterns."""
    id: str
    name: str
    description: str
    category: TemplateCategory
    parameters: list[QueryParameter]
    sub_queries: list[SubQuery]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExpandedQuery:
    """Result of expanding a query template."""
    template_id: str
    template_name: str
    expanded_queries: list[str]
    parameters_used: dict[str, Any]
    estimated_time_ms: int
    metadata: dict[str, Any]


class QueryTemplateEngine:
    """Engine for managing and expanding query templates."""

    def __init__(self):
        """Initialize query template engine."""
        self.templates = self._initialize_templates()

    def _initialize_templates(self) -> dict[str, QueryTemplate]:
        """Initialize the top 10 query templates."""
        templates = {}

        # 1. Emergency Server Down
        templates["emergency_server_down"] = QueryTemplate(
            id="emergency_server_down",
            name="Emergency Server Down",
            description="Comprehensive investigation for server outage",
            category=TemplateCategory.EMERGENCY,
            parameters=[
                QueryParameter(
                    name="server_name",
                    description="Name or ID of the affected server",
                    required=True,
                    value_type=str
                ),
                QueryParameter(
                    name="time_window",
                    description="Time window to check (in hours)",
                    required=False,
                    default_value=24,
                    value_type=int
                )
            ],
            sub_queries=[
                SubQuery(
                    query="MATCH (s:Server {name: $server_name}) RETURN s.status, s.last_seen, s.ip_address",
                    purpose="Get current server status",
                    priority=QueryPriority.CRITICAL,
                    parameters={"server_name": "{{server_name}}"}
                ),
                SubQuery(
                    query="MATCH (s:Server {name: $server_name})-[:RUNS]->(svc:Service) RETURN svc.name, svc.status",
                    purpose="Check dependent services",
                    priority=QueryPriority.CRITICAL,
                    parameters={"server_name": "{{server_name}}"}
                ),
                SubQuery(
                    query="MATCH (s:Server {name: $server_name})-[:DEPENDS_ON]->(dep) RETURN dep.name, dep.type, dep.status",
                    purpose="Check dependencies",
                    priority=QueryPriority.HIGH,
                    parameters={"server_name": "{{server_name}}"}
                ),
                SubQuery(
                    query="MATCH (s:Server {name: $server_name})<-[:MODIFIED]-(c:Change) WHERE c.timestamp > $since RETURN c",
                    purpose="Recent changes",
                    priority=QueryPriority.HIGH,
                    parameters={"server_name": "{{server_name}}", "since": "{{time_window}}"}
                ),
                SubQuery(
                    query="MATCH (s:Server {name: $server_name})-[:HAS_CREDENTIAL]->(p:Password) RETURN p.type, p.last_rotated",
                    purpose="Get access credentials",
                    priority=QueryPriority.MEDIUM,
                    parameters={"server_name": "{{server_name}}"}
                )
            ]
        )

        # 2. Password Recovery
        templates["password_recovery"] = QueryTemplate(
            id="password_recovery",
            name="Password Recovery",
            description="Retrieve and validate password information",
            category=TemplateCategory.RECOVERY,
            parameters=[
                QueryParameter(
                    name="system_name",
                    description="System or service name",
                    required=True,
                    value_type=str
                ),
                QueryParameter(
                    name="password_type",
                    description="Type of password (admin, root, service)",
                    required=False,
                    default_value="admin",
                    value_type=str
                ),
                QueryParameter(
                    name="organization",
                    description="Organization name",
                    required=False,
                    value_type=str
                )
            ],
            sub_queries=[
                SubQuery(
                    query="MATCH (p:Password {type: $password_type})-[:FOR_SYSTEM]->(s {name: $system_name}) RETURN p",
                    purpose="Find specific password",
                    priority=QueryPriority.CRITICAL,
                    parameters={"system_name": "{{system_name}}", "password_type": "{{password_type}}"}
                ),
                SubQuery(
                    query="MATCH (p:Password)-[:FOR_SYSTEM]->(s {name: $system_name}) RETURN p.type, p.username, p.last_rotated",
                    purpose="List all passwords for system",
                    priority=QueryPriority.HIGH,
                    parameters={"system_name": "{{system_name}}"}
                ),
                SubQuery(
                    query="MATCH (p:Password {type: $password_type})-[:SIMILAR_TO]->(related) RETURN related",
                    purpose="Find related passwords",
                    priority=QueryPriority.MEDIUM,
                    parameters={"password_type": "{{password_type}}"}
                ),
                SubQuery(
                    query="MATCH (p:Password)-[:FOR_SYSTEM]->(s {name: $system_name}) WHERE p.expires_at < $now RETURN p",
                    purpose="Check password expiration",
                    priority=QueryPriority.HIGH,
                    parameters={"system_name": "{{system_name}}", "now": "{{current_time}}"}
                )
            ]
        )

        # 3. Change Investigation
        templates["change_investigation"] = QueryTemplate(
            id="change_investigation",
            name="Change Investigation",
            description="Investigate recent changes and their impact",
            category=TemplateCategory.INVESTIGATION,
            parameters=[
                QueryParameter(
                    name="time_range",
                    description="Time range in hours",
                    required=False,
                    default_value=72,
                    value_type=int
                ),
                QueryParameter(
                    name="change_type",
                    description="Type of change (config, password, access)",
                    required=False,
                    value_type=str
                ),
                QueryParameter(
                    name="affected_system",
                    description="Specific system to investigate",
                    required=False,
                    value_type=str
                )
            ],
            sub_queries=[
                SubQuery(
                    query="MATCH (c:Change) WHERE c.timestamp > $since RETURN c ORDER BY c.timestamp DESC",
                    purpose="Get all recent changes",
                    priority=QueryPriority.HIGH,
                    parameters={"since": "{{time_range}}"}
                ),
                SubQuery(
                    query="MATCH (c:Change)-[:AFFECTED]->(s:System) WHERE c.timestamp > $since RETURN c, s",
                    purpose="Changes and affected systems",
                    priority=QueryPriority.HIGH,
                    parameters={"since": "{{time_range}}"}
                ),
                SubQuery(
                    query="MATCH (c:Change)-[:PERFORMED_BY]->(u:User) WHERE c.timestamp > $since RETURN u, count(c)",
                    purpose="Changes by user",
                    priority=QueryPriority.MEDIUM,
                    parameters={"since": "{{time_range}}"}
                ),
                SubQuery(
                    query="MATCH (c:Change)-[:TRIGGERED]->(i:Incident) WHERE c.timestamp > $since RETURN c, i",
                    purpose="Changes causing incidents",
                    priority=QueryPriority.CRITICAL,
                    parameters={"since": "{{time_range}}"}
                )
            ]
        )

        # 4. Impact Assessment
        templates["impact_assessment"] = QueryTemplate(
            id="impact_assessment",
            name="Impact Assessment",
            description="Assess impact of system failure or change",
            category=TemplateCategory.ASSESSMENT,
            parameters=[
                QueryParameter(
                    name="target_system",
                    description="System to assess impact for",
                    required=True,
                    value_type=str
                ),
                QueryParameter(
                    name="impact_depth",
                    description="Depth of dependency traversal",
                    required=False,
                    default_value=3,
                    value_type=int
                )
            ],
            sub_queries=[
                SubQuery(
                    query="MATCH (s {name: $target_system})<-[:DEPENDS_ON*1..$depth]-(dependent) RETURN dependent",
                    purpose="Find dependent systems",
                    priority=QueryPriority.CRITICAL,
                    parameters={"target_system": "{{target_system}}", "depth": "{{impact_depth}}"}
                ),
                SubQuery(
                    query="MATCH (s {name: $target_system})<-[:USES]-(u:User) RETURN count(u)",
                    purpose="Count affected users",
                    priority=QueryPriority.HIGH,
                    parameters={"target_system": "{{target_system}}"}
                ),
                SubQuery(
                    query="MATCH (s {name: $target_system})-[:PROVIDES]->(svc:Service) RETURN svc",
                    purpose="Services provided",
                    priority=QueryPriority.HIGH,
                    parameters={"target_system": "{{target_system}}"}
                ),
                SubQuery(
                    query="MATCH (s {name: $target_system})-[:CRITICAL_FOR]->(p:Process) RETURN p",
                    purpose="Critical business processes",
                    priority=QueryPriority.CRITICAL,
                    parameters={"target_system": "{{target_system}}"}
                )
            ]
        )

        # 5. Security Audit
        templates["security_audit"] = QueryTemplate(
            id="security_audit",
            name="Security Audit",
            description="Comprehensive security audit queries",
            category=TemplateCategory.COMPLIANCE,
            parameters=[
                QueryParameter(
                    name="audit_scope",
                    description="Scope of audit (passwords, access, certificates)",
                    required=False,
                    default_value="all",
                    value_type=str
                ),
                QueryParameter(
                    name="days_threshold",
                    description="Days threshold for expiration",
                    required=False,
                    default_value=30,
                    value_type=int
                )
            ],
            sub_queries=[
                SubQuery(
                    query="MATCH (p:Password) WHERE p.last_rotated < $threshold RETURN p",
                    purpose="Find old passwords",
                    priority=QueryPriority.CRITICAL,
                    parameters={"threshold": "{{days_threshold}}"}
                ),
                SubQuery(
                    query="MATCH (c:Certificate) WHERE c.expires_at < $threshold RETURN c",
                    purpose="Expiring certificates",
                    priority=QueryPriority.CRITICAL,
                    parameters={"threshold": "{{days_threshold}}"}
                ),
                SubQuery(
                    query="MATCH (u:User)-[:HAS_ACCESS]->(s:System) WHERE u.last_active < $threshold RETURN u, s",
                    purpose="Inactive user access",
                    priority=QueryPriority.HIGH,
                    parameters={"threshold": "{{days_threshold}}"}
                ),
                SubQuery(
                    query="MATCH (s:System) WHERE NOT exists(s.security_scan_date) RETURN s",
                    purpose="Systems without security scans",
                    priority=QueryPriority.HIGH,
                    parameters={}
                )
            ]
        )

        # 6. Network Connectivity Check
        templates["network_connectivity"] = QueryTemplate(
            id="network_connectivity",
            name="Network Connectivity Check",
            description="Verify network paths and connectivity",
            category=TemplateCategory.MONITORING,
            parameters=[
                QueryParameter(
                    name="source_system",
                    description="Source system or network",
                    required=True,
                    value_type=str
                ),
                QueryParameter(
                    name="target_system",
                    description="Target system or network",
                    required=True,
                    value_type=str
                )
            ],
            sub_queries=[
                SubQuery(
                    query="MATCH path = shortestPath((s {name: $source})-[:CONNECTED_TO*]-(t {name: $target})) RETURN path",
                    purpose="Find network path",
                    priority=QueryPriority.CRITICAL,
                    parameters={"source": "{{source_system}}", "target": "{{target_system}}"}
                ),
                SubQuery(
                    query="MATCH (s {name: $source})-[:IN_NETWORK]->(n:Network)<-[:IN_NETWORK]-(t {name: $target}) RETURN n",
                    purpose="Common networks",
                    priority=QueryPriority.HIGH,
                    parameters={"source": "{{source_system}}", "target": "{{target_system}}"}
                ),
                SubQuery(
                    query="MATCH (f:Firewall)-[:BLOCKS]->(rule) WHERE rule.source = $source AND rule.target = $target RETURN rule",
                    purpose="Firewall rules",
                    priority=QueryPriority.HIGH,
                    parameters={"source": "{{source_system}}", "target": "{{target_system}}"}
                )
            ]
        )

        # 7. Backup Verification
        templates["backup_verification"] = QueryTemplate(
            id="backup_verification",
            name="Backup Verification",
            description="Verify backup status and recovery points",
            category=TemplateCategory.MAINTENANCE,
            parameters=[
                QueryParameter(
                    name="system_name",
                    description="System to check backups for",
                    required=False,
                    value_type=str
                ),
                QueryParameter(
                    name="days_back",
                    description="Days to look back",
                    required=False,
                    default_value=7,
                    value_type=int
                )
            ],
            sub_queries=[
                SubQuery(
                    query="MATCH (b:Backup)-[:BACKS_UP]->(s:System) WHERE b.timestamp > $since RETURN b, s",
                    purpose="Recent backups",
                    priority=QueryPriority.HIGH,
                    parameters={"since": "{{days_back}}"}
                ),
                SubQuery(
                    query="MATCH (s:System) WHERE NOT exists((s)<-[:BACKS_UP]-(:Backup)) RETURN s",
                    purpose="Systems without backups",
                    priority=QueryPriority.CRITICAL,
                    parameters={}
                ),
                SubQuery(
                    query="MATCH (b:Backup) WHERE b.status = 'failed' AND b.timestamp > $since RETURN b",
                    purpose="Failed backups",
                    priority=QueryPriority.CRITICAL,
                    parameters={"since": "{{days_back}}"}
                )
            ]
        )

        # 8. Service Health Check
        templates["service_health"] = QueryTemplate(
            id="service_health",
            name="Service Health Check",
            description="Comprehensive service health assessment",
            category=TemplateCategory.MONITORING,
            parameters=[
                QueryParameter(
                    name="service_name",
                    description="Service to check",
                    required=False,
                    value_type=str
                ),
                QueryParameter(
                    name="include_dependencies",
                    description="Include dependency health",
                    required=False,
                    default_value=True,
                    value_type=bool
                )
            ],
            sub_queries=[
                SubQuery(
                    query="MATCH (svc:Service) WHERE svc.status != 'running' RETURN svc",
                    purpose="Non-running services",
                    priority=QueryPriority.CRITICAL,
                    parameters={}
                ),
                SubQuery(
                    query="MATCH (svc:Service)-[:DEPENDS_ON]->(dep) WHERE dep.status != 'healthy' RETURN svc, dep",
                    purpose="Services with unhealthy dependencies",
                    priority=QueryPriority.HIGH,
                    parameters={}
                ),
                SubQuery(
                    query="MATCH (svc:Service) RETURN svc.name, svc.cpu_usage, svc.memory_usage, svc.response_time",
                    purpose="Service metrics",
                    priority=QueryPriority.MEDIUM,
                    parameters={}
                )
            ]
        )

        # 9. Configuration Drift Detection
        templates["config_drift"] = QueryTemplate(
            id="config_drift",
            name="Configuration Drift Detection",
            description="Detect configuration changes and drift",
            category=TemplateCategory.COMPLIANCE,
            parameters=[
                QueryParameter(
                    name="baseline_date",
                    description="Baseline date for comparison",
                    required=False,
                    value_type=str
                ),
                QueryParameter(
                    name="system_group",
                    description="Group of systems to check",
                    required=False,
                    value_type=str
                )
            ],
            sub_queries=[
                SubQuery(
                    query="MATCH (c:Configuration)-[:CHANGED_FROM]->(baseline) WHERE c.timestamp > $baseline RETURN c",
                    purpose="Configuration changes",
                    priority=QueryPriority.HIGH,
                    parameters={"baseline": "{{baseline_date}}"}
                ),
                SubQuery(
                    query="MATCH (s:System)-[:HAS_CONFIG]->(c:Configuration) WHERE c.hash != c.baseline_hash RETURN s, c",
                    purpose="Systems with drift",
                    priority=QueryPriority.HIGH,
                    parameters={}
                ),
                SubQuery(
                    query="MATCH (c:Configuration) WHERE c.approved = false RETURN c",
                    purpose="Unapproved configurations",
                    priority=QueryPriority.CRITICAL,
                    parameters={}
                )
            ]
        )

        # 10. Incident Root Cause Analysis
        templates["incident_root_cause"] = QueryTemplate(
            id="incident_root_cause",
            name="Incident Root Cause Analysis",
            description="Analyze incident for root cause",
            category=TemplateCategory.INVESTIGATION,
            parameters=[
                QueryParameter(
                    name="incident_id",
                    description="Incident ID or description",
                    required=True,
                    value_type=str
                ),
                QueryParameter(
                    name="hours_before",
                    description="Hours before incident to analyze",
                    required=False,
                    default_value=24,
                    value_type=int
                )
            ],
            sub_queries=[
                SubQuery(
                    query="MATCH (i:Incident {id: $incident_id})-[:AFFECTED]->(s) RETURN s",
                    purpose="Affected systems",
                    priority=QueryPriority.CRITICAL,
                    parameters={"incident_id": "{{incident_id}}"}
                ),
                SubQuery(
                    query="MATCH (c:Change)-[:BEFORE]->(i:Incident {id: $incident_id}) WHERE c.timestamp > $since RETURN c",
                    purpose="Changes before incident",
                    priority=QueryPriority.CRITICAL,
                    parameters={"incident_id": "{{incident_id}}", "since": "{{hours_before}}"}
                ),
                SubQuery(
                    query="MATCH (e:Error)-[:RELATED_TO]->(i:Incident {id: $incident_id}) RETURN e",
                    purpose="Related errors",
                    priority=QueryPriority.HIGH,
                    parameters={"incident_id": "{{incident_id}}"}
                ),
                SubQuery(
                    query="MATCH (i:Incident {id: $incident_id})-[:SIMILAR_TO]->(past:Incident) RETURN past",
                    purpose="Similar past incidents",
                    priority=QueryPriority.MEDIUM,
                    parameters={"incident_id": "{{incident_id}}"}
                )
            ]
        )

        return templates

    def get_template(self, template_id: str) -> Optional[QueryTemplate]:
        """
        Get a query template by ID.

        Args:
            template_id: Template identifier

        Returns:
            Query template or None
        """
        return self.templates.get(template_id)

    def list_templates(
        self,
        category: Optional[TemplateCategory] = None
    ) -> list[QueryTemplate]:
        """
        List available templates.

        Args:
            category: Optional category filter

        Returns:
            List of templates
        """
        templates = list(self.templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        return templates

    def expand_template(
        self,
        template_id: str,
        parameters: dict[str, Any]
    ) -> ExpandedQuery:
        """
        Expand a template with parameters.

        Args:
            template_id: Template identifier
            parameters: Parameter values

        Returns:
            Expanded query with all sub-queries
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Validate required parameters
        for param in template.parameters:
            if param.required and param.name not in parameters:
                raise ValueError(f"Required parameter '{param.name}' missing")

        # Apply defaults
        final_params = {}
        for param in template.parameters:
            if param.name in parameters:
                final_params[param.name] = parameters[param.name]
            elif param.default_value is not None:
                final_params[param.name] = param.default_value

        # Add system parameters
        final_params["current_time"] = datetime.now().isoformat()

        # Expand sub-queries
        expanded_queries = []
        for sub_query in template.sub_queries:
            expanded = self._expand_query_string(
                sub_query.query,
                final_params
            )
            expanded_queries.append(expanded)

        # Estimate execution time
        estimated_time = len(expanded_queries) * 100  # 100ms per query estimate

        return ExpandedQuery(
            template_id=template_id,
            template_name=template.name,
            expanded_queries=expanded_queries,
            parameters_used=final_params,
            estimated_time_ms=estimated_time,
            metadata={
                "category": template.category.value,
                "sub_query_count": len(expanded_queries),
                "priority_breakdown": self._get_priority_breakdown(template)
            }
        )

    def _expand_query_string(
        self,
        query: str,
        parameters: dict[str, Any]
    ) -> str:
        """
        Expand parameter placeholders in query string.

        Args:
            query: Query string with placeholders
            parameters: Parameter values

        Returns:
            Expanded query string
        """
        result = query

        # Replace {{parameter}} style placeholders
        for key, value in parameters.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                # Handle time window parameters
                if key == "time_window" and isinstance(value, int):
                    # Convert hours to timestamp
                    time_ago = datetime.now() - timedelta(hours=value)
                    result = result.replace(placeholder, time_ago.isoformat())
                else:
                    result = result.replace(placeholder, str(value))

        return result

    def _get_priority_breakdown(
        self,
        template: QueryTemplate
    ) -> dict[str, int]:
        """
        Get priority breakdown for template.

        Args:
            template: Query template

        Returns:
            Count by priority level
        """
        breakdown = {
            QueryPriority.CRITICAL.value: 0,
            QueryPriority.HIGH.value: 0,
            QueryPriority.MEDIUM.value: 0,
            QueryPriority.LOW.value: 0
        }

        for sub_query in template.sub_queries:
            breakdown[sub_query.priority.value] += 1

        return breakdown

    def search_templates(
        self,
        keyword: str
    ) -> list[QueryTemplate]:
        """
        Search templates by keyword.

        Args:
            keyword: Search keyword

        Returns:
            Matching templates
        """
        keyword_lower = keyword.lower()
        results = []

        for template in self.templates.values():
            if (keyword_lower in template.name.lower() or
                keyword_lower in template.description.lower()):
                results.append(template)

        return results

    def get_template_suggestions(
        self,
        scenario: str
    ) -> list[str]:
        """
        Get template suggestions for a scenario.

        Args:
            scenario: User's scenario description

        Returns:
            List of suggested template IDs
        """
        scenario_lower = scenario.lower()
        suggestions = []

        # Keywords to template mapping
        keyword_map = {
            "server down": ["emergency_server_down", "impact_assessment"],
            "password": ["password_recovery", "security_audit"],
            "change": ["change_investigation", "config_drift"],
            "incident": ["incident_root_cause", "change_investigation"],
            "backup": ["backup_verification"],
            "network": ["network_connectivity"],
            "health": ["service_health"],
            "security": ["security_audit"],
            "impact": ["impact_assessment"],
            "audit": ["security_audit", "config_drift"]
        }

        for keyword, template_ids in keyword_map.items():
            if keyword in scenario_lower:
                suggestions.extend(template_ids)

        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for template_id in suggestions:
            if template_id not in seen:
                seen.add(template_id)
                unique_suggestions.append(template_id)

        return unique_suggestions
