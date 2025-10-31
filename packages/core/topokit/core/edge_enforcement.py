"""Edge Enforcement Engine for TopoKit with contract validation and policy enforcement."""

import asyncio
import time
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging

from ..types.topology import EdgePolicy, Contract, Node
from ..types.validation import ValidationResult, ValidationError, ValidationErrorType
from .schema_validator import SchemaValidator
from .guardrails import MultiStageGuardrails, GuardrailResult


class EnforcementAction(str, Enum):
    """Edge enforcement actions."""
    ALLOW = "allow"
    DENY = "deny"
    TRANSFORM = "transform"
    RATE_LIMIT = "rate_limit"
    AUDIT = "audit"
    HUMAN_REVIEW = "human_review"


class EnforcementResult(str, Enum):
    """Enforcement results."""
    SUCCESS = "success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    TRANSFORMED = "transformed"
    AUDITED = "audited"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


@dataclass
class EdgeEnforcementMetrics:
    """Edge enforcement metrics."""
    edge_id: str
    total_requests: int = 0
    allowed_requests: int = 0
    denied_requests: int = 0
    transformed_requests: int = 0
    rate_limited_requests: int = 0
    human_review_requests: int = 0
    average_processing_time_ms: float = 0.0
    last_request_time: Optional[datetime] = None
    error_count: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return (self.allowed_requests + self.transformed_requests) / self.total_requests
    
    @property
    def denial_rate(self) -> float:
        """Calculate denial rate."""
        if self.total_requests == 0:
            return 0.0
        return self.denied_requests / self.total_requests


@dataclass
class EdgeEnforcementResult:
    """Result of edge enforcement."""
    result: EnforcementResult
    action: EnforcementAction
    message: str
    data: Any = None
    transformed_data: Optional[Any] = None
    validation_errors: List[ValidationError] = field(default_factory=list)
    guardrail_results: List[GuardrailResult] = field(default_factory=list)
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class RateLimiter:
    """Rate limiter for edge enforcement."""
    
    def __init__(self, max_requests: int, window_seconds: int):
        """Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: List[float] = []
        self._lock = asyncio.Lock()
    
    async def is_allowed(self) -> bool:
        """Check if request is allowed under rate limit.
        
        Returns:
            True if request is allowed
        """
        async with self._lock:
            now = time.time()
            
            # Remove old requests outside window
            cutoff = now - self.window_seconds
            self.requests = [req_time for req_time in self.requests if req_time > cutoff]
            
            # Check if under limit
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            
            return False
    
    async def get_remaining_requests(self) -> int:
        """Get remaining requests in current window.
        
        Returns:
            Number of remaining requests
        """
        async with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            self.requests = [req_time for req_time in self.requests if req_time > cutoff]
            return max(0, self.max_requests - len(self.requests))


class EdgeEnforcementEngine:
    """Edge enforcement engine with contract validation and policy enforcement."""
    
    def __init__(self, 
                 schema_validator: Optional[SchemaValidator] = None,
                 guardrails: Optional[MultiStageGuardrails] = None):
        """Initialize edge enforcement engine.
        
        Args:
            schema_validator: Schema validator for contracts
            guardrails: Guardrails system for additional validation
        """
        self.schema_validator = schema_validator or SchemaValidator()
        self.guardrails = guardrails
        self.logger = logging.getLogger(__name__)
        
        # Edge metrics tracking
        self._metrics: Dict[str, EdgeEnforcementMetrics] = {}
        self._rate_limiters: Dict[str, RateLimiter] = {}
        self._enforcement_lock = asyncio.Lock()
        
        # Custom enforcement rules
        self._custom_rules: Dict[str, Callable] = {}
    
    async def enforce(self, 
                     edge: EdgePolicy, 
                     from_node: Node, 
                     to_node: Node,
                     data: Any,
                     session_id: str,
                     trace_id: str) -> EdgeEnforcementResult:
        """Enforce edge policy with contract validation.
        
        Args:
            edge: Edge policy to enforce
            from_node: Source node
            to_node: Target node
            data: Data to validate
            session_id: Session identifier
            trace_id: Trace identifier
            
        Returns:
            Edge enforcement result
        """
        start_time = time.time()
        
        try:
            # Initialize metrics if not exists
            if edge.id not in self._metrics:
                self._metrics[edge.id] = EdgeEnforcementMetrics(edge_id=edge.id)
            
            metrics = self._metrics[edge.id]
            metrics.total_requests += 1
            metrics.last_request_time = datetime.now(timezone.utc)
            
            # Check if edge is enabled
            if not edge.allow:
                return await self._create_result(
                    edge, EnforcementResult.FAILED, EnforcementAction.DENY,
                    "Edge is disabled", data, start_time
                )
            
            # Apply rate limiting
            if not await self._check_rate_limit(edge):
                metrics.rate_limited_requests += 1
                return await self._create_result(
                    edge, EnforcementResult.RATE_LIMITED, EnforcementAction.RATE_LIMIT,
                    "Rate limit exceeded", data, start_time
                )
            
            # Validate contracts
            contract_result = await self._validate_contracts(edge, data, from_node, to_node)
            if not contract_result.success:
                metrics.denied_requests += 1
                return await self._create_result(
                    edge, EnforcementResult.FAILED, EnforcementAction.DENY,
                    f"Contract validation failed: {contract_result.message}",
                    data, start_time, validation_errors=contract_result.errors
                )
            
            # Apply custom enforcement rules
            custom_result = await self._apply_custom_rules(edge, from_node, to_node, data, session_id, trace_id)
            if custom_result is not None:
                if custom_result.result == EnforcementResult.FAILED:
                    metrics.denied_requests += 1
                elif custom_result.result == EnforcementResult.TRANSFORMED:
                    metrics.transformed_requests += 1
                elif custom_result.result == EnforcementResult.HUMAN_REVIEW_REQUIRED:
                    metrics.human_review_requests += 1
                
                return custom_result
            
            # Apply guardrails if available
            if self.guardrails:
                guardrail_result = await self.guardrails.apply_pre_processing(
                    data=data, node=to_node, trace_id=trace_id
                )
                
                if not guardrail_result.passed:
                    metrics.denied_requests += 1
                    return await self._create_result(
                        edge, EnforcementResult.FAILED, EnforcementAction.DENY,
                        f"Guardrails failed: {guardrail_result.message}",
                        data, start_time, guardrail_results=[guardrail_result]
                    )
            
            # Check timeout
            if edge.timeout_ms > 0:
                elapsed_ms = (time.time() - start_time) * 1000
                if elapsed_ms > edge.timeout_ms:
                    metrics.denied_requests += 1
                    return await self._create_result(
                        edge, EnforcementResult.FAILED, EnforcementAction.DENY,
                        f"Request timeout exceeded: {elapsed_ms:.2f}ms > {edge.timeout_ms}ms",
                        data, start_time
                    )
            
            # Success
            metrics.allowed_requests += 1
            return await self._create_result(
                edge, EnforcementResult.SUCCESS, EnforcementAction.ALLOW,
                "Edge enforcement passed", data, start_time
            )
            
        except Exception as e:
            metrics.error_count += 1
            self.logger.error(f"Edge enforcement error for {edge.id}: {e}")
            
            return await self._create_result(
                edge, EnforcementResult.FAILED, EnforcementAction.DENY,
                f"Enforcement error: {str(e)}", data, start_time
            )
    
    async def _check_rate_limit(self, edge: EdgePolicy) -> bool:
        """Check rate limiting for edge."""
        if edge.max_retries <= 0:
            return True
        
        # Get or create rate limiter
        if edge.id not in self._rate_limiters:
            self._rate_limiters[edge.id] = RateLimiter(
                max_requests=edge.max_retries,
                window_seconds=60  # 1 minute window
            )
        
        rate_limiter = self._rate_limiters[edge.id]
        return await rate_limiter.is_allowed()
    
    async def _validate_contracts(self, 
                                edge: EdgePolicy, 
                                data: Any, 
                                from_node: Node, 
                                to_node: Node) -> ValidationResult:
        """Validate data against edge contracts."""
        if not edge.contracts:
            return ValidationResult(success=True, data=data)
        
        # For now, return success - in full implementation, this would validate against actual contracts
        # This would involve looking up contract schemas and validating data against them
        return ValidationResult(success=True, data=data)
    
    async def _apply_custom_rules(self, 
                                edge: EdgePolicy, 
                                from_node: Node, 
                                to_node: Node, 
                                data: Any,
                                session_id: str,
                                trace_id: str) -> Optional[EdgeEnforcementResult]:
        """Apply custom enforcement rules."""
        if edge.id not in self._custom_rules:
            return None
        
        try:
            rule_func = self._custom_rules[edge.id]
            result = await rule_func(edge, from_node, to_node, data, session_id, trace_id)
            return result
        except Exception as e:
            self.logger.error(f"Custom rule error for edge {edge.id}: {e}")
            return EdgeEnforcementResult(
                result=EnforcementResult.FAILED,
                action=EnforcementAction.DENY,
                message=f"Custom rule error: {str(e)}"
            )
    
    async def _create_result(self, 
                           edge: EdgePolicy,
                           result: EnforcementResult,
                           action: EnforcementAction,
                           message: str,
                           data: Any,
                           start_time: float,
                           validation_errors: List[ValidationError] = None,
                           guardrail_results: List[GuardrailResult] = None) -> EdgeEnforcementResult:
        """Create edge enforcement result."""
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Update metrics
        if edge.id in self._metrics:
            metrics = self._metrics[edge.id]
            if metrics.average_processing_time_ms == 0:
                metrics.average_processing_time_ms = processing_time_ms
            else:
                # Update running average
                metrics.average_processing_time_ms = (
                    (metrics.average_processing_time_ms * (metrics.total_requests - 1) + processing_time_ms) 
                    / metrics.total_requests
                )
        
        return EdgeEnforcementResult(
            result=result,
            action=action,
            message=message,
            data=data,
            validation_errors=validation_errors or [],
            guardrail_results=guardrail_results or [],
            processing_time_ms=processing_time_ms,
            metadata={
                "edge_id": edge.id,
                "from_node": edge.from_node,
                "to_node": edge.to_node,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def add_custom_rule(self, edge_id: str, rule_func: Callable) -> None:
        """Add custom enforcement rule for edge.
        
        Args:
            edge_id: Edge identifier
            rule_func: Custom rule function
        """
        self._custom_rules[edge_id] = rule_func
        self.logger.info(f"Added custom rule for edge {edge_id}")
    
    def remove_custom_rule(self, edge_id: str) -> None:
        """Remove custom enforcement rule for edge.
        
        Args:
            edge_id: Edge identifier
        """
        if edge_id in self._custom_rules:
            del self._custom_rules[edge_id]
            self.logger.info(f"Removed custom rule for edge {edge_id}")
    
    def get_metrics(self, edge_id: Optional[str] = None) -> Union[EdgeEnforcementMetrics, Dict[str, EdgeEnforcementMetrics]]:
        """Get enforcement metrics.
        
        Args:
            edge_id: Specific edge ID (if None, returns all metrics)
            
        Returns:
            Metrics for specific edge or all edges
        """
        if edge_id:
            return self._metrics.get(edge_id, EdgeEnforcementMetrics(edge_id=edge_id))
        return self._metrics.copy()
    
    def reset_metrics(self, edge_id: Optional[str] = None) -> None:
        """Reset enforcement metrics.
        
        Args:
            edge_id: Specific edge ID (if None, resets all metrics)
        """
        if edge_id:
            if edge_id in self._metrics:
                self._metrics[edge_id] = EdgeEnforcementMetrics(edge_id=edge_id)
        else:
            self._metrics.clear()
        
        self.logger.info(f"Reset metrics for edge {edge_id or 'all'}")
    
    def get_rate_limiter_status(self, edge_id: str) -> Optional[Dict[str, Any]]:
        """Get rate limiter status for edge.
        
        Args:
            edge_id: Edge identifier
            
        Returns:
            Rate limiter status or None if not found
        """
        if edge_id not in self._rate_limiters:
            return None
        
        rate_limiter = self._rate_limiters[edge_id]
        return {
            "max_requests": rate_limiter.max_requests,
            "window_seconds": rate_limiter.window_seconds,
            "current_requests": len(rate_limiter.requests),
            "remaining_requests": asyncio.create_task(rate_limiter.get_remaining_requests())
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get enforcement engine statistics."""
        total_requests = sum(metrics.total_requests for metrics in self._metrics.values())
        total_allowed = sum(metrics.allowed_requests for metrics in self._metrics.values())
        total_denied = sum(metrics.denied_requests for metrics in self._metrics.values())
        total_errors = sum(metrics.error_count for metrics in self._metrics.values())
        
        return {
            "total_edges": len(self._metrics),
            "total_requests": total_requests,
            "allowed_requests": total_allowed,
            "denied_requests": total_denied,
            "error_count": total_errors,
            "success_rate": total_allowed / total_requests if total_requests > 0 else 0.0,
            "denial_rate": total_denied / total_requests if total_requests > 0 else 0.0,
            "custom_rules_count": len(self._custom_rules),
            "rate_limiters_count": len(self._rate_limiters)
        }
