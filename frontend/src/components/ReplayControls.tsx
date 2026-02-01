/** Replay controls component for step-by-step execution visualization. */
import { useState, useEffect } from 'react';
import { api, Checkpoint } from '../lib/api';

interface ReplayControlsProps {
  threadId: string;
  onCheckpointChange?: (checkpointId: string | null) => void;
}

export default function ReplayControls({
  threadId,
  onCheckpointChange,
}: ReplayControlsProps) {
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number>(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1000); // ms per step

  useEffect(() => {
    async function fetchCheckpoints() {
      try {
        const data = await api.listCheckpoints(threadId);
        setCheckpoints(data.checkpoints);
        if (data.checkpoints.length > 0 && currentIndex === -1) {
          setCurrentIndex(0);
          if (onCheckpointChange) {
            onCheckpointChange(data.checkpoints[0].checkpoint_id);
          }
        }
      } catch (err) {
        console.error('Failed to load checkpoints:', err);
      }
    }

    if (threadId) {
      fetchCheckpoints();
    }
  }, [threadId]);

  useEffect(() => {
    if (isPlaying && checkpoints.length > 0) {
      const interval = setInterval(() => {
        setCurrentIndex((prev) => {
          const next = prev + 1;
          if (next >= checkpoints.length) {
            setIsPlaying(false);
            return prev;
          }
          if (onCheckpointChange) {
            onCheckpointChange(checkpoints[next].checkpoint_id);
          }
          return next;
        });
      }, playbackSpeed);

      return () => clearInterval(interval);
    }
  }, [isPlaying, checkpoints, playbackSpeed, onCheckpointChange]);

  const handlePlay = () => {
    if (currentIndex >= checkpoints.length - 1) {
      setCurrentIndex(0);
      if (onCheckpointChange && checkpoints.length > 0) {
        onCheckpointChange(checkpoints[0].checkpoint_id);
      }
    }
    setIsPlaying(true);
  };

  const handlePause = () => {
    setIsPlaying(false);
  };

  const handleStepForward = () => {
    if (currentIndex < checkpoints.length - 1) {
      const next = currentIndex + 1;
      setCurrentIndex(next);
      if (onCheckpointChange) {
        onCheckpointChange(checkpoints[next].checkpoint_id);
      }
    }
  };

  const handleStepBackward = () => {
    if (currentIndex > 0) {
      const prev = currentIndex - 1;
      setCurrentIndex(prev);
      if (onCheckpointChange) {
        onCheckpointChange(checkpoints[prev].checkpoint_id);
      }
    }
  };

  const handleJumpToStart = () => {
    setCurrentIndex(0);
    setIsPlaying(false);
    if (onCheckpointChange && checkpoints.length > 0) {
      onCheckpointChange(checkpoints[0].checkpoint_id);
    }
  };

  const handleJumpToEnd = () => {
    const lastIndex = checkpoints.length - 1;
    setCurrentIndex(lastIndex);
    setIsPlaying(false);
    if (onCheckpointChange && checkpoints.length > 0) {
      onCheckpointChange(checkpoints[lastIndex].checkpoint_id);
    }
  };

  if (checkpoints.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Replay</h3>
        <div className="text-gray-400 text-xs text-center py-4">No checkpoints to replay</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">Replay</h3>
      
      <div className="space-y-3">
        {/* Progress bar */}
        <div>
          <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
            <span>Step {currentIndex + 1} of {checkpoints.length}</span>
            <span>{Math.round(((currentIndex + 1) / checkpoints.length) * 100)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-indigo-500 h-2 rounded-full transition-all"
              style={{ width: `${((currentIndex + 1) / checkpoints.length) * 100}%` }}
            ></div>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleJumpToStart}
            className="px-2 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 rounded border border-gray-300"
            title="Jump to start"
          >
            ⏮
          </button>
          <button
            onClick={handleStepBackward}
            disabled={currentIndex === 0}
            className="px-2 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 rounded border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Step backward"
          >
            ⏪
          </button>
          <button
            onClick={isPlaying ? handlePause : handlePlay}
            className="px-3 py-1.5 text-xs bg-indigo-500 hover:bg-indigo-600 text-white rounded font-medium"
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? '⏸ Pause' : '▶ Play'}
          </button>
          <button
            onClick={handleStepForward}
            disabled={currentIndex >= checkpoints.length - 1}
            className="px-2 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 rounded border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Step forward"
          >
            ⏩
          </button>
          <button
            onClick={handleJumpToEnd}
            className="px-2 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 rounded border border-gray-300"
            title="Jump to end"
          >
            ⏭
          </button>
        </div>

        {/* Speed control */}
        <div>
          <label className="text-xs text-gray-600 mb-1 block">Speed</label>
          <select
            value={playbackSpeed}
            onChange={(e) => {
              setPlaybackSpeed(Number(e.target.value));
              setIsPlaying(false);
            }}
            className="w-full text-xs border border-gray-300 rounded px-2 py-1.5 bg-white"
          >
            <option value="2000">0.5x (Slow)</option>
            <option value="1000">1x (Normal)</option>
            <option value="500">2x (Fast)</option>
            <option value="250">4x (Very Fast)</option>
          </select>
        </div>

        {/* Current checkpoint info */}
        {currentIndex >= 0 && checkpoints[currentIndex] && (
          <div className="text-xs text-gray-600 bg-gray-50 rounded p-2 border border-gray-200">
            <div className="font-medium mb-1">
              {new Date(checkpoints[currentIndex].created_at).toLocaleString()}
            </div>
            {checkpoints[currentIndex].state_summary && (
              <div className="text-[10px] text-gray-500">
                Step: {checkpoints[currentIndex].state_summary.step_count || 0}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
