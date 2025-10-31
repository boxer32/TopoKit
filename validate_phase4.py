#!/usr/bin/env python3
"""Comprehensive validation script for Phase 4 Backend Foundation."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages', 'core'))

from datetime import datetime
import asyncio

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_deployment_model():
    """Test Deployment model."""
    print_section("1. Deployment Model Validation")
    
    try:
        from topokit.types.deployment import (
            Deployment, DeploymentConfig, DeploymentHealth, DeploymentMetrics,
            ResourceRequirements, SecurityConfig, MonitoringConfig,
            DeploymentStatus
        )
        from topokit.core.config import Environment
        
        # Create deployment config
        config = DeploymentConfig(
            environment=Environment.PRODUCTION,
            resources=ResourceRequirements(cpu_cores=4, memory_mb=4096),
            security=SecurityConfig(enable_ssl=True, enable_authentication=True),
            monitoring=MonitoringConfig(enable_metrics=True, alert_enabled=True)
        )
        
        # Create deployment
        deployment = Deployment(
            id="test-deployment",
            name="Test Deployment",
            topology_id="test-topology",
            topology_version="1.0.0",
            config=config,
            created_by="test-user"
        )
        
        print(f"✓ Deployment created: {deployment.id}")
        print(f"  - Status: {deployment.status.value}")
        print(f"  - Environment: {deployment.config.environment.value}")
        
        # Test health update
        health = DeploymentHealth(
            status="healthy",
            uptime_percentage=99.95,
            response_time_ms=150.0,
            error_rate=0.0005,
            active_instances=3,
            total_requests=1000
        )
        deployment.update_health(health)
        print(f"  - Health status: {deployment.health.status}")
        print(f"  - Uptime: {deployment.health.uptime_percentage}%")
        print(f"  - Is healthy: {deployment.is_healthy()}")
        
        # Test metrics update
        metrics = DeploymentMetrics(
            request_count=1000,
            success_count=995,
            error_count=5,
            avg_response_time_ms=180.0,
            p95_response_time_ms=350.0,
            error_rate=0.005  # Explicitly set error_rate
        )
        deployment.update_metrics(metrics)
        print(f"  - Metrics request count: {deployment.metrics.request_count}")
        print(f"  - Error count: {deployment.metrics.error_count}")
        if hasattr(deployment.metrics, 'error_rate'):
            print(f"  - Error rate: {deployment.metrics.error_rate}")
        else:
            # Calculate error rate
            error_rate = deployment.metrics.error_count / max(deployment.metrics.request_count, 1)
            print(f"  - Error rate (calculated): {error_rate:.4f}")
        print(f"  - Meets SLO: {deployment.meets_slo()}")
        
        return True
    except Exception as e:
        print(f"✗ Deployment model validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_alerting_system():
    """Test alerting system."""
    print_section("2. Alerting System Validation")
    
    try:
        from topokit.core.alerting import (
            AlertManager, get_alert_manager, AlertRule, AlertThreshold,
            AlertSeverity, AlertChannel
        )
        
        manager = get_alert_manager()
        print(f"✓ AlertManager created")
        print(f"  - Rules: {len(manager.rules)}")
        print(f"  - Notifiers: {len(manager.notifiers)}")
        
        # Create test rule
        rule = AlertRule(
            id="test-rule",
            name="Test Alert Rule",
            description="Test rule for validation",
            thresholds=[
                AlertThreshold(
                    metric_name="error_rate",
                    threshold_value=0.001,
                    comparison="gt",
                    severity=AlertSeverity.HIGH,
                    duration_seconds=60
                )
            ],
            channels=[AlertChannel.CONSOLE],
            enabled=True
        )
        manager.add_rule(rule)
        print(f"  - Rule added: {rule.name}")
        print(f"  - Total rules: {len(manager.rules)}")
        
        # Test threshold evaluation (non-async call to evaluate_threshold)
        # Note: This will trigger alerts if threshold is exceeded
        alerts = await manager.evaluate_threshold("error_rate", 0.002, "test-deployment")
        print(f"  - Alerts triggered: {len(alerts)}")
        
        # Get active alerts
        active_alerts = manager.get_active_alerts()
        print(f"  - Active alerts: {len(active_alerts)}")
        
        # Get statistics
        stats = manager.get_alert_statistics()
        print(f"  - Total alerts: {stats['total_alerts']}")
        print(f"  - Active alerts: {stats['active_alerts']}")
        
        return True
    except Exception as e:
        print(f"✗ Alerting system validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_monitoring_system():
    """Test monitoring system."""
    print_section("3. Performance Monitoring System Validation")
    
    try:
        from topokit.core.monitoring import (
            PerformanceMonitor, get_performance_monitor, Metric, MetricType
        )
        
        monitor = get_performance_monitor()
        print(f"✓ PerformanceMonitor created")
        print(f"  - Metric collector: {monitor.metric_collector is not None}")
        print(f"  - Trace collector: {monitor.trace_collector is not None}")
        print(f"  - Drift detector: {monitor.drift_detector is not None}")
        
        # Test metric recording
        metric = Metric(
            name="test.metric",
            value=100.0,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.utcnow()
        )
        monitor.metric_collector.record_metric(metric)
        print(f"  - Metric recorded: {len(monitor.metric_collector.metrics.get('test.metric', []))}")
        
        # Test response time recording
        monitor.metric_collector.record_response_time(150.0)
        print(f"  - Response times recorded: {len(monitor.metric_collector.response_times)}")
        
        # Test metrics evaluation
        metrics = await monitor.evaluate_metrics()
        print(f"  - Metrics evaluated: request_count={metrics.request_count}")
        print(f"  - Throughput: {metrics.throughput_rps} RPS")
        
        return True
    except Exception as e:
        print(f"✗ Monitoring system validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test deployment integration."""
    print_section("4. Deployment Integration Validation")
    
    try:
        from topokit.core.deployment_integration import DeploymentService, get_deployment_service
        from topokit.types.deployment import Deployment, DeploymentConfig, ResourceRequirements, SecurityConfig, MonitoringConfig
        from topokit.core.config import Environment
        from topokit.types.topology import TopologyPack, Node, NodeKind, NodeScope
        
        service = get_deployment_service()
        print(f"✓ DeploymentService created")
        print(f"  - Active deployments: {len(service.active_deployments)}")
        print(f"  - Performance monitor: {service.performance_monitor is not None}")
        print(f"  - Alert manager: {service.alert_manager is not None}")
        
        # Create test deployment
        config = DeploymentConfig(
            environment=Environment.PRODUCTION,
            resources=ResourceRequirements(cpu_cores=4, memory_mb=4096),
            security=SecurityConfig(enable_ssl=True),
            monitoring=MonitoringConfig(enable_metrics=True)
        )
        
        deployment = Deployment(
            id="integration-test",
            name="Integration Test",
            topology_id="test-topology",
            topology_version="1.0.0",
            config=config,
            created_by="test-user"
        )
        
        # Create minimal topology pack
        topology = TopologyPack(
            name="test-topology",
            nodes=[
                Node(id="test-node", kind=NodeKind.DATA, scope=NodeScope())
            ],
            edges=[],
            contracts=[]
        )
        
        print(f"  - Deployment created: {deployment.id}")
        print(f"  - Topology pack: {topology.name}")
        print(f"  - Nodes: {len(topology.nodes)}")
        
        return True
    except Exception as e:
        print(f"✗ Integration validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dashboard_api():
    """Test dashboard API structure."""
    print_section("5. Dashboard API Validation")
    
    try:
        import os
        dashboard_api = os.path.join(
            os.path.dirname(__file__), 
            'packages', 'dashboard', 'src', 'api', 'server.py'
        )
        
        if os.path.exists(dashboard_api):
            print(f"✓ Dashboard API file exists: {dashboard_api}")
            
            # Read and check for key components
            with open(dashboard_api, 'r') as f:
                content = f.read()
                
            checks = {
                "FastAPI app": "app = FastAPI" in content,
                "Health endpoint": "/api/v1/health" in content,
                "Deployments endpoint": "/api/v1/deployments" in content,
                "WebSocket support": "websocket" in content.lower(),
                "Metrics endpoint": "/api/v1/deployments/{deployment_id}/metrics" in content,
            }
            
            for check, result in checks.items():
                status = "✓" if result else "✗"
                print(f"  {status} {check}: {result}")
            
            all_passed = all(checks.values())
            return all_passed
        else:
            print(f"✗ Dashboard API file not found: {dashboard_api}")
            return False
            
    except Exception as e:
        print(f"✗ Dashboard API validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all validations."""
    print("\n" + "="*60)
    print("  Phase 4 Backend Foundation - Validation Test Suite")
    print("="*60)
    
    results = []
    
    # Run all tests
    results.append(("Deployment Model", test_deployment_model()))
    results.append(("Alerting System", await test_alerting_system()))
    results.append(("Monitoring System", await test_monitoring_system()))
    results.append(("Integration", test_integration()))
    results.append(("Dashboard API", test_dashboard_api()))
    
    # Summary
    print_section("Validation Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n  Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All validations passed! Phase 4 backend foundation is working correctly.")
        return 0
    else:
        print(f"\n✗ {total - passed} validation(s) failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

