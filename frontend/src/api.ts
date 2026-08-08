import type { ChatRequest, ChatResponse, FeedbackRequest, LoginRequest, LoginResponse } from "./types";

const API_BASE = "";

let _token: string | null = null;

export function setToken(token: string | null) {
  _token = token;
}

export function getToken(): string | null {
  return _token;
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
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Erro no chat" }));
    throw new Error(err.detail || "Erro no chat");
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
  if (!res.ok) {
    throw new Error("Erro ao enviar feedback");
  }
}