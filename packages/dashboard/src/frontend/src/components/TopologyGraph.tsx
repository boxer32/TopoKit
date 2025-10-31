/**
 * Module: TopologyGraph
 * Purpose: Interactive node/edge graph with live status indicators
 * Inputs: Topology data, deployment metrics, node/edge status
 * Outputs: Interactive graph visualization with real-time updates
 * Dependencies: cytoscape, react, deployment API
 * Failure Modes: Missing data → fallback to static graph, render errors → error boundary
 * Trace: page:dashboard, build:20250131, spec-id:T043a
 */

import { useEffect, useRef, useState } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import Cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import './TopologyGraph.css';

Cytoscape.use(dagre);

export interface NodeData {
  id: string;
  label: string;
  kind: 'ux' | 'ai' | 'data' | 'ops';
  status: 'running' | 'completed' | 'failed' | 'pending';
  sloCompliance: 'compliant' | 'warning' | 'critical';
  circuitBreaker?: 'closed' | 'open' | 'half-open';
  confidenceScore?: number;
  costUsage?: 'within_budget' | 'approaching_limit' | 'over_budget';
}

export interface EdgeData {
  id: string;
  source: string;
  target: string;
  status: 'active' | 'inactive' | 'error';
  latency?: number;
  errorRate?: number;
  dataFlowVolume?: 'low' | 'medium' | 'high';
}

interface TopologyGraphProps {
  nodes: NodeData[];
  edges: EdgeData[];
  onNodeClick?: (nodeId: string) => void;
  onEdgeClick?: (edgeId: string) => void;
  selectedNodeId?: string;
  selectedEdgeId?: string;
}

export default function TopologyGraph({
  nodes,
  edges,
  onNodeClick,
  onEdgeClick,
  selectedNodeId,
  selectedEdgeId,
}: TopologyGraphProps) {
  const [cy, setCy] = useState<Cytoscape.Core | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Convert nodes to Cytoscape format
  const cyNodes = nodes.map((node) => ({
    data: {
      id: node.id,
      label: node.label,
      kind: node.kind,
      status: node.status,
      sloCompliance: node.sloCompliance,
      circuitBreaker: node.circuitBreaker,
      confidenceScore: node.confidenceScore,
      costUsage: node.costUsage,
    },
    classes: [
      `node-${node.kind}`,
      `status-${node.status}`,
      `slo-${node.sloCompliance}`,
      node.circuitBreaker ? `circuit-${node.circuitBreaker}` : '',
      selectedNodeId === node.id ? 'selected' : '',
    ].filter(Boolean).join(' '),
  }));

  // Convert edges to Cytoscape format
  const cyEdges = edges.map((edge) => ({
    data: {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      status: edge.status,
      latency: edge.latency,
      errorRate: edge.errorRate,
      dataFlowVolume: edge.dataFlowVolume,
      label: `${edge.latency || 0}ms`,
    },
    classes: [
      `edge-${edge.status}`,
      edge.dataFlowVolume ? `flow-${edge.dataFlowVolume}` : '',
      selectedEdgeId === edge.id ? 'selected' : '',
    ].filter(Boolean).join(' '),
  }));

  const elements = [...cyNodes, ...cyEdges];

  const layout = {
    name: 'dagre',
    nodeSep: 100,
    rankSep: 150,
    rankDir: 'TB',
    animate: true,
    animationDuration: 500,
  };

  const stylesheet = [
    {
      selector: 'node',
      style: {
        'background-color': '#3b82f6',
        'label': 'data(label)',
        'width': 80,
        'height': 80,
        'shape': 'round-rectangle',
        'text-valign': 'center',
        'text-halign': 'center',
        'font-size': '12px',
        'font-weight': '500',
        'color': '#ffffff',
        'border-width': 3,
        'border-color': '#ffffff',
        'text-wrap': 'wrap',
        'text-max-width': 70,
      },
    },
    {
      selector: 'node.node-ux',
      style: { 'background-color': '#8b5cf6' },
    },
    {
      selector: 'node.node-ai',
      style: { 'background-color': '#10b981' },
    },
    {
      selector: 'node.node-data',
      style: { 'background-color': '#3b82f6' },
    },
    {
      selector: 'node.node-ops',
      style: { 'background-color': '#f59e0b' },
    },
    {
      selector: 'node.status-running',
      style: { 'border-color': '#10b981', 'border-width': 4 },
    },
    {
      selector: 'node.status-completed',
      style: { 'border-color': '#3b82f6', 'border-width': 3 },
    },
    {
      selector: 'node.status-failed',
      style: { 'border-color': '#ef4444', 'border-width': 4 },
    },
    {
      selector: 'node.status-pending',
      style: { 'border-color': '#64748b', 'border-width': 2 },
    },
    {
      selector: 'node.slo-compliant',
      style: { 'background-opacity': 1.0 },
    },
    {
      selector: 'node.slo-warning',
      style: { 'background-opacity': 0.8 },
    },
    {
      selector: 'node.slo-critical',
      style: { 'background-opacity': 0.6, 'border-color': '#ef4444' },
    },
    {
      selector: 'node.circuit-open',
      style: { 'border-style': 'dashed', 'border-color': '#ef4444' },
    },
    {
      selector: 'node.circuit-half-open',
      style: { 'border-style': 'dotted', 'border-color': '#f59e0b' },
    },
    {
      selector: 'node.selected',
      style: { 'border-color': '#2563eb', 'border-width': 5, 'z-index': 10 },
    },
    {
      selector: 'edge',
      style: {
        'width': 3,
        'line-color': '#94a3b8',
        'target-arrow-color': '#94a3b8',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'label': 'data(label)',
        'font-size': '10px',
        'text-rotation': 'autorotate',
        'text-margin-y': -10,
      },
    },
    {
      selector: 'edge.edge-active',
      style: { 'line-color': '#10b981', 'width': 4 },
    },
    {
      selector: 'edge.edge-inactive',
      style: { 'line-color': '#64748b', 'width': 2, 'opacity': 0.5 },
    },
    {
      selector: 'edge.edge-error',
      style: { 'line-color': '#ef4444', 'width': 5, 'line-style': 'dashed' },
    },
    {
      selector: 'edge.flow-high',
      style: { 'width': 6 },
    },
    {
      selector: 'edge.flow-medium',
      style: { 'width': 4 },
    },
    {
      selector: 'edge.flow-low',
      style: { 'width': 2 },
    },
    {
      selector: 'edge.selected',
      style: { 'line-color': '#2563eb', 'width': 6, 'z-index': 10 },
    },
  ];

  const handleNodeClick = (evt: any) => {
    const nodeId = evt.target.id();
    if (onNodeClick) {
      onNodeClick(nodeId);
    }
  };

  const handleEdgeClick = (evt: any) => {
    const edgeId = evt.target.id();
    if (onEdgeClick) {
      onEdgeClick(edgeId);
    }
  };

  return (
    <div ref={containerRef} className="topology-graph-container">
      <CytoscapeComponent
        elements={elements}
        style={{ width: '100%', height: '100%' }}
        layout={layout}
        stylesheet={stylesheet}
        cy={(cyInstance) => {
          if (cyInstance && !cy) {
            setCy(cyInstance);
            cyInstance.on('tap', 'node', handleNodeClick);
            cyInstance.on('tap', 'edge', handleEdgeClick);
            cyInstance.on('mouseover', 'node', (evt) => {
              evt.target.addClass('hover');
            });
            cyInstance.on('mouseout', 'node', (evt) => {
              evt.target.removeClass('hover');
            });
          }
        }}
      />
      
      <div className="graph-legend">
        <div className="legend-section">
          <h4>Node Status</h4>
          <div className="legend-item">
            <span className="legend-color running"></span>
            <span>Running</span>
          </div>
          <div className="legend-item">
            <span className="legend-color completed"></span>
            <span>Completed</span>
          </div>
          <div className="legend-item">
            <span className="legend-color failed"></span>
            <span>Failed</span>
          </div>
          <div className="legend-item">
            <span className="legend-color pending"></span>
            <span>Pending</span>
          </div>
        </div>
        
        <div className="legend-section">
          <h4>SLO Compliance</h4>
          <div className="legend-item">
            <span className="legend-color compliant"></span>
            <span>Compliant</span>
          </div>
          <div className="legend-item">
            <span className="legend-color warning"></span>
            <span>Warning</span>
          </div>
          <div className="legend-item">
            <span className="legend-color critical"></span>
            <span>Critical</span>
          </div>
        </div>
        
        <div className="legend-section">
          <h4>Node Types</h4>
          <div className="legend-item">
            <span className="legend-color node-ux"></span>
            <span>UX</span>
          </div>
          <div className="legend-item">
            <span className="legend-color node-ai"></span>
            <span>AI</span>
          </div>
          <div className="legend-item">
            <span className="legend-color node-data"></span>
            <span>Data</span>
          </div>
          <div className="legend-item">
            <span className="legend-color node-ops"></span>
            <span>Ops</span>
          </div>
        </div>
      </div>
    </div>
  );
}

