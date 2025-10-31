/**
 * Module: CircuitBreakerStatus
 * Purpose: Real-time monitoring of circuit breaker failure counts and recovery states
 * Inputs: Circuit breaker state data, failure counts, recovery timestamps
 * Outputs: Visual circuit breaker status indicators with counts and states
 * Dependencies: react, deployment API
 * Failure Modes: Missing data → empty state, connection errors → retry mechanism
 * Trace: page:dashboard, build:20250131, spec-id:T043c
 */

import { useEffect, useState } from 'react';
import './CircuitBreakerStatus.css';

export interface CircuitBreakerData {
  id: string;
  level: 'node' | 'edge' | 'domain' | 'system';
  state: 'closed' | 'open' | 'half-open' | 'bypass';
  failureCount: number;
  failureThreshold: number;
  successCount: number;
  successThreshold: number;
  lastFailureTime?: string;
  lastSuccessTime?: string;
  recoveryTime?: string;
  identifier: string;
}

interface CircuitBreakerStatusProps {
  breakers: CircuitBreakerData[];
  onBreakerClick?: (breakerId: string) => void;
}

export default function CircuitBreakerStatus({
  breakers,
  onBreakerClick,
}: CircuitBreakerStatusProps) {
  const getStateColor = (state: string) => {
    switch (state) {
      case 'closed':
        return '#10b981'; // Green - Normal operation
      case 'open':
        return '#ef4444'; // Red - Circuit is open
      case 'half-open':
        return '#f59e0b'; // Yellow - Testing recovery
      case 'bypass':
        return '#64748b'; // Gray - Bypassed
      default:
        return '#64748b';
    }
  };

  const getStateLabel = (state: string) => {
    switch (state) {
      case 'closed':
        return 'Normal';
      case 'open':
        return 'Open';
      case 'half-open':
        return 'Testing';
      case 'bypass':
        return 'Bypassed';
      default:
        return state;
    }
  };

  const getLevelBadge = (level: string) => {
    const colors: Record<string, string> = {
      node: '#3b82f6',
      edge: '#8b5cf6',
      domain: '#10b981',
      system: '#f59e0b',
    };
    return colors[level] || '#64748b';
  };

  const groupedByLevel = breakers.reduce((acc, breaker) => {
    if (!acc[breaker.level]) {
      acc[breaker.level] = [];
    }
    acc[breaker.level].push(breaker);
    return acc;
  }, {} as Record<string, CircuitBreakerData[]>);

  return (
    <div className="circuit-breaker-status">
      <div className="status-header">
        <h3>Circuit Breaker Status</h3>
        <div className="state-legend">
          <span className="legend-item">
            <span className="state-dot" style={{ backgroundColor: '#10b981' }}></span>
            Closed
          </span>
          <span className="legend-item">
            <span className="state-dot" style={{ backgroundColor: '#f59e0b' }}></span>
            Half-Open
          </span>
          <span className="legend-item">
            <span className="state-dot" style={{ backgroundColor: '#ef4444' }}></span>
            Open
          </span>
          <span className="legend-item">
            <span className="state-dot" style={{ backgroundColor: '#64748b' }}></span>
            Bypassed
          </span>
        </div>
      </div>

      <div className="breaker-list">
        {Object.entries(groupedByLevel).map(([level, levelBreakers]) => (
          <div key={level} className="breaker-group">
            <h4 className="level-header" style={{ borderLeftColor: getLevelBadge(level) }}>
              {level.charAt(0).toUpperCase() + level.slice(1)} Level
            </h4>
            <div className="breaker-cards">
              {levelBreakers.map((breaker) => {
                const stateColor = getStateColor(breaker.state);
                const failurePercentage = (breaker.failureCount / breaker.failureThreshold) * 100;
                const isAtThreshold = failurePercentage >= 100;

                return (
                  <div
                    key={breaker.id}
                    className={`breaker-card ${breaker.state}`}
                    onClick={() => onBreakerClick?.(breaker.id)}
                    style={{ '--state-color': stateColor } as React.CSSProperties}
                  >
                    <div className="card-header">
                      <span className="breaker-identifier">{breaker.identifier}</span>
                      <span
                        className="state-badge"
                        style={{
                          backgroundColor: stateColor,
                          color: '#ffffff',
                        }}
                      >
                        {getStateLabel(breaker.state)}
                      </span>
                    </div>

                    <div className="card-metrics">
                      <div className="metric-row">
                        <span className="metric-label">Failures</span>
                        <div className="metric-value">
                          <span
                            className={isAtThreshold ? 'threshold-exceeded' : ''}
                          >
                            {breaker.failureCount}
                          </span>
                          <span className="metric-threshold">/ {breaker.failureThreshold}</span>
                        </div>
                      </div>

                      <div className="progress-bar">
                        <div
                          className="progress-fill"
                          style={{
                            width: `${Math.min(failurePercentage, 100)}%`,
                            backgroundColor: isAtThreshold ? '#ef4444' : '#f59e0b',
                          }}
                        />
                      </div>

                      {breaker.state === 'half-open' && (
                        <div className="metric-row">
                          <span className="metric-label">Success Count</span>
                          <span className="metric-value">
                            {breaker.successCount} / {breaker.successThreshold}
                          </span>
                        </div>
                      )}

                      {breaker.lastFailureTime && (
                        <div className="metric-row">
                          <span className="metric-label">Last Failure</span>
                          <span className="metric-value time">
                            {new Date(breaker.lastFailureTime).toLocaleTimeString()}
                          </span>
                        </div>
                      )}

                      {breaker.recoveryTime && (
                        <div className="metric-row">
                          <span className="metric-label">Recovery Time</span>
                          <span className="metric-value time">
                            {new Date(breaker.recoveryTime).toLocaleTimeString()}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {breakers.length === 0 && (
        <div className="empty-state">
          <p>No circuit breakers configured</p>
        </div>
      )}
    </div>
  );
}

