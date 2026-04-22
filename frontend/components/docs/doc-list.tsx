"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Trash2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { DocStatusBadge } from "./doc-status-badge";
import { useDocs, useDeleteDoc } from "@/lib/hooks/use-docs";
import type { DocDetail } from "@/lib/types";

export function DocList() {
  const { data, isLoading, refetch } = useDocs();
  const deleteDoc = useDeleteDoc();
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const handleDelete = async (doc: DocDetail) => {
    if (confirmId !== doc.doc_id) {
      setConfirmId(doc.doc_id);
      return;
    }
    setConfirmId(null);
    try {
      await deleteDoc.mutateAsync(doc.doc_id);
      toast.success(`"${doc.filename}" removed`);
    } catch (err) {
      toast.error((err as Error).message);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  const docs = data?.documents?.filter((d) => d.status !== "removed" && d.status !== "superseded") ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-muted-foreground">
          {docs.length} document{docs.length !== 1 ? "s" : ""} &middot; {data?.total_chunks ?? 0} chunks total
        </p>
        <Button size="sm" variant="ghost" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-1" /> Refresh
        </Button>
      </div>
      {docs.length === 0 ? (
        <p className="text-center py-10 text-muted-foreground text-sm">No documents yet. Upload a PDF above.</p>
      ) : (
        <div className="rounded-md border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Filename</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-right font-medium">Chunks</th>
                <th className="px-4 py-3 text-right font-medium">Pages</th>
                <th className="px-4 py-3 text-right font-medium">Uploaded</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {docs.map((doc) => (
                <tr key={doc.doc_id} className="border-t hover:bg-muted/20 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs max-w-xs truncate">{doc.filename}</td>
                  <td className="px-4 py-3">
                    <DocStatusBadge status={doc.status} />
                  </td>
                  <td className="px-4 py-3 text-right text-muted-foreground">{doc.chunk_count ?? "—"}</td>
                  <td className="px-4 py-3 text-right text-muted-foreground">{doc.pages ?? "—"}</td>
                  <td className="px-4 py-3 text-right text-muted-foreground">
                    {new Date(doc.uploaded_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      size="sm"
                      variant={confirmId === doc.doc_id ? "destructive" : "ghost"}
                      onClick={() => handleDelete(doc)}
                      disabled={deleteDoc.isPending}
                    >
                      <Trash2 className="h-4 w-4" />
                      {confirmId === doc.doc_id && <span className="ml-1">Confirm</span>}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
