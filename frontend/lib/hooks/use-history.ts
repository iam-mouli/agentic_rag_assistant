"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api-client";
import { getCredentials } from "../auth";
import type { QueryHistoryResponse } from "../types";

function tenantId() {
  return getCredentials()?.tenantId ?? "";
}

export function useHistory(limit = 50) {
  const tid = tenantId();
  return useQuery<QueryHistoryResponse>({
    queryKey: ["history", tid, limit],
    queryFn: () => api.get(`/${tid}/history?limit=${limit}`),
    enabled: !!tid,
    staleTime: 0,
  });
}

export function useDeleteHistoryEntry() {
  const tid = tenantId();
  const client = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (queryId: string) =>
      api.delete(`/${tid}/history/${queryId}`),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["history", tid] });
    },
  });
}

export function useClearHistory() {
  const tid = tenantId();
  const client = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: () => api.delete(`/${tid}/history`),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["history", tid] });
    },
  });
}
