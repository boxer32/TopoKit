# Security Policy

## Supported Versions

We actively support and provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

1. **Email**: security@topokit.dev (preferred)
2. **GitHub Security Advisories**: Use the "Report a vulnerability" button on the Security tab

### What to Include

When reporting a vulnerability, please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Resolution**: Dependent on severity

## Security Features

TopoKit includes the following security features:

- Rate limiting
- Input sanitization
- PII redaction
- Audit logging
- RBAC (Role-Based Access Control)
- JWT authentication
- Security headers
- Account lockout after failed attempts

For more details, see `docs/security-hardening.md` and `SECURITY_CHECKLIST.md`.

## Security Best Practices

1. Always use the latest version of TopoKit
2. Keep dependencies up to date
3. Review `SECURITY_CHECKLIST.md` before production deployment
4. Enable all security features in production
5. Regularly audit access logs
6. Use strong secrets and rotate them regularly
7. Enable HTTPS/TLS in production
8. Review and configure security headers

## Known Security Considerations

- TopoKit requires API keys for LLM providers - store these securely
- Audit logs may contain sensitive data - ensure proper access controls
- PII redaction is configurable - review settings for your use case
- Rate limiting should be configured based on expected load

For production deployment, see `docs/production-readiness.md`.

