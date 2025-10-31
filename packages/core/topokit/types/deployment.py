"""Deployment type definitions for TopoKit production deployments."""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from topokit.core.config import Environment


class DeploymentStatus(str, Enum):
    """Deployment status types."""
    PENDING = "pending"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class ResourceRequirements(BaseModel):
    """Resource requirements for a deployment."""
    cpu_cores: int = Field(gt=0, default=2, description="CPU cores required")
    memory_mb: int = Field(gt=0, default=2048, description="Memory in MB required")
    storage_gb: int = Field(gt=0, default=10, description="Storage in GB required")
    max_instances: int = Field(gt=0, default=1, description="Maximum number of instances")
    min_instances: int = Field(gt=0, default=1, description="Minimum number of instances")
    auto_scaling: bool = Field(default=True, description="Enable auto-scaling")


class HealthCheckConfig(BaseModel):
    """Health check configuration."""
    enabled: bool = Field(default=True, description="Enable health checks")
    endpoint: str = Field(default="/health", description="Health check endpoint")
    interval_seconds: int = Field(gt=0, default=30, description="Check interval in seconds")
    timeout_seconds: int = Field(gt=0, default=10, description="Timeout in seconds")
    failure_threshold: int = Field(gt=0, default=3, description="Failure threshold before marking unhealthy")
    success_threshold: int = Field(gt=0, default=1, description="Success threshold before marking healthy")


class SecurityConfig(BaseModel):
    """Security configuration for deployment."""
    enable_ssl: bool = Field(default=True, description="Enable SSL/TLS")
    enable_authentication: bool = Field(default=True, description="Enable authentication")
    enable_authorization: bool = Field(default=True, description="Enable authorization")
    enable_audit_logging: bool = Field(default=True, description="Enable audit logging")
    enable_pii_redaction: bool = Field(default=True, description="Enable PII redaction")
    enable_encryption: bool = Field(default=True, description="Enable data encryption")
    allowed_ips: Optional[List[str]] = Field(default=None, description="Allowed IP addresses (whitelist)")
    blocked_ips: Optional[List[str]] = Field(default=None, description="Blocked IP addresses (blacklist)")


class MonitoringConfig(BaseModel):
    """Monitoring configuration for deployment."""
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    enable_tracing: bool = Field(default=True, description="Enable distributed tracing")
    enable_logging: bool = Field(default=True, description="Enable structured logging")
    metrics_port: int = Field(gt=0, default=8080, description="Metrics port")
    log_level: str = Field(default="INFO", description="Log level")
    alert_enabled: bool = Field(default=True, description="Enable alerts")
    alert_channels: List[str] = Field(default_factory=list, description="Alert channels (slack, email, webhook)")


class DeploymentConfig(BaseModel):
    """Deployment configuration."""
    environment: Environment = Field(..., description="Deployment environment")
    resources: ResourceRequirements = Field(default_factory=ResourceRequirements, description="Resource requirements")
    health_check: HealthCheckConfig = Field(default_factory=HealthCheckConfig, description="Health check configuration")
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="Security configuration")
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig, description="Monitoring configuration")
    custom_settings: Dict[str, Any] = Field(default_factory=dict, description="Custom deployment settings")


class DeploymentHealth(BaseModel):
    """Deployment health status."""
    status: str = Field(..., description="Health status (healthy, unhealthy, degraded)")
    last_check: datetime = Field(default_factory=datetime.utcnow, description="Last health check time")
    uptime_percentage: float = Field(ge=0.0, le=100.0, default=100.0, description="Uptime percentage")
    response_time_ms: float = Field(ge=0.0, default=0.0, description="Average response time in ms")
    error_rate: float = Field(ge=0.0, le=1.0, default=0.0, description="Error rate (0.0-1.0)")
    active_instances: int = Field(ge=0, default=1, description="Number of active instances")
    total_requests: int = Field(ge=0, default=0, description="Total requests handled")


class DeploymentMetrics(BaseModel):
    """Deployment performance metrics."""
    request_count: int = Field(ge=0, default=0, description="Total request count")
    success_count: int = Field(ge=0, default=0, description="Successful request count")
    error_count: int = Field(ge=0, default=0, description="Error count")
    avg_response_time_ms: float = Field(ge=0.0, default=0.0, description="Average response time in ms")
    p95_response_time_ms: float = Field(ge=0.0, default=0.0, description="95th percentile response time")
    p99_response_time_ms: float = Field(ge=0.0, default=0.0, description="99th percentile response time")
    throughput_rps: float = Field(ge=0.0, default=0.0, description="Requests per second")
    cpu_usage_percent: float = Field(ge=0.0, le=100.0, default=0.0, description="CPU usage percentage")
    memory_usage_percent: float = Field(ge=0.0, le=100.0, default=0.0, description="Memory usage percentage")
    token_usage: int = Field(ge=0, default=0, description="Total token usage")
    cost_usd: float = Field(ge=0.0, default=0.0, description="Total cost in USD")


class DeploymentHistory(BaseModel):
    """Deployment history entry."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Deployment timestamp")
    status: DeploymentStatus = Field(..., description="Deployment status")
    version: str = Field(..., description="Deployment version")
    deployed_by: str = Field(..., description="User who deployed")
    notes: Optional[str] = Field(default=None, description="Deployment notes")
    rollback_reason: Optional[str] = Field(default=None, description="Rollback reason if applicable")


class Deployment(BaseModel):
    """Deployment model for production deployments."""
    id: str = Field(..., description="Unique deployment identifier")
    name: str = Field(..., description="Deployment name")
    topology_id: str = Field(..., description="Topology pack identifier")
    topology_version: str = Field(..., description="Topology pack version")
    status: DeploymentStatus = Field(default=DeploymentStatus.PENDING, description="Current deployment status")
    config: DeploymentConfig = Field(..., description="Deployment configuration")
    health: Optional[DeploymentHealth] = Field(default=None, description="Current health status")
    metrics: Optional[DeploymentMetrics] = Field(default=None, description="Current performance metrics")
    history: List[DeploymentHistory] = Field(default_factory=list, description="Deployment history")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    created_by: str = Field(..., description="User who created the deployment")
    description: Optional[str] = Field(default=None, description="Deployment description")
    tags: Dict[str, str] = Field(default_factory=dict, description="Deployment tags for organization")
    
    def update_health(self, health: DeploymentHealth) -> None:
        """Update deployment health status."""
        self.health = health
        self.updated_at = datetime.utcnow()
    
    def update_metrics(self, metrics: DeploymentMetrics) -> None:
        """Update deployment metrics."""
        self.metrics = metrics
        self.updated_at = datetime.utcnow()
    
    def add_history_entry(self, entry: DeploymentHistory) -> None:
        """Add a history entry."""
        self.history.append(entry)
        self.status = entry.status
        self.updated_at = datetime.utcnow()
    
    def is_healthy(self) -> bool:
        """Check if deployment is healthy."""
        if not self.health:
            return False
        return self.health.status == "healthy" and self.health.uptime_percentage >= 99.9
    
    def meets_slo(self) -> bool:
        """Check if deployment meets SLO requirements."""
        if not self.metrics or not self.health:
            return False
        # Check 99.9% uptime requirement
        if self.health.uptime_percentage < 99.9:
            return False
        # Check error rate < 0.1%
        if self.metrics.error_count > 0 and (self.metrics.error_count / max(self.metrics.request_count, 1)) > 0.001:
            return False
        # Check response time < 2s for 95% of requests (approximated)
        if self.metrics.p95_response_time_ms > 2000:
            return False
        return True

