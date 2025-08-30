"""IT Glue data models."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class ITGlueModel(BaseModel):
    """Base model for IT Glue entities."""
    
    id: str
    type: str
    attributes: Dict[str, Any]
    relationships: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        extra = "allow"


class Organization(ITGlueModel):
    """Organization model."""
    
    type: str = "organizations"
    
    @property
    def name(self) -> str:
        return self.attributes.get("name", "")
    
    @property
    def organization_type(self) -> str:
        return self.attributes.get("organization-type-name", "")
    
    @property
    def organization_status(self) -> str:
        return self.attributes.get("organization-status-name", "")


class Configuration(ITGlueModel):
    """Configuration model."""
    
    type: str = "configurations"
    
    @property
    def name(self) -> str:
        return self.attributes.get("name", "")
    
    @property
    def configuration_type(self) -> str:
        return self.attributes.get("configuration-type-name", "")
    
    @property
    def configuration_status(self) -> str:
        return self.attributes.get("configuration-status-name", "")
    
    @property
    def serial_number(self) -> Optional[str]:
        return self.attributes.get("serial-number")
    
    @property
    def organization_id(self) -> Optional[str]:
        if self.relationships and "organization" in self.relationships:
            return self.relationships["organization"]["data"]["id"]
        return None


class FlexibleAsset(ITGlueModel):
    """Flexible Asset model."""
    
    type: str = "flexible-assets"
    
    @property
    def name(self) -> str:
        return self.attributes.get("name", "")
    
    @property
    def flexible_asset_type_id(self) -> str:
        return self.attributes.get("flexible-asset-type-id", "")
    
    @property
    def traits(self) -> Dict[str, Any]:
        return self.attributes.get("traits", {})
    
    @property
    def organization_id(self) -> Optional[str]:
        return self.attributes.get("organization-id")


class Password(ITGlueModel):
    """Password model."""
    
    type: str = "passwords"
    
    @property
    def name(self) -> str:
        return self.attributes.get("name", "")
    
    @property
    def username(self) -> Optional[str]:
        return self.attributes.get("username")
    
    @property
    def url(self) -> Optional[str]:
        return self.attributes.get("url")
    
    @property
    def notes(self) -> Optional[str]:
        return self.attributes.get("notes")
    
    @property
    def password_category(self) -> Optional[str]:
        return self.attributes.get("password-category-name")
    
    @property
    def organization_id(self) -> Optional[str]:
        return self.attributes.get("organization-id")


class Document(ITGlueModel):
    """Document model."""
    
    type: str = "documents"
    
    @property
    def name(self) -> str:
        return self.attributes.get("name", "")
    
    @property
    def content(self) -> Optional[str]:
        return self.attributes.get("content")
    
    @property
    def document_folder_id(self) -> Optional[str]:
        return self.attributes.get("document-folder-id")
    
    @property
    def organization_id(self) -> Optional[str]:
        return self.attributes.get("organization-id")


class Attachment(ITGlueModel):
    """Attachment model."""
    
    type: str = "attachments"
    
    @property
    def name(self) -> str:
        return self.attributes.get("name", "")
    
    @property
    def attachment_file_name(self) -> str:
        return self.attributes.get("attachment-file-name", "")
    
    @property
    def attachment_file_size(self) -> int:
        return self.attributes.get("attachment-file-size", 0)


class Contact(ITGlueModel):
    """Contact model."""
    
    type: str = "contacts"
    
    @property
    def first_name(self) -> str:
        return self.attributes.get("first-name", "")
    
    @property
    def last_name(self) -> str:
        return self.attributes.get("last-name", "")
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def title(self) -> Optional[str]:
        return self.attributes.get("title")
    
    @property
    def email(self) -> Optional[str]:
        emails = self.attributes.get("contact-emails", [])
        if emails and len(emails) > 0:
            return emails[0].get("value")
        return None
    
    @property
    def organization_id(self) -> Optional[str]:
        return self.attributes.get("organization-id")


class Location(ITGlueModel):
    """Location model."""
    
    type: str = "locations"
    
    @property
    def name(self) -> str:
        return self.attributes.get("name", "")
    
    @property
    def address(self) -> Optional[str]:
        return self.attributes.get("address")
    
    @property
    def city(self) -> Optional[str]:
        return self.attributes.get("city")
    
    @property
    def region(self) -> Optional[str]:
        return self.attributes.get("region-name")
    
    @property
    def country(self) -> Optional[str]:
        return self.attributes.get("country-name")
    
    @property
    def organization_id(self) -> Optional[str]:
        return self.attributes.get("organization-id")