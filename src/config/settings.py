"""Application configuration settings."""

from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with validation."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields from .env
    )
    
    # Environment
    environment: str = Field("development", description="Environment name")
    debug: bool = Field(False, description="Debug mode")
    log_level: str = Field("INFO", description="Logging level")
    
    # IT Glue API
    itglue_api_key: str = Field(..., description="IT Glue API key")
    itglue_api_url: str = Field(
        "https://api.itglue.com",
        description="IT Glue API base URL"
    )
    itglue_rate_limit: int = Field(100, description="API rate limit per minute")
    
    # Database URLs
    database_url: str = Field(..., description="PostgreSQL connection URL")
    neo4j_uri: str = Field(..., description="Neo4j connection URI")
    neo4j_user: str = Field("neo4j", description="Neo4j username")
    neo4j_password: str = Field(..., description="Neo4j password")
    qdrant_url: str = Field("http://localhost:6333", description="Qdrant URL")
    qdrant_api_key: Optional[str] = Field(None, description="Qdrant API key")
    redis_url: str = Field("redis://localhost:6379", description="Redis URL")
    
    # Celery
    celery_broker_url: str = Field(
        "redis://localhost:6379/0",
        description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        "redis://localhost:6379/1",
        description="Celery result backend"
    )
    
    # Security
    jwt_secret: str = Field(..., description="JWT secret key")
    jwt_algorithm: str = Field("HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(30, description="JWT expiration time")
    encryption_key: str = Field(..., description="Data encryption key")
    api_key_header: str = Field("X-API-Key", description="API key header name")
    
    # MCP Server
    mcp_server_host: str = Field("0.0.0.0", description="MCP server host")
    mcp_server_port: int = Field(8000, description="MCP server port")
    mcp_websocket_port: int = Field(8001, description="WebSocket port")
    
    # API Server
    api_host: str = Field("0.0.0.0", description="API server host")
    api_port: int = Field(8002, description="API server port")
    api_workers: int = Field(4, description="Number of API workers")
    
    # OpenAI (for embeddings)
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_model: str = Field(
        "text-embedding-ada-002",
        description="OpenAI embedding model"
    )
    openai_max_tokens: int = Field(8000, description="Max tokens for OpenAI")
    
    # Performance
    cache_ttl: int = Field(300, description="Cache TTL in seconds")
    query_timeout: int = Field(30, description="Query timeout in seconds")
    max_connections: int = Field(100, description="Max database connections")
    batch_size: int = Field(100, description="Batch processing size")
    sync_interval_minutes: int = Field(15, description="Sync interval")
    
    # Feature Flags
    enable_cross_company_search: bool = Field(
        False,
        description="Enable cross-company search"
    )
    enable_semantic_search: bool = Field(
        True,
        description="Enable semantic search"
    )
    enable_ai_suggestions: bool = Field(
        False,
        description="Enable AI suggestions"
    )
    enable_compliance_reporting: bool = Field(
        False,
        description="Enable compliance reporting"
    )
    enable_real_time_sync: bool = Field(
        False,
        description="Enable real-time sync"
    )
    
    # Monitoring
    prometheus_enabled: bool = Field(True, description="Enable Prometheus")
    prometheus_port: int = Field(9090, description="Prometheus port")
    sentry_dsn: Optional[str] = Field(None, description="Sentry DSN")
    
    @validator("encryption_key")
    def validate_encryption_key(cls, v):
        """Validate encryption key length."""
        if len(v) < 32:
            raise ValueError("Encryption key must be at least 32 characters")
        return v
    
    @validator("jwt_secret")
    def validate_jwt_secret(cls, v):
        """Validate JWT secret."""
        if len(v) < 32:
            raise ValueError("JWT secret must be at least 32 characters")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() == "development"
    
    @property
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent.parent


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export settings instance
settings = get_settings()