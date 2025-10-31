/**
 * Module: HumanGateQueue
 * Purpose: Management interface for human-in-the-loop approval workflows
 * Inputs: Gate approval requests, queue data, user actions
 * Outputs: Approval queue interface with request management
 * Dependencies: react, API client
 * Failure Modes: Missing data → empty state, approval errors → error handling
 * Trace: page:dashboard, build:20250131, spec-id:T043d
 */

import { useEffect, useState } from 'react';
import './HumanGateQueue.css';

export interface GateRequest {
  id: string;
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  status: 'pending' | 'approved' | 'rejected' | 'timeout';
  requestedAt: string;
  requestedBy: string;
  timeoutSeconds?: number;
  data: Record<string, any>;
  comments?: string[];
}

interface HumanGateQueueProps {
  deploymentId?: string;
  onApprove?: (requestId: string) => void;
  onReject?: (requestId: string, reason: string) => void;
}

export default function HumanGateQueue({
  deploymentId,
  onApprove,
  onReject,
}: HumanGateQueueProps) {
  const [requests, setRequests] = useState<GateRequest[]>([]);
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all');

  // Sample data - in real implementation, this would come from API
  useEffect(() => {
    const sampleRequests: GateRequest[] = [
      {
        id: 'gate-1',
        title: 'High-Risk Data Deletion',
        description: 'Request to delete user data for account ID: user-12345',
        priority: 'high',
        status: 'pending',
        requestedAt: new Date().toISOString(),
        requestedBy: 'system',
        timeoutSeconds: 300,
        data: { operation: 'delete_user', user_id: 'user-12345' },
      },
      {
        id: 'gate-2',
        title: 'Production Configuration Change',
        description: 'Update model temperature threshold from 0.2 to 0.5',
        priority: 'critical',
        status: 'pending',
        requestedAt: new Date().toISOString(),
        requestedBy: 'devops-engineer',
        timeoutSeconds: 600,
        data: { config_key: 'temperature', old_value: 0.2, new_value: 0.5 },
      },
    ];
    setRequests(sampleRequests);
  }, [deploymentId]);

  const filteredRequests = requests.filter((req) => {
    if (filter === 'all') return true;
    return req.status === filter;
  });

  const getPriorityColor = (priority: string) => {
    switch (priority) {
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return '#f59e0b';
      case 'approved':
        return '#10b981';
      case 'rejected':
        return '#ef4444';
      case 'timeout':
        return '#64748b';
      default:
        return '#64748b';
    }
  };

  const handleApprove = (requestId: string) => {
    setRequests((prev) =>
      prev.map((req) =>
        req.id === requestId ? { ...req, status: 'approved' as const } : req
      )
    );
    onApprove?.(requestId);
  };

  const handleReject = (requestId: string, reason: string) => {
    setRequests((prev) =>
      prev.map((req) =>
        req.id === requestId
          ? { ...req, status: 'rejected' as const, comments: [...(req.comments || []), reason] }
          : req
      )
    );
    onReject?.(requestId, reason);
  };

  return (
    <div className="human-gate-queue">
      <div className="queue-header">
        <h3>Human Gate Approval Queue</h3>
        <div className="queue-filters">
          <button
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button
            className={filter === 'pending' ? 'active' : ''}
            onClick={() => setFilter('pending')}
          >
            Pending ({requests.filter((r) => r.status === 'pending').length})
          </button>
          <button
            className={filter === 'approved' ? 'active' : ''}
            onClick={() => setFilter('approved')}
          >
            Approved
          </button>
          <button
            className={filter === 'rejected' ? 'active' : ''}
            onClick={() => setFilter('rejected')}
          >
            Rejected
          </button>
        </div>
      </div>

      <div className="queue-list">
        {filteredRequests.map((request) => (
          <div key={request.id} className={`gate-request ${request.priority}`}>
            <div className="request-header">
              <div className="request-title-section">
                <span
                  className="priority-badge"
                  style={{ backgroundColor: getPriorityColor(request.priority) }}
                >
                  {request.priority.toUpperCase()}
                </span>
                <h4 className="request-title">{request.title}</h4>
              </div>
              <span
                className="status-badge"
                style={{ backgroundColor: getStatusColor(request.status) }}
              >
                {request.status.toUpperCase()}
              </span>
            </div>

            <p className="request-description">{request.description}</p>

            <div className="request-meta">
              <span className="meta-item">
                <strong>Requested by:</strong> {request.requestedBy}
              </span>
              <span className="meta-item">
                <strong>Requested at:</strong>{' '}
                {new Date(request.requestedAt).toLocaleString()}
              </span>
              {request.timeoutSeconds && (
                <span className="meta-item">
                  <strong>Timeout:</strong> {request.timeoutSeconds}s
                </span>
              )}
            </div>

            {Object.keys(request.data).length > 0 && (
              <div className="request-data">
                <strong>Request Data:</strong>
                <pre>{JSON.stringify(request.data, null, 2)}</pre>
              </div>
            )}

            {request.comments && request.comments.length > 0 && (
              <div className="request-comments">
                <strong>Comments:</strong>
                {request.comments.map((comment, idx) => (
                  <div key={idx} className="comment">{comment}</div>
                ))}
              </div>
            )}

            {request.status === 'pending' && (
              <div className="request-actions">
                <button
                  className="btn-approve"
                  onClick={() => handleApprove(request.id)}
                >
                  Approve
                </button>
                <button
                  className="btn-reject"
                  onClick={() => {
                    const reason = prompt('Rejection reason:');
                    if (reason) {
                      handleReject(request.id, reason);
                    }
                  }}
                >
                  Reject
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {filteredRequests.length === 0 && (
        <div className="empty-state">
          <p>No gate requests {filter !== 'all' ? `with status "${filter}"` : ''}</p>
        </div>
      )}
    </div>
  );
}

