import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { traceApi, Trace } from '../api/client';
import './TracesPage.css';

export default function TracesPage() {
  const { id } = useParams<{ id: string }>();
  const [trace, setTrace] = useState<Trace | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (id) {
      loadTrace(id);
    }
  }, [id]);

  const loadTrace = async (traceId: string) => {
    try {
      setLoading(true);
      const data = await traceApi.getById(traceId);
      setTrace(data);
    } catch (err) {
      console.error('Failed to load trace:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="traces-page loading">Loading trace...</div>;
  }

  if (!trace) {
    return (
      <div className="traces-page">
        <h1>Trace Viewer</h1>
        <p>Enter a trace ID to view trace details</p>
      </div>
    );
  }

  return (
    <div className="traces-page">
      <div className="page-header">
        <h1>Trace: {trace.trace_id}</h1>
        <div className="trace-info">
          <span>Duration: {trace.duration_ms?.toFixed(2)}ms</span>
          <span>Spans: {trace.spans.length}</span>
        </div>
      </div>

      <div className="trace-details">
        <div className="trace-timeline">
          <h2>Execution Timeline</h2>
          <div className="timeline">
            {trace.spans.map((span) => (
              <div key={span.span_id} className="timeline-item">
                <div className="timeline-marker" data-status={span.status}></div>
                <div className="timeline-content">
                  <div className="timeline-header">
                    <span className="span-name">{span.name}</span>
                    <span className="span-duration">
                      {span.duration_ms?.toFixed(2)}ms
                    </span>
                  </div>
                  <div className="span-details">
                    <span className="span-id">Span ID: {span.span_id}</span>
                    {span.parent_span_id && (
                      <span className="parent-id">Parent: {span.parent_span_id}</span>
                    )}
                    {span.status && (
                      <span className={`span-status ${span.status}`}>
                        {span.status.toUpperCase()}
                      </span>
                    )}
                  </div>
                  {Object.keys(span.tags).length > 0 && (
                    <div className="span-tags">
                      {Object.entries(span.tags).map(([key, value]) => (
                        <span key={key} className="tag">
                          {key}: {value}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

