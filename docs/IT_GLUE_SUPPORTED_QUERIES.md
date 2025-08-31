# IT Glue MCP Server - Supported Queries Documentation

## Overview
The IT Glue MCP Server provides a comprehensive query interface for accessing IT documentation through natural language. All queries are **READ-ONLY** for production safety.

## Query Syntax

### Basic Format
```
query terms
```

### Targeted Organization Format
```
@organization query terms
```

### Examples
- `@faucets firewall details`
- `@faucets who is the main contact`
- `@faucets admin password for sophos`

---

## 📋 Organizations

### Available Queries
- Get all organizations
- Get organization by ID
- Filter organizations by name
- Get organization relationships

### Examples
```
@faucets organization details
List all organizations
Show organization info
```

---

## 🖥️ Configurations (Hardware/Network Devices)

### Available Queries
- Get all configurations
- Get configurations by organization
- Filter by configuration type (Server, Workstation, Firewall, Switch, etc.)
- Filter by status (Active, Inactive, Disposed)
- Filter by manufacturer
- Filter by model
- Search by serial number
- Search by hostname
- Search by IP address

### Query Patterns
| Query | Result |
|-------|--------|
| `@org firewall` | All firewalls for organization |
| `@org switch details` | All switches with details |
| `@org server list` | All servers |
| `@org workstation` | All workstations |
| `@org nas device` | NAS devices |
| `@org ups` | UPS devices |
| `@org printer` | Printers |
| `@org IP:10.40.0.251` | Device by IP address |
| `@org serial:XYZ123` | Device by serial number |

### Returned Attributes
- IP Address
- Serial Number
- Manufacturer & Model
- Hostname
- Default Gateway
- Installation Date
- Last Updated
- Location
- Status

---

## 🔐 Passwords

### Available Queries
- Get all passwords (metadata only)
- Get passwords by organization
- Filter by resource type
- Filter by username
- Search by name/description
- Get password categories
- Check password expiration dates

**Note**: Actual passwords are NEVER displayed for security. Only metadata is shown.

### Query Patterns
| Query | Result |
|-------|--------|
| `@org admin password` | Admin credentials |
| `@org domain admin` | Domain admin accounts |
| `@org local admin` | Local admin accounts |
| `@org wifi password` | WiFi credentials |
| `@org vpn credentials` | VPN access |
| `@org service account` | Service accounts |
| `@org application password` | App passwords |

### Returned Attributes
- Username
- Password name/description
- URL/System
- Created date
- Last changed date
- Password category
- Expiration status

---

## 📄 Documents

### Available Queries
- Get all documents
- Get documents by organization
- Filter by document type
- Search by document name
- Get document content (if available)
- Filter by created/updated date

### Query Patterns
| Query | Result |
|-------|--------|
| `@org network diagram` | Network documentation |
| `@org runbook` | Runbooks |
| `@org SOP` | Standard operating procedures |
| `@org backup procedure` | Backup docs |
| `@org disaster recovery` | DR plans |
| `@org license` | License documentation |

---

## 👥 Contacts

### Available Queries
- Get all contacts
- Get contacts by organization
- Search by name (first/last)
- Filter by title
- Get contact emails
- Get contact phones
- Filter by location
- Get primary contacts

### Query Patterns
| Query | Result |
|-------|--------|
| `@org main contact` | Primary contacts |
| `@org who is` | All contacts |
| `@org contact info` | Contact details |
| `@org IT contact` | IT personnel |
| `@org manager contact` | Managers |
| `@org [name]` | Specific person |

### Returned Attributes
- Full name
- Title
- Email address
- Phone number
- Location
- Notes

---

## 📍 Locations

### Available Queries
- Get all locations
- Get locations by organization
- Filter by location name
- Get primary location
- Get location addresses
- Get location contacts

### Query Patterns
| Query | Result |
|-------|--------|
| `@org main office` | Primary location |
| `@org branch office` | Branch locations |
| `@org data center` | DC locations |
| `@org location address` | Physical addresses |

---

## 🔧 Flexible Assets (Custom Data)

### Available Queries
- Get flexible assets by type
- Get flexible assets by organization
- Filter by asset attributes
- Search custom fields
- Get relationships between assets

---

## 🎯 Advanced Features

### Filtering Options
- By date range (created/updated)
- By status (Active/Inactive)
- By type/category
- By relationships
- By custom attributes

### Relationship Queries
- Configuration → Passwords (passwords for a device)
- Configuration → Documents (docs for a device)
- Configuration → Contacts (who manages device)
- Organization → All related data
- Location → Devices at location
- Contact → Managed devices

### Aggregate Queries
- Count configurations by type
- Count passwords by category
- List all device types
- Summary statistics per organization
- Asset inventory reports

---

## 🚀 Best Practices

### Query Optimization
1. **Use @organization** to target specific orgs (reduces results by ~99%)
2. **Be specific** with device types and names
3. **Use natural language** - the system understands context
4. **Combine filters** for precise results

### Security Notes
- All queries are **READ-ONLY**
- Passwords show metadata only, never actual credentials
- Sensitive data requires IT Glue direct access
- All queries are logged for audit purposes

### Examples of Effective Queries
```
@faucets firewall IP address
@faucets who manages the main server
@faucets switch configuration details
@faucets admin password last changed
@faucets server serial numbers
@faucets contact phone numbers
@faucets network documentation
```

---

## 📊 Output Format

### Standard Response Structure
```
**[Item Name]** (Type)
  • IP Address: xxx.xxx.xxx.xxx
  • Serial Number: XXXXX
  • Model: Manufacturer Model
  • Status: Active
  • Location: Main Office
  • Last Updated: YYYY-MM-DD
```

### Confidence Scoring
- Results include confidence scores (0.0 - 1.0)
- Higher scores indicate better matches
- Sources are listed with each result

---

## 🛠️ Troubleshooting

### Common Issues

**No results found**
- Check organization name spelling
- Verify you have access to the organization
- Try broader search terms

**Too many results**
- Use @organization to filter
- Add more specific keywords
- Use type filters (firewall, server, etc.)

**Missing attributes**
- Some fields may be empty in IT Glue
- Check IT Glue directly for complete data
- Report missing critical data to IT team

---

## 📈 Future Enhancements

### Planned Features
- Knowledge graph visualization (Neo4j)
- Cross-organization insights
- Predictive maintenance alerts
- Automated documentation generation
- AI-powered troubleshooting suggestions

### Coming Soon
- Relationship mapping between devices
- Dependency analysis
- Change tracking and history
- Bulk export capabilities
- Custom report generation

---

## 📝 Version Information

**Current Version**: 1.0.0  
**Last Updated**: 2025-08-30  
**API Compatibility**: IT Glue API v1  
**Database Support**: PostgreSQL, Qdrant, Redis (Neo4j provisioned)  

---

## 📞 Support

For issues or feature requests, please contact:
- GitHub: https://github.com/Blufix/it-glue-mcp-project
- Documentation: This document in Archon
- API Status: Check IT Glue API status page

---

*This document is maintained in Archon for easy access and updates.*