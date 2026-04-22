"use client";

import { useMutation } from "@tanstack/react-query";
import { api } from "../api-client";
import type { FeedbackRequest, QueryResponse } from "../types";
import { getCredentials } from "../auth";

function tenantId() {
  return getCredentials()?.tenantId ?? "";
}

export function useQueryAgent() {
  const tid = tenantId();
  return useMutation<QueryResponse & { runId?: string }, Error, string>({
    mutationFn: async (query: string) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/${tid}/query`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Tenant-ID": tid,
            "X-API-Key": getCredentials()?.apiKey ?? "",
          },
          body: JSON.stringify({ query }),
        }
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? res.statusText);
      }
      const runId = res.headers.get("X-Run-ID") ?? undefined;
      const data = (await res.json()) as QueryResponse;
      return { ...data, runId };
    },
  });
}

export function useFeedback() {
  const tid = tenantId();
  return useMutation<unknown, Error, FeedbackRequest>({
    mutationFn: (body: FeedbackRequest) =>
      api.post(`/${tid}/feedback`, body),
  });
}
