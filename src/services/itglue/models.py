"""IT Glue data models."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ITGlueModel(BaseModel):
    """Base model for IT Glue entities."""

    id: str
    type: str
    attributes: dict[str, Any]
    relationships: Optional[dict[str, Any]] = None
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
    def traits(self) -> dict[str, Any]:
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


class FlexibleAssetType(ITGlueModel):
    """Flexible Asset Type model for discovering available asset types."""

    type: str = "flexible-asset-types"

    @property
    def name(self) -> str:
        return self.attributes.get("name", "")

    @property
    def description(self) -> Optional[str]:
        return self.attributes.get("description")

    @property
    def icon(self) -> Optional[str]:
        return self.attributes.get("icon")

    @property
    def enabled(self) -> bool:
        return self.attributes.get("enabled", True)

    @property
    def show_in_menu(self) -> bool:
        return self.attributes.get("show-in-menu", False)

    @property
    def fields(self) -> list[dict[str, Any]]:
        """Get the flexible asset fields for this type."""
        if self.relationships and "flexible-asset-fields" in self.relationships:
            fields_data = self.relationships["flexible-asset-fields"].get("data", [])
            return fields_data
        return []


class FlexibleAssetField(ITGlueModel):
    """Flexible Asset Field model for field definitions."""

    type: str = "flexible-asset-fields"

    @property
    def name(self) -> str:
        return self.attributes.get("name", "")

    @property
    def kind(self) -> str:
        """Field type: Text, Select, Tag, Number, Date, etc."""
        return self.attributes.get("kind", "Text")

    @property
    def hint(self) -> Optional[str]:
        return self.attributes.get("hint")

    @property
    def required(self) -> bool:
        return self.attributes.get("required", False)

    @property
    def order(self) -> int:
        return self.attributes.get("order", 0)

    @property
    def default_value(self) -> Optional[str]:
        return self.attributes.get("default-value")

    @property
    def show_in_list(self) -> bool:
        return self.attributes.get("show-in-list", False)

    @property
    def use_for_title(self) -> bool:
        return self.attributes.get("use-for-title", False)

    @property
    def name_key(self) -> str:
        """Programmatic key for this field."""
        return self.attributes.get("name-key", self.name.lower().replace(" ", "_"))
