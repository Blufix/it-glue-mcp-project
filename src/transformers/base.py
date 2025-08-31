"""Base transformer classes for data transformation pipeline."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TypeVar, Generic
from datetime import datetime
import logging

from src.services.itglue.models import ITGlueModel

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=ITGlueModel)


class BaseTransformer(ABC, Generic[T]):
    """Base class for all data transformers."""
    
    @abstractmethod
    async def transform(self, data: Dict[str, Any]) -> T:
        """Transform raw data to model instance.
        
        Args:
            data: Raw data from IT Glue API
            
        Returns:
            Transformed model instance
        """
        pass
    
    @abstractmethod
    async def transform_batch(self, data_list: List[Dict[str, Any]]) -> List[T]:
        """Transform batch of raw data.
        
        Args:
            data_list: List of raw data items
            
        Returns:
            List of transformed model instances
        """
        pass
    
    def extract_attributes(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract attributes from IT Glue API response.
        
        Args:
            data: Raw API response
            
        Returns:
            Extracted attributes
        """
        # IT Glue API structure: {"data": {"id": "...", "type": "...", "attributes": {...}}}
        if isinstance(data, dict):
            if "attributes" in data:
                return data["attributes"]
            elif "data" in data and isinstance(data["data"], dict):
                return data["data"].get("attributes", {})
        return data
    
    def extract_relationships(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relationships from IT Glue API response.
        
        Args:
            data: Raw API response
            
        Returns:
            Extracted relationships
        """
        if isinstance(data, dict):
            if "relationships" in data:
                return data["relationships"]
            elif "data" in data and isinstance(data["data"], dict):
                return data["data"].get("relationships", {})
        return {}
    
    def extract_id(self, data: Dict[str, Any]) -> str:
        """Extract ID from IT Glue API response.
        
        Args:
            data: Raw API response
            
        Returns:
            Entity ID
        """
        if isinstance(data, dict):
            if "id" in data:
                return str(data["id"])
            elif "data" in data and isinstance(data["data"], dict):
                return str(data["data"].get("id", ""))
        return ""
    
    def extract_type(self, data: Dict[str, Any]) -> str:
        """Extract type from IT Glue API response.
        
        Args:
            data: Raw API response
            
        Returns:
            Entity type
        """
        if isinstance(data, dict):
            if "type" in data:
                return data["type"]
            elif "data" in data and isinstance(data["data"], dict):
                return data["data"].get("type", "")
        return ""
    
    def clean_text(self, text: Optional[str]) -> str:
        """Clean and normalize text data.
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        # Remove null characters
        text = text.replace("\x00", "")
        
        # Trim
        text = text.strip()
        
        return text
    
    def parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from various formats.
        
        Args:
            date_str: Date string
            
        Returns:
            Parsed datetime or None
        """
        if not date_str:
            return None
        
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def safe_get(
        self,
        data: Dict[str, Any],
        path: str,
        default: Any = None
    ) -> Any:
        """Safely get nested value from dictionary.
        
        Args:
            data: Dictionary to search
            path: Dot-separated path (e.g., "attributes.name")
            default: Default value if path not found
            
        Returns:
            Value at path or default
        """
        keys = path.split(".")
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        
        return value


class TransformationPipeline:
    """Pipeline for chaining transformers."""
    
    def __init__(self):
        """Initialize transformation pipeline."""
        self.transformers: List[BaseTransformer] = []
        self.error_handler: Optional[callable] = None
        
    def add_transformer(self, transformer: BaseTransformer) -> 'TransformationPipeline':
        """Add transformer to pipeline.
        
        Args:
            transformer: Transformer to add
            
        Returns:
            Self for chaining
        """
        self.transformers.append(transformer)
        return self
    
    def set_error_handler(self, handler: callable) -> 'TransformationPipeline':
        """Set error handler for pipeline.
        
        Args:
            handler: Error handler function
            
        Returns:
            Self for chaining
        """
        self.error_handler = handler
        return self
    
    async def process(self, data: Any) -> Any:
        """Process data through pipeline.
        
        Args:
            data: Input data
            
        Returns:
            Transformed data
        """
        result = data
        
        for transformer in self.transformers:
            try:
                if isinstance(result, list):
                    result = await transformer.transform_batch(result)
                else:
                    result = await transformer.transform(result)
            except Exception as e:
                logger.error(f"Transformation error in {transformer.__class__.__name__}: {e}")
                
                if self.error_handler:
                    result = self.error_handler(result, e)
                else:
                    raise
        
        return result


class ValidationTransformer(BaseTransformer):
    """Transformer that validates data during transformation."""
    
    def __init__(self, validator: Optional[callable] = None):
        """Initialize validation transformer.
        
        Args:
            validator: Validation function
        """
        self.validator = validator
        
    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform and validate data.
        
        Args:
            data: Raw data
            
        Returns:
            Validated data
        """
        if self.validator:
            if not self.validator(data):
                raise ValueError(f"Data validation failed: {data}")
        
        return data
    
    async def transform_batch(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform and validate batch.
        
        Args:
            data_list: List of raw data items
            
        Returns:
            List of validated data items
        """
        validated = []
        
        for item in data_list:
            try:
                validated_item = await self.transform(item)
                validated.append(validated_item)
            except ValueError as e:
                logger.warning(f"Skipping invalid item: {e}")
                continue
        
        return validated