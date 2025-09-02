"""Test data for IT Glue MCP Server tests."""

from datetime import datetime, timedelta
from typing import List, Dict, Any


def get_sample_organizations() -> List[Dict[str, Any]]:
    """Get sample organization data."""
    return [
        {
            "id": "1",
            "name": "Microsoft Corporation",
            "organization_type": "Customer",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "primary_location": "Redmond, WA",
            "short_name": "MSFT",
            "description": "Technology company"
        },
        {
            "id": "2",
            "name": "Google LLC",
            "organization_type": "Customer",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "primary_location": "Mountain View, CA",
            "short_name": "GOOGL",
            "description": "Search and technology company"
        },
        {
            "id": "3",
            "name": "Amazon Web Services",
            "organization_type": "Vendor",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "primary_location": "Seattle, WA",
            "short_name": "AWS",
            "description": "Cloud services provider"
        },
        {
            "id": "4",
            "name": "International Business Machines",
            "organization_type": "Customer",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "primary_location": "Armonk, NY",
            "short_name": "IBM",
            "description": "Technology and consulting company"
        },
        {
            "id": "5",
            "name": "Faucets Inc",
            "organization_type": "Customer",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "primary_location": "San Francisco, CA",
            "short_name": "FAUCETS",
            "description": "Plumbing supply company"
        }
    ]


def get_sample_configurations() -> List[Dict[str, Any]]:
    """Get sample configuration data."""
    return [
        {
            "id": "101",
            "name": "MSFT-DC01",
            "organization_id": "1",
            "configuration_type": "Server",
            "primary_ip": "10.0.1.10",
            "operating_system": "Windows Server 2022",
            "hostname": "dc01.microsoft.local",
            "serial_number": "SRV-2022-001",
            "installed_ram": 32,
            "cpu_count": 8
        },
        {
            "id": "102",
            "name": "MSFT-FW01",
            "organization_id": "1",
            "configuration_type": "Firewall",
            "primary_ip": "10.0.0.1",
            "manufacturer": "Sophos",
            "model": "XG 430",
            "serial_number": "FW-2022-001"
        },
        {
            "id": "103",
            "name": "GOOGL-WEB01",
            "organization_id": "2",
            "configuration_type": "Server",
            "primary_ip": "172.16.1.20",
            "operating_system": "Ubuntu 22.04 LTS",
            "hostname": "web01.google.local",
            "serial_number": "SRV-2022-002",
            "installed_ram": 64,
            "cpu_count": 16
        }
    ]


def get_sample_documents() -> List[Dict[str, Any]]:
    """Get sample document data."""
    return [
        {
            "id": "201",
            "name": "Network Troubleshooting Guide",
            "organization_id": "1",
            "document_type": "Runbook",
            "content": "Step 1: Check physical connections\nStep 2: Verify IP configuration\nStep 3: Test connectivity",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        },
        {
            "id": "202",
            "name": "Backup Procedures",
            "organization_id": "1",
            "document_type": "Procedure",
            "content": "Daily backup runs at 2 AM. Weekly full backup on Sundays. Monthly offsite storage.",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        },
        {
            "id": "203",
            "name": "Server Deployment Checklist",
            "organization_id": "2",
            "document_type": "Checklist",
            "content": "1. Install OS\n2. Configure network\n3. Join domain\n4. Install updates\n5. Configure monitoring",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]


def get_sample_flexible_assets() -> List[Dict[str, Any]]:
    """Get sample flexible asset data."""
    return [
        {
            "id": "301",
            "organization_id": "1",
            "flexible_asset_type_id": "401",
            "flexible_asset_type_name": "SSL Certificate",
            "traits": {
                "name": "*.microsoft.com",
                "issuer": "DigiCert",
                "expiry_date": (datetime.now() + timedelta(days=365)).isoformat(),
                "key_size": "2048",
                "algorithm": "RSA"
            }
        },
        {
            "id": "302",
            "organization_id": "1",
            "flexible_asset_type_id": "402",
            "flexible_asset_type_name": "Warranty",
            "traits": {
                "device_name": "MSFT-DC01",
                "vendor": "Dell",
                "expiry_date": (datetime.now() + timedelta(days=730)).isoformat(),
                "contract_number": "CNT-2022-001",
                "support_level": "ProSupport Plus"
            }
        },
        {
            "id": "303",
            "organization_id": "2",
            "flexible_asset_type_id": "403",
            "flexible_asset_type_name": "Software License",
            "traits": {
                "software_name": "VMware vSphere",
                "license_count": "100",
                "license_type": "Enterprise Plus",
                "expiry_date": (datetime.now() + timedelta(days=365)).isoformat()
            }
        }
    ]


def get_sample_locations() -> List[Dict[str, Any]]:
    """Get sample location data."""
    return [
        {
            "id": "501",
            "name": "Microsoft HQ",
            "organization_id": "1",
            "address": "1 Microsoft Way",
            "city": "Redmond",
            "state": "WA",
            "zip": "98052",
            "country": "USA",
            "phone": "425-882-8080",
            "primary": True
        },
        {
            "id": "502",
            "name": "Microsoft NYC Office",
            "organization_id": "1",
            "address": "11 Times Square",
            "city": "New York",
            "state": "NY",
            "zip": "10036",
            "country": "USA",
            "phone": "212-245-2100",
            "primary": False
        },
        {
            "id": "503",
            "name": "Google Mountain View",
            "organization_id": "2",
            "address": "1600 Amphitheatre Parkway",
            "city": "Mountain View",
            "state": "CA",
            "zip": "94043",
            "country": "USA",
            "phone": "650-253-0000",
            "primary": True
        }
    ]


def get_sample_asset_types() -> List[Dict[str, Any]]:
    """Get sample asset type data."""
    return [
        {
            "id": "401",
            "name": "SSL Certificate",
            "description": "SSL/TLS certificates for secure communication",
            "fields": [
                {"name": "name", "type": "text", "required": True},
                {"name": "issuer", "type": "text", "required": True},
                {"name": "expiry_date", "type": "date", "required": True},
                {"name": "key_size", "type": "number", "required": False},
                {"name": "algorithm", "type": "text", "required": False}
            ]
        },
        {
            "id": "402",
            "name": "Warranty",
            "description": "Hardware warranty information",
            "fields": [
                {"name": "device_name", "type": "text", "required": True},
                {"name": "vendor", "type": "text", "required": True},
                {"name": "expiry_date", "type": "date", "required": True},
                {"name": "contract_number", "type": "text", "required": False},
                {"name": "support_level", "type": "text", "required": False}
            ]
        },
        {
            "id": "403",
            "name": "Software License",
            "description": "Software licensing information",
            "fields": [
                {"name": "software_name", "type": "text", "required": True},
                {"name": "license_count", "type": "number", "required": True},
                {"name": "license_type", "type": "text", "required": False},
                {"name": "expiry_date", "type": "date", "required": False}
            ]
        }
    ]


def get_sample_contacts() -> List[Dict[str, Any]]:
    """Get sample contact data."""
    return [
        {
            "id": "601",
            "first_name": "John",
            "last_name": "Smith",
            "organization_id": "1",
            "title": "IT Manager",
            "email": "john.smith@microsoft.com",
            "phone": "425-882-8080 x1234",
            "location_id": "501"
        },
        {
            "id": "602",
            "first_name": "Jane",
            "last_name": "Doe",
            "organization_id": "2",
            "title": "Network Administrator",
            "email": "jane.doe@google.com",
            "phone": "650-253-0000 x5678",
            "location_id": "503"
        }
    ]


def get_sample_passwords() -> List[Dict[str, Any]]:
    """Get sample password data (metadata only, no actual passwords)."""
    return [
        {
            "id": "701",
            "name": "Domain Admin",
            "organization_id": "1",
            "resource_type": "Server",
            "resource_id": "101",
            "username": "administrator",
            "password_updated_at": datetime.now().isoformat(),
            "notes": "Main domain administrator account"
        },
        {
            "id": "702",
            "name": "Firewall Admin",
            "organization_id": "1",
            "resource_type": "Firewall",
            "resource_id": "102",
            "username": "admin",
            "password_updated_at": (datetime.now() - timedelta(days=45)).isoformat(),
            "notes": "Sophos firewall admin account"
        }
    ]