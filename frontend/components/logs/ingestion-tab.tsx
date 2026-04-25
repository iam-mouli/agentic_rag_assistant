"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useIngestionLogs } from "@/lib/hooks/use-logs";
import type { IngestionJob } from "@/lib/types";

const STATUSES = ["", "processing", "active", "failed", "quarantined"] as const;

const STATUS_VARIANT: Record<string, "success" | "warning" | "destructive" | "secondary"> = {
  active: "success",
  processing: "warning",
  failed: "destructive",
  quarantined: "destructive",
};

function JobRow({ job }: { job: IngestionJob }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`border-b last:border-0 px-4 py-3 text-xs ${job.error_message ? "cursor-pointer hover:bg-muted/40" : ""}`}
      onClick={() => job.error_message && setExpanded((v) => !v)}
    >
      <div className="flex items-center gap-3">
        <span className="text-muted-foreground shrink-0 w-36 font-mono">
          {job.uploaded_at ? new Date(job.uploaded_at).toLocaleString() : "—"}
        </span>
        <Badge
          variant={STATUS_VARIANT[job.status] ?? "secondary"}
          className="shrink-0 text-[10px] px-1.5 uppercase"
        >
          {job.status}
        </Badge>
        <span className="flex-1 truncate font-medium">{job.filename}</span>
        <span className="shrink-0 text-muted-foreground">
          {job.chunk_count != null ? `${job.chunk_count} chunks` : ""}
          {job.pages != null ? ` · ${job.pages} p` : ""}
        </span>
      </div>

      {expanded && job.error_message && (
        <pre className="mt-2 ml-[calc(9rem+1.5rem)] rounded bg-destructive/10 p-2 text-[11px] text-destructive overflow-x-auto">
          {job.error_message}
        </pre>
      )}
    </div>
  );
}

export function IngestionTab() {
  const [status, setStatus] = useState("");
  const { data, isLoading, refetch, isFetching } = useIngestionLogs(status || undefined);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-muted-foreground">Status:</span>
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
              status === s
                ? "bg-primary text-primary-foreground border-primary"
                : "text-muted-foreground border-border hover:bg-accent"
            }`}
          >
            {s === "" ? "All" : s}
          </button>
        ))}
        <Button
          size="sm"
          variant="outline"
          className="ml-auto h-7"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          <RefreshCw className={`h-3 w-3 mr-1 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {data?.error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {data.error}
        </div>
      )}

      <div className="rounded-lg border bg-background overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner className="h-5 w-5" />
          </div>
        ) : !data?.jobs.length ? (
          <p className="text-center py-12 text-sm text-muted-foreground">No ingestion jobs found.</p>
        ) : (
          <div className="divide-y max-h-[520px] overflow-y-auto">
            {data.jobs.map((job) => (
              <JobRow key={job.doc_id} job={job} />
            ))}
          </div>
        )}
      </div>

      {data && (
        <p className="text-xs text-muted-foreground text-right">
          {data.count} job{data.count !== 1 ? "s" : ""} · click a failed row to see the error · auto-refreshes every 10 s
        </p>
      )}
    </div>
  );
}
