/**
 * StateEditor component for editing checkpoint state.
 * Provides a JSON editor with validation and save functionality.
 */
import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';

interface StateEditorProps {
  threadId: string;
  checkpointId: string;
  initialState?: Record<string, any>;
  onSave?: (newCheckpointId: string) => void;
  onCancel?: () => void;
}

interface ValidationError {
  field: string;
  message: string;
  severity: string;
}

export const StateEditor: React.FC<StateEditorProps> = ({
  threadId,
  checkpointId,
  initialState,
  onSave,
  onCancel,
}) => {
  const [stateJson, setStateJson] = useState('');
  const [isValid, setIsValid] = useState(true);
  const [parseError, setParseError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [validationWarnings, setValidationWarnings] = useState<ValidationError[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [description, setDescription] = useState('');

  // Load initial state
  useEffect(() => {
    if (initialState) {
      setStateJson(JSON.stringify(initialState, null, 2));
    } else {
      // Fetch checkpoint state
      api.getCheckpoint(threadId, checkpointId).then((data) => {
        setStateJson(JSON.stringify(data.state, null, 2));
      });
    }
  }, [threadId, checkpointId, initialState]);

  // Parse and validate JSON
  const handleStateChange = (value: string) => {
    setStateJson(value);
    
    try {
      JSON.parse(value);
      setIsValid(true);
      setParseError(null);
    } catch (e) {
      setIsValid(false);
      setParseError(e instanceof Error ? e.message : 'Invalid JSON');
    }
  };

  // Validate state with backend
  const validateState = async () => {
    if (!isValid) return;

    setIsValidating(true);
    try {
      const state = JSON.parse(stateJson);
      const result = await api.validateCheckpointState(threadId, checkpointId, state);
      
      setValidationErrors(result.errors);
      setValidationWarnings(result.warnings);
    } catch (error) {
      console.error('Validation failed:', error);
    } finally {
      setIsValidating(false);
    }
  };

  // Save modified state
  const handleSave = async () => {
    if (!isValid || validationErrors.length > 0) return;

    setIsSaving(true);
    try {
      const state = JSON.parse(stateJson);
      const result = await api.updateCheckpointState(
        threadId,
        checkpointId,
        state,
        description || undefined
      );

      if (result.success && onSave) {
        onSave(result.new_checkpoint_id);
      }
    } catch (error) {
      console.error('Save failed:', error);
      alert('Failed to save state: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-800">Edit Checkpoint State</h2>
        <button
          onClick={onCancel}
          className="text-gray-500 hover:text-gray-700"
        >
          ✕
        </button>
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Checkpoint ID
        </label>
        <div className="text-sm text-gray-600 font-mono bg-gray-50 p-2 rounded">
          {checkpointId}
        </div>
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Description (optional)
        </label>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe your changes..."
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="flex-1 mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          State (JSON)
        </label>
        <textarea
          value={stateJson}
          onChange={(e) => handleStateChange(e.target.value)}
          className={`w-full h-full font-mono text-sm p-3 border rounded-md focus:outline-none focus:ring-2 ${
            isValid ? 'border-gray-300 focus:ring-blue-500' : 'border-red-500 focus:ring-red-500'
          }`}
          style={{ minHeight: '300px' }}
        />
        {parseError && (
          <div className="mt-2 text-sm text-red-600">
            Parse Error: {parseError}
          </div>
        )}
      </div>

      {/* Validation Results */}
      {(validationErrors.length > 0 || validationWarnings.length > 0) && (
        <div className="mb-4 space-y-2">
          {validationErrors.map((error, idx) => (
            <div key={`error-${idx}`} className="flex items-start p-2 bg-red-50 border border-red-200 rounded">
              <span className="text-red-600 font-bold mr-2">✕</span>
              <div>
                <span className="font-medium text-red-800">{error.field}:</span>{' '}
                <span className="text-red-700">{error.message}</span>
              </div>
            </div>
          ))}
          {validationWarnings.map((warning, idx) => (
            <div key={`warning-${idx}`} className="flex items-start p-2 bg-yellow-50 border border-yellow-200 rounded">
              <span className="text-yellow-600 font-bold mr-2">⚠</span>
              <div>
                <span className="font-medium text-yellow-800">{warning.field}:</span>{' '}
                <span className="text-yellow-700">{warning.message}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={validateState}
          disabled={!isValid || isValidating}
          className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          {isValidating ? 'Validating...' : 'Validate'}
        </button>
        <button
          onClick={handleSave}
          disabled={!isValid || validationErrors.length > 0 || isSaving}
          className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          {isSaving ? 'Saving...' : 'Save Changes'}
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
    </div>
  );
};
