import { Badge } from "@/components/ui/badge";
import { CitationCard } from "./citation-card";
import { FeedbackButtons } from "./feedback-buttons";
import type { QueryResponse } from "@/lib/types";

export interface Message {
  role: "user" | "assistant";
  text: string;
  response?: QueryResponse & { runId?: string };
}

const CONFIDENCE_VARIANT: Record<string, "success" | "warning" | "destructive"> = {
  high: "success",
  medium: "warning",
  low: "destructive",
};

export function MessageBubble({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-xl rounded-2xl rounded-br-sm bg-primary px-4 py-2 text-primary-foreground text-sm">
          {message.text}
        </div>
      </div>
    );
  }

  const res = message.response;
  return (
    <div className="flex justify-start">
      <div className="max-w-2xl space-y-3 w-full">
        <div className="rounded-2xl rounded-bl-sm bg-muted px-4 py-3 text-sm">
          {res?.fallback && (
            <p className="mb-2 text-xs text-muted-foreground italic">
              The documents do not contain a direct answer — responding from general knowledge.
            </p>
          )}
          <p className="whitespace-pre-wrap">{message.text}</p>
          {res && (
            <div className="mt-2 flex items-center gap-2">
              <Badge variant={CONFIDENCE_VARIANT[res.confidence_level] ?? "secondary"}>
                {res.confidence_level} confidence ({Math.round(res.confidence * 100)}%)
              </Badge>
              {res.cache && <Badge variant="secondary">cached</Badge>}
            </div>
          )}
        </div>

        {res && res.citations.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-1 font-medium">Sources</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {res.citations.map((c, i) => (
                <CitationCard key={i} citation={c} />
              ))}
            </div>
          </div>
        )}

        {res && <FeedbackButtons runId={res.runId} />}
      </div>
    </div>
  );
}
