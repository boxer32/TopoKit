"""Unit tests for Monitoring system."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from topokit.core.monitoring import (
    PerformanceMonitor,
    TraceSpan,
    TraceContext,
    get_performance_monitor,
)


class TestPerformanceMonitor:
    """Test cases for Performance Monitor."""
    
    @pytest.fixture
    def monitor(self):
        """Create performance monitor instance."""
        return PerformanceMonitor()
    
    @pytest.mark.asyncio
    async def test_monitor_initialization(self, monitor):
        """Test performance monitor initialization."""
        assert monitor is not None
    
    @pytest.mark.asyncio
    async def test_record_metric(self, monitor):
        """Test recording a metric."""
        node_id = "test-node"
        metric_name = "latency"
        value = 100.5
        
        await monitor.record_metric(node_id, metric_name, value)
        
        # Verify metric was recorded
        metrics = await monitor.get_metrics(node_id)
        assert metrics is not None
    
    @pytest.mark.asyncio
    async def test_create_trace_span(self, monitor):
        """Test creating a trace span."""
        span_name = "test-span"
        node_id = "test-node"
        
        span = await monitor.start_span(span_name, node_id)
        
        assert span is not None
        assert isinstance(span, TraceSpan)
        assert span.name == span_name
    
    @pytest.mark.asyncio
    async def test_end_trace_span(self, monitor):
        """Test ending a trace span."""
        span = await monitor.start_span("test-span", "test-node")
        
        await monitor.end_span(span)
        
        assert span.end_time is not None
    
    @pytest.mark.asyncio
    async def test_get_trace(self, monitor):
        """Test getting a trace."""
        trace_id = "test-trace"
        context = TraceContext(trace_id=trace_id)
        
        span = await monitor.start_span("test-span", "test-node", context=context)
        await monitor.end_span(span)
        
        trace = await monitor.get_trace(trace_id)
        
        assert trace is not None
        assert len(trace.spans) > 0


class TestTraceSpan:
    """Test cases for Trace Span."""
    
    def test_trace_span_creation(self):
        """Test creating a trace span."""
        span = TraceSpan(
            id="span-1",
            name="test-span",
            start_time=datetime.now(),
        )
        
        assert span.id == "span-1"
        assert span.name == "test-span"
        assert span.start_time is not None
    
    def test_trace_span_duration(self):
        """Test trace span duration calculation."""
        start_time = datetime.now()
        end_time = start_time
        
        span = TraceSpan(
            id="span-1",
            name="test-span",
            start_time=start_time,
            end_time=end_time,
        )
        
        # Duration should be calculated
        assert span.duration_ms is not None or span.duration_ms == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

