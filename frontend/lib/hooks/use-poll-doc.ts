"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "../api-client";
import type { DocDetail } from "../types";
import { getCredentials } from "../auth";

const POLL_INTERVAL_MS = 3000;

export function usePollDoc(docId: string | null) {
  const tid = getCredentials()?.tenantId ?? "";
  return useQuery<DocDetail>({
    queryKey: ["doc-poll", tid, docId],
    queryFn: () => api.get<DocDetail>(`/${tid}/docs/${docId}`),
    enabled: !!tid && !!docId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "processing" ? POLL_INTERVAL_MS : false;
    },
  });
}
