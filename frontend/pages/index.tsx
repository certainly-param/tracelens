import { useState } from 'react';
import Head from 'next/head';
import dynamic from 'next/dynamic';
import RunList from '../src/components/RunList';
import NodeDetails from '../src/components/NodeDetails';
import CheckpointBrowser from '../src/components/CheckpointBrowser';
import StateDiffViewer from '../src/components/StateDiffViewer';
import TimelineView from '../src/components/TimelineView';
import ReplayControls from '../src/components/ReplayControls';
import { StateEditor } from '../src/components/StateEditor';
import { PromptEditor } from '../src/components/PromptEditor';
import { ResumeControls } from '../src/components/ResumeControls';

// Dynamically import AgentGraph with SSR disabled (React Flow requires browser APIs)
const AgentGraph = dynamic(() => import('../src/components/AgentGraph'), {
  ssr: false,
});

type ViewMode = 'graph' | 'checkpoints' | 'timeline' | 'replay' | 'edit';

export default function Home() {
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<string | null>(null);
  const [compareCheckpoint, setCompareCheckpoint] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('graph');
  const [editMode, setEditMode] = useState<'state' | 'prompt' | 'resume' | null>(null);
  const [modifiedState, setModifiedState] = useState<Record<string, any> | null>(null);

  return (
    <>
      <Head>
        <title>TraceLens - Agent Debugger</title>
        <meta name="description" content="Visual Debugger for LangGraph Agents" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/tracelens_logo.png" type="image/png" />
      </Head>
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-[1600px] mx-auto px-6 py-6">
          {/* Header */}
          <header className="mb-6 flex items-center gap-3">
            <img src="/tracelens_logo.png" alt="TraceLens" className="h-10 w-auto" />
            <div>
              <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
                TraceLens
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Visual Debugger for LangGraph Agents
              </p>
            </div>
          </header>

          {/* Main Layout */}
          <div className="grid grid-cols-12 gap-4">
            {/* Run List Sidebar */}
            <div className="col-span-3">
              <RunList
                selectedRun={selectedRun}
                onSelectRun={setSelectedRun}
              />
            </div>

            {/* Main Content Area */}
            <div className="col-span-6">
              {selectedRun ? (
                <>
                  {/* View Mode Tabs */}
                  <div className="bg-white rounded-lg border border-gray-200 mb-4">
                    <div className="flex border-b border-gray-200">
                      {(['graph', 'checkpoints', 'timeline', 'replay', 'edit'] as ViewMode[]).map((mode) => (
                        <button
                          key={mode}
                          onClick={() => setViewMode(mode)}
                          className={`
                            flex-1 px-4 py-2 text-xs font-medium transition-colors
                            ${viewMode === mode
                              ? 'bg-indigo-50 text-indigo-700 border-b-2 border-indigo-500'
                              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                            }
                          `}
                        >
                          {mode.charAt(0).toUpperCase() + mode.slice(1)}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* View Content */}
                  {viewMode === 'graph' && (
                    <AgentGraph
                      threadId={selectedRun}
                      selectedNode={selectedNode}
                      onSelectNode={setSelectedNode}
                    />
                  )}

                  {viewMode === 'checkpoints' && (
                    <div className="space-y-4">
                      <CheckpointBrowser
                        threadId={selectedRun}
                        selectedCheckpoint={selectedCheckpoint}
                        onSelectCheckpoint={setSelectedCheckpoint}
                      />
                      {selectedCheckpoint && (
                        <div className="space-y-2">
                          <div className="text-xs text-gray-600">Compare with:</div>
                          <CheckpointBrowser
                            threadId={selectedRun}
                            selectedCheckpoint={compareCheckpoint}
                            onSelectCheckpoint={setCompareCheckpoint}
                          />
                          {compareCheckpoint && selectedCheckpoint !== compareCheckpoint && (
                            <StateDiffViewer
                              threadId={selectedRun}
                              checkpointId1={selectedCheckpoint}
                              checkpointId2={compareCheckpoint}
                            />
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {viewMode === 'timeline' && (
                    <TimelineView
                      threadId={selectedRun}
                      onJumpToCheckpoint={(cpId) => {
                        setSelectedCheckpoint(cpId);
                        setViewMode('checkpoints');
                      }}
                      onJumpToSpan={(spanId) => {
                        setSelectedNode(spanId);
                        setViewMode('graph');
                      }}
                    />
                  )}

                  {viewMode === 'replay' && (
                    <ReplayControls
                      threadId={selectedRun}
                      onCheckpointChange={setSelectedCheckpoint}
                    />
                  )}

                  {viewMode === 'edit' && (
                    <div className="space-y-4">
                      {!editMode && (
                        <div className="bg-white rounded-lg border border-gray-200 p-6">
                          <h2 className="text-lg font-bold text-gray-800 mb-4">
                            Active Intervention
                          </h2>
                          <p className="text-sm text-gray-600 mb-6">
                            Select a checkpoint from the Checkpoints tab, then choose an operation:
                          </p>
                          
                          {selectedCheckpoint ? (
                            <div className="space-y-3">
                              <div className="text-xs text-gray-500 mb-4">
                                Selected checkpoint: <code className="bg-gray-100 px-2 py-1 rounded">{selectedCheckpoint.substring(0, 16)}...</code>
                              </div>
                              
                              <button
                                onClick={() => setEditMode('state')}
                                className="w-full px-4 py-3 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-left"
                              >
                                <div className="font-medium">Edit State</div>
                                <div className="text-xs opacity-90 mt-1">Modify checkpoint state (JSON editor)</div>
                              </button>
                              
                              <button
                                onClick={() => setEditMode('prompt')}
                                className="w-full px-4 py-3 bg-purple-500 text-white rounded-md hover:bg-purple-600 text-left"
                              >
                                <div className="font-medium">Edit Prompts</div>
                                <div className="text-xs opacity-90 mt-1">Modify agent prompts and instructions</div>
                              </button>
                              
                              <button
                                onClick={() => setEditMode('resume')}
                                className="w-full px-4 py-3 bg-green-500 text-white rounded-md hover:bg-green-600 text-left"
                              >
                                <div className="font-medium">Resume / Branch</div>
                                <div className="text-xs opacity-90 mt-1">Resume execution or create a branch</div>
                              </button>
                            </div>
                          ) : (
                            <div className="text-center py-8 text-gray-400 text-sm">
                              Go to Checkpoints tab and select a checkpoint first
                            </div>
                          )}
                        </div>
                      )}

                      {editMode === 'state' && selectedCheckpoint && (
                        <StateEditor
                          threadId={selectedRun}
                          checkpointId={selectedCheckpoint}
                          onSave={(newCheckpointId) => {
                            setSelectedCheckpoint(newCheckpointId);
                            setEditMode(null);
                            alert(`State saved! New checkpoint: ${newCheckpointId}`);
                          }}
                          onCancel={() => setEditMode(null)}
                        />
                      )}

                      {editMode === 'prompt' && selectedCheckpoint && (
                        <PromptEditor
                          threadId={selectedRun}
                          checkpointId={selectedCheckpoint}
                          onSave={(newCheckpointId) => {
                            setSelectedCheckpoint(newCheckpointId);
                            setEditMode(null);
                            alert(`Prompts saved! New checkpoint: ${newCheckpointId}`);
                          }}
                          onCancel={() => setEditMode(null)}
                        />
                      )}

                      {editMode === 'resume' && selectedCheckpoint && (
                        <ResumeControls
                          threadId={selectedRun}
                          checkpointId={selectedCheckpoint}
                          modifiedState={modifiedState || undefined}
                          onResume={(newThreadId) => {
                            alert(`Execution resumed! New thread ID: ${newThreadId}\n\nRun your agent with this thread ID to continue.`);
                            setEditMode(null);
                          }}
                          onBranch={(branchThreadId) => {
                            alert(`Branch created! Branch thread ID: ${branchThreadId}\n\nRun your agent with this thread ID for the branch.`);
                            setEditMode(null);
                          }}
                          onCancel={() => setEditMode(null)}
                        />
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div className="bg-white rounded-lg border border-gray-200 h-[600px] flex items-center justify-center">
                  <div className="text-center">
                    <svg className="w-10 h-10 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                    <p className="text-gray-500 text-sm">Select a run to view graph</p>
                  </div>
                </div>
              )}
            </div>

            {/* Right Sidebar */}
            <div className="col-span-3 space-y-4">
              {selectedNode && selectedRun && viewMode === 'graph' ? (
                <NodeDetails
                  threadId={selectedRun}
                  nodeId={selectedNode}
                />
              ) : selectedCheckpoint && selectedRun && viewMode === 'checkpoints' ? (
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h3 className="text-sm font-semibold text-gray-900 mb-3">Checkpoint Details</h3>
                  <div className="text-xs text-gray-600 space-y-2">
                    <div>
                      <span className="font-medium">ID:</span>{' '}
                      <span className="font-mono">{selectedCheckpoint.substring(0, 16)}...</span>
                    </div>
                    <div>
                      <span className="font-medium">View:</span>{' '}
                      <button
                        onClick={() => {
                          // Could navigate to full checkpoint view
                        }}
                        className="text-indigo-600 hover:text-indigo-700 underline"
                      >
                        Full State
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                  <h3 className="text-sm font-semibold text-gray-900 mb-4">
                    {viewMode === 'graph' ? 'Node Details' : 'Details'}
                  </h3>
                  <div className="text-center py-8">
                    <svg className="w-8 h-8 mx-auto text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-gray-400 text-xs">
                      {viewMode === 'graph' 
                        ? 'Click a node to view details'
                        : 'Select an item to view details'
                      }
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
