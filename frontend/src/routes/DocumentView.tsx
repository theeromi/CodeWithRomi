import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, MessageSquare, Trash2, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { formatBytes, formatDate } from "@/lib/utils";

const PROCESSING = new Set(["uploaded", "extracting", "chunking", "embedding", "summarizing"]);

export default function DocumentView() {
  const { id } = useParams();
  const docId = Number(id);
  const nav = useNavigate();
  const qc = useQueryClient();

  const { data: doc, isLoading } = useQuery({
    queryKey: ["document", docId],
    queryFn: () => api.getDocument(docId),
    refetchInterval: (q) => (q.state.data && PROCESSING.has(q.state.data.status) ? 2000 : false),
  });

  const onDelete = async () => {
    if (!confirm(`Delete "${doc?.filename}"?`)) return;
    await api.deleteDocument(docId);
    qc.invalidateQueries({ queryKey: ["documents"] });
    nav("/");
  };

  const onAsk = async () => {
    const chat = await api.createChat(`Questions about ${doc?.filename}`);
    nav(`/chat/${chat.id}`);
  };

  if (isLoading || !doc) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="container max-w-6xl py-10">
      <Button variant="ghost" size="sm" onClick={() => nav("/")}>
        <ArrowLeft size={14} /> Back
      </Button>

      <div className="mt-4 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{doc.filename}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <StatusBadge status={doc.status} />
            <span>·</span>
            <span>{formatBytes(doc.size_bytes)}</span>
            <span>·</span>
            <span>{formatDate(doc.created_at)}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onAsk}>
            <MessageSquare size={14} /> Ask about this
          </Button>
          <Button variant="ghost" onClick={onDelete}>
            <Trash2 size={14} />
          </Button>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_18rem]">
        <Card className="p-6">
          <h2 className="text-sm font-semibold text-muted-foreground">Extracted text</h2>
          <pre className="mt-3 max-h-[70vh] overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed scrollbar-thin">
            {doc.extracted_text || (PROCESSING.has(doc.status) ? "Processing…" : "No text extracted.")}
          </pre>
        </Card>

        <div className="space-y-6">
          <Card className="p-6">
            <h2 className="text-sm font-semibold text-muted-foreground">Summary</h2>
            <p className="mt-3 text-sm leading-relaxed">
              {doc.summary || (PROCESSING.has(doc.status) ? "Generating…" : "—")}
            </p>
          </Card>

          {doc.status === "failed" && doc.error && (
            <Card className="border-destructive/30 bg-destructive/5 p-4">
              <h2 className="text-xs font-semibold text-destructive">Error</h2>
              <p className="mt-1 text-xs">{doc.error}</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
