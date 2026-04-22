"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api-client";
import type { DocDetail, DocListResponse, UploadResponse } from "../types";
import { getCredentials } from "../auth";

function tenantId() {
  return getCredentials()?.tenantId ?? "";
}

export function useDocs() {
  const tid = tenantId();
  return useQuery<DocListResponse>({
    queryKey: ["docs", tid],
    queryFn: () => api.get<DocListResponse>(`/${tid}/docs`),
    enabled: !!tid,
    refetchInterval: false,
  });
}

export function useDoc(docId: string) {
  const tid = tenantId();
  return useQuery<DocDetail>({
    queryKey: ["doc", tid, docId],
    queryFn: () => api.get<DocDetail>(`/${tid}/docs/${docId}`),
    enabled: !!tid && !!docId,
  });
}

export function useUploadDoc() {
  const qc = useQueryClient();
  const tid = tenantId();
  return useMutation<UploadResponse, Error, File>({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.post<UploadResponse>(`/${tid}/docs/upload`, form);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["docs", tid] }),
  });
}

export function useDeleteDoc() {
  const qc = useQueryClient();
  const tid = tenantId();
  return useMutation<unknown, Error, string>({
    mutationFn: (docId: string) => api.delete(`/${tid}/docs/${docId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["docs", tid] }),
  });
}
