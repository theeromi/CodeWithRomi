import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Settings as SettingsIcon, Cpu, Loader2, CheckCircle2, AlertCircle,
  Database, ExternalLink,
} from "lucide-react";
import { api, ApiError, ModelInfo } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/useToast";
import { cn, formatBytes } from "@/lib/utils";

export default function Settings() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["settings"],
    queryFn: api.getSettings,
    refetchOnMount: "always",
  });

  const [pending, setPending] = useState<string | null>(null);

  const swap = useMutation({
    mutationFn: (model: string) => api.setChatModel(model),
    onMutate: (model) => setPending(model),
    onSuccess: (next) => {
      qc.setQueryData(["settings"], next);
      qc.invalidateQueries({ queryKey: ["health"] });
      toast({
        title: `Now using ${next.chat_model}`,
        description: "All new chat messages will use this model.",
        variant: "success",
      });
    },
    onError: (err) => {
      const msg = err instanceof ApiError ? err.message : "Could not switch model";
      toast({ title: "Switch failed", description: msg, variant: "error" });
    },
    onSettled: () => setPending(null),
  });

  if (isLoading) {
    return (
      <div className="container max-w-3xl px-4 py-8">
        <div className="flex justify-center py-16 text-muted-foreground">
          <Loader2 className="animate-spin" />
        </div>
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="container max-w-3xl px-4 py-8">
        <Card className="flex items-start gap-3 border-destructive/30 bg-destructive/5 p-4">
          <AlertCircle size={18} className="text-destructive" />
          <div className="flex-1">
            <div className="text-sm font-medium">Could not load settings</div>
            <div className="mt-1 text-xs text-muted-foreground">
              The backend may be unreachable.
            </div>
          </div>
          <Button size="sm" variant="outline" onClick={() => refetch()}>
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="container max-w-3xl px-4 py-6 md:px-6 md:py-10">
      <div className="mb-6 flex items-center gap-3 md:mb-8">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-accent-foreground">
          <SettingsIcon size={18} />
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">Settings</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Pick which local model answers your questions.
          </p>
        </div>
      </div>

      {/* Ollama connection state */}
      <Card className={cn(
        "mb-4 flex items-center gap-3 p-4",
        data.ollama_reachable ? "" : "border-amber-500/30 bg-amber-500/5",
      )}>
        <div
          className={cn(
            "flex h-9 w-9 items-center justify-center rounded-xl",
            data.ollama_reachable ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                                  : "bg-amber-500/15 text-amber-600 dark:text-amber-400",
          )}
        >
          <Cpu size={16} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium">
            {data.ollama_reachable ? "Local AI is connected" : "Local AI is not reachable"}
          </div>
          <div className="text-xs text-muted-foreground">
            {data.ollama_reachable
              ? `${data.available_models.length} model${data.available_models.length === 1 ? "" : "s"} pulled on host`
              : "Start Ollama to switch models. Chat won't work until it's up."}
          </div>
        </div>
      </Card>

      {/* Embedding model — read-only for now */}
      <Card className="mb-6 p-4">
        <div className="mb-2 flex items-center gap-2">
          <Database size={14} className="text-muted-foreground" />
          <h2 className="text-sm font-semibold">Embedding model</h2>
          <Badge variant="secondary" className="ml-1 font-normal">Locked</Badge>
        </div>
        <div className="text-sm">
          <span className="font-mono">{data.embed_model}</span>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          Embeddings are what make documents searchable. Changing this would invalidate every
          stored vector and require reprocessing every document — kept locked for now.
        </p>
      </Card>

      {/* Chat model — selectable */}
      <Card className="p-4">
        <div className="mb-3 flex items-center gap-2">
          <Cpu size={14} className="text-muted-foreground" />
          <h2 className="text-sm font-semibold">Chat model</h2>
          <span className="ml-auto text-xs text-muted-foreground">
            Currently <span className="font-mono">{data.chat_model}</span>
          </span>
        </div>

        {data.available_models.length === 0 ? (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm">
            No models found. On the host, run{" "}
            <code className="rounded bg-amber-500/10 px-1">ollama pull qwen2.5:14b</code>{" "}
            (or any chat model) and refresh.
          </div>
        ) : (
          <div className="space-y-2">
            {data.available_models.map((m) => (
              <ModelRow
                key={m.name}
                model={m}
                active={m.name === data.chat_model}
                pending={pending === m.name}
                onPick={() => swap.mutate(m.name)}
              />
            ))}
          </div>
        )}

        <p className="mt-4 text-xs text-muted-foreground">
          Tip: bigger models give better answers but are slower.{" "}
          <a
            href="https://ollama.com/library"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-0.5 text-primary hover:underline"
          >
            Browse the Ollama library <ExternalLink size={11} />
          </a>{" "}
          to pull more, then refresh this page.
        </p>
      </Card>
    </div>
  );
}

function ModelRow({
  model, active, pending, onPick,
}: {
  model: ModelInfo;
  active: boolean;
  pending: boolean;
  onPick: () => void;
}) {
  return (
    <button
      onClick={onPick}
      disabled={active || pending}
      className={cn(
        "flex w-full items-center gap-3 rounded-xl border p-3 text-left transition",
        active
          ? "border-primary/60 bg-primary/5"
          : "hover:border-primary/40 hover:bg-accent/30",
        pending && "opacity-60",
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          active ? "bg-primary text-primary-foreground" : "bg-accent text-accent-foreground",
        )}
      >
        <Cpu size={14} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate font-mono text-sm">{model.name}</span>
          {model.parameter_size && (
            <Badge variant="outline" className="font-normal">
              {model.parameter_size}
            </Badge>
          )}
          {active && (
            <Badge variant="success" className="ml-auto gap-1">
              <CheckCircle2 size={11} /> Active
            </Badge>
          )}
        </div>
        <div className="mt-1 text-xs text-muted-foreground">
          {model.family ? `${model.family} · ` : ""}
          {formatBytes(model.size)}
        </div>
      </div>
      {pending && <Loader2 size={14} className="animate-spin text-muted-foreground" />}
    </button>
  );
}
