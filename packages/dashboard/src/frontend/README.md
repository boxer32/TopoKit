# TopoView Dashboard Frontend

React + TypeScript frontend for TopoView Dashboard providing real-time monitoring and visualization.

## Features

- ✅ **Interactive Topology Graph** - Cytoscape-based graph visualization with live status indicators
- ✅ **SLO Compliance Heatmap** - Visual representation of performance metrics
- ✅ **Circuit Breaker Status** - Real-time monitoring of failure counts and recovery states
- ✅ **Real-time Metrics** - WebSocket-based live updates (<1s refresh rate)
- ✅ **Alert Management** - Multi-channel alert viewing and management
- ✅ **Trace Viewer** - Distributed tracing visualization
- ✅ **Metrics Overview** - Key performance indicators at a glance

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Cytoscape** - Graph visualization
- **Recharts** - Charting library
- **Zustand** - State management
- **Axios** - HTTP client
- **React Router** - Routing

## Getting Started

### Prerequisites

- Node.js 18+
- npm or pnpm

### Installation

```bash
cd packages/dashboard/src/frontend
npm install
# or
pnpm install
```

### Development

```bash
npm run dev
# or
pnpm dev
```

The dashboard will be available at `http://localhost:3000`

### Build

```bash
npm run build
# or
pnpm build
```

## Project Structure

```
src/
├── api/
│   └── client.ts          # API client and WebSocket
├── components/
│   ├── DashboardLayout.tsx
│   ├── TopologyGraph.tsx  # Interactive graph (T043a)
│   ├── SLOHeatmap.tsx     # SLO compliance (T043b)
│   ├── CircuitBreakerStatus.tsx  # Circuit breakers (T043c)
│   └── MetricsOverview.tsx
├── pages/
│   ├── DashboardHome.tsx
│   ├── DeploymentDetail.tsx
│   ├── AlertsPage.tsx
│   └── TracesPage.tsx
├── App.tsx
└── main.tsx
```

## API Integration

The frontend connects to the FastAPI backend server running on `http://localhost:8080`:

- REST API: `/api/v1/*`
- WebSocket: `/ws/metrics/{deployment_id}` and `/ws/alerts`

## Features Implemented

### T043a - Interactive Node/Edge Graph ✅
- Live status indicators (running, completed, failed, pending)
- SLO compliance visualization (compliant, warning, critical)
- Circuit breaker state indicators
- Node type visualization (UX, AI, Data, Ops)
- Interactive filtering and drill-down

### T043b - SLO Compliance Heatmap ✅
- Visual heatmap with color coding
- Compliance scoring per node
- Metric thresholds tracking
- Performance metrics display

### T043c - Circuit Breaker Status ✅
- Real-time circuit breaker state monitoring
- Failure count tracking
- Recovery state visualization
- Multi-level breakers (node, edge, domain, system)

## Next Steps

Additional features to implement:
- T043d: Human gate approval queue management interface
- T043e: Cost & token usage tracking with budget alerts
- T043f: Drift detection alerts with visual indicators
- T043g: Interactive filtering and drill-down analysis
- T043h: Export capabilities (PNG, SVG, Mermaid, HTML)
- T043i: Real-time collaboration features

