/**
 * PromptEditor component for modifying node prompts and instructions.
 * Allows editing of system prompts, user instructions, and tool configurations.
 */
import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';

interface PromptEditorProps {
  threadId: string;
  checkpointId: string;
  onSave?: (newCheckpointId: string) => void;
  onCancel?: () => void;
}

interface PromptField {
  key: string;
  label: string;
  value: string;
  type: 'text' | 'textarea';
  description?: string;
}

export const PromptEditor: React.FC<PromptEditorProps> = ({
  threadId,
  checkpointId,
  onSave,
  onCancel,
}) => {
  const [state, setState] = useState<Record<string, any>>({});
  const [prompts, setPrompts] = useState<PromptField[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [description, setDescription] = useState('');

  // Load checkpoint state and extract prompt fields
  useEffect(() => {
    const loadState = async () => {
      try {
        const data = await api.getCheckpoint(threadId, checkpointId);
        setState(data.state);

        // Extract prompt-related fields from state
        const promptFields: PromptField[] = [];

        // Common prompt fields in agent state
        if (data.state.query) {
          promptFields.push({
            key: 'query',
            label: 'Query / Task',
            value: data.state.query,
            type: 'textarea',
            description: 'The main query or task for the agent',
          });
        }

        if (data.state.system_prompt) {
          promptFields.push({
            key: 'system_prompt',
            label: 'System Prompt',
            value: data.state.system_prompt,
            type: 'textarea',
            description: 'System-level instructions for the agent',
          });
        }

        if (data.state.instructions) {
          promptFields.push({
            key: 'instructions',
            label: 'Instructions',
            value: data.state.instructions,
            type: 'textarea',
            description: 'Specific instructions for the current task',
          });
        }

        if (data.state.context) {
          promptFields.push({
            key: 'context',
            label: 'Context',
            value: typeof data.state.context === 'string' 
              ? data.state.context 
              : JSON.stringify(data.state.context, null, 2),
            type: 'textarea',
            description: 'Additional context for the agent',
          });
        }

        // If no prompt fields found, show a message
        if (promptFields.length === 0) {
          promptFields.push({
            key: 'query',
            label: 'Query / Task',
            value: data.state.query || '',
            type: 'textarea',
            description: 'Add or modify the agent query',
          });
        }

        setPrompts(promptFields);
      } catch (error) {
        console.error('Failed to load checkpoint:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadState();
  }, [threadId, checkpointId]);

  // Update prompt field
  const handlePromptChange = (key: string, value: string) => {
    setPrompts((prev) =>
      prev.map((p) => (p.key === key ? { ...p, value } : p))
    );
  };

  // Save modified prompts
  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Update state with modified prompts
      const modifiedState = { ...state };
      prompts.forEach((prompt) => {
        // Try to parse as JSON if it looks like JSON
        if (prompt.value.trim().startsWith('{') || prompt.value.trim().startsWith('[')) {
          try {
            modifiedState[prompt.key] = JSON.parse(prompt.value);
          } catch {
            modifiedState[prompt.key] = prompt.value;
          }
        } else {
          modifiedState[prompt.key] = prompt.value;
        }
      });

      const result = await api.updateCheckpointState(
        threadId,
        checkpointId,
        modifiedState,
        description || 'Modified prompts/instructions'
      );

      if (result.success && onSave) {
        onSave(result.new_checkpoint_id);
      }
    } catch (error) {
      console.error('Save failed:', error);
      alert('Failed to save prompts: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500">Loading checkpoint state...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-800">Edit Prompts & Instructions</h2>
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

      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {prompts.map((prompt) => (
          <div key={prompt.key} className="border border-gray-200 rounded-lg p-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {prompt.label}
            </label>
            {prompt.description && (
              <p className="text-xs text-gray-500 mb-2">{prompt.description}</p>
            )}
            {prompt.type === 'textarea' ? (
              <textarea
                value={prompt.value}
                onChange={(e) => handlePromptChange(prompt.key, e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                rows={6}
              />
            ) : (
              <input
                type="text"
                value={prompt.value}
                onChange={(e) => handlePromptChange(prompt.key, e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            )}
          </div>
        ))}
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={isSaving}
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
