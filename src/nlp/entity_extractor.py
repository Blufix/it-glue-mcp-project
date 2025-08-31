"""Entity extraction for natural language queries."""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import ipaddress

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Types of entities to extract."""
    ORGANIZATION = "organization"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    SERVICE = "service"
    IP_ADDRESS = "ip_address"
    HOSTNAME = "hostname"
    DATE = "date"
    TIME_RANGE = "time_range"
    USER = "user"
    PASSWORD_TYPE = "password_type"
    LOCATION = "location"
    NETWORK = "network"
    PORT = "port"
    URL = "url"
    EMAIL = "email"
    ASSET_TAG = "asset_tag"
    SERIAL_NUMBER = "serial_number"
    VERSION = "version"
    OS = "operating_system"
    APPLICATION = "application"


@dataclass
class ExtractedEntity:
    """Represents an extracted entity."""
    text: str
    type: EntityType
    normalized: str
    confidence: float
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    

@dataclass 
class ExtractionContext:
    """Context for entity extraction."""
    known_organizations: List[str] = field(default_factory=list)
    known_systems: List[str] = field(default_factory=list)
    known_services: List[str] = field(default_factory=list)
    default_organization: Optional[str] = None
    default_time_zone: str = "UTC"
    

class EntityExtractor:
    """Extract entities from natural language IT queries."""
    
    def __init__(self):
        """Initialize the entity extractor."""
        self.patterns = self._compile_patterns()
        self.normalizers = self._initialize_normalizers()
        self.keyword_mappings = self._build_keyword_mappings()
        
    def _compile_patterns(self) -> Dict[EntityType, List[re.Pattern]]:
        """Compile regex patterns for entity extraction."""
        return {
            EntityType.IP_ADDRESS: [
                re.compile(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?:/\d{1,2})?\b'),
                re.compile(r'\b([0-9a-fA-F:]+::[0-9a-fA-F:]+)\b'),  # IPv6
            ],
            
            EntityType.HOSTNAME: [
                re.compile(r'\b([a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*)\b'),
            ],
            
            EntityType.EMAIL: [
                re.compile(r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'),
            ],
            
            EntityType.URL: [
                re.compile(r'\b(https?://[^\s<>"{}|\\^`\[\]]+)\b'),
                re.compile(r'\b(ftp://[^\s<>"{}|\\^`\[\]]+)\b'),
            ],
            
            EntityType.DATE: [
                # ISO format
                re.compile(r'\b(\d{4}-\d{2}-\d{2})\b'),
                # US format
                re.compile(r'\b(\d{1,2}/\d{1,2}/\d{4})\b'),
                # Natural dates
                re.compile(r'\b(today|yesterday|tomorrow)\b', re.I),
                re.compile(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.I),
                re.compile(r'\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b', re.I),
            ],
            
            EntityType.TIME_RANGE: [
                re.compile(r'\b(last|past|previous)\s+(\d+)\s+(minute|hour|day|week|month|year)s?\b', re.I),
                re.compile(r'\b(since|after|before)\s+(yesterday|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.I),
                re.compile(r'\b(between|from)\s+(.+?)\s+(and|to)\s+(.+?)(?:\s|$)', re.I),
                re.compile(r'\b(this|current)\s+(week|month|quarter|year)\b', re.I),
            ],
            
            EntityType.PORT: [
                re.compile(r'\bport\s+(\d{1,5})\b', re.I),
                re.compile(r':(\d{1,5})\b'),
            ],
            
            EntityType.VERSION: [
                re.compile(r'\bv?(\d+\.?\d*\.?\d*(?:-[a-zA-Z0-9]+)?)\b'),
                re.compile(r'\bversion\s+([^\s]+)\b', re.I),
            ],
            
            EntityType.ASSET_TAG: [
                re.compile(r'\b(?:asset|tag|asset.?tag)\s+#?([A-Z0-9]{3,})\b', re.I),
            ],
            
            EntityType.SERIAL_NUMBER: [
                re.compile(r'\b(?:serial|sn|s/n)\s+#?([A-Z0-9]{5,})\b', re.I),
            ],
            
            EntityType.ORGANIZATION: [
                re.compile(r'\b(?:org|organization|company|client|customer|account)\s+["\']?([^"\']+?)["\']?\s*(?:,|\.|$)', re.I),
                re.compile(r'\bfor\s+(?:org|organization|company|client)?\s*["\']?([A-Z][^"\']+?)["\']?\s*(?:,|\.|$)'),
            ],
            
            EntityType.CONFIGURATION: [
                re.compile(r'\b(?:config|configuration|server|host|machine|device|system)\s+["\']?([^"\']+?)["\']?\s*(?:,|\.|$)', re.I),
            ],
            
            EntityType.SERVICE: [
                re.compile(r'\b(?:service|application|app|process|daemon)\s+["\']?([^"\']+?)["\']?\s*(?:,|\.|$)', re.I),
            ],
            
            EntityType.USER: [
                re.compile(r'\b(?:user|account|login|username)\s+["\']?([^"\']+?)["\']?\s*(?:,|\.|$)', re.I),
                re.compile(r'\b([a-z][a-z0-9._-]+)@', re.I),  # Username from email
            ],
            
            EntityType.PASSWORD_TYPE: [
                re.compile(r'\b(admin|root|service|sa|administrator|local)\s+(?:password|credential|login)', re.I),
                re.compile(r'\b(?:password|credential|login)\s+(?:for|of)\s+([^\s]+)', re.I),
            ],
            
            EntityType.LOCATION: [
                re.compile(r'\b(?:location|site|office|datacenter|dc|region|zone|building)\s+["\']?([^"\']+?)["\']?\s*(?:,|\.|$)', re.I),
            ],
            
            EntityType.NETWORK: [
                re.compile(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})\b'),  # CIDR
                re.compile(r'\b(?:network|subnet|vlan|segment)\s+["\']?([^"\']+?)["\']?\s*(?:,|\.|$)', re.I),
            ],
            
            EntityType.OS: [
                re.compile(r'\b(windows|linux|ubuntu|centos|rhel|debian|macos|mac os|aix|solaris|freebsd)\s*(?:\d+(?:\.\d+)?)?', re.I),
                re.compile(r'\b(windows\s+(?:server|10|11|7|8)(?:\s+\w+)?)', re.I),
            ],
            
            EntityType.APPLICATION: [
                re.compile(r'\b(apache|nginx|iis|tomcat|mysql|postgres|postgresql|oracle|sql server|mongodb|redis|elasticsearch|jenkins|docker|kubernetes|k8s)\b', re.I),
            ],
            
            EntityType.SYSTEM: [
                re.compile(r'\b(?:system|server|host|machine|node|instance)\s+["\']?([^"\']+?)["\']?\s*(?:,|\.|$)', re.I),
            ],
        }
        
    def _initialize_normalizers(self) -> Dict[EntityType, callable]:
        """Initialize normalization functions for each entity type."""
        return {
            EntityType.IP_ADDRESS: self._normalize_ip,
            EntityType.DATE: self._normalize_date,
            EntityType.TIME_RANGE: self._normalize_time_range,
            EntityType.HOSTNAME: self._normalize_hostname,
            EntityType.EMAIL: str.lower,
            EntityType.PORT: self._normalize_port,
            EntityType.VERSION: self._normalize_version,
            EntityType.OS: self._normalize_os,
            EntityType.APPLICATION: self._normalize_application,
        }
        
    def _build_keyword_mappings(self) -> Dict[str, List[EntityType]]:
        """Build keyword to entity type mappings."""
        return {
            "server": [EntityType.SYSTEM, EntityType.CONFIGURATION],
            "host": [EntityType.SYSTEM, EntityType.HOSTNAME],
            "ip": [EntityType.IP_ADDRESS],
            "password": [EntityType.PASSWORD_TYPE],
            "credential": [EntityType.PASSWORD_TYPE],
            "user": [EntityType.USER],
            "account": [EntityType.USER],
            "service": [EntityType.SERVICE],
            "app": [EntityType.APPLICATION, EntityType.SERVICE],
            "application": [EntityType.APPLICATION, EntityType.SERVICE],
            "network": [EntityType.NETWORK],
            "subnet": [EntityType.NETWORK],
            "vlan": [EntityType.NETWORK],
            "org": [EntityType.ORGANIZATION],
            "company": [EntityType.ORGANIZATION],
            "client": [EntityType.ORGANIZATION],
            "location": [EntityType.LOCATION],
            "site": [EntityType.LOCATION],
            "datacenter": [EntityType.LOCATION],
            "dc": [EntityType.LOCATION],
        }
        
    def extract_entities(self, 
                        query: str, 
                        context: Optional[ExtractionContext] = None) -> List[ExtractedEntity]:
        """Extract entities from a natural language query."""
        entities = []
        context = context or ExtractionContext()
        
        # Extract using patterns
        for entity_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(query):
                    entity = self._create_entity(
                        match, entity_type, query, context
                    )
                    if entity and not self._is_duplicate(entity, entities):
                        entities.append(entity)
                        
        # Extract known entities from context
        entities.extend(self._extract_known_entities(query, context))
        
        # Post-process and validate entities
        entities = self._post_process_entities(entities, query)
        
        # Sort by position
        entities.sort(key=lambda e: e.start_pos)
        
        return entities
        
    def _create_entity(self,
                      match: re.Match,
                      entity_type: EntityType,
                      query: str,
                      context: ExtractionContext) -> Optional[ExtractedEntity]:
        """Create an entity from a regex match."""
        # Get matched text
        if match.lastgroup:
            text = match.group(match.lastgroup)
        elif len(match.groups()) > 0:
            text = match.group(1)
        else:
            text = match.group(0)
            
        # Clean up text
        text = text.strip(' ,.')
        if not text:
            return None
            
        # Normalize if normalizer exists
        normalized = text
        if entity_type in self.normalizers:
            try:
                normalized = self.normalizers[entity_type](text)
            except:
                pass
                
        # Calculate confidence
        confidence = self._calculate_confidence(text, entity_type, context)
        
        return ExtractedEntity(
            text=text,
            type=entity_type,
            normalized=normalized,
            confidence=confidence,
            start_pos=match.start(),
            end_pos=match.end(),
            metadata={}
        )
        
    def _extract_known_entities(self,
                               query: str,
                               context: ExtractionContext) -> List[ExtractedEntity]:
        """Extract entities that match known values from context."""
        entities = []
        query_lower = query.lower()
        
        # Check known organizations
        for org in context.known_organizations:
            if org.lower() in query_lower:
                start = query_lower.index(org.lower())
                entities.append(ExtractedEntity(
                    text=org,
                    type=EntityType.ORGANIZATION,
                    normalized=org,
                    confidence=1.0,
                    start_pos=start,
                    end_pos=start + len(org),
                    metadata={"source": "known"}
                ))
                
        # Check known systems
        for system in context.known_systems:
            if system.lower() in query_lower:
                start = query_lower.index(system.lower())
                entities.append(ExtractedEntity(
                    text=system,
                    type=EntityType.SYSTEM,
                    normalized=system,
                    confidence=1.0,
                    start_pos=start,
                    end_pos=start + len(system),
                    metadata={"source": "known"}
                ))
                
        return entities
        
    def _is_duplicate(self,
                     entity: ExtractedEntity,
                     entities: List[ExtractedEntity]) -> bool:
        """Check if entity is a duplicate or overlaps with existing entities."""
        for existing in entities:
            # Check for overlap
            if (entity.start_pos < existing.end_pos and 
                entity.end_pos > existing.start_pos):
                # Keep the one with higher confidence
                if entity.confidence <= existing.confidence:
                    return True
                else:
                    entities.remove(existing)
                    return False
                    
            # Check for same normalized value
            if (entity.type == existing.type and 
                entity.normalized == existing.normalized):
                return True
                
        return False
        
    def _post_process_entities(self,
                              entities: List[ExtractedEntity],
                              query: str) -> List[ExtractedEntity]:
        """Post-process extracted entities."""
        processed = []
        
        for entity in entities:
            # Validate entity
            if not self._validate_entity(entity):
                continue
                
            # Enhance metadata
            self._enhance_metadata(entity, query)
            
            # Resolve ambiguities
            entity = self._resolve_ambiguity(entity, entities)
            
            processed.append(entity)
            
        return processed
        
    def _validate_entity(self, entity: ExtractedEntity) -> bool:
        """Validate an extracted entity."""
        # IP address validation
        if entity.type == EntityType.IP_ADDRESS:
            try:
                ipaddress.ip_address(entity.normalized)
                return True
            except:
                return False
                
        # Port validation
        if entity.type == EntityType.PORT:
            try:
                port = int(entity.normalized)
                return 1 <= port <= 65535
            except:
                return False
                
        # Email validation
        if entity.type == EntityType.EMAIL:
            return '@' in entity.normalized and '.' in entity.normalized.split('@')[1]
            
        # URL validation
        if entity.type == EntityType.URL:
            return entity.normalized.startswith(('http://', 'https://', 'ftp://'))
            
        return True
        
    def _enhance_metadata(self, entity: ExtractedEntity, query: str):
        """Enhance entity metadata."""
        # Add context words
        words_before = query[:entity.start_pos].split()[-2:]
        words_after = query[entity.end_pos:].split()[:2]
        
        entity.metadata["context_before"] = ' '.join(words_before)
        entity.metadata["context_after"] = ' '.join(words_after)
        
        # Add specific metadata based on type
        if entity.type == EntityType.IP_ADDRESS:
            try:
                ip = ipaddress.ip_address(entity.normalized)
                entity.metadata["is_private"] = ip.is_private
                entity.metadata["version"] = ip.version
            except:
                pass
                
        elif entity.type == EntityType.DATE:
            entity.metadata["is_relative"] = entity.text.lower() in ['today', 'yesterday', 'tomorrow']
            
        elif entity.type == EntityType.VERSION:
            parts = entity.normalized.split('.')
            entity.metadata["major"] = parts[0] if parts else None
            entity.metadata["minor"] = parts[1] if len(parts) > 1 else None
            entity.metadata["patch"] = parts[2] if len(parts) > 2 else None
            
    def _resolve_ambiguity(self,
                          entity: ExtractedEntity,
                          all_entities: List[ExtractedEntity]) -> ExtractedEntity:
        """Resolve entity type ambiguities."""
        # Example: "server" could be SYSTEM or CONFIGURATION
        if entity.text.lower() in self.keyword_mappings:
            possible_types = self.keyword_mappings[entity.text.lower()]
            
            # Use context to determine best type
            context_before = entity.metadata.get("context_before", "").lower()
            context_after = entity.metadata.get("context_after", "").lower()
            
            if "config" in context_before or "configuration" in context_before:
                if EntityType.CONFIGURATION in possible_types:
                    entity.type = EntityType.CONFIGURATION
            elif "system" in context_before or "machine" in context_before:
                if EntityType.SYSTEM in possible_types:
                    entity.type = EntityType.SYSTEM
                    
        return entity
        
    def _calculate_confidence(self,
                            text: str,
                            entity_type: EntityType,
                            context: ExtractionContext) -> float:
        """Calculate confidence score for an extracted entity."""
        confidence = 0.7  # Base confidence
        
        # Boost for known entities
        if entity_type == EntityType.ORGANIZATION:
            if text in context.known_organizations:
                confidence = 1.0
        elif entity_type == EntityType.SYSTEM:
            if text in context.known_systems:
                confidence = 1.0
                
        # Boost for specific patterns
        if entity_type == EntityType.IP_ADDRESS:
            confidence = 0.95  # High confidence for IP patterns
        elif entity_type == EntityType.EMAIL:
            confidence = 0.95
        elif entity_type == EntityType.URL:
            confidence = 0.95
            
        # Lower confidence for ambiguous entities
        if text.lower() in self.keyword_mappings:
            confidence *= 0.8
            
        return min(confidence, 1.0)
        
    def _normalize_ip(self, ip_str: str) -> str:
        """Normalize IP address."""
        try:
            return str(ipaddress.ip_address(ip_str))
        except:
            return ip_str
            
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string."""
        date_lower = date_str.lower()
        
        # Handle relative dates
        if date_lower == "today":
            return datetime.now().strftime("%Y-%m-%d")
        elif date_lower == "yesterday":
            return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        elif date_lower == "tomorrow":
            return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            
        # Try to parse other formats
        # This is simplified - a real implementation would use dateutil or similar
        return date_str
        
    def _normalize_time_range(self, range_str: str) -> str:
        """Normalize time range string."""
        # Extract number and unit
        match = re.search(r'(\d+)\s+(minute|hour|day|week|month|year)s?', range_str, re.I)
        if match:
            number = int(match.group(1))
            unit = match.group(2).lower()
            return f"P{number}{unit[0].upper()}"  # ISO 8601 duration
        return range_str
        
    def _normalize_hostname(self, hostname: str) -> str:
        """Normalize hostname."""
        return hostname.lower()
        
    def _normalize_port(self, port_str: str) -> str:
        """Normalize port number."""
        # Extract just the number
        port_num = re.search(r'\d+', port_str)
        return port_num.group(0) if port_num else port_str
        
    def _normalize_version(self, version_str: str) -> str:
        """Normalize version string."""
        # Remove 'v' prefix if present
        if version_str.lower().startswith('v'):
            return version_str[1:]
        return version_str
        
    def _normalize_os(self, os_str: str) -> str:
        """Normalize operating system name."""
        os_map = {
            "windows": "Windows",
            "linux": "Linux",
            "ubuntu": "Ubuntu",
            "centos": "CentOS",
            "rhel": "RHEL",
            "red hat": "RHEL",
            "debian": "Debian",
            "macos": "macOS",
            "mac os": "macOS",
        }
        
        os_lower = os_str.lower()
        for key, value in os_map.items():
            if key in os_lower:
                # Extract version if present
                version_match = re.search(r'\d+(?:\.\d+)?', os_str)
                if version_match:
                    return f"{value} {version_match.group(0)}"
                return value
                
        return os_str
        
    def _normalize_application(self, app_str: str) -> str:
        """Normalize application name."""
        app_map = {
            "postgres": "PostgreSQL",
            "k8s": "Kubernetes",
            "iis": "IIS",
            "sql server": "SQL Server",
        }
        
        app_lower = app_str.lower()
        return app_map.get(app_lower, app_str)