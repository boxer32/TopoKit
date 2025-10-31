import { Link, useLocation } from 'react-router-dom';
import { ReactNode } from 'react';
import './DashboardLayout.css';

interface DashboardLayoutProps {
  children: ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path || location.pathname.startsWith(path + '/');

  return (
    <div className="dashboard-layout">
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="logo">
            <span className="logo-icon">⊚</span>
            TopoView
          </h1>
          <nav className="header-nav">
            <Link to="/" className={isActive('/') ? 'active' : ''}>
              Dashboard
            </Link>
            <Link to="/alerts" className={isActive('/alerts') ? 'active' : ''}>
              Alerts
            </Link>
            <Link to="/traces" className={isActive('/traces') ? 'active' : ''}>
              Traces
            </Link>
          </nav>
        </div>
      </header>

      <main className="dashboard-main">
        <aside className="dashboard-sidebar">
          <nav className="sidebar-nav">
            <h2>Deployments</h2>
            <DeploymentList />
          </nav>
        </aside>

        <div className="dashboard-content">
          {children}
        </div>
      </main>
    </div>
  );
}

function DeploymentList() {
  // This would fetch from API in real implementation
  return (
    <div className="deployment-list">
      <p className="text-muted">Loading deployments...</p>
    </div>
  );
}

