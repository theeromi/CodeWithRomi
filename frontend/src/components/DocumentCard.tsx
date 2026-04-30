import { Link } from "react-router-dom";
import { FileText, Trash2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/StatusBadge";
import { DocumentSummary } from "@/lib/api";
import { formatBytes, relativeTime } from "@/lib/utils";

interface Props {
  doc: DocumentSummary;
  onDelete: (id: number) => void;
}

export function DocumentCard({ doc, onDelete }: Props) {
  return (
    <Card className="group flex flex-col p-5 transition-shadow hover:shadow-md">
      <Link to={`/documents/${doc.id}`} className="flex-1 space-y-3">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent text-accent-foreground">
            <FileText size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="font-medium truncate" title={doc.filename}>
              {doc.filename}
            </div>
            <div className="text-xs text-muted-foreground">
              {formatBytes(doc.size_bytes)} · {relativeTime(doc.created_at)}
            </div>
          </div>
          <StatusBadge status={doc.status} />
        </div>

        <p className="text-sm text-muted-foreground line-clamp-3 min-h-[3.75rem]">
          {doc.status === "failed"
            ? doc.error || "Processing failed."
            : doc.summary || (doc.status === "ready" ? "" : "Processing…")}
        </p>
      </Link>

      <div className="mt-3 flex justify-end opacity-0 transition-opacity group-hover:opacity-100">
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.preventDefault();
            if (confirm(`Delete "${doc.filename}"?`)) onDelete(doc.id);
          }}
        >
          <Trash2 size={14} />
        </Button>
      </div>
    </Card>
  );
}
