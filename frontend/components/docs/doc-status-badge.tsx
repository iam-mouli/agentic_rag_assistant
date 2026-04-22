import { Badge } from "@/components/ui/badge";
import type { DocDetail } from "@/lib/types";

type Status = DocDetail["status"];

const STATUS_CONFIG: Record<Status, { label: string; variant: "processing" | "success" | "destructive" | "warning" | "secondary" }> = {
  processing: { label: "Processing", variant: "processing" },
  active: { label: "Active", variant: "success" },
  failed: { label: "Failed", variant: "destructive" },
  quarantined: { label: "Quarantined", variant: "warning" },
  removed: { label: "Removed", variant: "secondary" },
  superseded: { label: "Superseded", variant: "secondary" },
};

export function DocStatusBadge({ status }: { status: Status }) {
  const { label, variant } = STATUS_CONFIG[status] ?? { label: status, variant: "secondary" };
  return <Badge variant={variant}>{label}</Badge>;
}
