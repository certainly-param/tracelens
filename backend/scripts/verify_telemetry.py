"""Verification script to test end-to-end telemetry collection."""
import asyncio
import os
import sys
from pathlib import Path
import json
from datetime import datetime

# Fix Windows console encoding for emoji characters
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Load environment variables from .env file
from dotenv import load_dotenv
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / '.env')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage import SqliteCheckpointer, get_db_manager
from src.agent import create_research_agent, AgentState
from src.instrumentation import setup_opentelemetry


async def verify_checkpoints(db_path: str, thread_id: str):
    """Verify checkpoint chain in database."""
    print("\n" + "="*60)
    print("CHECKPOINT VERIFICATION")
    print("="*60)
    
    db_manager = get_db_manager(db_path)
    await db_manager.initialize()
    
    async with db_manager.get_connection() as db:
        async with db.execute("""
            SELECT checkpoint_id, parent_checkpoint_id, created_at, 
                   LENGTH(checkpoint_data) as data_size
            FROM checkpoints
            WHERE thread_id = ?
            ORDER BY created_at ASC
        """, (thread_id,)) as cursor:
            checkpoints = await cursor.fetchall()
            
            if not checkpoints:
                print(f"❌ No checkpoints found for thread_id: {thread_id}")
                return False
            
            print(f"✅ Found {len(checkpoints)} checkpoints")
            print("\nCheckpoint Chain:")
            print("-" * 60)
            
            for i, (cp_id, parent_id, created_at, data_size) in enumerate(checkpoints, 1):
                parent_info = f"parent: {parent_id[:8]}..." if parent_id else "root"
                print(f"{i}. {cp_id[:16]}... | {parent_info} | {created_at} | {data_size} bytes")
            
            # Verify chain integrity
            checkpoint_ids = {cp[0] for cp in checkpoints}
            for cp_id, parent_id, _, _ in checkpoints:
                if parent_id and parent_id not in checkpoint_ids:
                    print(f"⚠️  Warning: Checkpoint {cp_id[:8]}... has missing parent {parent_id[:8]}...")
            
            return True


async def verify_spans(db_path: str, thread_id: str):
    """Verify OpenTelemetry spans in database."""
    print("\n" + "="*60)
    print("SPAN VERIFICATION")
    print("="*60)
    
    db_manager = get_db_manager(db_path)
    await db_manager.initialize()
    
    async with db_manager.get_connection() as db:
        # Get all spans for this thread
        async with db.execute("""
            SELECT trace_id, span_id, parent_span_id, name, 
                   start_time, end_time, attributes
            FROM traces
            WHERE thread_id = ?
            ORDER BY start_time ASC
        """, (thread_id,)) as cursor:
            spans = await cursor.fetchall()
            
            if not spans:
                print(f"❌ No spans found for thread_id: {thread_id}")
                return False
            
            print(f"✅ Found {len(spans)} spans")
            print("\nSpan Hierarchy:")
            print("-" * 60)
            
            # Build span tree
            span_map = {}
            root_spans = []
            
            for trace_id, span_id, parent_span_id, name, start_time, end_time, attributes in spans:
                span_info = {
                    "trace_id": trace_id,
                    "span_id": span_id,
                    "parent_span_id": parent_span_id,
                    "name": name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "attributes": json.loads(attributes) if attributes else {},
                }
                span_map[span_id] = span_info
                
                if not parent_span_id:
                    root_spans.append(span_info)
            
            # Print hierarchy
            def print_span(span, indent=0):
                prefix = "  " * indent + ("└─ " if indent > 0 else "")
                duration = ""
                if span["end_time"] and span["start_time"]:
                    start = datetime.fromisoformat(span["start_time"])
                    end = datetime.fromisoformat(span["end_time"])
                    duration = f" ({end - start})"
                
                print(f"{prefix}{span['name']}{duration}")
                
                # Print children
                for child_span in span_map.values():
                    if child_span["parent_span_id"] == span["span_id"]:
                        print_span(child_span, indent + 1)
            
            for root_span in root_spans:
                print_span(root_span)
            
            # Verify trace consistency
            trace_ids = {s[0] for s in spans}
            if len(trace_ids) > 1:
                print(f"\n⚠️  Warning: Multiple trace IDs found: {len(trace_ids)}")
            else:
                print(f"\n✅ All spans belong to single trace: {list(trace_ids)[0][:16]}...")
            
            return True


async def run_agent_and_verify():
    """Run the agent and verify telemetry collection."""
    print("="*60)
    print("TRACELENS VERIFICATION SCRIPT")
    print("="*60)
    
    # Check for API key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY or GEMINI_API_KEY not set")
        print("   Please set one of these environment variables")
        return False
    
    # Setup OpenTelemetry
    print("\n📊 Setting up OpenTelemetry...")
    setup_opentelemetry()
    print("✅ OpenTelemetry initialized")
    
    # Initialize checkpointer
    db_path = os.getenv("DATABASE_PATH", "./tracelens.db")
    checkpointer = SqliteCheckpointer(db_path)
    
    # Create agent
    print("\n🤖 Creating research agent...")
    try:
        agent = create_research_agent(checkpointer)
        print("✅ Agent created successfully")
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        return False
    
    # Run agent
    thread_id = f"verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    config = {"configurable": {"thread_id": thread_id}}
    
    initial_state: AgentState = {
        "query": "langgraph opentelemetry",
        "results": [],
        "summary": "",
        "step_count": 0,
        "needs_more_info": False,
        "error_count": 0,
        "last_error": "",
        "thread_id": thread_id,
    }
    
    print(f"\n🚀 Running agent with thread_id: {thread_id}")
    print(f"   Query: {initial_state['query']}")
    print("-" * 60)
    
    try:
        # Stream agent execution
        async for event in agent.astream(initial_state, config):
            # Print node updates
            for node_name, node_state in event.items():
                if node_name != "__end__":
                    step_count = node_state.get("step_count", 0)
                    results_count = len(node_state.get("results", []))
                    print(f"  → {node_name}: step={step_count}, results={results_count}")
        
        print("\n✅ Agent execution completed")
        
        # Flush spans to ensure they're exported
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        
        provider = trace.get_tracer_provider()
        if isinstance(provider, TracerProvider):
            # Force flush all span processors
            # Access span processors through the internal structure
            if hasattr(provider, '_span_processors'):
                processors = provider._span_processors
            elif hasattr(provider, 'span_processors'):
                processors = provider.span_processors
            else:
                # Try to get processors another way
                processors = []
            
            for processor in processors:
                if hasattr(processor, 'force_flush'):
                    processor.force_flush()
                    print(f"  ✓ Flushed {type(processor).__name__}")
            print("\n📊 Flushed span processors")
        
        # Give spans time to be exported (increase wait time for async thread)
        await asyncio.sleep(3.0)
        print("⏳ Waited for span export to complete")
        
        # Verify checkpoints
        checkpoint_ok = await verify_checkpoints(db_path, thread_id)
        
        # Verify spans
        span_ok = await verify_spans(db_path, thread_id)
        
        if checkpoint_ok and span_ok:
            print("\n" + "="*60)
            print("✅ ALL VERIFICATIONS PASSED")
            print("="*60)
            return True
        else:
            print("\n" + "="*60)
            print("❌ SOME VERIFICATIONS FAILED")
            print("="*60)
            return False
            
    except Exception as e:
        print(f"\n❌ Agent execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_agent_and_verify())
    sys.exit(0 if success else 1)
