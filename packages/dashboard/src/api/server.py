"""API server for TopoView dashboard."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional
import asyncio
from datetime import datetime
import json

from topokit.core.deployment_integration import get_deployment_service
from topokit.core.monitoring import get_performance_monitor
from topokit.core.alerting import get_alert_manager
from topokit.types import Deployment, DeploymentStatus


app = FastAPI(title="TopoView Dashboard API", version="1.0.0")

# CORS middleware for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/v1/deployments")
async def get_deployments():
    """Get all deployments."""
    service = get_deployment_service()
    deployments = []
    
    for deployment_id, orchestrator in service.active_deployments.items():
        deployment = orchestrator.deployment
        deployments.append({
            "id": deployment.id,
            "name": deployment.name,
            "status": deployment.status.value,
            "environment": deployment.config.environment,
            "health": {
                "status": deployment.health.status if deployment.health else "unknown",
                "uptime_percentage": deployment.health.uptime_percentage if deployment.health else 0.0,
            } if deployment.health else None,
            "metrics": {
                "request_count": deployment.metrics.request_count if deployment.metrics else 0,
                "error_rate": deployment.metrics.error_rate if deployment.metrics else 0.0,
                "avg_response_time_ms": deployment.metrics.avg_response_time_ms if deployment.metrics else 0.0,
            } if deployment.metrics else None,
        })
    
    return {"deployments": deployments}


@app.get("/api/v1/deployments/{deployment_id}")
async def get_deployment(deployment_id: str):
    """Get deployment details."""
    service = get_deployment_service()
    orchestrator = service.get_production_orchestrator(deployment_id)
    
    if not orchestrator:
        return JSONResponse(
            status_code=404,
            content={"error": f"Deployment {deployment_id} not found"},
        )
    
    deployment = orchestrator.deployment
    
    return {
        "id": deployment.id,
        "name": deployment.name,
        "status": deployment.status.value,
        "environment": deployment.config.environment,
        "topology_id": deployment.topology_id,
        "topology_version": deployment.topology_version,
        "health": {
            "status": deployment.health.status if deployment.health else "unknown",
            "uptime_percentage": deployment.health.uptime_percentage if deployment.health else 0.0,
            "response_time_ms": deployment.health.response_time_ms if deployment.health else 0.0,
            "error_rate": deployment.health.error_rate if deployment.health else 0.0,
            "active_instances": deployment.health.active_instances if deployment.health else 0,
        } if deployment.health else None,
        "metrics": {
            "request_count": deployment.metrics.request_count if deployment.metrics else 0,
            "success_count": deployment.metrics.success_count if deployment.metrics else 0,
            "error_count": deployment.metrics.error_count if deployment.metrics else 0,
            "avg_response_time_ms": deployment.metrics.avg_response_time_ms if deployment.metrics else 0.0,
            "p95_response_time_ms": deployment.metrics.p95_response_time_ms if deployment.metrics else 0.0,
            "p99_response_time_ms": deployment.metrics.p99_response_time_ms if deployment.metrics else 0.0,
            "throughput_rps": deployment.metrics.throughput_rps if deployment.metrics else 0.0,
            "token_usage": deployment.metrics.token_usage if deployment.metrics else 0,
            "cost_usd": deployment.metrics.cost_usd if deployment.metrics else 0.0,
        } if deployment.metrics else None,
    }


@app.get("/api/v1/deployments/{deployment_id}/metrics")
async def get_deployment_metrics(deployment_id: str):
    """Get deployment metrics."""
    service = get_deployment_service()
    orchestrator = service.get_production_orchestrator(deployment_id)
    
    if not orchestrator:
        # Return default metrics instead of 404 for better UX
        return {
            "deployment_id": deployment_id,
            "metrics": {
                "request_count": 0,
                "success_count": 0,
                "error_count": 0,
                "avg_response_time_ms": 0.0,
                "p95_response_time_ms": 0.0,
                "p99_response_time_ms": 0.0,
                "throughput_rps": 0.0,
                "cpu_usage_percent": 0.0,
                "memory_usage_percent": 0.0,
                "token_usage": 0,
                "cost_usd": 0.0,
                "schema_pass_rate": 1.0,
                "error_rate": 0.0,
            },
        }
    
    metrics = service.get_deployment_metrics(deployment_id)
    
    if not metrics:
        # Return default metrics if not available
        return {
            "deployment_id": deployment_id,
            "metrics": {
                "request_count": 0,
                "success_count": 0,
                "error_count": 0,
                "avg_response_time_ms": 0.0,
                "p95_response_time_ms": 0.0,
                "p99_response_time_ms": 0.0,
                "throughput_rps": 0.0,
                "cpu_usage_percent": 0.0,
                "memory_usage_percent": 0.0,
                "token_usage": 0,
                "cost_usd": 0.0,
                "schema_pass_rate": 1.0,
                "error_rate": 0.0,
            },
        }
    
    # Get additional resource metrics if available
    cpu_usage = getattr(metrics, 'cpu_usage_percent', 0.0) if hasattr(metrics, 'cpu_usage_percent') else 0.0
    memory_usage = getattr(metrics, 'memory_usage_percent', 0.0) if hasattr(metrics, 'memory_usage_percent') else 0.0
    
    return {
        "deployment_id": deployment_id,
        "metrics": {
            "request_count": metrics.request_count,
            "success_count": metrics.success_count,
            "error_count": metrics.error_count,
            "avg_response_time_ms": metrics.avg_response_time_ms,
            "p95_response_time_ms": metrics.p95_response_time_ms,
            "p99_response_time_ms": metrics.p99_response_time_ms,
            "throughput_rps": metrics.throughput_rps,
            "cpu_usage_percent": cpu_usage,
            "memory_usage_percent": memory_usage,
            "token_usage": metrics.token_usage,
            "cost_usd": metrics.cost_usd,
            "schema_pass_rate": getattr(metrics, 'schema_pass_rate', 1.0) if hasattr(metrics, 'schema_pass_rate') else 1.0,
            "error_rate": metrics.error_rate,
        },
    }


@app.get("/api/v1/alerts")
async def get_alerts():
    """Get active alerts."""
    alert_manager = get_alert_manager()
    active_alerts = alert_manager.get_active_alerts()
    
    return {
        "alerts": [
            {
                "id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "created_at": alert.created_at.isoformat(),
                "deployment_id": getattr(alert, 'deployment_id', None),
                "node_id": getattr(alert, 'node_id', None),
            }
            for alert in active_alerts
        ],
        "statistics": alert_manager.get_alert_statistics(),
    }


@app.get("/api/v1/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Get trace by ID."""
    monitor = get_performance_monitor()
    trace = monitor.get_trace(trace_id)
    
    if not trace:
        return JSONResponse(
            status_code=404,
            content={"error": f"Trace {trace_id} not found"},
        )
    
    return {
        "trace_id": trace.trace_id,
        "start_time": trace.start_time.isoformat(),
        "end_time": trace.end_time.isoformat() if trace.end_time else None,
        "duration_ms": trace.duration_ms,
        "spans": [
            {
                "span_id": span.span_id,
                "parent_span_id": span.parent_span_id,
                "name": span.name,
                "start_time": span.start_time.isoformat(),
                "end_time": span.end_time.isoformat() if span.end_time else None,
                "duration_ms": span.duration_ms,
                "status": span.status,
                "tags": span.tags,
            }
            for span in trace.spans
        ],
    }


@app.websocket("/ws/metrics/{deployment_id}")
async def websocket_metrics(websocket: WebSocket, deployment_id: str):
    """WebSocket endpoint for real-time metrics."""
    await websocket.accept()
    
    try:
        while True:
            service = get_deployment_service()
            metrics = service.get_deployment_metrics(deployment_id)
            
            if metrics:
                await websocket.send_json({
                    "type": "metrics",
                    "deployment_id": deployment_id,
                    "metrics": {
                        "request_count": metrics.request_count,
                        "success_count": metrics.success_count,
                        "error_count": metrics.error_count,
                        "avg_response_time_ms": metrics.avg_response_time_ms,
                        "p95_response_time_ms": metrics.p95_response_time_ms,
                        "error_rate": metrics.error_rate,
                        "throughput_rps": metrics.throughput_rps,
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                })
            
            await asyncio.sleep(1)  # 1-second refresh rate
            
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """WebSocket endpoint for real-time alerts."""
    await websocket.accept()
    
    try:
        alert_manager = get_alert_manager()
        last_alert_count = 0
        
        while True:
            active_alerts = alert_manager.get_active_alerts()
            current_count = len(active_alerts)
            
            if current_count != last_alert_count:
                await websocket.send_json({
                    "type": "alerts",
                    "alerts": [
                        {
                            "id": alert.id,
                            "title": alert.title,
                            "message": alert.message,
                            "severity": alert.severity.value,
                            "status": alert.status.value,
                            "created_at": alert.created_at.isoformat(),
                            "deployment_id": alert.deployment_id if hasattr(alert, 'deployment_id') else None,
                        }
                        for alert in active_alerts[:10]  # Send top 10
                    ],
                    "statistics": {
                        "active_alerts": current_count,
                        "total_alerts": len(alert_manager.get_all_alerts()) if hasattr(alert_manager, 'get_all_alerts') else current_count,
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                })
                last_alert_count = current_count
            
            await asyncio.sleep(1)  # 1-second refresh rate
            
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/collaboration/{deployment_id}")
async def websocket_collaboration(websocket: WebSocket, deployment_id: str):
    """WebSocket endpoint for real-time collaboration."""
    await websocket.accept()
    
    try:
        # Store user session info (in production, use proper session management)
        user_id = f"user_{datetime.utcnow().timestamp()}"
        user_name = "Anonymous User"
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection",
            "connected": True,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Broadcast user joined
        await websocket.send_json({
            "type": "presence",
            "collaborators": [
                {
                    "id": user_id,
                    "name": user_name,
                    "color": f"#{hash(user_id) % 0xFFFFFF:06x}",
                    "status": "active",
                    "currentView": "dashboard",
                    "lastActivity": datetime.utcnow().isoformat(),
                }
            ],
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        while True:
            # Listen for messages from client
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                
                if data.get("type") == "create_annotation":
                    # Broadcast annotation to all clients (in production, use proper pub/sub)
                    await websocket.send_json({
                        "type": "annotation",
                        "annotation": {
                            "id": data.get("annotation", {}).get("id", f"ann_{datetime.utcnow().timestamp()}"),
                            "userId": user_id,
                            "userName": user_name,
                            "target": data.get("annotation", {}).get("target", "graph"),
                            "targetId": data.get("annotation", {}).get("targetId", ""),
                            "content": data.get("annotation", {}).get("content", ""),
                            "timestamp": datetime.utcnow().isoformat(),
                            "resolved": False,
                        },
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                
                elif data.get("type") == "resolve_annotation":
                    await websocket.send_json({
                        "type": "annotation_resolved",
                        "annotationId": data.get("annotationId"),
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    
            except asyncio.TimeoutError:
                # Keep connection alive
                continue
                
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

