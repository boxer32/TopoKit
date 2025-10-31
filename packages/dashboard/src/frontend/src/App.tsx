import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import DashboardLayout from './components/DashboardLayout';
import DashboardHome from './pages/DashboardHome';
import DeploymentDetail from './pages/DeploymentDetail';
import AlertsPage from './pages/AlertsPage';
import TracesPage from './pages/TracesPage';
import './App.css';

function App() {
  return (
    <Router>
      <DashboardLayout>
        <Routes>
          <Route path="/" element={<DashboardHome />} />
          <Route path="/deployments/:id" element={<DeploymentDetail />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/traces" element={<TracesPage />} />
        </Routes>
      </DashboardLayout>
    </Router>
  );
}

export default App;

