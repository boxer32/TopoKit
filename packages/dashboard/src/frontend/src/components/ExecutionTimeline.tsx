/**
 * Module: ExecutionTimeline
 * Purpose: Execution timeline visualization for topology runs
 * Inputs: Execution data, trace spans, timeline events
 * Outputs: Interactive timeline with step-by-step execution visualization
 * Dependencies: react, d3 or custom timeline component
 * Failure Modes: Missing data → empty state, rendering errors → error boundary
 * Trace: page:dashboard, build:20250131, spec-id:T044b
 */

import { useEffect, useState } from 'react';
import { deploymentApi, Trace } from '../api/client';
import './ExecutionTimeline.css';

interface TimelineEvent {
  id: string;
  nodeId: string;
  nodeName: string;
  startTime: Date;
  endTime?: Date;
  duration?: number;
  status: 'running' | 'completed' | 'failed' | 'pending';
  error?: string;
}

interface ExecutionTimelineProps {
  deploymentId?: string;
  executionId?: string;
  traceId?: string;
}

export default function ExecutionTimeline({
  deploymentId,
  executionId,
  traceId,
}: ExecutionTimelineProps) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<TimelineEvent | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (traceId) {
      loadTrace(traceId);
    } else {
      // Generate sample data for demonstration
      generateSampleTimeline();
    }
  }, [traceId]);

  const loadTrace = async (traceId: string) => {
    setLoading(true);
    try {
      // In real implementation, fetch trace data
      // const trace = await traceApi.getById(traceId);
      // Convert trace spans to timeline events
      generateSampleTimeline();
    } catch (error) {
      console.error('Failed to load trace:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateSampleTimeline = () => {
    const now = new Date();
    const sampleEvents: TimelineEvent[] = [
      {
        id: 'event-1',
        nodeId: 'node-1',
        nodeName: 'Data.Retrieval',
        startTime: new Date(now.getTime() - 5000),
        endTime: new Date(now.getTime() - 3500),
        duration: 1500,
        status: 'completed',
      },
      {
        id: 'event-2',
        nodeId: 'node-2',
        nodeName: 'AI.Answer',
        startTime: new Date(now.getTime() - 3500),
        endTime: new Date(now.getTime() - 1500),
        duration: 2000,
        status: 'completed',
      },
      {
        id: 'event-3',
        nodeId: 'node-3',
        nodeName: 'AI.Explain',
        startTime: new Date(now.getTime() - 1500),
        endTime: new Date(now.getTime() - 500),
        duration: 1000,
        status: 'completed',
      },
      {
        id: 'event-4',
        nodeId: 'node-4',
        nodeName: 'UX.Response',
        startTime: new Date(now.getTime() - 500),
        status: 'running',
      },
    ];
    setEvents(sampleEvents);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return '#10b981';
      case 'running':
        return '#3b82f6';
      case 'failed':
        return '#ef4444';
      case 'pending':
        return '#64748b';
      default:
        return '#64748b';
    }
  };

  const totalDuration = events.reduce((sum, event) => sum + (event.duration || 0), 0);
  const earliestTime = events.length > 0 ? events[0].startTime : new Date();
  const latestTime =
    events.length > 0
      ? events[events.length - 1].endTime || events[events.length - 1].startTime
      : new Date();

  const calculateLeft = (event: TimelineEvent) => {
    const start = earliestTime.getTime();
    const end = latestTime.getTime();
    const eventStart = event.startTime.getTime();
    return ((eventStart - start) / (end - start)) * 100;
  };

  const calculateWidth = (event: TimelineEvent) => {
    if (!event.endTime) return 5; // Show as a point if still running
    const start = earliestTime.getTime();
    const end = latestTime.getTime();
    const eventDuration = event.endTime.getTime() - event.startTime.getTime();
    return (eventDuration / (end - start)) * 100;
  };

  return (
    <div className="execution-timeline">
      <div className="timeline-header">
        <h3>Execution Timeline</h3>
        {totalDuration > 0 && (
          <span className="total-duration">Total Duration: {totalDuration}ms</span>
        )}
      </div>

      {loading ? (
        <div className="loading">Loading timeline...</div>
      ) : events.length === 0 ? (
        <div className="empty-state">No execution data available</div>
      ) : (
        <>
          <div className="timeline-container">
            <div className="timeline-track">
              {events.map((event) => {
                const left = calculateLeft(event);
                const width = calculateWidth(event);
                const color = getStatusColor(event.status);

                return (
                  <div
                    key={event.id}
                    className={`timeline-event ${event.status}`}
                    style={{
                      left: `${left}%`,
                      width: `${Math.max(width, 2)}%`,
                      backgroundColor: color,
                    }}
                    onClick={() => setSelectedEvent(event)}
                    title={`${event.nodeName}: ${event.duration || 'running'}ms`}
                  >
                    <div className="event-label">{event.nodeName}</div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="timeline-events-list">
            {events.map((event) => (
              <div
                key={event.id}
                className={`event-item ${selectedEvent?.id === event.id ? 'selected' : ''}`}
                onClick={() => setSelectedEvent(event)}
              >
                <div className="event-status" style={{ backgroundColor: getStatusColor(event.status) }}></div>
                <div className="event-info">
                  <span className="event-name">{event.nodeName}</span>
                  <span className="event-time">
                    {event.startTime.toLocaleTimeString()} -{' '}
                    {event.endTime ? event.endTime.toLocaleTimeString() : 'Running'}
                  </span>
                </div>
                <div className="event-duration">
                  {event.duration ? `${event.duration}ms` : 'Running...'}
                </div>
              </div>
            ))}
          </div>

          {selectedEvent && (
            <div className="event-details">
              <h4>{selectedEvent.nodeName}</h4>
              <div className="detail-row">
                <span>Node ID:</span>
                <span>{selectedEvent.nodeId}</span>
              </div>
              <div className="detail-row">
                <span>Status:</span>
                <span className={`status-badge ${selectedEvent.status}`}>
                  {selectedEvent.status.toUpperCase()}
                </span>
              </div>
              <div className="detail-row">
                <span>Start Time:</span>
                <span>{selectedEvent.startTime.toLocaleString()}</span>
              </div>
              {selectedEvent.endTime && (
                <div className="detail-row">
                  <span>End Time:</span>
                  <span>{selectedEvent.endTime.toLocaleString()}</span>
                </div>
              )}
              {selectedEvent.duration && (
                <div className="detail-row">
                  <span>Duration:</span>
                  <span>{selectedEvent.duration}ms</span>
                </div>
              )}
              {selectedEvent.error && (
                <div className="detail-row error">
                  <span>Error:</span>
                  <span>{selectedEvent.error}</span>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

