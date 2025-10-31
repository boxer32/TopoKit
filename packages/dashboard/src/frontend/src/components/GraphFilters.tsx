/**
 * Module: GraphFilters
 * Purpose: Interactive filtering and drill-down analysis for topology visualization
 * Inputs: Filter criteria, node/edge selection
 * Outputs: Filtered graph view with drill-down capabilities
 * Dependencies: react, topology graph component
 * Failure Modes: Invalid filters → error state, empty results → empty message
 * Trace: page:dashboard, build:20250131, spec-id:T043g
 */

import { useState } from 'react';
import './GraphFilters.css';

export interface FilterCriteria {
  nodeType?: 'ux' | 'ai' | 'data' | 'ops' | 'all';
  status?: 'active' | 'inactive' | 'error' | 'all';
  sloCompliance?: 'compliant' | 'warning' | 'critical' | 'all';
  timeRange?: 'last_hour' | 'last_day' | 'last_week' | 'all';
  sessionId?: string;
}

interface GraphFiltersProps {
  onFilterChange: (filters: FilterCriteria) => void;
  onReset: () => void;
}

export default function GraphFilters({ onFilterChange, onReset }: GraphFiltersProps) {
  const [filters, setFilters] = useState<FilterCriteria>({
    nodeType: 'all',
    status: 'all',
    sloCompliance: 'all',
    timeRange: 'last_day',
    sessionId: '',
  });

  const handleFilterChange = (key: keyof FilterCriteria, value: any) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  const handleReset = () => {
    const resetFilters: FilterCriteria = {
      nodeType: 'all',
      status: 'all',
      sloCompliance: 'all',
      timeRange: 'last_day',
      sessionId: '',
    };
    setFilters(resetFilters);
    onReset();
    onFilterChange(resetFilters);
  };

  return (
    <div className="graph-filters">
      <div className="filters-header">
        <h4>Filters</h4>
        <button className="reset-btn" onClick={handleReset}>
          Reset
        </button>
      </div>

      <div className="filters-grid">
        <div className="filter-group">
          <label>Node Type</label>
          <select
            value={filters.nodeType || 'all'}
            onChange={(e) => handleFilterChange('nodeType', e.target.value)}
          >
            <option value="all">All Types</option>
            <option value="ux">UX</option>
            <option value="ai">AI</option>
            <option value="data">Data</option>
            <option value="ops">Ops</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Status</label>
          <select
            value={filters.status || 'all'}
            onChange={(e) => handleFilterChange('status', e.target.value)}
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="error">Error</option>
          </select>
        </div>

        <div className="filter-group">
          <label>SLO Compliance</label>
          <select
            value={filters.sloCompliance || 'all'}
            onChange={(e) => handleFilterChange('sloCompliance', e.target.value)}
          >
            <option value="all">All</option>
            <option value="compliant">Compliant</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Time Range</label>
          <select
            value={filters.timeRange || 'last_day'}
            onChange={(e) => handleFilterChange('timeRange', e.target.value)}
          >
            <option value="last_hour">Last Hour</option>
            <option value="last_day">Last Day</option>
            <option value="last_week">Last Week</option>
            <option value="all">All Time</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Session ID</label>
          <input
            type="text"
            placeholder="Filter by session..."
            value={filters.sessionId || ''}
            onChange={(e) => handleFilterChange('sessionId', e.target.value)}
          />
        </div>
      </div>

      <div className="filter-summary">
        <span>Active Filters: </span>
        {Object.entries(filters)
          .filter(([_, value]) => value && value !== 'all')
          .map(([key, value]) => (
            <span key={key} className="filter-tag">
              {key}: {value}
            </span>
          ))}
      </div>
    </div>
  );
}

