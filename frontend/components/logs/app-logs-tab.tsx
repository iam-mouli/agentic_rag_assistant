"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { useAppLogs } from "@/lib/hooks/use-logs";
import type { AppLogEntry } from "@/lib/types";

const LEVELS = ["", "info", "warning", "error", "debug"] as const;

const LEVEL_VARIANT: Record<string, "success" | "warning" | "destructive" | "secondary"> = {
  info: "success",
  warning: "warning",
  error: "destructive",
  debug: "secondary",
};

function LogRow({ entry }: { entry: AppLogEntry }) {
  const [expanded, setExpanded] = useState(false);
  const { timestamp, level, event, tenant_id, request_id, ...rest } = entry;

  return (
    <div
      className="border-b last:border-0 px-4 py-2 text-xs cursor-pointer hover:bg-muted/40 transition-colors"
      onClick={() => setExpanded((v) => !v)}
    >
      <div className="flex items-start gap-3">
        <span className="text-muted-foreground shrink-0 w-44 font-mono">
          {timestamp ? new Date(timestamp).toLocaleString() : "—"}
        </span>
        <Badge
          variant={LEVEL_VARIANT[level?.toLowerCase() ?? ""] ?? "secondary"}
          className="shrink-0 uppercase text-[10px] px-1.5"
        >
          {level ?? "?"}
        </Badge>
        <span className="font-medium truncate flex-1">{event ?? "—"}</span>
      </div>

      {expanded && Object.keys(rest).length > 0 && (
        <pre className="mt-2 rounded bg-muted p-2 text-[11px] overflow-x-auto text-muted-foreground">
          {JSON.stringify(rest, null, 2)}
        </pre>
      )}
    </div>
  );
}

export function AppLogsTab() {
  const [level, setLevel] = useState("");
  const { data, isLoading, refetch, isFetching } = useAppLogs(level || undefined);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-muted-foreground">Level:</span>
        {LEVELS.map((l) => (
          <button
            key={l}
            onClick={() => setLevel(l)}
            className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
              level === l
                ? "bg-primary text-primary-foreground border-primary"
                : "text-muted-foreground border-border hover:bg-accent"
            }`}
          >
            {l === "" ? "All" : l}
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

      <div className="rounded-lg border bg-background overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner className="h-5 w-5" />
          </div>
        ) : !data?.entries.length ? (
          <p className="text-center py-12 text-sm text-muted-foreground">No log entries found.</p>
        ) : (
          <div className="divide-y max-h-[520px] overflow-y-auto">
            {data.entries.map((entry, i) => (
              <LogRow key={i} entry={entry} />
            ))}
          </div>
        )}
      </div>

      {data && (
        <p className="text-xs text-muted-foreground text-right">
          {data.count} entr{data.count === 1 ? "y" : "ies"} · auto-refreshes every 15 s
        </p>
      )}
    </div>
  );
}
