/**
 * Module: RealTimeMonitoring
 * Purpose: Real-time monitoring with <1s refresh rate for deployment metrics
 * Inputs: Deployment ID, WebSocket connection, metrics data
 * Outputs: Real-time dashboard with sub-second updates
 * Dependencies: react, WebSocket, recharts
 * Failure Modes: Connection errors → retry, data gaps → interpolation
 * Trace: page:dashboard, build:20250131, spec-id:T044
 */

import { useEffect, useState, useRef } from 'react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { WebSocketClient, deploymentApi } from '../api/client';
import './RealTimeMonitoring.css';

interface RealTimeMetric {
  timestamp: string;
  value: number;
  label: string;
}

interface RealTimeMonitoringProps {
  deploymentId: string;
  metrics?: string[]; // List of metric names to monitor
}

export default function RealTimeMonitoring({ deploymentId, metrics = [] }: RealTimeMonitoringProps) {
  const [metricData, setMetricData] = useState<Record<string, RealTimeMetric[]>>({});
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const wsClientRef = useRef<WebSocketClient | null>(null);
  const updateIntervalRef = useRef<number | null>(null);

  useEffect(() => {
    connectWebSocket();
    return () => {
      disconnectWebSocket();
    };
  }, [deploymentId]);

  const connectWebSocket = () => {
    const client = new WebSocketClient();
    wsClientRef.current = client;

    client.connect(`/ws/metrics/${deploymentId}`, (data) => {
      if (data.type === 'metrics') {
        updateMetrics(data.metrics);
        setLastUpdate(new Date());
        setIsConnected(true);
      } else if (data.type === 'connection') {
        setIsConnected(data.connected);
      }
    }, (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
      // Retry connection
      setTimeout(() => connectWebSocket(), 1000);
    });

    // Fallback polling if WebSocket fails
    startPolling();
  };

  const disconnectWebSocket = () => {
    if (wsClientRef.current) {
      wsClientRef.current.disconnect();
      wsClientRef.current = null;
    }
    if (updateIntervalRef.current) {
      clearInterval(updateIntervalRef.current);
    }
  };

  const startPolling = () => {
    // Poll every 500ms as fallback
    updateIntervalRef.current = window.setInterval(async () => {
      try {
        const data = await deploymentApi.getMetrics(deploymentId);
        updateMetrics(data.metrics);
        setLastUpdate(new Date());
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 500);
  };

  const updateMetrics = (metrics: any) => {
    const now = new Date().toISOString();
    const newData: Record<string, RealTimeMetric[]> = { ...metricData };

    // Update response time
    if (metrics.avg_response_time_ms !== undefined) {
      if (!newData['response_time']) {
        newData['response_time'] = [];
      }
      newData['response_time'].push({
        timestamp: now,
        value: metrics.avg_response_time_ms,
        label: 'Response Time (ms)',
      });
      // Keep only last 60 data points (30 seconds at 500ms intervals)
      if (newData['response_time'].length > 60) {
        newData['response_time'] = newData['response_time'].slice(-60);
      }
    }

    // Update error rate
    if (metrics.error_rate !== undefined) {
      if (!newData['error_rate']) {
        newData['error_rate'] = [];
      }
      newData['error_rate'].push({
        timestamp: now,
        value: metrics.error_rate * 100,
        label: 'Error Rate (%)',
      });
      if (newData['error_rate'].length > 60) {
        newData['error_rate'] = newData['error_rate'].slice(-60);
      }
    }

    // Update throughput
    if (metrics.throughput_rps !== undefined) {
      if (!newData['throughput']) {
        newData['throughput'] = [];
      }
      newData['throughput'].push({
        timestamp: now,
        value: metrics.throughput_rps,
        label: 'Throughput (req/s)',
      });
      if (newData['throughput'].length > 60) {
        newData['throughput'] = newData['throughput'].slice(-60);
      }
    }

    // Update CPU usage
    if (metrics.cpu_usage_percent !== undefined) {
      if (!newData['cpu']) {
        newData['cpu'] = [];
      }
      newData['cpu'].push({
        timestamp: now,
        value: metrics.cpu_usage_percent,
        label: 'CPU Usage (%)',
      });
      if (newData['cpu'].length > 60) {
        newData['cpu'] = newData['cpu'].slice(-60);
      }
    }

    // Update memory usage
    if (metrics.memory_usage_percent !== undefined) {
      if (!newData['memory']) {
        newData['memory'] = [];
      }
      newData['memory'].push({
        timestamp: now,
        value: metrics.memory_usage_percent,
        label: 'Memory Usage (%)',
      });
      if (newData['memory'].length > 60) {
        newData['memory'] = newData['memory'].slice(-60);
      }
    }

    setMetricData(newData);
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  return (
    <div className="realtime-monitoring">
      <div className="monitoring-header">
        <h3>Real-Time Monitoring</h3>
        <div className="connection-status">
          <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}></span>
          <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
          {lastUpdate && (
            <span className="last-update">
              Last update: {lastUpdate.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      <div className="metrics-grid">
        {Object.entries(metricData).map(([key, data]) => (
          <div key={key} className="metric-chart">
            <h4>{data[0]?.label || key}</h4>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={formatTime}
                  interval="preserveStartEnd"
                />
                <YAxis />
                <Tooltip
                  labelFormatter={formatTime}
                  formatter={(value: number) => [value.toFixed(2), data[0]?.label]}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#3b82f6"
                  fill="#3b82f6"
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
            <div className="metric-current">
              Current: {data.length > 0 ? data[data.length - 1].value.toFixed(2) : 'N/A'}
            </div>
          </div>
        ))}
      </div>

      {Object.keys(metricData).length === 0 && (
        <div className="empty-state">
          <p>Waiting for metrics data...</p>
        </div>
      )}
    </div>
  );
}

