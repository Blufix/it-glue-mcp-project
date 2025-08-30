# Frontend Architecture Document

## Executive Summary

This document outlines the frontend architecture for the IT Glue MCP Server, focusing on a Streamlit-based MVP that provides an intuitive natural language interface for querying IT documentation. The architecture prioritizes rapid development, real-time responsiveness, and zero-hallucination accuracy while maintaining a clear path to production-grade React/Next.js implementation.

## Architecture Overview

### Technology Stack Decision

**MVP Phase: Streamlit**
- **Rationale**: Rapid prototyping, Python ecosystem integration, built-in session management
- **Timeline**: 2-3 weeks to functional MVP
- **Limitations**: Single-page application, limited customization

**Production Phase: React + Next.js**
- **Rationale**: Full control, component reusability, better performance, SSR capabilities
- **Timeline**: Phase 2 (months 2-3)
- **Benefits**: Rich interactions, mobile responsiveness, offline capabilities

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   User Interface Layer                   │
├─────────────────────────────────────────────────────────┤
│  Streamlit MVP                │  Future: React/Next.js   │
│  ┌─────────────────────────┐  │  ┌────────────────────┐ │
│  │   Chat Interface        │  │  │  Component Library │ │
│  │   Company Selector      │  │  │  State Management  │ │
│  │   Results Display       │  │  │  Router           │ │
│  │   Admin Panel          │  │  │  Service Workers   │ │
│  └─────────────────────────┘  │  └────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│                  Communication Layer                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │  WebSocket (Real-time)  │  REST API  │  SSE     │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│                    State Management                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Session State  │  Query Cache  │  UI State     │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Streamlit MVP Architecture

### Component Structure

```python
# src/ui/streamlit_app.py
"""Main Streamlit application"""

import streamlit as st
from typing import Optional, Dict, List
import asyncio
from datetime import datetime

from src.ui.components.chat import ChatInterface
from src.ui.components.company_selector import CompanySelector
from src.ui.components.results_display import ResultsDisplay
from src.ui.components.admin_panel import AdminPanel
from src.ui.services.mcp_client import MCPClient
from src.ui.services.state_manager import StateManager
from src.ui.utils.auth import check_authentication

# Page configuration
st.set_page_config(
    page_title="IT Glue Intelligent Query",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

class ITGlueQueryApp:
    """Main application class"""
    
    def __init__(self):
        self.mcp_client = MCPClient()
        self.state_manager = StateManager()
        self._initialize_session_state()
        
    def _initialize_session_state(self):
        """Initialize Streamlit session state"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'selected_company' not in st.session_state:
            st.session_state.selected_company = None
        if 'query_history' not in st.session_state:
            st.session_state.query_history = []
        if 'current_results' not in st.session_state:
            st.session_state.current_results = None
            
    def run(self):
        """Main application entry point"""
        
        # Authentication check
        if not st.session_state.authenticated:
            self._render_login()
            return
            
        # Sidebar
        with st.sidebar:
            self._render_sidebar()
            
        # Main content area
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self._render_main_interface()
            
        with col2:
            self._render_context_panel()
            
    def _render_sidebar(self):
        """Render sidebar components"""
        st.title("🔍 IT Glue Query")
        
        # Company selector
        company = CompanySelector().render()
        if company != st.session_state.selected_company:
            st.session_state.selected_company = company
            st.rerun()
            
        st.divider()
        
        # Quick actions
        st.subheader("Quick Actions")
        if st.button("🔄 Sync Data"):
            self._trigger_sync()
        if st.button("📊 View Stats"):
            self._show_statistics()
            
        # Admin section
        if st.session_state.user_role == "admin":
            st.divider()
            AdminPanel().render()
            
    def _render_main_interface(self):
        """Render main chat interface"""
        st.header("Natural Language Query")
        
        # Chat interface
        chat = ChatInterface(
            mcp_client=self.mcp_client,
            company_id=st.session_state.selected_company
        )
        
        query = chat.render_input()
        
        if query:
            with st.spinner("Searching documentation..."):
                results = asyncio.run(
                    self.mcp_client.query(
                        query=query,
                        company_id=st.session_state.selected_company
                    )
                )
                
            if results.success:
                ResultsDisplay().render(results.data)
                st.session_state.current_results = results
            else:
                st.error(f"❌ {results.error}")
                
        # Query history
        chat.render_history(st.session_state.query_history)
```

### Key Components

#### 1. Chat Interface Component

```python
# src/ui/components/chat.py
"""Chat interface component"""

import streamlit as st
from typing import Optional, List, Dict
import time
from datetime import datetime

class ChatInterface:
    """Manages chat UI and interactions"""
    
    def __init__(self, mcp_client, company_id: Optional[str] = None):
        self.mcp_client = mcp_client
        self.company_id = company_id
        
    def render_input(self) -> Optional[str]:
        """Render query input area"""
        
        # Query input with examples
        query = st.text_input(
            "Ask a question about IT documentation:",
            placeholder="e.g., What's the router IP? Show me printer configuration",
            key="query_input"
        )
        
        # Suggested queries
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📍 Router IP", use_container_width=True):
                return "What is the router IP address?"
                
        with col2:
            if st.button("🖨️ Printers", use_container_width=True):
                return "Show printer configurations"
                
        with col3:
            if st.button("🔒 Passwords", use_container_width=True):
                return "List all password categories"
                
        return query if query else None
        
    def render_history(self, history: List[Dict]):
        """Render conversation history"""
        
        if not history:
            return
            
        st.subheader("Recent Queries")
        
        for item in reversed(history[-5:]):
            with st.expander(
                f"🕐 {item['timestamp']} - {item['query'][:50]}...",
                expanded=False
            ):
                st.write(f"**Query:** {item['query']}")
                st.write(f"**Company:** {item['company']}")
                
                if item['success']:
                    st.success("✅ Found results")
                    st.json(item['results'])
                else:
                    st.error(f"❌ {item['error']}")
                    
    def render_typing_indicator(self):
        """Show typing/processing indicator"""
        
        placeholder = st.empty()
        
        for i in range(3):
            placeholder.markdown(f"{'.' * (i + 1)}")
            time.sleep(0.3)
            
        placeholder.empty()
```

#### 2. Company Selector Component

```python
# src/ui/components/company_selector.py
"""Company selector component"""

import streamlit as st
from typing import Optional, List
import asyncio

class CompanySelector:
    """Company selection widget"""
    
    def __init__(self):
        self.companies = self._load_companies()
        
    def _load_companies(self) -> List[Dict]:
        """Load available companies"""
        # In production, this would fetch from API
        return [
            {"id": "comp-1", "name": "Company A", "type": "Customer"},
            {"id": "comp-2", "name": "Company B", "type": "Customer"},
            {"id": "comp-3", "name": "Internal", "type": "Internal"},
        ]
        
    def render(self) -> Optional[str]:
        """Render company selector"""
        
        st.subheader("Select Company")
        
        # Search filter
        search = st.text_input(
            "Search companies",
            key="company_search",
            label_visibility="collapsed"
        )
        
        # Filter companies
        filtered = [
            c for c in self.companies
            if not search or search.lower() in c['name'].lower()
        ]
        
        # Company selection
        if filtered:
            company_names = [c['name'] for c in filtered]
            selected_name = st.selectbox(
                "Company",
                options=company_names,
                key="company_select",
                label_visibility="collapsed"
            )
            
            # Get selected company ID
            selected = next(
                (c for c in filtered if c['name'] == selected_name),
                None
            )
            
            if selected:
                st.caption(f"Type: {selected['type']}")
                return selected['id']
                
        else:
            st.warning("No companies found")
            return None
            
    def render_multi_select(self) -> List[str]:
        """Render multi-company selector for cross-company search"""
        
        st.subheader("Select Companies")
        
        company_names = [c['name'] for c in self.companies]
        selected_names = st.multiselect(
            "Select companies for cross-company search",
            options=company_names,
            default=[],
            key="multi_company_select"
        )
        
        # Get selected IDs
        selected_ids = [
            c['id'] for c in self.companies
            if c['name'] in selected_names
        ]
        
        return selected_ids
```

#### 3. Results Display Component

```python
# src/ui/components/results_display.py
"""Results display component"""

import streamlit as st
from typing import Any, Dict, List
import json
import pandas as pd

class ResultsDisplay:
    """Display query results in various formats"""
    
    def render(self, data: Any):
        """Render results based on data type"""
        
        if data is None:
            st.info("No data available")
            return
            
        # Determine result type and render appropriately
        if isinstance(data, dict):
            self._render_dict_result(data)
        elif isinstance(data, list):
            self._render_list_result(data)
        elif isinstance(data, str):
            self._render_text_result(data)
        else:
            self._render_json_result(data)
            
    def _render_dict_result(self, data: Dict):
        """Render dictionary results"""
        
        # Check for special result types
        if 'password' in data:
            self._render_password_result(data)
        elif 'configuration' in data:
            self._render_configuration_result(data)
        elif 'document' in data:
            self._render_document_result(data)
        else:
            # Generic dictionary display
            for key, value in data.items():
                if key == 'password_encrypted':
                    st.text_input(key, value="•" * 10, disabled=True)
                else:
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                    
    def _render_password_result(self, data: Dict):
        """Render password with security"""
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader("🔒 Password Entry")
            st.write(f"**Name:** {data.get('name', 'N/A')}")
            st.write(f"**Username:** {data.get('username', 'N/A')}")
            st.write(f"**Category:** {data.get('category', 'N/A')}")
            
            if data.get('url'):
                st.write(f"**URL:** {data['url']}")
                
        with col2:
            if st.button("📋 Copy Password", key=f"copy_{data.get('id')}"):
                # In production, this would decrypt and copy
                st.success("Password copied!")
                
            if st.button("👁️ Show Password", key=f"show_{data.get('id')}"):
                # In production, this would decrypt and show
                st.text_input("Password", value="•" * 10, disabled=True)
                
    def _render_configuration_result(self, data: Dict):
        """Render configuration details"""
        
        st.subheader(f"⚙️ {data.get('name', 'Configuration')}")
        
        # Create tabs for different sections
        tabs = st.tabs(["General", "Network", "Notes"])
        
        with tabs[0]:
            st.write(f"**Type:** {data.get('type', 'N/A')}")
            st.write(f"**Serial:** {data.get('serial_number', 'N/A')}")
            st.write(f"**OS:** {data.get('operating_system', 'N/A')}")
            
        with tabs[1]:
            st.write(f"**IP Address:** `{data.get('ip_address', 'N/A')}`")
            st.write(f"**MAC Address:** `{data.get('mac_address', 'N/A')}`")
            
        with tabs[2]:
            st.text_area(
                "Notes",
                value=data.get('notes', 'No notes available'),
                height=100,
                disabled=True
            )
            
    def _render_list_result(self, data: List):
        """Render list results"""
        
        if not data:
            st.info("No results found")
            return
            
        # Check if it's a list of similar items
        if all(isinstance(item, dict) for item in data):
            # Try to display as table
            df = pd.DataFrame(data)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
        else:
            # Display as bullet list
            for item in data:
                st.write(f"• {item}")
                
    def _render_document_result(self, data: Dict):
        """Render document content"""
        
        st.subheader(f"📄 {data.get('name', 'Document')}")
        
        # Document metadata
        with st.expander("Document Info"):
            st.write(f"**Type:** {data.get('type', 'N/A')}")
            st.write(f"**Created:** {data.get('created_at', 'N/A')}")
            st.write(f"**Updated:** {data.get('updated_at', 'N/A')}")
            
        # Document content
        content = data.get('content', 'No content available')
        
        # Check if markdown
        if content.startswith('#') or '```' in content:
            st.markdown(content)
        else:
            st.text_area(
                "Content",
                value=content,
                height=300,
                disabled=True
            )
            
    def _render_text_result(self, data: str):
        """Render plain text result"""
        st.text(data)
        
    def _render_json_result(self, data: Any):
        """Render as JSON"""
        st.json(data)
```

### State Management

```python
# src/ui/services/state_manager.py
"""Application state management"""

import streamlit as st
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import hashlib

class StateManager:
    """Manages application state and caching"""
    
    def __init__(self):
        self._initialize_state()
        
    def _initialize_state(self):
        """Initialize default state values"""
        
        defaults = {
            'user': None,
            'authenticated': False,
            'selected_company': None,
            'query_history': [],
            'cache': {},
            'preferences': {
                'theme': 'light',
                'results_per_page': 10,
                'auto_refresh': False
            },
            'active_filters': {},
            'session_id': self._generate_session_id()
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
                
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        
        timestamp = datetime.utcnow().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:8]
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get state value"""
        return st.session_state.get(key, default)
        
    def set(self, key: str, value: Any):
        """Set state value"""
        st.session_state[key] = value
        
    def add_to_history(
        self,
        query: str,
        results: Any,
        company_id: str
    ):
        """Add query to history"""
        
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'query': query,
            'company': company_id,
            'success': results.success if hasattr(results, 'success') else False,
            'results': results.data if hasattr(results, 'data') else None,
            'error': results.error if hasattr(results, 'error') else None
        }
        
        st.session_state.query_history.append(entry)
        
        # Limit history size
        if len(st.session_state.query_history) > 50:
            st.session_state.query_history = st.session_state.query_history[-50:]
            
    def cache_result(
        self,
        query: str,
        company_id: str,
        result: Any,
        ttl_minutes: int = 5
    ):
        """Cache query result"""
        
        cache_key = self._generate_cache_key(query, company_id)
        
        st.session_state.cache[cache_key] = {
            'result': result,
            'timestamp': datetime.utcnow(),
            'ttl': ttl_minutes
        }
        
        # Clean expired cache entries
        self._clean_cache()
        
    def get_cached_result(
        self,
        query: str,
        company_id: str
    ) -> Optional[Any]:
        """Get cached result if available"""
        
        cache_key = self._generate_cache_key(query, company_id)
        cached = st.session_state.cache.get(cache_key)
        
        if cached:
            # Check if expired
            age = datetime.utcnow() - cached['timestamp']
            if age < timedelta(minutes=cached['ttl']):
                return cached['result']
            else:
                # Remove expired entry
                del st.session_state.cache[cache_key]
                
        return None
        
    def _generate_cache_key(self, query: str, company_id: str) -> str:
        """Generate cache key from query and company"""
        
        combined = f"{query}:{company_id}"
        return hashlib.md5(combined.encode()).hexdigest()
        
    def _clean_cache(self):
        """Remove expired cache entries"""
        
        now = datetime.utcnow()
        expired_keys = []
        
        for key, entry in st.session_state.cache.items():
            age = now - entry['timestamp']
            if age >= timedelta(minutes=entry['ttl']):
                expired_keys.append(key)
                
        for key in expired_keys:
            del st.session_state.cache[key]
```

### MCP Client Integration

```python
# src/ui/services/mcp_client.py
"""MCP client for frontend communication"""

import asyncio
from typing import Optional, Dict, Any, List
import json
import websockets
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    """Query result structure"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    source: Optional[str] = None
    execution_time_ms: Optional[float] = None
    confidence_score: Optional[float] = None

class MCPClient:
    """Client for MCP server communication"""
    
    def __init__(
        self,
        server_url: str = "ws://localhost:8000",
        timeout: int = 30
    ):
        self.server_url = server_url
        self.timeout = timeout
        self.connection = None
        
    async def connect(self):
        """Establish WebSocket connection"""
        
        try:
            self.connection = await websockets.connect(
                self.server_url,
                ping_interval=20,
                ping_timeout=10
            )
            logger.info("Connected to MCP server")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise
            
    async def disconnect(self):
        """Close WebSocket connection"""
        
        if self.connection:
            await self.connection.close()
            self.connection = None
            
    async def query(
        self,
        query: str,
        company_id: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> QueryResult:
        """Send query to MCP server"""
        
        if not self.connection:
            await self.connect()
            
        # Prepare request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "query",
                "arguments": {
                    "query": query,
                    "company": company_id,
                    "options": options or {}
                }
            },
            "id": 1
        }
        
        try:
            # Send request
            await self.connection.send(json.dumps(request))
            
            # Wait for response with timeout
            response_text = await asyncio.wait_for(
                self.connection.recv(),
                timeout=self.timeout
            )
            
            response = json.loads(response_text)
            
            # Parse response
            if "result" in response:
                result_data = response["result"]
                return QueryResult(
                    success=result_data.get("success", False),
                    data=result_data.get("data"),
                    error=result_data.get("error"),
                    source=result_data.get("source"),
                    execution_time_ms=result_data.get("execution_time_ms"),
                    confidence_score=result_data.get("confidence_score")
                )
            elif "error" in response:
                return QueryResult(
                    success=False,
                    error=response["error"].get("message", "Unknown error")
                )
            else:
                return QueryResult(
                    success=False,
                    error="Invalid response format"
                )
                
        except asyncio.TimeoutError:
            return QueryResult(
                success=False,
                error=f"Query timeout after {self.timeout} seconds"
            )
        except Exception as e:
            logger.error(f"Query error: {e}")
            return QueryResult(
                success=False,
                error=str(e)
            )
            
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Cross-company search"""
        
        if not self.connection:
            await self.connect()
            
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {
                    "query": query,
                    "limit": limit,
                    "filters": filters or {}
                }
            },
            "id": 2
        }
        
        try:
            await self.connection.send(json.dumps(request))
            response_text = await asyncio.wait_for(
                self.connection.recv(),
                timeout=self.timeout
            )
            
            response = json.loads(response_text)
            
            if "result" in response:
                return response["result"].get("results", [])
            else:
                return []
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
```

## User Experience Flows

### Primary User Flow: Quick Query

```mermaid
graph TD
    A[User Opens App] --> B[Select Company]
    B --> C[Type Natural Language Query]
    C --> D[System Processes Query]
    D --> E{Results Found?}
    E -->|Yes| F[Display Results]
    E -->|No| G[Show "No Data Available"]
    F --> H[User Actions]
    H --> I[Copy/Export Data]
    H --> J[Ask Follow-up Question]
    H --> K[View Related Info]
```

### Search Flow

1. **Company Selection**
   - Auto-complete search
   - Recent companies
   - Multi-select for cross-company

2. **Query Input**
   - Natural language text box
   - Suggested queries based on context
   - Query templates for common searches

3. **Results Display**
   - Instant results (<2 seconds)
   - Categorized by type (passwords, configs, docs)
   - Inline actions (copy, export, navigate)

4. **Refinement**
   - Filter results
   - Sort options
   - Related queries suggestions

## Responsive Design

### Mobile Considerations

```python
# src/ui/utils/responsive.py
"""Responsive design utilities"""

import streamlit as st

def get_device_type() -> str:
    """Detect device type from viewport"""
    
    # Streamlit doesn't directly provide viewport info
    # This is a simplified approach
    
    # In production, would use JavaScript injection
    return "desktop"  # Default for MVP

def responsive_columns(desktop: List[int], mobile: List[int]) -> tuple:
    """Create responsive column layout"""
    
    device = get_device_type()
    
    if device == "mobile":
        return st.columns(mobile)
    else:
        return st.columns(desktop)

def responsive_container(content_func, mobile_view_func=None):
    """Render content responsively"""
    
    device = get_device_type()
    
    if device == "mobile" and mobile_view_func:
        mobile_view_func()
    else:
        content_func()
```

### Accessibility Features

```python
# src/ui/utils/accessibility.py
"""Accessibility utilities"""

import streamlit as st
from typing import Optional

def accessible_button(
    label: str,
    key: Optional[str] = None,
    help_text: Optional[str] = None,
    **kwargs
) -> bool:
    """Create accessible button with ARIA labels"""
    
    # Streamlit limitation: Can't directly add ARIA labels
    # Workaround: Use help parameter for screen readers
    
    return st.button(
        label,
        key=key,
        help=help_text or f"Button: {label}",
        **kwargs
    )

def accessible_input(
    label: str,
    key: Optional[str] = None,
    description: Optional[str] = None,
    **kwargs
) -> str:
    """Create accessible input field"""
    
    if description:
        st.caption(description)
        
    return st.text_input(
        label,
        key=key,
        **kwargs
    )

def high_contrast_mode():
    """Apply high contrast theme"""
    
    st.markdown("""
    <style>
    .stApp {
        background-color: #000000;
        color: #FFFFFF;
    }
    .stButton > button {
        background-color: #FFFFFF;
        color: #000000;
        border: 2px solid #FFFFFF;
    }
    .stTextInput > div > div > input {
        background-color: #000000;
        color: #FFFFFF;
        border: 2px solid #FFFFFF;
    }
    </style>
    """, unsafe_allow_html=True)
```

## Performance Optimization

### Caching Strategy

```python
# src/ui/utils/cache.py
"""Frontend caching utilities"""

import streamlit as st
from typing import Any, Optional
import hashlib
import pickle
from datetime import datetime, timedelta

class FrontendCache:
    """Browser-side caching for Streamlit"""
    
    @staticmethod
    @st.cache_data(ttl=300)  # 5 minutes
    def cache_query_result(
        query: str,
        company_id: str
    ) -> Optional[Any]:
        """Cache query results"""
        
        # This decorator automatically handles caching
        return None
        
    @staticmethod
    @st.cache_resource
    def get_mcp_client():
        """Cache MCP client connection"""
        
        from src.ui.services.mcp_client import MCPClient
        return MCPClient()
        
    @staticmethod
    @st.cache_data(ttl=900)  # 15 minutes
    def load_companies():
        """Cache company list"""
        
        # In production, fetch from API
        return [
            {"id": "1", "name": "Company A"},
            {"id": "2", "name": "Company B"}
        ]
        
    @staticmethod
    def invalidate_cache(key: Optional[str] = None):
        """Invalidate cache entries"""
        
        if key:
            st.cache_data.clear()
        else:
            # Clear specific key if Streamlit supports it
            st.cache_data.clear()
```

### Lazy Loading

```python
# src/ui/utils/lazy_load.py
"""Lazy loading utilities"""

import streamlit as st
from typing import List, Any, Callable
import asyncio

class LazyLoader:
    """Implement lazy loading for large datasets"""
    
    def __init__(self, page_size: int = 20):
        self.page_size = page_size
        
    def render_paginated(
        self,
        data: List[Any],
        render_func: Callable,
        key_prefix: str = "page"
    ):
        """Render data with pagination"""
        
        total_items = len(data)
        total_pages = (total_items + self.page_size - 1) // self.page_size
        
        # Page selector
        if total_pages > 1:
            page = st.selectbox(
                "Page",
                options=range(1, total_pages + 1),
                key=f"{key_prefix}_selector"
            )
        else:
            page = 1
            
        # Calculate slice
        start_idx = (page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, total_items)
        
        # Render current page
        for item in data[start_idx:end_idx]:
            render_func(item)
            
        # Page info
        if total_pages > 1:
            st.caption(
                f"Showing {start_idx + 1}-{end_idx} of {total_items} items"
            )
            
    def render_infinite_scroll(
        self,
        fetch_func: Callable,
        render_func: Callable,
        key: str = "infinite"
    ):
        """Render with infinite scroll simulation"""
        
        if f"{key}_offset" not in st.session_state:
            st.session_state[f"{key}_offset"] = 0
            st.session_state[f"{key}_data"] = []
            
        # Load more button
        if st.button("Load More", key=f"{key}_load_more"):
            offset = st.session_state[f"{key}_offset"]
            
            with st.spinner("Loading..."):
                new_data = fetch_func(offset, self.page_size)
                st.session_state[f"{key}_data"].extend(new_data)
                st.session_state[f"{key}_offset"] += self.page_size
                
        # Render all loaded data
        for item in st.session_state[f"{key}_data"]:
            render_func(item)
```

## Security Considerations

### Authentication Flow

```python
# src/ui/utils/auth.py
"""Authentication utilities"""

import streamlit as st
from typing import Optional, Dict
import jwt
import requests
from datetime import datetime, timedelta

class AuthManager:
    """Manage user authentication"""
    
    def __init__(self, api_url: str):
        self.api_url = api_url
        
    def render_login_form(self) -> bool:
        """Render login form"""
        
        st.title("🔐 IT Glue Query Login")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            api_key = st.text_input(
                "Or use API Key",
                type="password",
                help="Enter your IT Glue API key for direct access"
            )
            
            submitted = st.form_submit_button("Login")
            
            if submitted:
                if api_key:
                    return self.authenticate_with_api_key(api_key)
                else:
                    return self.authenticate_with_credentials(
                        username,
                        password
                    )
                    
        return False
        
    def authenticate_with_credentials(
        self,
        username: str,
        password: str
    ) -> bool:
        """Authenticate with username/password"""
        
        try:
            response = requests.post(
                f"{self.api_url}/auth/login",
                json={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                self._store_auth_token(data["token"])
                self._store_user_info(data["user"])
                return True
            else:
                st.error("Invalid credentials")
                return False
                
        except Exception as e:
            st.error(f"Authentication error: {e}")
            return False
            
    def authenticate_with_api_key(self, api_key: str) -> bool:
        """Authenticate with API key"""
        
        try:
            response = requests.post(
                f"{self.api_url}/auth/api-key",
                headers={"X-API-Key": api_key}
            )
            
            if response.status_code == 200:
                data = response.json()
                st.session_state.api_key = api_key
                st.session_state.authenticated = True
                st.session_state.user = data.get("user", {})
                return True
            else:
                st.error("Invalid API key")
                return False
                
        except Exception as e:
            st.error(f"Authentication error: {e}")
            return False
            
    def _store_auth_token(self, token: str):
        """Store JWT token in session"""
        
        st.session_state.auth_token = token
        st.session_state.authenticated = True
        
        # Decode token for expiry
        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )
            st.session_state.token_expiry = datetime.fromtimestamp(
                payload.get("exp", 0)
            )
        except Exception:
            pass
            
    def _store_user_info(self, user: Dict):
        """Store user information"""
        
        st.session_state.user = user
        st.session_state.user_role = user.get("role", "user")
        
    def check_authentication(self) -> bool:
        """Check if user is authenticated"""
        
        if not st.session_state.get("authenticated", False):
            return False
            
        # Check token expiry
        if "token_expiry" in st.session_state:
            if datetime.utcnow() >= st.session_state.token_expiry:
                self.logout()
                return False
                
        return True
        
    def logout(self):
        """Log out user"""
        
        for key in ["authenticated", "auth_token", "user", "api_key"]:
            if key in st.session_state:
                del st.session_state[key]
                
        st.rerun()
```

### Input Sanitization

```python
# src/ui/utils/sanitization.py
"""Input sanitization utilities"""

import re
from typing import Any
import html

class InputSanitizer:
    """Sanitize user inputs"""
    
    @staticmethod
    def sanitize_query(query: str) -> str:
        """Sanitize search query"""
        
        # Remove potential SQL injection attempts
        sql_keywords = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE',
            'CREATE', 'ALTER', 'EXEC', 'UNION'
        ]
        
        for keyword in sql_keywords:
            query = re.sub(
                rf'\b{keyword}\b',
                '',
                query,
                flags=re.IGNORECASE
            )
            
        # Remove HTML/Script tags
        query = re.sub(r'<[^>]+>', '', query)
        
        # Escape special characters
        query = html.escape(query)
        
        # Limit length
        return query[:500]
        
    @staticmethod
    def sanitize_company_id(company_id: str) -> str:
        """Sanitize company ID"""
        
        # Allow only alphanumeric and hyphens
        return re.sub(r'[^a-zA-Z0-9-]', '', company_id)[:50]
        
    @staticmethod
    def validate_json(data: Any) -> bool:
        """Validate JSON structure"""
        
        try:
            import json
            json.dumps(data)
            return True
        except (TypeError, ValueError):
            return False
```

## Testing Strategy

### Component Testing

```python
# tests/ui/test_components.py
"""UI component tests"""

import pytest
from unittest.mock import Mock, patch
import streamlit as st
from src.ui.components.chat import ChatInterface
from src.ui.components.company_selector import CompanySelector

class TestChatInterface:
    """Test chat interface component"""
    
    @patch('streamlit.text_input')
    def test_render_input(self, mock_input):
        """Test query input rendering"""
        
        mock_input.return_value = "Test query"
        
        chat = ChatInterface(Mock(), "company-1")
        result = chat.render_input()
        
        assert result == "Test query"
        mock_input.assert_called_once()
        
    @patch('streamlit.button')
    def test_suggested_queries(self, mock_button):
        """Test suggested query buttons"""
        
        mock_button.side_effect = [True, False, False]
        
        chat = ChatInterface(Mock(), "company-1")
        result = chat.render_input()
        
        assert result == "What is the router IP address?"
        
    def test_render_history_empty(self):
        """Test empty history rendering"""
        
        chat = ChatInterface(Mock(), "company-1")
        
        # Should not raise error
        chat.render_history([])
        
    @patch('streamlit.expander')
    def test_render_history_with_items(self, mock_expander):
        """Test history rendering with items"""
        
        history = [
            {
                'timestamp': '2024-01-01T12:00:00',
                'query': 'Test query',
                'company': 'Company A',
                'success': True,
                'results': {'data': 'test'}
            }
        ]
        
        chat = ChatInterface(Mock(), "company-1")
        chat.render_history(history)
        
        mock_expander.assert_called_once()
```

### Integration Testing

```python
# tests/ui/test_integration.py
"""UI integration tests"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.ui.services.mcp_client import MCPClient, QueryResult

class TestMCPClient:
    """Test MCP client integration"""
    
    @pytest.mark.asyncio
    async def test_successful_query(self):
        """Test successful query flow"""
        
        client = MCPClient("ws://localhost:8000")
        
        # Mock WebSocket connection
        with patch('websockets.connect') as mock_connect:
            mock_ws = AsyncMock()
            mock_ws.recv.return_value = json.dumps({
                "jsonrpc": "2.0",
                "result": {
                    "success": True,
                    "data": {"router_ip": "192.168.1.1"}
                },
                "id": 1
            })
            mock_connect.return_value = mock_ws
            
            result = await client.query(
                "What is the router IP?",
                "company-1"
            )
            
            assert result.success is True
            assert result.data["router_ip"] == "192.168.1.1"
            
    @pytest.mark.asyncio
    async def test_query_timeout(self):
        """Test query timeout handling"""
        
        client = MCPClient("ws://localhost:8000", timeout=1)
        
        with patch('websockets.connect') as mock_connect:
            mock_ws = AsyncMock()
            mock_ws.recv.side_effect = asyncio.TimeoutError()
            mock_connect.return_value = mock_ws
            
            result = await client.query("Test query", "company-1")
            
            assert result.success is False
            assert "timeout" in result.error.lower()
```

## Migration Path to React

### Phase 2: React Architecture

```typescript
// src/frontend/architecture.ts
/**
 * Future React/Next.js architecture
 */

interface FrontendArchitecture {
  framework: 'Next.js 14+';
  styling: 'Tailwind CSS + shadcn/ui';
  state: 'Zustand + React Query';
  realtime: 'Socket.io + Server-Sent Events';
  testing: 'Jest + React Testing Library + Playwright';
}

// Component structure
interface ComponentHierarchy {
  app: {
    layout: ['Header', 'Sidebar', 'MainContent', 'Footer'];
    pages: {
      '/': 'HomePage';
      '/query': 'QueryPage';
      '/search': 'SearchPage';
      '/admin': 'AdminPage';
      '/settings': 'SettingsPage';
    };
    components: {
      shared: ['Button', 'Input', 'Card', 'Modal', 'Toast'];
      domain: ['QueryInput', 'ResultCard', 'CompanySelector'];
      features: ['ChatInterface', 'SearchFilters', 'AdminPanel'];
    };
  };
}

// State management
interface StateArchitecture {
  stores: {
    auth: 'Authentication state';
    query: 'Query history and cache';
    ui: 'UI preferences and settings';
    company: 'Selected companies and metadata';
  };
  
  api: {
    queries: 'React Query for API calls';
    websocket: 'Socket.io for real-time';
    cache: 'IndexedDB for offline';
  };
}
```

### Migration Strategy

1. **Phase 2a: Component Library** (Month 2)
   - Build React component library
   - Match Streamlit functionality
   - Establish design system

2. **Phase 2b: Core Features** (Month 3)
   - Implement query interface
   - Add real-time updates
   - Create admin panel

3. **Phase 2c: Enhanced Features** (Month 4)
   - Advanced search filters
   - Batch operations
   - Keyboard shortcuts
   - Mobile app

## Development Guidelines

### Code Organization

```
src/ui/
├── streamlit_app.py           # Main entry point
├── components/                 # UI components
│   ├── __init__.py
│   ├── chat.py                # Chat interface
│   ├── company_selector.py    # Company selection
│   ├── results_display.py     # Results rendering
│   ├── admin_panel.py         # Admin features
│   └── common/                # Shared components
│       ├── loading.py
│       ├── error.py
│       └── empty_state.py
├── services/                   # Business logic
│   ├── __init__.py
│   ├── mcp_client.py          # MCP communication
│   ├── state_manager.py       # State management
│   └── auth_service.py        # Authentication
├── utils/                      # Utilities
│   ├── __init__.py
│   ├── auth.py                # Auth helpers
│   ├── cache.py               # Caching utilities
│   ├── responsive.py          # Responsive design
│   ├── accessibility.py       # A11y utilities
│   ├── sanitization.py        # Input sanitization
│   └── lazy_load.py           # Performance utils
├── pages/                      # Multi-page support
│   ├── __init__.py
│   ├── query.py               # Query page
│   ├── search.py              # Search page
│   └── admin.py               # Admin page
└── config/                     # Configuration
    ├── __init__.py
    ├── theme.py               # UI theme config
    └── settings.py            # App settings
```

### Best Practices

1. **Component Design**
   - Single responsibility
   - Props validation
   - Error boundaries
   - Loading states

2. **State Management**
   - Minimize session state
   - Use caching strategically
   - Clear state on logout
   - Persist preferences

3. **Performance**
   - Lazy load components
   - Cache API responses
   - Debounce user input
   - Virtual scrolling for lists

4. **Security**
   - Sanitize all inputs
   - Validate API responses
   - Use HTTPS in production
   - Implement CSP headers

5. **Accessibility**
   - Keyboard navigation
   - Screen reader support
   - High contrast mode
   - Focus management

## Deployment Configuration

### Streamlit Cloud Deployment

```toml
# .streamlit/config.toml

[theme]
primaryColor = "#1E40AF"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F3F4F6"
textColor = "#1F2937"
font = "sans serif"

[server]
port = 8501
enableCORS = false
enableXsrfProtection = true
maxUploadSize = 10

[browser]
gatherUsageStats = false
serverPort = 8501

[runner]
magicEnabled = true
installTracer = false
fixMatplotlib = true
```

### Docker Deployment

```dockerfile
# docker/Dockerfile.streamlit
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ui/ ./src/ui/
COPY config/ ./config/

# Environment variables
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run Streamlit
CMD ["streamlit", "run", "src/ui/streamlit_app.py", "--server.baseUrlPath=/"]
```

## Monitoring and Analytics

### User Analytics

```python
# src/ui/utils/analytics.py
"""Analytics tracking"""

import streamlit as st
from typing import Dict, Any
from datetime import datetime
import json

class Analytics:
    """Track user interactions"""
    
    @staticmethod
    def track_event(
        event_name: str,
        properties: Dict[str, Any]
    ):
        """Track analytics event"""
        
        event = {
            'event': event_name,
            'timestamp': datetime.utcnow().isoformat(),
            'session_id': st.session_state.get('session_id'),
            'user_id': st.session_state.get('user', {}).get('id'),
            'properties': properties
        }
        
        # In production, send to analytics service
        # For MVP, log to file
        with open('/tmp/analytics.jsonl', 'a') as f:
            f.write(json.dumps(event) + '\n')
            
    @staticmethod
    def track_query(query: str, company_id: str, success: bool):
        """Track query execution"""
        
        Analytics.track_event('query_executed', {
            'query_length': len(query),
            'company_id': company_id,
            'success': success,
            'response_time_ms': st.session_state.get('last_query_time', 0)
        })
        
    @staticmethod
    def track_page_view(page: str):
        """Track page view"""
        
        Analytics.track_event('page_view', {
            'page': page,
            'referrer': st.session_state.get('previous_page')
        })
```

## Future Enhancements

### Planned Features

1. **Real-time Collaboration**
   - Live query sharing
   - Collaborative annotations
   - Team workspaces

2. **Advanced Visualizations**
   - Network topology diagrams
   - Relationship graphs
   - Timeline views

3. **AI Enhancements**
   - Query suggestions
   - Auto-completion
   - Pattern detection

4. **Mobile Application**
   - Native iOS/Android apps
   - Offline support
   - Push notifications

5. **Integration Expansions**
   - Slack bot interface
   - Teams integration
   - API webhooks

---

**Frontend Architecture Status: COMPLETE**

This frontend architecture provides a comprehensive blueprint for the Streamlit MVP with a clear migration path to React/Next.js for production deployment.