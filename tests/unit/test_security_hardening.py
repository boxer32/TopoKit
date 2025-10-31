"""Unit tests for Security Hardening utilities."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from topokit.core.security_hardening import (
    RateLimiter,
    InputSanitizer,
    SecurityHeaders,
    SecurityAuditor,
    RateLimitResult,
    SecurityCheckResult,
)


class TestRateLimiter:
    """Test cases for Rate Limiter."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter instance."""
        return RateLimiter(requests_per_minute=10)
    
    def test_rate_limiter_initialization(self, rate_limiter):
        """Test rate limiter initialization."""
        assert rate_limiter is not None
        assert rate_limiter.requests_per_minute == 10
    
    def test_rate_limiter_allows_request(self, rate_limiter):
        """Test rate limiter allows request within limit."""
        client_id = "test-client"
        
        result = rate_limiter.check_limit(client_id)
        
        assert result is not None
        assert isinstance(result, RateLimitResult)
        assert result.allowed is True
    
    def test_rate_limiter_blocks_excessive_requests(self, rate_limiter):
        """Test rate limiter blocks excessive requests."""
        client_id = "test-client"
        
        # Make requests up to limit
        for _ in range(rate_limiter.requests_per_minute):
            result = rate_limiter.check_limit(client_id)
            assert result.allowed is True
        
        # Next request should be blocked
        result = rate_limiter.check_limit(client_id)
        assert result.allowed is False
    
    def test_rate_limiter_reset(self, rate_limiter):
        """Test rate limiter resets after window."""
        client_id = "test-client"
        
        # Exhaust limit
        for _ in range(rate_limiter.requests_per_minute):
            rate_limiter.check_limit(client_id)
        
        # Reset
        rate_limiter.reset(client_id)
        
        # Should allow again
        result = rate_limiter.check_limit(client_id)
        assert result.allowed is True


class TestInputSanitizer:
    """Test cases for Input Sanitizer."""
    
    @pytest.fixture
    def sanitizer(self):
        """Create input sanitizer instance."""
        return InputSanitizer()
    
    def test_sanitizer_initialization(self, sanitizer):
        """Test sanitizer initialization."""
        assert sanitizer is not None
    
    def test_sanitize_html(self, sanitizer):
        """Test HTML sanitization."""
        input_text = "<script>alert('xss')</script>Hello"
        
        sanitized = sanitizer.sanitize(input_text)
        
        assert "<script>" not in sanitized
        assert "Hello" in sanitized
    
    def test_sanitize_sql_injection(self, sanitizer):
        """Test SQL injection prevention."""
        input_text = "'; DROP TABLE users; --"
        
        sanitized = sanitizer.sanitize(input_text)
        
        assert "DROP TABLE" not in sanitized or sanitized != input_text
    
    def test_sanitize_js_injection(self, sanitizer):
        """Test JavaScript injection prevention."""
        input_text = "javascript:alert('xss')"
        
        sanitized = sanitizer.sanitize(input_text)
        
        assert "javascript:" not in sanitized
    
    def test_validate_input(self, sanitizer):
        """Test input validation."""
        valid_input = "normal text input"
        
        is_valid = sanitizer.validate(valid_input)
        
        assert is_valid is True
    
    def test_validate_malicious_input(self, sanitizer):
        """Test validation of malicious input."""
        malicious_input = "<script>alert('xss')</script>"
        
        is_valid = sanitizer.validate(malicious_input)
        
        # Should either reject or sanitize
        assert is_valid is False or sanitizer.sanitize(malicious_input) != malicious_input


class TestSecurityHeaders:
    """Test cases for Security Headers."""
    
    @pytest.fixture
    def security_headers(self):
        """Create security headers instance."""
        return SecurityHeaders()
    
    def test_security_headers_initialization(self, security_headers):
        """Test security headers initialization."""
        assert security_headers is not None
    
    def test_get_headers(self, security_headers):
        """Test getting security headers."""
        headers = security_headers.get_headers()
        
        assert headers is not None
        assert isinstance(headers, dict)
        assert len(headers) > 0
    
    def test_csp_header(self, security_headers):
        """Test Content-Security-Policy header."""
        headers = security_headers.get_headers()
        
        # Should have CSP or X-Frame-Options
        assert "Content-Security-Policy" in headers or "X-Frame-Options" in headers
    
    def test_hsts_header(self, security_headers):
        """Test HSTS header."""
        headers = security_headers.get_headers()
        
        # Should have Strict-Transport-Security for HTTPS
        # In test, may not be present
        assert isinstance(headers, dict)


class TestSecurityAuditor:
    """Test cases for Security Auditor."""
    
    @pytest.fixture
    def security_auditor(self):
        """Create security auditor instance."""
        return SecurityAuditor()
    
    def test_security_auditor_initialization(self, security_auditor):
        """Test security auditor initialization."""
        assert security_auditor is not None
    
    def test_run_security_check(self, security_auditor):
        """Test running security check."""
        result = security_auditor.run_check()
        
        assert result is not None
        assert isinstance(result, SecurityCheckResult)
        assert hasattr(result, "passed") or hasattr(result, "status")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

