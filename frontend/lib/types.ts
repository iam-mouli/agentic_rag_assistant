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
