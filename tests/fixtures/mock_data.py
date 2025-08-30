"""Mock data for testing."""

from datetime import datetime
from typing import Dict, Any, List


def get_mock_organizations() -> List[Dict[str, Any]]:
    """Get mock organization data."""
    return [
        {
            "id": "org-1",
            "type": "organizations",
            "attributes": {
                "name": "Happy Frog Inc",
                "organization_type_name": "Customer",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T00:00:00Z"
            },
            "relationships": {}
        },
        {
            "id": "org-2",
            "type": "organizations",
            "attributes": {
                "name": "Acme Corp",
                "organization_type_name": "Customer",
                "created_at": "2024-01-02T00:00:00Z",
                "updated_at": "2024-01-16T00:00:00Z"
            },
            "relationships": {}
        },
        {
            "id": "org-3",
            "type": "organizations",
            "attributes": {
                "name": "Internal IT",
                "organization_type_name": "Internal",
                "created_at": "2024-01-03T00:00:00Z",
                "updated_at": "2024-01-17T00:00:00Z"
            },
            "relationships": {}
        }
    ]


def get_mock_configurations() -> List[Dict[str, Any]]:
    """Get mock configuration data."""
    return [
        {
            "id": "config-1",
            "type": "configurations",
            "attributes": {
                "name": "Main Router",
                "hostname": "router.happyfrog.local",
                "primary_ip": "192.168.1.1",
                "mac_address": "00:11:22:33:44:55",
                "configuration_type_name": "Router",
                "configuration_status_name": "Active",
                "operating_system": "RouterOS",
                "notes": "Main office router",
                "created_at": "2024-01-10T00:00:00Z",
                "updated_at": "2024-01-20T00:00:00Z"
            },
            "relationships": {
                "organization": {
                    "data": {"id": "org-1", "type": "organizations"}
                }
            }
        },
        {
            "id": "config-2",
            "type": "configurations",
            "attributes": {
                "name": "Web Server 01",
                "hostname": "web01.acme.com",
                "primary_ip": "10.0.1.10",
                "mac_address": "00:AA:BB:CC:DD:EE",
                "configuration_type_name": "Server",
                "configuration_status_name": "Active",
                "operating_system": "Ubuntu 22.04",
                "notes": "Production web server",
                "created_at": "2024-01-11T00:00:00Z",
                "updated_at": "2024-01-21T00:00:00Z"
            },
            "relationships": {
                "organization": {
                    "data": {"id": "org-2", "type": "organizations"}
                }
            }
        },
        {
            "id": "config-3",
            "type": "configurations",
            "attributes": {
                "name": "Office Printer",
                "hostname": "printer.happyfrog.local",
                "primary_ip": "192.168.1.100",
                "mac_address": "00:99:88:77:66:55",
                "configuration_type_name": "Printer",
                "configuration_status_name": "Active",
                "model": "HP LaserJet Pro",
                "notes": "2nd floor printer",
                "created_at": "2024-01-12T00:00:00Z",
                "updated_at": "2024-01-22T00:00:00Z"
            },
            "relationships": {
                "organization": {
                    "data": {"id": "org-1", "type": "organizations"}
                }
            }
        }
    ]


def get_mock_passwords() -> List[Dict[str, Any]]:
    """Get mock password data."""
    return [
        {
            "id": "pass-1",
            "type": "passwords",
            "attributes": {
                "name": "Router Admin",
                "username": "admin",
                "password": "[ENCRYPTED]",
                "url": "https://192.168.1.1",
                "notes": "Main router admin access",
                "created_at": "2024-01-05T00:00:00Z",
                "updated_at": "2024-01-25T00:00:00Z"
            },
            "relationships": {
                "organization": {
                    "data": {"id": "org-1", "type": "organizations"}
                }
            }
        },
        {
            "id": "pass-2",
            "type": "passwords",
            "attributes": {
                "name": "Web Server SSH",
                "username": "sysadmin",
                "password": "[ENCRYPTED]",
                "url": "ssh://10.0.1.10",
                "notes": "SSH access to web server",
                "created_at": "2024-01-06T00:00:00Z",
                "updated_at": "2024-01-26T00:00:00Z"
            },
            "relationships": {
                "organization": {
                    "data": {"id": "org-2", "type": "organizations"}
                }
            }
        }
    ]


def get_mock_documents() -> List[Dict[str, Any]]:
    """Get mock document data."""
    return [
        {
            "id": "doc-1",
            "type": "documents",
            "attributes": {
                "name": "Network Diagram",
                "description": "Complete network topology diagram",
                "content": "Network diagram showing all connections...",
                "created_at": "2024-01-08T00:00:00Z",
                "updated_at": "2024-01-28T00:00:00Z"
            },
            "relationships": {
                "organization": {
                    "data": {"id": "org-1", "type": "organizations"}
                }
            }
        },
        {
            "id": "doc-2",
            "type": "documents",
            "attributes": {
                "name": "Disaster Recovery Plan",
                "description": "DR procedures and contacts",
                "content": "In case of disaster, follow these steps...",
                "created_at": "2024-01-09T00:00:00Z",
                "updated_at": "2024-01-29T00:00:00Z"
            },
            "relationships": {
                "organization": {
                    "data": {"id": "org-2", "type": "organizations"}
                }
            }
        }
    ]


def get_mock_contacts() -> List[Dict[str, Any]]:
    """Get mock contact data."""
    return [
        {
            "id": "contact-1",
            "type": "contacts",
            "attributes": {
                "first_name": "John",
                "last_name": "Doe",
                "title": "IT Manager",
                "email": "john.doe@happyfrog.com",
                "phone": "+1-555-0100",
                "created_at": "2024-01-04T00:00:00Z",
                "updated_at": "2024-01-24T00:00:00Z"
            },
            "relationships": {
                "organization": {
                    "data": {"id": "org-1", "type": "organizations"}
                }
            }
        },
        {
            "id": "contact-2",
            "type": "contacts",
            "attributes": {
                "first_name": "Jane",
                "last_name": "Smith",
                "title": "System Administrator",
                "email": "jane.smith@acme.com",
                "phone": "+1-555-0200",
                "created_at": "2024-01-05T00:00:00Z",
                "updated_at": "2024-01-25T00:00:00Z"
            },
            "relationships": {
                "organization": {
                    "data": {"id": "org-2", "type": "organizations"}
                }
            }
        }
    ]


def get_mock_locations() -> List[Dict[str, Any]]:
    """Get mock location data."""
    return [
        {
            "id": "loc-1",
            "type": "locations",
            "attributes": {
                "name": "Main Office",
                "address": "123 Main St",
                "city": "San Francisco",
                "state": "CA",
                "zip": "94105",
                "country": "USA",
                "created_at": "2024-01-03T00:00:00Z",
                "updated_at": "2024-01-23T00:00:00Z"
            },
            "relationships": {
                "organization": {
                    "data": {"id": "org-1", "type": "organizations"}
                }
            }
        },
        {
            "id": "loc-2",
            "type": "locations",
            "attributes": {
                "name": "Data Center",
                "address": "456 Tech Blvd",
                "city": "San Jose",
                "state": "CA",
                "zip": "95110",
                "country": "USA",
                "created_at": "2024-01-04T00:00:00Z",
                "updated_at": "2024-01-24T00:00:00Z"
            },
            "relationships": {
                "organization": {
                    "data": {"id": "org-2", "type": "organizations"}
                }
            }
        }
    ]


def get_mock_flexible_assets() -> List[Dict[str, Any]]:
    """Get mock flexible asset data."""
    return [
        {
            "id": "asset-1",
            "type": "flexible_assets",
            "attributes": {
                "name": "SSL Certificate - happyfrog.com",
                "flexible_asset_type_name": "SSL Certificate",
                "traits": {
                    "domain": "happyfrog.com",
                    "issuer": "Let's Encrypt",
                    "expiry_date": "2024-12-31",
                    "key_size": "2048"
                },
                "created_at": "2024-01-07T00:00:00Z",
                "updated_at": "2024-01-27T00:00:00Z"
            },
            "relationships": {
                "organization": {
                    "data": {"id": "org-1", "type": "organizations"}
                }
            }
        },
        {
            "id": "asset-2",
            "type": "flexible_assets",
            "attributes": {
                "name": "Software License - Microsoft Office",
                "flexible_asset_type_name": "Software License",
                "traits": {
                    "product": "Microsoft Office 365",
                    "license_key": "[ENCRYPTED]",
                    "seats": "50",
                    "expiry_date": "2024-06-30"
                },
                "created_at": "2024-01-08T00:00:00Z",
                "updated_at": "2024-01-28T00:00:00Z"
            },
            "relationships": {
                "organization": {
                    "data": {"id": "org-2", "type": "organizations"}
                }
            }
        }
    ]


def get_all_mock_data() -> Dict[str, List[Dict[str, Any]]]:
    """Get all mock data."""
    return {
        "organizations": get_mock_organizations(),
        "configurations": get_mock_configurations(),
        "passwords": get_mock_passwords(),
        "documents": get_mock_documents(),
        "contacts": get_mock_contacts(),
        "locations": get_mock_locations(),
        "flexible_assets": get_mock_flexible_assets()
    }


def get_mock_embeddings(dimension: int = 384) -> List[float]:
    """Get mock embedding vector."""
    import random
    random.seed(42)
    return [random.random() for _ in range(dimension)]


def get_mock_search_results() -> List[Dict[str, Any]]:
    """Get mock search results."""
    return [
        {
            "id": "result-1",
            "entity_id": "config-1",
            "score": 0.92,
            "payload": {
                "name": "Main Router",
                "type": "configuration",
                "organization_id": "org-1"
            }
        },
        {
            "id": "result-2",
            "entity_id": "config-3",
            "score": 0.85,
            "payload": {
                "name": "Office Printer",
                "type": "configuration",
                "organization_id": "org-1"
            }
        },
        {
            "id": "result-3",
            "entity_id": "doc-1",
            "score": 0.78,
            "payload": {
                "name": "Network Diagram",
                "type": "document",
                "organization_id": "org-1"
            }
        }
    ]