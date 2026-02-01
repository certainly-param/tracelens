/** Checkpoint browser component for navigating checkpoint history. */
import { useEffect, useState } from 'react';
import { api, Checkpoint } from '../lib/api';

interface CheckpointBrowserProps {
  threadId: string;
  selectedCheckpoint: string | null;
  onSelectCheckpoint: (checkpointId: string | null) => void;
}

export default function CheckpointBrowser({
  threadId,
  selectedCheckpoint,
  onSelectCheckpoint,
}: CheckpointBrowserProps) {
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchCheckpoints() {
      try {
        setLoading(true);
        const data = await api.listCheckpoints(threadId);
        setCheckpoints(data.checkpoints);
        setError(null);
      } catch (err: any) {
        setError(err.message || 'Failed to load checkpoints');
      } finally {
        setLoading(false);
      }
    }

    if (threadId) {
      fetchCheckpoints();
    }
  }, [threadId]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Checkpoints</h3>
        <div className="animate-pulse space-y-2">
          <div className="h-8 bg-gray-100 rounded"></div>
          <div className="h-8 bg-gray-100 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Checkpoints</h3>
        <div className="text-red-600 text-xs bg-red-50 rounded p-2">{error}</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">Checkpoints</h3>
      <div className="space-y-2 max-h-[400px] overflow-y-auto">
        {checkpoints.length === 0 ? (
          <div className="text-gray-400 text-xs text-center py-4">No checkpoints</div>
        ) : (
          checkpoints.map((checkpoint, index) => (
            <button
              key={checkpoint.checkpoint_id}
              onClick={() =>
                onSelectCheckpoint(
                  selectedCheckpoint === checkpoint.checkpoint_id
                    ? null
                    : checkpoint.checkpoint_id
                )
              }
              className={`
                block w-full text-left rounded border px-2.5 py-2 text-xs transition-colors
                ${selectedCheckpoint === checkpoint.checkpoint_id
                  ? 'bg-indigo-50 border-indigo-300'
                  : 'bg-white border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }
              `}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-gray-900">
                  #{index + 1}
                </span>
                <span className="text-gray-400 font-mono text-[10px]">
                  {checkpoint.checkpoint_id.substring(0, 8)}...
                </span>
              </div>
              <div className="text-[10px] text-gray-500">
                {new Date(checkpoint.created_at).toLocaleTimeString()}
              </div>
              {checkpoint.state_summary && (
                <div className="text-[10px] text-gray-400 mt-1">
                  Step: {checkpoint.state_summary.step_count || 0}
                </div>
              )}
            </button>
          ))
        )}
      </div>
    </div>
  );
}
