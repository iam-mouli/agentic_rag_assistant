"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { MessageBubble, type Message } from "./message-bubble";
import { useQueryAgent } from "@/lib/hooks/use-query-agent";
import { useClearHistory, useHistory } from "@/lib/hooks/use-history";
import { getCredentials } from "@/lib/auth";

function historyKey(tid: string) {
  return ["history", tid, 50];
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const query = useQueryAgent();
  const client = useQueryClient();
  const tid = getCredentials()?.tenantId ?? "";

  const { data: historyData } = useHistory(50);
  const clearHistory = useClearHistory();

  // Pre-populate messages from persisted history (oldest → newest)
  useEffect(() => {
    if (hydrated || !historyData) return;
    const entries = [...historyData.entries].reverse();
    const restored: Message[] = entries.flatMap((e) => [
      { role: "user" as const, text: e.query },
      {
        role: "assistant" as const,
        text: e.answer,
        response: {
          answer: e.answer,
          confidence: e.confidence,
          confidence_level: e.confidence_level,
          fallback: e.fallback,
          citations: e.citations,
          cache: e.cache_hit,
          runId: e.run_id ?? undefined,
        },
      },
    ]);
    setMessages(restored);
    setHydrated(true);
  }, [historyData, hydrated]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || query.isPending) return;
    setInput("");

    setMessages((prev) => [...prev, { role: "user", text }]);

    try {
      const res = await query.mutateAsync(text);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: res.answer, response: res },
      ]);
      // Refresh history so the new entry is reflected
      client.invalidateQueries({ queryKey: historyKey(tid) });
    } catch (err) {
      const msg = (err as Error).message;
      if (msg !== "RateLimited") toast.error(msg);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Sorry, something went wrong. Please try again." },
      ]);
    }
  };

  const handleClearHistory = async () => {
    await clearHistory.mutateAsync();
    setMessages([]);
    setHydrated(false);
    toast.success("History cleared");
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header with clear button */}
      {messages.length > 0 && (
        <div className="flex justify-end px-4 pt-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearHistory}
            disabled={clearHistory.isPending}
            className="text-muted-foreground hover:text-destructive gap-1 text-xs"
          >
            <Trash2 className="h-3 w-3" />
            Clear history
          </Button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-4 p-4 min-h-0">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
            Ask a question about your documents
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {query.isPending && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-sm bg-muted px-4 py-3">
              <Spinner className="h-4 w-4" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t p-4">
        <form
          onSubmit={(e) => { e.preventDefault(); send(); }}
          className="flex gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question…"
            disabled={query.isPending}
            className="flex-1"
          />
          <Button type="submit" disabled={!input.trim() || query.isPending}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
