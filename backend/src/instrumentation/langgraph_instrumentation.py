"""LangGraph-specific OpenTelemetry instrumentation."""
import asyncio
from typing import Any, Dict, Optional
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .otel_setup import get_tracer


tracer = get_tracer("langgraph")


def instrument_node_execution(node_name: str, thread_id: str):
    """Create a context manager for instrumenting node execution."""
    return NodeExecutionSpan(node_name, thread_id)


class NodeExecutionSpan:
    """Context manager for instrumenting LangGraph node execution."""
    
    def __init__(self, node_name: str, thread_id: str):
        self.node_name = node_name
        self.thread_id = thread_id
        self.span: Optional[trace.Span] = None
        self._context_token = None
        self._span_context = None
    
    def __enter__(self):
        """Enter the span context."""
        self.span = tracer.start_span(
            f"agent.node.{self.node_name}",
            attributes={
                "node_id": self.node_name,
                "thread_id": self.thread_id,
                "langgraph.node": self.node_name,
            }
        )
        # Use the span in context - store the context manager
        self._span_context = trace.use_span(self.span, end_on_exit=False)
        self._context_token = self._span_context.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the span context."""
        if self._span_context:
            try:
                self._span_context.__exit__(exc_type, exc_val, exc_tb)
            except:
                pass
        
        if self.span:
            if exc_type:
                self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
                self.span.record_exception(exc_val)
            else:
                self.span.set_status(Status(StatusCode.OK))
            
            self.span.end()
    
    def set_state_snapshot(self, state: Dict[str, Any]):
        """Add state snapshot to span attributes."""
        if self.span:
            # Store a summary of state (not full state to avoid bloat)
            self.span.set_attribute("state.step_count", state.get("step_count", 0))
            self.span.set_attribute("state.has_results", bool(state.get("results")))
            self.span.set_attribute("state.has_summary", bool(state.get("summary")))
            self.span.set_attribute("state.needs_more_info", state.get("needs_more_info", False))
            self.span.set_attribute("state.error_count", state.get("error_count", 0))


def instrument_tool_call(tool_name: str, thread_id: str):
    """Create a context manager for instrumenting tool calls."""
    return ToolCallSpan(tool_name, thread_id)


class ToolCallSpan:
    """Context manager for instrumenting tool execution."""
    
    def __init__(self, tool_name: str, thread_id: str):
        self.tool_name = tool_name
        self.thread_id = thread_id
        self.span: Optional[trace.Span] = None
        self._context_token = None
        self._span_context = None
    
    def __enter__(self):
        """Enter the span context."""
        self.span = tracer.start_span(
            f"agent.tool.{self.tool_name}",
            attributes={
                "tool.name": self.tool_name,
                "thread_id": self.thread_id,
                "langgraph.tool": self.tool_name,
            }
        )
        # Use the span in context - store the context manager
        self._span_context = trace.use_span(self.span, end_on_exit=False)
        self._context_token = self._span_context.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the span context."""
        if self._span_context:
            try:
                self._span_context.__exit__(exc_type, exc_val, exc_tb)
            except:
                pass
        
        if self.span:
            if exc_type:
                self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
                self.span.record_exception(exc_val)
            else:
                self.span.set_status(Status(StatusCode.OK))
            
            self.span.end()
    
    def set_tool_input(self, input_data: Dict[str, Any]):
        """Add tool input to span attributes."""
        if self.span:
            # Store input summary
            for key, value in input_data.items():
                if isinstance(value, (str, int, float, bool)):
                    self.span.set_attribute(f"tool.input.{key}", str(value)[:200])
    
    def set_tool_output(self, output: Any):
        """Add tool output to span attributes."""
        if self.span:
            output_str = str(output)[:500]  # Limit output size
            self.span.set_attribute("tool.output", output_str)
