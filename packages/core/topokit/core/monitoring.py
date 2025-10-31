"""Performance monitoring system for TopoKit with drift detection, trace viewing, and log analysis."""

import asyncio
import statistics
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import json

from pydantic import BaseModel, Field
from .logging import get_logger
from .alerting import AlertManager, get_alert_manager, AlertSeverity, AlertThreshold


logger = get_logger(__name__)


class MetricType(str, Enum):
    """Metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Metric:
    """Performance metric."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None


@dataclass
class TraceSpan:
    """Trace span for distributed tracing."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[float]
    status: str  # 'success', 'error', 'timeout'
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class Trace:
    """Complete trace with spans."""
    trace_id: str
    spans: List[TraceSpan]
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[float]
    root_span: Optional[TraceSpan] = None


@dataclass
class SessionReplay:
    """Session replay data for debugging."""
    session_id: str
    topology_id: str
    execution_steps: List[Dict[str, Any]]
    start_time: datetime
    end_time: Optional[datetime]
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DriftResult:
    """Drift detection result."""
    metric_name: str
    baseline_value: float
    current_value: float
    drift_percentage: float
    is_anomaly: bool
    statistical_score: float
    detected_at: datetime


class PerformanceMetrics(BaseModel):
    """Performance metrics model."""
    request_count: int = Field(default=0, description="Total request count")
    success_count: int = Field(default=0, description="Successful request count")
    error_count: int = Field(default=0, description="Error count")
    avg_response_time_ms: float = Field(default=0.0, description="Average response time in ms")
    p50_response_time_ms: float = Field(default=0.0, description="50th percentile response time")
    p95_response_time_ms: float = Field(default=0.0, description="95th percentile response time")
    p99_response_time_ms: float = Field(default=0.0, description="99th percentile response time")
    throughput_rps: float = Field(default=0.0, description="Requests per second")
    cpu_usage_percent: float = Field(default=0.0, description="CPU usage percentage")
    memory_usage_percent: float = Field(default=0.0, description="Memory usage percentage")
    token_usage: int = Field(default=0, description="Total token usage")
    cost_usd: float = Field(default=0.0, description="Total cost in USD")
    schema_pass_rate: float = Field(default=0.0, description="Schema pass rate (0.0-1.0)")
    error_rate: float = Field(default=0.0, description="Error rate (0.0-1.0)")

    def update_from_values(self, response_times: List[float], success_count: int, error_count: int) -> None:
        """Update metrics from response time values."""
        if response_times:
            self.avg_response_time_ms = statistics.mean(response_times)
            sorted_times = sorted(response_times)
            self.p50_response_time_ms = statistics.median(sorted_times)
            if len(sorted_times) > 0:
                self.p95_response_time_ms = sorted_times[int(len(sorted_times) * 0.95)]
                self.p99_response_time_ms = sorted_times[int(len(sorted_times) * 0.99)]
        
        self.request_count = success_count + error_count
        self.success_count = success_count
        self.error_count = error_count
        
        if self.request_count > 0:
            self.error_rate = error_count / self.request_count
            self.schema_pass_rate = success_count / self.request_count


class MetricCollector:
    """Metric collector for performance monitoring."""

    def __init__(self):
        """Initialize metric collector."""
        self.metrics: Dict[str, List[Metric]] = defaultdict(list)
        self.baselines: Dict[str, float] = {}
        self.response_times: List[Tuple[datetime, float]] = []

    def record_metric(self, metric: Metric) -> None:
        """Record a metric."""
        self.metrics[metric.name].append(metric)
        
        # Keep only recent metrics (last hour)
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self.metrics[metric.name] = [
            m for m in self.metrics[metric.name]
            if m.timestamp > cutoff
        ]

    def record_response_time(self, response_time_ms: float) -> None:
        """Record response time."""
        self.response_times.append((datetime.utcnow(), response_time_ms))
        
        # Keep only recent response times (last hour)
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self.response_times = [
            (ts, val) for ts, val in self.response_times
            if ts > cutoff
        ]

    def get_recent_metrics(self, metric_name: str, minutes: int = 60) -> List[Metric]:
        """Get recent metrics for a metric name."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return [
            m for m in self.metrics.get(metric_name, [])
            if m.timestamp > cutoff
        ]

    def calculate_baseline(self, metric_name: str, window_minutes: int = 60) -> Optional[float]:
        """Calculate baseline value for a metric."""
        recent_metrics = self.get_recent_metrics(metric_name, window_minutes)
        if not recent_metrics:
            return None
        
        values = [m.value for m in recent_metrics]
        baseline = statistics.mean(values)
        self.baselines[metric_name] = baseline
        return baseline

    def get_baseline(self, metric_name: str) -> Optional[float]:
        """Get baseline value for a metric."""
        return self.baselines.get(metric_name)


class TraceCollector:
    """Trace collector for distributed tracing."""

    def __init__(self):
        """Initialize trace collector."""
        self.traces: Dict[str, Trace] = {}
        self.spans_by_trace: Dict[str, List[TraceSpan]] = defaultdict(list)

    def record_span(self, span: TraceSpan) -> None:
        """Record a trace span."""
        self.spans_by_trace[span.trace_id].append(span)
        
        # Update or create trace
        if span.trace_id not in self.traces:
            self.traces[span.trace_id] = Trace(
                trace_id=span.trace_id,
                spans=[],
                start_time=span.start_time,
                end_time=None,
                duration_ms=None,
            )
        
        trace = self.traces[span.trace_id]
        trace.spans.append(span)
        
        # Update trace timing
        if span.end_time:
            if not trace.end_time or span.end_time > trace.end_time:
                trace.end_time = span.end_time
            if span.duration_ms:
                if trace.duration_ms:
                    trace.duration_ms = max(trace.duration_ms, span.duration_ms)
                else:
                    trace.duration_ms = span.duration_ms
        
        # Set root span
        if not span.parent_span_id and not trace.root_span:
            trace.root_span = span

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get trace by ID."""
        return self.traces.get(trace_id)

    def get_recent_traces(self, minutes: int = 60) -> List[Trace]:
        """Get recent traces."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return [
            trace for trace in self.traces.values()
            if trace.start_time > cutoff
        ]


class DriftDetector:
    """Drift detection with statistical anomaly detection."""

    def __init__(self, threshold_percentage: float = 10.0, z_score_threshold: float = 3.0):
        """Initialize drift detector."""
        self.threshold_percentage = threshold_percentage
        self.z_score_threshold = z_score_threshold
        self.baselines: Dict[str, Tuple[float, float]] = {}  # (mean, std_dev)

    def calculate_statistics(self, values: List[float]) -> Tuple[float, float]:
        """Calculate mean and standard deviation."""
        if not values:
            return 0.0, 0.0
        
        mean = statistics.mean(values)
        if len(values) > 1:
            std_dev = statistics.stdev(values)
        else:
            std_dev = 0.0
        
        return mean, std_dev

    def update_baseline(self, metric_name: str, values: List[float]) -> None:
        """Update baseline statistics for a metric."""
        if values:
            mean, std_dev = self.calculate_statistics(values)
            self.baselines[metric_name] = (mean, std_dev)
            logger.info(f"Updated baseline for {metric_name}: mean={mean:.2f}, std_dev={std_dev:.2f}")

    def detect_drift(
        self,
        metric_name: str,
        current_value: float,
        recent_values: Optional[List[float]] = None,
    ) -> Optional[DriftResult]:
        """Detect drift for a metric."""
        if metric_name not in self.baselines:
            return None
        
        baseline_mean, baseline_std_dev = self.baselines[metric_name]
        
        # Calculate drift percentage
        if baseline_mean != 0:
            drift_percentage = abs((current_value - baseline_mean) / baseline_mean) * 100
        else:
            drift_percentage = abs(current_value) * 100
        
        # Calculate Z-score for statistical anomaly detection
        if baseline_std_dev > 0:
            z_score = abs((current_value - baseline_mean) / baseline_std_dev)
        else:
            z_score = 0.0
        
        # Check if drift exceeds threshold
        is_anomaly = (
            drift_percentage > self.threshold_percentage or
            z_score > self.z_score_threshold
        )
        
        return DriftResult(
            metric_name=metric_name,
            baseline_value=baseline_mean,
            current_value=current_value,
            drift_percentage=drift_percentage,
            is_anomaly=is_anomaly,
            statistical_score=z_score,
            detected_at=datetime.utcnow(),
        )


class PerformanceMonitor:
    """Performance monitoring system."""

    def __init__(self, alert_manager: Optional[AlertManager] = None):
        """Initialize performance monitor."""
        self.metric_collector = MetricCollector()
        self.trace_collector = TraceCollector()
        self.drift_detector = DriftDetector()
        self.alert_manager = alert_manager or get_alert_manager()
        self.session_replays: Dict[str, SessionReplay] = {}
        self.metrics_history: Dict[str, List[PerformanceMetrics]] = defaultdict(list)

    def record_execution(
        self,
        session_id: str,
        node_id: str,
        response_time_ms: float,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Record execution metrics."""
        self.metric_collector.record_response_time(response_time_ms)
        
        # Record success/error metrics
        metric_type = MetricType.GAUGE
        self.metric_collector.record_metric(Metric(
            name=f"node.{node_id}.response_time",
            value=response_time_ms,
            metric_type=metric_type,
            timestamp=datetime.utcnow(),
            labels={"node_id": node_id, "session_id": session_id},
            unit="ms",
        ))
        
        self.metric_collector.record_metric(Metric(
            name=f"node.{node_id}.success",
            value=1.0 if success else 0.0,
            metric_type=MetricType.COUNTER,
            timestamp=datetime.utcnow(),
            labels={"node_id": node_id, "session_id": session_id},
        ))

    def record_span(self, span: TraceSpan) -> None:
        """Record a trace span."""
        self.trace_collector.record_span(span)

    async def evaluate_metrics(self, deployment_id: Optional[str] = None) -> PerformanceMetrics:
        """Evaluate and aggregate performance metrics."""
        recent_response_times = [
            val for _, val in self.metric_collector.response_times
        ]
        
        # Calculate success/error counts from recent metrics
        success_metrics = self.metric_collector.get_recent_metrics("success", minutes=60)
        error_metrics = self.metric_collector.get_recent_metrics("error", minutes=60)
        
        success_count = len([m for m in success_metrics if m.value > 0])
        error_count = len([m for m in error_metrics if m.value > 0])
        
        # If no explicit success/error metrics, calculate from response times
        if not success_metrics and not error_metrics:
            # Assume recent executions were successful if we have response times
            success_count = len(recent_response_times)
            error_count = 0
        
        metrics = PerformanceMetrics()
        metrics.update_from_values(recent_response_times, success_count, error_count)
        
        # Store metrics history
        self.metrics_history["default"].append(metrics)
        
        # Keep only recent history (last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        # We'll store metrics with timestamps in a real implementation
        
        return metrics

    async def detect_drift(self, metric_name: str, current_value: float) -> Optional[DriftResult]:
        """Detect drift for a metric."""
        # Get recent values for baseline update
        recent_metrics = self.metric_collector.get_recent_metrics(metric_name, minutes=60)
        recent_values = [m.value for m in recent_metrics]
        
        # Update baseline if we have enough data
        if len(recent_values) >= 10:
            self.drift_detector.update_baseline(metric_name, recent_values)
        
        # Detect drift
        drift_result = self.drift_detector.detect_drift(metric_name, current_value, recent_values)
        
        if drift_result and drift_result.is_anomaly:
            logger.warning(
                f"Drift detected for {metric_name}: "
                f"{drift_result.drift_percentage:.2f}% drift "
                f"(baseline={drift_result.baseline_value:.2f}, current={drift_result.current_value:.2f})"
            )
            
            # Trigger alert
            await self.alert_manager.evaluate_threshold(
                metric_name=f"{metric_name}.drift",
                value=drift_result.drift_percentage,
                deployment_id=None,
            )
        
        return drift_result

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get trace by ID."""
        return self.trace_collector.get_trace(trace_id)

    def get_recent_traces(self, minutes: int = 60) -> List[Trace]:
        """Get recent traces."""
        return self.trace_collector.get_recent_traces(minutes)

    def create_session_replay(
        self,
        session_id: str,
        topology_id: str,
        input_data: Dict[str, Any],
    ) -> SessionReplay:
        """Create a session replay for debugging."""
        replay = SessionReplay(
            session_id=session_id,
            topology_id=topology_id,
            execution_steps=[],
            start_time=datetime.utcnow(),
            end_time=None,
            input_data=input_data,
            output_data=None,
            metadata={},
        )
        self.session_replays[session_id] = replay
        return replay

    def get_session_replay(self, session_id: str) -> Optional[SessionReplay]:
        """Get session replay by ID."""
        return self.session_replays.get(session_id)

    def add_execution_step(self, session_id: str, step: Dict[str, Any]) -> None:
        """Add execution step to session replay."""
        replay = self.session_replays.get(session_id)
        if replay:
            replay.execution_steps.append(step)

    def finalize_session_replay(self, session_id: str, output_data: Dict[str, Any]) -> None:
        """Finalize session replay."""
        replay = self.session_replays.get(session_id)
        if replay:
            replay.end_time = datetime.utcnow()
            replay.output_data = output_data


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

