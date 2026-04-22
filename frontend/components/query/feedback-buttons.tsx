"use client";

import { useState } from "react";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useFeedback } from "@/lib/hooks/use-query-agent";

export function FeedbackButtons({ runId }: { runId: string | undefined }) {
  const [voted, setVoted] = useState<1 | -1 | null>(null);
  const feedback = useFeedback();

  if (!runId) return null;

  const vote = async (score: 1 | -1) => {
    if (voted !== null) return;
    setVoted(score);
    try {
      await feedback.mutateAsync({ run_id: runId, score });
      toast.success("Feedback recorded — thank you");
    } catch {
      toast.error("Could not record feedback");
      setVoted(null);
    }
  };

  return (
    <div className="flex items-center gap-1 mt-2">
      <span className="text-xs text-muted-foreground mr-1">Was this helpful?</span>
      <Button
        size="icon"
        variant={voted === 1 ? "default" : "ghost"}
        className="h-7 w-7"
        onClick={() => vote(1)}
        disabled={voted !== null}
        title="Helpful"
      >
        <ThumbsUp className="h-3.5 w-3.5" />
      </Button>
      <Button
        size="icon"
        variant={voted === -1 ? "destructive" : "ghost"}
        className="h-7 w-7"
        onClick={() => vote(-1)}
        disabled={voted !== null}
        title="Not helpful"
      >
        <ThumbsDown className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}
