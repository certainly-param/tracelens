"""Main entry point for TraceLens backend."""
import uvicorn
import os

if __name__ == "__main__":
    host = os.getenv("FASTAPI_HOST", "localhost")
    port = int(os.getenv("FASTAPI_PORT", "8000"))
    
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=True,
    )
