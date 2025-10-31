import { useEffect, useState } from 'react';
import { alertApi, Alert, WebSocketClient } from '../api/client';
import './AlertsPage.css';

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [statistics, setStatistics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const wsClientRef = useState(() => new WebSocketClient());

  useEffect(() => {
    loadAlerts();
    connectWebSocket();
    return () => {
      wsClientRef[0].disconnect();
    };
  }, []);

  const loadAlerts = async () => {
    try {
      const data = await alertApi.getAll();
      setAlerts(data.alerts);
      setStatistics(data.statistics);
      setLoading(false);
    } catch (err) {
      console.error('Failed to load alerts:', err);
      setLoading(false);
    }
  };

  const connectWebSocket = () => {
    wsClientRef[0].connect('/ws/alerts', (data) => {
      if (data.type === 'alerts') {
        loadAlerts();
      }
    });
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return '#ef4444';
      case 'high':
        return '#f59e0b';
      case 'medium':
        return '#3b82f6';
      case 'low':
        return '#64748b';
      default:
        return '#64748b';
    }
  };

  if (loading) {
    return <div className="alerts-page loading">Loading alerts...</div>;
  }

  return (
    <div className="alerts-page">
      <div className="page-header">
        <h1>Alerts</h1>
        {statistics && (
          <div className="alert-stats">
            <div className="stat-item">
              <span className="stat-value">{statistics.active_alerts}</span>
              <span className="stat-label">Active</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{statistics.total_alerts}</span>
              <span className="stat-label">Total</span>
            </div>
          </div>
        )}
      </div>

      <div className="alerts-list">
        {alerts.map((alert) => (
          <div key={alert.id} className={`alert-card ${alert.severity}`}>
            <div className="alert-header">
              <span
                className="severity-badge"
                style={{ backgroundColor: getSeverityColor(alert.severity) }}
              >
                {alert.severity.toUpperCase()}
              </span>
              <span className="status-badge">{alert.status}</span>
            </div>
            <h3 className="alert-title">{alert.title}</h3>
            <p className="alert-message">{alert.message}</p>
            <div className="alert-footer">
              <span className="alert-time">
                {new Date(alert.created_at).toLocaleString()}
              </span>
              {alert.deployment_id && (
                <span className="alert-deployment">{alert.deployment_id}</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {alerts.length === 0 && (
        <div className="empty-state">
          <p>No active alerts</p>
        </div>
      )}
    </div>
  );
}

