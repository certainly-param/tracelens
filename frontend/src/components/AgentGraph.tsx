/** Agent Graph visualization using React Flow. */
import { useCallback, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Node,
  Edge,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  NodeTypes,
  Handle,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { useAgentGraph } from '../hooks/useAgentGraph';
import { Node as ApiNode } from '../lib/api';

interface AgentGraphProps {
  threadId: string;
  selectedNode: string | null;
  onSelectNode: (nodeId: string | null) => void;
}

// Clean, minimal node component
const CustomNode = ({ data, selected }: any) => {
  const statusColors: Record<string, { bg: string; border: string; text: string }> = {
    pending: { bg: '#fafafa', border: '#e5e7eb', text: '#6b7280' },
    active: { bg: '#eff6ff', border: '#3b82f6', text: '#1d4ed8' },
    completed: { bg: '#f0fdf4', border: '#22c55e', text: '#15803d' },
    failed: { bg: '#fef2f2', border: '#ef4444', text: '#dc2626' },
  };

  const status = data.status || 'pending';
  const type = data.type || 'agent_node';
  const duration = data.duration;
  const colors = statusColors[status] || statusColors.pending;

  return (
    <div
      className={`
        rounded-md transition-all
        ${selected ? 'ring-2 ring-indigo-400 ring-offset-1' : ''}
        ${type === 'tool_node' ? 'border-dashed' : 'border-solid'}
      `}
      style={{
        backgroundColor: colors.bg,
        border: `1.5px ${type === 'tool_node' ? 'dashed' : 'solid'} ${colors.border}`,
        minWidth: '100px',
        padding: '10px 14px',
      }}
    >
      <Handle
        type="source"
        position={Position.Top}
        style={{ background: '#94a3b8', width: 6, height: 6, border: 'none' }}
      />
      
      <div className="flex flex-col items-center justify-center">
        <div 
          className="font-medium text-center"
          style={{ color: '#1f2937', lineHeight: '1.4', fontSize: '13px' }}
        >
          {data.label}
        </div>
      </div>
      
      <Handle
        type="target"
        position={Position.Bottom}
        style={{ background: '#94a3b8', width: 6, height: 6, border: 'none' }}
      />
    </div>
  );
};

const nodeTypes: NodeTypes = {
  custom: CustomNode,
};

// Auto-layout function using dagre
function getLayoutedElements(nodes: Node[], edges: Edge[]) {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 40, ranksep: 60 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 120, height: 50 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - 60,
        y: nodeWithPosition.y - 25,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

export default function AgentGraph({
  threadId,
  selectedNode,
  onSelectNode,
}: AgentGraphProps) {
  const { graph, loading, error } = useAgentGraph(threadId);

  const { nodes: flowNodes, edges: flowEdges } = useMemo(() => {
    if (!graph) {
      return { nodes: [], edges: [] };
    }

    const nodes: Node[] = graph.nodes.map((apiNode: ApiNode) => ({
      id: apiNode.id,
      type: 'custom',
      data: {
        label: apiNode.label,
        type: apiNode.type,
        status: apiNode.status,
        duration: apiNode.duration,
        metadata: apiNode.metadata,
      },
      position: { x: 0, y: 0 },
    }));

    const edges: Edge[] = graph.edges
      .filter((edge) => {
        const sourceExists = nodes.some((n) => n.id === edge.source);
        const targetExists = nodes.some((n) => n.id === edge.target);
        return sourceExists && targetExists;
      })
      .map((edge) => ({
        id: `${edge.source}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        type: 'smoothstep',
        animated: edge.label === 'execution',
        style: { strokeWidth: 1.5, stroke: '#94a3b8' },
      }));

    return getLayoutedElements(nodes, edges);
  }, [graph]);

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  useEffect(() => {
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [flowNodes, flowEdges, setNodes, setEdges]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onSelectNode(node.id === selectedNode ? null : node.id);
    },
    [selectedNode, onSelectNode]
  );

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 h-[600px] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-gray-200 border-t-indigo-500 mx-auto"></div>
          <p className="mt-3 text-gray-400 text-sm">Loading...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 h-[600px] flex items-center justify-center">
        <p className="text-red-500 text-sm">{error}</p>
      </div>
    );
  }

  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 h-[600px] flex items-center justify-center">
        <p className="text-gray-400 text-sm">No graph data</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200" style={{ height: '600px' }}>
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          attributionPosition="bottom-left"
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#f1f5f9" gap={16} size={1} />
          <Controls showMiniMap={false} className="!border-gray-200 !shadow-none" />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}
