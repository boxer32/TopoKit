/**
 * Module: MetricsOverview
 * Purpose: Display key performance metrics at a glance
 * Inputs: Deployment metrics data
 * Outputs: Metrics cards with key indicators
 */

import { Deployment } from '../api/client';
import './MetricsOverview.css';

interface MetricsOverviewProps {
  deployment: Deployment;
}

export default function MetricsOverview({ deployment }: MetricsOverviewProps) {
  const { metrics, health } = deployment;

  if (!metrics || !health) {
    return null;
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return '#10b981';
      case 'unhealthy':
        return '#ef4444';
      case 'degraded':
        return '#f59e0b';
      default:
        return '#64748b';
    }
  };

  const getSloCompliance = () => {
    if (!metrics || !health) return 'unknown';
    if (health.uptime_percentage >= 99.9 && metrics.error_rate <= 0.001 && metrics.p95_response_time_ms <= 2000) {
      return 'compliant';
    }
    if (health.uptime_percentage >= 99.0 && metrics.error_rate <= 0.01 && metrics.p95_response_time_ms <= 3000) {
      return 'warning';
    }
    return 'critical';
  };

  const sloCompliance = getSloCompliance();

  return (
    <div className="metrics-overview">
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Health Status</span>
            <span
              className="status-badge"
              style={{ backgroundColor: getStatusColor(health.status) }}
            >
              {health.status}
            </span>
          </div>
          <div className="metric-value">{health.uptime_percentage.toFixed(2)}%</div>
          <div className="metric-label">Uptime</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">SLO Compliance</span>
            <span
              className={`compliance-badge ${sloCompliance}`}
            >
              {sloCompliance.toUpperCase()}
            </span>
          </div>
          <div className="metric-value">
            {metrics.schema_pass_rate ? (metrics.schema_pass_rate * 100).toFixed(1) : 'N/A'}%
          </div>
          <div className="metric-label">Schema Pass Rate</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Response Time (P95)</span>
          </div>
          <div className="metric-value">{metrics.p95_response_time_ms.toFixed(0)}ms</div>
          <div className="metric-label">
            {metrics.p95_response_time_ms <= 2000 ? '✓ Within SLO' : '✗ Exceeds SLO'}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Error Rate</span>
          </div>
          <div className="metric-value">{(metrics.error_rate * 100).toFixed(3)}%</div>
          <div className="metric-label">
            {metrics.error_rate <= 0.001 ? '✓ Within SLO' : '✗ Exceeds SLO'}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Throughput</span>
          </div>
          <div className="metric-value">{metrics.throughput_rps.toFixed(1)}</div>
          <div className="metric-label">Requests/Second</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Total Requests</span>
          </div>
          <div className="metric-value">{metrics.request_count.toLocaleString()}</div>
          <div className="metric-label">
            {metrics.success_count.toLocaleString()} successful, {metrics.error_count.toLocaleString()} errors
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Cost</span>
          </div>
          <div className="metric-value">${metrics.cost_usd.toFixed(2)}</div>
          <div className="metric-label">
            {metrics.token_usage.toLocaleString()} tokens
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Active Instances</span>
          </div>
          <div className="metric-value">{health.active_instances}</div>
          <div className="metric-label">Running instances</div>
        </div>
      </div>
    </div>
  );
}

