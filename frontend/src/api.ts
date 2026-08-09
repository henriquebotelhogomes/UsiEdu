import type {
  ChatHistoryResponse,
  ChatRequest,
  ChatResponse,
  ChatStreamEvent,
  ChatStreamFinal,
  ChatStreamMeta,
  FeedbackRecentResponse,
  FeedbackRequest,
  FeedbackStats,
  LoginRequest,
  LoginResponse,
  StoredUser,
} from "./types";

const API_BASE = "";

// Chaves de persistência da sessão (T7.4 / RF2-04)
const TOKEN_KEY = "usiedu_token";
const USER_KEY = "usiedu_user";
const SESSION_PREFIX = "usiedu_session_id:";

let _token: string | null = null;

/** Token expirado/inválido: localStorage foi limpo; redirecionar ao login. */
export class AuthError extends Error {}

function ensureAuthorized(res: Response) {
  if (res.status === 401) {
    clearStoredSession();
    throw new AuthError("Sessão expirada. Faça login novamente.");
  }
}

export function setToken(token: string | null) {
  _token = token;
  if (token === null) {
    localStorage.removeItem(TOKEN_KEY);
  } else {
    localStorage.setItem(TOKEN_KEY, token);
  }
}

export function getToken(): string | null {
  return _token;
}

/** Persiste token + usuário no localStorage (login). */
export function storeSession(user: StoredUser) {
  localStorage.setItem(TOKEN_KEY, user.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/** Restaura a sessão persistida (reload da página) ou null. */
export function loadStoredSession(): StoredUser | null {
  const rawUser = localStorage.getItem(USER_KEY);
  const token = localStorage.getItem(TOKEN_KEY);
  if (!rawUser || !token) return null;
  try {
    const user = JSON.parse(rawUser) as StoredUser;
    return { ...user, access_token: token };
  } catch {
    return null;
  }
}

/** Remove token/usuário persistidos (logout ou 401). */
export function clearStoredSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/** Session id de chat persistido para o usuário (uma conversa por usuário). */
export function getSessionIdFor(email: string): string | null {
  return localStorage.getItem(SESSION_PREFIX + email);
}

export function storeSessionId(email: string, sessionId: string) {
  localStorage.setItem(SESSION_PREFIX + email, sessionId);
}

export async function login(data: LoginRequest): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Erro de autenticação" }));
    throw new Error(err.detail || "Erro de autenticação");
  }
  return res.json();
}

export async function sendChat(data: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${_token}`,
    },
    body: JSON.stringify(data),
  });
  ensureAuthorized(res);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Erro no chat" }));
    throw new Error(err.detail || "Erro no chat");
  }
  return res.json();
}

export async function getChatHistory(sessionId: string): Promise<ChatHistoryResponse> {
  const res = await fetch(
    `${API_BASE}/chat/history?session_id=${encodeURIComponent(sessionId)}`,
    { headers: { Authorization: `Bearer ${_token}` } }
  );
  ensureAuthorized(res);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Erro ao carregar histórico" }));
    throw new Error(err.detail || "Erro ao carregar histórico");
  }
  return res.json();
}

// === Streaming SSE (T7.3 / RF2-03) ===
// SSE sobre POST exige fetch + ReadableStream (EventSource é GET-only).

export interface ChatStreamCallbacks {
  onMeta?: (meta: ChatStreamMeta) => void;
  onToken?: (delta: string) => void;
  onFinal?: (final: ChatStreamFinal) => void;
}

/**
 * Extrai eventos SSE completos do buffer (separados por linha em branco).
 * Retorna o resto (evento parcial) para o próximo chunk de rede.
 */
export function parseSseEvents(buffer: string): { events: ChatStreamEvent[]; rest: string } {
  const events: ChatStreamEvent[] = [];
  let rest = buffer;
  let sep: number;
  while ((sep = rest.indexOf("\n\n")) !== -1) {
    const rawEvent = rest.slice(0, sep);
    rest = rest.slice(sep + 2);
    for (const line of rawEvent.split("\n")) {
      if (!line.startsWith("data: ")) continue;
      events.push(JSON.parse(line.slice("data: ".length)) as ChatStreamEvent);
    }
  }
  return { events, rest };
}

/**
 * Envia mensagem via streaming SSE. Dispara os callbacks conforme os eventos
 * chegam (meta → token(s) → final). Erros de rede/parse propagam para o
 * chamador, que deve fazer fallback para `sendChat`.
 */
export async function sendChatStream(
  data: ChatRequest,
  callbacks: ChatStreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${_token}`,
    },
    body: JSON.stringify(data),
    signal,
  });
  ensureAuthorized(res);
  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({ detail: "Erro no streaming" }));
    throw new Error(err.detail || "Erro no streaming");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const { events, rest } = parseSseEvents(buffer);
      buffer = rest;
      for (const event of events) {
        if (event.event === "meta") callbacks.onMeta?.(event);
        else if (event.event === "token") callbacks.onToken?.(event.delta ?? "");
        else if (event.event === "final") callbacks.onFinal?.(event);
        else if (event.event === "error") {
          throw new Error(event.detail || "Erro no stream");
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export function generateSessionId(): string {
  return `sess-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export async function sendFeedback(data: FeedbackRequest): Promise<void> {
  const res = await fetch(`${API_BASE}/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${_token}`,
    },
    body: JSON.stringify(data),
  });
  ensureAuthorized(res);
  if (!res.ok) {
    throw new Error("Erro ao enviar feedback");
  }
}

// === Insights / satisfação (T8.2) ===

export async function getFeedbackStats(): Promise<FeedbackStats> {
  const res = await fetch(`${API_BASE}/feedback/stats`, {
    headers: { Authorization: `Bearer ${_token}` },
  });
  ensureAuthorized(res);
  if (!res.ok) {
    throw new Error("Erro ao carregar métricas de satisfação");
  }
  return res.json();
}

export async function getFeedbackRecent(limit = 20): Promise<FeedbackRecentResponse> {
  const res = await fetch(`${API_BASE}/feedback/recent?limit=${limit}`, {
    headers: { Authorization: `Bearer ${_token}` },
  });
  ensureAuthorized(res);
  if (!res.ok) {
    throw new Error("Erro ao carregar feedbacks recentes");
  }
  return res.json();
}