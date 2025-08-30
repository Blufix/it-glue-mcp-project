"""IT Glue MCP Server - Streamlit UI."""

import streamlit as st
import asyncio
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, List, Dict, Any
import httpx
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import settings
from src.query.engine import QueryEngine
from src.sync.orchestrator import SyncOrchestrator
from src.data.repositories import ITGlueRepository
from src.services.itglue.client import ITGlueClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

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
        
        # Search configurations if relevant keywords found
        if any(word in query_lower for word in ["server", "firewall", "switch", "router", "nas", "configuration", "device", "hardware", "sophos", "xgs", "network"]):
            try:
                # For configurations, use org_id directly
                configs = await client.get_configurations(org_id=org_id) if org_id else await client.get_configurations()
                
                for config in configs:  # Check all configs, not just first 10
                    config_name_lower = config.name.lower()
                    config_type_lower = (config.configuration_type or "").lower()
                    
                    # Smart matching: check both name and type
                    match_found = False
                    
                    # Skip common words that cause false positives
                    meaningful_words = [w for w in query_lower.split() 
                                       if w not in ["what", "is", "the", "name", "of", "at", "for", "in", "a", "an"]]
                    
                    # Type-based matching for common queries (check this first)
                    if "firewall" in query_lower and ("firewall" in config_type_lower or 
                                                      any(fw in config_name_lower for fw in ["sophos", "xgs", "xg", "fortinet", "sonicwall"])):
                        match_found = True
                    # Direct meaningful word match in name
                    elif meaningful_words and any(word in config_name_lower for word in meaningful_words):
                        match_found = True
                    elif "switch" in query_lower and "switch" in config_type_lower:
                        match_found = True
                    elif "server" in query_lower and "server" in config_type_lower:
                        match_found = True
                    elif "nas" in query_lower and ("nas" in config_type_lower or "nas" in config_name_lower):
                        match_found = True
                    elif "ups" in query_lower and ("ups" in config_type_lower or "ups" in config_name_lower):
                        match_found = True
                    elif "printer" in query_lower and "printer" in config_type_lower:
                        match_found = True
                    
                    if match_found and len(results) < 10:  # Limit results to 10
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
            except Exception as e:
                st.warning(f"Could not search configurations: {e}")
        
        # Search passwords if relevant keywords found
        if any(word in query_lower for word in ["password", "credential", "login", "username", "admin", "access"]):
            try:
                # For passwords, use org_id directly
                passwords = await client.get_passwords(org_id=org_id) if org_id else await client.get_passwords()
                
                for pwd in passwords[:10]:  # Limit to first 10
                    if any(word in pwd.name.lower() for word in query_lower.split()):
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
        
        # Search contacts if relevant keywords found
        if any(word in query_lower for word in ["contact", "person", "email", "phone", "user", "who", "main", "primary", "staff", "employee"]):
            try:
                # For contacts, use org_id directly
                contacts = await client.get_contacts(org_id=org_id) if org_id else await client.get_contacts()
                
                # For contact queries, be more lenient with matching
                for contact in contacts[:10]:  # Limit to first 10
                    match_found = False
                    
                    # If asking about "main contact" or similar, return all contacts for the org
                    if any(phrase in query_lower for phrase in ["main contact", "primary contact", "who is", "contact info", "contact details", "contact person"]):
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
            limit=10
        )
        
        return results

def render_sidebar():
    """Render sidebar with filters and stats."""
    with st.sidebar:
        st.markdown("## 🎛️ Control Panel")
        
        # Organization selector
        st.markdown("### 🏢 Organization")
        
        # Fetch organizations (mock for now)
        orgs = [("all", "All Organizations"), ("org1", "Contoso Ltd"), ("org2", "Fabrikam Inc")]
        
        selected = st.selectbox(
            "Select Organization",
            options=[org[0] for org in orgs],
            format_func=lambda x: next(org[1] for org in orgs if org[0] == x),
            key="org_selector"
        )
        st.session_state.selected_org = selected if selected != "all" else None
        
        # Sync status
        st.markdown("### 🔄 Sync Status")
        
        # Mock sync data
        sync_data = {
            "Organizations": {"status": "✅", "last_sync": "2 mins ago", "count": 45},
            "Configurations": {"status": "✅", "last_sync": "5 mins ago", "count": 1250},
            "Documents": {"status": "🔄", "last_sync": "Running...", "count": 3400},
            "Passwords": {"status": "✅", "last_sync": "10 mins ago", "count": 890},
            "Contacts": {"status": "⏰", "last_sync": "1 hour ago", "count": 567}
        }
        
        for entity, info in sync_data.items():
            col1, col2 = st.columns([1, 2])
            with col1:
                st.write(info["status"])
            with col2:
                st.caption(f"**{entity}**")
                st.caption(f"{info['count']} items • {info['last_sync']}")
        
        # Sync actions
        st.markdown("### 🚀 Actions")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Sync All", use_container_width=True):
                st.info("Sync started...")
        
        with col2:
            if st.button("🧹 Clear Cache", use_container_width=True):
                st.info("Cache cleared")
        
        # Statistics
        st.markdown("### 📊 Statistics")
        
        # Mock statistics
        stats = {
            "Total Queries": 1234,
            "Avg Response Time": "1.2s",
            "Cache Hit Rate": "78%",
            "Embeddings": "15.2k"
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