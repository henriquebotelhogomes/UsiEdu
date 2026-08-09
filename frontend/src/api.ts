import type {
  ChatHistoryResponse,
  ChatRequest,
  ChatResponse,
  FeedbackRequest,
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