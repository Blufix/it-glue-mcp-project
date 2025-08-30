"""
IT Glue API Code Examples for MCP Server Implementation
Based on extensive research from IT Glue API documentation
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

class ITGlueAPIClient:
    """
    IT Glue API Client with comprehensive examples for all major endpoints
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.itglue.com"):
        """
        Initialize IT Glue API client
        
        Args:
            api_key: Your IT Glue API key (format: ITG.xxxxxxxxxxxxxxxxxxxxxxxxx)
            base_url: Base URL for IT Glue API (default: https://api.itglue.com)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json"
        }
        
    # ==================== AUTHENTICATION ====================
    
    def test_connection(self) -> bool:
        """
        Test API connection and authentication
        Returns True if successful, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/organizations",
                headers=self.headers,
                params={"page[size]": 1}
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    # ==================== ORGANIZATIONS ====================
    
    def get_organizations(self, page_size: int = 50, page_number: int = 1) -> Dict:
        """
        GET /organizations
        List all organizations in your account
        
        Example response:
        {
            "data": [
                {
                    "id": "2",
                    "type": "organizations",
                    "attributes": {
                        "name": "Happy Frog",
                        "organization-type-id": 1,
                        "organization-type-name": "Customer",
                        "organization-status-id": 1,
                        "organization-status-name": "Active"
                    }
                }
            ]
        }
        """
        params = {
            "page[size]": page_size,
            "page[number]": page_number
        }
        
        response = requests.get(
            f"{self.base_url}/organizations",
            headers=self.headers,
            params=params
        )
        return response.json()
    
    def get_organization(self, org_id: int) -> Dict:
        """
        GET /organizations/:id
        Retrieve a specific organization
        """
        response = requests.get(
            f"{self.base_url}/organizations/{org_id}",
            headers=self.headers
        )
        return response.json()
    
    # ==================== FLEXIBLE ASSETS ====================
    
    def get_flexible_assets(
        self,
        org_id: int,
        flexible_asset_type_id: int,
        include_attachments: bool = False,
        page_size: int = 50
    ) -> Dict:
        """
        GET /flexible_assets
        List flexible assets for an organization
        
        Example response for Email flexible asset:
        {
            "data": [
                {
                    "id": "401",
                    "type": "flexible-assets",
                    "attributes": {
                        "organization-id": 2,
                        "organization-name": "Happy Frog",
                        "flexible-asset-type-id": 33,
                        "flexible-asset-type-name": "Email",
                        "name": "Exchange 2013",
                        "traits": {
                            "type": "Exchange 2013",
                            "domains": {
                                "type": "Domains",
                                "values": [
                                    {
                                        "id": 347287,
                                        "name": "happyfrog.itglue.com",
                                        "organization-name": "Happy Frog"
                                    }
                                ]
                            },
                            "email-servers": {
                                "type": "Configurations",
                                "values": [
                                    {
                                        "id": 11303436,
                                        "name": "HF-SF-EXCH01 (Exchange)",
                                        "hostname": "HF-SF-EXCH01",
                                        "configuration-type-name": "Managed Server"
                                    }
                                ]
                            },
                            "location": "On-Premises",
                            "inbound-delivery": "Office 365",
                            "webmail-url": "https://email.example.com"
                        }
                    }
                }
            ]
        }
        """
        params = {
            "filter[organization_id]": org_id,
            "filter[flexible_asset_type_id]": flexible_asset_type_id,
            "page[size]": page_size
        }
        
        if include_attachments:
            params["include"] = "attachments"
        
        response = requests.get(
            f"{self.base_url}/flexible_assets",
            headers=self.headers,
            params=params
        )
        return response.json()
    
    def create_flexible_asset(
        self,
        org_id: int,
        flexible_asset_type_id: int,
        traits: Dict
    ) -> Dict:
        """
        POST /flexible_assets
        Create a new flexible asset
        
        Example payload for creating an Email asset:
        {
            "data": {
                "type": "flexible_assets",
                "attributes": {
                    "organization-id": 2,
                    "flexible-asset-type-id": 33,
                    "traits": {
                        "type": "Exchange 2016",
                        "domains": [569],
                        "email-servers": [457, 676],
                        "location": "On-Premises",
                        "inbound-delivery": "Office 365",
                        "webmail-url": "https://email.example.com"
                    }
                }
            }
        }
        """
        payload = {
            "data": {
                "type": "flexible_assets",
                "attributes": {
                    "organization-id": org_id,
                    "flexible-asset-type-id": flexible_asset_type_id,
                    "traits": traits
                }
            }
        }
        
        response = requests.post(
            f"{self.base_url}/flexible_assets",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def update_flexible_asset(self, asset_id: int, traits: Dict) -> Dict:
        """
        PATCH /flexible_assets/:id
        Update an existing flexible asset
        
        Example payload:
        {
            "data": {
                "type": "flexible-assets",
                "attributes": {
                    "archived": true,
                    "traits": {
                        "type": "Exchange 2016",
                        "webmail-url": "https://email.newdomain.com"
                    }
                }
            }
        }
        """
        payload = {
            "data": {
                "type": "flexible-assets",
                "attributes": {
                    "traits": traits
                }
            }
        }
        
        response = requests.patch(
            f"{self.base_url}/flexible_assets/{asset_id}",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    # ==================== PASSWORDS ====================
    
    def get_passwords(
        self,
        org_id: Optional[int] = None,
        include_passwords: bool = False,
        page_size: int = 50
    ) -> Dict:
        """
        GET /passwords
        List passwords (optionally for specific organization)
        
        Example response:
        {
            "data": [
                {
                    "id": "54",
                    "type": "passwords",
                    "attributes": {
                        "organization-id": 2,
                        "organization-name": "Happy Frog",
                        "name": "Office 365 Admin",
                        "username": "tech@happyfrog.itglue.com",
                        "url": "https://login.itglue.com/",
                        "notes": "Admin account for all Office 365 users",
                        "password": "p4ssw0rd",  # Only if show_passwords is enabled
                        "password-category-id": 15,
                        "password-category-name": "Cloud"
                    }
                }
            ]
        }
        """
        params = {
            "page[size]": page_size
        }
        
        if org_id:
            params["filter[organization_id]"] = org_id
            
        if include_passwords:
            params["show_passwords"] = "true"
        
        response = requests.get(
            f"{self.base_url}/passwords",
            headers=self.headers,
            params=params
        )
        return response.json()
    
    def get_password(self, password_id: int, show_password: bool = False) -> Dict:
        """
        GET /passwords/:id
        Retrieve a specific password
        """
        params = {}
        if show_password:
            params["show_passwords"] = "true"
            
        response = requests.get(
            f"{self.base_url}/passwords/{password_id}",
            headers=self.headers,
            params=params
        )
        return response.json()
    
    # ==================== CONFIGURATIONS ====================
    
    def get_configurations(
        self,
        org_id: int,
        configuration_type_id: Optional[int] = None,
        page_size: int = 50
    ) -> Dict:
        """
        GET /configurations
        List configurations for an organization
        
        Configuration types typically include:
        - Managed Server
        - Managed Workstation
        - Network Device
        - Printer
        - Firewall
        """
        params = {
            "filter[organization_id]": org_id,
            "page[size]": page_size
        }
        
        if configuration_type_id:
            params["filter[configuration_type_id]"] = configuration_type_id
        
        response = requests.get(
            f"{self.base_url}/configurations",
            headers=self.headers,
            params=params
        )
        return response.json()
    
    # ==================== DOCUMENTS ====================
    
    def get_documents(
        self,
        org_id: int,
        page_size: int = 50
    ) -> Dict:
        """
        GET /documents
        List documents for an organization
        """
        params = {
            "filter[organization_id]": org_id,
            "page[size]": page_size
        }
        
        response = requests.get(
            f"{self.base_url}/documents",
            headers=self.headers,
            params=params
        )
        return response.json()
    
    # ==================== FLEXIBLE ASSET TYPES ====================
    
    def get_flexible_asset_types(self) -> Dict:
        """
        GET /flexible_asset_types
        List all flexible asset types in your account
        
        Common types include:
        - Email (id: 33)
        - Wireless
        - Applications
        - Domains
        """
        response = requests.get(
            f"{self.base_url}/flexible_asset_types",
            headers=self.headers
        )
        return response.json()
    
    def create_flexible_asset_type(self, name: str, description: str, fields: List[Dict]) -> Dict:
        """
        POST /flexible_asset_types
        Create a new flexible asset type with fields
        
        Example for Email asset type:
        {
            "data": {
                "type": "flexible_asset_types",
                "attributes": {
                    "name": "Email",
                    "description": "Email Platform Information",
                    "icon": "envelope",
                    "show-in-menu": true
                },
                "relationships": {
                    "flexible-asset-fields": {
                        "data": [
                            {
                                "type": "flexible_asset_fields",
                                "attributes": {
                                    "order": 1,
                                    "name": "Domains",
                                    "kind": "Tag",
                                    "tag-type": "Domains",
                                    "required": true
                                }
                            }
                        ]
                    }
                }
            }
        }
        """
        payload = {
            "data": {
                "type": "flexible_asset_types",
                "attributes": {
                    "name": name,
                    "description": description,
                    "show-in-menu": True
                },
                "relationships": {
                    "flexible-asset-fields": {
                        "data": fields
                    }
                }
            }
        }
        
        response = requests.post(
            f"{self.base_url}/flexible_asset_types",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    # ==================== PAGINATION HELPERS ====================
    
    def paginate_results(self, endpoint: str, params: Dict, max_pages: int = None) -> List[Dict]:
        """
        Helper to paginate through all results
        
        Args:
            endpoint: API endpoint (e.g., "/organizations")
            params: Query parameters
            max_pages: Maximum number of pages to fetch (None for all)
        
        Returns:
            List of all data items across pages
        """
        all_data = []
        page = 1
        
        while True:
            params["page[number]"] = page
            
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                params=params
            )
            
            if response.status_code != 200:
                break
                
            data = response.json()
            
            if "data" in data and data["data"]:
                all_data.extend(data["data"])
            else:
                break
            
            # Check if there are more pages
            if "meta" in data and "next-page" in data["meta"]:
                if data["meta"]["next-page"] is None:
                    break
            
            if max_pages and page >= max_pages:
                break
                
            page += 1
            time.sleep(0.5)  # Rate limiting
        
        return all_data
    
    # ==================== SEARCH HELPERS ====================
    
    def search_configurations_by_name(self, org_id: int, search_term: str) -> List[Dict]:
        """
        Search configurations by name (e.g., find all printers)
        """
        configs = self.get_configurations(org_id, page_size=100)
        
        results = []
        for config in configs.get("data", []):
            name = config["attributes"].get("name", "").lower()
            if search_term.lower() in name:
                results.append(config)
        
        return results
    
    def get_company_assets_summary(self, org_id: int) -> Dict:
        """
        Get a summary of all assets for a company
        Useful for answering questions like "What does Company A use for antivirus?"
        """
        summary = {
            "organization_id": org_id,
            "configurations": [],
            "flexible_assets": [],
            "passwords_count": 0,
            "documents_count": 0
        }
        
        # Get configurations
        configs = self.get_configurations(org_id)
        summary["configurations"] = [
            {
                "name": c["attributes"]["name"],
                "type": c["attributes"].get("configuration-type-name", "Unknown"),
                "id": c["id"]
            }
            for c in configs.get("data", [])
        ]
        
        # Get passwords count
        passwords = self.get_passwords(org_id, include_passwords=False, page_size=1)
        if "meta" in passwords:
            summary["passwords_count"] = passwords["meta"].get("total-count", 0)
        
        return summary


# ==================== USAGE EXAMPLES ====================

def example_usage():
    """
    Comprehensive examples of using the IT Glue API client
    """
    
    # Initialize client
    client = ITGlueAPIClient(api_key="ITG.xxxxxxxxxxxxxxxxxxxxxxxxx")
    
    # Test connection
    if not client.test_connection():
        print("Failed to connect to IT Glue API")
        return
    
    # 1. Get all organizations
    orgs = client.get_organizations()
    print(f"Found {len(orgs['data'])} organizations")
    
    # 2. Get specific organization details
    org_id = 2  # Happy Frog
    org = client.get_organization(org_id)
    print(f"Organization: {org['data']['attributes']['name']}")
    
    # 3. Search for printers in an organization
    printers = client.search_configurations_by_name(org_id, "printer")
    for printer in printers:
        print(f"Printer: {printer['attributes']['name']}")
        print(f"  IP: {printer['attributes'].get('primary-ip', 'N/A')}")
    
    # 4. Get passwords for organization (without actual passwords)
    passwords = client.get_passwords(org_id, include_passwords=False)
    for pwd in passwords['data'][:5]:  # First 5
        print(f"Password: {pwd['attributes']['name']}")
        print(f"  URL: {pwd['attributes'].get('url', 'N/A')}")
        print(f"  Username: {pwd['attributes'].get('username', 'N/A')}")
    
    # 5. Get flexible assets (e.g., Email configurations)
    email_type_id = 33  # Standard Email flexible asset type
    emails = client.get_flexible_assets(org_id, email_type_id)
    for email in emails['data']:
        print(f"Email System: {email['attributes']['name']}")
        traits = email['attributes']['traits']
        print(f"  Type: {traits.get('type', 'Unknown')}")
        print(f"  Webmail URL: {traits.get('webmail-url', 'N/A')}")
    
    # 6. Get company summary (useful for answering general questions)
    summary = client.get_company_assets_summary(org_id)
    print(f"Company has {len(summary['configurations'])} configurations")
    print(f"Company has {summary['passwords_count']} passwords stored")
    
    # 7. Paginate through all results
    all_orgs = client.paginate_results("/organizations", {"page[size]": 50})
    print(f"Total organizations across all pages: {len(all_orgs)}")


# ==================== RATE LIMITING ====================

class RateLimitedITGlueClient(ITGlueAPIClient):
    """
    Extended client with rate limiting and retry logic
    """
    
    def __init__(self, api_key: str, max_retries: int = 3, retry_delay: float = 1.0):
        super().__init__(api_key)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make HTTP request with retry logic for rate limiting (429 errors)
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.request(method, url, **kwargs)
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay))
                    print(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
        
        return response


# ==================== NATURAL LANGUAGE QUERY HELPERS ====================

class ITGlueQueryEngine:
    """
    Helper class to answer natural language queries about IT Glue data
    Perfect for MCP server implementation
    """
    
    def __init__(self, client: ITGlueAPIClient):
        self.client = client
    
    def answer_query(self, company_name: str, query: str) -> Dict[str, Any]:
        """
        Answer natural language queries like:
        - "What's the router IP for Company A?"
        - "Does Company B use Sophos?"
        - "What are the printer URLs for Company C?"
        
        Returns:
            Dict with 'success', 'answer', and 'data' keys
        """
        # First, find the organization
        orgs = self.client.get_organizations()
        org_id = None
        
        for org in orgs['data']:
            if company_name.lower() in org['attributes']['name'].lower():
                org_id = org['id']
                break
        
        if not org_id:
            return {
                "success": False,
                "answer": f"No data available for company '{company_name}'",
                "data": None
            }
        
        # Parse query for keywords
        query_lower = query.lower()
        
        # Router/Network queries
        if any(word in query_lower for word in ['router', 'gateway', 'firewall']):
            configs = self.client.get_configurations(org_id)
            routers = []
            
            for config in configs['data']:
                config_type = config['attributes'].get('configuration-type-name', '').lower()
                if any(t in config_type for t in ['router', 'gateway', 'firewall', 'network']):
                    routers.append({
                        "name": config['attributes']['name'],
                        "ip": config['attributes'].get('primary-ip', 'No IP documented'),
                        "type": config['attributes'].get('configuration-type-name')
                    })
            
            if routers:
                return {
                    "success": True,
                    "answer": f"Found {len(routers)} network device(s)",
                    "data": routers
                }
        
        # Printer queries
        if 'printer' in query_lower:
            printers = self.client.search_configurations_by_name(org_id, 'printer')
            
            if printers:
                printer_info = []
                for printer in printers:
                    info = {
                        "name": printer['attributes']['name'],
                        "ip": printer['attributes'].get('primary-ip', 'No IP documented')
                    }
                    
                    # Check for URL in notes or other fields
                    if 'url' in query_lower:
                        notes = printer['attributes'].get('notes', '')
                        if 'http' in notes.lower():
                            info['url'] = notes
                        else:
                            info['url'] = f"http://{info['ip']}" if info['ip'] != 'No IP documented' else 'No URL documented'
                    
                    printer_info.append(info)
                
                return {
                    "success": True,
                    "answer": f"Found {len(printer_info)} printer(s)",
                    "data": printer_info
                }
        
        # Antivirus/Software queries
        if any(word in query_lower for word in ['antivirus', 'sophos', 'defender', 'av']):
            # Check flexible assets for AV information
            summary = self.client.get_company_assets_summary(org_id)
            
            # This would need to check various flexible asset types
            # For now, return a structured "no data" response
            return {
                "success": False,
                "answer": "No antivirus information documented",
                "data": None
            }
        
        # Default response
        return {
            "success": False,
            "answer": "No data available for that query",
            "data": None
        }


if __name__ == "__main__":
    # Run examples
    example_usage()