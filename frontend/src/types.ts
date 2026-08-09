export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  profile: "student" | "staff";
  display_name: string;
}

/** Usuário logado com e-mail (T7.4): o e-mail identifica a sessão persistida. */
export interface StoredUser extends LoginResponse {
  email: string;
}

export interface Source {
  document: string;
  section: string | null;
  excerpt: string;
  url: string | null;
}

export interface ChatRequest {
  session_id: string;
  message: string;
}

export interface ChatResponse {
  session_id: string;
  message_id: string;
  answer: string;
  agents_involved: string[];
  sources: Source[];
  intent: string;
}

export interface FeedbackRequest {
  session_id: string;
  message_id: string;
  rating: "up" | "down";
  comment?: string;
}

// === Insights / satisfação (T8.2) ===

export interface FeedbackStats {
  total: number;
  up: number;
  down: number;
  satisfaction: number;
}

export interface FeedbackRecentItem {
  rating: "up" | "down";
  comment: string | null;
  profile: string;
  created_at: string;
  /** Hash truncado do message_id (o UUID do run não é exposto). */
  message_ref: string;
}

export interface FeedbackRecentResponse {
  items: FeedbackRecentItem[];
}

export interface ChatHistoryMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string | null;
}

export interface ChatHistoryResponse {
  session_id: string;
  messages: ChatHistoryMessage[];
}

// === Streaming SSE (T7.3 / RF2-03) ===

export interface ChatStreamMeta {
  session_id: string;
  message_id: string;
}

export interface ChatStreamFinal {
  agents: string[];
  sources: Source[];
  usage: { intent?: string };
  /** Campo extra do backend para reconciliar o texto final com os tokens. */
  answer: string;
}

export type ChatStreamEvent =
  | ({ event: "meta" } & ChatStreamMeta)
  | { event: "token"; delta: string }
  | ({ event: "final" } & ChatStreamFinal)
  | { event: "error"; detail: string };