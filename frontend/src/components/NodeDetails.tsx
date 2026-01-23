/** Node details panel component. */
import { useEffect, useState } from 'react';
import { api, Span } from '../lib/api';

interface NodeDetailsProps {
  threadId: string;
  nodeId: string;
}

export default function NodeDetails({ threadId, nodeId }: NodeDetailsProps) {
  const [span, setSpan] = useState<Span | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchSpan() {
      try {
        setLoading(true);
        const data = await api.listSpans(threadId);
        const foundSpan = data.spans.find((s) => s.span_id === nodeId);
        setSpan(foundSpan || null);
        setError(foundSpan ? null : 'Span not found');
      } catch (err: any) {
        setError(err.message || 'Failed to load span details');
      } finally {
        setLoading(false);
      }
    }

    if (threadId && nodeId) {
      fetchSpan();
    }
  }, [threadId, nodeId]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Node Details</h3>
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-100 rounded"></div>
          <div className="h-4 bg-gray-100 rounded w-3/4"></div>
          <div className="h-16 bg-gray-100 rounded"></div>
        </div>
      </div>
    );
  }

  if (error || !span) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Node Details</h3>
        <div className="text-red-500 text-xs bg-red-50 rounded p-2">{error || 'No data'}</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Node Details</h3>
      
      <div className="space-y-4">
        {/* Name */}
        <div>
          <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wide mb-1">Name</div>
          <div className="text-sm font-medium text-gray-900 bg-gray-50 px-3 py-2 rounded break-words">
            {span.name}
          </div>
        </div>

        {/* Status & Duration */}
        <div className="flex gap-3">
          <div className="flex-1">
            <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wide mb-1">Status</div>
            <span
              className={`inline-block px-2 py-1 rounded text-[10px] font-semibold ${
                span.status === 'ok'
                  ? 'bg-green-50 text-green-700'
                  : 'bg-red-50 text-red-700'
              }`}
            >
              {span.status.toUpperCase()}
            </span>
          </div>

          {span.duration !== undefined && (
            <div className="flex-1">
              <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wide mb-1">Duration</div>
              <div className="text-sm font-mono text-gray-900">
                {span.duration.toFixed(3)}s
              </div>
            </div>
          )}
        </div>

        {/* Timestamps */}
        <div>
          <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wide mb-1">Timestamps</div>
          <div className="bg-gray-50 rounded p-2.5 space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Start</span>
              <span className="font-mono text-gray-700">{new Date(span.start_time).toLocaleString()}</span>
            </div>
            {span.end_time && (
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">End</span>
                <span className="font-mono text-gray-700">{new Date(span.end_time).toLocaleString()}</span>
              </div>
            )}
          </div>
        </div>

        {/* Attributes */}
        {Object.keys(span.attributes).length > 0 && (
          <div>
            <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wide mb-1">Attributes</div>
            <div className="bg-gray-50 rounded p-2.5 max-h-48 overflow-y-auto">
              <pre 
                className="text-[11px] font-mono m-0 leading-relaxed"
                style={{ 
                  color: '#000000', 
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  overflowWrap: 'break-word',
                  maxWidth: '100%',
                  width: '100%',
                  boxSizing: 'border-box'
                }}
              >
                {JSON.stringify(span.attributes, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
