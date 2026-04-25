"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useTraces } from "@/lib/hooks/use-logs";
import type { TraceRun } from "@/lib/types";

function MetaChip({ label, value }: { label: string; value: unknown }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <span className="inline-flex items-center gap-1 rounded bg-muted px-2 py-0.5 text-[11px]">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{String(value)}</span>
    </span>
  );
}

function TraceRow({ run }: { run: TraceRun }) {
  const [open, setOpen] = useState(false);
  const isError = !!run.error || run.status === "error";
  const query = (run.inputs as Record<string, string>)?.query ?? "—";
  const answer = (run.outputs as Record<string, string>)?.generation ?? "";
  const meta = run.metadata as Record<string, unknown>;

  return (
    <div className="border-b last:border-0">
      <button
        className="w-full flex items-start gap-3 px-4 py-3 text-xs text-left hover:bg-muted/40 transition-colors"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <ChevronDown className="h-3.5 w-3.5 mt-0.5 shrink-0" /> : <ChevronRight className="h-3.5 w-3.5 mt-0.5 shrink-0" />}
        <span className="text-muted-foreground shrink-0 w-36 font-mono">
          {run.start_time ? new Date(run.start_time).toLocaleString() : "—"}
        </span>
        <Badge variant={isError ? "destructive" : "success"} className="shrink-0 text-[10px] px-1.5 uppercase">
          {isError ? "error" : "ok"}
        </Badge>
        <span className="flex-1 truncate text-foreground">{query}</span>
        <span className="shrink-0 text-muted-foreground">
          {run.latency_ms != null ? `${run.latency_ms} ms` : "—"}
        </span>
      </button>

      {open && (
        <div className="px-10 pb-4 space-y-3 text-xs">
          <div className="flex flex-wrap gap-1.5">
            <MetaChip label="route" value={meta.query_type} />
            <MetaChip label="rewrites" value={meta.rewrite_count} />
            <MetaChip label="hallucination" value={meta.hallucination_score != null ? Number(meta.hallucination_score).toFixed(2) : null} />
            <MetaChip label="answer_score" value={meta.answer_score != null ? Number(meta.answer_score).toFixed(2) : null} />
            <MetaChip label="fallback" value={meta.fallback ? "yes" : null} />
          </div>

          {answer && (
            <div>
              <p className="text-muted-foreground mb-1 font-medium">Answer</p>
              <p className="whitespace-pre-wrap leading-relaxed text-foreground">{answer}</p>
            </div>
          )}

          {run.error && (
            <div>
              <p className="text-destructive font-medium mb-1">Error</p>
              <pre className="rounded bg-destructive/10 p-2 text-destructive overflow-x-auto">{run.error}</pre>
            </div>
          )}

          <p className="text-muted-foreground font-mono">run_id: {run.run_id}</p>
        </div>
      )}
    </div>
  );
}

export function TracesTab() {
  const [limit, setLimit] = useState(20);
  const { data, isLoading, refetch, isFetching } = useTraces(limit);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Show last</span>
        {[10, 20, 50].map((n) => (
          <button
            key={n}
            onClick={() => setLimit(n)}
            className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
              limit === n
                ? "bg-primary text-primary-foreground border-primary"
                : "text-muted-foreground border-border hover:bg-accent"
            }`}
          >
            {n}
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

      {data && !data.langsmith_enabled && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          LangSmith is not configured — set <code>LANGSMITH_API_KEY</code> in your <code>.env</code> to enable trace collection.
        </div>
      )}

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
        ) : !data?.runs.length ? (
          <p className="text-center py-12 text-sm text-muted-foreground">No traces found for this tenant.</p>
        ) : (
          <div className="divide-y max-h-[520px] overflow-y-auto">
            {data.runs.map((run) => (
              <TraceRow key={run.run_id} run={run} />
            ))}
          </div>
        )}
      </div>

      {data?.runs.length ? (
        <p className="text-xs text-muted-foreground text-right">
          {data.runs.length} trace{data.runs.length !== 1 ? "s" : ""} · auto-refreshes every 30 s
        </p>
      ) : null}
    </div>
  );
}
