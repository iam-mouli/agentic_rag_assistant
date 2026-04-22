"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { usePollDoc } from "@/lib/hooks/use-poll-doc";
import { useUploadDoc } from "@/lib/hooks/use-docs";

export function DocUpload() {
  const [dragging, setDragging] = useState(false);
  const [pollingId, setPollingId] = useState<string | null>(null);
  const upload = useUploadDoc();
  const poll = usePollDoc(pollingId);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        toast.error("Only PDF files are supported");
        return;
      }
      try {
        const res = await upload.mutateAsync(file);
        setPollingId(res.doc_id);
        toast.info(`Uploaded "${file.name}" — processing…`);
      } catch (err) {
        toast.error((err as Error).message);
      }
    },
    [upload]
  );

  // Announce when polling resolves
  const polledStatus = poll.data?.status;
  const polledFile = poll.data?.filename;
  if (polledStatus && polledStatus !== "processing" && pollingId) {
    if (polledStatus === "active") {
      toast.success(`"${polledFile}" is ready — ${poll.data?.chunk_count ?? "?"} chunks indexed`);
    } else {
      toast.error(`"${polledFile}" ingestion ${polledStatus}`);
    }
    setPollingId(null);
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
        dragging ? "border-primary bg-primary/5" : "border-muted-foreground/25"
      }`}
    >
      {upload.isPending || (pollingId && poll.data?.status === "processing") ? (
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <Spinner />
          <span className="text-sm">
            {upload.isPending ? "Uploading…" : "Indexing…"}
          </span>
        </div>
      ) : (
        <>
          <Upload className="h-8 w-8 text-muted-foreground mb-2" />
          <p className="text-sm text-muted-foreground mb-3">Drag and drop a PDF here, or</p>
          <Button size="sm" variant="outline" asChild>
            <label className="cursor-pointer">
              Browse file
              <input
                type="file"
                accept=".pdf"
                className="sr-only"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFile(file);
                  e.target.value = "";
                }}
              />
            </label>
          </Button>
        </>
      )}
    </div>
  );
}
