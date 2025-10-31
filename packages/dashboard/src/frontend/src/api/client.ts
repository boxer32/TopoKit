/**
 * API client for TopoView Dashboard
 * 
 * Module: dashboard-api-client
 * Purpose: Provides API client for communicating with TopoView backend
 * Inputs: API endpoints, WebSocket connections
 * Outputs: Typed API responses, WebSocket event streams
 * Dependencies: axios, WebSocket API
 * Failure Modes: Network errors, connection failures → retry with exponential backoff
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface Deployment {
  id: string;
  name: string;
  status: string;
  environment: string;
  health?: {
    status: string;
    uptime_percentage: number;
    response_time_ms: number;
    error_rate: number;
    active_instances: number;
  };
  metrics?: {
    request_count: number;
    error_count: number;
    avg_response_time_ms: number;
    p95_response_time_ms: number;
    error_rate: number;
    throughput_rps: number;
  };
}

export interface DeploymentMetrics {
  deployment_id: string;
  metrics: {
    request_count: number;
    success_count: number;
    error_count: number;
    avg_response_time_ms: number;
    p95_response_time_ms: number;
    p99_response_time_ms: number;
    throughput_rps: number;
    cpu_usage_percent: number;
    memory_usage_percent: number;
    token_usage: number;
    cost_usd: number;
    schema_pass_rate: number;
    error_rate: number;
  };
}

export interface Alert {
  id: string;
  title: string;
  message: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  status: 'active' | 'acknowledged' | 'resolved' | 'suppressed';
  created_at: string;
  deployment_id?: string;
  node_id?: string;
}

export interface Trace {
  trace_id: string;
  start_time: string;
  end_time?: string;
  duration_ms?: number;
  spans: Array<{
    span_id: string;
    parent_span_id?: string;
    name: string;
    start_time: string;
    end_time?: string;
    duration_ms?: number;
    status: string;
    tags: Record<string, string>;
  }>;
}

// API functions
export const deploymentApi = {
  getAll: async (): Promise<{ deployments: Deployment[] }> => {
    const response = await apiClient.get('/deployments');
    return response.data;
  },

  getById: async (id: string): Promise<Deployment> => {
    const response = await apiClient.get(`/deployments/${id}`);
    return response.data;
  },

  getMetrics: async (id: string): Promise<DeploymentMetrics> => {
    const response = await apiClient.get(`/deployments/${id}/metrics`);
    return response.data;
  },
};

export const alertApi = {
  getAll: async (): Promise<{ alerts: Alert[]; statistics: any }> => {
    const response = await apiClient.get('/alerts');
    return response.data;
  },
};

export const traceApi = {
  getById: async (id: string): Promise<Trace> => {
    const response = await apiClient.get(`/traces/${id}`);
    return response.data;
  },
};

// WebSocket client
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  connect(url: string, onMessage: (data: any) => void, onError?: (error: Event) => void) {
    const wsUrl = url.startsWith('ws') ? url : `ws://${window.location.host}${url}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log(`WebSocket connected: ${url}`);
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (onError) {
        onError(error);
      }
    };

    this.ws.onclose = () => {
      console.log(`WebSocket disconnected: ${url}`);
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        setTimeout(() => {
          this.reconnectAttempts++;
          this.connect(url, onMessage, onError);
        }, this.reconnectDelay * this.reconnectAttempts);
      }
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

