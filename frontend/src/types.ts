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