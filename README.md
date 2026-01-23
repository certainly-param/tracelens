<div align="center">

# TraceLens

**A Visual Debugger and Replay Engine for LangGraph Agentic Workflows**

[![GitHub stars](https://img.shields.io/github/stars/certainly-param/tracelens?style=social)](https://github.com/certainly-param/tracelens)
[![GitHub watchers](https://img.shields.io/github/watchers/certainly-param/tracelens?style=social)](https://github.com/certainly-param/tracelens)
[![GitHub forks](https://img.shields.io/github/forks/certainly-param/tracelens?style=social)](https://github.com/certainly-param/tracelens)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Under Development](https://img.shields.io/badge/Status-Under%20Development-orange.svg)](https://github.com/certainly-param/tracelens)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 20+](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-00a7b7.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14+-000000.svg)](https://nextjs.org/)

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

## Project Overview

TraceLens addresses the **"Silent Failure" crisis** in agentic AI systems. Unlike traditional software where errors manifest as explicit exceptions, AI agents can fail silently through:

- **Tool Thrashing**: Infinite loops of repetitive tool invocations without progress
- **Context Drift**: Agent's internal world model diverging from actual system state
- **Non-Deterministic Failures**: Bugs that only appear in production due to LLM token sampling

TraceLens provides a **"Diagnostic Command Center"** that offers:
- **Real-Time Visualization**: Interactive graph showing agent execution flow
- **Time-Travel Navigation**: Rewind to any checkpoint and inspect state
- **Active Intervention**: Edit state and prompts, then resume execution from that point

## Features

- **Real-time Agent Monitoring**: Watch your LangGraph agents execute in real-time
- **Interactive Graph Visualization**: Beautiful React Flow graphs showing execution paths
- **Time-Travel Debugging**: Navigate through checkpoints and inspect state at any point
- **OpenTelemetry Integration**: Standardized telemetry collection and export
- **SQLite Persistence**: Local storage with WAL mode for efficient checkpointing
- **Modern UI**: Clean, minimalistic interface built with Next.js and Tailwind CSS
- **Easy Integration**: Sidecar pattern - no modifications to your agent code needed

## Architecture

TraceLens follows a "Sidecar" pattern where instrumentation wraps the agent without modifying core logic:

```
┌─────────────────┐
│  Agent Runtime  │  (LangGraph agent with tools)
└────────┬────────┘
         │
┌────────▼────────────────────────┐
│  Interceptor Layer             │
│  - OpenTelemetry Spans         │
│  - SQLite Checkpointer         │
└────────┬───────────────────────┘
         │
┌────────▼────────────────────────┐
│  Telemetry Server (FastAPI)    │
│  - REST API for trace data     │
│  - Graph transformation        │
└────────┬───────────────────────┘
         │
┌────────▼────────────────────────┐
│  Data Store (SQLite WAL)       │
│  - Checkpoints (state history) │
│  - Traces (OTel spans)          │
└────────────────────────────────┘
         │
┌────────▼────────────────────────┐
│  Diagnostic UI (Next.js)       │
│  - React Flow visualization    │
│  - Real-time updates           │
└────────────────────────────────┘
```

## Prerequisites

- **Python 3.11+** (for async/await support and modern typing)
- **Node.js 20+** and npm/yarn
- **Google Gemini API key** (get from [Google AI Studio](https://makersuite.google.com/app/apikey)) for sample agent
- **Docker & Docker Compose** (optional, for containerized deployment)

## Installation

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup

```bash
cd frontend
npm install
# or
yarn install
```

## Configuration

Create a `.env` file in the project root:

```env
# Required: Gemini API Key
GOOGLE_API_KEY=your_api_key_here
# or
GEMINI_API_KEY=your_api_key_here

# Optional: Database path (default: ./tracelens.db)
DATABASE_PATH=./tracelens.db

# Optional: OpenTelemetry exporter endpoint
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

# Optional: FastAPI server settings
FASTAPI_HOST=localhost
FASTAPI_PORT=8000

# Optional: LLM model selection
LLM_MODEL=gemini-1.5-pro  # or gemini-1.5-flash for faster responses
```

## Quick Start

1. **Start the backend server:**
   ```bash
   cd backend
   uvicorn src.api.main:app --reload
   ```

2. **Start the frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Run the sample agent:**
   ```bash
   python backend/scripts/verify_telemetry.py
   ```

4. **Access the UI:**
   Open [http://localhost:3000](http://localhost:3000) in your browser

## Usage Guide

### Instrumenting Your Own LangGraph Agents

To use TraceLens with your own agents:

1. Import the SQLite checkpointer:
   ```python
   from src.storage.sqlite_checkpointer import SqliteCheckpointer
   ```

2. Initialize with your graph:
   ```python
   checkpointer = SqliteCheckpointer(db_path="./tracelens.db")
   graph = graph.compile(checkpointer=checkpointer)
   ```

3. The instrumentation will automatically capture:
   - Node transitions
   - Tool invocations
   - LLM calls
   - State changes

## API Documentation

Once the backend is running, access the interactive API documentation at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Key Endpoints

- `GET /api/runs` - List all execution runs
- `GET /api/runs/{thread_id}/graph` - Get graph structure with nodes and edges
- `GET /api/runs/{thread_id}/checkpoints` - Get checkpoint history
- `GET /api/runs/{thread_id}/checkpoints/{checkpoint_id}` - Get specific checkpoint state
- `GET /api/runs/{thread_id}/spans` - Get OpenTelemetry spans for a run

## Development

### Project Structure

```
tracelens/
├── backend/
│   ├── src/
│   │   ├── agent/              # Sample LangGraph agent
│   │   ├── instrumentation/   # OTel hooks & checkpointer
│   │   ├── storage/            # SQLite persistence
│   │   └── api/                # FastAPI endpoints
│   ├── scripts/                # Utility scripts
│   ├── requirements.txt
│   └── main.py
├── frontend/                   # Next.js app
│   ├── components/             # React components
│   ├── hooks/                  # Custom React hooks
│   ├── pages/                  # Next.js pages
│   └── package.json
├── docker-compose.yml
├── README.md
└── .gitignore
```

### Key Dependencies

- **Agent Orchestration**: LangGraph for stateful, cyclic workflows
- **Observability**: OpenTelemetry (OTel) for standardized telemetry
- **Backend**: FastAPI for async, high-performance API server
- **Database**: SQLite with WAL mode for local persistence
- **LLM Gateway**: LiteLLM for multi-provider model access
- **Frontend**: Next.js + React Flow for graph visualization
- **Styling**: Tailwind CSS for modern UI

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [OpenTelemetry Standards](https://opentelemetry.io/)
- [React Flow Documentation](https://reactflow.dev/)
- [Google Gemini API](https://ai.google.dev/)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## What's Next

Upcoming features and improvements in the pipeline:

- **State editing and replay**: Modify checkpoint state and resume execution from any point
- **Prompt editing**: Edit agent prompts dynamically and test different strategies
- **Advanced filtering**: Filter runs by date range, status, duration, and custom attributes
- **Export capabilities**: Export traces and checkpoints to JSON, CSV, and OTLP formats
- **Search functionality**: Full-text search across spans, attributes, and checkpoint data
- **Performance metrics**: Detailed timing analysis and bottleneck identification
- **Multi-agent support**: Visualize and debug multiple agents running concurrently
- **Real-time streaming**: Live updates as agents execute without manual refresh
- **Custom visualizations**: Additional graph layouts and view modes
- **Integration plugins**: Easy integration with popular agent frameworks and tools

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [LangGraph](https://langchain-ai.github.io/langgraph/) for the agent orchestration framework
- [OpenTelemetry](https://opentelemetry.io/) for standardized observability
- [React Flow](https://reactflow.dev/) for graph visualization
- [FastAPI](https://fastapi.tiangolo.com/) for the high-performance API framework

---

<div align="center">

**Made with ❤️ for the AI agent development community**

⭐ Star this repo if you find it helpful!

</div>
