import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import { useQueryClient } from "@tanstack/react-query";
import { CloudUpload, CheckCircle2, AlertCircle, Loader2, FileText } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { cn, formatBytes } from "@/lib/utils";

interface Item {
  file: File;
  state: "uploading" | "done" | "error";
  message?: string;
}

const ACCEPT = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "text/plain": [".txt"],
  "text/markdown": [".md"],
};

export default function UploadPage() {
  const qc = useQueryClient();
  const nav = useNavigate();
  const [items, setItems] = useState<Item[]>([]);

  const onDrop = useCallback(async (files: File[]) => {
    const start = items.length;
    setItems((cur) => [...cur, ...files.map((f) => ({ file: f, state: "uploading" as const }))]);
    await Promise.all(
      files.map(async (f, i) => {
        try {
          await api.uploadDocument(f);
          setItems((cur) => {
            const next = [...cur];
            next[start + i] = { ...next[start + i], state: "done" };
            return next;
          });
        } catch (err) {
          const msg = err instanceof ApiError ? err.message : "Upload failed";
          setItems((cur) => {
            const next = [...cur];
            next[start + i] = { ...next[start + i], state: "error", message: msg };
            return next;
          });
        }
      }),
    );
    qc.invalidateQueries({ queryKey: ["documents"] });
  }, [items.length, qc]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT,
    multiple: true,
  });

  return (
    <div className="container max-w-3xl py-10">
      <h1 className="text-3xl font-semibold tracking-tight">Upload documents</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        PDF, DOCX, TXT, or Markdown. Files are stored locally and processed by your local Ollama.
      </p>

      <div
        {...getRootProps()}
        className={cn(
          "mt-8 flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-12 text-center transition-colors",
          isDragActive
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50 hover:bg-accent/30",
        )}
      >
        <input {...getInputProps()} />
        <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-accent text-accent-foreground">
          <CloudUpload size={26} />
        </div>
        <div className="text-base font-medium">
          {isDragActive ? "Drop to upload" : "Drag files here or click to browse"}
        </div>
        <div className="mt-1 text-xs text-muted-foreground">PDF · DOCX · TXT · MD</div>
      </div>

      {items.length > 0 && (
        <div className="mt-6 space-y-2">
          {items.map((it, i) => (
            <Card key={i} className="flex items-center gap-3 p-4">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent text-accent-foreground">
                <FileText size={16} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium">{it.file.name}</div>
                <div className="text-xs text-muted-foreground">
                  {formatBytes(it.file.size)}
                  {it.message && <span className="text-destructive"> · {it.message}</span>}
                </div>
              </div>
              {it.state === "uploading" && <Loader2 size={16} className="animate-spin text-muted-foreground" />}
              {it.state === "done" && <CheckCircle2 size={18} className="text-emerald-500" />}
              {it.state === "error" && <AlertCircle size={18} className="text-destructive" />}
            </Card>
          ))}

          {items.every((i) => i.state !== "uploading") && (
            <div className="flex justify-end pt-2">
              <Button onClick={() => nav("/")}>Back to documents</Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
