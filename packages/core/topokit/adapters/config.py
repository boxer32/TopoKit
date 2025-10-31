"""
Module: adapter_config
Purpose: Adapter configuration management and health monitoring
Inputs: Configuration files, adapter instances
Outputs: Validated configurations, health status
Dependencies: adapter.framework, yaml/json parsers
Failure Modes: Invalid config → validation error, health failure → alert
Trace: page:adapters, build:20250127, spec-id:T103
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import json
import yaml
from pathlib import Path

from .framework import (
    AdapterConfig,
    AdapterType,
    BaseAdapter,
    AdapterHealth,
    AdapterRegistry,
    get_adapter_registry,
    get_adapter,
)
from ..core.logging import get_logger


logger = get_logger(__name__)


@dataclass
class AdapterManagerConfig:
    """Configuration for adapter manager."""
    adapters: List[AdapterConfig] = field(default_factory=list)
    health_check_interval_seconds: int = 60
    enable_health_monitoring: bool = True
    enable_auto_retry: bool = True
    max_retries: int = 3


class AdapterManager:
    """Manager for adapter configuration and health monitoring."""
    
    def __init__(self, config: Optional[AdapterManagerConfig] = None):
        """Initialize adapter manager.
        
        Args:
            config: Manager configuration
        """
        self.config = config or AdapterManagerConfig()
        self.logger = logger
        self.registry = get_adapter_registry()
        self._adapters: Dict[str, BaseAdapter] = {}
        self._health_status: Dict[str, AdapterHealth] = {}
        self._monitoring_task: Optional[Any] = None
    
    async def initialize(self) -> None:
        """Initialize all adapters."""
        self.logger.info("Initializing adapter manager")
        
        for adapter_config in self.config.adapters:
            if not adapter_config.enabled:
                continue
            
            try:
                adapter = get_adapter(adapter_config)
                await adapter.initialize()
                self._adapters[adapter_config.adapter_id] = adapter
                self.logger.info(f"Initialized adapter: {adapter_config.adapter_id}")
            except Exception as e:
                self.logger.error(f"Failed to initialize adapter {adapter_config.adapter_id}: {e}")
        
        # Start health monitoring if enabled
        if self.config.enable_health_monitoring:
            await self.start_health_monitoring()
    
    async def start_health_monitoring(self) -> None:
        """Start periodic health checks."""
        import asyncio
        
        async def monitor_health():
            """Periodic health check loop."""
            while True:
                await asyncio.sleep(self.config.health_check_interval_seconds)
                await self.check_all_health()
        
        self._monitoring_task = asyncio.create_task(monitor_health())
        self.logger.info("Started health monitoring")
    
    async def check_all_health(self) -> Dict[str, AdapterHealth]:
        """Check health of all adapters.
        
        Returns:
            Dictionary mapping adapter IDs to health status
        """
        health_results = {}
        
        for adapter_id, adapter in self._adapters.items():
            try:
                health = await adapter.health_check()
                health_results[adapter_id] = health
                self._health_status[adapter_id] = health
                
                if not health.healthy:
                    self.logger.warning(
                        f"Adapter {adapter_id} is unhealthy: {health.error_message}"
                    )
            except Exception as e:
                self.logger.error(f"Health check failed for adapter {adapter_id}: {e}")
                health = AdapterHealth(
                    adapter_id=adapter_id,
                    healthy=False,
                    last_check=datetime.now(timezone.utc),
                    error_message=str(e),
                )
                health_results[adapter_id] = health
                self._health_status[adapter_id] = health
        
        return health_results
    
    def get_adapter(self, adapter_id: str) -> Optional[BaseAdapter]:
        """Get adapter instance.
        
        Args:
            adapter_id: Adapter identifier
            
        Returns:
            Adapter instance or None if not found
        """
        return self._adapters.get(adapter_id)
    
    def get_health_status(self, adapter_id: str) -> Optional[AdapterHealth]:
        """Get health status for an adapter.
        
        Args:
            adapter_id: Adapter identifier
            
        Returns:
            Health status or None if not found
        """
        return self._health_status.get(adapter_id)
    
    async def shutdown(self) -> None:
        """Shutdown adapter manager."""
        self.logger.info("Shutting down adapter manager")
        
        # Stop monitoring
        if self._monitoring_task:
            self._monitoring_task.cancel()
        
        # Cleanup adapters
        for adapter in self._adapters.values():
            try:
                await adapter.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up adapter: {e}")
        
        self._adapters.clear()
        self._health_status.clear()


def load_adapter_configs(path: str) -> AdapterManagerConfig:
    """Load adapter configurations from file.
    
    Args:
        path: Path to configuration file (JSON or YAML)
        
    Returns:
        Adapter manager configuration
    """
    config_path = Path(path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    
    with open(config_path, "r") as f:
        if config_path.suffix in [".yaml", ".yml"]:
            data = yaml.safe_load(f)
        else:
            data = json.load(f)
    
    # Parse adapter configurations
    adapters = []
    for adapter_data in data.get("adapters", []):
        adapter_config = AdapterConfig(
            adapter_id=adapter_data["adapter_id"],
            adapter_type=AdapterType(adapter_data["adapter_type"]),
            provider=adapter_data["provider"],
            version=adapter_data.get("version", "1.0.0"),
            enabled=adapter_data.get("enabled", True),
            timeout_ms=adapter_data.get("timeout_ms", 30000),
            max_retries=adapter_data.get("max_retries", 3),
            retry_delay_ms=adapter_data.get("retry_delay_ms", 1000),
            connection_params=adapter_data.get("connection_params", {}),
            metadata=adapter_data.get("metadata", {}),
        )
        adapters.append(adapter_config)
    
    manager_config = AdapterManagerConfig(
        adapters=adapters,
        health_check_interval_seconds=data.get("health_check_interval_seconds", 60),
        enable_health_monitoring=data.get("enable_health_monitoring", True),
        enable_auto_retry=data.get("enable_auto_retry", True),
        max_retries=data.get("max_retries", 3),
    )
    
    return manager_config


def validate_adapter_config(config: AdapterConfig) -> List[str]:
    """Validate adapter configuration.
    
    Args:
        config: Adapter configuration
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    if not config.adapter_id:
        errors.append("adapter_id is required")
    
    if not config.provider:
        errors.append("provider is required")
    
    if config.timeout_ms <= 0:
        errors.append("timeout_ms must be positive")
    
    if config.max_retries < 0:
        errors.append("max_retries must be non-negative")
    
    # Provider-specific validation
    if config.adapter_type == AdapterType.LLM_PROVIDER:
        if config.provider in ["openai", "anthropic"]:
            if "api_key" not in config.connection_params:
                errors.append(f"{config.provider} requires api_key in connection_params")
    
    elif config.adapter_type == AdapterType.VECTOR_DATABASE:
        if config.provider == "pinecone":
            if "api_key" not in config.connection_params:
                errors.append("pinecone requires api_key in connection_params")
        elif config.provider == "weaviate":
            if "url" not in config.connection_params:
                errors.append("weaviate requires url in connection_params")
    
    elif config.adapter_type == AdapterType.GRAPH_DATABASE:
        if config.provider == "neo4j":
            if "uri" not in config.connection_params:
                errors.append("neo4j requires uri in connection_params")
            if "password" not in config.connection_params:
                errors.append("neo4j requires password in connection_params")
    
    return errors

