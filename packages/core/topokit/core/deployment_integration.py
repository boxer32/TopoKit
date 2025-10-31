"""Integration module connecting production deployment with User Story 1 components."""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from ..types import Deployment, DeploymentStatus, DeploymentHealth, DeploymentMetrics
from ..types.topology import TopologyPack
from .orchestrator import EnhancedTopoOrchestrator
from .pack_parser import EnhancedPackParser
from .monitoring import PerformanceMonitor, get_performance_monitor, TraceSpan
from .alerting import AlertManager, get_alert_manager, AlertSeverity, AlertThreshold, AlertRule, AlertChannel
from .logging import get_logger


logger = get_logger(__name__)


class ProductionOrchestrator:
    """Production orchestrator that integrates User Story 1 components with deployment monitoring."""

    def __init__(
        self,
        deployment: Deployment,
        orchestrator: Optional[EnhancedTopoOrchestrator] = None,
        performance_monitor: Optional[PerformanceMonitor] = None,
        alert_manager: Optional[AlertManager] = None,
    ):
        """Initialize production orchestrator.

        Args:
            deployment: Deployment configuration
            orchestrator: Base orchestrator from User Story 1
            performance_monitor: Performance monitoring system
            alert_manager: Alert management system
        """
        self.deployment = deployment
        self.orchestrator = orchestrator
        self.performance_monitor = performance_monitor or get_performance_monitor()
        self.alert_manager = alert_manager or get_alert_manager()
        self.logger = logger
        
        # Setup alert rules for deployment
        self._setup_alert_rules()

    def _setup_alert_rules(self) -> None:
        """Setup alert rules for production deployment."""
        # SLO violation alert rule
        slo_rule = AlertRule(
            id="slo-violation",
            name="SLO Violation",
            description="Alert when deployment fails to meet SLO requirements",
            thresholds=[
                AlertThreshold(
                    metric_name="uptime_percentage",
                    threshold_value=99.9,
                    comparison="lt",
                    severity=AlertSeverity.CRITICAL,
                    duration_seconds=300,  # 5 minutes
                ),
                AlertThreshold(
                    metric_name="error_rate",
                    threshold_value=0.001,
                    comparison="gt",
                    severity=AlertSeverity.HIGH,
                    duration_seconds=60,
                ),
                AlertThreshold(
                    metric_name="p95_response_time_ms",
                    threshold_value=2000.0,
                    comparison="gt",
                    severity=AlertSeverity.MEDIUM,
                    duration_seconds=120,
                ),
            ],
            channels=[AlertChannel.SLACK, AlertChannel.EMAIL] if self.deployment.config.monitoring.alert_channels else [AlertChannel.CONSOLE],
            enabled=True,
            tags={"deployment_id": self.deployment.id, "type": "slo"},
        )
        self.alert_manager.add_rule(slo_rule)

        # Circuit breaker alert rule
        circuit_breaker_rule = AlertRule(
            id="circuit-breaker-open",
            name="Circuit Breaker Open",
            description="Alert when circuit breaker opens",
            thresholds=[
                AlertThreshold(
                    metric_name="circuit_breaker_failures",
                    threshold_value=0,
                    comparison="gt",
                    severity=AlertSeverity.HIGH,
                    duration_seconds=10,
                ),
            ],
            channels=[AlertChannel.SLACK, AlertChannel.EMAIL] if self.deployment.config.monitoring.alert_channels else [AlertChannel.CONSOLE],
            enabled=True,
            tags={"deployment_id": self.deployment.id, "type": "circuit_breaker"},
        )
        self.alert_manager.add_rule(circuit_breaker_rule)

    async def execute(
        self,
        session_id: str,
        input_data: Dict[str, Any],
        entry_node: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute topology with production monitoring and alerting.

        Args:
            session_id: Unique session identifier
            input_data: Input data for execution
            entry_node: Entry node ID (optional)
            timeout_seconds: Execution timeout (optional)

        Returns:
            Execution result with monitoring data
        """
        if not self.orchestrator:
            raise ValueError("Orchestrator not initialized")

        start_time = datetime.utcnow()
        trace_id = f"trace-{datetime.utcnow().timestamp()}"

        try:
            # Create trace span for root execution
            root_span = TraceSpan(
                span_id=f"span-{trace_id}",
                trace_id=trace_id,
                parent_span_id=None,
                name="topology_execution",
                start_time=start_time,
                end_time=None,
                duration_ms=None,
                status="success",
                tags={
                    "session_id": session_id,
                    "deployment_id": self.deployment.id,
                    "entry_node": entry_node or "auto",
                },
            )
            self.performance_monitor.record_span(root_span)

            # Execute topology
            result = await self.orchestrator.execute(
                session_id=session_id,
                input_data=input_data,
                entry_node=entry_node,
                timeout_seconds=timeout_seconds,
            )

            # Record execution metrics
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            success = result.get("success", False)

            # Update root span
            root_span.end_time = datetime.utcnow()
            root_span.duration_ms = execution_time_ms
            root_span.status = "success" if success else "error"
            self.performance_monitor.record_span(root_span)

            # Record performance metrics
            nodes_executed = result.get("nodes_executed", [])
            for node_id in nodes_executed:
                node_response_time = execution_time_ms / max(len(nodes_executed), 1)
                self.performance_monitor.record_execution(
                    session_id=session_id,
                    node_id=node_id,
                    response_time_ms=node_response_time,
                    success=success,
                )

            # Update deployment health and metrics
            await self._update_deployment_metrics(execution_time_ms, success)

            # Add monitoring data to result
            result["monitoring"] = {
                "trace_id": trace_id,
                "execution_time_ms": execution_time_ms,
                "deployment_id": self.deployment.id,
                "session_id": session_id,
            }

            return result

        except Exception as e:
            # Record error
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            root_span.end_time = datetime.utcnow()
            root_span.duration_ms = execution_time_ms
            root_span.status = "error"
            root_span.logs = [{"error": str(e)}]
            self.performance_monitor.record_span(root_span)

            # Record error metrics
            self.performance_monitor.record_execution(
                session_id=session_id,
                node_id=entry_node or "unknown",
                response_time_ms=execution_time_ms,
                success=False,
                error=str(e),
            )

            # Update deployment metrics
            await self._update_deployment_metrics(execution_time_ms, False)

            # Trigger alert if critical error
            await self.alert_manager.evaluate_threshold(
                metric_name="execution_error_rate",
                value=1.0,
                deployment_id=self.deployment.id,
            )

            raise

    async def _update_deployment_metrics(self, execution_time_ms: float, success: bool) -> None:
        """Update deployment health and metrics."""
        # Evaluate performance metrics
        metrics = await self.performance_monitor.evaluate_metrics(
            deployment_id=self.deployment.id,
        )

        # Update deployment metrics
        deployment_metrics = DeploymentMetrics(
            request_count=metrics.request_count + 1,
            success_count=metrics.success_count + (1 if success else 0),
            error_count=metrics.error_count + (0 if success else 1),
            avg_response_time_ms=metrics.avg_response_time_ms,
            p95_response_time_ms=metrics.p95_response_time_ms,
            p99_response_time_ms=metrics.p99_response_time_ms,
            throughput_rps=metrics.throughput_rps,
            cpu_usage_percent=metrics.cpu_usage_percent,
            memory_usage_percent=metrics.memory_usage_percent,
            token_usage=metrics.token_usage,
            cost_usd=metrics.cost_usd,
            schema_pass_rate=metrics.schema_pass_rate,
            error_rate=metrics.error_rate,
        )

        self.deployment.update_metrics(deployment_metrics)

        # Update deployment health
        health = DeploymentHealth(
            status="healthy" if self.deployment.meets_slo() else "unhealthy",
            uptime_percentage=99.9 if success else 99.0,  # Simplified for demo
            response_time_ms=execution_time_ms,
            error_rate=deployment_metrics.error_rate,
            active_instances=1,  # Would be actual instance count in production
            total_requests=deployment_metrics.request_count,
        )
        self.deployment.update_health(health)

        # Evaluate metrics for alerting
        if deployment_metrics.request_count > 0:
            # Check SLO compliance
            if not self.deployment.meets_slo():
                await self.alert_manager.evaluate_threshold(
                    metric_name="uptime_percentage",
                    value=health.uptime_percentage,
                    deployment_id=self.deployment.id,
                )

            # Check error rate
            if deployment_metrics.error_rate > 0.001:
                await self.alert_manager.evaluate_threshold(
                    metric_name="error_rate",
                    value=deployment_metrics.error_rate,
                    deployment_id=self.deployment.id,
                )

            # Check response time
            if deployment_metrics.p95_response_time_ms > 2000.0:
                await self.alert_manager.evaluate_threshold(
                    metric_name="p95_response_time_ms",
                    value=deployment_metrics.p95_response_time_ms,
                    deployment_id=self.deployment.id,
                )


class DeploymentService:
    """Service for managing production deployments with User Story 1 integration."""

    def __init__(
        self,
        performance_monitor: Optional[PerformanceMonitor] = None,
        alert_manager: Optional[AlertManager] = None,
    ):
        """Initialize deployment service.

        Args:
            performance_monitor: Performance monitoring system
            alert_manager: Alert management system
        """
        self.performance_monitor = performance_monitor or get_performance_monitor()
        self.alert_manager = alert_manager or get_alert_manager()
        self.active_deployments: Dict[str, ProductionOrchestrator] = {}
        self.logger = logger

    async def create_production_orchestrator(
        self,
        deployment: Deployment,
        topology_pack: TopologyPack,
    ) -> ProductionOrchestrator:
        """Create a production orchestrator for a deployment.

        Args:
            deployment: Deployment configuration
            topology_pack: Topology pack to execute

        Returns:
            Production orchestrator instance
        """
        # Create base orchestrator from User Story 1
        orchestrator = EnhancedTopoOrchestrator(topology_pack)

        # Create production orchestrator with monitoring and alerting
        prod_orchestrator = ProductionOrchestrator(
            deployment=deployment,
            orchestrator=orchestrator,
            performance_monitor=self.performance_monitor,
            alert_manager=self.alert_manager,
        )

        # Store active deployment
        self.active_deployments[deployment.id] = prod_orchestrator

        self.logger.info(f"Created production orchestrator for deployment {deployment.id}")
        return prod_orchestrator

    async def load_deployment_from_topology(
        self,
        deployment: Deployment,
        topology_path: str,
    ) -> ProductionOrchestrator:
        """Load deployment from topology files.

        Args:
            deployment: Deployment configuration
            topology_path: Path to topology directory

        Returns:
            Production orchestrator instance
        """
        # Parse topology using User Story 1 parser
        parser = EnhancedPackParser(topology_path)
        parse_result = parser.parse()

        if not parse_result.success:
            raise ValueError(f"Failed to parse topology: {parse_result.errors}")

        # Create production orchestrator
        return await self.create_production_orchestrator(
            deployment=deployment,
            topology_pack=parse_result.pack,
        )

    def get_production_orchestrator(self, deployment_id: str) -> Optional[ProductionOrchestrator]:
        """Get production orchestrator by deployment ID.

        Args:
            deployment_id: Deployment identifier

        Returns:
            Production orchestrator or None if not found
        """
        return self.active_deployments.get(deployment_id)

    async def execute_deployment(
        self,
        deployment_id: str,
        session_id: str,
        input_data: Dict[str, Any],
        entry_node: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute topology for a deployment.

        Args:
            deployment_id: Deployment identifier
            session_id: Session identifier
            input_data: Input data
            entry_node: Entry node (optional)
            timeout_seconds: Timeout (optional)

        Returns:
            Execution result
        """
        orchestrator = self.get_production_orchestrator(deployment_id)
        if not orchestrator:
            raise ValueError(f"Deployment {deployment_id} not found")

        return await orchestrator.execute(
            session_id=session_id,
            input_data=input_data,
            entry_node=entry_node,
            timeout_seconds=timeout_seconds,
        )

    def get_deployment_health(self, deployment_id: str) -> Optional[DeploymentHealth]:
        """Get deployment health status.

        Args:
            deployment_id: Deployment identifier

        Returns:
            Deployment health or None if not found
        """
        orchestrator = self.get_production_orchestrator(deployment_id)
        if not orchestrator:
            return None

        return orchestrator.deployment.health

    def get_deployment_metrics(self, deployment_id: str) -> Optional[DeploymentMetrics]:
        """Get deployment metrics.

        Args:
            deployment_id: Deployment identifier

        Returns:
            Deployment metrics or None if not found
        """
        orchestrator = self.get_production_orchestrator(deployment_id)
        if not orchestrator:
            return None

        return orchestrator.deployment.metrics


# Global deployment service instance
_deployment_service: Optional[DeploymentService] = None


def get_deployment_service() -> DeploymentService:
    """Get or create global deployment service instance."""
    global _deployment_service
    if _deployment_service is None:
        _deployment_service = DeploymentService()
    return _deployment_service

