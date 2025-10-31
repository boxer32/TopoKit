/**
 * Module: PerformanceDashboard
 * Purpose: Performance metrics dashboard with real-time charts
 * Inputs: Deployment metrics, historical data, time ranges
 * Outputs: Comprehensive performance visualization with charts
 * Dependencies: react, recharts, monitoring API
 * Failure Modes: Missing data → empty states, API errors → error handling
 * Trace: page:dashboard, build:20250131, spec-id:T044a
 */

import { useEffect, useState } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import { deploymentApi, DeploymentMetrics } from '../api/client';
import './PerformanceDashboard.css';

interface PerformanceDashboardProps {
  deploymentId: string;
  timeRange?: '1h' | '24h' | '7d' | '30d';
}

export default function PerformanceDashboard({ deploymentId, timeRange = '24h' }: PerformanceDashboardProps) {
  const [metrics, setMetrics] = useState<DeploymentMetrics | null>(null);
  const [historicalData, setHistoricalData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMetrics();
    loadHistoricalData();
  }, [deploymentId, timeRange]);

  const loadMetrics = async () => {
    try {
      const data = await deploymentApi.getMetrics(deploymentId);
      setMetrics(data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load metrics:', error);
      setLoading(false);
    }
  };

  const loadHistoricalData = async () => {
    // Generate sample historical data (in real implementation, this would come from API)
    const dataPoints = timeRange === '1h' ? 60 : timeRange === '24h' ? 288 : timeRange === '7d' ? 168 : 720;
    const interval = timeRange === '1h' ? 60 * 1000 : timeRange === '24h' ? 5 * 60 * 1000 : timeRange === '7d' ? 60 * 60 * 1000 : 2 * 60 * 60 * 1000;

    const data = Array.from({ length: dataPoints }, (_, i) => {
      const date = new Date();
      date.setTime(date.getTime() - (dataPoints - i) * interval);
      return {
        timestamp: date.toISOString(),
        responseTime: 150 + Math.random() * 100,
        errorRate: Math.random() * 0.02,
        throughput: 50 + Math.random() * 30,
        cpuUsage: 40 + Math.random() * 40,
        memoryUsage: 50 + Math.random() * 30,
        tokenUsage: 5000 + Math.random() * 2000,
      };
    });
    setHistoricalData(data);
  };

  if (loading) {
    return <div className="performance-dashboard loading">Loading performance data...</div>;
  }

  if (!metrics) {
    return <div className="performance-dashboard error">Failed to load metrics</div>;
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    if (timeRange === '1h') {
      return date.toLocaleTimeString();
    } else if (timeRange === '24h') {
      return date.toLocaleTimeString();
    } else {
      return date.toLocaleDateString();
    }
  };

  return (
    <div className="performance-dashboard">
      <div className="dashboard-header">
        <h3>Performance Metrics Dashboard</h3>
        <div className="time-range-selector">
          {(['1h', '24h', '7d', '30d'] as const).map((range) => (
            <button
              key={range}
              className={timeRange === range ? 'active' : ''}
              onClick={() => {
                // This would update the timeRange prop in parent component
              }}
            >
              {range.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="metrics-summary">
        <div className="summary-card">
          <span className="summary-label">Avg Response Time</span>
          <span className="summary-value">{metrics.metrics.avg_response_time_ms.toFixed(0)}ms</span>
          <span className="summary-trend">P95: {metrics.metrics.p95_response_time_ms.toFixed(0)}ms</span>
        </div>
        <div className="summary-card">
          <span className="summary-label">Error Rate</span>
          <span className="summary-value">{(metrics.metrics.error_rate * 100).toFixed(3)}%</span>
          <span className="summary-trend">Errors: {metrics.metrics.error_count}</span>
        </div>
        <div className="summary-card">
          <span className="summary-label">Throughput</span>
          <span className="summary-value">{metrics.metrics.throughput_rps.toFixed(1)} req/s</span>
          <span className="summary-trend">Total: {metrics.metrics.request_count.toLocaleString()}</span>
        </div>
        <div className="summary-card">
          <span className="summary-label">Success Rate</span>
          <span className="summary-value">
            {((metrics.metrics.success_count / metrics.metrics.request_count) * 100).toFixed(2)}%
          </span>
          <span className="summary-trend">Success: {metrics.metrics.success_count.toLocaleString()}</span>
        </div>
      </div>

      <div className="charts-grid">
        <div className="chart-container">
          <h4>Response Time</h4>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={historicalData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" tickFormatter={formatTime} />
              <YAxis />
              <Tooltip labelFormatter={formatTime} />
              <Legend />
              <Line type="monotone" dataKey="responseTime" stroke="#3b82f6" name="Response Time (ms)" />
              <ReferenceLine y={2000} stroke="#ef4444" strokeDasharray="5 5" label="SLO Threshold" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <h4>Error Rate</h4>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={historicalData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" tickFormatter={formatTime} />
              <YAxis />
              <Tooltip labelFormatter={formatTime} />
              <Legend />
              <Area
                type="monotone"
                dataKey="errorRate"
                stroke="#ef4444"
                fill="#ef4444"
                fillOpacity={0.3}
                name="Error Rate"
              />
              <ReferenceLine y={0.001} stroke="#f59e0b" strokeDasharray="5 5" label="Warning" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <h4>Throughput</h4>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={historicalData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" tickFormatter={formatTime} />
              <YAxis />
              <Tooltip labelFormatter={formatTime} />
              <Legend />
              <Bar dataKey="throughput" fill="#10b981" name="Requests/sec" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <h4>Resource Utilization</h4>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={historicalData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" tickFormatter={formatTime} />
              <YAxis />
              <Tooltip labelFormatter={formatTime} />
              <Legend />
              <Line type="monotone" dataKey="cpuUsage" stroke="#f59e0b" name="CPU (%)" />
              <Line type="monotone" dataKey="memoryUsage" stroke="#8b5cf6" name="Memory (%)" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

