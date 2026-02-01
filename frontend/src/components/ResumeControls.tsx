/**
 * ResumeControls component for resuming execution from checkpoints.
 * Supports resume and branch operations with optional state modifications.
 */
import React, { useState } from 'react';
import { api } from '../lib/api';

interface ResumeControlsProps {
  threadId: string;
  checkpointId: string;
  modifiedState?: Record<string, any>;
  onResume?: (newThreadId: string) => void;
  onBranch?: (branchThreadId: string) => void;
  onCancel?: () => void;
}

export const ResumeControls: React.FC<ResumeControlsProps> = ({
  threadId,
  checkpointId,
  modifiedState,
  onResume,
  onBranch,
  onCancel,
}) => {
  const [operation, setOperation] = useState<'resume' | 'branch'>('resume');
  const [branchName, setBranchName] = useState('');
  const [description, setDescription] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<{
    success: boolean;
    message: string;
    newThreadId?: string;
  } | null>(null);

  // Handle resume execution
  const handleResume = async () => {
    setIsProcessing(true);
    setResult(null);
    
    try {
      const response = await api.resumeExecution(
        threadId,
        checkpointId,
        modifiedState,
        description || undefined
      );

      setResult({
        success: response.success,
        message: response.message,
        newThreadId: response.new_thread_id,
      });

      if (response.success && onResume) {
        onResume(response.new_thread_id);
      }
    } catch (error) {
      console.error('Resume failed:', error);
      setResult({
        success: false,
        message: 'Failed to resume: ' + (error instanceof Error ? error.message : 'Unknown error'),
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle create branch
  const handleBranch = async () => {
    if (!branchName.trim()) {
      alert('Please enter a branch name');
      return;
    }

    setIsProcessing(true);
    setResult(null);
    
    try {
      const response = await api.createBranch(
        threadId,
        checkpointId,
        branchName,
        modifiedState,
        description || undefined
      );

      setResult({
        success: response.success,
        message: response.message,
        newThreadId: response.branch_thread_id,
      });

      if (response.success && onBranch) {
        onBranch(response.branch_thread_id);
      }
    } catch (error) {
      console.error('Branch creation failed:', error);
      setResult({
        success: false,
        message: 'Failed to create branch: ' + (error instanceof Error ? error.message : 'Unknown error'),
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle execute
  const handleExecute = () => {
    if (operation === 'resume') {
      handleResume();
    } else {
      handleBranch();
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-800">Resume Execution</h2>
        <button
          onClick={onCancel}
          className="text-gray-500 hover:text-gray-700"
        >
          ✕
        </button>
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          From Checkpoint
        </label>
        <div className="text-sm text-gray-600 font-mono bg-gray-50 p-2 rounded">
          {checkpointId}
        </div>
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Original Thread ID
        </label>
        <div className="text-sm text-gray-600 font-mono bg-gray-50 p-2 rounded">
          {threadId}
        </div>
      </div>

      {/* Operation Type */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Operation Type
        </label>
        <div className="flex gap-2">
          <button
            onClick={() => setOperation('resume')}
            className={`flex-1 px-4 py-2 rounded-md font-medium ${
              operation === 'resume'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Resume
          </button>
          <button
            onClick={() => setOperation('branch')}
            className={`flex-1 px-4 py-2 rounded-md font-medium ${
              operation === 'branch'
                ? 'bg-purple-500 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Create Branch
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          {operation === 'resume'
            ? 'Resume execution from this checkpoint in a new thread'
            : 'Create a named branch for A/B testing or exploration'}
        </p>
      </div>

      {/* Branch Name (only for branch operation) */}
      {operation === 'branch' && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Branch Name *
          </label>
          <input
            type="text"
            value={branchName}
            onChange={(e) => setBranchName(e.target.value)}
            placeholder="e.g., experiment_1, alternative_approach"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
        </div>
      )}

      {/* Description */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Description (optional)
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe the purpose of this operation..."
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          rows={3}
        />
      </div>

      {/* Modified State Info */}
      {modifiedState && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <div className="flex items-start">
            <span className="text-yellow-600 font-bold mr-2">⚠</span>
            <div>
              <p className="text-sm font-medium text-yellow-800">Modified State Detected</p>
              <p className="text-xs text-yellow-700 mt-1">
                This operation will use the modified state you edited.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Result Message */}
      {result && (
        <div
          className={`mb-4 p-3 rounded-md ${
            result.success
              ? 'bg-green-50 border border-green-200'
              : 'bg-red-50 border border-red-200'
          }`}
        >
          <p
            className={`text-sm font-medium ${
              result.success ? 'text-green-800' : 'text-red-800'
            }`}
          >
            {result.message}
          </p>
          {result.success && result.newThreadId && (
            <div className="mt-2">
              <p className="text-xs text-gray-600">New Thread ID:</p>
              <code className="text-xs bg-white px-2 py-1 rounded border border-gray-200">
                {result.newThreadId}
              </code>
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleExecute}
          disabled={isProcessing || (operation === 'branch' && !branchName.trim())}
          className={`flex-1 px-4 py-2 text-white rounded-md font-medium ${
            operation === 'resume'
              ? 'bg-blue-500 hover:bg-blue-600'
              : 'bg-purple-500 hover:bg-purple-600'
          } disabled:bg-gray-300 disabled:cursor-not-allowed`}
        >
          {isProcessing
            ? 'Processing...'
            : operation === 'resume'
            ? 'Resume Execution'
            : 'Create Branch'}
        </button>
        {onCancel && (
          <button
            onClick={onCancel}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Info Box */}
      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
        <p className="text-xs text-blue-800">
          <strong>Note:</strong> This operation creates a new thread with the checkpoint state.
          To actually execute the agent, you'll need to run it separately using the new thread ID.
        </p>
      </div>
    </div>
  );
};
