/** Custom hook for fetching and polling agent graph data. */
import { useEffect, useState } from 'react';
import useSWR from 'swr';
import { api, GraphResponse } from '../lib/api';

export function useAgentGraph(threadId: string | null) {
  const { data, error, isLoading } = useSWR<GraphResponse>(
    threadId ? [`graph`, threadId] : null,
    ([, id]) => api.getGraph(id),
    {
      refreshInterval: 2000, // Poll every 2 seconds
      revalidateOnFocus: true,
      revalidateOnReconnect: true,
    }
  );

  return {
    graph: data || null,
    loading: isLoading,
    error: error?.message || null,
  };
}
