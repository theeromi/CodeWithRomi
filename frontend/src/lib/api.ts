const API_BASE = (import.meta.env.VITE_API_BASE as string) || "/api";

const TOKEN_KEY = "vaultai_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string | null) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  asForm = false,
): Promise<T> {
  const headers: Record<string, string> = {
    ...((init.headers as Record<string, string>) || {}),
  };
  if (!asForm) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const r = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!r.ok) {
    let detail = r.statusText;
    try {
      const body = await r.json();
      // Three FastAPI error shapes we care about:
      //   1) {"detail": "plain string"}                    — most routes
      //   2) {"detail": {"error": "...", "message": "..."}} — quota helpers (limits.py)
      //   3) {"error": "rate_limited", "detail": "..."}     — slowapi 429 handler
      if (body?.error === "rate_limited" && typeof body.detail === "string") {
        detail = body.detail;
      } else if (body?.detail) {
        if (typeof body.detail === "string") {
          detail = body.detail;
        } else if (typeof body.detail === "object" && typeof body.detail.message === "string") {
          detail = body.detail.message;
        } else {
          detail = JSON.stringify(body.detail);
        }
      }
    } catch { /* empty */ }
    throw new ApiError(r.status, detail);
  }
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
}

export const api = {
  // auth
  register: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<UserResponse>("/auth/me"),

  // documents
  listDocuments: () => request<DocumentSummary[]>("/documents"),
  getDocument: (id: number) => request<DocumentDetail>(`/documents/${id}`),
  getDocumentStatus: (id: number) =>
    request<{ id: number; status: string; error: string | null }>(`/documents/${id}/status`),
  deleteDocument: (id: number) =>
    request<void>(`/documents/${id}`, { method: "DELETE" }),
  retryDocument: (id: number) =>
    request<DocumentSummary>(`/documents/${id}/retry`, { method: "POST" }),
  uploadDocument: async (file: File): Promise<DocumentSummary> => {
    const fd = new FormData();
    fd.append("file", file);
    return request<DocumentSummary>("/documents", { method: "POST", body: fd }, true);
  },
  getTransactions: (id: number) => request<TransactionsData>(`/documents/${id}/transactions`),

  // search
  search: (q: string) =>
    request<SearchHit[]>(`/search?q=${encodeURIComponent(q)}`),

  // settings
  getSettings: () => request<SettingsData>("/settings"),
  setChatModel: (chatModel: string) =>
    request<SettingsData>("/settings/chat-model", {
      method: "PUT",
      body: JSON.stringify({ chat_model: chatModel }),
    }),

  // chats
  listChats: () => request<ChatSummary[]>("/chats"),
  getChat: (id: number) => request<ChatDetail>(`/chats/${id}`),
  createChat: (title?: string, documentId?: number) =>
    request<ChatSummary>("/chats", {
      method: "POST",
      body: JSON.stringify({ title: title ?? null, document_id: documentId ?? null }),
    }),
  deleteChat: (id: number) =>
    request<void>(`/chats/${id}`, { method: "DELETE" }),
};

export const apiBaseUrl = API_BASE;

// Types mirrored from backend schemas
export interface UserResponse {
  id: number;
  email: string;
  created_at: string;
}
export interface DocumentSummary {
  id: number;
  filename: string;
  mime_type: string;
  size_bytes: number;
  status: string;
  summary: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}
export interface DocumentDetail extends DocumentSummary {
  extracted_text: string | null;
}
export interface SearchHit {
  document_id: number;
  filename: string;
  snippet: string;
  score: number;
}
export interface ChatSummary {
  id: number;
  title: string;
  document_id: number | null;
  created_at: string;
}
export interface Citation {
  document_id: number;
  filename: string;
  chunk_ordinal: number;
  snippet: string;
}
export interface MessageResponse {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  citations: Citation[];
  created_at: string;
}
export interface ChatDetail {
  id: number;
  title: string;
  document_id: number | null;
  document_filename: string | null;
  created_at: string;
  messages: MessageResponse[];
}

export interface TransactionLine {
  id: number;
  ordinal: number;
  posted_date: string | null;
  description: string;
  category: string | null;
  direction: "debit" | "credit";
  amount: number;
  balance_after: number | null;
  source_format: string;
}

export interface TransactionExtreme {
  description: string;
  posted_date: string | null;
  amount: number;
}

export interface TransactionStats {
  count_total: number;
  count_debits: number;
  count_credits: number;
  total_debits: number;
  total_credits: number;
  net: number;
  max_debit: TransactionExtreme | null;
  max_credit: TransactionExtreme | null;
  min_debit: TransactionExtreme | null;
  min_credit: TransactionExtreme | null;
}

export interface TransactionsData {
  document_id: number;
  source_format: string | null;
  stats: TransactionStats;
  lines: TransactionLine[];
}

export interface ModelInfo {
  name: string;
  size: number;
  parameter_size: string | null;
  family: string | null;
  modified_at: string | null;
}

export interface SettingsData {
  chat_model: string;
  embed_model: string;
  available_models: ModelInfo[];
  ollama_reachable: boolean;
}
