"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "../api-client";
import { getCredentials } from "../auth";
import type { AppLogsResponse, TracesResponse, IngestionLogsResponse } from "../types";

function tid() {
  return getCredentials()?.tenantId ?? "";
}

export function useAppLogs(level?: string, limit = 100) {
  const tenantId = tid();
  const params = new URLSearchParams({ limit: String(limit) });
  if (level) params.set("level", level);

  return useQuery<AppLogsResponse>({
    queryKey: ["logs", "app", tenantId, level, limit],
    queryFn: () => api.get(`/${tenantId}/logs/app?${params}`),
    refetchInterval: 15_000,
    staleTime: 10_000,
  });
}

export function useTraces(limit = 20) {
  const tenantId = tid();

  return useQuery<TracesResponse>({
    queryKey: ["logs", "traces", tenantId, limit],
    queryFn: () => api.get(`/${tenantId}/logs/traces?limit=${limit}`),
    refetchInterval: 30_000,
    staleTime: 20_000,
  });
}

export function useIngestionLogs(status?: string, limit = 50) {
  const tenantId = tid();
  const params = new URLSearchParams({ limit: String(limit) });
  if (status) params.set("status", status);

  return useQuery<IngestionLogsResponse>({
    queryKey: ["logs", "ingestion", tenantId, status, limit],
    queryFn: () => api.get(`/${tenantId}/logs/ingestion?${params}`),
    refetchInterval: 10_000,
    staleTime: 8_000,
  });
}
