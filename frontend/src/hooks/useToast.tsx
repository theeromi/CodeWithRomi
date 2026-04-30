import { createContext, useContext, useState, ReactNode, useCallback } from "react";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";

interface Toast {
  id: number;
  title: string;
  description?: string;
  variant?: "default" | "error" | "success";
}

const Ctx = createContext<{ toast: (t: Omit<Toast, "id">) => void } | null>(null);

let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = (id: number) => setToasts((t) => t.filter((x) => x.id !== id));

  const toast = useCallback((t: Omit<Toast, "id">) => {
    const id = nextId++;
    setToasts((cur) => [...cur, { id, ...t }]);
    setTimeout(() => dismiss(id), 5000);
  }, []);

  return (
    <Ctx.Provider value={{ toast }}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={cn(
              "pointer-events-auto flex items-start gap-3 rounded-2xl border bg-card p-4 shadow-lg",
              t.variant === "error" && "border-destructive/40",
              t.variant === "success" && "border-emerald-500/40",
            )}
          >
            <div className="flex-1">
              <div className="font-medium text-sm">{t.title}</div>
              {t.description && (
                <div className="text-xs text-muted-foreground mt-0.5">{t.description}</div>
              )}
            </div>
            <button
              onClick={() => dismiss(t.id)}
              className="text-muted-foreground hover:text-foreground transition"
            >
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export function useToast() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useToast must be used inside ToastProvider");
  return v;
}
