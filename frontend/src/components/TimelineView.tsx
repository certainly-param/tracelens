/** Timeline view component for execution timeline navigation. */
import { useEffect, useState } from 'react';
import { api } from '../lib/api';

interface TimelineViewProps {
  threadId: string;
  onJumpToCheckpoint?: (checkpointId: string) => void;
  onJumpToSpan?: (spanId: string) => void;
}

interface TimelineEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  checkpoint_id?: string;
  span_id?: string;
  node_id?: string;
  description: string;
  metadata: Record<string, any>;
}

export default function TimelineView({
  threadId,
  onJumpToCheckpoint,
  onJumpToSpan,
}: TimelineViewProps) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchTimeline() {
      try {
        setLoading(true);
        const data = await api.getTimeline(threadId);
        setEvents(data.events);
        setError(null);
      } catch (err: any) {
        setError(err.message || 'Failed to load timeline');
      } finally {
        setLoading(false);
      }
    }

    if (threadId) {
      fetchTimeline();
    }
  }, [threadId]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Timeline</h3>
        <div className="animate-pulse space-y-2">
          <div className="h-6 bg-gray-100 rounded"></div>
          <div className="h-6 bg-gray-100 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Timeline</h3>
        <div className="text-red-600 text-xs bg-red-50 rounded p-2">{error}</div>
      </div>
    );
  }

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'checkpoint':
        return 'bg-blue-100 border-blue-300 text-blue-700';
      case 'span':
        return 'bg-green-100 border-green-300 text-green-700';
      case 'node_transition':
        return 'bg-purple-100 border-purple-300 text-purple-700';
      default:
        return 'bg-gray-100 border-gray-300 text-gray-700';
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">Timeline</h3>
      <div className="space-y-1.5 max-h-[500px] overflow-y-auto">
        {events.length === 0 ? (
          <div className="text-gray-400 text-xs text-center py-4">No events</div>
        ) : (
          events.map((event, index) => (
            <button
              key={event.event_id}
              onClick={() => {
                if (event.checkpoint_id && onJumpToCheckpoint) {
                  onJumpToCheckpoint(event.checkpoint_id);
                } else if (event.span_id && onJumpToSpan) {
                  onJumpToSpan(event.span_id);
                }
              }}
              className="w-full text-left rounded border px-2.5 py-1.5 text-xs transition-colors hover:bg-gray-50 border-gray-200"
            >
              <div className="flex items-center gap-2 mb-0.5">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${getEventColor(event.event_type)}`}>
                  {event.event_type}
                </span>
                <span className="text-gray-500 font-mono text-[10px]">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className="text-gray-700">{event.description}</div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
