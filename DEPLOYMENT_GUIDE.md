# TopoKit Platform - Deployment Guide

**Date**: 2025-01-31  
**Status**: Ready for Deployment

## Quick Start

### 1. Development Use ✅

#### Prerequisites
```bash
# Python 3.13+
python --version

# Node.js 18+ (for CLI)
node --version

# Virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
cd packages/cli && npm install
```

#### Development Setup
```bash
# Install in development mode
cd packages/core
pip install -e .

# Run tests
pytest tests/ -v

# Use CLI
cd packages/cli
npm run build
npm link  # or use: node dist/index.js

# Initialize a project
topokit init --template=rag-system
```

#### Development Workflow
```bash
# Start development server (if API enabled)
uvicorn topokit.api:app --reload --port 8000

# Run dashboard (if enabled)
cd packages/dashboard
npm run dev

# Run linter
black packages/core/topokit/
flake8 packages/core/topokit/

# Run tests
pytest tests/ -v --cov=packages/core/topokit
```

### 2. Staging Deployment 🚀

#### Environment Setup
```bash
# Set environment variables
export ENVIRONMENT=staging
export DATABASE_URL=postgresql://user:pass@staging-db:5432/topokit
export SECRET_KEY=$(openssl rand -hex 32)
export JWT_SECRET_KEY=$(openssl rand -hex 32)

# Or use .env file
cp .env.example .env.staging
# Edit .env.staging with staging values
```

#### Docker Deployment (Recommended)
```bash
# Build Docker image
docker build -t topokit:staging .

# Run with docker-compose
docker-compose -f docker-compose.staging.yml up -d

# Or run directly
docker run -d \
  --name topokit-staging \
  -p 8000:8000 \
  -e ENVIRONMENT=staging \
  -e DATABASE_URL=$DATABASE_URL \
  -e SECRET_KEY=$SECRET_KEY \
  topokit:staging
```

#### Staging Validation
```bash
# Health check
curl http://staging-server:8000/health

# Run smoke tests
pytest tests/integration/ -v -m staging

# Check logs
docker logs topokit-staging

# Monitor
curl http://staging-server:8000/metrics
```

#### Database Migration
```bash
# Run migrations
alembic upgrade head

# Verify schema
python -m topokit.cli.migrate --status
```

### 3. Production Deployment 🔒

#### Pre-Deployment Checklist

✅ **Security Review (T076)**
- [ ] Review `SECURITY_CHECKLIST.md`
- [ ] Run security audit: `bandit -r packages/core/topokit/`
- [ ] Dependency scan: `pip-audit` and `npm audit`
- [ ] Review `docs/security-hardening.md`
- [ ] Verify all secrets in secure storage (not in code)

✅ **Configuration**
- [ ] Production environment variables configured
- [ ] Database credentials secured
- [ ] SSL/TLS certificates configured
- [ ] Rate limiting enabled
- [ ] Security headers enabled
- [ ] Audit logging enabled
- [ ] PII redaction enabled

✅ **Testing**
- [ ] All tests passing: `pytest tests/ -v`
- [ ] Load testing completed
- [ ] Security testing completed
- [ ] Integration testing completed

✅ **Documentation**
- [ ] Production deployment guide reviewed
- [ ] Runbook prepared
- [ ] Monitoring dashboards configured
- [ ] Alert rules configured

#### Production Setup

##### 1. Infrastructure
```bash
# Provision infrastructure (AWS/GCP/Azure)
# - Database: PostgreSQL with backups
# - Cache: Redis for context store
# - Load Balancer: With SSL termination
# - Monitoring: Prometheus/Grafana or cloud equivalent
```

##### 2. Secrets Management
```bash
# Use secret management service
# AWS Secrets Manager / GCP Secret Manager / HashiCorp Vault

# Required secrets:
# - DATABASE_URL
# - SECRET_KEY
# - JWT_SECRET_KEY
# - LLM_API_KEYS (OpenAI, Anthropic, etc.)
# - ADAPTER_CREDENTIALS
```

##### 3. Database Setup
```bash
# Create production database
createdb topokit_production

# Run migrations
ENVIRONMENT=production alembic upgrade head

# Set up backups
# Configure automated backups (daily)
# Test restore procedure
```

##### 4. Application Deployment

**Option A: Docker (Recommended)**
```bash
# Build production image
docker build -t topokit:production --target production .

# Tag for registry
docker tag topokit:production registry.example.com/topokit:v1.0.0

# Push to registry
docker push registry.example.com/topokit:v1.0.0

# Deploy (Kubernetes example)
kubectl apply -f k8s/production/

# Or Docker Compose
docker-compose -f docker-compose.production.yml up -d
```

**Option B: Direct Deployment**
```bash
# Install on server
ssh production-server
git clone https://github.com/yourorg/topokit.git
cd topokit
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  topokit.api:app
```

##### 5. Monitoring Setup
```bash
# Deploy TopoView dashboard
cd packages/dashboard
npm run build
# Deploy to static hosting or serve with nginx

# Configure monitoring
# - Prometheus metrics endpoint: /metrics
# - Health check endpoint: /health
# - Alert rules configured
# - Log aggregation setup
```

##### 6. Security Configuration
```bash
# Enable security features
export ENABLE_SECURITY_HEADERS=true
export ENABLE_RATE_LIMITING=true
export ENABLE_INPUT_SANITIZATION=true
export ENABLE_PII_REDACTION=true
export ENABLE_AUDIT_LOGGING=true
export ENABLE_ACCOUNT_LOCKOUT=true

# Configure CORS
export CORS_ORIGINS=https://yourdomain.com

# SSL/TLS
# Configure SSL certificates (Let's Encrypt or commercial)
# Force HTTPS redirects
```

##### 7. Validation
```bash
# Health check
curl https://api.yourdomain.com/health

# Smoke tests
pytest tests/integration/ -v -m production

# Security check
bandit -r packages/core/topokit/ -f json -o security-report.json

# Load test
# Use k6, locust, or similar tool
# Target: 1000+ RPS

# Monitor
# - Check metrics dashboard
# - Verify alerts are working
# - Review logs for errors
```

## Deployment Commands

### Quick Deploy Script
```bash
#!/bin/bash
# deploy.sh

set -e

ENVIRONMENT=${1:-staging}

echo "Deploying TopoKit to $ENVIRONMENT..."

# Run tests
echo "Running tests..."
pytest tests/ -v

# Build
echo "Building..."
docker build -t topokit:$ENVIRONMENT .

# Deploy
echo "Deploying..."
docker-compose -f docker-compose.$ENVIRONMENT.yml up -d

# Verify
echo "Verifying..."
sleep 5
curl http://localhost:8000/health

echo "Deployment complete!"
```

## Environment Variables

### Required (All Environments)
```bash
ENVIRONMENT=production|staging|development
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SECRET_KEY=<random-32-char-string>
JWT_SECRET_KEY=<random-32-char-string>
```

### Production Only
```bash
# Security
ENABLE_SECURITY_HEADERS=true
ENABLE_RATE_LIMITING=true
ENABLE_PII_REDACTION=true
ENABLE_AUDIT_LOGGING=true
CORS_ORIGINS=https://yourdomain.com

# Monitoring
ENABLE_METRICS=true
METRICS_ENDPOINT=/metrics
LOG_LEVEL=INFO

# LLM Providers (if using)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Rollback Procedure

### Quick Rollback
```bash
# Docker
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d topokit:previous-version

# Kubernetes
kubectl rollout undo deployment/topokit

# Database (if needed)
alembic downgrade -1
```

## Monitoring & Alerts

### Key Metrics to Monitor
- Request rate and latency
- Error rates
- Database connection pool
- Circuit breaker states
- Cost per request
- Token usage
- Drift detection alerts

### Alert Thresholds
- Error rate > 1%
- Latency p95 > 2s
- Database connections > 80%
- Circuit breaker open > 5 min
- Cost spike > 20%

## Support

### Documentation
- Quickstart: `docs/quickstart.md`
- Architecture: `docs/architecture.md`
- Security: `docs/security-hardening.md`
- Production: `docs/production-readiness.md`

### Troubleshooting
- Check logs: `docker logs topokit-production`
- Health check: `curl /health`
- Metrics: `curl /metrics`
- Review `PROJECT_STATUS.md` for known issues

---

**Ready for Deployment**: ✅ YES  
**Last Updated**: 2025-01-31

