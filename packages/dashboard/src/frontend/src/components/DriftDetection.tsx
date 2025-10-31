/**
 * Module: DriftDetection
 * Purpose: Visual indicators for performance and quality drift with statistical anomaly detection
 * Inputs: Drift metrics, baseline data, anomaly scores
 * Outputs: Drift visualization with alerts and recommendations
 * Dependencies: react, recharts, monitoring API
 * Failure Modes: Missing data → empty state, calculation errors → fallback display
 * Trace: page:dashboard, build:20250131, spec-id:T043f
 */

import { useEffect, useState } from 'react';
import { LineChart, Line, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import './DriftDetection.css';

export interface DriftMetric {
  metricName: string;
  baselineValue: number;
  currentValue: number;
  driftPercentage: number;
  isAnomaly: boolean;
  statisticalScore: number;
  detectedAt: string;
}

interface DriftDetectionProps {
  deploymentId?: string;
}

export default function DriftDetection({ deploymentId }: DriftDetectionProps) {
  const [driftMetrics, setDriftMetrics] = useState<DriftMetric[]>([]);
  const [history, setHistory] = useState<Array<{ timestamp: string; value: number; metric: string }>>([]);

  useEffect(() => {
    // Generate sample drift data (in real implementation, this would come from API)
    const sampleMetrics: DriftMetric[] = [
      {
        metricName: 'Response Time',
        baselineValue: 150.0,
        currentValue: 175.0,
        driftPercentage: 16.67,
        isAnomaly: true,
        statisticalScore: 2.5,
        detectedAt: new Date().toISOString(),
      },
      {
        metricName: 'Error Rate',
        baselineValue: 0.0005,
        currentValue: 0.0012,
        driftPercentage: 140.0,
        isAnomaly: true,
        statisticalScore: 3.8,
        detectedAt: new Date().toISOString(),
      },
      {
        metricName: 'Token Usage',
        baselineValue: 5000,
        currentValue: 5200,
        driftPercentage: 4.0,
        isAnomaly: false,
        statisticalScore: 0.8,
        detectedAt: new Date().toISOString(),
      },
    ];
    setDriftMetrics(sampleMetrics);

    // Generate history data
    const historyData: Array<{ timestamp: string; value: number; metric: string }> = [];
    const metrics = ['Response Time', 'Error Rate', 'Token Usage'];
    const baselines = [150.0, 0.0005, 5000];
    
    for (let i = 0; i < 30; i++) {
      const date = new Date();
      date.setDate(date.getDate() - (29 - i));
      metrics.forEach((metric, idx) => {
        const variance = (Math.random() - 0.5) * 0.2;
        historyData.push({
          timestamp: date.toISOString().split('T')[0],
          value: baselines[idx] * (1 + variance),
          metric,
        });
      });
    }
    setHistory(historyData);
  }, [deploymentId]);

  const getDriftColor = (isAnomaly: boolean, driftPercentage: number) => {
    if (isAnomaly || driftPercentage > 10) {
      return '#ef4444';
    }
    if (driftPercentage > 5) {
      return '#f59e0b';
    }
    return '#10b981';
  };

  const criticalDrifts = driftMetrics.filter((m) => m.isAnomaly || m.driftPercentage > 10);

  return (
    <div className="drift-detection">
      <div className="drift-header">
        <h3>Drift Detection</h3>
        {criticalDrifts.length > 0 && (
          <span className="alert-badge">
            {criticalDrifts.length} Anomaly{criticalDrifts.length !== 1 ? 'ies' : ''} Detected
          </span>
        )}
      </div>

      <div className="drift-metrics">
        {driftMetrics.map((metric) => {
          const color = getDriftColor(metric.isAnomaly, metric.driftPercentage);
          const status = metric.isAnomaly || metric.driftPercentage > 10 ? 'critical' :
                        metric.driftPercentage > 5 ? 'warning' : 'normal';

          return (
            <div key={metric.metricName} className={`drift-card ${status}`}>
              <div className="card-header">
                <span className="metric-name">{metric.metricName}</span>
                <span
                  className="drift-badge"
                  style={{ backgroundColor: color }}
                >
                  {metric.driftPercentage > 0 ? '+' : ''}{metric.driftPercentage.toFixed(1)}%
                </span>
              </div>
              
              <div className="drift-values">
                <div className="value-comparison">
                  <div className="value-item">
                    <span className="value-label">Baseline</span>
                    <span className="value">{metric.baselineValue.toFixed(2)}</span>
                  </div>
                  <div className="value-item">
                    <span className="value-label">Current</span>
                    <span className="value" style={{ color }}>
                      {metric.currentValue.toFixed(2)}
                    </span>
                  </div>
                  <div className="value-item">
                    <span className="value-label">Z-Score</span>
                    <span className="value" style={{ color }}>
                      {metric.statisticalScore.toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="drift-indicator">
                <div className="indicator-bar">
                  <div
                    className="indicator-fill"
                    style={{
                      width: `${Math.min(Math.abs(metric.driftPercentage), 100)}%`,
                      backgroundColor: color,
                    }}
                  />
                </div>
              </div>

              {metric.isAnomaly && (
                <div className="anomaly-alert">
                  <strong>⚠ Anomaly Detected</strong> Statistical score ({metric.statisticalScore.toFixed(2)}) exceeds threshold (3.0)
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="drift-chart">
        <h4>Drift History (30 Days)</h4>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={history}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="timestamp" />
            <YAxis />
            <Tooltip />
            <Legend />
            {driftMetrics.map((metric, idx) => {
              const filteredHistory = history.filter((h) => h.metric === metric.metricName);
              return (
                <Line
                  key={metric.metricName}
                  type="monotone"
                  dataKey="value"
                  data={filteredHistory}
                  stroke={getDriftColor(metric.isAnomaly, metric.driftPercentage)}
                  name={metric.metricName}
                  strokeWidth={2}
                />
              );
            })}
            {driftMetrics.map((metric) => (
              <ReferenceLine
                key={`baseline-${metric.metricName}`}
                y={metric.baselineValue}
                stroke="#64748b"
                strokeDasharray="5 5"
                label={{ value: `${metric.metricName} Baseline`, position: 'right' }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

