"""Transformers for IT Glue entity types."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.transformers.base import BaseTransformer
from src.services.itglue.models import (
    Organization,
    Configuration,
    FlexibleAsset,
    Password,
    Document,
    Contact,
    Location
)
from src.data.models import ITGlueEntity

logger = logging.getLogger(__name__)


class OrganizationTransformer(BaseTransformer[Organization]):
    """Transform IT Glue organization data."""
    
    async def transform(self, data: Dict[str, Any]) -> Organization:
        """Transform organization data.
        
        Args:
            data: Raw organization data
            
        Returns:
            Organization model instance
        """
        attributes = self.extract_attributes(data)
        
        return Organization(
            id=self.extract_id(data),
            name=self.clean_text(attributes.get("name", "")),
            description=self.clean_text(attributes.get("description", "")),
            organization_type=attributes.get("organization-type-name", ""),
            organization_status=attributes.get("organization-status-name", ""),
            created_at=self.parse_datetime(attributes.get("created-at")),
            updated_at=self.parse_datetime(attributes.get("updated-at")),
            attributes=attributes,
            relationships=self.extract_relationships(data)
        )
    
    async def transform_batch(self, data_list: List[Dict[str, Any]]) -> List[Organization]:
        """Transform batch of organizations.
        
        Args:
            data_list: List of raw organization data
            
        Returns:
            List of Organization instances
        """
        organizations = []
        
        for item in data_list:
            try:
                org = await self.transform(item)
                organizations.append(org)
            except Exception as e:
                logger.error(f"Failed to transform organization: {e}")
                continue
        
        return organizations


class ConfigurationTransformer(BaseTransformer[Configuration]):
    """Transform IT Glue configuration data."""
    
    async def transform(self, data: Dict[str, Any]) -> Configuration:
        """Transform configuration data.
        
        Args:
            data: Raw configuration data
            
        Returns:
            Configuration model instance
        """
        attributes = self.extract_attributes(data)
        relationships = self.extract_relationships(data)
        
        return Configuration(
            id=self.extract_id(data),
            organization_id=self.safe_get(relationships, "organization.data.id"),
            name=self.clean_text(attributes.get("name", "")),
            hostname=attributes.get("hostname", ""),
            configuration_type=attributes.get("configuration-type-name", ""),
            configuration_status=attributes.get("configuration-status-name", ""),
            operating_system=attributes.get("operating-system", ""),
            ip_address=attributes.get("primary-ip", ""),
            mac_address=attributes.get("mac-address", ""),
            serial_number=attributes.get("serial-number", ""),
            asset_tag=attributes.get("asset-tag", ""),
            notes=self.clean_text(attributes.get("notes", "")),
            created_at=self.parse_datetime(attributes.get("created-at")),
            updated_at=self.parse_datetime(attributes.get("updated-at")),
            attributes=attributes,
            relationships=relationships
        )
    
    async def transform_batch(self, data_list: List[Dict[str, Any]]) -> List[Configuration]:
        """Transform batch of configurations.
        
        Args:
            data_list: List of raw configuration data
            
        Returns:
            List of Configuration instances
        """
        configurations = []
        
        for item in data_list:
            try:
                config = await self.transform(item)
                configurations.append(config)
            except Exception as e:
                logger.error(f"Failed to transform configuration: {e}")
                continue
        
        return configurations


class FlexibleAssetTransformer(BaseTransformer[FlexibleAsset]):
    """Transform IT Glue flexible asset data."""
    
    async def transform(self, data: Dict[str, Any]) -> FlexibleAsset:
        """Transform flexible asset data.
        
        Args:
            data: Raw flexible asset data
            
        Returns:
            FlexibleAsset model instance
        """
        attributes = self.extract_attributes(data)
        relationships = self.extract_relationships(data)
        
        # Parse traits (custom fields)
        traits = attributes.get("traits", {})
        
        return FlexibleAsset(
            id=self.extract_id(data),
            organization_id=self.safe_get(relationships, "organization.data.id"),
            flexible_asset_type_id=self.safe_get(relationships, "flexible-asset-type.data.id"),
            name=self.clean_text(attributes.get("name", "")),
            traits=traits,
            created_at=self.parse_datetime(attributes.get("created-at")),
            updated_at=self.parse_datetime(attributes.get("updated-at")),
            attributes=attributes,
            relationships=relationships
        )
    
    async def transform_batch(self, data_list: List[Dict[str, Any]]) -> List[FlexibleAsset]:
        """Transform batch of flexible assets.
        
        Args:
            data_list: List of raw flexible asset data
            
        Returns:
            List of FlexibleAsset instances
        """
        assets = []
        
        for item in data_list:
            try:
                asset = await self.transform(item)
                assets.append(asset)
            except Exception as e:
                logger.error(f"Failed to transform flexible asset: {e}")
                continue
        
        return assets


class PasswordTransformer(BaseTransformer[Password]):
    """Transform IT Glue password data."""
    
    async def transform(self, data: Dict[str, Any]) -> Password:
        """Transform password data.
        
        Args:
            data: Raw password data
            
        Returns:
            Password model instance
        """
        attributes = self.extract_attributes(data)
        relationships = self.extract_relationships(data)
        
        # Note: We don't store actual password values
        return Password(
            id=self.extract_id(data),
            organization_id=self.safe_get(relationships, "organization.data.id"),
            name=self.clean_text(attributes.get("name", "")),
            username=attributes.get("username", ""),
            password_category=attributes.get("password-category-name", ""),
            url=attributes.get("url", ""),
            notes=self.clean_text(attributes.get("notes", "")),
            created_at=self.parse_datetime(attributes.get("created-at")),
            updated_at=self.parse_datetime(attributes.get("updated-at")),
            password_updated_at=self.parse_datetime(attributes.get("password-updated-at")),
            attributes={k: v for k, v in attributes.items() if k != "password"},
            relationships=relationships
        )
    
    async def transform_batch(self, data_list: List[Dict[str, Any]]) -> List[Password]:
        """Transform batch of passwords.
        
        Args:
            data_list: List of raw password data
            
        Returns:
            List of Password instances
        """
        passwords = []
        
        for item in data_list:
            try:
                password = await self.transform(item)
                passwords.append(password)
            except Exception as e:
                logger.error(f"Failed to transform password: {e}")
                continue
        
        return passwords


class DocumentTransformer(BaseTransformer[Document]):
    """Transform IT Glue document data."""
    
    async def transform(self, data: Dict[str, Any]) -> Document:
        """Transform document data.
        
        Args:
            data: Raw document data
            
        Returns:
            Document model instance
        """
        attributes = self.extract_attributes(data)
        relationships = self.extract_relationships(data)
        
        return Document(
            id=self.extract_id(data),
            organization_id=self.safe_get(relationships, "organization.data.id"),
            name=self.clean_text(attributes.get("name", "")),
            content=self.clean_text(attributes.get("content", "")),
            folder_name=attributes.get("folder-name", ""),
            created_by=attributes.get("created-by", ""),
            updated_by=attributes.get("updated-by", ""),
            created_at=self.parse_datetime(attributes.get("created-at")),
            updated_at=self.parse_datetime(attributes.get("updated-at")),
            attributes=attributes,
            relationships=relationships
        )
    
    async def transform_batch(self, data_list: List[Dict[str, Any]]) -> List[Document]:
        """Transform batch of documents.
        
        Args:
            data_list: List of raw document data
            
        Returns:
            List of Document instances
        """
        documents = []
        
        for item in data_list:
            try:
                doc = await self.transform(item)
                documents.append(doc)
            except Exception as e:
                logger.error(f"Failed to transform document: {e}")
                continue
        
        return documents


class UnifiedEntityTransformer:
    """Transform IT Glue entities to unified database model."""
    
    def __init__(self):
        """Initialize unified transformer."""
        self.transformers = {
            "organizations": OrganizationTransformer(),
            "configurations": ConfigurationTransformer(),
            "flexible-assets": FlexibleAssetTransformer(),
            "passwords": PasswordTransformer(),
            "documents": DocumentTransformer(),
        }
    
    async def transform_to_entity(
        self,
        data: Dict[str, Any],
        entity_type: str
    ) -> ITGlueEntity:
        """Transform IT Glue data to unified entity model.
        
        Args:
            data: Raw IT Glue data
            entity_type: Type of entity
            
        Returns:
            ITGlueEntity instance
        """
        # Get appropriate transformer
        transformer = self.transformers.get(entity_type)
        
        if not transformer:
            logger.warning(f"No transformer for entity type: {entity_type}")
            # Create basic entity
            return ITGlueEntity(
                itglue_id=self.extract_id(data),
                entity_type=entity_type,
                name="Unknown",
                attributes=data,
                relationships={},
                search_text=""
            )
        
        # Transform to specific model
        model = await transformer.transform(data)
        
        # Convert to unified entity
        return ITGlueEntity(
            itglue_id=model.id,
            entity_type=entity_type,
            organization_id=getattr(model, "organization_id", None),
            name=model.name,
            attributes=model.attributes,
            relationships=model.relationships,
            search_text=self._generate_search_text(model),
            last_synced=datetime.utcnow()
        )
    
    def _generate_search_text(self, model: Any) -> str:
        """Generate searchable text from model.
        
        Args:
            model: Model instance
            
        Returns:
            Searchable text
        """
        search_parts = []
        
        # Add name
        if hasattr(model, "name"):
            search_parts.append(model.name)
        
        # Add description/notes
        if hasattr(model, "description"):
            search_parts.append(model.description)
        elif hasattr(model, "notes"):
            search_parts.append(model.notes)
        
        # Add type-specific fields
        if hasattr(model, "hostname"):
            search_parts.append(model.hostname)
        if hasattr(model, "ip_address"):
            search_parts.append(model.ip_address)
        if hasattr(model, "serial_number"):
            search_parts.append(model.serial_number)
        if hasattr(model, "username"):
            search_parts.append(model.username)
        
        # Clean and join
        search_text = " ".join(filter(None, search_parts))
        return search_text.lower()
    
    def extract_id(self, data: Dict[str, Any]) -> str:
        """Extract ID from data."""
        if "id" in data:
            return str(data["id"])
        elif "data" in data and "id" in data["data"]:
            return str(data["data"]["id"])
        return ""