/**
 * Module: Collaboration
 * Purpose: Real-time collaboration features for multi-user dashboard sessions
 * Inputs: User presence data, shared sessions, annotations, comments
 * Outputs: Real-time collaboration interface with user indicators and shared views
 * Dependencies: react, WebSocket, collaboration API
 * Failure Modes: Connection errors → retry mechanism, missing data → fallback display
 * Trace: page:dashboard, build:20250131, spec-id:T043i
 */

import { useEffect, useState, useRef } from 'react';
import { WebSocketClient } from '../api/client';
import './Collaboration.css';

export interface Collaborator {
  id: string;
  name: string;
  avatar?: string;
  color: string;
  status: 'active' | 'viewing' | 'idle';
  currentView?: string;
  lastActivity: string;
}

export interface Annotation {
  id: string;
  userId: string;
  userName: string;
  target: 'node' | 'edge' | 'graph';
  targetId: string;
  content: string;
  timestamp: string;
  resolved: boolean;
}

interface CollaborationProps {
  deploymentId: string;
  sessionId?: string;
}

export default function Collaboration({ deploymentId, sessionId }: CollaborationProps) {
  const [collaborators, setCollaborators] = useState<Collaborator[]>([]);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [isActive, setIsActive] = useState(false);
  const [newAnnotation, setNewAnnotation] = useState('');
  const [selectedTarget, setSelectedTarget] = useState<{ type: string; id: string } | null>(null);
  const wsClientRef = useRef<WebSocketClient | null>(null);
  const userColorRef = useRef<string>('#' + Math.floor(Math.random() * 16777215).toString(16));

  useEffect(() => {
    connectCollaboration();
    return () => {
      if (wsClientRef.current) {
        wsClientRef.current.disconnect();
      }
    };
  }, [deploymentId, sessionId]);

  const connectCollaboration = () => {
    const client = new WebSocketClient();
    wsClientRef.current = client;

    const wsUrl = sessionId
      ? `/ws/collaboration/${deploymentId}/${sessionId}`
      : `/ws/collaboration/${deploymentId}`;

    client.connect(wsUrl, (data) => {
      if (data.type === 'presence') {
        setCollaborators(data.collaborators || []);
      } else if (data.type === 'annotation') {
        setAnnotations((prev) => {
          const exists = prev.find((a) => a.id === data.annotation.id);
          if (exists) {
            return prev.map((a) => (a.id === data.annotation.id ? data.annotation : a));
          }
          return [...prev, data.annotation];
        });
      } else if (data.type === 'annotation_resolved') {
        setAnnotations((prev) =>
          prev.map((a) => (a.id === data.annotationId ? { ...a, resolved: true } : a))
        );
      }
    });
  };

  const sendAnnotation = () => {
    if (!newAnnotation.trim() || !selectedTarget) return;

    const annotation: Annotation = {
      id: `ann-${Date.now()}`,
      userId: 'current-user',
      userName: 'You',
      target: selectedTarget.type as 'node' | 'edge' | 'graph',
      targetId: selectedTarget.id,
      content: newAnnotation,
      timestamp: new Date().toISOString(),
      resolved: false,
    };

    setAnnotations((prev) => [...prev, annotation]);
    setNewAnnotation('');
    setSelectedTarget(null);

    // In real implementation, send via WebSocket
    if (wsClientRef.current) {
      // wsClientRef.current.send({ type: 'create_annotation', annotation });
    }
  };

  const resolveAnnotation = (annotationId: string) => {
    setAnnotations((prev) =>
      prev.map((a) => (a.id === annotationId ? { ...a, resolved: true } : a))
    );
  };

  const activeCollaborators = collaborators.filter((c) => c.status === 'active');
  const activeAnnotations = annotations.filter((a) => !a.resolved);

  return (
    <div className="collaboration-panel">
      <div className="collaboration-header">
        <h4>Collaboration</h4>
        <button
          className={`toggle-btn ${isActive ? 'active' : ''}`}
          onClick={() => setIsActive(!isActive)}
        >
          {isActive ? 'Active' : 'Inactive'}
        </button>
      </div>

      {isActive && (
        <>
          <div className="collaborators-section">
            <h5>Active Users ({activeCollaborators.length})</h5>
            <div className="collaborators-list">
              {activeCollaborators.map((collaborator) => (
                <div key={collaborator.id} className="collaborator-item">
                  <div
                    className="collaborator-avatar"
                    style={{ backgroundColor: collaborator.color }}
                  >
                    {collaborator.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="collaborator-info">
                    <span className="collaborator-name">{collaborator.name}</span>
                    {collaborator.currentView && (
                      <span className="collaborator-view">Viewing: {collaborator.currentView}</span>
                    )}
                  </div>
                  <div className={`status-indicator ${collaborator.status}`}></div>
                </div>
              ))}
            </div>
          </div>

          <div className="annotations-section">
            <h5>Annotations ({activeAnnotations.length})</h5>
            <div className="annotations-list">
              {activeAnnotations.map((annotation) => (
                <div key={annotation.id} className="annotation-item">
                  <div className="annotation-header">
                    <span className="annotation-user" style={{ color: userColorRef.current }}>
                      {annotation.userName}
                    </span>
                    <span className="annotation-time">
                      {new Date(annotation.timestamp).toLocaleTimeString()}
                    </span>
                    <button
                      className="resolve-btn"
                      onClick={() => resolveAnnotation(annotation.id)}
                    >
                      ✓
                    </button>
                  </div>
                  <div className="annotation-content">{annotation.content}</div>
                  <div className="annotation-target">
                    {annotation.target}: {annotation.targetId}
                  </div>
                </div>
              ))}
            </div>

            <div className="annotation-form">
              <input
                type="text"
                placeholder="Add annotation..."
                value={newAnnotation}
                onChange={(e) => setNewAnnotation(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendAnnotation()}
              />
              <button onClick={sendAnnotation} disabled={!newAnnotation.trim()}>
                Add
              </button>
            </div>
          </div>

          <div className="session-info">
            <span>Session ID: {sessionId || 'Default'}</span>
            <span>Your Color: </span>
            <span
              className="user-color-indicator"
              style={{ backgroundColor: userColorRef.current }}
            ></span>
          </div>
        </>
      )}
    </div>
  );
}

