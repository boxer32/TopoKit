"""Unit tests for Circuit Breaker."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from topokit.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerConfig,
    CircuitBreakerLevel,
)


class TestCircuitBreaker:
    """Test cases for Circuit Breaker."""
    
    @pytest.fixture
    def circuit_breaker_config(self):
        """Create circuit breaker configuration."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            timeout_seconds=60,
        )
    
    @pytest.fixture
    def circuit_breaker(self, circuit_breaker_config):
        """Create circuit breaker instance."""
        return CircuitBreaker(
            identifier="test-circuit",
            level=CircuitBreakerLevel.NODE,
            config=circuit_breaker_config
        )
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_initialization(self, circuit_breaker):
        """Test circuit breaker initialization."""
        assert circuit_breaker is not None
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state(self, circuit_breaker):
        """Test circuit breaker in closed state."""
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_call_success(self, circuit_breaker):
        """Test circuit breaker with successful call."""
        async def test_func():
            return "success"
        
        result = await circuit_breaker.call(test_func)
        
        assert result == "success"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_call_failure(self, circuit_breaker):
        """Test circuit breaker with failed call."""
        async def test_func():
            raise ValueError("test error")
        
        with pytest.raises(ValueError):
            await circuit_breaker.call(test_func)
        
        # Should have recorded failure
        assert circuit_breaker.metrics.failed_requests > 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_trips_to_open(self, circuit_breaker):
        """Test circuit breaker trips to open state after threshold failures."""
        async def failing_func():
            raise ValueError("failure")
        
        # Record failures up to threshold
        for _ in range(circuit_breaker.config.failure_threshold):
            try:
                await circuit_breaker.call(failing_func)
            except ValueError:
                pass
        
        # Should be open now
        assert circuit_breaker.state == CircuitBreakerState.OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics(self, circuit_breaker):
        """Test circuit breaker metrics collection."""
        async def test_func():
            return "success"
        
        await circuit_breaker.call(test_func)
        
        assert circuit_breaker.metrics.total_requests > 0
        assert circuit_breaker.metrics.successful_requests > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

