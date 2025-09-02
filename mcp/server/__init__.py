"""MCP Server module stub for testing."""

from typing import Any, Callable, Dict, Optional
import asyncio
from functools import wraps


class Server:
    """Mock MCP Server class."""
    
    def __init__(self, name: str):
        self.name = name
        self.tools = {}
        
    def tool(self, name: Optional[str] = None):
        """Decorator for registering tools."""
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            self.tools[tool_name] = func
            return func
        return decorator
        
    async def run(self):
        """Run the server."""
        pass


class Tool:
    """Mock Tool class."""
    
    def __init__(self, name: str, description: str, handler: Callable):
        self.name = name
        self.description = description
        self.handler = handler