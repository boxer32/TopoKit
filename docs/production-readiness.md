# TopoKit Production Readiness Guide

This guide outlines the steps required to prepare TopoKit for production deployment.

## Pre-Production Checklist

### 🔐 Security (CRITICAL - Week 1)

#### Must Complete Before Production

1. **Token Storage Migration**
   ```python
   # Replace in-memory token revocation with Redis
   # File: packages/core/topokit/core/auth.py
   # Current line ~246: self._revoked_tokens: Set[str] = set()
   # Replace with Redis implementation
   ```

2. **Secret Management**
   ```bash
   # Migrate all secrets to key management service
   # - JWT secret keys
   # - Database passwords
   # - API keys for adapters
   # Use: AWS KMS, HashiCorp Vault, or Azure Key Vault
   ```

3. **Database Encryption**
   ```sql
   -- PostgreSQL
   ALTER DATABASE topokit SET encryption = 'on';
   -- Verify encryption is enabled
   SELECT name, setting FROM pg_settings WHERE name LIKE '%encrypt%';
   ```

4. **Enable Security Features**
   ```python
   # Update security configuration
   security = SecurityConfig(
       enable_security_headers=True,
       enable_input_sanitization=True,
       strict_input_validation=True,
       enable_account_lockout=True,
       max_failed_attempts=5,
       account_lockout_minutes=30,
   )
   ```

5. **Rate Limiting**
   ```python
   from topokit.core.security_hardening import SecurityAuditor
   
   auditor = SecurityAuditor(security_config)
   
   # Check rate limit before processing
   result = await auditor.rate_limiter.check_rate_limit(
       "api_requests",
       ip_address
   )
   if not result.allowed:
       raise RateLimitExceeded()
   ```

### 📊 Monitoring & Observability (HIGH - Week 1)

1. **Enable All Monitoring**
   ```python
   observability = ObservabilityConfig(
       enable_metrics=True,
       enable_tracing=True,
       enable_logging=True,
       log_level=LogLevel.INFO,
   )
   ```

2. **Configure Alerting**
   - Set up alert thresholds
   - Configure notification channels (Slack, email, PagerDuty)
   - Test alert delivery

3. **Dashboard Setup**
   - Deploy TopoView dashboard
   - Configure authentication
   - Set up dashboards for key metrics

### 🔄 Database & Infrastructure (HIGH - Week 1)

1. **Database Setup**
   ```bash
   # Run migrations
   python -m topokit.core.database migrate
   
   # Create read replicas for production
   # Configure connection pooling
   # Set up database backups
   ```

2. **Redis Setup**
   ```bash
   # For token revocation and caching
   # Configure Redis cluster for HA
   # Set up Redis persistence
   ```

3. **Load Balancer**
   - Configure load balancer
   - Set up SSL termination
   - Configure health checks

### 🔐 Security Configuration (HIGH - Week 1)

1. **Environment Variables**
   ```bash
   # All secrets from key management service
   export TOPOKIT_SECRET_KEY=$(aws kms decrypt ...)
   export TOPOKIT_DB_PASSWORD=$(aws secretsmanager get-secret-value ...)
   export OPENAI_API_KEY=$(aws secretsmanager get-secret-value ...)
   ```

2. **Network Security**
   - Configure firewall rules
   - Set up VPC/private networking
   - Implement network segmentation

3. **Security Headers**
   ```python
   # Add to FastAPI middleware
   from topokit.core.security_hardening import SecurityHeaders
   
   @app.middleware("http")
   async def add_security_headers(request, call_next):
       response = await call_next(request)
       headers = SecurityHeaders.get_security_headers(strict=True)
       for key, value in headers.items():
           response.headers[key] = value
       return response
   ```

### 📋 Compliance Verification (MEDIUM - Week 2)

1. **GDPR Compliance**
   - [x] Right to deletion implemented
   - [x] Right to access implemented
   - [ ] Verify complete data deletion across all systems
   - [ ] Test data export functionality

2. **Audit Logging**
   - [x] Tamper-evident logging implemented
   - [ ] Set up immutable audit log storage
   - [ ] Configure audit log retention (7 years for SOX)
   - [ ] Test audit log integrity verification

3. **Data Retention**
   - [x] Retention policies configured
   - [ ] Verify automated deletion works
   - [ ] Document retention periods

### 🧪 Testing (HIGH - Week 2)

1. **Load Testing**
   ```bash
   # Test with expected production load
   # Verify 1,000+ RPS target
   # Test concurrent session handling
   ```

2. **Security Testing**
   ```bash
   # Run security tests
   pytest tests/security/
   
   # Dependency vulnerability scan
   pip-audit
   npm audit
   
   # Code security scan
   bandit -r packages/core/topokit/
   ```

3. **Integration Testing**
   ```bash
   # Test all adapters in staging
   # Test deployment process
   # Test rollback procedures
   ```

## Production Deployment Steps

### Step 1: Infrastructure Setup

1. Provision production infrastructure
2. Configure networking and security groups
3. Set up databases (PostgreSQL, Redis)
4. Configure load balancer and SSL certificates
5. Set up monitoring and alerting

### Step 2: Application Deployment

1. Build production Docker images
2. Push images to container registry
3. Deploy to production environment
4. Run database migrations
5. Configure environment variables

### Step 3: Security Configuration

1. Configure secrets management
2. Enable security features
3. Set up rate limiting
4. Configure security headers
5. Enable audit logging

### Step 4: Monitoring Setup

1. Deploy TopoView dashboard
2. Configure monitoring dashboards
3. Set up alerting rules
4. Test monitoring and alerts
5. Document monitoring procedures

### Step 5: Validation

1. Run smoke tests
2. Verify security features
3. Test compliance features
4. Load testing
5. Security audit

## Production Configuration Template

### `production.config.yaml`

```yaml
environment: production

database:
  host: ${DB_HOST}
  port: 5432
  name: topokit_prod
  user: topokit_prod
  password: ${DB_PASSWORD}  # From secrets manager
  ssl_mode: require
  pool_size: 20
  max_overflow: 40
  encryption: true

redis:
  host: ${REDIS_HOST}
  port: 6379
  password: ${REDIS_PASSWORD}  # From secrets manager
  max_connections: 200
  ssl: true

security:
  secret_key: ${JWT_SECRET_KEY}  # From KMS
  jwt_algorithm: HS256
  jwt_expire_minutes: 15
  jwt_refresh_expire_days: 7
  password_min_length: 12
  password_require_special: true
  password_require_numbers: true
  password_require_uppercase: true
  password_expire_days: 90
  max_failed_attempts: 5
  account_lockout_minutes: 30
  enable_mfa: true
  require_mfa: false
  enable_account_lockout: true
  enable_security_headers: true
  enable_input_sanitization: true
  strict_input_validation: true
  rate_limit_requests: 100
  rate_limit_window: 60
  cors_origins:
    - https://app.topokit.dev
  cors_allow_credentials: true

compliance:
  enable_gdpr: true
  enable_ccpa: true
  enable_sox: true
  enable_hipaa: true
  audit_retention_days: 2555  # 7 years
  audit_immutable: true
  enable_pii_redaction: true

observability:
  enable_metrics: true
  enable_tracing: true
  enable_logging: true
  log_level: INFO
  metrics_port: 8080
  tracing_endpoint: ${JAEGER_ENDPOINT}

performance:
  max_concurrent_executions: 1000
  execution_timeout: 300
  cache_ttl: 3600
  cache_max_size: 10000
```

## Security Posture Summary

### ✅ Implemented
- JWT authentication with RBAC
- Password hashing (bcrypt)
- PII detection and redaction
- Tamper-evident audit logging
- Rate limiting framework
- Input sanitization framework
- Security headers framework
- Account lockout framework
- Compliance frameworks (GDPR, CCPA, SOX, HIPAA)

### ⚠️ Production Hardening Required
1. Token storage (Redis migration)
2. Secret management (KMS integration)
3. Database encryption (verification)
4. Rate limiting (enable on endpoints)
5. Security headers (enable in middleware)
6. Input sanitization (enable on endpoints)

### 📅 Timeline
- **Week 1**: Critical security items (token storage, secrets, encryption)
- **Week 2**: High-priority items (rate limiting, headers, testing)
- **Ongoing**: Medium-priority items (MFA, monitoring, documentation)

## Post-Deployment

### Monitoring

1. **Watch Key Metrics**
   - Error rates
   - Latency (p50, p95, p99)
   - Cost per request
   - Drift detection alerts
   - Circuit breaker states

2. **Security Monitoring**
   - Failed login attempts
   - Rate limit violations
   - Unusual access patterns
   - Audit log integrity

3. **Health Checks**
   - API health endpoints
   - Database connectivity
   - Redis connectivity
   - Adapter health status

### Maintenance

1. **Regular Updates**
   - Security patches
   - Dependency updates
   - Feature updates

2. **Security Reviews**
   - Monthly security audits
   - Quarterly penetration testing
   - Annual compliance audits

3. **Backup & Recovery**
   - Daily database backups
   - Test restore procedures
   - Document disaster recovery plan

## Support

- **Security Issues**: security@topokit.dev
- **Production Issues**: oncall@topokit.dev
- **Documentation**: [docs.topokit.dev](https://docs.topokit.dev)

---

**Ready for Production?** Complete the [Security Checklist](SECURITY_CHECKLIST.md) and verify all critical items are addressed.

