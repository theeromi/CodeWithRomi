import { ReactNode, useEffect, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { FileText, Upload, MessageSquare, LogOut, Moon, Sun, Sparkles, Menu, X, AlertTriangle } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "@/hooks/useTheme";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const navItems = [
  { to: "/", label: "Documents", icon: FileText, end: true },
  { to: "/upload", label: "Upload", icon: Upload },
  { to: "/chat", label: "Chat", icon: MessageSquare },
];

interface HealthResponse {
  status: string;
  ollama: boolean;
  chat_model: string;
  embed_model: string;
}

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const nav = useNavigate();
  const loc = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Close the mobile drawer on route change
  useEffect(() => { setDrawerOpen(false); }, [loc.pathname]);

  // Lock body scroll while the drawer is open on mobile
  useEffect(() => {
    if (drawerOpen) document.body.style.overflow = "hidden";
    else document.body.style.overflow = "";
    return () => { document.body.style.overflow = ""; };
  }, [drawerOpen]);

  const { data: health } = useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: async () => (await fetch("/api/health")).json(),
    refetchInterval: 15000,
    staleTime: 10000,
  });
  const ollamaDown = health && !health.ollama;

  const sidebar = (
    <>
      <div className="mb-8 flex items-center gap-2 px-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <Sparkles size={18} />
        </div>
        <div>
          <div className="text-sm font-semibold leading-tight">VaultAI</div>
          <div className="text-xs text-muted-foreground">Private document vault</div>
        </div>
      </div>

      <nav className="flex flex-col gap-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground font-medium"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
              )
            }
          >
            <item.icon size={16} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto flex flex-col gap-2 pt-4">
        <div className="rounded-xl border bg-background/60 px-3 py-2 text-xs">
          <div className="font-medium truncate">{user?.email}</div>
          <div className="text-muted-foreground">Signed in</div>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="icon" onClick={toggle} title="Toggle theme">
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="flex-1 justify-start"
            onClick={() => { logout(); nav("/login"); }}
          >
            <LogOut size={14} /> Sign out
          </Button>
        </div>
      </div>
    </>
  );

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      {/* Mobile top bar */}
      <header className="flex items-center justify-between border-b bg-card/50 px-4 py-2 md:hidden">
        <button
          aria-label="Open menu"
          className="-ml-1 flex h-9 w-9 items-center justify-center rounded-xl hover:bg-accent"
          onClick={() => setDrawerOpen(true)}
        >
          <Menu size={18} />
        </button>
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Sparkles size={13} />
          </div>
          <span className="text-sm font-semibold">VaultAI</span>
        </div>
        <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle theme">
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </Button>
      </header>

      {/* Desktop sidebar */}
      <aside className="hidden w-64 shrink-0 flex-col border-r bg-card/50 p-4 md:flex">
        {sidebar}
      </aside>

      {/* Mobile drawer */}
      {drawerOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/40 md:hidden"
            onClick={() => setDrawerOpen(false)}
            aria-hidden
          />
          <aside className="fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r bg-card p-4 shadow-xl md:hidden">
            <button
              aria-label="Close menu"
              className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-lg hover:bg-accent"
              onClick={() => setDrawerOpen(false)}
            >
              <X size={16} />
            </button>
            {sidebar}
          </aside>
        </>
      )}

      <main className="flex-1 overflow-y-auto scrollbar-thin">
        {ollamaDown && (
          <div className="flex items-start gap-3 border-b border-amber-500/30 bg-amber-500/10 px-4 py-2 text-xs text-amber-800 dark:text-amber-200">
            <AlertTriangle size={14} className="mt-0.5 shrink-0" />
            <div>
              <div className="font-medium">Local AI is not running.</div>
              <div className="opacity-80">
                Chat and document processing won't work. Start Ollama on the host
                (<code className="rounded bg-amber-500/20 px-1">ollama serve</code>) and ensure
                <code className="rounded bg-amber-500/20 px-1">{health?.chat_model}</code> + <code className="rounded bg-amber-500/20 px-1">{health?.embed_model}</code> are pulled.
              </div>
            </div>
          </div>
        )}
        {children}
      </main>
    </div>
  );
}
