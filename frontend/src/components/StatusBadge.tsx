import { Badge } from "@/components/ui/badge";
import { Loader2 } from "lucide-react";

const labels: Record<string, { label: string; variant: "default" | "secondary" | "success" | "warning" | "error"; spin?: boolean }> = {
  uploaded:    { label: "Queued",        variant: "secondary", spin: true },
  extracting:  { label: "Extracting",    variant: "warning",   spin: true },
  chunking:    { label: "Chunking",      variant: "warning",   spin: true },
  embedding:   { label: "Embedding",     variant: "warning",   spin: true },
  parsing:     { label: "Parsing rows",  variant: "warning",   spin: true },
  summarizing: { label: "Summarizing",   variant: "warning",   spin: true },
  ready:       { label: "Ready",        variant: "success" },
  failed:      { label: "Failed",       variant: "error" },
};

export function StatusBadge({ status }: { status: string }) {
  const m = labels[status] ?? { label: status, variant: "secondary" as const };
  return (
    <Badge variant={m.variant} className="gap-1">
      {m.spin && <Loader2 size={10} className="animate-spin" />}
      {m.label}
    </Badge>
  );
}
