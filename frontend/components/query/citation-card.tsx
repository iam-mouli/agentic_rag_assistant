import { FileText } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { Citation } from "@/lib/types";

export function CitationCard({ citation }: { citation: Citation }) {
  return (
    <Card className="text-xs">
      <CardContent className="p-3 flex gap-2 items-start">
        <FileText className="h-4 w-4 mt-0.5 shrink-0 text-muted-foreground" />
        <div className="min-w-0">
          <p className="font-medium truncate">{citation.filename ?? "Unknown file"}</p>
          {citation.page != null && (
            <p className="text-muted-foreground">Page {citation.page}</p>
          )}
          {citation.chunk_preview && (
            <p className="mt-1 text-muted-foreground line-clamp-2 italic">
              &ldquo;{citation.chunk_preview}&rdquo;
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
