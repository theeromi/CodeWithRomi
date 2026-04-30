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
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
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
  uploadDocument: async (file: File): Promise<DocumentSummary> => {
    const fd = new FormData();
    fd.append("file", file);
    return request<DocumentSummary>("/documents", { method: "POST", body: fd }, true);
  },

  // search
  search: (q: string) =>
    request<SearchHit[]>(`/search?q=${encodeURIComponent(q)}`),

  // chats
  listChats: () => request<ChatSummary[]>("/chats"),
  getChat: (id: number) => request<ChatDetail>(`/chats/${id}`),
  createChat: (title?: string) =>
    request<ChatSummary>("/chats", {
      method: "POST",
      body: JSON.stringify({ title: title ?? null }),
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
  created_at: string;
  messages: MessageResponse[];
}
