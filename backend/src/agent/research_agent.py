"""Sample Research Agent demonstrating common failure modes."""
import os
import time
from typing import TypedDict, Annotated, Literal
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from ..storage import SqliteCheckpointer
from ..instrumentation import instrument_node_execution, instrument_tool_call


# State schema
class AgentState(TypedDict):
    """State schema for the research agent."""
    query: str
    results: Annotated[list[str], "List of search results"]
    summary: str
    step_count: int
    needs_more_info: bool
    error_count: int
    last_error: str
    thread_id: str  # Added for instrumentation


# Tools
@tool
def web_search(query: str) -> str:
    """Search the web for information. Returns mock results for demonstration.
    
    This is a mock tool that simulates web search. In a real scenario,
    this would call an actual search API.
    """
    # Simulate some delay
    time.sleep(0.1)
    
    # Mock results - intentionally can return incomplete results
    mock_results = {
        "python async": "Python async/await allows concurrent execution...",
        "langgraph": "LangGraph is a library for building stateful agent workflows...",
        "opentelemetry": "OpenTelemetry provides observability standards...",
    }
    
    # Simulate failure mode: return empty for certain queries
    if "xyz123" in query.lower():
        return "No results found"
    
    # Return partial results to trigger "needs_more_info" loop
    result = mock_results.get(query.lower(), f"Some information about {query}")
    return result


@tool
def summarize_results(results: list[str]) -> str:
    """Summarize a list of search results into a coherent summary."""
    if not results:
        return "No results to summarize"
    
    combined = " ".join(results)
    # Simple mock summarization
    return f"Summary: {combined[:200]}..."


@tool
def retrieve_document(doc_id: str) -> str:
    """Retrieve a document by ID. Mock implementation."""
    # Simulate failure: return error for certain IDs
    if doc_id == "error_doc":
        raise ValueError("Document not found")
    
    return f"Document content for {doc_id}: This is a sample document..."


def should_continue(state: AgentState) -> Literal["search", "summarize", "end"]:
    """Determine next step based on state."""
    step_count = state.get("step_count", 0)
    needs_more_info = state.get("needs_more_info", False)
    error_count = state.get("error_count", 0)
    
    # Failure mode: can get stuck in loop if needs_more_info is always True
    if step_count > 10:  # Prevent infinite loops in demo
        return "end"
    
    if error_count > 3:  # Too many errors
        return "end"
    
    if not state.get("results"):
        return "search"
    
    if needs_more_info and step_count < 5:  # Can loop here
        return "search"
    
    if not state.get("summary"):
        return "summarize"
    
    return "end"


async def search_node(state: AgentState) -> AgentState:
    """Node that performs web search."""
    query = state.get("query", "")
    step_count = state.get("step_count", 0)
    thread_id = state.get("thread_id", "default")
    
    # Instrument node execution
    with instrument_node_execution("search", thread_id) as node_span:
        node_span.set_state_snapshot(state)
        
        try:
            # Instrument tool call
            with instrument_tool_call("web_search", thread_id) as tool_span:
                tool_span.set_tool_input({"query": query})
                result = web_search.invoke({"query": query})
                tool_span.set_tool_output(result)
            
            current_results = state.get("results", [])
            if result and result != "No results found":
                current_results.append(result)
            
            # Simulate "needs_more_info" - can cause loops
            needs_more_info = len(current_results) < 2 or step_count < 3
            
            new_state = {
                **state,
                "results": current_results,
                "step_count": step_count + 1,
                "needs_more_info": needs_more_info,
                "error_count": 0,
            }
            node_span.set_state_snapshot(new_state)
            return new_state
        except Exception as e:
            new_state = {
                **state,
                "step_count": step_count + 1,
                "error_count": state.get("error_count", 0) + 1,
                "last_error": str(e),
            }
            return new_state


async def summarize_node(state: AgentState) -> AgentState:
    """Node that summarizes results."""
    results = state.get("results", [])
    step_count = state.get("step_count", 0)
    thread_id = state.get("thread_id", "default")
    
    # Instrument node execution
    with instrument_node_execution("summarize", thread_id) as node_span:
        node_span.set_state_snapshot(state)
        
        try:
            # Instrument tool call
            with instrument_tool_call("summarize_results", thread_id) as tool_span:
                tool_span.set_tool_input({"results": results})
                summary = summarize_results.invoke({"results": results})
                tool_span.set_tool_output(summary)
            
            new_state = {
                **state,
                "summary": summary,
                "step_count": step_count + 1,
                "needs_more_info": False,
            }
            node_span.set_state_snapshot(new_state)
            return new_state
        except Exception as e:
            new_state = {
                **state,
                "step_count": step_count + 1,
                "error_count": state.get("error_count", 0) + 1,
                "last_error": str(e),
            }
            return new_state


def create_research_agent(checkpointer: SqliteCheckpointer) -> StateGraph:
    """Create and compile the research agent graph."""
    # Get API key from environment
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY must be set")
    
    # Get model from environment or use default
    model_name = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    
    # Initialize LLM
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.7,
    )
    
    # Bind tools to LLM
    tools = [web_search, summarize_results, retrieve_document]
    llm_with_tools = llm.bind_tools(tools)
    
    # Create graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("search", search_node)
    workflow.add_node("summarize", summarize_node)
    
    # Set entry point
    workflow.set_entry_point("search")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "search",
        should_continue,
        {
            "search": "search",
            "summarize": "summarize",
            "end": END,
        }
    )
    
    workflow.add_conditional_edges(
        "summarize",
        should_continue,
        {
            "search": "search",
            "summarize": "summarize",
            "end": END,
        }
    )
    
    # Compile with checkpointer
    app = workflow.compile(checkpointer=checkpointer)
    
    return app
