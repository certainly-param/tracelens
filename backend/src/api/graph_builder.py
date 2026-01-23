"""Graph transformation logic for converting checkpoints/spans to React Flow format."""
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import NodeModel, EdgeModel, GraphResponse
from ..storage.db_manager import get_db_manager


class GraphBuilder:
    """Builds graph structure from checkpoint and span data."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_manager = get_db_manager(db_path)
    
    async def build_graph(self, thread_id: str) -> GraphResponse:
        """Build graph structure from checkpoints and spans."""
        await self.db_manager.initialize()
        
        # Get checkpoints
        checkpoints = await self._get_checkpoints(thread_id)
        
        # Get spans
        spans = await self._get_spans(thread_id)
        
        # Build nodes from spans (more detailed than checkpoints)
        nodes = self._build_nodes_from_spans(spans, checkpoints)
        
        # Build edges from span hierarchy (only between existing nodes)
        edges = self._build_edges_from_spans(spans, nodes)
        
        # Remove duplicate edges
        edges = self._deduplicate_edges(edges)
        
        # Determine metadata
        metadata = {
            "thread_id": thread_id,
            "start_time": checkpoints[0]["created_at"] if checkpoints else None,
            "end_time": checkpoints[-1]["created_at"] if checkpoints else None,
            "total_checkpoints": len(checkpoints),
            "total_spans": len(spans),
        }
        
        return GraphResponse(
            nodes=nodes,
            edges=edges,
            metadata=metadata,
        )
    
    async def _get_checkpoints(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all checkpoints for a thread."""
        async with self.db_manager.get_connection() as db:
            async with db.execute("""
                SELECT checkpoint_id, parent_checkpoint_id, created_at, metadata
                FROM checkpoints
                WHERE thread_id = ?
                ORDER BY created_at ASC
            """, (thread_id,)) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "checkpoint_id": row[0],
                        "parent_checkpoint_id": row[1],
                        "created_at": datetime.fromisoformat(row[2]) if isinstance(row[2], str) else row[2],
                        "metadata": json.loads(row[3]) if row[3] else {},
                    }
                    for row in rows
                ]
    
    async def _get_spans(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all spans for a thread."""
        async with self.db_manager.get_connection() as db:
            async with db.execute("""
                SELECT trace_id, span_id, parent_span_id, name,
                       start_time, end_time, attributes
                FROM traces
                WHERE thread_id = ?
                ORDER BY start_time ASC
            """, (thread_id,)) as cursor:
                rows = await cursor.fetchall()
                spans = []
                for row in rows:
                    start_time = row[4]
                    end_time = row[5]
                    if isinstance(start_time, str):
                        start_time = datetime.fromisoformat(start_time)
                    if isinstance(end_time, str) and end_time:
                        end_time = datetime.fromisoformat(end_time)
                    
                    duration = None
                    if start_time and end_time:
                        duration = (end_time - start_time).total_seconds()
                    
                    spans.append({
                        "trace_id": row[0],
                        "span_id": row[1],
                        "parent_span_id": row[2],
                        "name": row[3],
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": duration,
                        "attributes": json.loads(row[6]) if row[6] else {},
                    })
                return spans
    
    def _build_nodes_from_spans(
        self, 
        spans: List[Dict[str, Any]], 
        checkpoints: List[Dict[str, Any]]
    ) -> List[NodeModel]:
        """Build nodes from spans."""
        nodes = []
        node_map = {}  # Map span_id to node
        
        # Create nodes from agent node spans
        for span in spans:
            name = span["name"]
            if name.startswith("agent.node."):
                node_name = name.replace("agent.node.", "")
                span_id = span["span_id"]
                
                # Determine status
                status = "completed"
                if span["end_time"] is None:
                    status = "active"
                elif "error" in span["attributes"].get("status", "").lower():
                    status = "failed"
                
                node = NodeModel(
                    id=span_id,
                    label=node_name,
                    type="agent_node",
                    status=status,
                    timestamp=span["start_time"],
                    duration=span["duration"],
                    metadata={
                        "span_id": span_id,
                        "trace_id": span["trace_id"],
                        "attributes": span["attributes"],
                    }
                )
                nodes.append(node)
                node_map[span_id] = node
        
        # Add tool nodes
        for span in spans:
            name = span["name"]
            if name.startswith("agent.tool."):
                tool_name = name.replace("agent.tool.", "")
                span_id = span["span_id"]
                parent_span_id = span["parent_span_id"]
                
                # Find parent node
                parent_node = node_map.get(parent_span_id)
                if parent_node:
                    # Create tool node
                    status = "completed"
                    if span["end_time"] is None:
                        status = "active"
                    
                    node = NodeModel(
                        id=span_id,
                        label=tool_name,
                        type="tool_node",
                        status=status,
                        timestamp=span["start_time"],
                        duration=span["duration"],
                        metadata={
                            "span_id": span_id,
                            "parent_span_id": parent_span_id,
                            "attributes": span["attributes"],
                        }
                    )
                    nodes.append(node)
        
        return nodes
    
    def _build_edges_from_spans(
        self, 
        spans: List[Dict[str, Any]], 
        nodes: List[NodeModel]
    ) -> List[EdgeModel]:
        """Build edges from span hierarchy, only between existing nodes."""
        edges = []
        
        # Create a set of valid node IDs for quick lookup
        valid_node_ids = {node.id for node in nodes}
        
        # Map span_id to span for quick lookup
        span_map = {span["span_id"]: span for span in spans}
        
        # Build edges only between agent nodes (not tool nodes)
        # Connect agent nodes in execution order
        agent_spans = [
            span for span in spans 
            if span["name"].startswith("agent.node.") and span["span_id"] in valid_node_ids
        ]
        
        # Sort by start time to get execution order
        agent_spans.sort(key=lambda s: s["start_time"] if s["start_time"] else datetime.min)
        
        # Create edges between consecutive agent nodes
        for i in range(1, len(agent_spans)):
            prev_span = agent_spans[i - 1]
            curr_span = agent_spans[i]
            
            # Only create edge if both nodes exist
            if prev_span["span_id"] in valid_node_ids and curr_span["span_id"] in valid_node_ids:
                edge = EdgeModel(
                    source=prev_span["span_id"],
                    target=curr_span["span_id"],
                    condition="next",
                    label="execution",
                )
                edges.append(edge)
        
        # Also add parent-child edges for tool nodes (tool -> parent agent node)
        for span in spans:
            if span["name"].startswith("agent.tool.") and span["span_id"] in valid_node_ids:
                parent_span_id = span["parent_span_id"]
                if parent_span_id and parent_span_id in valid_node_ids:
                    edge = EdgeModel(
                        source=parent_span_id,
                        target=span["span_id"],
                        condition=None,
                        label=span["name"].replace("agent.tool.", ""),
                    )
                    edges.append(edge)
        
        return edges
    
    def _deduplicate_edges(self, edges: List[EdgeModel]) -> List[EdgeModel]:
        """Remove duplicate edges."""
        seen = set()
        unique_edges = []
        
        for edge in edges:
            key = (edge.source, edge.target)
            if key not in seen:
                seen.add(key)
                unique_edges.append(edge)
        
        return unique_edges
