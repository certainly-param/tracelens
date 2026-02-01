"""SQLite exporter for OpenTelemetry spans."""
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Span

from ..storage.db_manager import get_db_manager


def _verbose() -> bool:
    """True when verbose export logging is enabled (env TRACELENS_OTEL_VERBOSE=1)."""
    return os.getenv("TRACELENS_OTEL_VERBOSE", "").lower() in ("1", "true", "yes")


class SqliteSpanExporter(SpanExporter):
    """Exports OpenTelemetry spans to SQLite database."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the SQLite span exporter.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_manager = get_db_manager(db_path)
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure database is initialized."""
        if not self._initialized:
            await self.db_manager.initialize()
            self._initialized = True
    
    def export(self, spans: list[Span]) -> SpanExportResult:
        """Export spans to SQLite (synchronous wrapper for async)."""
        import asyncio
        import threading
        
        if not spans:
            return SpanExportResult.SUCCESS
        
        if _verbose():
            print(f"[SpanExporter] Exporting {len(spans)} spans")
            for span in spans:
                attrs = dict(span.attributes) if span.attributes else {}
                thread_id = attrs.get("thread_id") or attrs.get("langgraph.thread_id")
                print(f"  - {span.name}: thread_id={thread_id}")
        
        # Use a thread-safe approach for async export
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._export_async(spans))
                loop.close()
                if _verbose():
                    print(f"[SpanExporter] Successfully exported {len(spans)} spans")
            except Exception as e:
                print(f"[SpanExporter] Error exporting spans: {e}")
                import traceback
                traceback.print_exc()
        
        # Run in background thread to avoid blocking
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
        
        return SpanExportResult.SUCCESS
    
    async def _export_async(self, spans: list[Span]):
        """Async export implementation."""
        await self._ensure_initialized()
        
        if not spans:
            return
        
        async with self.db_manager.get_connection() as db:
            for span in spans:
                # Extract span data
                span_context = span.get_span_context()
                trace_id = format(span_context.trace_id, '032x')
                span_id = format(span_context.span_id, '032x')
                
                parent_span_id = None
                if span.parent:
                    parent_span_id = format(span.parent.span_id, '032x')
                
                # Extract attributes
                attributes = dict(span.attributes) if span.attributes else {}
                
                # Extract thread_id from attributes if present
                thread_id = attributes.get("thread_id") or attributes.get("langgraph.thread_id")
                
                if _verbose() and not thread_id:
                    print(f"[SpanExporter] WARNING: Span '{span.name}' has no thread_id attribute")
                    print(f"  Available attributes: {list(attributes.keys())}")
                
                # Convert timestamps
                start_time = datetime.fromtimestamp(span.start_time / 1e9) if span.start_time else None
                end_time = datetime.fromtimestamp(span.end_time / 1e9) if span.end_time else None
                
                # Serialize attributes to JSON
                attributes_json = json.dumps(attributes)
                
                # Insert or update span
                await db.execute("""
                    INSERT OR REPLACE INTO traces 
                    (trace_id, span_id, parent_span_id, name, attributes, 
                     start_time, end_time, thread_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trace_id,
                    span_id,
                    parent_span_id,
                    span.name,
                    attributes_json,
                    start_time.isoformat() if start_time else None,
                    end_time.isoformat() if end_time else None,
                    thread_id,
                ))
            
            await db.commit()
    
    def shutdown(self):
        """Shutdown the exporter."""
        pass
