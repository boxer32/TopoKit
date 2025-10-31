"""Contract test for production deployment in TopoKit."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from topokit.types import (
    Deployment,
    DeploymentStatus,
    DeploymentConfig,
    DeploymentHealth,
    DeploymentMetrics,
    DeploymentHistory,
    ResourceRequirements,
    HealthCheckConfig,
    SecurityConfig,
    MonitoringConfig
)
from topokit.core.config import Environment


class TestProductionDeployment:
    """Contract tests for production deployment."""
    
    @pytest.fixture
    def sample_deployment_config(self):
        """Create a sample deployment configuration."""
        return DeploymentConfig(
            environment=Environment.PRODUCTION,
            resources=ResourceRequirements(
                cpu_cores=4,
                memory_mb=4096,
                storage_gb=20,
                max_instances=5,
                min_instances=2,
                auto_scaling=True
            ),
            health_check=HealthCheckConfig(
                enabled=True,
                endpoint="/health",
                interval_seconds=30,
                timeout_seconds=10,
                failure_threshold=3,
                success_threshold=1
            ),
            security=SecurityConfig(
                enable_ssl=True,
                enable_authentication=True,
                enable_authorization=True,
                enable_audit_logging=True,
                enable_pii_redaction=True,
                enable_encryption=True
            ),
            monitoring=MonitoringConfig(
                enable_metrics=True,
                enable_tracing=True,
                enable_logging=True,
                metrics_port=8080,
                log_level="INFO",
                alert_enabled=True,
                alert_channels=["slack", "email"]
            )
        )
    
    def test_deployment_creation_contract(self, sample_deployment_config):
        """Contract test: Deployment creation must include all required components."""
        deployment = Deployment(
            id="deployment-001",
            name="production-deployment",
            topology_id="topology-rag-system",
            topology_version="1.0.0",
            config=sample_deployment_config,
            created_by="devops-engineer"
        )
        
        # Contract: Must have all required fields
        assert deployment.id == "deployment-001"
        assert deployment.name == "production-deployment"
        assert deployment.topology_id == "topology-rag-system"
        assert deployment.topology_version == "1.0.0"
        assert deployment.status == DeploymentStatus.PENDING
        assert isinstance(deployment.config, DeploymentConfig)
        assert deployment.environment == Environment.PRODUCTION
        
        # Contract: Must have creation metadata
        assert deployment.created_at is not None
        assert deployment.updated_at is not None
        assert deployment.created_by == "devops-engineer"
    
    def test_deployment_configuration_contract(self, sample_deployment_config):
        """Contract test: Deployment configuration must include production requirements."""
        # Contract: Production environment must have security enabled
        assert sample_deployment_config.environment == Environment.PRODUCTION
        assert sample_deployment_config.security.enable_ssl is True
        assert sample_deployment_config.security.enable_authentication is True
        assert sample_deployment_config.security.enable_authorization is True
        assert sample_deployment_config.security.enable_audit_logging is True
        
        # Contract: Production must have monitoring enabled
        assert sample_deployment_config.monitoring.enable_metrics is True
        assert sample_deployment_config.monitoring.enable_tracing is True
        assert sample_deployment_config.monitoring.enable_logging is True
        
        # Contract: Production must have health checks
        assert sample_deployment_config.health_check.enabled is True
        assert sample_deployment_config.health_check.endpoint == "/health"
    
    def test_deployment_health_contract(self, sample_deployment_config):
        """Contract test: Deployment health must track uptime and performance."""
        deployment = Deployment(
            id="deployment-001",
            name="production-deployment",
            topology_id="topology-rag-system",
            topology_version="1.0.0",
            config=sample_deployment_config,
            created_by="devops-engineer"
        )
        
        # Contract: Health status must be trackable
        health = DeploymentHealth(
            status="healthy",
            uptime_percentage=99.95,
            response_time_ms=150.0,
            error_rate=0.001,
            active_instances=3,
            total_requests=10000
        )
        
        deployment.update_health(health)
        
        # Contract: Deployment must track health
        assert deployment.health is not None
        assert deployment.health.status == "healthy"
        assert deployment.health.uptime_percentage == 99.95
        assert deployment.health.response_time_ms == 150.0
        assert deployment.health.error_rate == 0.001
        
        # Contract: Health check must update timestamp
        assert deployment.updated_at is not None
    
    def test_deployment_metrics_contract(self, sample_deployment_config):
        """Contract test: Deployment metrics must track performance and cost."""
        deployment = Deployment(
            id="deployment-001",
            name="production-deployment",
            topology_id="topology-rag-system",
            topology_version="1.0.0",
            config=sample_deployment_config,
            created_by="devops-engineer"
        )
        
        # Contract: Metrics must track performance
        metrics = DeploymentMetrics(
            request_count=100000,
            success_count=99900,
            error_count=100,
            avg_response_time_ms=180.0,
            p95_response_time_ms=350.0,
            p99_response_time_ms=500.0,
            throughput_rps=50.0,
            cpu_usage_percent=45.0,
            memory_usage_percent=60.0,
            token_usage=5000000,
            cost_usd=50.0
        )
        
        deployment.update_metrics(metrics)
        
        # Contract: Deployment must track metrics
        assert deployment.metrics is not None
        assert deployment.metrics.request_count == 100000
        assert deployment.metrics.success_count == 99900
        assert deployment.metrics.error_count == 100
        assert deployment.metrics.avg_response_time_ms == 180.0
        assert deployment.metrics.token_usage == 5000000
        assert deployment.metrics.cost_usd == 50.0
        
        # Contract: Metrics update must update timestamp
        assert deployment.updated_at is not None
    
    def test_deployment_history_contract(self, sample_deployment_config):
        """Contract test: Deployment history must track all state changes."""
        deployment = Deployment(
            id="deployment-001",
            name="production-deployment",
            topology_id="topology-rag-system",
            topology_version="1.0.0",
            config=sample_deployment_config,
            created_by="devops-engineer"
        )
        
        # Contract: Must track deployment history
        history_entry = DeploymentHistory(
            timestamp=datetime.utcnow(),
            status=DeploymentStatus.DEPLOYING,
            version="1.0.0",
            deployed_by="devops-engineer",
            notes="Initial deployment"
        )
        
        deployment.add_history_entry(history_entry)
        
        # Contract: History must be recorded
        assert len(deployment.history) == 1
        assert deployment.history[0].status == DeploymentStatus.DEPLOYING
        assert deployment.history[0].version == "1.0.0"
        assert deployment.history[0].deployed_by == "devops-engineer"
        
        # Contract: Status must be updated from history
        assert deployment.status == DeploymentStatus.DEPLOYING
        
        # Contract: History entry must update timestamp
        assert deployment.updated_at is not None
    
    def test_deployment_health_check_contract(self, sample_deployment_config):
        """Contract test: Deployment must validate health status."""
        deployment = Deployment(
            id="deployment-001",
            name="production-deployment",
            topology_id="topology-rag-system",
            topology_version="1.0.0",
            config=sample_deployment_config,
            created_by="devops-engineer"
        )
        
        # Contract: Deployment without health is not healthy
        assert deployment.is_healthy() is False
        
        # Contract: Healthy deployment must have 99.9%+ uptime
        healthy_status = DeploymentHealth(
            status="healthy",
            uptime_percentage=99.95,
            response_time_ms=150.0,
            error_rate=0.0005,
            active_instances=3,
            total_requests=100000
        )
        deployment.update_health(healthy_status)
        assert deployment.is_healthy() is True
        
        # Contract: Deployment with <99.9% uptime is not healthy
        unhealthy_status = DeploymentHealth(
            status="degraded",
            uptime_percentage=99.5,
            response_time_ms=200.0,
            error_rate=0.001,
            active_instances=2,
            total_requests=50000
        )
        deployment.update_health(unhealthy_status)
        assert deployment.is_healthy() is False
    
    def test_deployment_slo_compliance_contract(self, sample_deployment_config):
        """Contract test: Deployment must validate SLO compliance."""
        deployment = Deployment(
            id="deployment-001",
            name="production-deployment",
            topology_id="topology-rag-system",
            topology_version="1.0.0",
            config=sample_deployment_config,
            created_by="devops-engineer"
        )
        
        # Contract: Deployment without metrics/health cannot meet SLO
        assert deployment.meets_slo() is False
        
        # Contract: Deployment meeting SLO must have:
        # - 99.9%+ uptime
        # - <0.1% error rate
        # - <2s p95 response time
        health = DeploymentHealth(
            status="healthy",
            uptime_percentage=99.95,
            response_time_ms=150.0,
            error_rate=0.0005,
            active_instances=3,
            total_requests=100000
        )
        
        metrics = DeploymentMetrics(
            request_count=100000,
            success_count=99950,
            error_count=50,
            avg_response_time_ms=180.0,
            p95_response_time_ms=1800.0,  # < 2s
            p99_response_time_ms=2200.0,
            throughput_rps=50.0,
            cpu_usage_percent=45.0,
            memory_usage_percent=60.0,
            token_usage=5000000,
            cost_usd=50.0
        )
        
        deployment.update_health(health)
        deployment.update_metrics(metrics)
        
        # Contract: Deployment must meet SLO requirements
        assert deployment.meets_slo() is True
        
        # Contract: Deployment with high error rate fails SLO
        metrics.error_count = 200  # 0.2% error rate
        deployment.update_metrics(metrics)
        assert deployment.meets_slo() is False
    
    def test_deployment_status_transitions_contract(self, sample_deployment_config):
        """Contract test: Deployment status must transition through valid states."""
        deployment = Deployment(
            id="deployment-001",
            name="production-deployment",
            topology_id="topology-rag-system",
            topology_version="1.0.0",
            config=sample_deployment_config,
            created_by="devops-engineer"
        )
        
        # Contract: Initial status must be PENDING
        assert deployment.status == DeploymentStatus.PENDING
        
        # Contract: Must transition through valid states
        deployment.add_history_entry(DeploymentHistory(
            timestamp=datetime.utcnow(),
            status=DeploymentStatus.DEPLOYING,
            version="1.0.0",
            deployed_by="devops-engineer"
        ))
        assert deployment.status == DeploymentStatus.DEPLOYING
        
        deployment.add_history_entry(DeploymentHistory(
            timestamp=datetime.utcnow(),
            status=DeploymentStatus.ACTIVE,
            version="1.0.0",
            deployed_by="devops-engineer"
        ))
        assert deployment.status == DeploymentStatus.ACTIVE
        
        # Contract: Can transition to failed state
        deployment.add_history_entry(DeploymentHistory(
            timestamp=datetime.utcnow(),
            status=DeploymentStatus.FAILED,
            version="1.0.0",
            deployed_by="devops-engineer",
            notes="Deployment failed due to health check timeout"
        ))
        assert deployment.status == DeploymentStatus.FAILED
    
    def test_deployment_production_requirements_contract(self):
        """Contract test: Production deployment must enforce all security and monitoring requirements."""
        # Contract: Production deployment must have security enabled
        production_config = DeploymentConfig(
            environment=Environment.PRODUCTION,
            security=SecurityConfig(
                enable_ssl=True,
                enable_authentication=True,
                enable_authorization=True,
                enable_audit_logging=True,
                enable_pii_redaction=True,
                enable_encryption=True
            ),
            monitoring=MonitoringConfig(
                enable_metrics=True,
                enable_tracing=True,
                enable_logging=True,
                alert_enabled=True
            )
        )
        
        assert production_config.environment == Environment.PRODUCTION
        assert production_config.security.enable_ssl is True
        assert production_config.security.enable_authentication is True
        assert production_config.monitoring.enable_metrics is True
        assert production_config.monitoring.alert_enabled is True

