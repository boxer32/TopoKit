"""Unit tests for Adapter Framework."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from topokit.adapters.framework import (
    BaseAdapter,
    AdapterConfig,
    AdapterType,
    AdapterHealth,
    AdapterRegistry,
    register_adapter,
    get_adapter,
    ExecutionContext,
    ExecutionResult,
)
from topokit.types.topology import Node, NodeKind, ExecutionProfile


class MockAdapter(BaseAdapter):
    """Mock adapter for testing."""
    
    @property
    def adapter_type(self) -> AdapterType:
        return AdapterType.LLM_PROVIDER
    
    @property
    def provider(self) -> str:
        return "mock"
    
    async def _initialize_impl(self) -> None:
        self._client = Mock()
    
    async def _execute_impl(self, context: ExecutionContext) -> ExecutionResult:
        return ExecutionResult(
            success=True,
            output_data={"result": "mock output"},
            metadata={"tokens": 100},
        )
    
    async def _health_check_impl(self) -> AdapterHealth:
        return AdapterHealth(
            healthy=True,
            last_check=None,
            details={},
        )


class TestAdapterConfig:
    """Test cases for AdapterConfig."""
    
    def test_adapter_config_creation(self):
        """Test creating adapter configuration."""
        config = AdapterConfig(
            adapter_id="test-adapter",
            adapter_type=AdapterType.LLM_PROVIDER,
            provider="test-provider",
        )
        
        assert config.adapter_id == "test-adapter"
        assert config.adapter_type == AdapterType.LLM_PROVIDER
        assert config.provider == "test-provider"
        assert config.enabled is True


class TestBaseAdapter:
    """Test cases for BaseAdapter."""
    
    @pytest.fixture
    def adapter_config(self):
        """Create adapter configuration."""
        return AdapterConfig(
            adapter_id="test-adapter",
            adapter_type=AdapterType.LLM_PROVIDER,
            provider="mock",
        )
    
    @pytest.fixture
    def adapter(self, adapter_config):
        """Create mock adapter instance."""
        return MockAdapter(adapter_config)
    
    @pytest.mark.asyncio
    async def test_adapter_initialization(self, adapter):
        """Test adapter initialization."""
        await adapter.initialize()
        
        assert adapter._initialized is True
    
    @pytest.mark.asyncio
    async def test_adapter_execute(self, adapter):
        """Test adapter execution."""
        await adapter.initialize()
        
        node = Node(id="test-node", kind=NodeKind.AI)
        context = ExecutionContext(
            node=node,
            session_id="test-session",
            trace_id="test-trace",
            input_data={"query": "test"},
            execution_profile=ExecutionProfile(),
        )
        
        result = await adapter.execute(context)
        
        assert result.success is True
        assert result.output_data is not None
    
    @pytest.mark.asyncio
    async def test_adapter_health_check(self, adapter):
        """Test adapter health check."""
        await adapter.initialize()
        
        health = await adapter.health_check()
        
        assert health is not None
        assert health.healthy is True


class TestAdapterRegistry:
    """Test cases for AdapterRegistry."""
    
    @pytest.fixture
    def registry(self):
        """Create adapter registry."""
        return AdapterRegistry()
    
    def test_register_adapter(self, registry):
        """Test registering an adapter."""
        config = AdapterConfig(
            adapter_id="test-adapter",
            adapter_type=AdapterType.LLM_PROVIDER,
            provider="mock",
        )
        adapter = MockAdapter(config)
        
        registry.register("mock", adapter)
        
        assert "mock" in registry._adapters
    
    def test_get_adapter(self, registry):
        """Test getting an adapter."""
        config = AdapterConfig(
            adapter_id="test-adapter",
            adapter_type=AdapterType.LLM_PROVIDER,
            provider="mock",
        )
        adapter = MockAdapter(config)
        
        registry.register("mock", adapter)
        
        retrieved = registry.get("mock")
        assert retrieved == adapter
    
    def test_get_nonexistent_adapter(self, registry):
        """Test getting non-existent adapter."""
        retrieved = registry.get("nonexistent")
        assert retrieved is None


class TestRegisterAdapterDecorator:
    """Test cases for register_adapter decorator."""
    
    def test_register_adapter_decorator(self):
        """Test register_adapter decorator."""
        @register_adapter("test-provider")
        class TestAdapter(BaseAdapter):
            @property
            def adapter_type(self):
                return AdapterType.LLM_PROVIDER
            
            @property
            def provider(self):
                return "test-provider"
            
            async def _initialize_impl(self):
                pass
            
            async def _execute_impl(self, context):
                return ExecutionResult(success=True, output_data={})
            
            async def _health_check_impl(self):
                return AdapterHealth(healthy=True, last_check=None, details={})
        
        # Verify adapter can be retrieved
        registry = get_adapter_registry()
        adapter_class = registry.get_adapter_class("test-provider")
        assert adapter_class is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

