"""Unit tests for entity extraction."""

import pytest
from datetime import datetime, timedelta

from src.nlp.entity_extractor import (
    EntityExtractor,
    ExtractedEntity,
    EntityType,
    ExtractionContext
)


class TestEntityExtractor:
    """Test the entity extractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create an entity extractor instance."""
        return EntityExtractor()
        
    @pytest.fixture
    def context(self):
        """Create extraction context with known entities."""
        return ExtractionContext(
            known_organizations=["Acme Corporation", "TechCorp", "Global Systems"],
            known_systems=["prod-web-01", "prod-db-01", "staging-app-01"],
            known_services=["nginx", "mysql", "redis"],
            default_organization="Acme Corporation"
        )
        
    def test_extract_ip_addresses(self, extractor):
        """Test IP address extraction."""
        query = "Check connectivity to 192.168.1.100 and 10.0.0.1"
        entities = extractor.extract_entities(query)
        
        ip_entities = [e for e in entities if e.type == EntityType.IP_ADDRESS]
        assert len(ip_entities) == 2
        assert "192.168.1.100" in [e.normalized for e in ip_entities]
        assert "10.0.0.1" in [e.normalized for e in ip_entities]
        
    def test_extract_ipv6_addresses(self, extractor):
        """Test IPv6 address extraction."""
        query = "Server at 2001:db8::1 is unreachable"
        entities = extractor.extract_entities(query)
        
        ip_entities = [e for e in entities if e.type == EntityType.IP_ADDRESS]
        assert len(ip_entities) >= 1
        assert any("2001:db8::1" in e.text for e in ip_entities)
        
    def test_extract_hostnames(self, extractor):
        """Test hostname extraction."""
        query = "Connect to server.example.com and backup.internal.local"
        entities = extractor.extract_entities(query)
        
        hostname_entities = [e for e in entities if e.type == EntityType.HOSTNAME]
        assert len(hostname_entities) >= 2
        assert "server.example.com" in [e.text for e in hostname_entities]
        assert "backup.internal.local" in [e.text for e in hostname_entities]
        
    def test_extract_emails(self, extractor):
        """Test email extraction."""
        query = "Send alert to admin@example.com and support@company.org"
        entities = extractor.extract_entities(query)
        
        email_entities = [e for e in entities if e.type == EntityType.EMAIL]
        assert len(email_entities) == 2
        assert "admin@example.com" in [e.normalized for e in email_entities]
        assert "support@company.org" in [e.normalized for e in email_entities]
        
    def test_extract_urls(self, extractor):
        """Test URL extraction."""
        query = "Check https://api.example.com/status and http://internal.local:8080"
        entities = extractor.extract_entities(query)
        
        url_entities = [e for e in entities if e.type == EntityType.URL]
        assert len(url_entities) == 2
        assert any("https://api.example.com/status" in e.text for e in url_entities)
        
    def test_extract_dates(self, extractor):
        """Test date extraction."""
        queries = [
            ("Show logs from 2024-01-15", "2024-01-15"),
            ("What happened yesterday", "yesterday"),
            ("Changes on 12/25/2024", "12/25/2024"),
            ("Backup from last Monday", "monday"),
        ]
        
        for query, expected in queries:
            entities = extractor.extract_entities(query)
            date_entities = [e for e in entities if e.type == EntityType.DATE]
            assert len(date_entities) >= 1
            assert any(expected.lower() in e.text.lower() for e in date_entities)
            
    def test_extract_time_ranges(self, extractor):
        """Test time range extraction."""
        queries = [
            "Show logs from last 24 hours",
            "Changes in the past 7 days",
            "Activity since yesterday",
            "Metrics for this week"
        ]
        
        for query in queries:
            entities = extractor.extract_entities(query)
            time_entities = [e for e in entities if e.type == EntityType.TIME_RANGE]
            assert len(time_entities) >= 1
            
    def test_extract_ports(self, extractor):
        """Test port number extraction."""
        query = "Service running on port 8080 and connect to :3306"
        entities = extractor.extract_entities(query)
        
        port_entities = [e for e in entities if e.type == EntityType.PORT]
        assert len(port_entities) == 2
        assert "8080" in [e.normalized for e in port_entities]
        assert "3306" in [e.normalized for e in port_entities]
        
    def test_extract_versions(self, extractor):
        """Test version extraction."""
        query = "Upgrade from v2.4.1 to version 3.0.0-beta"
        entities = extractor.extract_entities(query)
        
        version_entities = [e for e in entities if e.type == EntityType.VERSION]
        assert len(version_entities) >= 2
        assert "2.4.1" in [e.normalized for e in version_entities]
        assert "3.0.0-beta" in [e.normalized for e in version_entities]
        
    def test_extract_organizations(self, extractor, context):
        """Test organization extraction."""
        query = "Show passwords for org Acme Corporation and company TechCorp"
        entities = extractor.extract_entities(query, context)
        
        org_entities = [e for e in entities if e.type == EntityType.ORGANIZATION]
        assert len(org_entities) >= 2
        assert "Acme Corporation" in [e.text for e in org_entities]
        assert "TechCorp" in [e.text for e in org_entities]
        
        # Test confidence for known organizations
        acme_entity = next(e for e in org_entities if "Acme" in e.text)
        assert acme_entity.confidence == 1.0
        
    def test_extract_systems(self, extractor):
        """Test system/server extraction."""
        query = "Check server web-01 and system database-master"
        entities = extractor.extract_entities(query)
        
        system_entities = [e for e in entities if e.type in [EntityType.SYSTEM, EntityType.CONFIGURATION]]
        assert len(system_entities) >= 2
        assert any("web-01" in e.text for e in system_entities)
        assert any("database-master" in e.text for e in system_entities)
        
    def test_extract_services(self, extractor):
        """Test service/application extraction."""
        query = "Restart service nginx and check application mysql status"
        entities = extractor.extract_entities(query)
        
        service_entities = [e for e in entities if e.type in [EntityType.SERVICE, EntityType.APPLICATION]]
        assert len(service_entities) >= 2
        assert any("nginx" in e.text for e in service_entities)
        assert any("mysql" in e.text for e in service_entities)
        
    def test_extract_users(self, extractor):
        """Test user/account extraction."""
        query = "Reset password for user john.doe and account admin@example.com"
        entities = extractor.extract_entities(query)
        
        user_entities = [e for e in entities if e.type == EntityType.USER]
        assert len(user_entities) >= 1
        assert any("john.doe" in e.text for e in user_entities)
        
    def test_extract_password_types(self, extractor):
        """Test password type extraction."""
        query = "Find admin password and root credential for the server"
        entities = extractor.extract_entities(query)
        
        pwd_entities = [e for e in entities if e.type == EntityType.PASSWORD_TYPE]
        assert len(pwd_entities) >= 2
        assert any("admin" in e.text for e in pwd_entities)
        assert any("root" in e.text for e in pwd_entities)
        
    def test_extract_locations(self, extractor):
        """Test location extraction."""
        query = "Servers in datacenter east and location building-A"
        entities = extractor.extract_entities(query)
        
        location_entities = [e for e in entities if e.type == EntityType.LOCATION]
        assert len(location_entities) >= 2
        assert any("east" in e.text for e in location_entities)
        assert any("building-A" in e.text for e in location_entities)
        
    def test_extract_networks(self, extractor):
        """Test network/subnet extraction."""
        query = "Scan network 192.168.0.0/24 and vlan production"
        entities = extractor.extract_entities(query)
        
        network_entities = [e for e in entities if e.type == EntityType.NETWORK]
        assert len(network_entities) >= 2
        assert any("192.168.0.0/24" in e.text for e in network_entities)
        assert any("production" in e.text for e in network_entities)
        
    def test_extract_operating_systems(self, extractor):
        """Test OS extraction."""
        query = "Update Windows Server 2019 and Ubuntu 20.04 systems"
        entities = extractor.extract_entities(query)
        
        os_entities = [e for e in entities if e.type == EntityType.OS]
        assert len(os_entities) >= 2
        assert any("Windows" in e.normalized for e in os_entities)
        assert any("Ubuntu" in e.normalized for e in os_entities)
        
    def test_extract_applications(self, extractor):
        """Test application extraction."""
        query = "Configure Apache and PostgreSQL with Redis cache"
        entities = extractor.extract_entities(query)
        
        app_entities = [e for e in entities if e.type == EntityType.APPLICATION]
        assert len(app_entities) >= 3
        assert any("apache" in e.text.lower() for e in app_entities)
        assert any("PostgreSQL" in e.normalized for e in app_entities)
        assert any("redis" in e.text.lower() for e in app_entities)
        
    def test_no_overlapping_entities(self, extractor):
        """Test that overlapping entities are resolved."""
        query = "Server at 192.168.1.100"
        entities = extractor.extract_entities(query)
        
        # Check no overlapping positions
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                assert not (entity1.start_pos < entity2.end_pos and 
                          entity1.end_pos > entity2.start_pos)
                          
    def test_entity_metadata(self, extractor):
        """Test entity metadata enhancement."""
        query = "Server 192.168.1.100 is down"
        entities = extractor.extract_entities(query)
        
        ip_entity = next((e for e in entities if e.type == EntityType.IP_ADDRESS), None)
        assert ip_entity is not None
        assert "is_private" in ip_entity.metadata
        assert ip_entity.metadata["is_private"] is True
        assert ip_entity.metadata["version"] == 4
        
    def test_known_entity_extraction(self, extractor, context):
        """Test extraction of known entities from context."""
        query = "Check prod-web-01 status"
        entities = extractor.extract_entities(query, context)
        
        system_entities = [e for e in entities if e.type == EntityType.SYSTEM]
        assert len(system_entities) >= 1
        assert system_entities[0].confidence == 1.0
        assert system_entities[0].metadata.get("source") == "known"
        
    def test_complex_query(self, extractor, context):
        """Test extraction from complex query."""
        query = ("Show all passwords for org Acme Corporation on server prod-web-01 "
                "at 192.168.1.100 changed in the last 7 days by user admin@example.com")
                
        entities = extractor.extract_entities(query, context)
        
        # Check various entity types were extracted
        entity_types = set(e.type for e in entities)
        assert EntityType.ORGANIZATION in entity_types
        assert EntityType.SYSTEM in entity_types
        assert EntityType.IP_ADDRESS in entity_types
        assert EntityType.TIME_RANGE in entity_types
        assert EntityType.EMAIL in entity_types
        
    def test_entity_position_tracking(self, extractor):
        """Test that entity positions are correctly tracked."""
        query = "Server web-01 at location DC-East"
        entities = extractor.extract_entities(query)
        
        # Entities should be sorted by position
        for i in range(len(entities) - 1):
            assert entities[i].start_pos <= entities[i+1].start_pos
            
    def test_normalization(self, extractor):
        """Test entity normalization."""
        # Test hostname normalization
        query = "Connect to SERVER.EXAMPLE.COM"
        entities = extractor.extract_entities(query)
        hostname = next((e for e in entities if e.type == EntityType.HOSTNAME), None)
        if hostname:
            assert hostname.normalized == "server.example.com"
            
        # Test OS normalization
        query = "Update windows servers"
        entities = extractor.extract_entities(query)
        os = next((e for e in entities if e.type == EntityType.OS), None)
        if os:
            assert "Windows" in os.normalized