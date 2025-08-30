# IT Glue API Integration Specification

## Table of Contents
1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Endpoint Mappings](#endpoint-mappings)
4. [Rate Limiting Strategy](#rate-limiting-strategy)
5. [Pagination Handling](#pagination-handling)
6. [Error Recovery Patterns](#error-recovery-patterns)
7. [Data Transformation](#data-transformation)
8. [Request/Response Examples](#requestresponse-examples)
9. [Performance Optimization](#performance-optimization)
10. [Testing the Integration](#testing-the-integration)

## Overview

The IT Glue API integration is the critical data pipeline for the MCP Server, providing access to all IT documentation, configurations, passwords, and flexible assets. This specification defines the complete integration approach including rate limiting, error handling, and data transformation.

### Base Configuration
```python
# Environment Variables
ITGLUE_API_URL=https://api.itglue.com
ITGLUE_API_KEY=your_api_key_here
ITGLUE_RATE_LIMIT_PER_SECOND=10
ITGLUE_MAX_RETRIES=3
ITGLUE_TIMEOUT_SECONDS=30
```

### API Version
- **Current Version:** v1
- **Base URL:** `https://api.itglue.com/`
- **Content Type:** `application/vnd.api+json`
- **Authentication:** API Key in header

## Authentication

### API Key Configuration
```python
class ITGlueAuth:
    """IT Glue API authentication handler"""
    
    def __init__(self):
        self.api_key = os.getenv("ITGLUE_API_KEY")
        if not self.api_key:
            raise ValueError("ITGLUE_API_KEY environment variable not set")
    
    def get_headers(self) -> Dict[str, str]:
        """Get authenticated headers for requests"""
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json"
        }
    
    def validate_key(self) -> bool:
        """Validate API key by making a test request"""
        try:
            response = requests.get(
                f"{ITGLUE_API_URL}/organizations?page[size]=1",
                headers=self.get_headers(),
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
```

## Endpoint Mappings

### Core Endpoints

| Resource | Endpoint | Method | Purpose | Rate Limit |
|----------|----------|--------|---------|------------|
| **Organizations** | `/organizations` | GET | List all organizations | 10/sec |
| **Organization** | `/organizations/{id}` | GET | Get single organization | 10/sec |
| **Configurations** | `/configurations` | GET | List configurations | 10/sec |
| **Configuration** | `/configurations/{id}` | GET | Get single configuration | 10/sec |
| **Flexible Assets** | `/flexible_assets` | GET | List flexible assets | 10/sec |
| **Flexible Asset** | `/flexible_assets/{id}` | GET | Get single asset | 10/sec |
| **Flexible Asset Types** | `/flexible_asset_types` | GET | Get asset schemas | 10/sec |
| **Passwords** | `/passwords` | GET | List passwords | 5/sec |
| **Password** | `/passwords/{id}` | GET | Get single password | 5/sec |
| **Documents** | `/documents` | GET | List documents | 10/sec |
| **Document** | `/documents/{id}` | GET | Get single document | 10/sec |
| **Configuration Types** | `/configuration_types` | GET | Get config types | 10/sec |
| **Configuration Statuses** | `/configuration_statuses` | GET | Get statuses | 10/sec |

### Relationship Endpoints

```python
# Relationship URL patterns
RELATIONSHIP_ENDPOINTS = {
    "configuration_interfaces": "/configurations/{id}/relationships/configuration_interfaces",
    "configuration_contacts": "/configurations/{id}/relationships/contacts",
    "asset_configurations": "/flexible_assets/{id}/relationships/configurations",
    "password_assets": "/passwords/{id}/relationships/flexible_assets",
    "document_assets": "/documents/{id}/relationships/flexible_assets"
}
```

### Filter Parameters

```python
class ITGlueFilters:
    """Filter parameter builder for IT Glue API"""
    
    @staticmethod
    def organization_filter(org_id: int) -> Dict[str, Any]:
        return {"filter[organization_id]": org_id}
    
    @staticmethod
    def modified_since_filter(timestamp: datetime) -> Dict[str, Any]:
        return {"filter[updated_at]": f">{timestamp.isoformat()}"}
    
    @staticmethod
    def type_filter(type_id: int) -> Dict[str, Any]:
        return {"filter[flexible_asset_type_id]": type_id}
    
    @staticmethod
    def name_filter(name: str) -> Dict[str, Any]:
        return {"filter[name]": name}
    
    @staticmethod
    def combine_filters(*filters) -> Dict[str, Any]:
        """Combine multiple filter dictionaries"""
        combined = {}
        for f in filters:
            combined.update(f)
        return combined
```

## Rate Limiting Strategy

### Adaptive Rate Limiter
```python
import asyncio
import time
from typing import Optional, Dict, Any
from collections import deque

class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on API responses"""
    
    def __init__(self, initial_rate: int = 10):
        self.rate_limit = initial_rate
        self.request_times = deque(maxlen=100)
        self.semaphore = asyncio.Semaphore(initial_rate)
        self.backoff_until = 0
        self.consecutive_errors = 0
    
    async def acquire(self):
        """Acquire permission to make a request"""
        # Check if in backoff period
        if time.time() < self.backoff_until:
            wait_time = self.backoff_until - time.time()
            await asyncio.sleep(wait_time)
        
        # Rate limiting
        async with self.semaphore:
            # Ensure minimum time between requests
            if self.request_times:
                elapsed = time.time() - self.request_times[-1]
                min_interval = 1.0 / self.rate_limit
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)
            
            self.request_times.append(time.time())
    
    def handle_response(self, response: httpx.Response):
        """Adjust rate limit based on response headers"""
        # Check rate limit headers
        if "X-RateLimit-Remaining" in response.headers:
            remaining = int(response.headers["X-RateLimit-Remaining"])
            
            # Slow down if getting close to limit
            if remaining < 10:
                self.rate_limit = max(1, self.rate_limit - 2)
                self.semaphore = asyncio.Semaphore(self.rate_limit)
            elif remaining > 50 and self.rate_limit < 10:
                # Speed up if we have headroom
                self.rate_limit = min(10, self.rate_limit + 1)
                self.semaphore = asyncio.Semaphore(self.rate_limit)
        
        # Handle rate limit errors
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            self.backoff_until = time.time() + retry_after
            self.consecutive_errors += 1
            
            # Exponential backoff for repeated errors
            if self.consecutive_errors > 3:
                self.rate_limit = max(1, self.rate_limit // 2)
                self.semaphore = asyncio.Semaphore(self.rate_limit)
        else:
            self.consecutive_errors = 0
```

### Request Queue Manager
```python
class RequestQueueManager:
    """Manages request queue with priority and retry logic"""
    
    def __init__(self, rate_limiter: AdaptiveRateLimiter):
        self.rate_limiter = rate_limiter
        self.priority_queue = asyncio.PriorityQueue()
        self.retry_queue = deque()
        self.max_retries = 3
    
    async def add_request(
        self, 
        endpoint: str, 
        params: Optional[Dict] = None,
        priority: int = 5
    ):
        """Add request to queue with priority (1=highest, 10=lowest)"""
        await self.priority_queue.put((
            priority,
            time.time(),
            {
                "endpoint": endpoint,
                "params": params,
                "retries": 0
            }
        ))
    
    async def process_queue(self):
        """Process requests from queue with rate limiting"""
        while True:
            # Get highest priority request
            priority, timestamp, request = await self.priority_queue.get()
            
            # Acquire rate limit permission
            await self.rate_limiter.acquire()
            
            try:
                response = await self._make_request(request)
                self.rate_limiter.handle_response(response)
                
                if response.status_code == 200:
                    yield response
                elif response.status_code == 429:
                    # Rate limited - requeue with lower priority
                    request["retries"] += 1
                    if request["retries"] < self.max_retries:
                        await self.priority_queue.put((
                            min(10, priority + 2),
                            time.time(),
                            request
                        ))
                else:
                    # Other error - retry with exponential backoff
                    await self._handle_error(request, priority)
                    
            except Exception as e:
                await self._handle_error(request, priority)
```

## Pagination Handling

### Cursor-Based Pagination Handler
```python
class PaginationHandler:
    """Handles IT Glue API pagination with cursor support"""
    
    def __init__(self, page_size: int = 50):
        self.page_size = min(page_size, 100)  # IT Glue max is 100
    
    async def paginate_all(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all pages of results"""
        all_data = []
        params = params or {}
        params["page[size]"] = self.page_size
        
        next_url = endpoint
        
        while next_url:
            response = await client.get(next_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            all_data.extend(data.get("data", []))
            
            # Get next page URL from links
            links = data.get("links", {})
            next_url = links.get("next")
            
            # Clear params for subsequent requests (URL has params)
            params = {}
            
            # Optional: yield progress
            yield {
                "page_data": data.get("data", []),
                "total": data.get("meta", {}).get("total-count"),
                "current": len(all_data)
            }
    
    async def paginate_chunked(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        chunk_size: int = 500,
        params: Optional[Dict] = None
    ) -> AsyncIterator[List[Dict]]:
        """Yield data in chunks for memory efficiency"""
        chunk = []
        
        async for page in self.paginate_all(client, endpoint, params):
            chunk.extend(page["page_data"])
            
            if len(chunk) >= chunk_size:
                yield chunk[:chunk_size]
                chunk = chunk[chunk_size:]
        
        # Yield remaining data
        if chunk:
            yield chunk
```

### Parallel Pagination
```python
class ParallelPaginator:
    """Fetch multiple resources in parallel with pagination"""
    
    def __init__(self, rate_limiter: AdaptiveRateLimiter):
        self.rate_limiter = rate_limiter
        self.pagination_handler = PaginationHandler()
    
    async def fetch_organization_data(
        self,
        client: httpx.AsyncClient,
        org_id: int
    ) -> Dict[str, List]:
        """Fetch all data for an organization in parallel"""
        
        tasks = {
            "configurations": self._fetch_configurations(client, org_id),
            "flexible_assets": self._fetch_flexible_assets(client, org_id),
            "passwords": self._fetch_passwords(client, org_id),
            "documents": self._fetch_documents(client, org_id)
        }
        
        results = {}
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception as e:
                logger.error(f"Failed to fetch {name}: {e}")
                results[name] = []
        
        return results
    
    async def _fetch_configurations(
        self,
        client: httpx.AsyncClient,
        org_id: int
    ) -> List[Dict]:
        """Fetch all configurations for organization"""
        params = {"filter[organization_id]": org_id}
        
        all_configs = []
        async for chunk in self.pagination_handler.paginate_chunked(
            client, 
            "/configurations",
            params=params
        ):
            all_configs.extend(chunk)
        
        return all_configs
```

## Error Recovery Patterns

### Comprehensive Error Handler
```python
from enum import Enum
from typing import Optional, Callable

class ErrorType(Enum):
    RATE_LIMIT = "rate_limit"
    NETWORK = "network"
    TIMEOUT = "timeout"
    AUTH = "authentication"
    NOT_FOUND = "not_found"
    SERVER = "server_error"
    UNKNOWN = "unknown"

class ErrorRecoveryStrategy:
    """Defines recovery strategies for different error types"""
    
    STRATEGIES = {
        ErrorType.RATE_LIMIT: {
            "retry": True,
            "backoff": "exponential",
            "max_retries": 5,
            "initial_delay": 60
        },
        ErrorType.NETWORK: {
            "retry": True,
            "backoff": "exponential",
            "max_retries": 3,
            "initial_delay": 1
        },
        ErrorType.TIMEOUT: {
            "retry": True,
            "backoff": "linear",
            "max_retries": 2,
            "initial_delay": 5
        },
        ErrorType.AUTH: {
            "retry": False,
            "action": "refresh_auth"
        },
        ErrorType.NOT_FOUND: {
            "retry": False,
            "action": "skip"
        },
        ErrorType.SERVER: {
            "retry": True,
            "backoff": "exponential",
            "max_retries": 3,
            "initial_delay": 10
        }
    }
    
    @classmethod
    def get_strategy(cls, error_type: ErrorType) -> Dict:
        return cls.STRATEGIES.get(error_type, cls.STRATEGIES[ErrorType.UNKNOWN])

class ResilientAPIClient:
    """API client with comprehensive error recovery"""
    
    def __init__(self):
        self.auth = ITGlueAuth()
        self.rate_limiter = AdaptiveRateLimiter()
        self.circuit_breaker = CircuitBreaker()
    
    async def request_with_recovery(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Optional[Dict]:
        """Make request with automatic error recovery"""
        
        # Check circuit breaker
        if not self.circuit_breaker.is_closed():
            raise Exception("Circuit breaker is open - API unavailable")
        
        error_type = None
        last_error = None
        
        for attempt in range(5):  # Max attempts across all strategies
            try:
                # Rate limiting
                await self.rate_limiter.acquire()
                
                # Make request
                response = await self._make_request(method, endpoint, **kwargs)
                
                # Success - reset circuit breaker
                self.circuit_breaker.record_success()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                error_type = self._classify_error(e)
                strategy = ErrorRecoveryStrategy.get_strategy(error_type)
                
                if not strategy["retry"] or attempt >= strategy.get("max_retries", 0):
                    self.circuit_breaker.record_failure()
                    raise
                
                # Calculate backoff
                delay = self._calculate_backoff(
                    attempt,
                    strategy["initial_delay"],
                    strategy["backoff"]
                )
                
                logger.warning(f"Error {error_type}: retrying in {delay}s")
                await asyncio.sleep(delay)
                
            except Exception as e:
                last_error = e
                self.circuit_breaker.record_failure()
                
                # Network errors - retry with backoff
                if attempt < 3:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
        
        raise last_error or Exception("Max retries exceeded")
    
    def _classify_error(self, error: httpx.HTTPStatusError) -> ErrorType:
        """Classify error type from response"""
        status = error.response.status_code
        
        if status == 429:
            return ErrorType.RATE_LIMIT
        elif status == 401:
            return ErrorType.AUTH
        elif status == 404:
            return ErrorType.NOT_FOUND
        elif status == 408:
            return ErrorType.TIMEOUT
        elif 500 <= status < 600:
            return ErrorType.SERVER
        else:
            return ErrorType.UNKNOWN
    
    def _calculate_backoff(
        self,
        attempt: int,
        initial_delay: int,
        strategy: str
    ) -> int:
        """Calculate backoff delay"""
        if strategy == "exponential":
            return initial_delay * (2 ** attempt)
        elif strategy == "linear":
            return initial_delay * (attempt + 1)
        else:
            return initial_delay

class CircuitBreaker:
    """Circuit breaker pattern for API protection"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def is_closed(self) -> bool:
        """Check if circuit breaker allows requests"""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
                return True
            return False
        
        return self.state == "half-open"
    
    def record_success(self):
        """Record successful request"""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        """Record failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.error(f"Circuit breaker opened after {self.failure_count} failures")
```

## Data Transformation

### IT Glue to Internal Model Transformation
```python
from typing import Dict, Any, Optional
from datetime import datetime

class DataTransformer:
    """Transform IT Glue API responses to internal models"""
    
    @staticmethod
    def transform_organization(data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform IT Glue organization to internal model"""
        attributes = data.get("attributes", {})
        
        return {
            "id": int(data["id"]),
            "name": attributes.get("name"),
            "description": attributes.get("description"),
            "created_at": parse_datetime(attributes.get("created-at")),
            "updated_at": parse_datetime(attributes.get("updated-at")),
            "settings": {
                "alert_email": attributes.get("alert"),
                "primary_contact": attributes.get("primary-contact-name"),
                "quick_notes": attributes.get("quick-notes")
            }
        }
    
    @staticmethod
    def transform_configuration(data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform IT Glue configuration to internal model"""
        attributes = data.get("attributes", {})
        
        return {
            "id": int(data["id"]),
            "organization_id": int(attributes.get("organization-id")),
            "name": attributes.get("name"),
            "configuration_type": attributes.get("configuration-type-name"),
            "configuration_type_id": attributes.get("configuration-type-id"),
            "status": attributes.get("configuration-status-name"),
            "ip_address": attributes.get("primary-ip"),
            "mac_address": attributes.get("mac-address"),
            "hostname": attributes.get("hostname"),
            "serial_number": attributes.get("serial-number"),
            "asset_tag": attributes.get("asset-tag"),
            "operating_system": attributes.get("operating-system"),
            "notes": attributes.get("notes"),
            "attributes": attributes,  # Store full attributes for flexibility
            "relationships": data.get("relationships", {}),
            "created_at": parse_datetime(attributes.get("created-at")),
            "updated_at": parse_datetime(attributes.get("updated-at"))
        }
    
    @staticmethod
    def transform_flexible_asset(data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform IT Glue flexible asset to internal model"""
        attributes = data.get("attributes", {})
        
        return {
            "id": int(data["id"]),
            "organization_id": int(attributes.get("organization-id")),
            "flexible_asset_type_id": int(attributes.get("flexible-asset-type-id")),
            "name": attributes.get("name"),
            "traits": attributes.get("traits", {}),  # Dynamic fields based on type
            "created_at": parse_datetime(attributes.get("created-at")),
            "updated_at": parse_datetime(attributes.get("updated-at"))
        }
    
    @staticmethod
    def transform_password(data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform IT Glue password to internal model"""
        attributes = data.get("attributes", {})
        
        return {
            "id": int(data["id"]),
            "organization_id": int(attributes.get("organization-id")),
            "name": attributes.get("name"),
            "username": attributes.get("username"),
            "password": attributes.get("password"),  # Already encrypted
            "url": attributes.get("url"),
            "notes": attributes.get("notes"),
            "password_category": attributes.get("password-category-name"),
            "restricted": attributes.get("restricted"),
            "created_at": parse_datetime(attributes.get("created-at")),
            "updated_at": parse_datetime(attributes.get("updated-at"))
        }
    
    @staticmethod
    def transform_document(data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform IT Glue document to internal model"""
        attributes = data.get("attributes", {})
        
        return {
            "id": int(data["id"]),
            "organization_id": int(attributes.get("organization-id")),
            "name": attributes.get("name"),
            "content": attributes.get("content"),  # HTML content
            "content_text": strip_html(attributes.get("content")),  # Plain text
            "folder": attributes.get("folder-name"),
            "created_at": parse_datetime(attributes.get("created-at")),
            "updated_at": parse_datetime(attributes.get("updated-at")),
            "published_at": parse_datetime(attributes.get("published-at"))
        }

class BulkTransformer:
    """Efficient bulk data transformation"""
    
    def __init__(self):
        self.transformer = DataTransformer()
    
    async def transform_batch(
        self,
        data_type: str,
        items: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> AsyncIterator[List[Dict]]:
        """Transform data in batches for efficiency"""
        
        transform_map = {
            "organizations": self.transformer.transform_organization,
            "configurations": self.transformer.transform_configuration,
            "flexible_assets": self.transformer.transform_flexible_asset,
            "passwords": self.transformer.transform_password,
            "documents": self.transformer.transform_document
        }
        
        transform_func = transform_map.get(data_type)
        if not transform_func:
            raise ValueError(f"Unknown data type: {data_type}")
        
        batch = []
        for item in items:
            try:
                transformed = transform_func(item)
                batch.append(transformed)
                
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
            except Exception as e:
                logger.error(f"Failed to transform {data_type} item {item.get('id')}: {e}")
        
        # Yield remaining items
        if batch:
            yield batch

def parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """Parse IT Glue datetime format"""
    if not date_str:
        return None
    
    try:
        # IT Glue format: 2024-01-30T10:30:00.000Z
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except:
        return None

def strip_html(html: Optional[str]) -> Optional[str]:
    """Strip HTML tags from content"""
    if not html:
        return None
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(strip=True)
```

## Request/Response Examples

### Example 1: Get Organizations
```python
# Request
GET https://api.itglue.com/organizations?page[size]=50
Headers:
  x-api-key: your_api_key
  Content-Type: application/vnd.api+json

# Response
{
  "data": [
    {
      "id": "12345",
      "type": "organizations",
      "attributes": {
        "name": "Company A",
        "description": "Main client company",
        "created-at": "2023-01-15T10:00:00.000Z",
        "updated-at": "2024-01-30T15:30:00.000Z",
        "alert": "support@companya.com",
        "primary-contact-name": "John Doe"
      }
    }
  ],
  "links": {
    "self": "https://api.itglue.com/organizations?page[number]=1&page[size]=50",
    "next": "https://api.itglue.com/organizations?page[number]=2&page[size]=50",
    "last": "https://api.itglue.com/organizations?page[number]=10&page[size]=50"
  },
  "meta": {
    "current-page": 1,
    "next-page": 2,
    "prev-page": null,
    "total-pages": 10,
    "total-count": 487
  }
}
```

### Example 2: Get Configurations with Filters
```python
# Request
GET https://api.itglue.com/configurations?filter[organization_id]=12345&filter[configuration_type_id]=1
Headers:
  x-api-key: your_api_key

# Response
{
  "data": [
    {
      "id": "67890",
      "type": "configurations",
      "attributes": {
        "organization-id": 12345,
        "name": "DC01-Server",
        "configuration-type-id": 1,
        "configuration-type-name": "Server",
        "configuration-status-name": "Active",
        "primary-ip": "192.168.1.10",
        "mac-address": "00:1B:44:11:3A:B7",
        "hostname": "DC01",
        "serial-number": "SRV123456",
        "operating-system": "Windows Server 2019",
        "notes": "Primary domain controller"
      },
      "relationships": {
        "configuration-interfaces": {
          "data": [
            {"type": "configuration_interfaces", "id": "111"}
          ]
        },
        "configuration-contacts": {
          "data": []
        }
      }
    }
  ]
}
```

### Example 3: Error Response
```python
# Response for rate limit error
{
  "errors": [
    {
      "status": 429,
      "title": "Too Many Requests",
      "detail": "Rate limit exceeded. Please retry after 60 seconds.",
      "source": {
        "pointer": "/data"
      }
    }
  ]
}

# Response for authentication error
{
  "errors": [
    {
      "status": 401,
      "title": "Unauthorized",
      "detail": "Invalid API key provided",
      "source": {
        "pointer": "/headers/x-api-key"
      }
    }
  ]
}
```

## Performance Optimization

### Caching Strategy
```python
class ITGlueCacheManager:
    """Intelligent caching for IT Glue data"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl_map = {
            "organizations": 3600,  # 1 hour
            "configuration_types": 86400,  # 24 hours
            "flexible_asset_types": 86400,  # 24 hours
            "configurations": 900,  # 15 minutes
            "flexible_assets": 900,  # 15 minutes
            "passwords": 60,  # 1 minute (sensitive)
            "documents": 1800  # 30 minutes
        }
    
    async def get_or_fetch(
        self,
        key: str,
        fetch_func: Callable,
        data_type: str
    ) -> Any:
        """Get from cache or fetch from API"""
        
        # Try cache first
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        
        # Fetch from API
        data = await fetch_func()
        
        # Cache with appropriate TTL
        ttl = self.ttl_map.get(data_type, 300)
        await self.redis.setex(
            key,
            ttl,
            json.dumps(data)
        )
        
        return data
    
    async def invalidate_org_cache(self, org_id: int):
        """Invalidate all cache for an organization"""
        pattern = f"itglue:org:{org_id}:*"
        
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(
                cursor,
                match=pattern,
                count=100
            )
            
            if keys:
                await self.redis.delete(*keys)
            
            if cursor == 0:
                break
```

### Batch Processing
```python
class BatchProcessor:
    """Process IT Glue data in efficient batches"""
    
    def __init__(self, db_session, vector_db, graph_db):
        self.db = db_session
        self.vector_db = vector_db
        self.graph_db = graph_db
    
    async def process_configurations_batch(
        self,
        configs: List[Dict],
        batch_size: int = 50
    ):
        """Process configurations in batches"""
        
        for i in range(0, len(configs), batch_size):
            batch = configs[i:i + batch_size]
            
            # Prepare bulk operations
            db_objects = []
            vector_updates = []
            graph_updates = []
            
            for config in batch:
                # Database object
                db_objects.append(Configuration(**config))
                
                # Vector embedding
                text = f"{config['name']} {config['configuration_type']} {config.get('ip_address', '')}"
                embedding = await generate_embedding(text)
                vector_updates.append({
                    "id": config["id"],
                    "vector": embedding,
                    "payload": {
                        "org_id": config["organization_id"],
                        "name": config["name"],
                        "type": config["configuration_type"]
                    }
                })
                
                # Graph relationships
                graph_updates.append({
                    "id": config["id"],
                    "properties": {
                        "name": config["name"],
                        "ip": config.get("ip_address")
                    }
                })
            
            # Execute bulk operations
            await asyncio.gather(
                self.db.bulk_insert_mappings(Configuration, db_objects),
                self.vector_db.upsert_batch("configurations", vector_updates),
                self.graph_db.merge_nodes_batch("Configuration", graph_updates)
            )
```

## Testing the Integration

### Integration Test Suite
```python
import pytest
from unittest.mock import Mock, patch
import httpx

class TestITGlueIntegration:
    """Test suite for IT Glue API integration"""
    
    @pytest.fixture
    def mock_client(self):
        """Create mock HTTP client"""
        client = Mock(spec=httpx.AsyncClient)
        return client
    
    @pytest.fixture
    def api_client(self):
        """Create API client instance"""
        return ResilientAPIClient()
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, api_client, mock_client):
        """Test rate limiting behavior"""
        # Simulate rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        
        with patch.object(api_client, '_make_request', side_effect=httpx.HTTPStatusError(
            "Rate limited",
            request=Mock(),
            response=mock_response
        )):
            with pytest.raises(Exception):
                await api_client.request_with_recovery(
                    "GET",
                    "/organizations"
                )
            
            # Verify backoff was applied
            assert api_client.rate_limiter.backoff_until > time.time()
    
    @pytest.mark.asyncio
    async def test_pagination(self):
        """Test pagination handling"""
        paginator = PaginationHandler(page_size=2)
        
        # Mock responses for 3 pages
        mock_responses = [
            {
                "data": [{"id": "1"}, {"id": "2"}],
                "links": {"next": "/organizations?page=2"}
            },
            {
                "data": [{"id": "3"}, {"id": "4"}],
                "links": {"next": "/organizations?page=3"}
            },
            {
                "data": [{"id": "5"}],
                "links": {}
            }
        ]
        
        # Test pagination collection
        all_data = []
        for response in mock_responses:
            all_data.extend(response["data"])
        
        assert len(all_data) == 5
    
    @pytest.mark.asyncio
    async def test_data_transformation(self):
        """Test data transformation"""
        transformer = DataTransformer()
        
        # Sample IT Glue response
        itglue_config = {
            "id": "12345",
            "type": "configurations",
            "attributes": {
                "organization-id": 1,
                "name": "Test-Server",
                "configuration-type-name": "Server",
                "primary-ip": "192.168.1.100"
            }
        }
        
        # Transform
        internal_model = transformer.transform_configuration(itglue_config)
        
        # Verify transformation
        assert internal_model["id"] == 12345
        assert internal_model["name"] == "Test-Server"
        assert internal_model["ip_address"] == "192.168.1.100"
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, api_client):
        """Test error recovery strategies"""
        # Test network error recovery
        with patch.object(api_client, '_make_request') as mock_request:
            # Fail twice, then succeed
            mock_request.side_effect = [
                httpx.NetworkError("Connection failed"),
                httpx.NetworkError("Connection failed"),
                Mock(json=lambda: {"data": []})
            ]
            
            result = await api_client.request_with_recovery(
                "GET",
                "/organizations"
            )
            
            assert result == {"data": []}
            assert mock_request.call_count == 3
```

### Load Testing
```python
import asyncio
import time
from statistics import mean, stdev

async def load_test_api_integration():
    """Load test the IT Glue API integration"""
    
    client = ResilientAPIClient()
    
    # Test parameters
    num_requests = 100
    concurrent_requests = 10
    
    async def make_request():
        start = time.time()
        try:
            await client.request_with_recovery(
                "GET",
                "/organizations",
                params={"page[size]": 1}
            )
            return time.time() - start
        except Exception as e:
            return None
    
    # Run concurrent requests
    tasks = []
    for _ in range(num_requests):
        tasks.append(make_request())
        
        # Limit concurrency
        if len(tasks) >= concurrent_requests:
            results = await asyncio.gather(*tasks)
            tasks = []
    
    # Process results
    response_times = [r for r in results if r is not None]
    error_count = len([r for r in results if r is None])
    
    print(f"Load Test Results:")
    print(f"Total Requests: {num_requests}")
    print(f"Successful: {len(response_times)}")
    print(f"Failed: {error_count}")
    print(f"Avg Response Time: {mean(response_times):.2f}s")
    print(f"Std Dev: {stdev(response_times):.2f}s")
    print(f"Min: {min(response_times):.2f}s")
    print(f"Max: {max(response_times):.2f}s")
```

## Best Practices

1. **Always use rate limiting** - Never bypass the rate limiter
2. **Cache strategically** - Cache stable data longer (types, categories)
3. **Handle errors gracefully** - Use circuit breaker pattern
4. **Transform data once** - Transform on ingestion, not on query
5. **Paginate efficiently** - Use cursor-based pagination for large datasets
6. **Monitor API usage** - Track rate limit headers and adjust
7. **Test error scenarios** - Test rate limits, timeouts, and failures
8. **Use async operations** - Leverage asyncio for concurrent requests
9. **Validate API responses** - Always validate data structure before transformation
10. **Log comprehensively** - Log all API interactions for debugging

---

**Version:** 1.0
**Last Updated:** 2025-01-30
**Status:** Production Ready