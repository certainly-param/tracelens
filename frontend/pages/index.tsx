import { useState } from 'react';
import Head from 'next/head';
import dynamic from 'next/dynamic';
import RunList from '../src/components/RunList';
import NodeDetails from '../src/components/NodeDetails';

// Dynamically import AgentGraph with SSR disabled (React Flow requires browser APIs)
const AgentGraph = dynamic(() => import('../src/components/AgentGraph'), {
  ssr: false,
});

export default function Home() {
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  return (
    <>
      <Head>
        <title>TraceLens - Agent Debugger</title>
        <meta name="description" content="Visual Debugger for LangGraph Agents" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-[1600px] mx-auto px-6 py-6">
          {/* Header */}
          <header className="mb-6">
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
              TraceLens
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              Visual Debugger for LangGraph Agents
            </p>
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

            {/* Main Graph View */}
            <div className="col-span-6">
              {selectedRun ? (
                <AgentGraph
                  threadId={selectedRun}
                  selectedNode={selectedNode}
                  onSelectNode={setSelectedNode}
                />
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

            {/* Node Details Sidebar */}
            <div className="col-span-3">
              {selectedNode && selectedRun ? (
                <NodeDetails
                  threadId={selectedRun}
                  nodeId={selectedNode}
                />
              ) : (
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                  <h3 className="text-sm font-semibold text-gray-900 mb-4">Node Details</h3>
                  <div className="text-center py-8">
                    <svg className="w-8 h-8 mx-auto text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-gray-400 text-xs">Click a node to view details</p>
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
