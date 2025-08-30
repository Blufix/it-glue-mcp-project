-- IT Glue MCP Server Database Initialization Script
-- Creates initial database schema and extensions

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text similarity search

-- Create database if it doesn't exist (this will be handled by docker-compose)
-- Just ensure we're using the right database
\c itglue;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS itglue;
CREATE SCHEMA IF NOT EXISTS cache;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set search path
SET search_path TO itglue, public;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA itglue TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA cache TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA audit TO postgres;

-- Create enum types
CREATE TYPE IF NOT EXISTS entity_type AS ENUM (
    'organization',
    'configuration',
    'password',
    'document',
    'contact',
    'location',
    'domain',
    'network',
    'ssl_certificate',
    'flexible_asset'
);

CREATE TYPE IF NOT EXISTS sync_status AS ENUM (
    'pending',
    'in_progress',
    'completed',
    'failed',
    'partial'
);

-- Initial indexes for performance
-- These will be supplemented by Alembic migrations
CREATE INDEX IF NOT EXISTS idx_gin_trgm ON itglue.entities USING gin (content gin_trgm_ops);

COMMENT ON SCHEMA itglue IS 'Main schema for IT Glue entities and data';
COMMENT ON SCHEMA cache IS 'Schema for cached query results and temporary data';
COMMENT ON SCHEMA audit IS 'Schema for audit logs and compliance tracking';