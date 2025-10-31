/**
 * Module: DashboardHome
 * Purpose: Main dashboard page with topology graph, SLO heatmap, and metrics overview
 * Inputs: Deployment data, metrics, alerts
 * Outputs: Dashboard home page with real-time visualizations
 * Dependencies: TopologyGraph, SLOHeatmap, CircuitBreakerStatus, API client
 * Failure Modes: API errors → error state, missing data → empty states
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import TopologyGraph, { NodeData, EdgeData } from '../components/TopologyGraph';
import SLOHeatmap, { SLOMetric } from '../components/SLOHeatmap';
import CircuitBreakerStatus, { CircuitBreakerData } from '../components/CircuitBreakerStatus';
import MetricsOverview from '../components/MetricsOverview';
import HumanGateQueue from '../components/HumanGateQueue';
import CostTracking from '../components/CostTracking';
import DriftDetection from '../components/DriftDetection';
import GraphFilters, { FilterCriteria } from '../components/GraphFilters';
import ExportTools from '../components/ExportTools';
import Collaboration from '../components/Collaboration';
import RealTimeMonitoring from '../monitoring/RealTimeMonitoring';
import PerformanceDashboard from '../components/PerformanceDashboard';
import ExecutionTimeline from '../components/ExecutionTimeline';
import ResourceUtilization from '../components/ResourceUtilization';
import CostQualityTrends from '../components/CostQualityTrends';
import { deploymentApi, Deployment, WebSocketClient } from '../api/client';
import './DashboardHome.css';

export default function DashboardHome() {
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [selectedDeployment, setSelectedDeployment] = useState<Deployment | null>(null);
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [edges, setEdges] = useState<EdgeData[]>([]);
  const [sloMetrics, setSloMetrics] = useState<SLOMetric[]>([]);
  const [circuitBreakers, setCircuitBreakers] = useState<CircuitBreakerData[]>([]);
  const [filters, setFilters] = useState<FilterCriteria>({
    nodeType: 'all',
    status: 'all',
    sloCompliance: 'all',
    timeRange: 'last_day',
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const wsClientRef = useState(() => new WebSocketClient());

  useEffect(() => {
    loadDeployments();
  }, []);

  useEffect(() => {
    if (selectedDeployment) {
      loadDeploymentDetails(selectedDeployment.id);
      connectWebSocket(selectedDeployment.id);
    }
    return () => {
      wsClientRef[0].disconnect();
    };
  }, [selectedDeployment]);

  const loadDeployments = async () => {
    try {
      setLoading(true);
      const data = await deploymentApi.getAll();
      setDeployments(data.deployments);
      if (data.deployments.length > 0) {
        setSelectedDeployment(data.deployments[0]);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load deployments');
    } finally {
      setLoading(false);
    }
  };

  const loadDeploymentDetails = async (deploymentId: string) => {
    try {
      const deployment = await deploymentApi.getById(deploymentId);
      setSelectedDeployment(deployment);

      // Generate sample topology data (in real implementation, this comes from topology pack)
      const sampleNodes: NodeData[] = [
        {
          id: 'node-1',
          label: 'Data.Retrieval',
          kind: 'data',
          status: 'running',
          sloCompliance: 'compliant',
          circuitBreaker: 'closed',
          confidenceScore: 0.95,
        },
        {
          id: 'node-2',
          label: 'AI.Answer',
          kind: 'ai',
          status: 'running',
          sloCompliance: 'warning',
          circuitBreaker: 'half-open',
          confidenceScore: 0.78,
        },
      ];

      const sampleEdges: EdgeData[] = [
        {
          id: 'edge-1',
          source: 'node-1',
          target: 'node-2',
          status: 'active',
          latency: 150,
          errorRate: 0.001,
          dataFlowVolume: 'medium',
        },
      ];

      setNodes(sampleNodes);
      setEdges(sampleEdges);

      // Generate SLO metrics
      const metrics = await deploymentApi.getMetrics(deploymentId);
      const sloMetricsData: SLOMetric[] = [
        {
          nodeId: 'node-1',
          nodeName: 'Data.Retrieval',
          metricName: 'Response Time',
          currentValue: metrics.metrics.avg_response_time_ms,
          threshold: 1000,
          compliance: metrics.metrics.avg_response_time_ms <= 1000 ? 'compliant' : 'warning',
        },
        {
          nodeId: 'node-1',
          nodeName: 'Data.Retrieval',
          metricName: 'Error Rate',
          currentValue: metrics.metrics.error_rate,
          threshold: 0.001,
          compliance: metrics.metrics.error_rate <= 0.001 ? 'compliant' : 'critical',
        },
        {
          nodeId: 'node-2',
          nodeName: 'AI.Answer',
          metricName: 'Response Time',
          currentValue: metrics.metrics.p95_response_time_ms,
          threshold: 2000,
          compliance: metrics.metrics.p95_response_time_ms <= 2000 ? 'compliant' : 'warning',
        },
      ];
      setSloMetrics(sloMetricsData);

      // Generate circuit breaker data
      const breakerData: CircuitBreakerData[] = [
        {
          id: 'cb-1',
          level: 'node',
          state: 'closed',
          failureCount: 0,
          failureThreshold: 3,
          successCount: 0,
          successThreshold: 3,
          identifier: 'node-1',
        },
        {
          id: 'cb-2',
          level: 'node',
          state: 'half-open',
          failureCount: 2,
          failureThreshold: 3,
          successCount: 1,
          successThreshold: 3,
          identifier: 'node-2',
          lastFailureTime: new Date().toISOString(),
        },
      ];
      setCircuitBreakers(breakerData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load deployment details');
    }
  };

  const connectWebSocket = (deploymentId: string) => {
    wsClientRef[0].disconnect();
    wsClientRef[0].connect(
      `/ws/metrics/${deploymentId}`,
      (data) => {
        if (data.type === 'metrics' && selectedDeployment) {
          // Update deployment metrics in real-time
          loadDeploymentDetails(deploymentId);
        }
      }
    );
  };

  if (loading) {
    return (
      <div className="dashboard-home loading">
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-home error">
        <p>Error: {error}</p>
        <button onClick={loadDeployments}>Retry</button>
      </div>
    );
  }

  return (
    <div className="dashboard-home">
      <div className="dashboard-header-section">
        <h1>TopoView Dashboard</h1>
        {selectedDeployment && (
          <div className="deployment-selector">
            <label>Deployment:</label>
            <select
              value={selectedDeployment.id}
              onChange={(e) => {
                const deployment = deployments.find((d) => d.id === e.target.value);
                if (deployment) setSelectedDeployment(deployment);
              }}
            >
              {deployments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.environment})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {selectedDeployment && (
        <>
          <MetricsOverview deployment={selectedDeployment} />

          <GraphFilters
            onFilterChange={(newFilters) => {
              setFilters(newFilters);
              // Apply filters to graph data
            }}
            onReset={() => {
              setFilters({
                nodeType: 'all',
                status: 'all',
                sloCompliance: 'all',
                timeRange: 'last_day',
              });
            }}
          />

          <ExportTools
            onExport={(format) => {
              console.log('Exporting as', format);
              // In real implementation, this would trigger export
            }}
            graphData={{ nodes, edges }}
            metricsData={selectedDeployment}
          />

          <div className="dashboard-grid">
            <div className="grid-item graph-section">
              <h2>Topology Graph</h2>
              <TopologyGraph
                nodes={nodes}
                edges={edges}
                onNodeClick={(nodeId) => {
                  console.log('Node clicked:', nodeId);
                }}
                onEdgeClick={(edgeId) => {
                  console.log('Edge clicked:', edgeId);
                }}
              />
            </div>

            <div className="grid-item slo-section">
              <SLOHeatmap
                metrics={sloMetrics}
                onNodeClick={(nodeId) => {
                  console.log('SLO node clicked:', nodeId);
                }}
              />
            </div>

            <div className="grid-item circuit-breaker-section">
              <CircuitBreakerStatus
                breakers={circuitBreakers}
                onBreakerClick={(breakerId) => {
                  console.log('Circuit breaker clicked:', breakerId);
                }}
              />
            </div>

            <div className="grid-item cost-section">
              <CostTracking deploymentId={selectedDeployment.id} />
            </div>

            <div className="grid-item drift-section">
              <DriftDetection deploymentId={selectedDeployment.id} />
            </div>

            <div className="grid-item gate-section">
              <HumanGateQueue deploymentId={selectedDeployment.id} />
            </div>

            <div className="grid-item collaboration-section">
              <Collaboration deploymentId={selectedDeployment.id} />
            </div>

            <div className="grid-item realtime-section">
              <RealTimeMonitoring deploymentId={selectedDeployment.id} />
            </div>

            <div className="grid-item performance-section">
              <PerformanceDashboard deploymentId={selectedDeployment.id} />
            </div>

            <div className="grid-item timeline-section">
              <ExecutionTimeline deploymentId={selectedDeployment.id} />
            </div>

            <div className="grid-item resource-section">
              <ResourceUtilization deploymentId={selectedDeployment.id} />
            </div>

            <div className="grid-item trends-section">
              <CostQualityTrends deploymentId={selectedDeployment.id} />
            </div>
          </div>
        </>
      )}

      {!selectedDeployment && (
        <div className="empty-state">
          <p>No deployments available</p>
          <Link to="/">Create your first deployment</Link>
        </div>
      )}
    </div>
  );
}

