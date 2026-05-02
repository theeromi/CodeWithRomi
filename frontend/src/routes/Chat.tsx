import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Send, Plus, MessageSquare, Loader2, FileText, Trash2, CheckSquare, Square, X, AlertCircle, RotateCw } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, apiBaseUrl, Citation, getToken, MessageResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface LiveMessage extends MessageResponse {
  streaming?: boolean;
  error?: string;     // network/ollama error, surfaced as a card with retry
  retryFor?: string;  // the user question this assistant message was answering
}

export default function Chat() {
  const { id } = useParams();
  const chatId = id ? Number(id) : null;
  const nav = useNavigate();
  const qc = useQueryClient();

  const { data: chats } = useQuery({ queryKey: ["chats"], queryFn: api.listChats });
  const { data: chatDetail } = useQuery({
    queryKey: ["chat", chatId],
    queryFn: () => api.getChat(chatId!),
    enabled: chatId !== null,
  });

  const [liveMessages, setLiveMessages] = useState<LiveMessage[] | null>(null);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Multi-select state for the chat sidebar
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const allSelected = !!chats && chats.length > 0 && selectedIds.size === chats.length;

  // Mobile drawer state for the chat list
  const [chatListOpen, setChatListOpen] = useState(false);
  useEffect(() => { setChatListOpen(false); }, [chatId]);

  useEffect(() => {
    setLiveMessages(chatDetail ? chatDetail.messages : null);
  }, [chatDetail]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [liveMessages]);

  const messages = useMemo<LiveMessage[]>(() => liveMessages ?? [], [liveMessages]);

  const newChat = async () => {
    const c = await api.createChat();
    qc.invalidateQueries({ queryKey: ["chats"] });
    nav(`/chat/${c.id}`);
  };

  const removeChat = async (cid: number) => {
    if (!confirm("Delete this chat?")) return;
    await api.deleteChat(cid);
    qc.invalidateQueries({ queryKey: ["chats"] });
    if (chatId === cid) nav("/chat");
  };

  const toggleSelected = (cid: number) =>
    setSelectedIds((s) => {
      const next = new Set(s);
      next.has(cid) ? next.delete(cid) : next.add(cid);
      return next;
    });

  const exitSelectMode = () => { setSelectMode(false); setSelectedIds(new Set()); };

  const selectAllToggle = () => {
    if (!chats) return;
    setSelectedIds(allSelected ? new Set() : new Set(chats.map((c) => c.id)));
  };

  const deleteSelected = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Delete ${selectedIds.size} chat${selectedIds.size === 1 ? "" : "s"}? This cannot be undone.`)) return;
    const ids = [...selectedIds];
    await Promise.all(ids.map((id) => api.deleteChat(id)));
    qc.invalidateQueries({ queryKey: ["chats"] });
    if (chatId !== null && selectedIds.has(chatId)) nav("/chat");
    exitSelectMode();
  };

  const send = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || streaming) return;
    await sendQuestion(input);
    setInput("");
  };

  const retryLast = async (question: string) => {
    if (streaming) return;
    // Drop the failed assistant placeholder before re-asking, so the retry
    // doesn't accumulate ghost messages on screen.
    setLiveMessages((cur) => {
      if (!cur) return cur;
      const next = [...cur];
      // Remove trailing assistant message if it had an error
      if (next.length && next[next.length - 1].role === "assistant" && next[next.length - 1].error) {
        next.pop();
      }
      // Also remove the matching user message we'll re-add inside sendQuestion
      if (next.length && next[next.length - 1].role === "user" && next[next.length - 1].content === question) {
        next.pop();
      }
      return next;
    });
    await sendQuestion(question);
  };

  const sendQuestion = async (question: string) => {
    let activeChatId = chatId;
    if (activeChatId === null) {
      const c = await api.createChat(question.slice(0, 60));
      qc.invalidateQueries({ queryKey: ["chats"] });
      nav(`/chat/${c.id}`, { replace: true });
      activeChatId = c.id;
    }

    const userMessage: LiveMessage = {
      id: -Date.now(),
      role: "user",
      content: question,
      citations: [],
      created_at: new Date().toISOString(),
    };
    const assistantPlaceholder: LiveMessage = {
      id: -Date.now() - 1,
      role: "assistant",
      content: "",
      citations: [],
      created_at: new Date().toISOString(),
      streaming: true,
      retryFor: question,
    };
    setLiveMessages((cur) => [...(cur ?? []), userMessage, assistantPlaceholder]);
    setStreaming(true);

    try {
      const res = await fetch(`${apiBaseUrl}/chats/${activeChatId}/messages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ content: question }),
      });
      if (!res.ok || !res.body) {
        // Mirror the parser in lib/api.ts: handle slowapi rate-limit shape,
        // FastAPI quota dict shape, and plain {"detail": "..."}.
        let detail = `HTTP ${res.status}`;
        try {
          const body = await res.json();
          if (body?.error === "rate_limited" && typeof body.detail === "string") {
            detail = body.detail;
          } else if (body?.detail) {
            if (typeof body.detail === "string") detail = body.detail;
            else if (typeof body.detail === "object" && typeof body.detail.message === "string") detail = body.detail.message;
            else detail = JSON.stringify(body.detail);
          }
        } catch { /* empty */ }
        throw new Error(detail);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let idx;
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
          const block = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          handleEvent(block);
        }
      }
    } catch (err) {
      setLiveMessages((cur) => {
        if (!cur) return cur;
        const next = [...cur];
        const last = next[next.length - 1];
        next[next.length - 1] = {
          ...last,
          streaming: false,
          error: (err as Error).message || "Connection lost.",
        };
        return next;
      });
    } finally {
      setStreaming(false);
      qc.invalidateQueries({ queryKey: ["chat", activeChatId] });
      qc.invalidateQueries({ queryKey: ["chats"] });
    }
  };

  function handleEvent(raw: string) {
    let event = "message";
    const dataLines: string[] = [];
    for (const line of raw.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) {
        // SSE spec: strip exactly one leading space after "data:"; preserve the rest.
        // Trimming would eat whitespace-only tokens (spaces between words from the LLM).
        let v = line.slice(5);
        if (v.startsWith(" ")) v = v.slice(1);
        dataLines.push(v);
      }
    }
    const data = dataLines.join("\n");
    if (event === "citations") {
      try {
        const citations = JSON.parse(data) as Citation[];
        setLiveMessages((cur) => {
          if (!cur) return cur;
          const next = [...cur];
          const last = next[next.length - 1];
          next[next.length - 1] = { ...last, citations };
          return next;
        });
      } catch { /* empty */ }
    } else if (event === "token") {
      setLiveMessages((cur) => {
        if (!cur) return cur;
        const next = [...cur];
        const last = next[next.length - 1];
        next[next.length - 1] = { ...last, content: last.content + data };
        return next;
      });
    } else if (event === "done") {
      setLiveMessages((cur) => {
        if (!cur) return cur;
        const next = [...cur];
        const last = next[next.length - 1];
        next[next.length - 1] = { ...last, streaming: false };
        return next;
      });
    } else if (event === "error") {
      setLiveMessages((cur) => {
        if (!cur) return cur;
        const next = [...cur];
        const last = next[next.length - 1];
        next[next.length - 1] = { ...last, streaming: false, error: data || "Generation failed." };
        return next;
      });
    }
  }

  return (
    <div className="flex h-[calc(100vh-3rem)] md:h-screen">
      {/* Mobile chat-list toggle */}
      <button
        aria-label={chatListOpen ? "Hide chats" : "Show chats"}
        className="fixed bottom-20 right-4 z-30 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg md:hidden"
        onClick={() => setChatListOpen((v) => !v)}
      >
        {chatListOpen ? <X size={18} /> : <MessageSquare size={18} />}
      </button>

      {chatListOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/40 md:hidden"
          onClick={() => setChatListOpen(false)}
          aria-hidden
        />
      )}

      <div
        className={cn(
          "flex shrink-0 flex-col border-r bg-card/30 p-3",
          // Desktop: always visible 72-wide column
          "md:relative md:w-72",
          // Mobile: drawer from the left
          "fixed inset-y-0 left-0 z-30 w-72 transition-transform md:translate-x-0",
          chatListOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {selectMode ? (
          <div className="mb-3 flex items-center gap-1">
            <Button onClick={selectAllToggle} variant="outline" size="sm" className="flex-1 justify-start">
              {allSelected ? <CheckSquare size={14} /> : <Square size={14} />}
              {allSelected ? "Unselect all" : "Select all"}
            </Button>
            <Button onClick={exitSelectMode} variant="ghost" size="icon" title="Cancel">
              <X size={14} />
            </Button>
          </div>
        ) : (
          <div className="mb-3 flex items-center gap-1">
            <Button onClick={newChat} variant="outline" size="sm" className="flex-1 justify-start">
              <Plus size={14} /> New chat
            </Button>
            {chats && chats.length > 0 && (
              <Button onClick={() => setSelectMode(true)} variant="ghost" size="icon" title="Select to delete">
                <CheckSquare size={14} />
              </Button>
            )}
          </div>
        )}

        {selectMode && selectedIds.size > 0 && (
          <Button onClick={deleteSelected} variant="destructive" size="sm" className="mb-3 w-full">
            <Trash2 size={14} /> Delete {selectedIds.size} chat{selectedIds.size === 1 ? "" : "s"}
          </Button>
        )}

        <div className="flex-1 space-y-1 overflow-y-auto scrollbar-thin">
          {chats?.map((c) => {
            const checked = selectedIds.has(c.id);
            return (
              <div key={c.id} className="group relative">
                {selectMode ? (
                  <button
                    onClick={() => toggleSelected(c.id)}
                    className={cn(
                      "flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm transition",
                      checked
                        ? "bg-primary/10 text-foreground ring-1 ring-primary/40"
                        : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                    )}
                  >
                    {checked ? <CheckSquare size={14} className="shrink-0 text-primary" /> : <Square size={14} className="shrink-0" />}
                    <span className="truncate">{c.title}</span>
                  </button>
                ) : (
                  <>
                    <Link
                      to={`/chat/${c.id}`}
                      className={cn(
                        "flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition",
                        chatId === c.id
                          ? "bg-accent text-accent-foreground"
                          : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                      )}
                    >
                      <MessageSquare size={14} className="shrink-0" />
                      <span className="truncate">{c.title}</span>
                    </Link>
                    <button
                      onClick={() => removeChat(c.id)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition text-muted-foreground hover:text-destructive"
                      title="Delete"
                    >
                      <Trash2 size={12} />
                    </button>
                  </>
                )}
              </div>
            );
          })}
          {chats && chats.length === 0 && (
            <div className="px-3 py-2 text-xs text-muted-foreground">No chats yet</div>
          )}
        </div>
      </div>

      <div className="flex flex-1 flex-col">
        {chatDetail?.document_filename && (
          <div className="flex items-center gap-2 border-b bg-accent/30 px-4 py-2 text-xs">
            <FileText size={12} className="shrink-0 text-muted-foreground" />
            <span className="text-muted-foreground">Scoped to</span>
            <Link
              to={`/documents/${chatDetail.document_id}`}
              className="truncate font-medium hover:underline"
            >
              {chatDetail.document_filename}
            </Link>
          </div>
        )}
        <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin">
          <div className="container max-w-3xl px-4 py-6 md:px-6 md:py-8">
            {messages.length === 0 ? (
              <div className="mt-12 text-center md:mt-20">
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-accent text-accent-foreground">
                  <MessageSquare size={20} />
                </div>
                <h2 className="text-base font-medium md:text-lg">Ask anything about your documents</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Answers are grounded in your uploaded files and stay on your machine.
                </p>
              </div>
            ) : (
              <div className="space-y-4 md:space-y-6">
                {messages.map((m) => (
                  <MessageBubble key={m.id} message={m} onRetry={retryLast} />
                ))}
              </div>
            )}
          </div>
        </div>

        <form onSubmit={send} className="border-t bg-background p-3 md:p-4">
          <div className="container flex max-w-3xl gap-2 px-1">
            <Input
              placeholder="Ask a question about your documents…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={streaming}
              className="h-11"
            />
            <Button type="submit" size="lg" disabled={streaming || !input.trim()}>
              {streaming ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function MessageBubble({
  message, onRetry,
}: { message: LiveMessage; onRetry: (q: string) => void }) {
  const isUser = message.role === "user";
  const hasError = !!message.error;
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[90%] rounded-2xl px-4 py-3 text-sm md:max-w-[85%]",
          isUser
            ? "bg-primary text-primary-foreground"
            : hasError
            ? "border border-destructive/30 bg-destructive/5"
            : "bg-card border",
        )}
      >
        {isUser ? (
          <div className="whitespace-pre-wrap">{message.content}</div>
        ) : hasError ? (
          <div className="space-y-2">
            <div className="flex items-start gap-2">
              <AlertCircle size={14} className="mt-0.5 shrink-0 text-destructive" />
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium text-destructive">Couldn't get an answer</div>
                <div className="mt-0.5 text-xs text-muted-foreground break-words">{message.error}</div>
              </div>
            </div>
            {message.retryFor && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => onRetry(message.retryFor!)}
                className="h-7"
              >
                <RotateCw size={12} /> Retry
              </Button>
            )}
          </div>
        ) : (
          <>
            <div className="prose prose-sm dark:prose-invert max-w-none">
              {message.content ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
              ) : (
                <span className="text-muted-foreground">
                  <Loader2 size={14} className="inline animate-spin mr-1" /> Thinking…
                </span>
              )}
            </div>
            {message.citations.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {message.citations.map((c, i) => (
                  <Link
                    key={`${c.document_id}-${c.chunk_ordinal}`}
                    to={`/documents/${c.document_id}`}
                    title={c.snippet}
                    className="inline-flex items-center gap-1 rounded-full bg-accent px-2 py-0.5 text-xs text-accent-foreground hover:bg-accent/80"
                  >
                    <FileText size={10} />[{i + 1}] {c.filename}
                  </Link>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
