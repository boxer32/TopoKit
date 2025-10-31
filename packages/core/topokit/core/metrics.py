"""Token & drift metrics implementation in TopoKit."""

import time
import statistics
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
import json


@dataclass
class TokenUsage:
    """Token usage metrics."""
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CostMetrics:
    """Cost efficiency metrics."""
    total_cost_usd: float = 0.0
    cost_per_request: float = 0.0
    cost_per_token: float = 0.0
    cost_per_successful_request: float = 0.0
    baseline_cost_usd: float = 0.0
    cost_reduction_percent: float = 0.0
    optimization_savings_usd: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LatencyMetrics:
    """Latency and throughput metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    p50_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    throughput_rps: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConsistencyMetrics:
    """Consistency rate measurement metrics."""
    total_executions: int = 0
    consistent_executions: int = 0
    inconsistent_executions: int = 0
    consistency_rate: float = 0.0
    consistency_threshold: float = 0.95
    variance: float = 0.0
    standard_deviation: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class CostEfficiencyTracker:
    """Tracks cost efficiency and optimization."""
    
    def __init__(self, baseline_cost_usd: float = 0.0):
        """Initialize cost efficiency tracker."""
        self.baseline_cost_usd = baseline_cost_usd
        self._cost_history: deque = deque(maxlen=1000)
        self._token_history: deque = deque(maxlen=1000)
        self._request_history: deque = deque(maxlen=1000)
    
    def record_request(
        self,
        token_usage: TokenUsage,
        cost_usd: float,
        success: bool = True
    ) -> None:
        """Record a request's cost and token usage."""
        self._cost_history.append({
            "cost_usd": cost_usd,
            "timestamp": datetime.utcnow(),
            "success": success
        })
        self._token_history.append({
            "total_tokens": token_usage.total_tokens,
            "input_tokens": token_usage.input_tokens,
            "output_tokens": token_usage.output_tokens,
            "timestamp": datetime.utcnow()
        })
        self._request_history.append({
            "cost_usd": cost_usd,
            "success": success,
            "timestamp": datetime.utcnow()
        })
    
    def calculate_metrics(self, window_minutes: int = 60) -> CostMetrics:
        """Calculate cost efficiency metrics."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        
        # Filter recent records
        recent_costs = [
            r for r in self._cost_history
            if r["timestamp"] >= cutoff_time
        ]
        recent_tokens = [
            r for r in self._token_history
            if r["timestamp"] >= cutoff_time
        ]
        recent_requests = [
            r for r in self._request_history
            if r["timestamp"] >= cutoff_time
        ]
        
        if not recent_requests:
            return CostMetrics()
        
        # Calculate totals
        total_cost = sum(r["cost_usd"] for r in recent_costs)
        total_requests = len(recent_requests)
        successful_requests = sum(1 for r in recent_requests if r["success"])
        
        # Calculate averages
        cost_per_request = total_cost / total_requests if total_requests > 0 else 0.0
        cost_per_successful = (
            total_cost / successful_requests if successful_requests > 0 else 0.0
        )
        
        # Calculate token-based costs
        total_tokens = sum(r["total_tokens"] for r in recent_tokens)
        cost_per_token = total_cost / total_tokens if total_tokens > 0 else 0.0
        
        # Calculate optimization
        cost_reduction_percent = 0.0
        optimization_savings = 0.0
        if self.baseline_cost_usd > 0:
            avg_baseline_cost = self.baseline_cost_usd / total_requests if total_requests > 0 else self.baseline_cost_usd
            cost_reduction_percent = (
                ((avg_baseline_cost - cost_per_request) / avg_baseline_cost) * 100.0
                if avg_baseline_cost > 0 else 0.0
            )
            optimization_savings = (
                (avg_baseline_cost - cost_per_request) * total_requests
                if cost_per_request < avg_baseline_cost else 0.0
            )
        
        return CostMetrics(
            total_cost_usd=total_cost,
            cost_per_request=cost_per_request,
            cost_per_token=cost_per_token,
            cost_per_successful_request=cost_per_successful,
            baseline_cost_usd=self.baseline_cost_usd,
            cost_reduction_percent=max(0.0, cost_reduction_percent),
            optimization_savings_usd=max(0.0, optimization_savings)
        )
    
    def set_baseline(self, baseline_cost_usd: float) -> None:
        """Set baseline cost for optimization tracking."""
        self.baseline_cost_usd = baseline_cost_usd


class LatencyThroughputMonitor:
    """Monitors latency and throughput."""
    
    def __init__(self, window_size: int = 1000):
        """Initialize latency/throughput monitor."""
        self._response_times: deque = deque(maxlen=window_size)
        self._request_timestamps: deque = deque(maxlen=window_size)
        self._success_count = 0
        self._failure_count = 0
    
    def record_response(
        self,
        response_time_ms: float,
        success: bool = True
    ) -> None:
        """Record a response time."""
        self._response_times.append(response_time_ms)
        self._request_timestamps.append(datetime.utcnow())
        
        if success:
            self._success_count += 1
        else:
            self._failure_count += 1
    
    def calculate_metrics(self, window_seconds: int = 60) -> LatencyMetrics:
        """Calculate latency and throughput metrics."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=window_seconds)
        
        # Filter recent response times
        recent_times = [
            t for t, ts in zip(self._response_times, self._request_timestamps)
            if ts >= cutoff_time
        ]
        
        if not recent_times:
            return LatencyMetrics()
        
        # Calculate statistics
        sorted_times = sorted(recent_times)
        total_requests = len(recent_times)
        
        avg_response_time = statistics.mean(recent_times)
        p50_response_time = sorted_times[int(len(sorted_times) * 0.50)] if sorted_times else 0.0
        p95_response_time = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0.0
        p99_response_time = sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0.0
        min_response_time = min(recent_times) if recent_times else 0.0
        max_response_time = max(recent_times) if recent_times else 0.0
        
        # Calculate throughput (requests per second)
        time_span = window_seconds
        throughput_rps = total_requests / time_span if time_span > 0 else 0.0
        
        return LatencyMetrics(
            total_requests=total_requests,
            successful_requests=self._success_count,
            failed_requests=self._failure_count,
            avg_response_time_ms=avg_response_time,
            p50_response_time_ms=p50_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            min_response_time_ms=min_response_time,
            max_response_time_ms=max_response_time,
            throughput_rps=throughput_rps
        )
    
    def reset(self) -> None:
        """Reset metrics."""
        self._response_times.clear()
        self._request_timestamps.clear()
        self._success_count = 0
        self._failure_count = 0


class ConsistencyRateMeasurer:
    """Measures consistency rate across executions."""
    
    def __init__(self, consistency_threshold: float = 0.95):
        """Initialize consistency measurer."""
        self.consistency_threshold = consistency_threshold
        self._execution_outputs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._execution_history: List[Dict[str, Any]] = []
    
    def record_execution(
        self,
        execution_id: str,
        output: Dict[str, Any],
        input_hash: Optional[str] = None
    ) -> None:
        """Record an execution output."""
        key = input_hash or execution_id
        self._execution_outputs[key].append({
            "execution_id": execution_id,
            "output": output,
            "timestamp": datetime.utcnow()
        })
        
        self._execution_history.append({
            "execution_id": execution_id,
            "input_hash": input_hash,
            "timestamp": datetime.utcnow()
        })
    
    def calculate_metrics(self, window_minutes: int = 60) -> ConsistencyMetrics:
        """Calculate consistency rate metrics."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        
        # Filter recent executions
        recent_executions = [
            h for h in self._execution_history
            if h["timestamp"] >= cutoff_time
        ]
        
        if not recent_executions:
            return ConsistencyMetrics()
        
        total_executions = len(recent_executions)
        consistent_executions = 0
        inconsistent_executions = 0
        output_values = []
        
        # Group by input hash and check consistency
        for key, outputs in self._execution_outputs.items():
            # Filter recent outputs
            recent_outputs = [
                o for o in outputs
                if o["timestamp"] >= cutoff_time
            ]
            
            if len(recent_outputs) < 2:
                continue
            
            # Compare outputs
            first_output = json.dumps(recent_outputs[0]["output"], sort_keys=True)
            all_consistent = all(
                json.dumps(o["output"], sort_keys=True) == first_output
                for o in recent_outputs[1:]
            )
            
            if all_consistent:
                consistent_executions += len(recent_outputs)
            else:
                inconsistent_executions += len(recent_outputs)
            
            # Track output variance (simplified)
            output_hash = hash(first_output)
            output_values.append(output_hash)
        
        # Calculate consistency rate
        total_compared = consistent_executions + inconsistent_executions
        consistency_rate = (
            consistent_executions / total_compared if total_compared > 0 else 1.0
        )
        
        # Calculate variance
        variance = 0.0
        std_dev = 0.0
        if len(output_values) > 1:
            variance = statistics.variance(output_values) if output_values else 0.0
            std_dev = statistics.stdev(output_values) if len(output_values) > 1 else 0.0
        
        return ConsistencyMetrics(
            total_executions=total_executions,
            consistent_executions=consistent_executions,
            inconsistent_executions=inconsistent_executions,
            consistency_rate=consistency_rate,
            consistency_threshold=self.consistency_threshold,
            variance=variance,
            standard_deviation=std_dev
        )
    
    def is_consistent(
        self,
        current_output: Dict[str, Any],
        previous_outputs: List[Dict[str, Any]]
    ) -> bool:
        """Check if current output is consistent with previous outputs."""
        if not previous_outputs:
            return True
        
        current_str = json.dumps(current_output, sort_keys=True)
        return all(
            json.dumps(prev, sort_keys=True) == current_str
            for prev in previous_outputs
        )


class MetricsCollector:
    """Comprehensive metrics collector for token, cost, latency, and consistency."""
    
    def __init__(
        self,
        cost_tracker: Optional[CostEfficiencyTracker] = None,
        latency_monitor: Optional[LatencyThroughputMonitor] = None,
        consistency_measurer: Optional[ConsistencyRateMeasurer] = None
    ):
        """Initialize metrics collector."""
        self.cost_tracker = cost_tracker or CostEfficiencyTracker()
        self.latency_monitor = latency_monitor or LatencyThroughputMonitor()
        self.consistency_measurer = consistency_measurer or ConsistencyRateMeasurer()
    
    def record_execution(
        self,
        token_usage: TokenUsage,
        cost_usd: float,
        response_time_ms: float,
        success: bool,
        output: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None
    ) -> None:
        """Record a complete execution with all metrics."""
        self.cost_tracker.record_request(token_usage, cost_usd, success)
        self.latency_monitor.record_response(response_time_ms, success)
        
        if output and execution_id:
            input_hash = hashlib.md5(
                json.dumps(token_usage.__dict__, sort_keys=True).encode()
            ).hexdigest()
            self.consistency_measurer.record_execution(execution_id, output, input_hash)
    
    def get_all_metrics(
        self,
        window_minutes: int = 60
    ) -> Dict[str, Any]:
        """Get all collected metrics."""
        cost_metrics = self.cost_tracker.calculate_metrics(window_minutes)
        latency_metrics = self.latency_monitor.calculate_metrics(window_minutes * 60)
        consistency_metrics = self.consistency_measurer.calculate_metrics(window_minutes)
        
        return {
            "cost": {
                "total_cost_usd": cost_metrics.total_cost_usd,
                "cost_per_request": cost_metrics.cost_per_request,
                "cost_per_token": cost_metrics.cost_per_token,
                "cost_reduction_percent": cost_metrics.cost_reduction_percent,
                "optimization_savings_usd": cost_metrics.optimization_savings_usd
            },
            "latency": {
                "avg_response_time_ms": latency_metrics.avg_response_time_ms,
                "p95_response_time_ms": latency_metrics.p95_response_time_ms,
                "p99_response_time_ms": latency_metrics.p99_response_time_ms,
                "throughput_rps": latency_metrics.throughput_rps
            },
            "consistency": {
                "consistency_rate": consistency_metrics.consistency_rate,
                "total_executions": consistency_metrics.total_executions,
                "consistent_executions": consistency_metrics.consistent_executions,
                "variance": consistency_metrics.variance
            },
            "timestamp": datetime.utcnow().isoformat()
        }

