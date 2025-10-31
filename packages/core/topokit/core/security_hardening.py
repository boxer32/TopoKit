"""
Module: security_hardening
Purpose: Additional security hardening utilities for production deployment
Inputs: Security configuration, request context
Outputs: Security checks, rate limiting, input sanitization
Dependencies: auth, compliance, config
Failure Modes: Security check failure → block request, rate limit exceeded → throttling
Trace: page:security, build:20250127, spec-id:T076
"""

from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
import re
import hashlib
import hmac
import logging
from collections import defaultdict, deque

from .logging import get_logger
from .config import SecurityConfig


logger = get_logger(__name__)


@dataclass
class RateLimitResult:
    """Rate limiting result."""
    allowed: bool
    remaining: int
    reset_at: datetime
    limit: int
    window_seconds: int


@dataclass
class SecurityCheckResult:
    """Security check result."""
    passed: bool
    check_name: str
    message: str
    severity: str = "medium"  # low, medium, high, critical
    metadata: Dict[str, Any] = field(default_factory=dict)


class RateLimiter:
    """Rate limiting for API endpoints and adapters."""
    
    def __init__(self):
        """Initialize rate limiter."""
        self.logger = logger
        self._counters: Dict[str, deque] = defaultdict(lambda: deque())
        self._limits: Dict[str, Dict[str, int]] = {}
    
    def configure_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int = 60
    ) -> None:
        """Configure rate limit for a key.
        
        Args:
            key: Rate limit key (e.g., user_id, ip_address)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
        """
        self._limits[key] = {
            "max": max_requests,
            "window": window_seconds
        }
    
    async def check_rate_limit(
        self,
        key: str,
        identifier: str
    ) -> RateLimitResult:
        """Check if request is within rate limit.
        
        Args:
            key: Rate limit configuration key
            identifier: Request identifier (user_id, ip_address, etc.)
            
        Returns:
            Rate limit result
        """
        limit_config = self._limits.get(key, {"max": 100, "window": 60})
        max_requests = limit_config["max"]
        window_seconds = limit_config["window"]
        
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=window_seconds)
        
        # Get counter for identifier
        counter_key = f"{key}:{identifier}"
        requests = self._counters[counter_key]
        
        # Remove old requests
        while requests and requests[0] < cutoff:
            requests.popleft()
        
        # Check limit
        allowed = len(requests) < max_requests
        
        if allowed:
            requests.append(now)
        
        reset_at = now + timedelta(seconds=window_seconds) if requests else now
        
        return RateLimitResult(
            allowed=allowed,
            remaining=max(0, max_requests - len(requests)),
            reset_at=reset_at,
            limit=max_requests,
            window_seconds=window_seconds
        )


class InputSanitizer:
    """Input sanitization for security."""
    
    def __init__(self):
        """Initialize input sanitizer."""
        self.logger = logger
        
        # SQL injection patterns
        self.sql_patterns = [
            re.compile(r"(union|select|insert|update|delete|drop|create|alter|exec|execute)", re.IGNORECASE),
            re.compile(r"(--|;|/\*|\*/)", re.IGNORECASE),
        ]
        
        # XSS patterns
        self.xss_patterns = [
            re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
            re.compile(r"javascript:", re.IGNORECASE),
            re.compile(r"on\w+\s*=", re.IGNORECASE),
        ]
        
        # Command injection patterns
        self.command_patterns = [
            re.compile(r"[;&|`$(){}]", re.IGNORECASE),
            re.compile(r"(rm|cat|ls|chmod|sudo)", re.IGNORECASE),
        ]
    
    def sanitize_string(self, value: str, strict: bool = False) -> str:
        """Sanitize string input.
        
        Args:
            value: Input string
            strict: Use strict sanitization
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return str(value)
        
        # Remove null bytes
        value = value.replace("\x00", "")
        
        # Check for SQL injection
        if any(pattern.search(value) for pattern in self.sql_patterns):
            if strict:
                raise ValueError("Potential SQL injection detected")
            logger.warning(f"Potential SQL injection in input: {value[:50]}")
            value = re.sub(r"[;&]", "", value)
        
        # Check for XSS
        if any(pattern.search(value) for pattern in self.xss_patterns):
            if strict:
                raise ValueError("Potential XSS detected")
            logger.warning(f"Potential XSS in input: {value[:50]}")
            # Escape HTML
            value = (
                value.replace("<", "&lt;")
                     .replace(">", "&gt;")
                     .replace('"', "&quot;")
                     .replace("'", "&#x27;")
            )
        
        return value
    
    def sanitize_dict(self, data: Dict[str, Any], strict: bool = False) -> Dict[str, Any]:
        """Sanitize dictionary input.
        
        Args:
            data: Input dictionary
            strict: Use strict sanitization
            
        Returns:
            Sanitized dictionary
        """
        sanitized = {}
        
        for key, value in data.items():
            # Sanitize key
            sanitized_key = self.sanitize_string(str(key), strict)
            
            # Sanitize value
            if isinstance(value, str):
                sanitized[sanitized_key] = self.sanitize_string(value, strict)
            elif isinstance(value, dict):
                sanitized[sanitized_key] = self.sanitize_dict(value, strict)
            elif isinstance(value, list):
                sanitized[sanitized_key] = [
                    self.sanitize_string(str(item), strict) if isinstance(item, str)
                    else self.sanitize_dict(item, strict) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                sanitized[sanitized_key] = value
        
        return sanitized


class SecurityHeaders:
    """Security headers for HTTP responses."""
    
    @staticmethod
    def get_security_headers(strict: bool = True) -> Dict[str, str]:
        """Get security headers for HTTP responses.
        
        Args:
            strict: Use strict security headers
            
        Returns:
            Dictionary of security headers
        """
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
        
        if strict:
            headers.update({
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
                "Content-Security-Policy": "default-src 'self'",
                "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            })
        
        return headers


class SecurityAuditor:
    """Security auditing and checks."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize security auditor.
        
        Args:
            config: Security configuration
        """
        self.config = config
        self.logger = logger
        self.rate_limiter = RateLimiter()
        self.input_sanitizer = InputSanitizer()
        self.failed_attempts: Dict[str, int] = defaultdict(int)
        self.locked_accounts: Dict[str, datetime] = {}
    
    def check_account_lockout(self, identifier: str) -> bool:
        """Check if account is locked.
        
        Args:
            identifier: User identifier
            
        Returns:
            True if account is locked
        """
        if identifier in self.locked_accounts:
            lock_time = self.locked_accounts[identifier]
            lockout_duration = timedelta(minutes=30)  # Configurable
            
            if datetime.now(timezone.utc) - lock_time < lockout_duration:
                return True
            else:
                # Unlock after duration
                del self.locked_accounts[identifier]
                self.failed_attempts[identifier] = 0
                return False
        
        return False
    
    def record_failed_attempt(self, identifier: str) -> None:
        """Record failed authentication attempt.
        
        Args:
            identifier: User identifier
        """
        self.failed_attempts[identifier] += 1
        max_attempts = 5  # Configurable
        
        if self.failed_attempts[identifier] >= max_attempts:
            self.locked_accounts[identifier] = datetime.now(timezone.utc)
            self.logger.warning(f"Account locked due to failed attempts: {identifier}")
    
    def record_successful_attempt(self, identifier: str) -> None:
        """Record successful authentication attempt.
        
        Args:
            identifier: User identifier
        """
        if identifier in self.failed_attempts:
            del self.failed_attempts[identifier]
        if identifier in self.locked_accounts:
            del self.locked_accounts[identifier]
    
    async def perform_security_checks(
        self,
        request_data: Dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> List[SecurityCheckResult]:
        """Perform security checks on request.
        
        Args:
            request_data: Request data
            user_id: User ID
            ip_address: IP address
            
        Returns:
            List of security check results
        """
        results = []
        
        # Check account lockout
        if user_id:
            if self.check_account_lockout(user_id):
                results.append(SecurityCheckResult(
                    passed=False,
                    check_name="account_lockout",
                    message="Account is locked due to too many failed attempts",
                    severity="high"
                ))
        
        # Check rate limiting
        if ip_address:
            rate_limit_result = await self.rate_limiter.check_rate_limit(
                "api_requests",
                ip_address
            )
            
            if not rate_limit_result.allowed:
                results.append(SecurityCheckResult(
                    passed=False,
                    check_name="rate_limit",
                    message=f"Rate limit exceeded. Limit: {rate_limit_result.limit}/window",
                    severity="medium",
                    metadata={
                        "remaining": rate_limit_result.remaining,
                        "reset_at": rate_limit_result.reset_at.isoformat()
                    }
                ))
        
        # Check input sanitization
        try:
            sanitized = self.input_sanitizer.sanitize_dict(request_data, strict=False)
            if sanitized != request_data:
                results.append(SecurityCheckResult(
                    passed=True,
                    check_name="input_sanitization",
                    message="Input sanitized (potential issues detected and cleaned)",
                    severity="low",
                    metadata={"sanitized_fields": list(sanitized.keys())}
                ))
        except Exception as e:
            results.append(SecurityCheckResult(
                passed=False,
                check_name="input_sanitization",
                message=f"Input sanitization failed: {e}",
                severity="high"
            ))
        
        return results


def get_security_auditor(config: Optional[SecurityConfig] = None) -> SecurityAuditor:
    """Get security auditor instance.
    
    Args:
        config: Security configuration
        
    Returns:
        SecurityAuditor instance
    """
    if config is None:
        from .config import get_config
        config = get_config().security
    
    return SecurityAuditor(config)

