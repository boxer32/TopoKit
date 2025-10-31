"""Integration test for production monitoring in TopoKit."""

import pytest
import tempfile
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from topokit.core.pack_parser import EnhancedPackParser, PackParseResult
from topokit.core.orchestrator import EnhancedTopoOrchestrator
from topokit.types.topology import TopologyPack, Node, EdgePolicy
from topokit.types import (
    Deployment,
    DeploymentStatus,
    DeploymentConfig,
    DeploymentHealth,
    DeploymentMetrics,
    ResourceRequirements,
    HealthCheckConfig,
    SecurityConfig,
    MonitoringConfig
)
from topokit.core.config import Environment


class TestProductionMonitoring:
    """Integration tests for production monitoring."""
    
    @pytest.fixture
    def sample_topology_dir(self):
        """Create a temporary directory with sample topology files."""
        temp_dir = tempfile.mkdtemp()
        topology_dir = Path(temp_dir) / "topology"
        topology_dir.mkdir()
        
        # Create nodes.yaml
        nodes_yaml = """nodes:
  - id: "Data.Retrieval"
    kind: "data"
    version: "1.0.0"
    scope:
      contracts: ["retrieve"]
      context_required: false
    execution_profile:
      temperature: 0.2
      top_p: 0.9
      seed: "stable"
      max_tokens: 1000
      deterministic_reranker: true
    slos:
      schema_pass_rate: "≥ 99%"
      drift_threshold: "≤ 10%"
      latency_budget: "≤ 1000ms"
    circuit_breaker:
      failure_threshold: 3
      timeout_ms: 2000
  - id: "AI.Answer"
    kind: "ai"
    version: "1.0.0"
    scope:
      contracts: ["answer"]
      context_required: false
    execution_profile:
      temperature: 0.2
      top_p: 0.9
      seed: "stable"
      max_tokens: 1000
      deterministic_reranker: true
    slos:
      schema_pass_rate: "≥ 99%"
      drift_threshold: "≤ 10%"
      latency_budget: "≤ 2000ms"
    circuit_breaker:
      failure_threshold: 3
      timeout_ms: 2000
"""
        (topology_dir / "nodes.yaml").write_text(nodes_yaml)
        
        # Create edges.yaml
        edges_yaml = """edges:
  - id: "Data.Retrieval_to_AI.Answer"
    from: "Data.Retrieval"
    to: "AI.Answer"
    version: "1.0.0"
    contracts: ["retrieve"]
    allow: true
    timeout_ms: 4000
    max_retries: 0
"""
        (topology_dir / "edges.yaml").write_text(edges_yaml)
        
        # Create contracts directory and contract file
        contracts_dir = topology_dir / "contracts"
        contracts_dir.mkdir()
        
        retrieve_contract = """{
  "name": "retrieve",
  "version": "1.0.0",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query"
      }
    },
    "required": ["query"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "results": {
        "type": "array",
        "items": {"type": "string"}
      }
    },
    "required": ["results"]
  },
  "description": "Retrieval contract"
}
"""
        (contracts_dir / "retrieve.json").write_text(retrieve_contract)
        
        answer_contract = """{
  "name": "answer",
  "version": "1.0.0",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "context": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["query", "context"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "answer": {"type": "string"}
    },
    "required": ["answer"]
  },
  "description": "Answer contract"
}
"""
        (contracts_dir / "answer.json").write_text(answer_contract)
        
        # Create guardrails.yaml
        guardrails_yaml = """determinism:
  temperature: 0.2
  seed: "session-hash"
  canonical_sort: true

confidence:
  threshold: 0.6

fallback:
  enabled: true
  policy: rule_first

circuit_breakers:
  enabled: true
  failure_threshold: 3

policy_engine:
  enabled: true
  environment: "production"

observability:
  enabled: true
  logging_level: "info"
"""
        (topology_dir / "guardrails.yaml").write_text(guardrails_yaml)
        
        yield str(topology_dir)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def production_deployment(self, sample_topology_dir):
        """Create a production deployment for testing."""
        parser = EnhancedPackParser(sample_topology_dir)
        result = parser.parse()
        pack = result.pack
        
        deployment_config = DeploymentConfig(
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
        
        deployment = Deployment(
            id="deployment-001",
            name="production-deployment",
            topology_id="rag-system",
            topology_version="1.0.0",
            config=deployment_config,
            created_by="devops-engineer"
        )
        
        return deployment, pack
    
    def test_monitoring_configuration_contract(self, production_deployment):
        """Integration test: Production deployment must have monitoring enabled."""
        deployment, pack = production_deployment
        
        # Contract: Production deployment must have monitoring enabled
        assert deployment.config.monitoring.enable_metrics is True
        assert deployment.config.monitoring.enable_tracing is True
        assert deployment.config.monitoring.enable_logging is True
        assert deployment.config.monitoring.alert_enabled is True
        assert len(deployment.config.monitoring.alert_channels) > 0
        
        # Contract: Production deployment must have health checks
        assert deployment.config.health_check.enabled is True
        assert deployment.config.health_check.endpoint == "/health"
        
        # Contract: Production deployment must have security enabled
        assert deployment.config.security.enable_ssl is True
        assert deployment.config.security.enable_authentication is True
        assert deployment.config.security.enable_audit_logging is True
    
    def test_health_monitoring_integration(self, production_deployment):
        """Integration test: Deployment must track health status in real-time."""
        deployment, pack = production_deployment
        
        # Contract: Deployment must support health monitoring
        initial_health = DeploymentHealth(
            status="healthy",
            uptime_percentage=100.0,
            response_time_ms=150.0,
            error_rate=0.0,
            active_instances=2,
            total_requests=0
        )
        
        deployment.update_health(initial_health)
        
        # Contract: Deployment must track health status
        assert deployment.health is not None
        assert deployment.health.status == "healthy"
        assert deployment.health.uptime_percentage == 100.0
        
        # Contract: Deployment must be able to update health in real-time
        updated_health = DeploymentHealth(
            status="healthy",
            uptime_percentage=99.95,
            response_time_ms=180.0,
            error_rate=0.0005,
            active_instances=3,
            total_requests=10000
        )
        
        deployment.update_health(updated_health)
        assert deployment.health.uptime_percentage == 99.95
        assert deployment.health.total_requests == 10000
    
    def test_metrics_collection_integration(self, production_deployment):
        """Integration test: Deployment must collect performance metrics."""
        deployment, pack = production_deployment
        
        # Contract: Deployment must support metrics collection
        metrics = DeploymentMetrics(
            request_count=100000,
            success_count=99950,
            error_count=50,
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
        
        # Contract: Deployment must track all performance metrics
        assert deployment.metrics is not None
        assert deployment.metrics.request_count == 100000
        assert deployment.metrics.success_count == 99950
        assert deployment.metrics.error_count == 50
        assert deployment.metrics.avg_response_time_ms == 180.0
        assert deployment.metrics.p95_response_time_ms == 350.0
        assert deployment.metrics.token_usage == 5000000
        assert deployment.metrics.cost_usd == 50.0
    
    def test_slo_compliance_monitoring_integration(self, production_deployment):
        """Integration test: Deployment must monitor SLO compliance."""
        deployment, pack = production_deployment
        
        # Contract: Deployment must validate SLO compliance
        # Setup healthy deployment meeting SLO
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
        
        # Contract: Deployment must detect SLO violations
        # Violate error rate requirement
        metrics.error_count = 200  # 0.2% error rate > 0.1%
        deployment.update_metrics(metrics)
        assert deployment.meets_slo() is False
    
    def test_alert_integration(self, production_deployment):
        """Integration test: Deployment must support alerting."""
        deployment, pack = production_deployment
        
        # Contract: Production deployment must have alerting configured
        assert deployment.config.monitoring.alert_enabled is True
        assert len(deployment.config.monitoring.alert_channels) > 0
        assert "slack" in deployment.config.monitoring.alert_channels
        assert "email" in deployment.config.monitoring.alert_channels
        
        # Contract: Alerts should trigger on SLO violations
        health = DeploymentHealth(
            status="unhealthy",
            uptime_percentage=99.5,  # < 99.9%
            response_time_ms=2500.0,
            error_rate=0.002,  # > 0.1%
            active_instances=1,
            total_requests=50000
        )
        
        metrics = DeploymentMetrics(
            request_count=50000,
            success_count=49900,
            error_count=100,
            avg_response_time_ms=2500.0,
            p95_response_time_ms=3000.0,  # > 2s
            p99_response_time_ms=4000.0,
            throughput_rps=25.0,
            cpu_usage_percent=80.0,
            memory_usage_percent=85.0,
            token_usage=2500000,
            cost_usd=25.0
        )
        
        deployment.update_health(health)
        deployment.update_metrics(metrics)
        
        # Contract: Deployment should be marked as not meeting SLO when unhealthy
        assert deployment.meets_slo() is False
        assert deployment.is_healthy() is False
    
    def test_real_time_monitoring_integration(self, production_deployment):
        """Integration test: Deployment must support real-time monitoring with <1s refresh rate."""
        deployment, pack = production_deployment
        
        # Contract: Deployment must support rapid health updates
        start_time = datetime.utcnow()
        
        # Simulate rapid health updates
        for i in range(10):
            health = DeploymentHealth(
                status="healthy",
                uptime_percentage=99.95 - (i * 0.001),
                response_time_ms=150.0 + (i * 10),
                error_rate=0.0005 + (i * 0.0001),
                active_instances=3,
                total_requests=10000 * (i + 1)
            )
            deployment.update_health(health)
        
        end_time = datetime.utcnow()
        update_duration = (end_time - start_time).total_seconds()
        
        # Contract: Health updates must complete quickly (<1s for multiple updates)
        assert update_duration < 1.0, f"Health updates took {update_duration}s, exceeds <1s requirement"
        
        # Contract: Latest health status must be available
        assert deployment.health is not None
        assert deployment.health.total_requests == 100000
    
    def test_production_deployment_orchestration_integration(self, production_deployment, sample_topology_dir):
        """Integration test: Production deployment must work with orchestrator."""
        deployment, pack = production_deployment
        
        # Contract: Deployment must be compatible with orchestrator
        orchestrator = EnhancedTopoOrchestrator(pack)
        assert orchestrator is not None
        
        # Contract: Deployment monitoring must track orchestrator execution
        # Simulate execution metrics
        metrics = DeploymentMetrics(
            request_count=1000,
            success_count=995,
            error_count=5,
            avg_response_time_ms=180.0,
            p95_response_time_ms=350.0,
            p99_response_time_ms=500.0,
            throughput_rps=50.0,
            cpu_usage_percent=45.0,
            memory_usage_percent=60.0,
            token_usage=50000,
            cost_usd=0.5
        )
        
        deployment.update_metrics(metrics)
        
        # Contract: Metrics must reflect orchestrator performance
        assert deployment.metrics.request_count == 1000
        assert deployment.metrics.success_count == 995
        assert deployment.metrics.error_count == 5
    
    def test_production_deployment_security_monitoring_integration(self, production_deployment):
        """Integration test: Production deployment must monitor security controls."""
        deployment, pack = production_deployment
        
        # Contract: Production deployment must have all security controls enabled
        assert deployment.config.security.enable_ssl is True
        assert deployment.config.security.enable_authentication is True
        assert deployment.config.security.enable_authorization is True
        assert deployment.config.security.enable_audit_logging is True
        assert deployment.config.security.enable_pii_redaction is True
        assert deployment.config.security.enable_encryption is True
        
        # Contract: Security configuration must be validated for production
        assert deployment.config.environment == Environment.PRODUCTION
    
    def test_production_deployment_acceptance_criteria_integration(self, production_deployment):
        """Integration test: Production deployment must meet acceptance criteria from spec."""
        deployment, pack = production_deployment
        
        # Acceptance Criteria 1: Deploy with 99.9% uptime and all security controls active
        health = DeploymentHealth(
            status="healthy",
            uptime_percentage=99.95,  # > 99.9%
            response_time_ms=150.0,
            error_rate=0.0005,
            active_instances=3,
            total_requests=100000
        )
        deployment.update_health(health)
        
        assert deployment.is_healthy() is True
        assert deployment.config.security.enable_ssl is True
        assert deployment.config.security.enable_authentication is True
        assert deployment.config.security.enable_audit_logging is True
        
        # Acceptance Criteria 2: Real-time metrics, alerts, and drill-down capabilities
        metrics = DeploymentMetrics(
            request_count=100000,
            success_count=99950,
            error_count=50,
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
        
        assert deployment.metrics is not None
        assert deployment.config.monitoring.alert_enabled is True
        
        # Acceptance Criteria 3: Circuit breakers and fallback systems maintain 99.9% availability
        assert deployment.health.uptime_percentage >= 99.9
        assert deployment.meets_slo() is True

