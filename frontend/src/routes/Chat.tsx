import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Send, Plus, MessageSquare, Loader2, FileText, Trash2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, apiBaseUrl, Citation, getToken, MessageResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface LiveMessage extends MessageResponse {
  streaming?: boolean;
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

  const send = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || streaming) return;

    let activeChatId = chatId;
    if (activeChatId === null) {
      const c = await api.createChat(input.slice(0, 60));
      qc.invalidateQueries({ queryKey: ["chats"] });
      nav(`/chat/${c.id}`, { replace: true });
      activeChatId = c.id;
    }

    const userMessage: LiveMessage = {
      id: -Date.now(),
      role: "user",
      content: input,
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
    };
    setLiveMessages((cur) => [...(cur ?? []), userMessage, assistantPlaceholder]);
    const question = input;
    setInput("");
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
      if (!res.ok || !res.body) throw new Error(`Request failed: ${res.status}`);

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
          content: last.content + `\n\n_Error: ${(err as Error).message}_`,
          streaming: false,
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
        next[next.length - 1] = {
          ...last,
          content: last.content + `\n\n_Error: ${data}_`,
          streaming: false,
        };
        return next;
      });
    }
  }

  return (
    <div className="flex h-screen">
      <div className="flex w-72 shrink-0 flex-col border-r bg-card/30 p-3">
        <Button onClick={newChat} className="mb-3 w-full justify-start" variant="outline">
          <Plus size={14} /> New chat
        </Button>
        <div className="flex-1 space-y-1 overflow-y-auto scrollbar-thin">
          {chats?.map((c) => (
            <div key={c.id} className="group relative">
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
            </div>
          ))}
          {chats && chats.length === 0 && (
            <div className="px-3 py-2 text-xs text-muted-foreground">No chats yet</div>
          )}
        </div>
      </div>

      <div className="flex flex-1 flex-col">
        <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin">
          <div className="container max-w-3xl py-8">
            {messages.length === 0 ? (
              <div className="mt-20 text-center">
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-accent text-accent-foreground">
                  <MessageSquare size={20} />
                </div>
                <h2 className="text-lg font-medium">Ask anything about your documents</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Answers are grounded in your uploaded files and stay on your machine.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {messages.map((m) => (
                  <MessageBubble key={m.id} message={m} />
                ))}
              </div>
            )}
          </div>
        </div>

        <form onSubmit={send} className="border-t bg-background p-4">
          <div className="container max-w-3xl flex gap-2">
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

function MessageBubble({ message }: { message: LiveMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-3 text-sm",
          isUser ? "bg-primary text-primary-foreground" : "bg-card border",
        )}
      >
        {isUser ? (
          <div className="whitespace-pre-wrap">{message.content}</div>
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
