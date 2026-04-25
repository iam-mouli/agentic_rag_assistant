export interface Citation {
  doc_id?: string;
  filename?: string;
  page?: number;
  chunk_preview?: string;
}

export interface QueryResponse {
  answer: string;
  confidence: number;
  confidence_level: "high" | "medium" | "low";
  fallback: boolean;
  citations: Citation[];
  cache: boolean;
}

export interface DocDetail {
  doc_id: string;
  filename: string;
  status: "processing" | "active" | "failed" | "quarantined" | "removed" | "superseded";
  chunk_count: number | null;
  pages: number | null;
  uploaded_at: string;
  file_hash?: string;
  version?: string;
}

export interface DocListResponse {
  tenant_id: string;
  total_docs: number;
  total_chunks: number;
  documents: DocDetail[];
}

export interface UploadResponse {
  doc_id: string;
  filename: string;
  status: string;
}

export interface FeedbackRequest {
  run_id: string;
  score: 1 | -1;
  comment?: string;
}

export interface Credentials {
  tenantId: string;
  apiKey: string;
}

// ---- Query History ----

export interface QueryHistoryEntry {
  query_id: string;
  tenant_id: string;
  query: string;
  answer: string;
  citations: Citation[];
  confidence: number;
  confidence_level: "high" | "medium" | "low";
  fallback: boolean;
  run_id: string | null;
  cache_hit: boolean;
  created_at: string;
}

export interface QueryHistoryResponse {
  entries: QueryHistoryEntry[];
  count: number;
}

// ---- Logs ----

export interface AppLogEntry {
  timestamp?: string;
  level?: string;
  event?: string;
  tenant_id?: string;
  request_id?: string;
  [key: string]: unknown;
}

export interface AppLogsResponse {
  entries: AppLogEntry[];
  count: number;
}

export interface TraceRun {
  run_id: string;
  start_time: string | null;
  end_time: string | null;
  latency_ms: number | null;
  status: string | null;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  error: string | null;
  metadata: Record<string, unknown>;
}

export interface TracesResponse {
  runs: TraceRun[];
  langsmith_enabled: boolean;
  error?: string;
}

export interface IngestionJob {
  doc_id: string;
  filename: string;
  status: string;
  uploaded_at: string | null;
  chunk_count: number | null;
  pages: number | null;
  error_message: string | null;
}

export interface IngestionLogsResponse {
  jobs: IngestionJob[];
  count: number;
  error?: string;
}
