/**
 * Module: SLOHeatmap
 * Purpose: Visual representation of SLO compliance with performance metrics
 * Inputs: Deployment metrics, SLO thresholds, node performance data
 * Outputs: Heatmap visualization (green/yellow/red) for compliance status
 * Dependencies: react, recharts, deployment API
 * Failure Modes: Missing data → empty state, calculation errors → fallback display
 * Trace: page:dashboard, build:20250131, spec-id:T043b
 */

import { useMemo } from 'react';
import './SLOHeatmap.css';

export interface SLOMetric {
  nodeId: string;
  nodeName: string;
  metricName: string;
  currentValue: number;
  threshold: number;
  compliance: 'compliant' | 'warning' | 'critical';
}

interface SLOHeatmapProps {
  metrics: SLOMetric[];
  onNodeClick?: (nodeId: string) => void;
}

export default function SLOHeatmap({ metrics, onNodeClick }: SLOHeatmapProps) {
  const groupedMetrics = useMemo(() => {
    const grouped = new Map<string, SLOMetric[]>();
    metrics.forEach((metric) => {
      if (!grouped.has(metric.nodeId)) {
        grouped.set(metric.nodeId, []);
      }
      grouped.get(metric.nodeId)!.push(metric);
    });
    return Array.from(grouped.entries());
  }, [metrics]);

  const getComplianceColor = (compliance: string) => {
    switch (compliance) {
      case 'compliant':
        return '#10b981';
      case 'warning':
        return '#f59e0b';
      case 'critical':
        return '#ef4444';
      default:
        return '#64748b';
    }
  };

  const getComplianceScore = (nodeMetrics: SLOMetric[]): number => {
    const total = nodeMetrics.length;
    const compliant = nodeMetrics.filter((m) => m.compliance === 'compliant').length;
    return total > 0 ? (compliant / total) * 100 : 0;
  };

  return (
    <div className="slo-heatmap">
      <div className="heatmap-header">
        <h3>SLO Compliance Heatmap</h3>
        <div className="compliance-legend">
          <span className="legend-item">
            <span className="color-dot compliant"></span>
            Compliant
          </span>
          <span className="legend-item">
            <span className="color-dot warning"></span>
            Warning
          </span>
          <span className="legend-item">
            <span className="color-dot critical"></span>
            Critical
          </span>
        </div>
      </div>

      <div className="heatmap-grid">
        {groupedMetrics.map(([nodeId, nodeMetrics]) => {
          const score = getComplianceScore(nodeMetrics);
          const overallCompliance = 
            score === 100 ? 'compliant' :
            score >= 70 ? 'warning' : 'critical';

          return (
            <div
              key={nodeId}
              className={`heatmap-cell ${overallCompliance}`}
              onClick={() => onNodeClick?.(nodeId)}
              style={{ '--compliance-color': getComplianceColor(overallCompliance) } as React.CSSProperties}
            >
              <div className="cell-header">
                <span className="node-name">{nodeMetrics[0].nodeName}</span>
                <span className="compliance-score">{score.toFixed(0)}%</span>
              </div>
              <div className="cell-metrics">
                {nodeMetrics.map((metric) => (
                  <div key={metric.metricName} className="metric-item">
                    <span className="metric-name">{metric.metricName}</span>
                    <span className={`metric-status ${metric.compliance}`}>
                      {metric.currentValue.toFixed(2)} / {metric.threshold.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {metrics.length === 0 && (
        <div className="empty-state">
          <p>No SLO metrics available</p>
        </div>
      )}
    </div>
  );
}

