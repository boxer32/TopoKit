"""
Module: adapter_framework
Purpose: Base adapter framework with plugin system for LLM providers, vector databases, and graph databases
Inputs: Adapter configuration, node execution context, input data
Outputs: Execution results, health status, configuration validation
Dependencies: topokit.types.topology, topokit.core.logging
Failure Modes: Adapter initialization failure → fallback to default, health check failure → circuit breaker
Trace: page:adapters, build:20250127, spec-id:T101
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing_extensions import Protocol

from ..types.topology import Node, ExecutionProfile
from ..core.logging import get_logger


logger = get_logger(__name__)


class AdapterType(str, Enum):
    """Types of adapters."""
    LLM_PROVIDER = "llm_provider"
    VECTOR_DATABASE = "vector_database"
    GRAPH_DATABASE = "graph_database"
    CUSTOM = "custom"


@dataclass
class AdapterConfig:
    """Adapter configuration."""
    adapter_id: str
    adapter_type: AdapterType
    provider: str  # e.g., "openai", "langchain", "pinecone"
    version: str = "1.0.0"
    enabled: bool = True
    timeout_ms: int = 30000
    max_retries: int = 3
    retry_delay_ms: int = 1000
    connection_params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterHealth:
    """Adapter health status."""
    adapter_id: str
    healthy: bool
    last_check: datetime
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """Context for adapter execution."""
    node: Node
    session_id: str
    trace_id: str
    input_data: Any
    dependencies: Dict[str, Any] = field(default_factory=dict)
    execution_profile: Optional[ExecutionProfile] = None


@dataclass
class ExecutionResult:
    """Result from adapter execution."""
    success: bool
    output_data: Any
    confidence: float = 1.0
    latency_ms: float = 0.0
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class BaseAdapter(ABC):
    """
    Base adapter interface for LLM providers, vector databases, and graph databases.
    
    All adapters must implement this interface to integrate with TopoKit orchestrator.
    """
    
    def __init__(self, config: AdapterConfig):
        """Initialize adapter.
        
        Args:
            config: Adapter configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._initialized = False
        self._health_status: Optional[AdapterHealth] = None
    
    @property
    @abstractmethod
    def adapter_type(self) -> AdapterType:
        """Get adapter type."""
        pass
    
    @property
    @abstractmethod
    def provider(self) -> str:
        """Get provider name."""
        pass
    
    async def initialize(self) -> None:
        """Initialize adapter connection/resources."""
        if self._initialized:
            return
        
        try:
            await self._initialize_impl()
            self._initialized = True
            self.logger.info(f"Adapter {self.config.adapter_id} initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize adapter {self.config.adapter_id}: {e}")
            raise
    
    @abstractmethod
    async def _initialize_impl(self) -> None:
        """Implementation-specific initialization."""
        pass
    
    async def execute(
        self,
        context: ExecutionContext,
    ) -> ExecutionResult:
        """Execute adapter operation.
        
        Args:
            context: Execution context with node, session, input data
            
        Returns:
            Execution result with output data, confidence, metrics
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Use execution profile from context or node
            execution_profile = (
                context.execution_profile or context.node.execution_profile
            )
            
            result = await self._execute_impl(context, execution_profile)
            
            # Calculate latency
            end_time = datetime.now(timezone.utc)
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            result.latency_ms = latency_ms
            
            self.logger.debug(
                f"Adapter {self.config.adapter_id} executed in {latency_ms:.2f}ms"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Adapter {self.config.adapter_id} execution failed: {e}")
            
            end_time = datetime.now(timezone.utc)
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            return ExecutionResult(
                success=False,
                output_data=None,
                confidence=0.0,
                latency_ms=latency_ms,
                error=str(e),
            )
    
    @abstractmethod
    async def _execute_impl(
        self,
        context: ExecutionContext,
        execution_profile: ExecutionProfile,
    ) -> ExecutionResult:
        """Implementation-specific execution logic."""
        pass
    
    async def health_check(self) -> AdapterHealth:
        """Check adapter health.
        
        Returns:
            Health status with latency and error information
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            healthy = await self._health_check_impl()
            
            end_time = datetime.now(timezone.utc)
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            health = AdapterHealth(
                adapter_id=self.config.adapter_id,
                healthy=healthy,
                last_check=end_time,
                latency_ms=latency_ms,
            )
            
            self._health_status = health
            return health
            
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            health = AdapterHealth(
                adapter_id=self.config.adapter_id,
                healthy=False,
                last_check=end_time,
                latency_ms=latency_ms,
                error_message=str(e),
            )
            
            self._health_status = health
            return health
    
    @abstractmethod
    async def _health_check_impl(self) -> bool:
        """Implementation-specific health check."""
        pass
    
    async def cleanup(self) -> None:
        """Cleanup adapter resources."""
        if not self._initialized:
            return
        
        try:
            await self._cleanup_impl()
            self._initialized = False
            self.logger.info(f"Adapter {self.config.adapter_id} cleaned up")
        except Exception as e:
            self.logger.error(f"Error cleaning up adapter {self.config.adapter_id}: {e}")
    
    async def _cleanup_impl(self) -> None:
        """Implementation-specific cleanup."""
        pass
    
    def get_health_status(self) -> Optional[AdapterHealth]:
        """Get cached health status."""
        return self._health_status


# Adapter Registry for Plugin System
class AdapterRegistry:
    """Registry for managing adapter instances and discovery."""
    
    def __init__(self):
        """Initialize adapter registry."""
        self._adapters: Dict[str, Type[BaseAdapter]] = {}
        self._instances: Dict[str, BaseAdapter] = {}
        self._logger = logging.getLogger(__name__)
    
    def register(
        self,
        adapter_id: str,
        adapter_class: Type[BaseAdapter],
        overwrite: bool = False,
    ) -> None:
        """Register an adapter class.
        
        Args:
            adapter_id: Unique adapter identifier
            adapter_class: Adapter class implementing BaseAdapter
            overwrite: Whether to overwrite existing registration
        """
        if adapter_id in self._adapters and not overwrite:
            raise ValueError(f"Adapter {adapter_id} already registered")
        
        self._adapters[adapter_id] = adapter_class
        self._logger.info(f"Registered adapter: {adapter_id} ({adapter_class.__name__})")
    
    def create_adapter(self, config: AdapterConfig) -> BaseAdapter:
        """Create an adapter instance.
        
        Args:
            config: Adapter configuration
            
        Returns:
            Adapter instance
            
        Raises:
            ValueError: If adapter class not found
        """
        if config.adapter_id in self._instances:
            return self._instances[config.adapter_id]
        
        adapter_class = self._adapters.get(config.adapter_id)
        if not adapter_class:
            # Try to find by provider name
            adapter_class = next(
                (
                    cls for cls in self._adapters.values()
                    if hasattr(cls, 'provider') and cls.provider == config.provider
                ),
                None
            )
        
        if not adapter_class:
            raise ValueError(
                f"Adapter class not found for {config.adapter_id} "
                f"(provider: {config.provider})"
            )
        
        adapter = adapter_class(config)
        self._instances[config.adapter_id] = adapter
        return adapter
    
    def get_adapter(self, adapter_id: str) -> Optional[BaseAdapter]:
        """Get an existing adapter instance.
        
        Args:
            adapter_id: Adapter identifier
            
        Returns:
            Adapter instance or None if not found
        """
        return self._instances.get(adapter_id)
    
    def list_adapters(self) -> List[str]:
        """List all registered adapter IDs.
        
        Returns:
            List of adapter identifiers
        """
        return list(self._adapters.keys())
    
    def unregister(self, adapter_id: str) -> None:
        """Unregister an adapter.
        
        Args:
            adapter_id: Adapter identifier
        """
        if adapter_id in self._adapters:
            del self._adapters[adapter_id]
        
        if adapter_id in self._instances:
            instance = self._instances.pop(adapter_id)
            # Cleanup instance if possible
            if hasattr(instance, 'cleanup'):
                try:
                    import asyncio
                    if asyncio.iscoroutinefunction(instance.cleanup):
                        asyncio.create_task(instance.cleanup())
                    else:
                        instance.cleanup()
                except Exception as e:
                    self._logger.warning(f"Error cleaning up adapter {adapter_id}: {e}")


# Global adapter registry
_registry = AdapterRegistry()


def register_adapter(
    adapter_id: str,
    adapter_class: Type[BaseAdapter],
    overwrite: bool = False,
) -> None:
    """Register an adapter class in the global registry.
    
    Args:
        adapter_id: Unique adapter identifier
        adapter_class: Adapter class implementing BaseAdapter
        overwrite: Whether to overwrite existing registration
    """
    _registry.register(adapter_id, adapter_class, overwrite)


def get_adapter_registry() -> AdapterRegistry:
    """Get the global adapter registry.
    
    Returns:
        Global adapter registry instance
    """
    return _registry


def get_adapter(config: AdapterConfig) -> BaseAdapter:
    """Get or create an adapter instance.
    
    Args:
        config: Adapter configuration
        
    Returns:
        Adapter instance
    """
    return _registry.create_adapter(config)

