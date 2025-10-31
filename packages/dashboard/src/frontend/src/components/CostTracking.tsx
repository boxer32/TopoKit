/**
 * Module: CostTracking
 * Purpose: Real-time cost monitoring and budget alerts for token usage
 * Inputs: Cost data, token usage, budget thresholds
 * Outputs: Cost visualization with budget alerts and optimization recommendations
 * Dependencies: react, recharts, deployment API
 * Failure Modes: Missing data → empty state, API errors → error handling
 * Trace: page:dashboard, build:20250131, spec-id:T043e
 */

import { useEffect, useState } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { deploymentApi, DeploymentMetrics, WebSocketClient } from '../api/client';
import './CostTracking.css';

interface CostTrackingProps {
  deploymentId: string;
}

interface CostData {
  timestamp: string;
  cost: number;
  tokens: number;
  requests: number;
}

export default function CostTracking({ deploymentId }: CostTrackingProps) {
  const [metrics, setMetrics] = useState<DeploymentMetrics | null>(null);
  const [costHistory, setCostHistory] = useState<CostData[]>([]);
  const [budget, setBudget] = useState(100.0);
  const [budgetThreshold, setBudgetThreshold] = useState(80.0);
  const wsClientRef = useState(() => new WebSocketClient());

  useEffect(() => {
    loadMetrics();
    connectWebSocket();
    return () => {
      wsClientRef[0].disconnect();
    };
  }, [deploymentId]);

  const loadMetrics = async () => {
    try {
      const data = await deploymentApi.getMetrics(deploymentId);
      setMetrics(data);
      
      // Generate sample cost history (in real implementation, this would come from API)
      const history: CostData[] = Array.from({ length: 30 }, (_, i) => {
        const date = new Date();
        date.setDate(date.getDate() - (29 - i));
        return {
          timestamp: date.toISOString().split('T')[0],
          cost: data.metrics.cost_usd * (0.8 + Math.random() * 0.4),
          tokens: data.metrics.token_usage * (0.8 + Math.random() * 0.4),
          requests: data.metrics.request_count * (0.8 + Math.random() * 0.4),
        };
      });
      setCostHistory(history);
    } catch (err) {
      console.error('Failed to load metrics:', err);
    }
  };

  const connectWebSocket = () => {
    wsClientRef[0].connect(`/ws/metrics/${deploymentId}`, (data) => {
      if (data.type === 'metrics') {
        loadMetrics();
      }
    });
  };

  const currentCost = metrics?.metrics.cost_usd || 0;
  const budgetUsage = (currentCost / budget) * 100;
  const isOverBudget = budgetUsage > 100;
  const isNearBudget = budgetUsage > budgetThreshold && budgetUsage <= 100;
  const costPerRequest = metrics ? metrics.metrics.cost_usd / Math.max(metrics.metrics.request_count, 1) : 0;

  return (
    <div className="cost-tracking">
      <div className="cost-header">
        <h3>Cost & Token Usage Tracking</h3>
        <div className="budget-controls">
          <label>
            Budget: $
            <input
              type="number"
              value={budget}
              onChange={(e) => setBudget(parseFloat(e.target.value) || 0)}
              step="10"
              min="0"
            />
          </label>
          <label>
            Alert Threshold: %
            <input
              type="number"
              value={budgetThreshold}
              onChange={(e) => setBudgetThreshold(parseFloat(e.target.value) || 0)}
              step="5"
              min="0"
              max="100"
            />
          </label>
        </div>
      </div>

      <div className="cost-overview">
        <div className={`cost-card ${isOverBudget ? 'over-budget' : isNearBudget ? 'near-budget' : 'within-budget'}`}>
          <div className="card-header">
            <span className="card-title">Current Cost</span>
            <span className={`budget-status ${isOverBudget ? 'over' : isNearBudget ? 'warning' : 'ok'}`}>
              {isOverBudget ? '⚠ Over Budget' : isNearBudget ? '⚠ Near Budget' : '✓ Within Budget'}
            </span>
          </div>
          <div className="cost-value">${currentCost.toFixed(2)}</div>
          <div className="cost-details">
            <span>Budget Usage: {budgetUsage.toFixed(1)}%</span>
            <span>Remaining: ${Math.max(0, budget - currentCost).toFixed(2)}</span>
          </div>
        </div>

        <div className="cost-card">
          <div className="card-header">
            <span className="card-title">Token Usage</span>
          </div>
          <div className="cost-value">{metrics?.metrics.token_usage.toLocaleString() || '0'}</div>
          <div className="cost-details">
            <span>Cost per Request: ${costPerRequest.toFixed(4)}</span>
            <span>Cost per 1K Tokens: ${metrics ? (metrics.metrics.cost_usd / (metrics.metrics.token_usage / 1000)).toFixed(4) : '0'}</span>
          </div>
        </div>

        <div className="cost-card">
          <div className="card-header">
            <span className="card-title">Efficiency</span>
          </div>
          <div className="cost-value">
            {metrics ? (metrics.metrics.token_usage / Math.max(metrics.metrics.request_count, 1)).toFixed(0) : '0'}
          </div>
          <div className="cost-details">
            <span>Tokens per Request</span>
          </div>
        </div>
      </div>

      <div className="cost-charts">
        <div className="chart-section">
          <h4>Cost Trends (30 Days)</h4>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={costHistory}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="cost"
                stroke="#3b82f6"
                strokeWidth={2}
                name="Cost (USD)"
              />
              <Line
                type="monotone"
                dataKey={budget}
                stroke="#ef4444"
                strokeDasharray="5 5"
                name="Budget"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-section">
          <h4>Token Usage (30 Days)</h4>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={costHistory}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="tokens" fill="#10b981" name="Tokens" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {isOverBudget && (
        <div className="budget-alert">
          <strong>⚠ Budget Exceeded!</strong> Current cost (${currentCost.toFixed(2)}) exceeds budget
          (${budget.toFixed(2)}). Consider optimizing token usage or increasing budget.
        </div>
      )}

      {isNearBudget && (
        <div className="budget-warning">
          <strong>⚠ Approaching Budget Limit</strong> Current budget usage is {budgetUsage.toFixed(1)}%.
          Monitor closely and consider optimization.
        </div>
      )}
    </div>
  );
}

