import { Chat } from "@/components/query/chat";

export default function QueryPage() {
  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="mb-4">
        <h1 className="text-2xl font-bold">Query</h1>
        <p className="text-muted-foreground text-sm mt-1">Ask questions about your indexed documents</p>
      </div>
      <div className="flex-1 rounded-lg border bg-background overflow-hidden min-h-0">
        <Chat />
      </div>
    </div>
  );
}
