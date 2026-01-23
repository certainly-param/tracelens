/** Run list component. */
import { useEffect, useState } from 'react';
import { api, Run } from '../lib/api';

interface RunListProps {
  selectedRun: string | null;
  onSelectRun: (threadId: string | null) => void;
}

export default function RunList({ selectedRun, onSelectRun }: RunListProps) {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchRuns() {
      try {
        setLoading(true);
        const data = await api.listRuns();
        setRuns(data.runs);
        setError(null);
      } catch (err: any) {
        setError(err.message || 'Failed to load runs');
      } finally {
        setLoading(false);
      }
    }

    fetchRuns();
    const interval = setInterval(fetchRuns, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Runs</h3>
        <div className="animate-pulse space-y-2">
          <div className="h-10 bg-gray-100 rounded"></div>
          <div className="h-10 bg-gray-100 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Runs</h3>
        <div className="text-red-600 text-xs bg-red-50 rounded p-2">{error}</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Runs</h3>
      <div className="space-y-3">
        {runs.length === 0 ? (
          <div className="text-gray-400 text-xs text-center py-6">
            No runs found
          </div>
        ) : (
          runs.map((run) => (
            <button
              key={run.thread_id}
              onClick={() =>
                onSelectRun(selectedRun === run.thread_id ? null : run.thread_id)
              }
              className={`
                block w-full text-left rounded-lg border px-3 py-3 transition-colors
                ${selectedRun === run.thread_id
                  ? 'bg-indigo-50 border-indigo-300 shadow-sm'
                  : 'bg-white border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }
              `}
            >
              <div className="text-xs font-semibold text-gray-900 break-words mb-1">
                {run.thread_id}
              </div>
              <div className="text-[11px] text-gray-600 mb-0.5">
                {run.span_count} spans
              </div>
              <div className="text-[10px] text-gray-500">
                {new Date(run.last_updated).toLocaleString()}
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
