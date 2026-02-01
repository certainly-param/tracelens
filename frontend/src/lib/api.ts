/** API client for TraceLens backend. */
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_KEY = process.env.NEXT_PUBLIC_TRACELENS_API_KEY || '';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    ...(API_KEY && { 'X-API-Key': API_KEY }),
  },
});

// Types
export interface Node {
  id: string;
  label: string;
  type: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
  timestamp?: string;
  duration?: number;
  metadata?: Record<string, any>;
}

export interface Edge {
  source: string;
  target: string;
  condition?: string;
  label?: string;
}

export interface GraphResponse {
  nodes: Node[];
  edges: Edge[];
  metadata: {
    thread_id: string;
    start_time?: string;
    end_time?: string;
    total_checkpoints: number;
    total_spans: number;
  };
}

export interface Run {
  thread_id: string;
  created_at: string;
  last_updated: string;
  checkpoint_count: number;
  span_count: number;
  status: string;
}

export interface Checkpoint {
  checkpoint_id: string;
  parent_checkpoint_id?: string;
  created_at: string;
  state_summary: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface Span {
  trace_id: string;
  span_id: string;
  parent_span_id?: string;
  name: string;
  start_time: string;
  end_time?: string;
  duration?: number;
  attributes: Record<string, any>;
  status: string;
}

// API functions
export const api = {
  // Health check
  async healthCheck(): Promise<{ status: string; service: string }> {
    const response = await apiClient.get('/api/health');
    return response.data;
  },

  // List all runs
  async listRuns(): Promise<{ runs: Run[]; total: number }> {
    const response = await apiClient.get('/api/runs');
    return response.data;
  },

  // Get graph for a run
  async getGraph(threadId: string): Promise<GraphResponse> {
    const response = await apiClient.get(`/api/runs/${threadId}/graph`);
    return response.data;
  },

  // List checkpoints for a run
  async listCheckpoints(threadId: string): Promise<{
    thread_id: string;
    checkpoints: Checkpoint[];
    total: number;
  }> {
    const response = await apiClient.get(`/api/runs/${threadId}/checkpoints`);
    return response.data;
  },

  // Get specific checkpoint
  async getCheckpoint(threadId: string, checkpointId: string): Promise<any> {
    const response = await apiClient.get(
      `/api/runs/${threadId}/checkpoints/${checkpointId}`
    );
    return response.data;
  },

  // List spans for a run
  async listSpans(threadId: string): Promise<{
    thread_id: string;
    spans: Span[];
    total: number;
  }> {
    const response = await apiClient.get(`/api/runs/${threadId}/spans`);
    return response.data;
  },

  // Get checkpoint diff
  async getCheckpointDiff(
    threadId: string,
    checkpointId1: string,
    checkpointId2: string
  ): Promise<{
    checkpoint_id_1: string;
    checkpoint_id_2: string;
    added: Record<string, any>;
    removed: Record<string, any>;
    modified: Record<string, any>;
  }> {
    const response = await apiClient.get(
      `/api/runs/${threadId}/checkpoints/${checkpointId1}/diff`,
      { params: { compare_to: checkpointId2 } }
    );
    return response.data;
  },

  // Get timeline
  async getTimeline(threadId: string): Promise<{
    thread_id: string;
    events: Array<{
      event_id: string;
      event_type: string;
      timestamp: string;
      checkpoint_id?: string;
      span_id?: string;
      node_id?: string;
      description: string;
      metadata: Record<string, any>;
    }>;
    total: number;
  }> {
    const response = await apiClient.get(`/api/runs/${threadId}/timeline`);
    return response.data;
  },

  // Phase 4: Active Intervention

  // Update checkpoint state
  async updateCheckpointState(
    threadId: string,
    checkpointId: string,
    state: Record<string, any>,
    description?: string
  ): Promise<{
    success: boolean;
    new_checkpoint_id: string;
    thread_id: string;
    message: string;
  }> {
    const response = await apiClient.put(
      `/api/runs/${threadId}/checkpoints/${checkpointId}/state`,
      { state, description }
    );
    return response.data;
  },

  // Validate checkpoint state
  async validateCheckpointState(
    threadId: string,
    checkpointId: string,
    state: Record<string, any>
  ): Promise<{
    valid: boolean;
    errors: Array<{ field: string; message: string; severity: string }>;
    warnings: Array<{ field: string; message: string; severity: string }>;
  }> {
    const response = await apiClient.post(
      `/api/runs/${threadId}/checkpoints/${checkpointId}/validate`,
      { state }
    );
    return response.data;
  },

  // Resume execution from checkpoint
  async resumeExecution(
    threadId: string,
    checkpointId: string,
    modifiedState?: Record<string, any>,
    description?: string
  ): Promise<{
    success: boolean;
    new_thread_id: string;
    original_thread_id: string;
    from_checkpoint_id: string;
    message: string;
  }> {
    const response = await apiClient.post(
      `/api/runs/${threadId}/checkpoints/${checkpointId}/resume`,
      {
        from_checkpoint_id: checkpointId,
        modified_state: modifiedState,
        description,
      }
    );
    return response.data;
  },

  // Create execution branch
  async createBranch(
    threadId: string,
    checkpointId: string,
    branchName?: string,
    modifiedState?: Record<string, any>,
    description?: string
  ): Promise<{
    success: boolean;
    branch_thread_id: string;
    original_thread_id: string;
    from_checkpoint_id: string;
    branch_name?: string;
    message: string;
  }> {
    const response = await apiClient.post(
      `/api/runs/${threadId}/checkpoints/${checkpointId}/branch`,
      {
        from_checkpoint_id: checkpointId,
        branch_name: branchName,
        modified_state: modifiedState,
        description,
      }
    );
    return response.data;
  },
};
