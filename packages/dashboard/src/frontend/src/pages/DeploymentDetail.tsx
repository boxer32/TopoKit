import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { deploymentApi, Deployment, WebSocketClient } from '../api/client';
import TopologyGraph, { NodeData, EdgeData } from '../components/TopologyGraph';
import SLOHeatmap, { SLOMetric } from '../components/SLOHeatmap';
import CircuitBreakerStatus, { CircuitBreakerData } from '../components/CircuitBreakerStatus';
import MetricsOverview from '../components/MetricsOverview';
import './DeploymentDetail.css';

export default function DeploymentDetail() {
  const { id } = useParams<{ id: string }>();
  const [deployment, setDeployment] = useState<Deployment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      loadDeployment(id);
    }
  }, [id]);

  const loadDeployment = async (deploymentId: string) => {
    try {
      setLoading(true);
      const data = await deploymentApi.getById(deploymentId);
      setDeployment(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load deployment');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="deployment-detail loading">
        <p>Loading deployment details...</p>
      </div>
    );
  }

  if (error || !deployment) {
    return (
      <div className="deployment-detail error">
        <p>Error: {error || 'Deployment not found'}</p>
        <Link to="/">Back to Dashboard</Link>
      </div>
    );
  }

  return (
    <div className="deployment-detail">
      <div className="detail-header">
        <Link to="/" className="back-link">← Back to Dashboard</Link>
        <h1>{deployment.name}</h1>
        <div className="deployment-info">
          <span className="info-badge">{deployment.environment}</span>
          <span className="info-badge status">{deployment.status}</span>
        </div>
      </div>

      <MetricsOverview deployment={deployment} />

      <div className="detail-sections">
        <section className="detail-section">
          <h2>Topology Graph</h2>
          <TopologyGraph
            nodes={[]}
            edges={[]}
          />
        </section>

        <section className="detail-section">
          <h2>SLO Compliance</h2>
          <SLOHeatmap metrics={[]} />
        </section>

        <section className="detail-section">
          <h2>Circuit Breakers</h2>
          <CircuitBreakerStatus breakers={[]} />
        </section>
      </div>
    </div>
  );
}

