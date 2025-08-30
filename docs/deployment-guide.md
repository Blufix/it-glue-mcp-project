# IT Glue MCP Server - Deployment Guide 🚀

## Overview

This guide provides comprehensive instructions for deploying the IT Glue MCP Server in various environments, from local development to production cloud deployments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Docker Compose Deployment](#docker-compose-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Cloud Deployment](#cloud-deployment)
6. [Monitoring & Observability](#monitoring--observability)
7. [Backup & Recovery](#backup--recovery)
8. [Production Checklist](#production-checklist)
9. [Troubleshooting](#troubleshooting)
10. [Scaling Strategies](#scaling-strategies)

## Prerequisites

### System Requirements

```yaml
minimum_requirements:
  cpu: 4 cores
  ram: 8GB
  disk: 50GB SSD
  
recommended_requirements:
  cpu: 8 cores
  ram: 16GB
  disk: 100GB SSD
  
production_requirements:
  cpu: 16+ cores
  ram: 32GB+
  disk: 500GB+ SSD (RAID configured)
```

### Software Dependencies

```bash
# Required software
docker >= 24.0.0
docker-compose >= 2.20.0
python >= 3.11
node >= 18.0.0
git >= 2.40.0

# Optional for production
kubectl >= 1.28.0
helm >= 3.12.0
terraform >= 1.5.0
```

## Environment Configuration

### Configuration Files Structure

```
deployment/
├── .env.example              # Template environment file
├── .env.development          # Development settings
├── .env.staging             # Staging settings
├── .env.production          # Production settings
├── docker-compose.yml       # Main compose file
├── docker-compose.dev.yml   # Development overrides
├── docker-compose.prod.yml  # Production overrides
└── configs/
    ├── nginx.conf          # Reverse proxy config
    ├── prometheus.yml      # Monitoring config
    └── grafana/            # Dashboard configs
```

### Environment Variables

```bash
# .env.production
# API Configuration
IT_GLUE_API_KEY=your_production_api_key_here
IT_GLUE_BASE_URL=https://api.itglue.com
IT_GLUE_ACCOUNT_ID=your_account_id

# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=itglue_mcp
POSTGRES_USER=itglue_user
POSTGRES_PASSWORD=secure_password_here
POSTGRES_SSL_MODE=require

# Neo4j Configuration
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=secure_neo4j_password
NEO4J_DATABASE=itglue

# Qdrant Configuration
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_API_KEY=secure_qdrant_key
QDRANT_COLLECTION=it_documentation

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=secure_redis_password
REDIS_DB=0
REDIS_SSL=true

# Application Settings
APP_ENV=production
APP_DEBUG=false
APP_LOG_LEVEL=info
APP_SECRET_KEY=generate_strong_secret_key_here
APP_CORS_ORIGINS=["https://your-domain.com"]

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
RATE_LIMIT_STRATEGY=adaptive

# MCP Server Configuration
MCP_SERVER_PORT=8080
MCP_SERVER_HOST=0.0.0.0
MCP_MAX_CONNECTIONS=100
MCP_REQUEST_TIMEOUT=30

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
ENABLE_TRACING=true
JAEGER_ENDPOINT=http://jaeger:14268/api/traces

# Security
JWT_SECRET_KEY=generate_jwt_secret_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
ENABLE_API_KEY_AUTH=true
```

## Docker Compose Deployment

### Development Deployment

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - ./src:/app/src
      - ./tests:/app/tests
    environment:
      - APP_ENV=development
      - APP_DEBUG=true
    ports:
      - "8080:8080"
      - "5678:5678"  # Debugger port
    command: python -m debugpy --listen 0.0.0.0:5678 -m uvicorn main:app --reload --host 0.0.0.0 --port 8080

  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  neo4j:
    image: neo4j:5-community
    ports:
      - "7474:7474"  # Browser
      - "7687:7687"  # Bolt
    volumes:
      - neo4j_dev_data:/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_dev_data:/qdrant/storage

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_dev_data:/data

volumes:
  postgres_dev_data:
  neo4j_dev_data:
  qdrant_dev_data:
  redis_dev_data:
```

### Production Deployment

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./configs/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - nginx_cache:/var/cache/nginx
    depends_on:
      - app
    restart: unless-stopped

  app:
    image: itglue-mcp-server:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    environment:
      - APP_ENV=production
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups/postgres:/backups
    environment:
      POSTGRES_REPLICATION_MODE: master
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}
    restart: unless-stopped
    command: >
      postgres
      -c max_connections=200
      -c shared_buffers=256MB
      -c effective_cache_size=1GB
      -c maintenance_work_mem=64MB
      -c checkpoint_completion_target=0.9
      -c wal_buffers=16MB
      -c default_statistics_target=100
      -c random_page_cost=1.1
      -c effective_io_concurrency=200
      -c work_mem=1310kB
      -c min_wal_size=1GB
      -c max_wal_size=4GB

  neo4j:
    image: neo4j:5-enterprise
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - ./backups/neo4j:/backups
    environment:
      - NEO4J_ACCEPT_LICENSE_AGREEMENT=yes
      - NEO4J_dbms_memory_heap_initial__size=2G
      - NEO4J_dbms_memory_heap_max__size=4G
      - NEO4J_dbms_memory_pagecache_size=2G
    restart: unless-stopped

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage
      - ./backups/qdrant:/snapshots
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 4G

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
      - ./configs/redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./configs/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
      - ./configs/grafana:/etc/grafana/provisioning
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_INSTALL_PLUGINS=redis-datasource
    restart: unless-stopped

volumes:
  nginx_cache:
  postgres_data:
  neo4j_data:
  neo4j_logs:
  qdrant_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

### Deployment Commands

```bash
# Development deployment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# View logs
docker-compose logs -f app

# Scale services
docker-compose up -d --scale app=3

# Update deployment
docker-compose pull
docker-compose up -d --no-deps app

# Health check
docker-compose exec app curl http://localhost:8080/health
```

## Kubernetes Deployment

### Helm Chart Structure

```yaml
# helm/itglue-mcp/values.yaml
replicaCount: 3

image:
  repository: itglue-mcp-server
  pullPolicy: IfNotPresent
  tag: "latest"

service:
  type: LoadBalancer
  port: 80
  targetPort: 8080

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
  hosts:
    - host: api.your-domain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: itglue-mcp-tls
      hosts:
        - api.your-domain.com

resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 1000m
    memory: 2Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

persistence:
  postgres:
    enabled: true
    size: 100Gi
    storageClass: fast-ssd
  neo4j:
    enabled: true
    size: 50Gi
    storageClass: fast-ssd
  qdrant:
    enabled: true
    size: 50Gi
    storageClass: fast-ssd
```

### Kubernetes Manifests

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: itglue-mcp-server
  labels:
    app: itglue-mcp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: itglue-mcp
  template:
    metadata:
      labels:
        app: itglue-mcp
    spec:
      containers:
      - name: app
        image: itglue-mcp-server:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: itglue-secrets
              key: database-url
        - name: IT_GLUE_API_KEY
          valueFrom:
            secretKeyRef:
              name: itglue-secrets
              key: api-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      imagePullSecrets:
      - name: regcred
```

### Deployment Commands

```bash
# Create namespace
kubectl create namespace itglue-mcp

# Create secrets
kubectl create secret generic itglue-secrets \
  --from-env-file=.env.production \
  -n itglue-mcp

# Deploy with Helm
helm install itglue-mcp ./helm/itglue-mcp \
  --namespace itglue-mcp \
  --values ./helm/itglue-mcp/values.production.yaml

# Update deployment
helm upgrade itglue-mcp ./helm/itglue-mcp \
  --namespace itglue-mcp \
  --values ./helm/itglue-mcp/values.production.yaml

# Check status
kubectl get pods -n itglue-mcp
kubectl get services -n itglue-mcp
kubectl get ingress -n itglue-mcp
```

## Cloud Deployment

### AWS Deployment

```hcl
# terraform/aws/main.tf
provider "aws" {
  region = var.aws_region
}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "itglue-mcp-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  
  enable_nat_gateway = true
  enable_vpn_gateway = true
  enable_dns_hostnames = true
}

module "ecs" {
  source = "terraform-aws-modules/ecs/aws"
  
  cluster_name = "itglue-mcp-cluster"
  
  fargate_capacity_providers = {
    FARGATE = {
      default_capacity_provider_strategy = {
        weight = 50
      }
    }
    FARGATE_SPOT = {
      default_capacity_provider_strategy = {
        weight = 50
      }
    }
  }
}

resource "aws_ecs_service" "itglue_mcp" {
  name            = "itglue-mcp-service"
  cluster         = module.ecs.cluster_id
  task_definition = aws_ecs_task_definition.itglue_mcp.arn
  desired_count   = 3
  
  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }
  
  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.itglue_mcp.arn
    container_name   = "itglue-mcp-app"
    container_port   = 8080
  }
}

resource "aws_rds_cluster" "postgres" {
  cluster_identifier      = "itglue-mcp-postgres"
  engine                  = "aurora-postgresql"
  engine_version          = "15.2"
  master_username         = var.db_username
  master_password         = var.db_password
  backup_retention_period = 30
  preferred_backup_window = "03:00-04:00"
  
  db_subnet_group_name = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  
  enabled_cloudwatch_logs_exports = ["postgresql"]
  
  serverlessv2_scaling_configuration {
    max_capacity = 16
    min_capacity = 2
  }
}
```

### GCP Deployment

```yaml
# gcp/cloud-run-service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: itglue-mcp-server
  annotations:
    run.googleapis.com/launch-stage: GA
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "3"
        autoscaling.knative.dev/maxScale: "100"
        run.googleapis.com/cpu-throttling: "false"
    spec:
      containerConcurrency: 100
      timeoutSeconds: 300
      containers:
      - image: gcr.io/PROJECT_ID/itglue-mcp-server:latest
        resources:
          limits:
            cpu: "2"
            memory: "4Gi"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-url
              key: latest
        - name: IT_GLUE_API_KEY
          valueFrom:
            secretKeyRef:
              name: itglue-api-key
              key: latest
        startupProbe:
          httpGet:
            path: /health
          initialDelaySeconds: 0
          periodSeconds: 10
          timeoutSeconds: 1
          failureThreshold: 3
```

### Azure Deployment

```json
// azure/container-instances.json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "containerGroupName": {
      "type": "string",
      "defaultValue": "itglue-mcp-server"
    }
  },
  "resources": [
    {
      "type": "Microsoft.ContainerInstance/containerGroups",
      "apiVersion": "2021-09-01",
      "name": "[parameters('containerGroupName')]",
      "location": "[resourceGroup().location]",
      "properties": {
        "containers": [
          {
            "name": "itglue-mcp-app",
            "properties": {
              "image": "itgluemcp.azurecr.io/itglue-mcp-server:latest",
              "resources": {
                "requests": {
                  "cpu": 2,
                  "memoryInGb": 4
                }
              },
              "ports": [
                {
                  "port": 8080,
                  "protocol": "TCP"
                }
              ],
              "environmentVariables": [
                {
                  "name": "DATABASE_URL",
                  "secureValue": "[parameters('databaseUrl')]"
                },
                {
                  "name": "IT_GLUE_API_KEY",
                  "secureValue": "[parameters('apiKey')]"
                }
              ]
            }
          }
        ],
        "osType": "Linux",
        "ipAddress": {
          "type": "Public",
          "ports": [
            {
              "protocol": "TCP",
              "port": 443
            }
          ]
        }
      }
    }
  ]
}
```

## Monitoring & Observability

### Metrics Configuration

```yaml
# configs/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'itglue-mcp'
    static_configs:
      - targets: ['app:9090']
    metrics_path: /metrics

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:2004']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - '/etc/prometheus/alerts/*.yml'
```

### Alert Rules

```yaml
# configs/prometheus/alerts/application.yml
groups:
  - name: application
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected
          description: "Error rate is {{ $value | humanizePercentage }}"

      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High latency detected
          description: "95th percentile latency is {{ $value }}s"

      - alert: DatabaseConnectionPool
        expr: database_connections_active / database_connections_max > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: Database connection pool nearly exhausted
          description: "{{ $value | humanizePercentage }} of connections in use"
```

### Grafana Dashboards

```json
// configs/grafana/dashboards/application.json
{
  "dashboard": {
    "title": "IT Glue MCP Server",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "{{status}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "p95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "p99"
          }
        ]
      },
      {
        "title": "Active Connections",
        "targets": [
          {
            "expr": "mcp_active_connections",
            "legendFormat": "Active"
          },
          {
            "expr": "mcp_max_connections",
            "legendFormat": "Max"
          }
        ]
      }
    ]
  }
}
```

### Logging Configuration

```python
# src/config/logging.py
import logging
import json
from pythonjsonlogger import jsonlogger

def setup_logging(app_env: str, log_level: str):
    """Configure structured logging"""
    
    # Create formatter
    formatter = jsonlogger.JsonFormatter(
        fmt='%(timestamp)s %(level)s %(name)s %(message)s',
        rename_fields={'timestamp': '@timestamp'}
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for production
    if app_env == 'production':
        file_handler = logging.handlers.RotatingFileHandler(
            '/var/log/itglue-mcp/app.log',
            maxBytes=100_000_000,  # 100MB
            backupCount=10
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Configure third-party loggers
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.INFO)
    
    return root_logger
```

## Backup & Recovery

### Automated Backup Script

```bash
#!/bin/bash
# scripts/backup.sh

set -e

BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL
echo "Backing up PostgreSQL..."
docker-compose exec -T postgres pg_dumpall -U $POSTGRES_USER | gzip > "$BACKUP_DIR/postgres.sql.gz"

# Backup Neo4j
echo "Backing up Neo4j..."
docker-compose exec -T neo4j neo4j-admin database dump --to-path=/backups/neo4j.dump neo4j

# Backup Qdrant
echo "Backing up Qdrant..."
curl -X POST "http://localhost:6333/collections/it_documentation/snapshots" \
  -H "api-key: $QDRANT_API_KEY" \
  -d '{"wait": true}'

# Backup Redis
echo "Backing up Redis..."
docker-compose exec -T redis redis-cli --rdb /data/dump.rdb BGSAVE
sleep 5
cp redis_data/dump.rdb "$BACKUP_DIR/redis.rdb"

# Upload to S3
aws s3 sync "$BACKUP_DIR" "s3://itglue-mcp-backups/$BACKUP_DIR"

# Clean old local backups (keep 7 days)
find /backups -type d -mtime +7 -exec rm -rf {} +

echo "Backup completed: $BACKUP_DIR"
```

### Recovery Procedure

```bash
#!/bin/bash
# scripts/restore.sh

set -e

BACKUP_DATE=$1
if [ -z "$BACKUP_DATE" ]; then
    echo "Usage: ./restore.sh YYYYMMDD_HHMMSS"
    exit 1
fi

BACKUP_DIR="/backups/$BACKUP_DATE"

# Download from S3 if not local
if [ ! -d "$BACKUP_DIR" ]; then
    aws s3 sync "s3://itglue-mcp-backups/$BACKUP_DIR" "$BACKUP_DIR"
fi

# Stop services
docker-compose stop app

# Restore PostgreSQL
echo "Restoring PostgreSQL..."
gunzip < "$BACKUP_DIR/postgres.sql.gz" | docker-compose exec -T postgres psql -U $POSTGRES_USER

# Restore Neo4j
echo "Restoring Neo4j..."
docker-compose exec -T neo4j neo4j-admin database load --from-path=/backups/neo4j.dump neo4j --overwrite

# Restore Qdrant
echo "Restoring Qdrant..."
# Stop Qdrant, replace data directory, restart
docker-compose stop qdrant
rm -rf qdrant_data/*
# Copy snapshot data
docker-compose start qdrant

# Restore Redis
echo "Restoring Redis..."
docker-compose stop redis
cp "$BACKUP_DIR/redis.rdb" redis_data/dump.rdb
docker-compose start redis

# Restart application
docker-compose start app

echo "Restore completed from: $BACKUP_DIR"
```

### Disaster Recovery Plan

```yaml
# disaster-recovery-plan.yaml
recovery_objectives:
  rto: 4 hours  # Recovery Time Objective
  rpo: 1 hour   # Recovery Point Objective

backup_strategy:
  frequency:
    full: daily
    incremental: hourly
    transaction_logs: continuous
  
  retention:
    daily: 7 days
    weekly: 4 weeks
    monthly: 12 months
    yearly: 7 years

recovery_procedures:
  1_assessment:
    - Identify failure scope
    - Determine data loss window
    - Notify stakeholders
  
  2_infrastructure:
    - Provision replacement infrastructure
    - Restore network configuration
    - Configure security groups
  
  3_data_recovery:
    - Identify latest clean backup
    - Restore databases in order
    - Verify data integrity
  
  4_application:
    - Deploy application containers
    - Configure environment variables
    - Restore application state
  
  5_validation:
    - Run smoke tests
    - Verify API endpoints
    - Check data consistency
  
  6_switchover:
    - Update DNS records
    - Enable traffic routing
    - Monitor performance

testing_schedule:
  full_recovery_test: quarterly
  backup_restoration_test: monthly
  failover_test: weekly
```

## Production Checklist

### Pre-Deployment

- [ ] **Environment Configuration**
  - [ ] All environment variables configured
  - [ ] Secrets stored in secure vault
  - [ ] SSL certificates obtained and configured
  - [ ] Domain names configured

- [ ] **Security**
  - [ ] Security scan completed
  - [ ] Dependency vulnerabilities patched
  - [ ] Network policies configured
  - [ ] RBAC policies implemented
  - [ ] API rate limiting configured
  - [ ] WAF rules configured

- [ ] **Database**
  - [ ] Database migrations completed
  - [ ] Indexes optimized
  - [ ] Connection pooling configured
  - [ ] Backup strategy implemented
  - [ ] Replication configured

- [ ] **Performance**
  - [ ] Load testing completed
  - [ ] Cache warming implemented
  - [ ] CDN configured
  - [ ] Image optimization completed
  - [ ] Query optimization done

### Deployment

- [ ] **Infrastructure**
  - [ ] High availability configured
  - [ ] Auto-scaling configured
  - [ ] Load balancers configured
  - [ ] Health checks implemented
  - [ ] Monitoring configured

- [ ] **Application**
  - [ ] Zero-downtime deployment tested
  - [ ] Rollback procedure documented
  - [ ] Feature flags configured
  - [ ] Error tracking configured
  - [ ] Logging configured

### Post-Deployment

- [ ] **Validation**
  - [ ] Smoke tests passed
  - [ ] Integration tests passed
  - [ ] Performance benchmarks met
  - [ ] Security scan passed
  - [ ] Monitoring alerts active

- [ ] **Documentation**
  - [ ] Runbooks updated
  - [ ] API documentation published
  - [ ] Change log updated
  - [ ] Team notified
  - [ ] Customer communication sent

## Troubleshooting

### Common Issues

#### Application Won't Start

```bash
# Check logs
docker-compose logs app

# Common causes:
# 1. Missing environment variables
docker-compose config | grep -E "IT_GLUE|POSTGRES|NEO4J"

# 2. Database connection issues
docker-compose exec app nc -zv postgres 5432

# 3. Port conflicts
netstat -tulpn | grep -E "8080|5432|7687|6333|6379"
```

#### High Memory Usage

```bash
# Check memory usage
docker stats

# Analyze memory dump
docker-compose exec app python -m memory_profiler main.py

# Adjust memory limits
docker-compose exec app python -c "import resource; resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, -1))"
```

#### Slow API Response

```bash
# Enable profiling
export ENABLE_PROFILING=true
docker-compose restart app

# Check slow queries
docker-compose exec postgres psql -U $POSTGRES_USER -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Check cache hit rate
docker-compose exec redis redis-cli INFO stats | grep keyspace_hits
```

#### Database Connection Pool Exhausted

```python
# Increase pool size
# src/config/database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,        # Increase from default 5
    max_overflow=40,     # Increase from default 10
    pool_pre_ping=True,  # Verify connections
    pool_recycle=3600    # Recycle connections hourly
)
```

## Scaling Strategies

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  app:
    deploy:
      replicas: 5
      update_config:
        parallelism: 2
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

  nginx:
    configs:
      - source: nginx_config
        target: /etc/nginx/nginx.conf
    deploy:
      placement:
        constraints:
          - node.role == manager

configs:
  nginx_config:
    file: ./configs/nginx-load-balancer.conf
```

### Database Scaling

```sql
-- PostgreSQL Read Replicas
CREATE PUBLICATION itglue_publication FOR ALL TABLES;

-- On replica
CREATE SUBSCRIPTION itglue_subscription
CONNECTION 'host=primary dbname=itglue_mcp'
PUBLICATION itglue_publication;
```

### Caching Strategy

```python
# src/services/cache.py
from functools import lru_cache
import redis
import pickle

class CacheService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=False,
            connection_pool=redis.BlockingConnectionPool(
                max_connections=50,
                max_connections_per_db=True
            )
        )
    
    def cache_result(self, key: str, ttl: int = 3600):
        def decorator(func):
            def wrapper(*args, **kwargs):
                cache_key = f"{key}:{str(args)}:{str(kwargs)}"
                
                # Try to get from cache
                cached = self.redis_client.get(cache_key)
                if cached:
                    return pickle.loads(cached)
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Store in cache
                self.redis_client.setex(
                    cache_key,
                    ttl,
                    pickle.dumps(result)
                )
                
                return result
            return wrapper
        return decorator
```

### Auto-Scaling Configuration

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: itglue-mcp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: itglue-mcp-server
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
```

## Summary

This deployment guide provides comprehensive instructions for deploying the IT Glue MCP Server across different environments. Key areas covered include:

1. **Environment Setup**: Proper configuration management and secrets handling
2. **Container Orchestration**: Docker Compose for development and Kubernetes for production
3. **Cloud Deployment**: Templates for AWS, GCP, and Azure
4. **Monitoring**: Prometheus, Grafana, and structured logging
5. **Backup & Recovery**: Automated backups and disaster recovery procedures
6. **Production Readiness**: Comprehensive checklist and troubleshooting guide
7. **Scaling**: Horizontal and vertical scaling strategies

Remember to:
- Always test deployments in staging before production
- Maintain separate configurations for each environment
- Implement proper monitoring and alerting
- Regular backup testing and disaster recovery drills
- Keep documentation updated with deployment changes

For additional support, consult the troubleshooting section or reach out to the DevOps team.