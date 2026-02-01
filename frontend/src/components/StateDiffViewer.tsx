/** State diff viewer component for comparing checkpoint states. */
import { useEffect, useState } from 'react';
import { api } from '../lib/api';

interface StateDiffViewerProps {
  threadId: string;
  checkpointId1: string;
  checkpointId2: string;
}

export default function StateDiffViewer({
  threadId,
  checkpointId1,
  checkpointId2,
}: StateDiffViewerProps) {
  const [diff, setDiff] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchDiff() {
      try {
        setLoading(true);
        const data = await api.getCheckpointDiff(threadId, checkpointId1, checkpointId2);
        setDiff(data);
        setError(null);
      } catch (err: any) {
        setError(err.message || 'Failed to load diff');
      } finally {
        setLoading(false);
      }
    }

    if (threadId && checkpointId1 && checkpointId2) {
      fetchDiff();
    }
  }, [threadId, checkpointId1, checkpointId2]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">State Diff</h3>
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-gray-100 rounded"></div>
          <div className="h-4 bg-gray-100 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">State Diff</h3>
        <div className="text-red-600 text-xs bg-red-50 rounded p-2">{error}</div>
      </div>
    );
  }

  if (!diff) {
    return null;
  }

  const hasChanges =
    Object.keys(diff.added).length > 0 ||
    Object.keys(diff.removed).length > 0 ||
    Object.keys(diff.modified).length > 0;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">State Diff</h3>
      
      {!hasChanges ? (
        <div className="text-gray-400 text-xs text-center py-4">No changes</div>
      ) : (
        <div className="space-y-3 max-h-[500px] overflow-y-auto">
          {Object.keys(diff.added).length > 0 && (
            <div>
              <div className="text-xs font-semibold text-green-700 mb-1.5">Added</div>
              <div className="bg-green-50 border border-green-200 rounded p-2.5">
                <pre className="text-[10px] font-mono text-gray-700 whitespace-pre-wrap break-words">
                  {JSON.stringify(diff.added, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {Object.keys(diff.removed).length > 0 && (
            <div>
              <div className="text-xs font-semibold text-red-700 mb-1.5">Removed</div>
              <div className="bg-red-50 border border-red-200 rounded p-2.5">
                <pre className="text-[10px] font-mono text-gray-700 whitespace-pre-wrap break-words">
                  {JSON.stringify(diff.removed, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {Object.keys(diff.modified).length > 0 && (
            <div>
              <div className="text-xs font-semibold text-blue-700 mb-1.5">Modified</div>
              <div className="bg-blue-50 border border-blue-200 rounded p-2.5">
                <pre className="text-[10px] font-mono text-gray-700 whitespace-pre-wrap break-words">
                  {JSON.stringify(diff.modified, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
