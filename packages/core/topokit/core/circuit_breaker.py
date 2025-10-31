"""Circuit Breaker implementation for TopoKit with multi-tier failure protection."""

import asyncio
import time
from typing import Any, Dict, List, Optional, Set, Callable, Union
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
import logging

from .logging import get_logger


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service is back
    BYPASS = "bypass"      # Bypass circuit breaker


class CircuitBreakerLevel(str, Enum):
    """Circuit breaker levels."""
    NODE = "node"          # Node-level circuit breaker
    EDGE = "edge"          # Edge-level circuit breaker
    DOMAIN = "domain"      # Domain-level circuit breaker
    SYSTEM = "system"      # System-level circuit breaker


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5          # Number of failures before opening
    success_threshold: int = 3          # Number of successes to close from half-open
    timeout_seconds: int = 60           # Timeout before trying half-open
    max_requests_half_open: int = 5    # Max requests in half-open state
    failure_rate_threshold: float = 0.5  # Failure rate threshold (0.0-1.0)
    window_size_seconds: int = 60       # Time window for failure rate calculation
    enable_bypass: bool = True          # Enable bypass mode
    enable_metrics: bool = True         # Enable metrics collection


@dataclass
class CircuitBreakerMetrics:
    """Circuit breaker metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    bypassed_requests: int = 0
    state_changes: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    current_failure_rate: float = 0.0
    average_response_time_ms: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests


@dataclass
class CircuitBreakerEvent:
    """Circuit breaker event."""
    timestamp: datetime
    event_type: str
    level: CircuitBreakerLevel
    identifier: str
    details: Dict[str, Any] = field(default_factory=dict)


class CircuitBreaker:
    """Circuit breaker implementation with multi-tier failure protection."""
    
    def __init__(self, 
                 identifier: str,
                 level: CircuitBreakerLevel,
                 config: Optional[CircuitBreakerConfig] = None):
        """Initialize circuit breaker.
        
        Args:
            identifier: Unique identifier for the circuit breaker
            level: Circuit breaker level
            config: Configuration options
        """
        self.identifier = identifier
        self.level = level
        self.config = config or CircuitBreakerConfig()
        self.logger = get_logger(__name__)
        
        # State management
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_requests = 0
        self.last_failure_time: Optional[datetime] = None
        self.state_change_time = datetime.now(timezone.utc)
        
        # Metrics
        self.metrics = CircuitBreakerMetrics()
        
        # Request tracking for failure rate calculation
        self.request_history: List[Dict[str, Any]] = []
        self._history_lock = asyncio.Lock()
        
        # Event callbacks
        self._event_callbacks: List[Callable[[CircuitBreakerEvent], None]] = []
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: When circuit is open
            CircuitBreakerTimeoutError: When circuit times out
        """
        async with self._lock:
            # Check if circuit breaker should allow the request
            if not await self._should_allow_request():
                raise CircuitBreakerOpenError(f"Circuit breaker {self.identifier} is {self.state.value}")
            
            # Increment half-open requests if in half-open state
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.half_open_requests += 1
            
            # Execute the function
            start_time = time.time()
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Record success
                await self._record_success(time.time() - start_time)
                return result
                
            except Exception as e:
                # Record failure
                await self._record_failure(time.time() - start_time, str(e))
                raise e
    
    async def _should_allow_request(self) -> bool:
        """Check if request should be allowed based on current state."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        elif self.state == CircuitBreakerState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time and \
               datetime.now(timezone.utc) - self.last_failure_time > timedelta(seconds=self.config.timeout_seconds):
                await self._transition_to_half_open()
                return True
            return False
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Allow limited requests in half-open state
            return self.half_open_requests < self.config.max_requests_half_open
        
        elif self.state == CircuitBreakerState.BYPASS:
            return True
        
        return False
    
    async def _record_success(self, response_time: float):
        """Record successful request."""
        self.metrics.total_requests += 1
        self.metrics.successful_requests += 1
        self.metrics.last_success_time = datetime.now(timezone.utc)
        
        # Update response time metrics
        self._update_response_time_metrics(response_time)
        
        # Add to request history
        await self._add_to_history(True, response_time)
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                await self._transition_to_closed()
        
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
        
        # Emit success event
        await self._emit_event("success", {
            "response_time_ms": response_time * 1000,
            "state": self.state.value
        })
    
    async def _record_failure(self, response_time: float, error_message: str):
        """Record failed request."""
        self.metrics.total_requests += 1
        self.metrics.failed_requests += 1
        self.metrics.last_failure_time = datetime.now(timezone.utc)
        
        # Update response time metrics
        self._update_response_time_metrics(response_time)
        
        # Add to request history
        await self._add_to_history(False, response_time)
        
        if self.state == CircuitBreakerState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.config.failure_threshold:
                await self._transition_to_open()
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Any failure in half-open state goes back to open
            await self._transition_to_open()
        
        # Emit failure event
        await self._emit_event("failure", {
            "response_time_ms": response_time * 1000,
            "error_message": error_message,
            "state": self.state.value
        })
    
    async def _transition_to_open(self):
        """Transition circuit breaker to open state."""
        if self.state != CircuitBreakerState.OPEN:
            self.state = CircuitBreakerState.OPEN
            self.state_change_time = datetime.now(timezone.utc)
            self.metrics.state_changes += 1
            self.half_open_requests = 0
            
            self.logger.warning(f"Circuit breaker {self.identifier} opened")
            await self._emit_event("state_change", {
                "new_state": "open",
                "failure_count": self.failure_count
            })
    
    async def _transition_to_half_open(self):
        """Transition circuit breaker to half-open state."""
        if self.state != CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.HALF_OPEN
            self.state_change_time = datetime.now(timezone.utc)
            self.metrics.state_changes += 1
            self.success_count = 0
            self.half_open_requests = 0
            
            self.logger.info(f"Circuit breaker {self.identifier} transitioned to half-open")
            await self._emit_event("state_change", {
                "new_state": "half_open",
                "timeout_seconds": self.config.timeout_seconds
            })
    
    async def _transition_to_closed(self):
        """Transition circuit breaker to closed state."""
        if self.state != CircuitBreakerState.CLOSED:
            self.state = CircuitBreakerState.CLOSED
            self.state_change_time = datetime.now(timezone.utc)
            self.metrics.state_changes += 1
            self.failure_count = 0
            self.success_count = 0
            self.half_open_requests = 0
            
            self.logger.info(f"Circuit breaker {self.identifier} closed")
            await self._emit_event("state_change", {
                "new_state": "closed",
                "success_count": self.success_count
            })
    
    async def _transition_to_bypass(self):
        """Transition circuit breaker to bypass state."""
        if self.state != CircuitBreakerState.BYPASS:
            self.state = CircuitBreakerState.BYPASS
            self.state_change_time = datetime.now(timezone.utc)
            self.metrics.state_changes += 1
            
            self.logger.info(f"Circuit breaker {self.identifier} bypassed")
            await self._emit_event("state_change", {
                "new_state": "bypass"
            })
    
    async def _add_to_history(self, success: bool, response_time: float):
        """Add request to history for failure rate calculation."""
        async with self._history_lock:
            now = datetime.now(timezone.utc)
            self.request_history.append({
                "timestamp": now,
                "success": success,
                "response_time": response_time
            })
            
            # Remove old entries outside the window
            cutoff = now - timedelta(seconds=self.config.window_size_seconds)
            self.request_history = [
                req for req in self.request_history 
                if req["timestamp"] > cutoff
            ]
            
            # Calculate current failure rate
            if self.request_history:
                failures = sum(1 for req in self.request_history if not req["success"])
                self.metrics.current_failure_rate = failures / len(self.request_history)
    
    def _update_response_time_metrics(self, response_time: float):
        """Update response time metrics."""
        response_time_ms = response_time * 1000
        if self.metrics.average_response_time_ms == 0:
            self.metrics.average_response_time_ms = response_time_ms
        else:
            # Update running average
            self.metrics.average_response_time_ms = (
                (self.metrics.average_response_time_ms * (self.metrics.total_requests - 1) + response_time_ms) 
                / self.metrics.total_requests
            )
    
    async def _emit_event(self, event_type: str, details: Dict[str, Any]):
        """Emit circuit breaker event."""
        event = CircuitBreakerEvent(
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            level=self.level,
            identifier=self.identifier,
            details=details
        )
        
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"Error in circuit breaker event callback: {e}")
    
    def add_event_callback(self, callback: Callable[[CircuitBreakerEvent], None]):
        """Add event callback.
        
        Args:
            callback: Callback function
        """
        self._event_callbacks.append(callback)
    
    def remove_event_callback(self, callback: Callable[[CircuitBreakerEvent], None]):
        """Remove event callback.
        
        Args:
            callback: Callback function
        """
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
    
    async def reset(self):
        """Reset circuit breaker to closed state."""
        async with self._lock:
            await self._transition_to_closed()
            self.request_history.clear()
            self.metrics = CircuitBreakerMetrics()
            self.logger.info(f"Circuit breaker {self.identifier} reset")
    
    async def bypass(self):
        """Bypass circuit breaker."""
        if self.config.enable_bypass:
            async with self._lock:
                await self._transition_to_bypass()
    
    async def unbypass(self):
        """Remove bypass and return to normal operation."""
        async with self._lock:
            await self._transition_to_closed()
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state.
        
        Returns:
            State information
        """
        return {
            "identifier": self.identifier,
            "level": self.level.value,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "half_open_requests": self.half_open_requests,
            "last_failure_time": self.metrics.last_failure_time.isoformat() if self.metrics.last_failure_time else None,
            "last_success_time": self.metrics.last_success_time.isoformat() if self.metrics.last_success_time else None,
            "state_change_time": self.state_change_time.isoformat(),
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "success_rate": self.metrics.success_rate,
                "failure_rate": self.metrics.failure_rate,
                "current_failure_rate": self.metrics.current_failure_rate,
                "average_response_time_ms": self.metrics.average_response_time_ms,
                "state_changes": self.metrics.state_changes
            }
        }
    
    def get_metrics(self) -> CircuitBreakerMetrics:
        """Get circuit breaker metrics.
        
        Returns:
            Circuit breaker metrics
        """
        return self.metrics


class CircuitBreakerManager:
    """Manager for multiple circuit breakers with hierarchical protection."""
    
    def __init__(self):
        """Initialize circuit breaker manager."""
        self.logger = get_logger(__name__)
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._level_hierarchy = {
            CircuitBreakerLevel.NODE: 1,
            CircuitBreakerLevel.EDGE: 2,
            CircuitBreakerLevel.DOMAIN: 3,
            CircuitBreakerLevel.SYSTEM: 4
        }
    
    def create_circuit_breaker(self, 
                              identifier: str, 
                              level: CircuitBreakerLevel,
                              config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Create a new circuit breaker.
        
        Args:
            identifier: Unique identifier
            level: Circuit breaker level
            config: Configuration options
            
        Returns:
            Circuit breaker instance
        """
        if identifier in self._circuit_breakers:
            raise ValueError(f"Circuit breaker {identifier} already exists")
        
        circuit_breaker = CircuitBreaker(identifier, level, config)
        self._circuit_breakers[identifier] = circuit_breaker
        
        self.logger.info(f"Created circuit breaker {identifier} at {level.value} level")
        return circuit_breaker
    
    def get_circuit_breaker(self, identifier: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by identifier.
        
        Args:
            identifier: Circuit breaker identifier
            
        Returns:
            Circuit breaker instance or None
        """
        return self._circuit_breakers.get(identifier)
    
    def remove_circuit_breaker(self, identifier: str) -> bool:
        """Remove circuit breaker.
        
        Args:
            identifier: Circuit breaker identifier
            
        Returns:
            True if removed successfully
        """
        if identifier in self._circuit_breakers:
            del self._circuit_breakers[identifier]
            self.logger.info(f"Removed circuit breaker {identifier}")
            return True
        return False
    
    async def call_with_protection(self, 
                                 identifier: str, 
                                 func: Callable, 
                                 *args, 
                                 **kwargs) -> Any:
        """Call function with circuit breaker protection.
        
        Args:
            identifier: Circuit breaker identifier
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        circuit_breaker = self.get_circuit_breaker(identifier)
        if not circuit_breaker:
            raise ValueError(f"Circuit breaker {identifier} not found")
        
        return await circuit_breaker.call(func, *args, **kwargs)
    
    def get_circuit_breakers_by_level(self, level: CircuitBreakerLevel) -> List[CircuitBreaker]:
        """Get all circuit breakers at a specific level.
        
        Args:
            level: Circuit breaker level
            
        Returns:
            List of circuit breakers
        """
        return [
            cb for cb in self._circuit_breakers.values() 
            if cb.level == level
        ]
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get states of all circuit breakers.
        
        Returns:
            Dictionary of circuit breaker states
        """
        return {
            identifier: cb.get_state() 
            for identifier, cb in self._circuit_breakers.items()
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health based on circuit breakers.
        
        Returns:
            System health information
        """
        total_circuits = len(self._circuit_breakers)
        open_circuits = sum(1 for cb in self._circuit_breakers.values() if cb.state == CircuitBreakerState.OPEN)
        half_open_circuits = sum(1 for cb in self._circuit_breakers.values() if cb.state == CircuitBreakerState.HALF_OPEN)
        bypassed_circuits = sum(1 for cb in self._circuit_breakers.values() if cb.state == CircuitBreakerState.BYPASS)
        
        return {
            "total_circuits": total_circuits,
            "open_circuits": open_circuits,
            "half_open_circuits": half_open_circuits,
            "bypassed_circuits": bypassed_circuits,
            "closed_circuits": total_circuits - open_circuits - half_open_circuits - bypassed_circuits,
            "health_score": (total_circuits - open_circuits) / total_circuits if total_circuits > 0 else 1.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreakerTimeoutError(Exception):
    """Exception raised when circuit breaker times out."""
    pass


# Global circuit breaker manager
_circuit_breaker_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get global circuit breaker manager.
    
    Returns:
        CircuitBreakerManager instance
    """
    global _circuit_breaker_manager
    
    if _circuit_breaker_manager is None:
        _circuit_breaker_manager = CircuitBreakerManager()
    
    return _circuit_breaker_manager
