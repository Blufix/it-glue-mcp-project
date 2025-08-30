"""Base tool class for MCP tools."""

import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Base class for all MCP tools."""
    
    def __init__(self, name: str, description: str):
        """Initialize base tool.
        
        Args:
            name: Tool name
            description: Tool description
        """
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"mcp.tools.{name}")
        
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool.
        
        Args:
            **kwargs: Tool-specific arguments
            
        Returns:
            Tool execution result
        """
        pass
        
    def validate_params(self, params: Dict[str, Any], required: list) -> Optional[str]:
        """Validate required parameters.
        
        Args:
            params: Parameters to validate
            required: List of required parameter names
            
        Returns:
            Error message if validation fails, None otherwise
        """
        missing = [p for p in required if p not in params or params[p] is None]
        
        if missing:
            return f"Missing required parameters: {', '.join(missing)}"
            
        return None
        
    def format_success(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Format successful response.
        
        Args:
            data: Response data
            **kwargs: Additional response fields
            
        Returns:
            Formatted response
        """
        response = {
            "success": True,
            "tool": self.name,
            "data": data
        }
        response.update(kwargs)
        return response
        
    def format_error(self, error: str, **kwargs) -> Dict[str, Any]:
        """Format error response.
        
        Args:
            error: Error message
            **kwargs: Additional response fields
            
        Returns:
            Formatted error response
        """
        response = {
            "success": False,
            "tool": self.name,
            "error": error
        }
        response.update(kwargs)
        return response