import { Badge } from "@/components/ui/badge";
import { Loader2 } from "lucide-react";

// Pipeline ordering — used to render "step N of 5". 'uploaded' is the queued
// state before step 1; 'ready' and 'failed' are terminal.
const PIPELINE_STEPS = ["extracting", "chunking", "embedding", "parsing", "summarizing"] as const;

const labels: Record<
  string,
  { label: string; variant: "default" | "secondary" | "success" | "warning" | "error"; spin?: boolean }
> = {
  uploaded:    { label: "Queued",       variant: "secondary", spin: true },
  extracting:  { label: "Extracting",   variant: "warning",   spin: true },
  chunking:    { label: "Chunking",     variant: "warning",   spin: true },
  embedding:   { label: "Embedding",    variant: "warning",   spin: true },
  parsing:     { label: "Parsing rows", variant: "warning",   spin: true },
  summarizing: { label: "Summarizing",  variant: "warning",   spin: true },
  ready:       { label: "Ready",        variant: "success" },
  failed:      { label: "Failed",       variant: "error" },
};

export function StatusBadge({ status }: { status: string }) {
  const m = labels[status] ?? { label: status, variant: "secondary" as const };
  // Show "N/5" for the pipeline-running states so the user can see progress.
  const stepIdx = (PIPELINE_STEPS as readonly string[]).indexOf(status);
  const stepText = stepIdx >= 0 ? `${stepIdx + 1}/${PIPELINE_STEPS.length} ` : "";
  return (
    <Badge variant={m.variant} className="gap-1">
      {m.spin && <Loader2 size={10} className="animate-spin" />}
      {stepText}{m.label}
    </Badge>
  );
}
