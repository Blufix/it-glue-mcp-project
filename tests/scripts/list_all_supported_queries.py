#!/usr/bin/env python3
"""List all available IT Glue queries supported by the MCP server."""

print("=" * 80)
print("IT GLUE MCP SERVER - SUPPORTED QUERIES")
print("=" * 80)

print("""
## 📋 ORGANIZATIONS
- Get all organizations
- Get organization by ID
- Filter organizations by name
- Get organization relationships

## 🖥️ CONFIGURATIONS (Hardware/Network Devices)
- Get all configurations
- Get configurations by organization
- Filter by configuration type (Server, Workstation, Firewall, Switch, etc.)
- Filter by status (Active, Inactive, Disposed)
- Filter by manufacturer
- Filter by model
- Search by serial number
- Search by hostname
- Search by IP address

## 🔐 PASSWORDS
- Get all passwords (metadata only)
- Get passwords by organization
- Filter by resource type
- Filter by username
- Search by name/description
- Get password categories
- Check password expiration dates
- Note: Actual passwords are never displayed for security

## 📄 DOCUMENTS
- Get all documents
- Get documents by organization
- Filter by document type
- Search by document name
- Get document content (if available)
- Filter by created/updated date

## 👥 CONTACTS
- Get all contacts
- Get contacts by organization
- Search by name (first/last)
- Filter by title
- Get contact emails
- Get contact phones
- Filter by location
- Get primary contacts

## 📍 LOCATIONS
- Get all locations
- Get locations by organization
- Filter by location name
- Get primary location
- Get location addresses
- Get location contacts

## 🔧 FLEXIBLE ASSETS (Custom Data)
- Get flexible assets by type
- Get flexible assets by organization
- Filter by asset attributes
- Search custom fields
- Get relationships between assets

## 🔍 AVAILABLE SEARCH PATTERNS

### Configuration Searches:
- "@org firewall" → All firewalls for organization
- "@org switch details" → All switches with details
- "@org server list" → All servers
- "@org workstation" → All workstations
- "@org nas device" → NAS devices
- "@org ups" → UPS devices
- "@org printer" → Printers
- "@org IP:10.40.0.251" → Device by IP address
- "@org serial:XYZ123" → Device by serial number

### Password Searches:
- "@org admin password" → Admin credentials
- "@org domain admin" → Domain admin accounts
- "@org local admin" → Local admin accounts
- "@org wifi password" → WiFi credentials
- "@org vpn credentials" → VPN access
- "@org service account" → Service accounts
- "@org application password" → App passwords

### Contact Searches:
- "@org main contact" → Primary contacts
- "@org who is" → All contacts
- "@org contact info" → Contact details
- "@org IT contact" → IT personnel
- "@org manager contact" → Managers
- "@org [name]" → Specific person

### Document Searches:
- "@org network diagram" → Network documentation
- "@org runbook" → Runbooks
- "@org SOP" → Standard operating procedures
- "@org backup procedure" → Backup docs
- "@org disaster recovery" → DR plans
- "@org license" → License documentation

### Location Searches:
- "@org main office" → Primary location
- "@org branch office" → Branch locations
- "@org data center" → DC locations
- "@org location address" → Physical addresses

## 🎯 ADVANCED QUERY FEATURES

### Filtering Options:
- By date range (created/updated)
- By status (Active/Inactive)
- By type/category
- By relationships
- By custom attributes

### Output Details Available:
- IP addresses & network info
- Serial numbers & asset tags
- Manufacturer & model details
- Install dates & warranty info
- Last update timestamps
- Location information
- Related configurations
- Contact associations
- Document links

## 🔗 RELATIONSHIP QUERIES
- Configuration → Passwords (passwords for a device)
- Configuration → Documents (docs for a device)
- Configuration → Contacts (who manages device)
- Organization → All related data
- Location → Devices at location
- Contact → Managed devices

## 📊 AGGREGATE QUERIES
- Count configurations by type
- Count passwords by category
- List all device types
- Summary statistics per organization
- Asset inventory reports

## 🚀 COMMAND SYNTAX
Basic: "query terms"
Targeted: "@organization query terms"
Examples:
- "@faucets firewall details"
- "@faucets who is the main contact"
- "@faucets admin password for sophos"
- "@faucets switch configuration"
- "@faucets server list with IP addresses"
""")

print("\n" + "=" * 80)
print("NOTES:")
print("=" * 80)
print("""
1. All queries are READ-ONLY for production safety
2. Use @organization to target specific orgs (reduces results by ~99%)
3. Passwords show metadata only, never actual credentials
4. Results include rich details (IP, serial, dates, status, etc.)
5. Natural language queries are supported
6. Multiple filter combinations can be used
""")

print("\n" + "=" * 80)
print("END OF SUPPORTED QUERIES LIST")
print("=" * 80)