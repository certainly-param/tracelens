/** API client for TraceLens backend. */
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
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
};
