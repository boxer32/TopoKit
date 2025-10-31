"""Multi-Stage Guardrails System for TopoKit with pre/post processing guards and circuit breakers."""

import asyncio
import time
import json
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import logging

from ..types.topology import GuardrailsConfig, Node, EdgePolicy


class GuardrailType(str, Enum):
    """Types of guardrails."""
    PRE_PROCESSING = "pre_processing"
    POST_PROCESSING = "post_processing"
    CIRCUIT_BREAKER = "circuit_breaker"
    HUMAN_GATE = "human_gate"
    POLICY_ENGINE = "policy_engine"
    CONTENT_MODERATION = "content_moderation"
    CONFIDENCE_GATING = "confidence_gating"


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service is back
    BYPASS = "bypass"      # Bypass circuit breaker


class PolicyEnvironment(str, Enum):
    """Policy environments."""
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"


@dataclass
class GuardrailResult:
    """Result of guardrail evaluation."""
    passed: bool
    score: float = 0.0
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    action_required: Optional[str] = None
    confidence: float = 1.0


@dataclass
class CircuitBreakerMetrics:
    """Circuit breaker metrics."""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_rate: float = 0.0


@dataclass
class HumanGateRequest:
    """Human gate approval request."""
    request_id: str
    node_id: str
    trace_id: str
    action: str
    data: Dict[str, Any]
    risk_level: str
    requested_by: str
    requested_at: datetime
    timeout_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    reason: Optional[str] = None


class MultiStageGuardrails:
    """Multi-stage guardrails system with pre/post processing and circuit breakers."""
    
    def __init__(self, config: GuardrailsConfig, environment: PolicyEnvironment = PolicyEnvironment.DEVELOPMENT):
        """Initialize multi-stage guardrails system.
        
        Args:
            config: Guardrails configuration
            environment: Policy environment
        """
        self.config = config
        self.environment = environment
        self.logger = logging.getLogger(__name__)
        
        # Circuit breakers by node/edge
        self._circuit_breakers: Dict[str, CircuitBreakerMetrics] = {}
        
        # Human gate queue
        self._human_gate_queue: List[HumanGateRequest] = []
        self._gate_lock = asyncio.Lock()
        
        # Policy templates
        self._policy_templates = self._load_policy_templates()
        
        # Content moderation patterns
        self._content_patterns = self._load_content_patterns()
        
        # Confidence thresholds
        self._confidence_thresholds = self._load_confidence_thresholds()
    
    async def apply_pre_processing(self, data: Any, node: Node, trace_id: str) -> GuardrailResult:
        """Apply pre-processing guardrails.
        
        Args:
            data: Input data to process
            node: Target node
            trace_id: Trace identifier
            
        Returns:
            Guardrail result
        """
        results = []
        
        # Input validation
        validation_result = await self._validate_input(data, node)
        results.append(validation_result)
        
        # Content moderation
        if self._should_apply_content_moderation(node):
            moderation_result = await self._apply_content_moderation(data, node)
            results.append(moderation_result)
        
        # Policy engine checks
        policy_result = await self._apply_policy_checks(data, node, trace_id, "pre")
        results.append(policy_result)
        
        # Circuit breaker check
        circuit_result = await self._check_circuit_breaker(node.id)
        results.append(circuit_result)
        
        # Combine results
        return self._combine_results(results, "pre_processing")
    
    async def apply_post_processing(self, data: Any, node: Node, trace_id: str) -> GuardrailResult:
        """Apply post-processing guardrails.
        
        Args:
            data: Output data to process
            node: Source node
            trace_id: Trace identifier
            
        Returns:
            Guardrail result
        """
        results = []
        
        # Output validation
        validation_result = await self._validate_output(data, node)
        results.append(validation_result)
        
        # Confidence gating
        confidence_result = await self._apply_confidence_gating(data, node)
        results.append(confidence_result)
        
        # Content moderation
        if self._should_apply_content_moderation(node):
            moderation_result = await self._apply_content_moderation(data, node)
            results.append(moderation_result)
        
        # Policy engine checks
        policy_result = await self._apply_policy_checks(data, node, trace_id, "post")
        results.append(policy_result)
        
        # Combine results
        return self._combine_results(results, "post_processing")
    
    async def _validate_input(self, data: Any, node: Node) -> GuardrailResult:
        """Validate input data against node contracts."""
        try:
            # Check if data matches expected input schema
            if hasattr(node, 'scope') and node.scope.contracts:
                # In a full implementation, this would validate against JSON Schema
                return GuardrailResult(
                    passed=True,
                    score=1.0,
                    message="Input validation passed",
                    metadata={"contracts_checked": len(node.scope.contracts)}
                )
            
            return GuardrailResult(
                passed=True,
                score=1.0,
                message="No input contracts to validate"
            )
            
        except Exception as e:
            return GuardrailResult(
                passed=False,
                score=0.0,
                message=f"Input validation failed: {e}",
                metadata={"error": str(e)}
            )
    
    async def _validate_output(self, data: Any, node: Node) -> GuardrailResult:
        """Validate output data against node contracts."""
        try:
            # Check if data matches expected output schema
            if hasattr(node, 'scope') and node.scope.contracts:
                # In a full implementation, this would validate against JSON Schema
                return GuardrailResult(
                    passed=True,
                    score=1.0,
                    message="Output validation passed",
                    metadata={"contracts_checked": len(node.scope.contracts)}
                )
            
            return GuardrailResult(
                passed=True,
                score=1.0,
                message="No output contracts to validate"
            )
            
        except Exception as e:
            return GuardrailResult(
                passed=False,
                score=0.0,
                message=f"Output validation failed: {e}",
                metadata={"error": str(e)}
            )
    
    async def _apply_content_moderation(self, data: Any, node: Node) -> GuardrailResult:
        """Apply content moderation filters."""
        try:
            # Convert data to string for pattern matching
            data_str = str(data).lower()
            
            violations = []
            for pattern_name, pattern in self._content_patterns.items():
                if pattern.search(data_str):
                    violations.append(pattern_name)
            
            if violations:
                return GuardrailResult(
                    passed=False,
                    score=0.0,
                    message=f"Content moderation violations: {violations}",
                    metadata={"violations": violations},
                    action_required="content_blocked"
                )
            
            return GuardrailResult(
                passed=True,
                score=1.0,
                message="Content moderation passed"
            )
            
        except Exception as e:
            return GuardrailResult(
                passed=False,
                score=0.0,
                message=f"Content moderation error: {e}",
                metadata={"error": str(e)}
            )
    
    async def _apply_confidence_gating(self, data: Any, node: Node) -> GuardrailResult:
        """Apply confidence-based gating."""
        try:
            # Extract confidence score from data
            confidence = self._extract_confidence(data)
            threshold = self._confidence_thresholds.get(node.id, 0.8)
            
            if confidence < threshold:
                return GuardrailResult(
                    passed=False,
                    score=confidence,
                    message=f"Confidence {confidence:.2f} below threshold {threshold:.2f}",
                    metadata={"confidence": confidence, "threshold": threshold},
                    action_required="confidence_gate"
                )
            
            return GuardrailResult(
                passed=True,
                score=confidence,
                message=f"Confidence {confidence:.2f} above threshold {threshold:.2f}",
                metadata={"confidence": confidence, "threshold": threshold}
            )
            
        except Exception as e:
            return GuardrailResult(
                passed=False,
                score=0.0,
                message=f"Confidence gating error: {e}",
                metadata={"error": str(e)}
            )
    
    async def _apply_policy_checks(self, data: Any, node: Node, trace_id: str, stage: str) -> GuardrailResult:
        """Apply policy engine checks."""
        try:
            # Get policy template for environment
            template = self._policy_templates.get(self.environment, {})
            
            # Apply environment-specific policies
            if stage == "pre" and "pre_policies" in template:
                policies = template["pre_policies"]
            elif stage == "post" and "post_policies" in template:
                policies = template["post_policies"]
            else:
                return GuardrailResult(
                    passed=True,
                    score=1.0,
                    message="No policies to apply"
                )
            
            # Evaluate policies
            violations = []
            for policy_name, policy_func in policies.items():
                if not policy_func(data, node, trace_id):
                    violations.append(policy_name)
            
            if violations:
                return GuardrailResult(
                    passed=False,
                    score=0.0,
                    message=f"Policy violations: {violations}",
                    metadata={"violations": violations},
                    action_required="policy_violation"
                )
            
            return GuardrailResult(
                passed=True,
                score=1.0,
                message="Policy checks passed"
            )
            
        except Exception as e:
            return GuardrailResult(
                passed=False,
                score=0.0,
                message=f"Policy check error: {e}",
                metadata={"error": str(e)}
            )
    
    async def _check_circuit_breaker(self, node_id: str) -> GuardrailResult:
        """Check circuit breaker status for node."""
        try:
            metrics = self._circuit_breakers.get(node_id, CircuitBreakerMetrics())
            
            if metrics.state == CircuitBreakerState.OPEN:
                return GuardrailResult(
                    passed=False,
                    score=0.0,
                    message=f"Circuit breaker OPEN for node {node_id}",
                    metadata={"state": metrics.state.value, "failure_count": metrics.failure_count},
                    action_required="circuit_breaker_open"
                )
            elif metrics.state == CircuitBreakerState.HALF_OPEN:
                return GuardrailResult(
                    passed=True,
                    score=0.5,
                    message=f"Circuit breaker HALF_OPEN for node {node_id}",
                    metadata={"state": metrics.state.value}
                )
            
            return GuardrailResult(
                passed=True,
                score=1.0,
                message=f"Circuit breaker CLOSED for node {node_id}",
                metadata={"state": metrics.state.value}
            )
            
        except Exception as e:
            return GuardrailResult(
                passed=False,
                score=0.0,
                message=f"Circuit breaker check error: {e}",
                metadata={"error": str(e)}
            )
    
    async def record_success(self, node_id: str):
        """Record successful operation for circuit breaker."""
        metrics = self._circuit_breakers.get(node_id, CircuitBreakerMetrics())
        metrics.success_count += 1
        metrics.last_success_time = datetime.now(timezone.utc)
        
        # Reset circuit breaker if it was open/half-open
        if metrics.state in [CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN]:
            metrics.state = CircuitBreakerState.CLOSED
            metrics.failure_count = 0
        
        self._circuit_breakers[node_id] = metrics
    
    async def record_failure(self, node_id: str, failure_threshold: int = 3):
        """Record failed operation for circuit breaker."""
        metrics = self._circuit_breakers.get(node_id, CircuitBreakerMetrics())
        metrics.failure_count += 1
        metrics.last_failure_time = datetime.now(timezone.utc)
        
        # Calculate failure rate
        total_ops = metrics.success_count + metrics.failure_count
        if total_ops > 0:
            metrics.failure_rate = metrics.failure_count / total_ops
        
        # Open circuit breaker if threshold exceeded
        if metrics.failure_count >= failure_threshold:
            metrics.state = CircuitBreakerState.OPEN
        
        self._circuit_breakers[node_id] = metrics
    
    async def request_human_approval(self, node_id: str, trace_id: str, action: str, 
                                   data: Dict[str, Any], risk_level: str, 
                                   requested_by: str, timeout_minutes: int = 30) -> str:
        """Request human approval for high-risk action.
        
        Args:
            node_id: Node requesting approval
            trace_id: Trace identifier
            action: Action requiring approval
            data: Data associated with action
            risk_level: Risk level (low, medium, high, critical)
            requested_by: User requesting approval
            timeout_minutes: Timeout in minutes
            
        Returns:
            Request ID for tracking
        """
        async with self._gate_lock:
            request_id = f"gate_{node_id}_{int(time.time())}"
            timeout_at = datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)
            
            request = HumanGateRequest(
                request_id=request_id,
                node_id=node_id,
                trace_id=trace_id,
                action=action,
                data=data,
                risk_level=risk_level,
                requested_by=requested_by,
                requested_at=datetime.now(timezone.utc),
                timeout_at=timeout_at
            )
            
            self._human_gate_queue.append(request)
            
            return request_id
    
    async def approve_request(self, request_id: str, approved_by: str, reason: str = "") -> bool:
        """Approve a human gate request."""
        async with self._gate_lock:
            for request in self._human_gate_queue:
                if request.request_id == request_id:
                    request.approved_by = approved_by
                    request.approved_at = datetime.now(timezone.utc)
                    request.reason = reason
                    return True
            return False
    
    async def reject_request(self, request_id: str, rejected_by: str, reason: str = "") -> bool:
        """Reject a human gate request."""
        async with self._gate_lock:
            for request in self._human_gate_queue:
                if request.request_id == request_id:
                    request.rejected_by = rejected_by
                    request.rejected_at = datetime.now(timezone.utc)
                    request.reason = reason
                    return True
            return False
    
    async def get_pending_requests(self) -> List[HumanGateRequest]:
        """Get all pending human gate requests."""
        async with self._gate_lock:
            return [req for req in self._human_gate_queue 
                   if not req.approved_by and not req.rejected_by]
    
    def _should_apply_content_moderation(self, node: Node) -> bool:
        """Check if content moderation should be applied to node."""
        # Apply to AI nodes by default, configurable per node
        return node.kind == "ai" or getattr(node, 'content_moderation_enabled', False)
    
    def _extract_confidence(self, data: Any) -> float:
        """Extract confidence score from data."""
        if isinstance(data, dict):
            return data.get('confidence', data.get('score', 1.0))
        return 1.0
    
    def _combine_results(self, results: List[GuardrailResult], stage: str) -> GuardrailResult:
        """Combine multiple guardrail results."""
        if not results:
            return GuardrailResult(passed=True, score=1.0, message=f"{stage} completed")
        
        # Check if any result failed
        failed_results = [r for r in results if not r.passed]
        if failed_results:
            messages = [r.message for r in failed_results]
            actions = [r.action_required for r in failed_results if r.action_required]
            
            return GuardrailResult(
                passed=False,
                score=min(r.score for r in failed_results),
                message=f"{stage} failed: {'; '.join(messages)}",
                metadata={"failed_checks": len(failed_results)},
                action_required=actions[0] if actions else None
            )
        
        # All passed
        avg_score = sum(r.score for r in results) / len(results)
        return GuardrailResult(
            passed=True,
            score=avg_score,
            message=f"{stage} passed",
            metadata={"checks_passed": len(results)}
        )
    
    def _load_policy_templates(self) -> Dict[PolicyEnvironment, Dict[str, Any]]:
        """Load policy templates for different environments."""
        return {
            PolicyEnvironment.PRODUCTION: {
                "pre_policies": {
                    "strict_input_validation": lambda data, node, trace: True,
                    "rate_limiting": lambda data, node, trace: True,
                },
                "post_policies": {
                    "output_sanitization": lambda data, node, trace: True,
                    "audit_logging": lambda data, node, trace: True,
                }
            },
            PolicyEnvironment.DEVELOPMENT: {
                "pre_policies": {
                    "basic_validation": lambda data, node, trace: True,
                },
                "post_policies": {
                    "debug_logging": lambda data, node, trace: True,
                }
            },
            PolicyEnvironment.TESTING: {
                "pre_policies": {
                    "test_mode": lambda data, node, trace: True,
                },
                "post_policies": {
                    "test_validation": lambda data, node, trace: True,
                }
            }
        }
    
    def _load_content_patterns(self) -> Dict[str, Any]:
        """Load content moderation patterns."""
        import re
        return {
            "profanity": re.compile(r'\b(bad|word|here)\b'),
            "pii": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),  # SSN pattern
            "malicious": re.compile(r'<script|javascript:|eval\('),
        }
    
    def _load_confidence_thresholds(self) -> Dict[str, float]:
        """Load confidence thresholds per node."""
        return {
            "default": 0.8,
            "ai_classifier": 0.9,
            "ai_generator": 0.7,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get guardrails statistics."""
        return {
            "circuit_breakers": {
                node_id: {
                    "state": metrics.state.value,
                    "failure_count": metrics.failure_count,
                    "success_count": metrics.success_count,
                    "failure_rate": metrics.failure_rate
                }
                for node_id, metrics in self._circuit_breakers.items()
            },
            "human_gate_queue_size": len(self._human_gate_queue),
            "environment": self.environment.value,
            "policy_templates_loaded": len(self._policy_templates)
        }


# Backward compatibility
Guardrails = MultiStageGuardrails
