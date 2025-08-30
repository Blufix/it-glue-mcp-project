# IT Glue MCP Server - Security & Compliance Documentation 🔒

## Overview

This document outlines the security architecture, compliance requirements, and best practices for the IT Glue MCP Server. It covers data protection, access control, audit logging, compliance standards, and incident response procedures.

## Table of Contents

1. [Security Architecture](#security-architecture)
2. [Authentication & Authorization](#authentication--authorization)
3. [Data Protection](#data-protection)
4. [Network Security](#network-security)
5. [Application Security](#application-security)
6. [Compliance Standards](#compliance-standards)
7. [Audit & Logging](#audit--logging)
8. [Incident Response](#incident-response)
9. [Security Testing](#security-testing)
10. [Security Checklist](#security-checklist)

## Security Architecture

### Defense in Depth

```
┌─────────────────────────────────────────────────────────┐
│                   External Firewall                      │
├─────────────────────────────────────────────────────────┤
│                      WAF (Web Application Firewall)      │
├─────────────────────────────────────────────────────────┤
│                    Load Balancer (SSL/TLS)              │
├─────────────────────────────────────────────────────────┤
│                   API Gateway (Rate Limiting)            │
├──────────────────┬────────────────┬────────────────────┤
│   Application    │   Middleware    │    Monitoring      │
│    Security      │    Security     │    & Alerting     │
├──────────────────┴────────────────┴────────────────────┤
│                   Database Security                      │
│              (Encryption, Access Control)                │
└─────────────────────────────────────────────────────────┘
```

### Security Components

| Layer | Component | Purpose | Implementation |
|-------|-----------|---------|----------------|
| **Perimeter** | Firewall | Network filtering | AWS Security Groups / Azure NSG |
| **Application** | WAF | Application protection | CloudFlare / AWS WAF |
| **Transport** | TLS/SSL | Data in transit | Let's Encrypt / ACM |
| **Authentication** | OAuth2/JWT | Identity verification | Auth0 / Okta |
| **Authorization** | RBAC | Access control | Custom ACL system |
| **Data** | Encryption | Data at rest | AES-256-GCM |
| **Monitoring** | SIEM | Security monitoring | Splunk / ELK Stack |

### Threat Model

```yaml
threats:
  - name: SQL Injection
    severity: HIGH
    mitigation:
      - Parameterized queries
      - Input validation
      - Stored procedures
    
  - name: Cross-Site Scripting (XSS)
    severity: HIGH
    mitigation:
      - Content Security Policy
      - Input sanitization
      - Output encoding
    
  - name: Authentication Bypass
    severity: CRITICAL
    mitigation:
      - Multi-factor authentication
      - Session management
      - Account lockout policies
    
  - name: Data Exposure
    severity: HIGH
    mitigation:
      - Encryption at rest
      - Encryption in transit
      - Access control lists
    
  - name: DDoS Attacks
    severity: MEDIUM
    mitigation:
      - Rate limiting
      - CDN protection
      - Auto-scaling
```

## Authentication & Authorization

### Authentication Flow

```python
# src/auth/authentication.py
from typing import Optional
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

class AuthenticationService:
    """Handles user authentication."""
    
    def __init__(self):
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12
        )
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        self.algorithm = "HS256"
        self.token_expiry = timedelta(hours=24)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, user_id: str, scopes: List[str]) -> str:
        """Create JWT access token."""
        payload = {
            "sub": user_id,
            "scopes": scopes,
            "exp": datetime.utcnow() + self.token_expiry,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4())  # JWT ID for revocation
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Check if token is revoked
            if self.is_token_revoked(payload["jti"]):
                raise HTTPException(status_code=401, detail="Token revoked")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
```

### Multi-Factor Authentication

```python
# src/auth/mfa.py
import pyotp
import qrcode
from io import BytesIO
import base64

class MFAService:
    """Multi-factor authentication service."""
    
    def generate_secret(self, user_email: str) -> Dict:
        """Generate TOTP secret for user."""
        secret = pyotp.random_base32()
        
        # Generate QR code
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name='IT Glue MCP'
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format='PNG')
        
        qr_code = base64.b64encode(buf.getvalue()).decode()
        
        return {
            "secret": secret,
            "qr_code": f"data:image/png;base64,{qr_code}",
            "manual_entry_key": secret
        }
    
    def verify_token(self, secret: str, token: str) -> bool:
        """Verify TOTP token."""
        totp = pyotp.TOTP(secret)
        
        # Allow for time drift (30 second window)
        return totp.verify(token, valid_window=1)
    
    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup codes for account recovery."""
        import secrets
        
        codes = []
        for _ in range(count):
            code = f"{secrets.randbelow(1000):03d}-{secrets.randbelow(1000):03d}"
            codes.append(code)
        
        return codes
```

### Role-Based Access Control (RBAC)

```python
# src/auth/rbac.py
from enum import Enum
from typing import List, Dict

class Permission(Enum):
    """System permissions."""
    READ_PASSWORDS = "passwords:read"
    WRITE_PASSWORDS = "passwords:write"
    READ_CONFIGS = "configs:read"
    WRITE_CONFIGS = "configs:write"
    READ_SENSITIVE = "sensitive:read"
    ADMIN_USERS = "users:admin"
    ADMIN_SYSTEM = "system:admin"

class Role(Enum):
    """User roles."""
    VIEWER = "viewer"
    USER = "user"
    POWER_USER = "power_user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

ROLE_PERMISSIONS = {
    Role.VIEWER: [
        Permission.READ_CONFIGS
    ],
    Role.USER: [
        Permission.READ_CONFIGS,
        Permission.READ_PASSWORDS
    ],
    Role.POWER_USER: [
        Permission.READ_CONFIGS,
        Permission.READ_PASSWORDS,
        Permission.WRITE_CONFIGS,
        Permission.READ_SENSITIVE
    ],
    Role.ADMIN: [
        Permission.READ_CONFIGS,
        Permission.READ_PASSWORDS,
        Permission.WRITE_CONFIGS,
        Permission.WRITE_PASSWORDS,
        Permission.READ_SENSITIVE,
        Permission.ADMIN_USERS
    ],
    Role.SUPER_ADMIN: [p for p in Permission]  # All permissions
}

class RBACService:
    """Role-based access control service."""
    
    def check_permission(
        self,
        user_role: Role,
        required_permission: Permission
    ) -> bool:
        """Check if role has required permission."""
        role_perms = ROLE_PERMISSIONS.get(user_role, [])
        return required_permission in role_perms
    
    def get_user_permissions(self, user_role: Role) -> List[Permission]:
        """Get all permissions for a role."""
        return ROLE_PERMISSIONS.get(user_role, [])
    
    def enforce_permission(
        self,
        user_role: Role,
        required_permission: Permission
    ):
        """Enforce permission requirement."""
        if not self.check_permission(user_role, required_permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {required_permission.value}"
            )
```

## Data Protection

### Encryption at Rest

```python
# src/security/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64
import os

class EncryptionService:
    """Data encryption service."""
    
    def __init__(self):
        self.master_key = self._get_or_create_master_key()
        self.fernet = Fernet(self.master_key)
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key."""
        key_file = "/secure/keys/master.key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            
            # Store securely (use KMS in production)
            os.makedirs(os.path.dirname(key_file), exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
            
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            
            return key
    
    def encrypt_field(self, data: str) -> str:
        """Encrypt sensitive field."""
        if not data:
            return data
        
        encrypted = self.fernet.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_field(self, encrypted_data: str) -> str:
        """Decrypt sensitive field."""
        if not encrypted_data:
            return encrypted_data
        
        try:
            decoded = base64.b64decode(encrypted_data)
            decrypted = self.fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data")
    
    def encrypt_file(self, file_path: str, output_path: str):
        """Encrypt entire file."""
        with open(file_path, 'rb') as f:
            data = f.read()
        
        encrypted = self.fernet.encrypt(data)
        
        with open(output_path, 'wb') as f:
            f.write(encrypted)
    
    def rotate_encryption_key(self):
        """Rotate encryption keys."""
        # Generate new key
        new_key = Fernet.generate_key()
        new_fernet = Fernet(new_key)
        
        # Re-encrypt all data with new key
        # This should be done in batches for large datasets
        
        # Update master key
        self.master_key = new_key
        self.fernet = new_fernet
```

### Data Masking

```python
# src/security/data_masking.py
import re
from typing import Dict, Any

class DataMaskingService:
    """Service for masking sensitive data."""
    
    PATTERNS = {
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        'api_key': r'\b(sk|pk|api[_-]?key)[_-]?[A-Za-z0-9]{32,}\b',
        'password': r'(?i)(password|pwd|pass)[\s:=]+[\S]+',
        'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    }
    
    def mask_data(self, data: str, patterns: List[str] = None) -> str:
        """Mask sensitive data in string."""
        if patterns is None:
            patterns = self.PATTERNS.keys()
        
        masked = data
        for pattern_name in patterns:
            if pattern_name in self.PATTERNS:
                pattern = self.PATTERNS[pattern_name]
                masked = re.sub(pattern, self._mask_match, masked)
        
        return masked
    
    def _mask_match(self, match) -> str:
        """Mask matched pattern."""
        text = match.group(0)
        length = len(text)
        
        if length <= 4:
            return '*' * length
        else:
            # Show first and last 2 characters
            return text[:2] + '*' * (length - 4) + text[-2:]
    
    def mask_dict(self, data: Dict[str, Any], sensitive_keys: List[str]) -> Dict:
        """Mask sensitive fields in dictionary."""
        masked = data.copy()
        
        for key in sensitive_keys:
            if key in masked and masked[key]:
                if isinstance(masked[key], str):
                    # Mask string value
                    masked[key] = '***MASKED***'
                elif isinstance(masked[key], dict):
                    # Recursively mask nested dict
                    masked[key] = self.mask_dict(masked[key], sensitive_keys)
        
        return masked
```

### Secure Key Management

```python
# src/security/key_management.py
import boto3
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from google.cloud import secretmanager
import hvac

class KeyManagementService:
    """Centralized key management service."""
    
    def __init__(self, provider: str = "aws"):
        self.provider = provider
        self._init_provider()
    
    def _init_provider(self):
        """Initialize KMS provider."""
        if self.provider == "aws":
            self.client = boto3.client('kms')
            self.secrets_client = boto3.client('secretsmanager')
        elif self.provider == "azure":
            credential = DefaultAzureCredential()
            vault_url = os.getenv("AZURE_KEY_VAULT_URL")
            self.client = SecretClient(vault_url=vault_url, credential=credential)
        elif self.provider == "gcp":
            self.client = secretmanager.SecretManagerServiceClient()
        elif self.provider == "hashicorp":
            self.client = hvac.Client(url=os.getenv("VAULT_URL"))
            self.client.token = os.getenv("VAULT_TOKEN")
    
    def get_secret(self, secret_name: str) -> str:
        """Retrieve secret from KMS."""
        if self.provider == "aws":
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            return response['SecretString']
        elif self.provider == "azure":
            secret = self.client.get_secret(secret_name)
            return secret.value
        elif self.provider == "gcp":
            name = f"projects/{os.getenv('GCP_PROJECT')}/secrets/{secret_name}/versions/latest"
            response = self.client.access_secret_version(request={"name": name})
            return response.payload.data.decode('UTF-8')
        elif self.provider == "hashicorp":
            response = self.client.secrets.kv.v2.read_secret_version(path=secret_name)
            return response['data']['data']['value']
    
    def store_secret(self, secret_name: str, secret_value: str):
        """Store secret in KMS."""
        if self.provider == "aws":
            self.secrets_client.create_secret(
                Name=secret_name,
                SecretString=secret_value
            )
        elif self.provider == "azure":
            self.client.set_secret(secret_name, secret_value)
        # Additional providers...
    
    def rotate_secret(self, secret_name: str) -> str:
        """Rotate secret and return new value."""
        import secrets
        
        # Generate new secret
        new_secret = secrets.token_urlsafe(32)
        
        # Store new version
        self.store_secret(secret_name, new_secret)
        
        # Log rotation event
        logger.info(f"Secret rotated: {secret_name}")
        
        return new_secret
```

## Network Security

### TLS Configuration

```nginx
# configs/nginx-ssl.conf
server {
    listen 443 ssl http2;
    server_name api.your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/nginx/ssl/chain.pem;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    location / {
        proxy_pass http://app:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Firewall Rules

```yaml
# firewall-rules.yaml
ingress_rules:
  - name: allow-https
    protocol: TCP
    port: 443
    source: 0.0.0.0/0
    action: ALLOW
    
  - name: allow-ssh-bastion
    protocol: TCP
    port: 22
    source: 10.0.1.0/24  # Bastion subnet only
    action: ALLOW
    
  - name: allow-monitoring
    protocol: TCP
    port: 9090
    source: 10.0.2.0/24  # Monitoring subnet
    action: ALLOW

egress_rules:
  - name: allow-https-out
    protocol: TCP
    port: 443
    destination: 0.0.0.0/0
    action: ALLOW
    
  - name: allow-dns
    protocol: UDP
    port: 53
    destination: 0.0.0.0/0
    action: ALLOW
    
  - name: block-all-else
    protocol: ALL
    destination: 0.0.0.0/0
    action: DENY
```

## Application Security

### Input Validation

```python
# src/security/validation.py
from pydantic import BaseModel, validator, constr, EmailStr
import re
import html
import urllib.parse

class InputValidator:
    """Input validation service."""
    
    @staticmethod
    def validate_sql_input(value: str) -> str:
        """Validate input for SQL injection."""
        # Blocklist of SQL keywords
        sql_keywords = [
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP',
            'UNION', 'EXEC', 'EXECUTE', '--', '/*', '*/',
            'xp_', 'sp_', 'OR 1=1', 'AND 1=1'
        ]
        
        upper_value = value.upper()
        for keyword in sql_keywords:
            if keyword in upper_value:
                raise ValueError(f"Potential SQL injection detected: {keyword}")
        
        return value
    
    @staticmethod
    def validate_xss_input(value: str) -> str:
        """Validate and sanitize input for XSS."""
        # Remove HTML tags
        sanitized = html.escape(value)
        
        # Remove JavaScript patterns
        js_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe',
            r'<object',
            r'<embed'
        ]
        
        for pattern in js_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"Potential XSS detected: {pattern}")
        
        return sanitized
    
    @staticmethod
    def validate_path_traversal(path: str) -> str:
        """Validate path for directory traversal attacks."""
        # Normalize path
        normalized = os.path.normpath(path)
        
        # Check for traversal patterns
        if '..' in normalized or normalized.startswith('/'):
            raise ValueError("Path traversal attempt detected")
        
        # Ensure path is within allowed directory
        base_dir = '/app/data'
        full_path = os.path.join(base_dir, normalized)
        
        if not full_path.startswith(base_dir):
            raise ValueError("Path outside allowed directory")
        
        return normalized
    
    @staticmethod
    def validate_command_injection(command: str) -> str:
        """Validate input for command injection."""
        # Dangerous characters
        dangerous_chars = ['&', '|', ';', '$', '>', '<', '`', '\\', '(', ')', '[', ']', '{', '}']
        
        for char in dangerous_chars:
            if char in command:
                raise ValueError(f"Potential command injection: {char}")
        
        return command

class SecureQueryModel(BaseModel):
    """Secure query model with validation."""
    
    query: constr(min_length=1, max_length=500)
    company_id: constr(regex=r'^[a-zA-Z0-9_-]+$')
    email: EmailStr
    
    @validator('query')
    def validate_query(cls, v):
        """Validate query for injection attacks."""
        InputValidator.validate_sql_input(v)
        InputValidator.validate_xss_input(v)
        return v
    
    @validator('company_id')
    def validate_company_id(cls, v):
        """Validate company ID format."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Invalid company ID format")
        return v
```

### Security Headers

```python
# src/middleware/security_headers.py
from fastapi import Request
from fastapi.responses import Response

class SecurityHeadersMiddleware:
    """Add security headers to responses."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = self._get_csp()
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response
    
    def _get_csp(self) -> str:
        """Get Content Security Policy."""
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.your-domain.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
```

## Compliance Standards

### GDPR Compliance

```python
# src/compliance/gdpr.py
from datetime import datetime, timedelta
from typing import Dict, List

class GDPRComplianceService:
    """GDPR compliance implementation."""
    
    async def export_user_data(self, user_id: str) -> Dict:
        """Export all user data (Right to Data Portability)."""
        user_data = {
            "personal_info": await self._get_personal_info(user_id),
            "activity_logs": await self._get_activity_logs(user_id),
            "queries": await self._get_user_queries(user_id),
            "preferences": await self._get_user_preferences(user_id),
            "exported_at": datetime.utcnow().isoformat()
        }
        
        # Log data export
        await self._log_data_export(user_id)
        
        return user_data
    
    async def delete_user_data(self, user_id: str) -> bool:
        """Delete all user data (Right to Erasure)."""
        # Delete personal data
        await self._delete_personal_info(user_id)
        
        # Anonymize logs (keep for legal requirements)
        await self._anonymize_logs(user_id)
        
        # Delete cached data
        await self._delete_cached_data(user_id)
        
        # Log deletion
        await self._log_data_deletion(user_id)
        
        return True
    
    async def get_consent_status(self, user_id: str) -> Dict:
        """Get user consent status."""
        return {
            "data_processing": await self._get_consent(user_id, "data_processing"),
            "marketing": await self._get_consent(user_id, "marketing"),
            "analytics": await self._get_consent(user_id, "analytics"),
            "third_party": await self._get_consent(user_id, "third_party")
        }
    
    async def update_consent(self, user_id: str, consent_type: str, granted: bool):
        """Update user consent."""
        await self._store_consent(
            user_id=user_id,
            consent_type=consent_type,
            granted=granted,
            timestamp=datetime.utcnow()
        )
    
    def anonymize_data(self, data: Dict) -> Dict:
        """Anonymize personal data."""
        anonymized = data.copy()
        
        # Replace personal identifiers
        if 'email' in anonymized:
            anonymized['email'] = 'user@anonymized.com'
        if 'name' in anonymized:
            anonymized['name'] = 'Anonymous User'
        if 'ip_address' in anonymized:
            anonymized['ip_address'] = '0.0.0.0'
        if 'user_id' in anonymized:
            anonymized['user_id'] = 'anonymous_' + hashlib.sha256(
                anonymized['user_id'].encode()
            ).hexdigest()[:8]
        
        return anonymized
```

### PCI DSS Compliance

```python
# src/compliance/pci_dss.py
class PCIDSSCompliance:
    """PCI DSS compliance implementation."""
    
    def mask_card_number(self, card_number: str) -> str:
        """Mask credit card number (show only last 4 digits)."""
        if len(card_number) < 8:
            return '*' * len(card_number)
        
        return '*' * (len(card_number) - 4) + card_number[-4:]
    
    def tokenize_card(self, card_number: str) -> str:
        """Tokenize credit card for storage."""
        # Use payment processor's tokenization service
        # This is a simplified example
        import hashlib
        
        token = hashlib.sha256(
            (card_number + os.getenv("TOKENIZATION_SALT")).encode()
        ).hexdigest()
        
        return f"tok_{token[:32]}"
    
    def validate_card_security(self, card_data: Dict) -> List[str]:
        """Validate card data security requirements."""
        violations = []
        
        # Check if card number is encrypted
        if 'card_number' in card_data and not card_data.get('encrypted'):
            violations.append("Card number must be encrypted")
        
        # Check if CVV is stored (should never be stored)
        if 'cvv' in card_data or 'cvc' in card_data:
            violations.append("CVV/CVC must not be stored")
        
        # Check if sensitive authentication data is stored
        if 'pin' in card_data:
            violations.append("PIN must not be stored")
        
        return violations
    
    def audit_card_access(self, user_id: str, action: str, card_token: str):
        """Audit card data access."""
        audit_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "card_token": card_token,
            "ip_address": request.client.host,
            "user_agent": request.headers.get("User-Agent")
        }
        
        # Store in tamper-proof audit log
        self._store_audit_log(audit_log)
```

### HIPAA Compliance

```python
# src/compliance/hipaa.py
class HIPAACompliance:
    """HIPAA compliance for healthcare data."""
    
    def encrypt_phi(self, phi_data: Dict) -> Dict:
        """Encrypt Protected Health Information."""
        encrypted_data = {}
        
        for key, value in phi_data.items():
            if self._is_phi_field(key):
                encrypted_data[key] = self.encryption_service.encrypt_field(str(value))
            else:
                encrypted_data[key] = value
        
        return encrypted_data
    
    def audit_phi_access(self, user_id: str, patient_id: str, action: str, fields: List[str]):
        """Audit PHI access for HIPAA compliance."""
        audit_entry = {
            "timestamp": datetime.utcnow(),
            "user_id": user_id,
            "patient_id": patient_id,
            "action": action,
            "accessed_fields": fields,
            "reason": request.headers.get("X-Access-Reason"),
            "ip_address": request.client.host
        }
        
        # Store in HIPAA-compliant audit log
        self._store_hipaa_audit(audit_entry)
    
    def _is_phi_field(self, field_name: str) -> bool:
        """Check if field contains PHI."""
        phi_fields = [
            'patient_name', 'date_of_birth', 'ssn', 'medical_record_number',
            'health_plan_number', 'diagnosis', 'treatment', 'medication'
        ]
        return field_name.lower() in phi_fields
```

## Audit & Logging

### Audit Logging System

```python
# src/audit/audit_logger.py
import json
from datetime import datetime
from typing import Dict, Any
import hashlib

class AuditLogger:
    """Comprehensive audit logging system."""
    
    def __init__(self):
        self.log_queue = []
        self.batch_size = 100
    
    async def log_event(
        self,
        event_type: str,
        user_id: str,
        action: str,
        resource: str,
        details: Dict[str, Any],
        result: str = "success"
    ):
        """Log audit event."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_id": self._generate_event_id(),
            "event_type": event_type,
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details,
            "result": result,
            "ip_address": self._get_client_ip(),
            "user_agent": self._get_user_agent(),
            "session_id": self._get_session_id(),
            "checksum": None  # Will be set after
        }
        
        # Add integrity checksum
        event["checksum"] = self._calculate_checksum(event)
        
        # Add to queue
        self.log_queue.append(event)
        
        # Flush if batch size reached
        if len(self.log_queue) >= self.batch_size:
            await self._flush_logs()
    
    def _calculate_checksum(self, event: Dict) -> str:
        """Calculate integrity checksum for event."""
        # Remove checksum field for calculation
        event_copy = {k: v for k, v in event.items() if k != "checksum"}
        
        # Create deterministic JSON string
        event_str = json.dumps(event_copy, sort_keys=True)
        
        # Calculate SHA-256 hash
        return hashlib.sha256(event_str.encode()).hexdigest()
    
    async def _flush_logs(self):
        """Flush audit logs to storage."""
        if not self.log_queue:
            return
        
        # Store in database
        await self._store_in_database(self.log_queue)
        
        # Send to SIEM
        await self._send_to_siem(self.log_queue)
        
        # Clear queue
        self.log_queue = []
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        import uuid
        return str(uuid.uuid4())
```

### Security Event Monitoring

```python
# src/monitoring/security_monitor.py
from collections import defaultdict
from datetime import datetime, timedelta

class SecurityMonitor:
    """Real-time security monitoring."""
    
    def __init__(self):
        self.failed_login_attempts = defaultdict(list)
        self.rate_limit_violations = defaultdict(int)
        self.suspicious_patterns = []
    
    async def monitor_login_attempt(self, username: str, success: bool, ip: str):
        """Monitor login attempts for anomalies."""
        if not success:
            self.failed_login_attempts[username].append({
                "timestamp": datetime.utcnow(),
                "ip": ip
            })
            
            # Check for brute force
            recent_attempts = [
                a for a in self.failed_login_attempts[username]
                if a["timestamp"] > datetime.utcnow() - timedelta(minutes=15)
            ]
            
            if len(recent_attempts) >= 5:
                await self._trigger_alert(
                    "BRUTE_FORCE",
                    f"Multiple failed login attempts for {username}",
                    {"username": username, "attempts": len(recent_attempts)}
                )
                
                # Lock account
                await self._lock_account(username)
    
    async def monitor_api_access(self, endpoint: str, user_id: str, response_code: int):
        """Monitor API access patterns."""
        # Check for scanning behavior
        if response_code == 404:
            self._track_404_pattern(user_id, endpoint)
        
        # Check for authorization failures
        if response_code == 403:
            await self._track_authorization_failure(user_id, endpoint)
    
    async def _trigger_alert(self, alert_type: str, message: str, details: Dict):
        """Trigger security alert."""
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": alert_type,
            "severity": self._get_severity(alert_type),
            "message": message,
            "details": details
        }
        
        # Send to monitoring systems
        await self._send_to_siem(alert)
        await self._send_to_slack(alert)
        
        # Log alert
        logger.warning(f"Security Alert: {alert}")
```

## Incident Response

### Incident Response Plan

```yaml
# incident-response-plan.yaml
incident_response:
  phases:
    1_preparation:
      - Maintain incident response team contacts
      - Keep runbooks updated
      - Regular training and drills
      - Tool preparation and access
    
    2_identification:
      - Monitor security alerts
      - Analyze anomalies
      - Determine incident severity
      - Initial classification
    
    3_containment:
      short_term:
        - Isolate affected systems
        - Block malicious IPs
        - Disable compromised accounts
        - Preserve evidence
      
      long_term:
        - Apply patches
        - Remove backdoors
        - Reset credentials
        - Strengthen defenses
    
    4_eradication:
      - Remove malware
      - Close vulnerabilities
      - Update security controls
      - Verify system integrity
    
    5_recovery:
      - Restore from clean backups
      - Monitor for re-infection
      - Verify functionality
      - Gradual service restoration
    
    6_lessons_learned:
      - Document timeline
      - Identify root cause
      - Update procedures
      - Share intelligence

severity_levels:
  critical:
    response_time: 15 minutes
    escalation: immediate
    examples:
      - Data breach
      - Ransomware
      - Complete system compromise
  
  high:
    response_time: 1 hour
    escalation: within 30 minutes
    examples:
      - Authenticated RCE
      - Privilege escalation
      - Service disruption
  
  medium:
    response_time: 4 hours
    escalation: within 2 hours
    examples:
      - Suspicious activity
      - Policy violations
      - Failed attack attempts
  
  low:
    response_time: 24 hours
    escalation: next business day
    examples:
      - Misconfiguration
      - Info disclosure
      - Best practice violations
```

### Incident Response Automation

```python
# src/incident_response/automation.py
class IncidentResponseAutomation:
    """Automated incident response actions."""
    
    async def respond_to_breach(self, incident_type: str, affected_resources: List[str]):
        """Automated breach response."""
        incident_id = self._create_incident()
        
        # Immediate containment
        if incident_type == "CREDENTIAL_COMPROMISE":
            await self._revoke_all_sessions(affected_resources)
            await self._force_password_reset(affected_resources)
            await self._enable_mfa_requirement(affected_resources)
        
        elif incident_type == "DATA_EXFILTRATION":
            await self._block_outbound_traffic()
            await self._isolate_affected_systems(affected_resources)
            await self._capture_network_traffic()
        
        elif incident_type == "RANSOMWARE":
            await self._shutdown_affected_systems(affected_resources)
            await self._isolate_network_segment()
            await self._activate_backup_systems()
        
        # Notification
        await self._notify_incident_response_team(incident_id)
        await self._notify_stakeholders(incident_id)
        
        # Evidence collection
        await self._collect_forensic_data(affected_resources)
        
        return incident_id
    
    async def _collect_forensic_data(self, resources: List[str]):
        """Collect forensic evidence."""
        for resource in resources:
            # Memory dump
            await self._capture_memory_dump(resource)
            
            # Disk image
            await self._create_disk_image(resource)
            
            # Logs
            await self._collect_logs(resource)
            
            # Network connections
            await self._capture_network_state(resource)
```

## Security Testing

### Security Test Suite

```python
# tests/security/test_security.py
import pytest
from src.security import SecurityValidator

class TestSecurityValidation:
    """Security validation tests."""
    
    @pytest.mark.parametrize("input,expected", [
        ("'; DROP TABLE users; --", False),
        ("1' OR '1'='1", False),
        ("normal query", True),
        ("SELECT * FROM", False),
    ])
    def test_sql_injection_prevention(self, input, expected):
        """Test SQL injection prevention."""
        validator = SecurityValidator()
        assert validator.is_safe_sql(input) == expected
    
    @pytest.mark.parametrize("input,expected", [
        ("<script>alert('XSS')</script>", False),
        ("javascript:alert(1)", False),
        ("<img src=x onerror=alert(1)>", False),
        ("normal text", True),
    ])
    def test_xss_prevention(self, input, expected):
        """Test XSS prevention."""
        validator = SecurityValidator()
        assert validator.is_safe_html(input) == expected
    
    def test_password_complexity(self):
        """Test password complexity requirements."""
        validator = SecurityValidator()
        
        # Too short
        assert not validator.is_strong_password("Pass1!")
        
        # No uppercase
        assert not validator.is_strong_password("password123!")
        
        # No special character
        assert not validator.is_strong_password("Password123")
        
        # Strong password
        assert validator.is_strong_password("MyStr0ng!Pass#2024")
    
    def test_rate_limiting(self):
        """Test rate limiting implementation."""
        from src.middleware import RateLimiter
        
        limiter = RateLimiter(requests=10, window=60)
        
        # Should allow first 10 requests
        for i in range(10):
            assert limiter.is_allowed("user1")
        
        # Should block 11th request
        assert not limiter.is_allowed("user1")
```

### Penetration Testing Checklist

```markdown
## Penetration Testing Checklist

### Authentication Testing
- [ ] Test for default credentials
- [ ] Test password brute force protection
- [ ] Test account lockout mechanism
- [ ] Test password reset vulnerability
- [ ] Test session management
- [ ] Test MFA bypass attempts
- [ ] Test JWT token manipulation

### Authorization Testing
- [ ] Test horizontal privilege escalation
- [ ] Test vertical privilege escalation
- [ ] Test IDOR vulnerabilities
- [ ] Test forced browsing
- [ ] Test API authorization

### Input Validation Testing
- [ ] Test SQL injection
- [ ] Test NoSQL injection
- [ ] Test LDAP injection
- [ ] Test XSS (reflected, stored, DOM)
- [ ] Test XXE injection
- [ ] Test command injection
- [ ] Test directory traversal
- [ ] Test file upload vulnerabilities

### Session Management Testing
- [ ] Test session fixation
- [ ] Test session timeout
- [ ] Test concurrent sessions
- [ ] Test session token randomness
- [ ] Test cookie security flags

### Cryptography Testing
- [ ] Test SSL/TLS configuration
- [ ] Test cipher strength
- [ ] Test certificate validation
- [ ] Test encryption of sensitive data
- [ ] Test key management

### Business Logic Testing
- [ ] Test race conditions
- [ ] Test workflow bypass
- [ ] Test price manipulation
- [ ] Test negative testing

### API Security Testing
- [ ] Test rate limiting
- [ ] Test API versioning
- [ ] Test API authentication
- [ ] Test API input validation
- [ ] Test GraphQL specific vulnerabilities
```

## Security Checklist

### Development Security Checklist

```markdown
## Development Security Checklist

### Code Security
- [ ] No hardcoded credentials
- [ ] No sensitive data in logs
- [ ] Input validation on all user inputs
- [ ] Output encoding for all outputs
- [ ] Parameterized queries for database access
- [ ] Secure random number generation
- [ ] No eval() or exec() with user input
- [ ] Dependencies updated and scanned

### Authentication & Authorization
- [ ] Strong password policy enforced
- [ ] MFA implemented for sensitive operations
- [ ] Session timeout configured
- [ ] Account lockout after failed attempts
- [ ] Role-based access control implemented
- [ ] JWT tokens properly validated
- [ ] API keys rotated regularly

### Data Protection
- [ ] Sensitive data encrypted at rest
- [ ] TLS 1.2+ for data in transit
- [ ] PII data masked in non-production
- [ ] Backup encryption enabled
- [ ] Key management system in use
- [ ] Data retention policies implemented

### Infrastructure Security
- [ ] Firewall rules configured
- [ ] Network segmentation implemented
- [ ] Intrusion detection system active
- [ ] Security patches applied
- [ ] Unnecessary services disabled
- [ ] Secure bastion host for SSH

### Monitoring & Logging
- [ ] Security events logged
- [ ] Audit trail maintained
- [ ] Log integrity protected
- [ ] Real-time alerting configured
- [ ] SIEM integration complete
- [ ] Incident response plan tested

### Compliance
- [ ] GDPR requirements met
- [ ] PCI DSS compliance (if applicable)
- [ ] HIPAA compliance (if applicable)
- [ ] SOC 2 controls implemented
- [ ] Regular security assessments
- [ ] Vulnerability scanning automated
```

### Production Deployment Checklist

```markdown
## Production Security Deployment Checklist

### Pre-Deployment
- [ ] Security scan completed
- [ ] Penetration test passed
- [ ] Code review completed
- [ ] Secrets removed from code
- [ ] Dependencies vulnerability scan
- [ ] SAST/DAST tools run

### Deployment
- [ ] SSL certificates valid
- [ ] Security headers configured
- [ ] WAF rules updated
- [ ] Rate limiting enabled
- [ ] DDoS protection active
- [ ] Backup system tested

### Post-Deployment
- [ ] Security monitoring active
- [ ] Alerts configured
- [ ] Incident response team notified
- [ ] Security documentation updated
- [ ] Compliance verification completed
- [ ] Security training conducted
```

## Summary

This security and compliance documentation provides comprehensive guidelines for securing the IT Glue MCP Server. Key components include:

1. **Defense in Depth**: Multiple security layers from network to application
2. **Strong Authentication**: MFA, JWT tokens, and session management
3. **Data Protection**: Encryption at rest and in transit, key management
4. **Compliance**: GDPR, PCI DSS, HIPAA implementations
5. **Monitoring**: Real-time security monitoring and audit logging
6. **Incident Response**: Automated response and recovery procedures
7. **Security Testing**: Comprehensive testing and validation

Remember:
- Security is everyone's responsibility
- Follow the principle of least privilege
- Regularly update and patch systems
- Monitor and respond to security events
- Maintain compliance with regulations
- Conduct regular security assessments

Stay secure! 🔒