"""Generates comprehensive infrastructure documentation from normalized data."""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class DocumentGenerator:
    """Generates professional infrastructure documentation."""

    MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB limit

    def __init__(self):
        """Initialize the document generator."""
        self.section_generators = {
            'configurations': self._generate_configurations_section,
            'flexible_assets': self._generate_flexible_assets_section,
            'contacts': self._generate_contacts_section,
            'locations': self._generate_locations_section,
            'documents': self._generate_documents_section,
            'passwords': self._generate_passwords_section,
            'domains': self._generate_domains_section,
            'networks': self._generate_networks_section
        }

    async def generate(
        self,
        normalized_data: dict[str, Any],
        organization_name: str,
        snapshot_id: str
    ) -> dict[str, Any]:
        """Generate infrastructure documentation.

        Args:
            normalized_data: Normalized data from DataNormalizer
            organization_name: Name of the organization
            snapshot_id: Snapshot ID for reference

        Returns:
            Generated document with content and metadata
        """
        logger.info(f"Generating documentation for {organization_name}")

        # Start building the document
        document = {
            'title': f"Infrastructure Documentation - {organization_name}",
            'generated_at': datetime.utcnow().isoformat(),
            'snapshot_id': snapshot_id,
            'content': '',
            'sections': [],
            'table_of_contents': []
        }

        # Generate markdown content
        markdown_content = self._generate_header(organization_name, normalized_data)

        # Add executive summary
        markdown_content += self._generate_executive_summary(normalized_data)

        # Generate table of contents
        toc = self._generate_table_of_contents(normalized_data)
        markdown_content += toc

        # Generate sections for each resource type
        for resource_type in ['configurations', 'flexible_assets', 'contacts',
                             'locations', 'networks', 'domains', 'passwords', 'documents']:

            # Get resources of this type
            resources = [
                r['data'] for r in normalized_data.get('resources', [])
                if r['type'] == resource_type
            ]

            if not resources:
                continue

            # Generate section
            generator = self.section_generators.get(resource_type)
            if generator:
                section_content = generator(
                    resources,
                    normalized_data.get('summaries', {}).get(resource_type, {})
                )
                markdown_content += section_content

                # Track section in metadata
                document['sections'].append({
                    'type': resource_type,
                    'count': len(resources)
                })

        # Add appendix
        markdown_content += self._generate_appendix(normalized_data)

        # Check document size
        content_size = len(markdown_content.encode('utf-8'))
        if content_size > self.MAX_DOCUMENT_SIZE:
            logger.warning(f"Document size ({content_size} bytes) exceeds limit, truncating")
            markdown_content = self._truncate_document(markdown_content)

        document['content'] = markdown_content
        document['size_bytes'] = len(markdown_content.encode('utf-8'))

        return document

    def _generate_header(self, organization_name: str, data: dict) -> str:
        """Generate document header.

        Args:
            organization_name: Organization name
            data: Normalized data

        Returns:
            Markdown header
        """
        header = f"""# Infrastructure Documentation
## {organization_name}

**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Document Type:** Complete Infrastructure Audit
**Total Resources:** {len(data.get('resources', []))}

---

"""
        return header

    def _generate_executive_summary(self, data: dict) -> str:
        """Generate executive summary section.

        Args:
            data: Normalized data

        Returns:
            Markdown executive summary
        """
        counts = data.get('counts', {})

        summary = """## Executive Summary

This document provides a comprehensive overview of the IT infrastructure and resources
managed for this organization. The documentation includes detailed information about
configurations, assets, contacts, and network resources.

### Resource Overview

| Resource Type | Count |
|--------------|-------|
"""

        for resource_type, count in counts.items():
            display_name = resource_type.replace('_', ' ').title()
            summary += f"| {display_name} | {count} |\n"

        summary += "\n---\n\n"
        return summary

    def _generate_table_of_contents(self, data: dict) -> str:
        """Generate table of contents.

        Args:
            data: Normalized data

        Returns:
            Markdown table of contents
        """
        toc = "## Table of Contents\n\n"

        section_num = 1
        for resource_type in ['configurations', 'flexible_assets', 'contacts',
                            'locations', 'networks', 'domains', 'passwords', 'documents']:

            count = data.get('counts', {}).get(resource_type, 0)
            if count > 0:
                display_name = resource_type.replace('_', ' ').title()
                toc += f"{section_num}. [{display_name}](#{resource_type}) ({count} items)\n"
                section_num += 1

        toc += "\n---\n\n"
        return toc

    def _generate_configurations_section(self, configs: list[dict], summary: dict) -> str:
        """Generate configurations section.

        Args:
            configs: List of configuration items
            summary: Summary statistics

        Returns:
            Markdown section
        """
        section = "## Configurations\n\n"

        # Add summary
        if summary.get('by_type'):
            section += "### Configuration Types\n\n"
            for config_type, count in summary['by_type'].items():
                section += f"- **{config_type}**: {count} devices\n"
            section += "\n"

        # Create table of configurations
        section += """### Configuration Details

| Name | Type | Status | IP Address | Operating System | Location |
|------|------|--------|------------|------------------|----------|
"""

        for config in configs[:100]:  # Limit to first 100 for readability
            name = config.get('name', 'N/A')
            config_type = config.get('type', 'N/A')
            status = config.get('status', 'N/A')
            ip = config.get('primary_ip', 'N/A')
            os = config.get('operating_system', 'N/A')
            location = config.get('location', 'N/A')

            section += f"| {name} | {config_type} | {status} | {ip} | {os} | {location} |\n"

        if len(configs) > 100:
            section += f"\n*Note: Showing first 100 of {len(configs)} configurations*\n"

        section += "\n---\n\n"
        return section

    def _generate_flexible_assets_section(self, assets: list[dict], summary: dict) -> str:
        """Generate flexible assets section.

        Args:
            assets: List of flexible asset items
            summary: Summary statistics

        Returns:
            Markdown section
        """
        section = "## Flexible Assets\n\n"

        # Group by type
        by_type = {}
        for asset in assets:
            asset_type = asset.get('type', 'Unknown')
            if asset_type not in by_type:
                by_type[asset_type] = []
            by_type[asset_type].append(asset)

        # Generate subsection for each type
        for asset_type, type_assets in by_type.items():
            section += f"### {asset_type} ({len(type_assets)} items)\n\n"

            # Create simple list
            for asset in type_assets[:20]:  # Limit each type to 20 items
                name = asset.get('name', 'Unnamed')
                section += f"- **{name}**"

                # Add key traits if available
                traits = asset.get('traits', {})
                if traits:
                    important_traits = []
                    for key, value in list(traits.items())[:3]:  # Show first 3 traits
                        if value:
                            important_traits.append(f"{key}: {value}")
                    if important_traits:
                        section += f" ({', '.join(important_traits)})"

                section += "\n"

            if len(type_assets) > 20:
                section += f"\n*... and {len(type_assets) - 20} more {asset_type} assets*\n"

            section += "\n"

        section += "---\n\n"
        return section

    def _generate_contacts_section(self, contacts: list[dict], summary: dict) -> str:
        """Generate contacts section.

        Args:
            contacts: List of contact items
            summary: Summary statistics

        Returns:
            Markdown section
        """
        section = "## Contacts\n\n"

        # Separate important contacts
        important = [c for c in contacts if c.get('important')]
        regular = [c for c in contacts if not c.get('important')]

        if important:
            section += f"### Important Contacts ({len(important)})\n\n"
            section += "| Name | Title | Location | Primary Email | Primary Phone |\n"
            section += "|------|-------|----------|---------------|---------------|\n"

            for contact in important[:20]:
                name = contact.get('name', 'N/A')
                title = contact.get('title', 'N/A')
                location = contact.get('location', 'N/A')

                # Get primary email
                emails = contact.get('emails', [])
                email = emails[0].get('value', 'N/A') if emails else 'N/A'

                # Get primary phone
                phones = contact.get('phones', [])
                phone = phones[0].get('value', 'N/A') if phones else 'N/A'

                section += f"| {name} | {title} | {location} | {email} | {phone} |\n"

            section += "\n"

        if regular:
            section += f"### Additional Contacts ({len(regular)})\n\n"
            section += "*Full contact list available in IT Glue*\n\n"

        section += "---\n\n"
        return section

    def _generate_locations_section(self, locations: list[dict], summary: dict) -> str:
        """Generate locations section.

        Args:
            locations: List of location items
            summary: Summary statistics

        Returns:
            Markdown section
        """
        section = "## Locations\n\n"

        # Separate primary locations
        primary = [loc for loc in locations if loc.get('primary')]
        secondary = [loc for loc in locations if not loc.get('primary')]

        if primary:
            section += "### Primary Locations\n\n"
            for loc in primary:
                name = loc.get('name', 'N/A')
                address = loc.get('address', '')
                city = loc.get('city', '')
                region = loc.get('region', '')
                postal = loc.get('postal_code', '')
                phone = loc.get('phone', '')

                section += f"**{name}**\n"
                if address:
                    section += f"- Address: {address}"
                    if city:
                        section += f", {city}"
                    if region:
                        section += f", {region}"
                    if postal:
                        section += f" {postal}"
                    section += "\n"
                if phone:
                    section += f"- Phone: {phone}\n"
                section += "\n"

        if secondary:
            section += f"### Additional Locations ({len(secondary)})\n\n"
            for loc in secondary[:10]:
                name = loc.get('name', 'N/A')
                city = loc.get('city', '')
                section += f"- **{name}**"
                if city:
                    section += f" ({city})"
                section += "\n"

            if len(secondary) > 10:
                section += f"\n*... and {len(secondary) - 10} more locations*\n"

        section += "\n---\n\n"
        return section

    def _generate_networks_section(self, networks: list[dict], summary: dict) -> str:
        """Generate networks section.

        Args:
            networks: List of network items
            summary: Summary statistics

        Returns:
            Markdown section
        """
        section = "## Networks\n\n"

        section += "| Network Name | Network/CIDR | Location | Description |\n"
        section += "|--------------|--------------|----------|-------------|\n"

        for network in networks[:50]:
            name = network.get('name', 'N/A')
            network_cidr = network.get('network', 'N/A')
            location = network.get('location', 'N/A')
            description = network.get('description', '')[:50]  # Truncate long descriptions

            section += f"| {name} | {network_cidr} | {location} | {description} |\n"

        if len(networks) > 50:
            section += f"\n*Showing first 50 of {len(networks)} networks*\n"

        section += "\n---\n\n"
        return section

    def _generate_domains_section(self, domains: list[dict], summary: dict) -> str:
        """Generate domains section.

        Args:
            domains: List of domain items
            summary: Summary statistics

        Returns:
            Markdown section
        """
        section = "## Domains\n\n"

        section += "| Domain | Registrar | Expires | Notes |\n"
        section += "|--------|-----------|---------|-------|\n"

        for domain in domains:
            name = domain.get('name', 'N/A')
            registrar = domain.get('registrar', 'N/A')
            expires = domain.get('expires', 'N/A')
            notes = domain.get('notes', '')[:50] if domain.get('notes') else ''

            section += f"| {name} | {registrar} | {expires} | {notes} |\n"

        section += "\n---\n\n"
        return section

    def _generate_passwords_section(self, passwords: list[dict], summary: dict) -> str:
        """Generate passwords section (metadata only).

        Args:
            passwords: List of password items
            summary: Summary statistics

        Returns:
            Markdown section
        """
        section = "## Password Vault Summary\n\n"

        # Group by category
        by_category = {}
        for pwd in passwords:
            category = pwd.get('category', 'Uncategorized')
            if category not in by_category:
                by_category[category] = 0
            by_category[category] += 1

        section += "### Password Categories\n\n"
        for category, count in by_category.items():
            section += f"- **{category}**: {count} passwords\n"

        section += f"\n**Total Passwords:** {len(passwords)}\n"
        section += "\n*Note: Actual passwords are securely stored in IT Glue and not included in this document*\n"

        section += "\n---\n\n"
        return section

    def _generate_documents_section(self, documents: list[dict], summary: dict) -> str:
        """Generate documents section.

        Args:
            documents: List of document items
            summary: Summary statistics

        Returns:
            Markdown section
        """
        section = "## Documentation Library\n\n"

        section += f"**Total Documents:** {len(documents)}\n\n"

        # List recent documents
        section += "### Recent Documentation\n\n"

        # Sort by updated_at
        sorted_docs = sorted(
            documents,
            key=lambda x: x.get('updated_at', ''),
            reverse=True
        )

        for doc in sorted_docs[:20]:
            name = doc.get('name', 'Untitled')
            updated = doc.get('updated_at', 'N/A')
            section += f"- **{name}** (Updated: {updated})\n"

        if len(documents) > 20:
            section += f"\n*Showing most recent 20 of {len(documents)} documents*\n"

        section += "\n---\n\n"
        return section

    def _generate_appendix(self, data: dict) -> str:
        """Generate appendix section.

        Args:
            data: Normalized data

        Returns:
            Markdown appendix
        """
        appendix = """## Appendix

### Document Information

- **Generation Method:** Automated IT Glue API Query
- **Data Source:** IT Glue Platform
- **Snapshot ID:** {snapshot_id}
- **Timestamp:** {timestamp}

### Data Retention

This documentation represents a point-in-time snapshot of the infrastructure.
For the most current information, please refer to the IT Glue platform directly.

### Contact Information

For questions about this documentation or to request updates, please contact
your IT administrator or refer to the IT Glue platform.

---

*End of Document*
""".format(
            snapshot_id=data.get('snapshot_id', 'N/A'),
            timestamp=data.get('timestamp', 'N/A')
        )

        return appendix

    def _truncate_document(self, content: str) -> str:
        """Truncate document to stay within size limit.

        Args:
            content: Full document content

        Returns:
            Truncated content
        """
        max_chars = self.MAX_DOCUMENT_SIZE // 4  # Rough estimate for UTF-8

        if len(content) <= max_chars:
            return content

        # Truncate and add notice
        truncated = content[:max_chars - 500]
        truncated += "\n\n---\n\n## Document Truncated\n\n"
        truncated += "This document has been truncated due to size limitations. "
        truncated += "Please refer to IT Glue for complete information.\n"

        return truncated
