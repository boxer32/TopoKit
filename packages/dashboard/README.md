# TopoView Dashboard

Enterprise-grade real-time monitoring dashboard for TopoKit deployments.

## Overview

TopoView is a web-based dashboard that provides real-time monitoring, alerting, and visualization for TopoKit production deployments. It integrates with the TopoKit core components to provide comprehensive observability.

## Features

- **Real-time Monitoring**: <1s refresh rate for live metrics
- **Interactive Graph Visualization**: Node/edge status with live indicators
- **SLO Compliance Tracking**: Visual heatmaps for performance metrics
- **Circuit Breaker Status**: Real-time monitoring of failure counts
- **Alert Management**: Multi-channel alerting (Slack, Email, Webhook)
- **Cost & Token Tracking**: Budget alerts and usage monitoring
- **Drift Detection**: Statistical anomaly detection with visual indicators
- **Trace Viewer**: Distributed tracing with span visualization
- **Session Replay**: Step-through execution debugging

## Architecture

```
packages/dashboard/
├── src/
│   ├── api/           # FastAPI backend server
│   │   └── server.py  # API endpoints and WebSocket connections
│   └── frontend/      # Frontend application (to be implemented)
├── README.md
└── requirements.txt
```

## API Endpoints

### REST API

- `GET /api/v1/health` - Health check
- `GET /api/v1/deployments` - List all deployments
- `GET /api/v1/deployments/{id}` - Get deployment details
- `GET /api/v1/deployments/{id}/metrics` - Get deployment metrics
- `GET /api/v1/alerts` - Get active alerts
- `GET /api/v1/traces/{id}` - Get trace by ID

### WebSocket

- `WS /ws/metrics/{deployment_id}` - Real-time metrics stream
- `WS /ws/alerts` - Real-time alerts stream

## Getting Started

### Prerequisites

- Python 3.11+
- FastAPI
- Uvicorn

### Installation

```bash
cd packages/dashboard
pip install -r requirements.txt
```

### Running the API Server

```bash
python src/api/server.py
```

The API server will start on `http://localhost:8080`

### Development

```bash
uvicorn src.api.server:app --reload --port 8080
```

## Integration

The dashboard integrates with:

- **Deployment System**: `topokit.core.deployment_integration`
- **Performance Monitoring**: `topokit.core.monitoring`
- **Alert Management**: `topokit.core.alerting`
- **User Story 1 Components**: Orchestrator, Parser, Validator

## Next Steps

The frontend application (React/Vue/etc.) can be implemented to consume these APIs and provide:

- Interactive topology graph visualization
- Real-time charts and metrics
- Alert management interface
- Trace viewer UI
- Session replay interface

