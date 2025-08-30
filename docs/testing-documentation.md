# IT Glue MCP Server - Testing Documentation 🧪

## Overview

This comprehensive testing guide covers all aspects of testing the IT Glue MCP Server, from unit tests to end-to-end integration testing, performance testing, and production validation.

## Table of Contents

1. [Testing Strategy](#testing-strategy)
2. [Test Environment Setup](#test-environment-setup)
3. [Unit Testing](#unit-testing)
4. [Integration Testing](#integration-testing)
5. [End-to-End Testing](#end-to-end-testing)
6. [Performance Testing](#performance-testing)
7. [Security Testing](#security-testing)
8. [MCP Protocol Testing](#mcp-protocol-testing)
9. [Test Data Management](#test-data-management)
10. [CI/CD Pipeline Testing](#cicd-pipeline-testing)
11. [Test Coverage & Metrics](#test-coverage--metrics)
12. [Testing Best Practices](#testing-best-practices)

## Testing Strategy

### Testing Pyramid

```
         /\
        /E2E\        <- End-to-End Tests (5%)
       /------\
      /  Integ  \    <- Integration Tests (15%)
     /------------\
    /   Component  \  <- Component Tests (30%)
   /----------------\
  /      Unit        \ <- Unit Tests (50%)
 /____________________\
```

### Test Categories

| Category | Purpose | Tools | Frequency |
|----------|---------|-------|-----------|
| Unit | Test individual functions | pytest, unittest.mock | Every commit |
| Integration | Test component interactions | pytest, testcontainers | Every PR |
| E2E | Test complete workflows | pytest, Selenium | Daily |
| Performance | Test load and stress | locust, k6 | Weekly |
| Security | Test vulnerabilities | bandit, safety | Every release |
| MCP Protocol | Test MCP compliance | custom fixtures | Every PR |

## Test Environment Setup

### Prerequisites Installation

```bash
# Install testing dependencies
pip install -r requirements-test.txt

# requirements-test.txt
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-timeout==2.2.0
pytest-xdist==3.5.0
testcontainers==3.7.1
factory-boy==3.3.0
faker==20.1.0
hypothesis==6.92.1
locust==2.17.0
responses==0.24.1
freezegun==1.4.0
```

### Test Configuration

```python
# tests/conftest.py
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from testcontainers.postgres import PostgresContainer
from testcontainers.compose import DockerCompose

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db():
    """Provide test database"""
    with PostgresContainer("postgres:15-alpine") as postgres:
        engine = create_async_engine(postgres.get_connection_url())
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine
        await engine.dispose()

@pytest.fixture
async def db_session(test_db) -> AsyncGenerator[AsyncSession, None]:
    """Provide database session for tests"""
    async with AsyncSession(test_db) as session:
        yield session
        await session.rollback()

@pytest.fixture(scope="session")
def docker_services():
    """Start all required services"""
    compose = DockerCompose(
        "tests/docker-compose.test.yml",
        pull=True,
        build=True
    )
    with compose:
        compose.wait_for("http://localhost:8080/health")
        yield compose

@pytest.fixture
def mock_itglue_api():
    """Mock IT Glue API responses"""
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://api.itglue.com/organizations",
            json={"data": [{"id": "1", "attributes": {"name": "Test Org"}}]},
            status=200
        )
        yield rsps
```

### Test Docker Compose

```yaml
# tests/docker-compose.test.yml
version: '3.8'

services:
  test-postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: test_db
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_pass
    ports:
      - "5433:5432"
    tmpfs:
      - /var/lib/postgresql/data

  test-neo4j:
    image: neo4j:5-community
    environment:
      NEO4J_AUTH: neo4j/test_password
      NEO4J_dbms_memory_heap_max__size: 512M
    ports:
      - "7475:7474"
      - "7688:7687"
    tmpfs:
      - /data

  test-redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"
    command: redis-server --save ""

  test-qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6334:6333"
    tmpfs:
      - /qdrant/storage
```

## Unit Testing

### Service Layer Tests

```python
# tests/unit/services/test_query_handler.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.services.query_handler import QueryHandler
from src.models.query import QueryRequest, QueryResponse

class TestQueryHandler:
    @pytest.fixture
    def query_handler(self):
        return QueryHandler()
    
    @pytest.fixture
    def mock_vector_store(self):
        with patch('src.services.query_handler.QdrantClient') as mock:
            mock.return_value.search = AsyncMock(return_value=[
                {"id": "1", "score": 0.95, "payload": {"content": "Test content"}}
            ])
            yield mock
    
    @pytest.mark.asyncio
    async def test_process_query_success(self, query_handler, mock_vector_store):
        """Test successful query processing"""
        request = QueryRequest(
            query="What is the backup policy?",
            company_id="123",
            limit=5
        )
        
        response = await query_handler.process_query(request)
        
        assert isinstance(response, QueryResponse)
        assert response.success is True
        assert len(response.results) > 0
        assert response.results[0].score >= 0.9
    
    @pytest.mark.asyncio
    async def test_process_query_with_filters(self, query_handler):
        """Test query with document type filters"""
        request = QueryRequest(
            query="Show me network diagrams",
            filters={"document_type": "diagram"},
            limit=10
        )
        
        response = await query_handler.process_query(request)
        
        assert all(r.document_type == "diagram" for r in response.results)
    
    @pytest.mark.asyncio
    async def test_query_validation(self, query_handler):
        """Test query validation logic"""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await query_handler.process_query(
                QueryRequest(query="", company_id="123")
            )
    
    @pytest.mark.parametrize("query,expected_intent", [
        ("What is the password for", "password_lookup"),
        ("Show me the network diagram", "diagram_request"),
        ("List all servers", "inventory_query"),
        ("How do I configure", "configuration_guide")
    ])
    async def test_intent_detection(self, query_handler, query, expected_intent):
        """Test query intent detection"""
        detected_intent = await query_handler.detect_intent(query)
        assert detected_intent == expected_intent
```

### Validation Tests

```python
# tests/unit/services/test_validation.py
import pytest
from src.services.validation import ValidationService
from src.models.document import Document

class TestValidationService:
    @pytest.fixture
    def validator(self):
        return ValidationService()
    
    def test_validate_response_no_hallucination(self, validator):
        """Test that validation prevents hallucination"""
        source_docs = [
            Document(content="Server IP is 192.168.1.100"),
            Document(content="Backup runs at 2 AM daily")
        ]
        
        # Valid response - information from sources
        response = "The server IP is 192.168.1.100 and backups run at 2 AM"
        assert validator.validate_response(response, source_docs) is True
        
        # Invalid response - hallucinated information
        response = "The server IP is 192.168.1.100 with 16GB RAM"
        assert validator.validate_response(response, source_docs) is False
    
    def test_validate_sensitive_data_masking(self, validator):
        """Test sensitive data detection and masking"""
        content = "Password: SecretPass123! API Key: sk-1234567890"
        
        masked = validator.mask_sensitive_data(content)
        
        assert "SecretPass123!" not in masked
        assert "sk-1234567890" not in masked
        assert "***" in masked
    
    @pytest.mark.parametrize("content,expected_valid", [
        ("Normal documentation content", True),
        ("<script>alert('XSS')</script>", False),
        ("'; DROP TABLE users; --", False),
        ("../../etc/passwd", False)
    ])
    def test_content_sanitization(self, validator, content, expected_valid):
        """Test content sanitization for security"""
        is_safe = validator.is_safe_content(content)
        assert is_safe == expected_valid
```

### API Client Tests

```python
# tests/unit/clients/test_itglue_client.py
import pytest
from unittest.mock import Mock, patch
import responses
from src.clients.itglue_client import ITGlueClient
from src.models.itglue import Organization, Configuration

class TestITGlueClient:
    @pytest.fixture
    def client(self):
        return ITGlueClient(api_key="test_key")
    
    @responses.activate
    def test_get_organizations(self, client):
        """Test fetching organizations"""
        responses.add(
            responses.GET,
            "https://api.itglue.com/organizations",
            json={
                "data": [
                    {
                        "id": "1",
                        "type": "organizations",
                        "attributes": {
                            "name": "Acme Corp",
                            "created_at": "2024-01-01T00:00:00Z"
                        }
                    }
                ]
            },
            status=200
        )
        
        orgs = client.get_organizations()
        
        assert len(orgs) == 1
        assert orgs[0].name == "Acme Corp"
        assert isinstance(orgs[0], Organization)
    
    @responses.activate
    def test_rate_limiting(self, client):
        """Test rate limit handling"""
        responses.add(
            responses.GET,
            "https://api.itglue.com/configurations",
            status=429,
            headers={"Retry-After": "5"}
        )
        
        with pytest.raises(RateLimitError) as exc:
            client.get_configurations()
        
        assert exc.value.retry_after == 5
    
    @responses.activate
    def test_pagination(self, client):
        """Test pagination handling"""
        # First page
        responses.add(
            responses.GET,
            "https://api.itglue.com/configurations?page[number]=1",
            json={
                "data": [{"id": "1", "type": "configurations"}],
                "links": {"next": "https://api.itglue.com/configurations?page[number]=2"}
            }
        )
        # Second page
        responses.add(
            responses.GET,
            "https://api.itglue.com/configurations?page[number]=2",
            json={
                "data": [{"id": "2", "type": "configurations"}],
                "links": {"next": None}
            }
        )
        
        configs = list(client.get_all_configurations())
        
        assert len(configs) == 2
        assert configs[0].id == "1"
        assert configs[1].id == "2"
```

## Integration Testing

### Database Integration Tests

```python
# tests/integration/test_database_integration.py
import pytest
from sqlalchemy import select
from src.models.database import Document, Query, User
from src.repositories.document_repository import DocumentRepository

@pytest.mark.integration
class TestDatabaseIntegration:
    @pytest.mark.asyncio
    async def test_document_crud(self, db_session):
        """Test document CRUD operations"""
        repo = DocumentRepository(db_session)
        
        # Create
        doc = await repo.create(
            title="Test Document",
            content="Test content",
            company_id="123"
        )
        assert doc.id is not None
        
        # Read
        retrieved = await repo.get(doc.id)
        assert retrieved.title == "Test Document"
        
        # Update
        updated = await repo.update(doc.id, content="Updated content")
        assert updated.content == "Updated content"
        
        # Delete
        await repo.delete(doc.id)
        deleted = await repo.get(doc.id)
        assert deleted is None
    
    @pytest.mark.asyncio
    async def test_query_logging(self, db_session):
        """Test query logging and retrieval"""
        query = Query(
            user_id="user123",
            query_text="Test query",
            response="Test response",
            execution_time_ms=150,
            success=True
        )
        
        db_session.add(query)
        await db_session.commit()
        
        # Retrieve queries
        result = await db_session.execute(
            select(Query).where(Query.user_id == "user123")
        )
        queries = result.scalars().all()
        
        assert len(queries) == 1
        assert queries[0].execution_time_ms == 150
```

### Vector Store Integration Tests

```python
# tests/integration/test_vector_store.py
import pytest
import numpy as np
from src.services.vector_store import VectorStoreService
from src.models.embedding import DocumentEmbedding

@pytest.mark.integration
class TestVectorStoreIntegration:
    @pytest.fixture
    async def vector_store(self, docker_services):
        service = VectorStoreService(
            host="localhost",
            port=6334
        )
        await service.initialize()
        yield service
        await service.cleanup()
    
    @pytest.mark.asyncio
    async def test_embedding_storage_retrieval(self, vector_store):
        """Test storing and retrieving embeddings"""
        # Create test embeddings
        doc_embedding = DocumentEmbedding(
            document_id="doc123",
            content="This is a test document about network configuration",
            embedding=np.random.rand(768).tolist()
        )
        
        # Store
        await vector_store.upsert(doc_embedding)
        
        # Search
        query_embedding = np.random.rand(768).tolist()
        results = await vector_store.search(
            query_embedding,
            limit=5
        )
        
        assert len(results) > 0
        assert results[0].document_id == "doc123"
    
    @pytest.mark.asyncio
    async def test_filtered_search(self, vector_store):
        """Test vector search with metadata filters"""
        # Store documents with different types
        for i, doc_type in enumerate(["config", "password", "diagram"]):
            embedding = DocumentEmbedding(
                document_id=f"doc{i}",
                content=f"Document of type {doc_type}",
                embedding=np.random.rand(768).tolist(),
                metadata={"type": doc_type, "company_id": "123"}
            )
            await vector_store.upsert(embedding)
        
        # Search with filter
        results = await vector_store.search(
            query_embedding=np.random.rand(768).tolist(),
            filters={"type": "config", "company_id": "123"},
            limit=10
        )
        
        assert all(r.metadata["type"] == "config" for r in results)
```

### Graph Database Integration Tests

```python
# tests/integration/test_neo4j_integration.py
import pytest
from src.services.graph_service import GraphService
from src.models.relationships import EntityRelationship

@pytest.mark.integration
class TestNeo4jIntegration:
    @pytest.fixture
    async def graph_service(self, docker_services):
        service = GraphService(
            uri="bolt://localhost:7688",
            user="neo4j",
            password="test_password"
        )
        await service.connect()
        yield service
        await service.close()
    
    @pytest.mark.asyncio
    async def test_relationship_creation(self, graph_service):
        """Test creating and querying relationships"""
        # Create entities and relationships
        await graph_service.create_entity("Server", {"name": "web-01", "ip": "192.168.1.10"})
        await graph_service.create_entity("Application", {"name": "webapp", "port": 8080})
        await graph_service.create_relationship(
            "web-01", "HOSTS", "webapp",
            {"since": "2024-01-01"}
        )
        
        # Query relationships
        relationships = await graph_service.get_relationships("web-01")
        
        assert len(relationships) == 1
        assert relationships[0].target == "webapp"
        assert relationships[0].type == "HOSTS"
    
    @pytest.mark.asyncio
    async def test_path_finding(self, graph_service):
        """Test finding paths between entities"""
        # Create network topology
        await graph_service.create_entity("Server", {"name": "server1"})
        await graph_service.create_entity("Switch", {"name": "switch1"})
        await graph_service.create_entity("Router", {"name": "router1"})
        await graph_service.create_entity("Server", {"name": "server2"})
        
        await graph_service.create_relationship("server1", "CONNECTED_TO", "switch1")
        await graph_service.create_relationship("switch1", "CONNECTED_TO", "router1")
        await graph_service.create_relationship("router1", "CONNECTED_TO", "server2")
        
        # Find path
        path = await graph_service.find_shortest_path("server1", "server2")
        
        assert len(path) == 4  # server1 -> switch1 -> router1 -> server2
```

## End-to-End Testing

### MCP Server E2E Tests

```python
# tests/e2e/test_mcp_server.py
import pytest
import json
from src.mcp.server import MCPServer
from src.mcp.client import MCPTestClient

@pytest.mark.e2e
class TestMCPServerE2E:
    @pytest.fixture
    async def mcp_server(self, docker_services):
        server = MCPServer(port=8080)
        await server.start()
        yield server
        await server.stop()
    
    @pytest.fixture
    def mcp_client(self):
        return MCPTestClient("http://localhost:8080")
    
    @pytest.mark.asyncio
    async def test_complete_query_workflow(self, mcp_server, mcp_client):
        """Test complete query workflow from request to response"""
        # Send query
        response = await mcp_client.query({
            "method": "query_documentation",
            "params": {
                "query": "What is the backup schedule for the main database?",
                "company_id": "123",
                "include_related": True
            }
        })
        
        # Verify response structure
        assert response["success"] is True
        assert "results" in response
        assert len(response["results"]) > 0
        
        # Verify result content
        result = response["results"][0]
        assert "content" in result
        assert "source" in result
        assert "confidence" in result
        assert result["confidence"] >= 0.8
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mcp_server, mcp_client):
        """Test error handling in E2E workflow"""
        # Send invalid query
        response = await mcp_client.query({
            "method": "query_documentation",
            "params": {
                "query": "",  # Empty query
                "company_id": "123"
            }
        })
        
        assert response["success"] is False
        assert "error" in response
        assert response["error"]["code"] == "INVALID_QUERY"
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, mcp_server, mcp_client):
        """Test handling concurrent requests"""
        import asyncio
        
        queries = [
            "What is the WiFi password?",
            "Show me the network diagram",
            "List all servers",
            "What are the backup procedures?"
        ]
        
        # Send concurrent requests
        tasks = [
            mcp_client.query({
                "method": "query_documentation",
                "params": {"query": q, "company_id": "123"}
            })
            for q in queries
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(r["success"] for r in responses)
        assert len(responses) == len(queries)
```

### UI Integration Tests

```python
# tests/e2e/test_ui_integration.py
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.mark.e2e
@pytest.mark.ui
class TestUIIntegration:
    @pytest.fixture
    def driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
        driver.get("http://localhost:8501")  # Streamlit app
        yield driver
        driver.quit()
    
    def test_query_submission(self, driver):
        """Test submitting a query through UI"""
        # Find query input
        query_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[aria-label='Query']"))
        )
        
        # Enter query
        query_input.send_keys("What is the admin password?")
        
        # Submit
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[kind='primary']")
        submit_button.click()
        
        # Wait for results
        results = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".results-container"))
        )
        
        assert results is not None
        assert "password" in results.text.lower()
```

## Performance Testing

### Load Testing with Locust

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import random

class ITGlueMCPUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize user session"""
        self.company_id = random.choice(["123", "456", "789"])
        self.queries = [
            "What is the backup policy?",
            "Show me the network diagram",
            "List all servers",
            "What are the passwords?",
            "How do I configure VPN?",
            "What is the disaster recovery plan?",
            "Show me compliance documentation",
            "List all software licenses"
        ]
    
    @task(weight=70)
    def query_documentation(self):
        """Test documentation queries"""
        response = self.client.post(
            "/api/query",
            json={
                "query": random.choice(self.queries),
                "company_id": self.company_id,
                "limit": 5
            }
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @task(weight=20)
    def search_configurations(self):
        """Test configuration search"""
        response = self.client.get(
            f"/api/configurations?company_id={self.company_id}&type=server"
        )
        
        assert response.status_code == 200
    
    @task(weight=10)
    def get_relationships(self):
        """Test relationship queries"""
        response = self.client.get(
            f"/api/relationships?entity=server-01&company_id={self.company_id}"
        )
        
        assert response.status_code == 200

# Run with: locust -f locustfile.py --host=http://localhost:8080
```

### Stress Testing

```python
# tests/performance/test_stress.py
import pytest
import asyncio
import aiohttp
from datetime import datetime, timedelta

@pytest.mark.performance
class TestStressScenarios:
    @pytest.mark.asyncio
    async def test_sustained_load(self):
        """Test sustained load over time"""
        async with aiohttp.ClientSession() as session:
            start_time = datetime.now()
            end_time = start_time + timedelta(minutes=5)
            
            request_count = 0
            error_count = 0
            
            while datetime.now() < end_time:
                try:
                    async with session.post(
                        "http://localhost:8080/api/query",
                        json={"query": "test query", "company_id": "123"}
                    ) as response:
                        if response.status != 200:
                            error_count += 1
                        request_count += 1
                except Exception:
                    error_count += 1
                    request_count += 1
                
                await asyncio.sleep(0.1)  # 10 requests per second
            
            error_rate = error_count / request_count
            assert error_rate < 0.01  # Less than 1% error rate
    
    @pytest.mark.asyncio
    async def test_spike_load(self):
        """Test handling sudden spike in traffic"""
        async with aiohttp.ClientSession() as session:
            # Send 100 concurrent requests
            tasks = []
            for _ in range(100):
                task = session.post(
                    "http://localhost:8080/api/query",
                    json={"query": "spike test", "company_id": "123"}
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check success rate
            successful = sum(1 for r in responses if not isinstance(r, Exception))
            success_rate = successful / len(responses)
            
            assert success_rate > 0.95  # At least 95% success rate
```

### Memory and Resource Testing

```python
# tests/performance/test_resources.py
import pytest
import psutil
import tracemalloc
from memory_profiler import profile

@pytest.mark.performance
class TestResourceUsage:
    def test_memory_usage(self):
        """Test memory usage doesn't exceed limits"""
        tracemalloc.start()
        
        # Perform memory-intensive operations
        from src.services.query_handler import QueryHandler
        handler = QueryHandler()
        
        for _ in range(1000):
            handler.process_query({
                "query": "test query",
                "company_id": "123"
            })
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory should not exceed 500MB for 1000 queries
        assert peak / 1024 / 1024 < 500
    
    @profile
    def test_memory_leaks(self):
        """Test for memory leaks in long-running operations"""
        import gc
        
        initial_objects = len(gc.get_objects())
        
        # Run operations that might leak memory
        for _ in range(100):
            self._process_large_dataset()
            gc.collect()
        
        final_objects = len(gc.get_objects())
        
        # Object count shouldn't grow significantly
        assert final_objects - initial_objects < 1000
    
    def _process_large_dataset(self):
        """Helper to process large dataset"""
        data = [{"id": i, "content": f"Document {i}" * 100} for i in range(1000)]
        # Process data
        return len(data)
```

## Security Testing

### Security Vulnerability Tests

```python
# tests/security/test_security.py
import pytest
from src.services.validation import SecurityValidator

@pytest.mark.security
class TestSecurityVulnerabilities:
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention"""
        malicious_queries = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM passwords --"
        ]
        
        validator = SecurityValidator()
        
        for query in malicious_queries:
            assert validator.is_safe_query(query) is False
    
    def test_xss_prevention(self):
        """Test XSS attack prevention"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(1)'>"
        ]
        
        validator = SecurityValidator()
        
        for payload in xss_payloads:
            sanitized = validator.sanitize_content(payload)
            assert "<script>" not in sanitized
            assert "javascript:" not in sanitized
    
    def test_path_traversal_prevention(self):
        """Test path traversal attack prevention"""
        malicious_paths = [
            "../../etc/passwd",
            "../../../windows/system32/config/sam",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
        
        validator = SecurityValidator()
        
        for path in malicious_paths:
            assert validator.is_safe_path(path) is False
    
    def test_api_key_validation(self):
        """Test API key validation and rotation"""
        from src.auth.api_key import APIKeyManager
        
        manager = APIKeyManager()
        
        # Generate key
        key = manager.generate_key()
        assert len(key) >= 32
        
        # Validate key
        assert manager.validate_key(key) is True
        assert manager.validate_key("invalid_key") is False
        
        # Revoke key
        manager.revoke_key(key)
        assert manager.validate_key(key) is False
```

### Penetration Testing

```python
# tests/security/test_penetration.py
import pytest
import requests
from zapv2 import ZAPv2

@pytest.mark.security
@pytest.mark.penetration
class TestPenetrationTesting:
    @pytest.fixture
    def zap(self):
        """Initialize OWASP ZAP proxy"""
        return ZAPv2(proxies={'http': 'http://127.0.0.1:8080'})
    
    def test_automated_security_scan(self, zap):
        """Run automated security scan"""
        target = 'http://localhost:8080'
        
        # Spider the application
        scan_id = zap.spider.scan(target)
        while int(zap.spider.status(scan_id)) < 100:
            time.sleep(2)
        
        # Run active scan
        scan_id = zap.ascan.scan(target)
        while int(zap.ascan.status(scan_id)) < 100:
            time.sleep(5)
        
        # Check for high-risk alerts
        alerts = zap.core.alerts(baseurl=target)
        high_risk = [a for a in alerts if a['risk'] == 'High']
        
        assert len(high_risk) == 0, f"Found high-risk vulnerabilities: {high_risk}"
```

## MCP Protocol Testing

### Protocol Compliance Tests

```python
# tests/mcp/test_protocol_compliance.py
import pytest
import json
from src.mcp.protocol import MCPMessage, MCPResponse

@pytest.mark.mcp
class TestMCPProtocolCompliance:
    def test_message_format_validation(self):
        """Test MCP message format compliance"""
        valid_message = {
            "jsonrpc": "2.0",
            "method": "query_documentation",
            "params": {
                "query": "test query"
            },
            "id": 1
        }
        
        message = MCPMessage.from_dict(valid_message)
        assert message.is_valid()
    
    def test_response_format(self):
        """Test MCP response format"""
        response = MCPResponse(
            id=1,
            result={"success": True, "data": "test"},
            error=None
        )
        
        serialized = response.to_json()
        parsed = json.loads(serialized)
        
        assert parsed["jsonrpc"] == "2.0"
        assert parsed["id"] == 1
        assert "result" in parsed
        assert "error" not in parsed
    
    def test_error_response_format(self):
        """Test MCP error response format"""
        response = MCPResponse(
            id=1,
            result=None,
            error={
                "code": -32600,
                "message": "Invalid Request",
                "data": {"details": "Missing required parameter"}
            }
        )
        
        serialized = response.to_json()
        parsed = json.loads(serialized)
        
        assert parsed["error"]["code"] == -32600
        assert "message" in parsed["error"]
    
    @pytest.mark.parametrize("method,params,expected_valid", [
        ("query_documentation", {"query": "test"}, True),
        ("invalid_method", {"query": "test"}, False),
        ("query_documentation", {}, False),  # Missing required param
        ("query_documentation", {"query": "test", "extra": "param"}, True)  # Extra params OK
    ])
    def test_method_validation(self, method, params, expected_valid):
        """Test MCP method validation"""
        message = MCPMessage(
            method=method,
            params=params,
            id=1
        )
        
        assert message.is_valid_method() == expected_valid
```

## Test Data Management

### Test Data Fixtures

```python
# tests/fixtures/test_data.py
import pytest
from faker import Faker
import factory
from src.models.database import Document, Organization

fake = Faker()

class OrganizationFactory(factory.Factory):
    class Meta:
        model = Organization
    
    id = factory.Sequence(lambda n: n)
    name = factory.Faker('company')
    created_at = factory.Faker('date_time')

class DocumentFactory(factory.Factory):
    class Meta:
        model = Document
    
    id = factory.Sequence(lambda n: n)
    title = factory.Faker('sentence')
    content = factory.Faker('text', max_nb_chars=1000)
    company_id = factory.Faker('random_int', min=1, max=100)
    document_type = factory.Faker('random_element', elements=['config', 'password', 'guide'])
    created_at = factory.Faker('date_time')

@pytest.fixture
def sample_organizations():
    """Generate sample organizations"""
    return [OrganizationFactory() for _ in range(10)]

@pytest.fixture
def sample_documents():
    """Generate sample documents"""
    return [DocumentFactory() for _ in range(100)]

@pytest.fixture
def test_dataset():
    """Generate complete test dataset"""
    return {
        'organizations': [OrganizationFactory() for _ in range(5)],
        'documents': [DocumentFactory() for _ in range(50)],
        'queries': [
            {
                'text': fake.sentence(),
                'expected_results': fake.random_int(1, 10)
            }
            for _ in range(20)
        ]
    }
```

### Test Data Seeding

```python
# tests/fixtures/seed_test_data.py
import asyncio
from src.database import get_db
from tests.fixtures.test_data import DocumentFactory, OrganizationFactory

async def seed_test_database():
    """Seed database with test data"""
    async with get_db() as session:
        # Create organizations
        orgs = []
        for i in range(3):
            org = OrganizationFactory(
                name=f"Test Org {i}",
                id=f"org_{i}"
            )
            session.add(org)
            orgs.append(org)
        
        # Create documents for each org
        for org in orgs:
            for j in range(20):
                doc = DocumentFactory(
                    company_id=org.id,
                    title=f"{org.name} - Document {j}"
                )
                session.add(doc)
        
        await session.commit()
        print(f"Seeded {len(orgs)} organizations with 20 documents each")

if __name__ == "__main__":
    asyncio.run(seed_test_database())
```

## CI/CD Pipeline Testing

### GitHub Actions Configuration

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run unit tests
        run: |
          pytest tests/unit -v --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      neo4j:
        image: neo4j:5
        env:
          NEO4J_AUTH: neo4j/test
        options: >-
          --health-cmd "cypher-shell -u neo4j -p test 'RETURN 1'"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Run integration tests
        run: |
          docker-compose -f tests/docker-compose.test.yml up -d
          pytest tests/integration -v
      
      - name: Cleanup
        if: always()
        run: docker-compose -f tests/docker-compose.test.yml down

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build and start services
        run: |
          docker-compose up -d --build
          ./scripts/wait-for-healthy.sh
      
      - name: Run E2E tests
        run: pytest tests/e2e -v --timeout=60
      
      - name: Collect logs
        if: failure()
        run: |
          docker-compose logs > docker-logs.txt
          
      - name: Upload logs
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: docker-logs
          path: docker-logs.txt

  security-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Bandit security scan
        run: |
          pip install bandit
          bandit -r src/ -f json -o bandit-report.json
      
      - name: Run Safety check
        run: |
          pip install safety
          safety check --json > safety-report.json
      
      - name: Run Trivy scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload security results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  performance-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v3
      
      - name: Start services
        run: docker-compose up -d
      
      - name: Run load tests
        run: |
          pip install locust
          locust -f tests/performance/locustfile.py \
            --headless \
            --users 10 \
            --spawn-rate 2 \
            --run-time 60s \
            --host http://localhost:8080
      
      - name: Check performance regression
        run: python scripts/check_performance.py
```

## Test Coverage & Metrics

### Coverage Configuration

```ini
# .coveragerc
[run]
source = src
omit = 
    */tests/*
    */migrations/*
    */__pycache__/*
    */venv/*

[report]
precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov

[xml]
output = coverage.xml
```

### Test Metrics Dashboard

```python
# scripts/test_metrics.py
import json
import xml.etree.ElementTree as ET
from pathlib import Path

def generate_test_metrics():
    """Generate test metrics report"""
    metrics = {
        'coverage': parse_coverage(),
        'test_results': parse_test_results(),
        'performance': parse_performance_results(),
        'security': parse_security_results()
    }
    
    # Generate report
    report = f"""
    # Test Metrics Report
    
    ## Coverage
    - Line Coverage: {metrics['coverage']['line_rate']}%
    - Branch Coverage: {metrics['coverage']['branch_rate']}%
    
    ## Test Results
    - Total Tests: {metrics['test_results']['total']}
    - Passed: {metrics['test_results']['passed']}
    - Failed: {metrics['test_results']['failed']}
    - Skipped: {metrics['test_results']['skipped']}
    
    ## Performance
    - Avg Response Time: {metrics['performance']['avg_response_time']}ms
    - P95 Response Time: {metrics['performance']['p95_response_time']}ms
    - Requests/sec: {metrics['performance']['rps']}
    
    ## Security
    - Vulnerabilities: {metrics['security']['vulnerabilities']}
    - Security Score: {metrics['security']['score']}/100
    """
    
    return report

def parse_coverage():
    """Parse coverage.xml"""
    tree = ET.parse('coverage.xml')
    root = tree.getroot()
    return {
        'line_rate': float(root.get('line-rate', 0)) * 100,
        'branch_rate': float(root.get('branch-rate', 0)) * 100
    }

def parse_test_results():
    """Parse pytest results"""
    with open('.pytest_cache/v/cache/lastfailed', 'r') as f:
        data = json.load(f)
    return {
        'total': data.get('total', 0),
        'passed': data.get('passed', 0),
        'failed': data.get('failed', 0),
        'skipped': data.get('skipped', 0)
    }

if __name__ == "__main__":
    print(generate_test_metrics())
```

## Testing Best Practices

### Test Organization

```
tests/
├── unit/               # Fast, isolated tests
│   ├── services/
│   ├── models/
│   └── utils/
├── integration/        # Component interaction tests
│   ├── database/
│   ├── api/
│   └── external/
├── e2e/               # Full workflow tests
│   ├── scenarios/
│   └── ui/
├── performance/       # Load and stress tests
│   ├── load/
│   └── stress/
├── security/          # Security tests
│   ├── vulnerability/
│   └── penetration/
├── fixtures/          # Test data and mocks
│   ├── data/
│   └── mocks/
└── conftest.py        # Shared fixtures
```

### Testing Guidelines

1. **Test Naming**
   - Use descriptive names: `test_should_return_error_when_query_is_empty`
   - Group related tests in classes
   - Use consistent naming patterns

2. **Test Independence**
   - Each test should be independent
   - Use fixtures for setup/teardown
   - Avoid test order dependencies

3. **Assertions**
   - One logical assertion per test
   - Use specific assertions
   - Include helpful error messages

4. **Mocking**
   - Mock external dependencies
   - Use dependency injection
   - Verify mock interactions

5. **Performance**
   - Keep unit tests fast (<100ms)
   - Use test categories for slow tests
   - Parallelize test execution

6. **Documentation**
   - Document complex test scenarios
   - Include examples in docstrings
   - Maintain test documentation

### Example Test Template

```python
"""
Test module for QueryHandler service.

This module tests the core query processing functionality including:
- Query validation
- Result ranking
- Error handling
"""

import pytest
from unittest.mock import Mock, patch
from src.services.query_handler import QueryHandler

class TestQueryHandler:
    """Test cases for QueryHandler service"""
    
    @pytest.fixture
    def handler(self):
        """Provide QueryHandler instance with mocked dependencies"""
        with patch('src.services.query_handler.VectorStore') as mock_store:
            handler = QueryHandler(vector_store=mock_store)
            yield handler
    
    def test_should_process_valid_query_successfully(self, handler):
        """
        Test that valid queries are processed correctly.
        
        Given: A valid query with proper parameters
        When: The query is processed
        Then: Results should be returned with proper ranking
        """
        # Arrange
        query = "What is the backup policy?"
        expected_results = [{"content": "Backup runs daily", "score": 0.95}]
        handler.vector_store.search.return_value = expected_results
        
        # Act
        results = handler.process_query(query)
        
        # Assert
        assert len(results) == 1
        assert results[0]["score"] >= 0.9
        handler.vector_store.search.assert_called_once_with(query)
```

## Summary

This testing documentation provides a comprehensive framework for testing the IT Glue MCP Server. Key components include:

1. **Multi-layer Testing**: Unit, integration, E2E, performance, and security tests
2. **Test Automation**: CI/CD pipeline integration with comprehensive test suites
3. **Performance Validation**: Load testing, stress testing, and resource monitoring
4. **Security Testing**: Vulnerability scanning, penetration testing, and compliance checks
5. **MCP Protocol Testing**: Protocol compliance and message validation
6. **Test Data Management**: Fixtures, factories, and seeding strategies
7. **Metrics & Reporting**: Coverage tracking and test metrics dashboards

Remember to:
- Maintain high test coverage (>80% for critical paths)
- Run tests automatically on every commit
- Keep tests fast and independent
- Document test scenarios and expectations
- Regularly update test data and scenarios