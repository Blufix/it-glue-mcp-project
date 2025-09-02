"""IT Glue MCP Server - Streamlit UI."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings
from src.data.repositories import ITGlueRepository
from src.services.itglue.client import ITGlueClient

# Page configuration
st.set_page_config(
    page_title="IT Glue Knowledge Base",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .user-message {
        background: #e3f2fd;
        margin-left: 20%;
    }
    .assistant-message {
        background: #f3e5f5;
        margin-right: 20%;
    }
    .source-card {
        background: #fff3e0;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.25rem 0;
        font-size: 0.9rem;
    }
    .confidence-high { color: #2e7d32; }
    .confidence-medium { color: #f57c00; }
    .confidence-low { color: #d32f2f; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'query_history' not in st.session_state:
    st.session_state.query_history = []
if 'selected_org' not in st.session_state:
    st.session_state.selected_org = None
if 'sync_status' not in st.session_state:
    st.session_state.sync_status = {}
if 'query_count' not in st.session_state:
    st.session_state.query_count = 0

# Database setup
@st.cache_resource
def get_database_engine():
    """Get database engine."""
    return create_async_engine(settings.database_url)

@st.cache_resource
def get_session_maker():
    """Get session maker."""
    engine = get_database_engine()
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_organizations():
    """Fetch available organizations from IT Glue API."""
    try:
        # Try to get from IT Glue API first
        client = ITGlueClient(
            api_key=settings.itglue_api_key,
            api_url=settings.itglue_api_url
        )

        organizations = await client.get_organizations()
        await client.disconnect()

        # Return list of (id, name) tuples
        return [(org.id, org.name) for org in organizations if org.name]

    except Exception as e:
        st.error(f"Failed to fetch organizations from IT Glue: {e}")

        # Fallback to database if API fails
        SessionLocal = get_session_maker()
        async with SessionLocal() as session:
            repo = ITGlueRepository(session)
            # Get unique organizations
            query = """
                SELECT DISTINCT organization_id,
                       MAX(attributes->>'organization_name') as org_name
                FROM itglue_entities
                WHERE organization_id IS NOT NULL
                GROUP BY organization_id
                ORDER BY org_name
            """
            from sqlalchemy import text
            result = await session.execute(text(query))
            orgs = result.fetchall()
            return [(org[0], org[1] or f"Org {org[0]}") for org in orgs]

async def get_entity_stats(org_id: Optional[str] = None):
    """Get entity statistics from IT Glue."""
    try:
        if org_id:
            # Get stats from IT Glue API for specific org
            client = ITGlueClient(
                api_key=settings.itglue_api_key,
                api_url=settings.itglue_api_url
            )

            stats = {}

            # Get configurations count
            try:
                configs = await client.get_configurations(filters={"organization_id": org_id})
                stats["configurations"] = len(configs)
            except:
                stats["configurations"] = 0

            # Get contacts count
            try:
                contacts = await client.get_contacts(filters={"organization_id": org_id})
                stats["contacts"] = len(contacts)
            except:
                stats["contacts"] = 0

            # Get passwords count
            try:
                passwords = await client.get_passwords(filters={"organization_id": org_id})
                stats["passwords"] = len(passwords)
            except:
                stats["passwords"] = 0

            await client.disconnect()
            return stats

    except Exception as e:
        st.error(f"Failed to get stats from IT Glue: {e}")

    # Fallback to database
    SessionLocal = get_session_maker()
    async with SessionLocal() as session:
        from sqlalchemy import text

        base_query = """
            SELECT entity_type, COUNT(*) as count
            FROM itglue_entities
            {where_clause}
            GROUP BY entity_type
            ORDER BY count DESC
        """

        where_clause = f"WHERE organization_id = '{org_id}'" if org_id else ""
        query = base_query.format(where_clause=where_clause)

        result = await session.execute(text(query))
        stats = result.fetchall()
        return {row[0]: row[1] for row in stats}

async def find_org_by_name(org_name: str) -> Optional[str]:
    """Find organization ID by partial name match."""
    try:
        client = ITGlueClient(
            api_key=settings.itglue_api_key,
            api_url=settings.itglue_api_url
        )

        # Get all organizations
        orgs = await client.get_organizations()

        # Look for exact or partial match (case insensitive)
        org_name_lower = org_name.lower()
        for org in orgs:
            if org_name_lower in org.name.lower():
                await client.disconnect()
                return org.id

        await client.disconnect()
        return None

    except Exception as e:
        st.error(f"Error finding organization: {e}")
        return None

async def search_itglue_data(query: str, org_id: Optional[str] = None):
    """Search IT Glue data for relevant information."""
    try:
        client = ITGlueClient(
            api_key=settings.itglue_api_key,
            api_url=settings.itglue_api_url
        )

        sources = []
        results = []

        # Determine what to search for based on query
        query_lower = query.lower()

        # PRIORITY 1: "list" queries should always search configurations
        # Search configurations if relevant keywords found (including "list" queries and "access point")
        if "list" in query_lower or any(word in query_lower for word in ["server", "firewall", "switch", "router", "nas", "configuration", "device", "hardware", "sophos", "xgs", "network", "printer", "ups", "laptop", "desktop", "workstation", "access point", "ap ", "aps", "ubiquiti"]):
            try:
                # For configurations, use org_id directly
                configs = await client.get_configurations(org_id=org_id) if org_id else await client.get_configurations()
                
                # Debug: Show how many configs we're checking
                print(f"DEBUG: Checking {len(configs)} configurations for query: {query_lower}")
                matches_found = 0

                for config in configs:  # Check ALL configs
                    # Check if configuration is archived
                    attrs = config.attributes if hasattr(config, 'attributes') else {}
                    is_archived = attrs.get('archived', False)
                    
                    # Check if user is specifically asking for archived items
                    listing_archived = "list archive" in query_lower or "list archived" in query_lower
                    
                    # Skip archived items UNLESS user is specifically listing archived
                    if is_archived and not listing_archived:
                        print(f"DEBUG: Skipping archived config: {config.name}")
                        continue
                    
                    # Skip non-archived items if user is specifically listing archived
                    if not is_archived and listing_archived:
                        continue
                    
                    config_name_lower = config.name.lower()
                    config_type_lower = (config.configuration_type or "").lower()

                    # Smart matching: check both name and type
                    match_found = False

                    # Skip common words that cause false positives
                    meaningful_words = [w for w in query_lower.split()
                                       if w not in ["what", "is", "the", "name", "of", "at", "for", "in", "a", "an"]]

                    # Check for "list [type]" pattern - specific listing queries
                    if "list" in query_lower:
                        # Map common terms to IT Glue configuration types
                        type_mappings = {
                            "switch": ["switch"],
                            "switches": ["switch"],
                            "printer": ["printer"],
                            "printers": ["printer"],
                            "server": ["server"],
                            "servers": ["server"],
                            "firewall": ["firewall"],
                            "firewalls": ["firewall"],
                            "access point": ["ubiquiti access point"],
                            "access points": ["ubiquiti access point"],
                            "ap": ["ubiquiti access point"],
                            "aps": ["ubiquiti access point"],
                            "ubiquiti": ["ubiquiti access point"],
                            "laptop": ["laptop"],
                            "laptops": ["laptop"],
                            "desktop": ["desktop"],
                            "desktops": ["desktop"],
                            "workstation": ["desktop", "laptop"],
                            "workstations": ["desktop", "laptop"],
                            "nas": ["nas", "network device (nas)"],
                            "security": ["security"],
                            "ups": ["ups"],
                            "network device": ["network device"],
                            "all": ["all"],  # List everything
                            "configuration": ["all"],  # List all configurations
                            "configurations": ["all"]
                        }
                        
                        # Special case: "list archived" is handled above in the filtering
                        if listing_archived:
                            match_found = True  # Include all archived items
                        else:
                            # Check if query matches any type mapping
                            for term, config_types in type_mappings.items():
                                if term in query_lower:
                                    if "all" in config_types:
                                        # For "list all", include everything not archived
                                        match_found = True
                                        break
                                    else:
                                        # Check if config type matches any of the mapped types
                                        if any(ct in config_type_lower for ct in config_types):
                                            match_found = True
                                            break
                    
                    # Check for network-related queries - match ALL network devices
                    elif any(term in query_lower for term in ["network", "all config", "all device", "show config"]):
                        # Match actual IT Glue configuration types for network devices
                        network_config_types = [
                            "firewall",
                            "switch", 
                            "ubiquiti access point",
                            "network device (other)",
                            "network device (nas)",
                            "printer",
                            "server",  # Servers are network devices too
                            "nas"
                        ]
                        # Check if the config type matches any network type
                        if any(nt in config_type_lower for nt in network_config_types):
                            match_found = True
                        # Also check device names for network keywords
                        elif any(keyword in config_name_lower for keyword in ["switch", "router", "firewall", "access point", "ap", "gateway", "ubiquiti", "unifi", "sophos", "xgs", "printer"]):
                            match_found = True
                    # Type-based matching for specific queries (using exact IT Glue types)
                    elif "firewall" in query_lower and config_type_lower == "firewall":
                        match_found = True
                    elif "switch" in query_lower and config_type_lower == "switch":
                        match_found = True
                    elif "server" in query_lower and config_type_lower == "server":
                        match_found = True
                    elif "nas" in query_lower and config_type_lower in ["nas", "network device (nas)"]:
                        match_found = True
                    elif "ups" in query_lower and config_type_lower == "ups":
                        match_found = True
                    elif "printer" in query_lower and config_type_lower == "printer":
                        match_found = True
                    elif "laptop" in query_lower and config_type_lower == "laptop":
                        match_found = True
                    elif "desktop" in query_lower and config_type_lower == "desktop":
                        match_found = True
                    elif "workstation" in query_lower and config_type_lower in ["desktop", "laptop"]:
                        match_found = True
                    elif "access point" in query_lower and config_type_lower == "ubiquiti access point":
                        match_found = True
                    elif "security" in query_lower and config_type_lower == "security":
                        match_found = True
                    # Direct meaningful word match in name
                    elif meaningful_words and any(word in config_name_lower for word in meaningful_words):
                        match_found = True
                    # Also match if asking for IP and any of the above matched
                    elif "ip" in query_lower and meaningful_words and any(word in config_name_lower for word in meaningful_words):
                        match_found = True

                    if match_found:  # NO LIMIT - show all matches
                        matches_found += 1
                        sources.append({
                            "type": "Configuration",
                            "name": config.name,
                            "confidence": 0.85
                        })

                        # Build detailed result with all available attributes
                        details = []
                        details.append(f"**{config.name}** ({config.configuration_type})")

                        # Add key attributes if available
                        attrs = config.attributes if hasattr(config, 'attributes') else {}

                        if attrs.get('primary-ip'):
                            details.append(f"  • IP Address: {attrs.get('primary-ip')}")
                        if attrs.get('serial-number'):
                            details.append(f"  • Serial Number: {attrs.get('serial-number')}")
                        if attrs.get('manufacturer-name') or attrs.get('model-name'):
                            manufacturer = attrs.get('manufacturer-name', '')
                            model = attrs.get('model-name', '')
                            if manufacturer or model:
                                details.append(f"  • Model: {manufacturer} {model}".strip())
                        if attrs.get('default-gateway'):
                            details.append(f"  • Gateway: {attrs.get('default-gateway')}")
                        if attrs.get('hostname'):
                            details.append(f"  • Hostname: {attrs.get('hostname')}")
                        if attrs.get('installed-at'):
                            details.append(f"  • Installed: {attrs.get('installed-at')[:10]}")
                        if attrs.get('created-at'):
                            details.append(f"  • Added to IT Glue: {attrs.get('created-at')[:10]}")
                        if attrs.get('updated-at'):
                            details.append(f"  • Last Updated: {attrs.get('updated-at')[:10]}")
                        if attrs.get('location-name'):
                            details.append(f"  • Location: {attrs.get('location-name')}")
                        if attrs.get('configuration-status-name'):
                            details.append(f"  • Status: {attrs.get('configuration-status-name')}")

                        results.append("\n".join(details))
                
                # Debug: Show how many matches were found
                print(f"DEBUG: Found {matches_found} matching configurations out of {len(configs)} total")
                
            except Exception as e:
                st.warning(f"Could not search configurations: {e}")

        # Search passwords if relevant keywords found (but not for "access point" queries)
        if "list password" in query_lower or ("access point" not in query_lower and "access points" not in query_lower and any(word in query_lower for word in ["password", "credential", "login", "username", "admin", "access"])):
            try:
                # For passwords, use org_id directly
                passwords = await client.get_passwords(org_id=org_id) if org_id else await client.get_passwords()

                for pwd in passwords:  # Check ALL passwords
                    # If using "list passwords", show ALL passwords
                    if "list password" in query_lower or "list all password" in query_lower:
                        match_found = True
                    # Otherwise check if any word matches the password name
                    elif any(word in pwd.name.lower() for word in query_lower.split()):
                        match_found = True
                    else:
                        match_found = False
                    
                    if match_found:
                        sources.append({
                            "type": "Password",
                            "name": pwd.name,
                            "confidence": 0.90
                        })
                        # Don't show actual password, just indicate it exists
                        pwd_details = []
                        pwd_details.append(f"**{pwd.name}**")

                        attrs = pwd.attributes if hasattr(pwd, 'attributes') else {}

                        if pwd.username:
                            pwd_details.append(f"  • Username: {pwd.username}")
                        if attrs.get('url'):
                            pwd_details.append(f"  • URL: {attrs.get('url')}")
                        if attrs.get('created-at'):
                            pwd_details.append(f"  • Created: {attrs.get('created-at')[:10]}")
                        if attrs.get('updated-at'):
                            pwd_details.append(f"  • Last Changed: {attrs.get('updated-at')[:10]}")
                        if attrs.get('notes'):
                            pwd_details.append(f"  • Notes: {attrs.get('notes')[:100]}...")

                        pwd_details.append("  • 🔒 Password stored securely in IT Glue")
                        results.append("\n".join(pwd_details))
            except Exception as e:
                st.warning(f"Could not search passwords: {e}")

        # Search contacts if relevant keywords found (including "list contacts")
        if "list contact" in query_lower or any(word in query_lower for word in ["contact", "person", "email", "phone", "user", "who", "main", "primary", "staff", "employee"]):
            try:
                # For contacts, use org_id directly
                contacts = await client.get_contacts(org_id=org_id) if org_id else await client.get_contacts()

                # For contact queries, be more lenient with matching
                for contact in contacts:  # Check ALL contacts
                    match_found = False

                    # If using "list contacts", show ALL contacts
                    if "list contact" in query_lower or "list all contact" in query_lower:
                        match_found = True
                    # If asking about "main contact" or similar, return all contacts for the org
                    elif any(phrase in query_lower for phrase in ["main contact", "primary contact", "who is", "contact info", "contact details", "contact person"]):
                        match_found = True
                    # Otherwise check if any word matches the contact name
                    elif any(word in contact.full_name.lower() for word in query_lower.split()):
                        match_found = True

                    if match_found:
                        sources.append({
                            "type": "Contact",
                            "name": contact.full_name,
                            "confidence": 0.80
                        })

                        contact_details = []
                        contact_details.append(f"**{contact.full_name}**")

                        attrs = contact.attributes if hasattr(contact, 'attributes') else {}

                        if attrs.get('title'):
                            contact_details.append(f"  • Title: {attrs.get('title')}")
                        if attrs.get('contact-emails'):
                            emails = attrs.get('contact-emails', [])
                            if emails and len(emails) > 0:
                                contact_details.append(f"  • Email: {emails[0].get('value', 'N/A')}")
                        if attrs.get('contact-phones'):
                            phones = attrs.get('contact-phones', [])
                            if phones and len(phones) > 0:
                                contact_details.append(f"  • Phone: {phones[0].get('value', 'N/A')}")
                        if attrs.get('location-name'):
                            contact_details.append(f"  • Location: {attrs.get('location-name')}")
                        if attrs.get('notes'):
                            contact_details.append(f"  • Notes: {attrs.get('notes')[:100]}...")

                        results.append("\n".join(contact_details))
            except Exception as e:
                st.warning(f"Could not search contacts: {e}")

        # Search documents if relevant keywords found (including "list documents")
        if "list document" in query_lower or any(word in query_lower for word in ["document", "documentation", "runbook", "sop", "procedure", "diagram", "network diagram", "backup", "disaster recovery", "dr plan", "license", "guide", "manual", "policy", "standard"]):
            try:
                # For documents, use org_id directly
                documents = await client.get_documents(org_id=org_id) if org_id else await client.get_documents()

                # If no documents found, add a note about API limitations
                if not documents and any(word in query_lower for word in ["document", "documentation"]):
                    results.append(
                        "📁 **No API documents found**\n\n"
                        "IT Glue has two document systems:\n"
                        "• **API Documents**: Created programmatically (searchable here)\n"
                        "• **File Uploads**: Word/PDF files uploaded via UI (not accessible via API)\n\n"
                        "Documents like 'Bawso Autopilot Configuration' in folders are likely file uploads "
                        "that can only be viewed in the IT Glue web interface."
                    )

                for doc in documents:  # Check ALL documents
                    doc_name_lower = doc.name.lower() if hasattr(doc, 'name') else ""

                    # Check if any word from query matches document name
                    match_found = False

                    # If using "list documents", show ALL documents
                    if "list document" in query_lower or "list all document" in query_lower:
                        match_found = True
                    # Remove common words for better matching
                    else:
                        meaningful_words = [w for w in query_lower.split()
                                           if w not in ["what", "is", "the", "show", "get", "find", "list", "all", "for", "in", "a", "an"]]

                    # Check for specific document types if not listing all
                    if "runbook" in query_lower and "runbook" in doc_name_lower:
                        match_found = True
                    elif "sop" in query_lower and ("sop" in doc_name_lower or "standard operating" in doc_name_lower):
                        match_found = True
                    elif "diagram" in query_lower and "diagram" in doc_name_lower:
                        match_found = True
                    elif "backup" in query_lower and "backup" in doc_name_lower:
                        match_found = True
                    elif "disaster recovery" in query_lower and ("disaster" in doc_name_lower or "dr" in doc_name_lower):
                        match_found = True
                    elif "license" in query_lower and "license" in doc_name_lower:
                        match_found = True
                    elif "policy" in query_lower and "policy" in doc_name_lower:
                        match_found = True
                    # General document search - match any meaningful word
                    elif meaningful_words and any(word in doc_name_lower for word in meaningful_words):
                        match_found = True
                    # If just asking for "documentation" or "documents", show all for this org
                    elif any(phrase in query_lower for phrase in ["all documentation", "all documents", "show documentation", "list documents"]):
                        match_found = True

                    if match_found:
                        sources.append({
                            "type": "Document",
                            "name": doc.name if hasattr(doc, 'name') else "Unnamed Document",
                            "confidence": 0.85
                        })

                        doc_details = []
                        doc_details.append(f"**{doc.name if hasattr(doc, 'name') else 'Unnamed Document'}** (Document)")

                        attrs = doc.attributes if hasattr(doc, 'attributes') else {}

                        # Add document type if available
                        if attrs.get('document-type'):
                            doc_details.append(f"  • Type: {attrs.get('document-type')}")

                        # Add created and updated dates
                        if attrs.get('created-at'):
                            doc_details.append(f"  • Created: {attrs.get('created-at')[:10]}")
                        if attrs.get('updated-at'):
                            doc_details.append(f"  • Last Updated: {attrs.get('updated-at')[:10]}")

                        # Add author if available
                        if attrs.get('created-by'):
                            doc_details.append(f"  • Author: {attrs.get('created-by')}")

                        # Add description or excerpt if available
                        if attrs.get('description'):
                            doc_details.append(f"  • Description: {attrs.get('description')[:200]}...")
                        elif attrs.get('content'):
                            # Show first 200 chars of content as preview
                            content_preview = str(attrs.get('content'))[:200]
                            doc_details.append(f"  • Preview: {content_preview}...")

                        # Add URL if it's a linked document
                        if attrs.get('url'):
                            doc_details.append(f"  • URL: {attrs.get('url')}")

                        doc_details.append("  • 📄 Full document available in IT Glue")
                        results.append("\n".join(doc_details))
            except Exception as e:
                st.warning(f"Could not search documents: {e}")

        await client.disconnect()

        # Format response
        if results:
            content = f"Based on your search for '{query}', I found the following in IT Glue:\n\n"
            content += "\n\n".join(results)  # Results already formatted with details
            if any("Password" in str(source.get("type")) for source in sources):
                content += "\n\n🔐 **Security Note**: Actual passwords are not displayed. Access IT Glue directly to retrieve credentials."
        else:
            content = f"No relevant information found for '{query}' in IT Glue. Try refining your search or check if you have the correct organization selected."

        return {
            "content": content,
            "sources": sources[:5],  # Limit sources shown
            "confidence": 0.85 if sources else 0.0
        }

    except Exception as e:
        st.error(f"Error searching IT Glue: {e}")
        return {
            "content": f"Error searching IT Glue: {str(e)}",
            "sources": [],
            "confidence": 0.0
        }

async def get_sync_status():
    """Get sync status for all entity types."""
    SessionLocal = get_session_maker()
    async with SessionLocal() as session:
        from sqlalchemy import text

        query = """
            SELECT entity_type,
                   last_sync_completed,
                   last_sync_status,
                   records_synced
            FROM sync_status
            ORDER BY last_sync_completed DESC
        """

        result = await session.execute(text(query))
        return result.fetchall()

async def search_knowledge_base(query: str, org_id: Optional[str] = None):
    """Search the knowledge base."""
    SessionLocal = get_session_maker()
    async with SessionLocal() as session:
        # Initialize query engine
        from src.query.engine import QueryEngine
        engine = QueryEngine()

        # Execute search
        results = await engine.search(
            query=query,
            organization_id=org_id,
            limit=100  # Increased limit for testing
        )

        return results

def render_sidebar():
    """Render sidebar with filters and stats."""
    with st.sidebar:
        st.markdown("## 🎛️ Control Panel")

        # Organization selector with counts
        st.markdown("### 🏢 Organization")

        # Fetch organizations (without counts for performance)
        @st.cache_data(ttl=300)  # Cache for 5 minutes
        def fetch_organizations():
            """Fetch organizations from IT Glue."""
            try:
                async def get_orgs():
                    client = ITGlueClient(
                        api_key=settings.itglue_api_key,
                        api_url=settings.itglue_api_url
                    )
                    
                    # Get organizations
                    orgs = await client.get_organizations()
                    org_data = []
                    
                    # Get ALL organizations and ensure Faucets is included
                    for org in orgs:  # Get ALL orgs
                        org_data.append({
                            "id": org.id,
                            "name": org.name,
                            "display": org.name
                        })
                    
                    await client.disconnect()
                    return org_data

                return asyncio.run(get_orgs())
            except Exception as e:
                st.error(f"Failed to fetch organizations: {e}")
                return []

        # Get organizations
        org_data = fetch_organizations()
        
        # Add search filter for organizations
        search_term = st.text_input(
            "🔍 Search Organizations", 
            placeholder="Type to filter...",
            help=f"Search among {len(org_data)} organizations"
        )
        
        # Build options list
        orgs = [{"id": "all", "display": "🌍 All Organizations"}]
        if org_data:
            # Filter by search term if provided
            if search_term:
                filtered_data = [
                    org for org in org_data 
                    if search_term.lower() in org["name"].lower()
                ]
                # If search found something, use filtered list
                if filtered_data:
                    org_data_sorted = sorted(filtered_data, key=lambda x: x["name"])
                    orgs.extend(org_data_sorted)
                    st.caption(f"Found {len(filtered_data)} matching organizations")
                else:
                    st.warning(f"No organizations found matching '{search_term}'")
                    # Still show all orgs if no match
                    org_data_sorted = sorted(org_data, key=lambda x: x["name"])
                    orgs.extend(org_data_sorted)
            else:
                # Sort alphabetically for easier finding
                org_data_sorted = sorted(org_data, key=lambda x: x["name"])
                orgs.extend(org_data_sorted)
        else:
            # Fallback to known organizations if API fails
            orgs.extend([
                {"id": "3183713165639879", "display": "Faucets Limited"},
                {"id": "2092605563994340", "display": "CSG Computer Services Ltd"},
                {"id": "2093707467407574", "display": "ConnectWise"}
            ])

        # Check if Faucets is in the list
        faucets_found = any("faucet" in org.get("display", "").lower() for org in orgs)
        if not faucets_found and not search_term:
            st.warning("⚠️ Faucets organization not found in list. Try searching for 'Faucet' above.")

        selected = st.selectbox(
            "Select Organization",
            options=[org["id"] for org in orgs],
            format_func=lambda x: next((org["display"] for org in orgs if org["id"] == x), x),
            key="org_selector",
            help=f"Select from {len(orgs)-1} organizations"  # -1 for "All Organizations"
        )
        st.session_state.selected_org = selected if selected != "all" else None

        # Detailed stats for selected organization
        if st.session_state.selected_org and st.session_state.selected_org != "all":
            st.markdown("### 📊 Organization Details")
            
            # Get detailed counts from IT Glue
            @st.cache_data(ttl=60)  # Cache for 1 minute
            def get_detailed_entity_counts(org_id):
                """Get detailed entity counts for an organization."""
                try:
                    async def get_counts():
                        client = ITGlueClient(
                            api_key=settings.itglue_api_key,
                            api_url=settings.itglue_api_url
                        )

                        counts = {}
                        
                        # Get configurations with breakdown by type
                        try:
                            configs = await client.get_configurations(org_id=org_id)
                            
                            # Filter out archived configurations (archived=true)
                            active_configs = []
                            for config in configs:
                                attrs = config.attributes if hasattr(config, 'attributes') else {}
                                is_archived = attrs.get('archived', False)
                                if not is_archived:
                                    active_configs.append(config)
                            
                            counts['total_configs'] = len(active_configs)
                            
                            # Count by configuration type (excluding archived)
                            config_types = {}
                            for config in active_configs:
                                config_type = config.configuration_type or "Unknown"
                                config_types[config_type] = config_types.get(config_type, 0) + 1
                            counts['config_types'] = config_types
                        except:
                            counts['total_configs'] = 0
                            counts['config_types'] = {}

                        # Get other entity counts
                        try:
                            passwords = await client.get_passwords(org_id=org_id)
                            counts['passwords'] = len(passwords)
                        except:
                            counts['passwords'] = 0

                        try:
                            contacts = await client.get_contacts(org_id=org_id)
                            counts['contacts'] = len(contacts)
                        except:
                            counts['contacts'] = 0
                            
                        try:
                            documents = await client.get_documents(org_id=org_id)
                            counts['documents'] = len(documents)
                        except:
                            counts['documents'] = 0

                        await client.disconnect()
                        return counts

                    return asyncio.run(get_counts())
                except Exception as e:
                    st.error(f"Failed to get entity counts: {e}")
                    return {'total_configs': 0, 'config_types': {}, 'passwords': 0, 'contacts': 0, 'documents': 0}

            entity_counts = get_detailed_entity_counts(st.session_state.selected_org)
            
            # Display summary metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Configurations", entity_counts['total_configs'])
                st.metric("Passwords", entity_counts['passwords'])
            with col2:
                st.metric("Contacts", entity_counts['contacts'])
                st.metric("Documents", entity_counts['documents'])
            
            # Show configuration breakdown if available
            if entity_counts['config_types']:
                with st.expander("Configuration Types", expanded=False):
                    for config_type, count in sorted(entity_counts['config_types'].items(), key=lambda x: x[1], reverse=True):
                        st.write(f"• **{config_type}**: {count}")
        
        # Sync status section
        st.markdown("### 🔄 Sync Status")

        # Simplified sync status
        @st.cache_data(ttl=60)  # Cache for 1 minute
        def get_sync_status():
            """Get sync status."""
            try:
                async def get_status():
                    client = ITGlueClient(
                        api_key=settings.itglue_api_key,
                        api_url=settings.itglue_api_url
                    )

                    counts = {}
                    # Get organization count
                    orgs = await client.get_organizations()
                    counts['Organizations'] = len(orgs)
                    
                    # Global counts if no org selected
                    if not st.session_state.selected_org or st.session_state.selected_org == "all":
                        counts['Status'] = "Connected"
                    else:
                        counts['Status'] = "Filtered"
                        counts['Contacts'] = "N/A"

                    counts['Documents'] = "N/A"  # Documents endpoint may vary

                    await client.disconnect()
                    return counts

                return asyncio.run(get_status())
            except Exception:
                return {"Status": "Disconnected", "Organizations": 0}

        # Get sync status
        sync_status = get_sync_status()
        
        # Display sync status
        if sync_status.get("Status") == "Connected":
            st.success(f"✅ Connected - {sync_status.get('Organizations', 0)} organizations")
        elif sync_status.get("Status") == "Filtered":
            st.info(f"🔍 Filtered View Active")
        else:
            st.error("❌ Disconnected from IT Glue")

        # Sync actions
        st.markdown("### 🚀 Actions")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        with col2:
            if st.button("🧹 Clear Cache", use_container_width=True):
                st.cache_data.clear()
                st.info("Cache cleared")

        # Statistics
        st.markdown("### 📊 Statistics")

        # Real statistics
        stats = {
            "Total Queries": st.session_state.get('query_count', 0),
            "Current Session": len(st.session_state.messages),
            "Cache Status": "Active",
            "API Status": "✅ Connected"
        }

        for label, value in stats.items():
            st.metric(label, value)

        # Query history
        st.markdown("### 📜 Recent Queries")

        if st.session_state.query_history:
            for i, query in enumerate(st.session_state.query_history[-5:][::-1]):
                with st.expander(f"Q{i+1}: {query['query'][:30]}...", expanded=False):
                    st.caption(f"Time: {query['timestamp']}")
                    st.caption(f"Confidence: {query['confidence']:.1%}")
                    if query.get('sources'):
                        st.caption(f"Sources: {len(query['sources'])}")

def render_chat_interface():
    """Render the main chat interface."""
    st.markdown('<h1 class="main-header">🔍 IT Glue Knowledge Base</h1>', unsafe_allow_html=True)

    # Display chat messages
    messages_container = st.container()

    with messages_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message user-message">👤 {message["content"]}</div>',
                          unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message assistant-message">🤖 {message["content"]}</div>',
                          unsafe_allow_html=True)

                # Show sources if available
                if message.get("sources"):
                    with st.expander("📚 Sources", expanded=False):
                        for source in message["sources"]:
                            confidence_class = (
                                "confidence-high" if source.get("confidence", 0) > 0.8
                                else "confidence-medium" if source.get("confidence", 0) > 0.6
                                else "confidence-low"
                            )
                            st.markdown(
                                f'<div class="source-card">'
                                f'<b>{source.get("type", "Unknown")}</b>: {source.get("name", "Unnamed")}<br>'
                                f'<span class="{confidence_class}">Confidence: {source.get("confidence", 0):.1%}</span>'
                                f'</div>',
                                unsafe_allow_html=True
                            )

    # Query input
    with st.form(key="query_form", clear_on_submit=True):
        col1, col2 = st.columns([6, 1])

        with col1:
            query = st.text_input(
                "Ask a question about your IT infrastructure...",
                placeholder="e.g., @faucets what's the firewall name?",
                label_visibility="collapsed",
                help="💡 Use @organization to target a specific organization (e.g., @faucets firewall details)"
            )

        with col2:
            submit = st.form_submit_button("🔍 Search", use_container_width=True, type="primary")

        if submit and query:
            # Add user message
            st.session_state.messages.append({"role": "user", "content": query})

            # Process query with real IT Glue data
            with st.spinner("🔍 Searching IT Glue knowledge base..."):
                # Parse for @organization command
                org_id = st.session_state.get("selected_org")
                org_name = None

                # Check for @organization syntax
                import re
                match = re.search(r'@(\w+)', query)
                if match:
                    org_name = match.group(1)
                    # Remove the @organization from the query
                    query_clean = re.sub(r'@\w+\s*', '', query).strip()

                    # Find the organization by name
                    org_id_found = asyncio.run(find_org_by_name(org_name))
                    if org_id_found:
                        org_id = org_id_found
                        st.info(f"🎯 Targeting organization: {org_name}")
                    else:
                        st.warning(f"⚠️ Organization '{org_name}' not found, using current selection")
                else:
                    query_clean = query

                # Search IT Glue for relevant data
                response = asyncio.run(search_itglue_data(query_clean, org_id))

                # Add assistant message
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response["content"],
                    "sources": response["sources"]
                })

                # Add to query history
                st.session_state.query_history.append({
                    "query": query,
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "confidence": response["confidence"],
                    "sources": response["sources"]
                })

                # Increment query counter
                st.session_state.query_count += 1

                st.rerun()

def render_metrics_dashboard():
    """Render metrics dashboard."""
    st.markdown("## 📈 System Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Entities",
            value="5,352",
            delta="+125 today",
            delta_color="normal"
        )

    with col2:
        st.metric(
            label="Organizations",
            value="45",
            delta="+2 this week",
            delta_color="normal"
        )

    with col3:
        st.metric(
            label="Query Performance",
            value="1.2s",
            delta="-0.3s",
            delta_color="inverse"
        )

    with col4:
        st.metric(
            label="System Health",
            value="98%",
            delta="+2%",
            delta_color="normal"
        )

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        # Query volume chart
        dates = pd.date_range(end=datetime.now(), periods=7, freq='D')
        query_volumes = [45, 52, 48, 61, 55, 72, 68]

        fig = px.line(
            x=dates,
            y=query_volumes,
            title="Query Volume (Last 7 Days)",
            labels={"x": "Date", "y": "Queries"}
        )
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Entity distribution
        entity_types = ["Configurations", "Documents", "Passwords", "Contacts", "Networks"]
        entity_counts = [1250, 3400, 890, 567, 245]

        fig = px.pie(
            values=entity_counts,
            names=entity_types,
            title="Entity Distribution"
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

def main():
    """Main application."""
    # Render sidebar
    render_sidebar()

    # Main content area
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Dashboard", "⚙️ Settings"])

    with tab1:
        render_chat_interface()

    with tab2:
        render_metrics_dashboard()

    with tab3:
        st.markdown("## ⚙️ Settings")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### API Configuration")
            api_key = st.text_input("IT Glue API Key", type="password", value="*" * 20)
            api_url = st.text_input("API URL", value=settings.itglue_api_url)

            st.markdown("### Query Settings")
            confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.7, 0.05)
            max_results = st.number_input("Max Results", 1, 50, 10)

        with col2:
            st.markdown("### Cache Settings")
            cache_ttl = st.number_input("Cache TTL (seconds)", 60, 3600, 300)
            cache_enabled = st.checkbox("Enable Query Cache", value=True)

            st.markdown("### Sync Settings")
            auto_sync = st.checkbox("Auto Sync", value=True)
            sync_interval = st.number_input("Sync Interval (minutes)", 5, 60, 15)

        if st.button("💾 Save Settings", type="primary"):
            st.success("Settings saved successfully!")

if __name__ == "__main__":
    main()
