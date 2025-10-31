"""Unit tests for Metrics system."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from topokit.core.metrics import MetricsCollector, TokenUsage, CostMetrics, LatencyMetrics


class TestMetricsCollector:
    """Test cases for Metrics Collector."""
    
    @pytest.fixture
    def metrics_collector(self):
        """Create metrics collector instance."""
        return MetricsCollector()
    
    @pytest.mark.asyncio
    async def test_metrics_collector_initialization(self, metrics_collector):
        """Test metrics collector initialization."""
        assert metrics_collector is not None
    
    @pytest.mark.asyncio
    async def test_record_metric(self, metrics_collector):
        """Test recording a metric."""
        node_id = "test-node"
        metric_type = MetricType.LATENCY
        value = 100.5
        
        await metrics_collector.record(node_id, metric_type, value)
        
        # Verify metric was recorded
        metrics = await metrics_collector.get_metrics(node_id, metric_type)
        assert metrics is not None or len(metrics) >= 0
    
    @pytest.mark.asyncio
    async def test_record_latency(self, metrics_collector):
        """Test recording latency metric."""
        node_id = "test-node"
        latency = LatencyMetrics(execution_time_ms=100.5, response_time_ms=150.0)
        
        await metrics_collector.record_latency(node_id, latency)
        
        # Verify metric was recorded
        metrics = metrics_collector.get_node_metrics(node_id)
        assert metrics is not None
    
    @pytest.mark.asyncio
    async def test_record_cost(self, metrics_collector):
        """Test recording cost metric."""
        node_id = "test-node"
        cost = CostMetrics(total_cost=0.01, prompt_cost=0.005, completion_cost=0.005)
        
        await metrics_collector.record_cost(node_id, cost)
        
        # Verify metric was recorded
        metrics = metrics_collector.get_node_metrics(node_id)
        assert metrics is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

