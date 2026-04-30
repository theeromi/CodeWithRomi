import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FilePlus2, Search as SearchIcon, FileText } from "lucide-react";
import { api, SearchHit } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { DocumentCard } from "@/components/DocumentCard";
import { useToast } from "@/hooks/useToast";

const PROCESSING = new Set(["uploaded", "extracting", "chunking", "embedding", "summarizing"]);

export default function Dashboard() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [searching, setSearching] = useState(false);

  const { data: docs } = useQuery({
    queryKey: ["documents"],
    queryFn: api.listDocuments,
    refetchInterval: (query) => {
      const list = query.state.data;
      return list && list.some((d) => PROCESSING.has(d.status)) ? 2000 : false;
    },
  });

  // debounced search
  useEffect(() => {
    if (!q.trim()) { setHits(null); return; }
    const handle = setTimeout(async () => {
      setSearching(true);
      try {
        setHits(await api.search(q));
      } catch {
        setHits([]);
      } finally {
        setSearching(false);
      }
    }, 250);
    return () => clearTimeout(handle);
  }, [q]);

  const onDelete = async (id: number) => {
    try {
      await api.deleteDocument(id);
      qc.invalidateQueries({ queryKey: ["documents"] });
    } catch (e) {
      toast({ title: "Could not delete", variant: "error" });
    }
  };

  const empty = docs && docs.length === 0;
  const filteredCount = useMemo(() => (hits ? hits.length : null), [hits]);

  return (
    <div className="container max-w-6xl py-10">
      <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Your documents</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Upload PDFs, DOCX, or text files. Everything stays on your machine.
          </p>
        </div>
        <Button asChild size="lg">
          <Link to="/upload"><FilePlus2 size={16} /> Upload</Link>
        </Button>
      </div>

      <div className="relative mb-6">
        <SearchIcon size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input
          className="pl-9 h-11"
          placeholder="Search across your documents…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

      {hits !== null ? (
        <div>
          <div className="mb-3 text-sm text-muted-foreground">
            {searching ? "Searching…" : `${filteredCount} ${filteredCount === 1 ? "result" : "results"} for "${q}"`}
          </div>
          <div className="space-y-2">
            {hits.map((h) => (
              <Link
                key={`${h.document_id}-${h.snippet}`}
                to={`/documents/${h.document_id}`}
                className="block"
              >
                <Card className="p-4 transition hover:bg-accent/40">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <FileText size={14} /> {h.filename}
                  </div>
                  <p
                    className="mt-1 text-sm text-muted-foreground"
                    dangerouslySetInnerHTML={{ __html: h.snippet }}
                  />
                </Card>
              </Link>
            ))}
            {!searching && hits.length === 0 && (
              <Card className="p-6 text-center text-sm text-muted-foreground">
                No matches found.
              </Card>
            )}
          </div>
        </div>
      ) : empty ? (
        <Card className="flex flex-col items-center gap-3 p-12 text-center">
          <FileText className="text-muted-foreground" />
          <div>
            <div className="text-base font-medium">No documents yet</div>
            <p className="mt-1 text-sm text-muted-foreground">
              Upload your first file to start asking questions.
            </p>
          </div>
          <Button asChild className="mt-2">
            <Link to="/upload"><FilePlus2 size={16} /> Upload a document</Link>
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {docs?.map((d) => (
            <DocumentCard key={d.id} doc={d} onDelete={onDelete} />
          ))}
        </div>
      )}
    </div>
  );
}
