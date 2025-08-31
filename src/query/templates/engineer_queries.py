"""Top 10 query templates for common support engineer scenarios."""

import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class QueryTemplate:
    """Predefined query template for common tasks."""
    name: str  # e.g., 'emergency_server_down'
    pattern: str  # User-facing pattern
    expands_to: list[str]  # Multiple queries to execute
    parameters: list[str]  # Required parameters
    priority: int  # Execution order
    description: str  # What this template does
    tags: list[str]  # Categories for this template


class EngineerQueryTemplates:
    """Collection of the top 10 query templates for support engineers."""

    def __init__(self):
        """Initialize query templates."""
        self.templates = self._build_templates()

    def _build_templates(self) -> dict[str, QueryTemplate]:
        """Build the top 10 query templates from PRD."""
        return {
            'emergency_server_down': QueryTemplate(
                name='emergency_server_down',
                pattern='EMERGENCY: {server} is down',
                expands_to=[
                    'show dependencies for {server}',
                    'what changed recently for {server}',
                    'show passwords for {server}',
                    'find documentation for {server}',
                    'show monitoring alerts for {server}',
                    'list recent tickets for {server}'
                ],
                parameters=['server'],
                priority=1,
                description='Comprehensive emergency response for server outages',
                tags=['emergency', 'outage', 'critical']
            ),

            'password_recovery': QueryTemplate(
                name='password_recovery',
                pattern='need password for {system}',
                expands_to=[
                    'show admin password for {system}',
                    'show service accounts for {system}',
                    'show related passwords for {system}',
                    'show password history for {system}',
                    'find password documentation for {system}'
                ],
                parameters=['system'],
                priority=2,
                description='Retrieve passwords and credentials for a system',
                tags=['password', 'credentials', 'access']
            ),

            'change_investigation': QueryTemplate(
                name='change_investigation',
                pattern='investigate changes for {system}',
                expands_to=[
                    'show recent changes for {system}',
                    'who changed {system} in the last 7 days',
                    'show change history for {system}',
                    'compare current and previous configuration for {system}',
                    'show change tickets for {system}'
                ],
                parameters=['system'],
                priority=3,
                description='Investigate recent changes and their impact',
                tags=['changes', 'audit', 'investigation']
            ),

            'impact_assessment': QueryTemplate(
                name='impact_assessment',
                pattern='assess impact of {system} failure',
                expands_to=[
                    'what depends on {system}',
                    'show critical dependencies for {system}',
                    'find affected services if {system} fails',
                    'list users of {system}',
                    'show business impact of {system} outage'
                ],
                parameters=['system'],
                priority=4,
                description='Assess the impact of system failures',
                tags=['impact', 'dependencies', 'risk']
            ),

            'compliance_audit': QueryTemplate(
                name='compliance_audit',
                pattern='audit {organization}',
                expands_to=[
                    'show expired passwords for {organization}',
                    'find systems without backups for {organization}',
                    'list non-compliant configurations for {organization}',
                    'show missing documentation for {organization}',
                    'find unpatched systems for {organization}',
                    'show security violations for {organization}'
                ],
                parameters=['organization'],
                priority=5,
                description='Compliance and security audit for organization',
                tags=['compliance', 'audit', 'security']
            ),

            'network_troubleshooting': QueryTemplate(
                name='network_troubleshooting',
                pattern='troubleshoot network for {location}',
                expands_to=[
                    'show network topology for {location}',
                    'list network devices at {location}',
                    'show VLAN configuration for {location}',
                    'find firewall rules for {location}',
                    'show network performance metrics for {location}',
                    'list recent network changes for {location}'
                ],
                parameters=['location'],
                priority=6,
                description='Network troubleshooting and diagnostics',
                tags=['network', 'troubleshooting', 'connectivity']
            ),

            'backup_verification': QueryTemplate(
                name='backup_verification',
                pattern='verify backups for {system}',
                expands_to=[
                    'show backup status for {system}',
                    'when was {system} last backed up',
                    'show backup history for {system}',
                    'find backup documentation for {system}',
                    'show restore procedures for {system}',
                    'list backup failures for {system}'
                ],
                parameters=['system'],
                priority=7,
                description='Verify backup status and recovery procedures',
                tags=['backup', 'recovery', 'disaster recovery']
            ),

            'performance_investigation': QueryTemplate(
                name='performance_investigation',
                pattern='investigate performance of {application}',
                expands_to=[
                    'show performance metrics for {application}',
                    'find resource usage for {application}',
                    'show database queries for {application}',
                    'list slow transactions for {application}',
                    'show error logs for {application}',
                    'compare current and baseline performance for {application}'
                ],
                parameters=['application'],
                priority=8,
                description='Performance analysis and troubleshooting',
                tags=['performance', 'monitoring', 'optimization']
            ),

            'security_incident': QueryTemplate(
                name='security_incident',
                pattern='security incident on {system}',
                expands_to=[
                    'show access logs for {system}',
                    'list recent logins to {system}',
                    'show configuration changes for {system}',
                    'find security alerts for {system}',
                    'show firewall logs for {system}',
                    'list privileged account usage on {system}'
                ],
                parameters=['system'],
                priority=9,
                description='Security incident investigation and response',
                tags=['security', 'incident', 'forensics']
            ),

            'new_employee_setup': QueryTemplate(
                name='new_employee_setup',
                pattern='setup access for {employee} at {organization}',
                expands_to=[
                    'show standard access for {organization}',
                    'list AD groups for {organization}',
                    'show application access matrix for {organization}',
                    'find onboarding documentation for {organization}',
                    'show VPN configuration for {organization}',
                    'list required software for {organization}'
                ],
                parameters=['employee', 'organization'],
                priority=10,
                description='New employee onboarding and access setup',
                tags=['onboarding', 'access', 'setup']
            )
        }

    async def expand_template(
        self,
        template_name: str,
        params: dict[str, str]
    ) -> list[str]:
        """
        Expand a template with provided parameters.

        Args:
            template_name: Name of the template to expand
            params: Parameters to fill in the template

        Returns:
            List of expanded queries

        Raises:
            ValueError: If template not found or missing parameters
        """
        template = self.templates.get(template_name)
        if not template:
            available = ', '.join(self.templates.keys())
            raise ValueError(f"Unknown template: {template_name}. Available: {available}")

        # Validate required parameters
        missing = set(template.parameters) - set(params.keys())
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")

        # Expand queries with parameters
        expanded = []
        for query_pattern in template.expands_to:
            try:
                expanded_query = query_pattern.format(**params)
                expanded.append(expanded_query)
            except KeyError as e:
                logger.warning(f"Failed to expand query pattern: {e}")
                continue

        if not expanded:
            raise ValueError(f"No queries could be expanded for template: {template_name}")

        logger.info(f"Expanded template '{template_name}' to {len(expanded)} queries")
        return expanded

    def get_template(self, template_name: str) -> Optional[QueryTemplate]:
        """Get a specific template by name."""
        return self.templates.get(template_name)

    def list_templates(self) -> list[dict[str, Any]]:
        """List all available templates with metadata."""
        return [
            {
                'name': template.name,
                'description': template.description,
                'parameters': template.parameters,
                'priority': template.priority,
                'tags': template.tags,
                'query_count': len(template.expands_to)
            }
            for template in sorted(
                self.templates.values(),
                key=lambda t: t.priority
            )
        ]

    def find_templates_by_tag(self, tag: str) -> list[QueryTemplate]:
        """Find templates that have a specific tag."""
        return [
            template
            for template in self.templates.values()
            if tag.lower() in [t.lower() for t in template.tags]
        ]

    def validate_parameters(
        self,
        template_name: str,
        params: dict[str, str]
    ) -> dict[str, Any]:
        """
        Validate parameters for a template.

        Returns:
            Dict with 'valid' bool and 'errors' list
        """
        template = self.templates.get(template_name)
        if not template:
            return {
                'valid': False,
                'errors': [f"Template '{template_name}' not found"]
            }

        errors = []

        # Check for missing parameters
        missing = set(template.parameters) - set(params.keys())
        if missing:
            errors.append(f"Missing parameters: {', '.join(missing)}")

        # Check for empty parameters
        empty = [k for k, v in params.items() if not v or not v.strip()]
        if empty:
            errors.append(f"Empty parameters: {', '.join(empty)}")

        # Check for extra parameters (warning only)
        extra = set(params.keys()) - set(template.parameters)
        if extra:
            logger.warning(f"Extra parameters provided: {', '.join(extra)}")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': [f"Extra parameters: {', '.join(extra)}"] if extra else []
        }

    def suggest_template(self, query: str) -> Optional[str]:
        """
        Suggest the most appropriate template based on query keywords.

        Args:
            query: User's natural language query

        Returns:
            Template name or None if no good match
        """
        query_lower = query.lower()

        # Keywords to template mapping
        keyword_map = {
            ('emergency', 'down', 'outage', 'critical'): 'emergency_server_down',
            ('password', 'credential', 'login', 'access'): 'password_recovery',
            ('change', 'modified', 'updated', 'who changed'): 'change_investigation',
            ('impact', 'depends', 'affected', 'failure'): 'impact_assessment',
            ('audit', 'compliance', 'expired', 'violation'): 'compliance_audit',
            ('network', 'connectivity', 'vlan', 'firewall'): 'network_troubleshooting',
            ('backup', 'restore', 'recovery', 'dr'): 'backup_verification',
            ('performance', 'slow', 'latency', 'metrics'): 'performance_investigation',
            ('security', 'incident', 'breach', 'attack'): 'security_incident',
            ('onboard', 'new employee', 'setup', 'provision'): 'new_employee_setup'
        }

        # Score each template based on keyword matches
        scores = {}
        for keywords, template_name in keyword_map.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                scores[template_name] = score

        # Return the highest scoring template
        if scores:
            best_template = max(scores, key=scores.get)
            if scores[best_template] >= 2:  # Require at least 2 keyword matches
                logger.info(f"Suggested template '{best_template}' for query: {query}")
                return best_template

        return None

    def execute_template_priority(
        self,
        templates: list[str]
    ) -> list[str]:
        """
        Order templates by priority for execution.

        Args:
            templates: List of template names

        Returns:
            Ordered list of template names by priority
        """
        template_objects = [
            self.templates[name]
            for name in templates
            if name in self.templates
        ]

        # Sort by priority (lower number = higher priority)
        template_objects.sort(key=lambda t: t.priority)

        return [t.name for t in template_objects]
