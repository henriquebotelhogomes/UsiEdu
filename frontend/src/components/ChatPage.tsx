import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import type { ChatResponse, ChatSessionSummary, StoredUser } from "../types";
import {
  AuthError,
  RateLimitError,
  generateSessionId,
  getChatHistory,
  getSessionIdFor,
  sendChat,
  sendChatStream,
  sendFeedback,
  storeSessionId,
} from "../api";
import Markdown from "./Markdown";
import MessageCard from "./MessageCard";

const SCENARIOS = [
  { label: "Notas e faltas", icon: "📊", message: "Quero ver minhas notas e faltas", intent: "academico" },
  { label: "Boleto e renegociação", icon: "💳", message: "Qual o valor do meu boleto? Pode simular renegociação?", intent: "financeiro" },
  { label: "Pergunta composta", icon: "🧠", message: "Quero ver minhas notas e o valor do boleto", intent: "composta" },
  { label: "Política institucional", icon: "🏛️", message: "Qual a política de uso dos laboratórios?", intent: "institucional" },
];

interface Message {
  role: "user" | "assistant";
  content: string;
  message_id?: string;
  feedback?: "up" | "down";
  agents_involved?: string[];
  sources?: ChatResponse["sources"];
  streaming?: boolean;
  isError?: boolean;
  originalPrompt?: string;
}

interface ChatPageProps {
  user: StoredUser;
  onLogout: () => void;
}

const SESSIONS_STORAGE_PREFIX = "usiedu_sessions_list:";

function loadUserSessions(email: string): ChatSessionSummary[] {
  try {
    const raw = localStorage.getItem(SESSIONS_STORAGE_PREFIX + email);
    if (!raw) return [];
    return JSON.parse(raw) as ChatSessionSummary[];
  } catch {
    return [];
  }
}

function saveUserSessions(email: string, sessions: ChatSessionSummary[]) {
  try {
    localStorage.setItem(SESSIONS_STORAGE_PREFIX + email, JSON.stringify(sessions));
  } catch {
    // Ignora quota excessiva
  }
}

export default function ChatPage({ user, onLogout }: ChatPageProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    return (localStorage.getItem("usiedu_theme") as "dark" | "light") || "dark";
  });

  const [sessionId, setSessionId] = useState<string>(
    () => getSessionIdFor(user.email) ?? generateSessionId()
  );

  const [sessions, setSessions] = useState<ChatSessionSummary[]>(() =>
    loadUserSessions(user.email)
  );

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const onLogoutRef = useRef(onLogout);
  onLogoutRef.current = onLogout;

  // Sincroniza tema com documento
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("usiedu_theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  // Aborta stream ao desmontar
  useEffect(() => () => abortRef.current?.abort(), []);

  // Persiste sessão ativa
  useEffect(() => {
    storeSessionId(user.email, sessionId);
  }, [user.email, sessionId]);

  // Carrega histórico para a sessão selecionada
  useEffect(() => {
    let active = true;
    setRestoring(true);
    getChatHistory(sessionId)
      .then((history) => {
        if (active) {
          setMessages(history.messages.map((m) => ({ role: m.role, content: m.content })));
        }
      })
      .catch((err) => {
        if (err instanceof AuthError) {
          onLogoutRef.current();
          return;
        }
        if (active) setMessages([]);
      })
      .finally(() => {
        if (active) setRestoring(false);
      });
    return () => {
      active = false;
    };
  }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleNewConversation = () => {
    abortRef.current?.abort();
    const newId = generateSessionId();
    setSessionId(newId);
    setMessages([]);
    setInput("");
    setSidebarOpen(false);
  };

  const handleSelectSession = (id: string) => {
    if (id === sessionId) {
      setSidebarOpen(false);
      return;
    }
    abortRef.current?.abort();
    setSessionId(id);
    setInput("");
    setSidebarOpen(false);
  };

  const handleDeleteSession = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updated = sessions.filter((s) => s.id !== id);
    setSessions(updated);
    saveUserSessions(user.email, updated);
    if (id === sessionId) {
      handleNewConversation();
    }
  };

  const recordSessionActivity = (currentSessionId: string, firstUserMessage: string) => {
    setSessions((prev) => {
      const existing = prev.find((s) => s.id === currentSessionId);
      const title = existing?.title || firstUserMessage.slice(0, 38) + (firstUserMessage.length > 38 ? "..." : "");
      const updated: ChatSessionSummary = {
        id: currentSessionId,
        title,
        createdAt: existing?.createdAt || Date.now(),
        lastMessage: firstUserMessage,
      };
      const filtered = prev.filter((s) => s.id !== currentSessionId);
      const nextList = [updated, ...filtered].slice(0, 20);
      saveUserSessions(user.email, nextList);
      return nextList;
    });
  };

  const updateLastAssistant = (updater: (m: Message) => Message) => {
    setMessages((prev) => {
      const idx = prev.length - 1;
      if (idx < 0 || prev[idx].role !== "assistant") return prev;
      const next = [...prev];
      next[idx] = updater(next[idx]);
      return next;
    });
  };

  const handleCopyMessage = (index: number, text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    });
  };

  const handleSend = async (text: string) => {
    if (!text.trim() || loading) return;

    recordSessionActivity(sessionId, text);

    const userMsg: Message = { role: "user", content: text };
    const streamingMsg: Message = {
      role: "assistant",
      content: "",
      streaming: true,
      originalPrompt: text,
    };
    setMessages((prev) => [...prev, userMsg, streamingMsg]);
    setInput("");
    setLoading(true);

    let streamMessageId: string | undefined;
    let receivedTokens = false;
    let finalized = false;
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await sendChatStream(
        { session_id: sessionId, message: text },
        {
          onMeta: (meta) => {
            streamMessageId = meta.message_id;
          },
          onToken: (delta) => {
            receivedTokens = true;
            updateLastAssistant((m) => ({ ...m, content: m.content + delta }));
          },
          onFinal: (final) => {
            finalized = true;
            updateLastAssistant((m) => ({
              ...m,
              content: final.answer || m.content,
              message_id: streamMessageId,
              agents_involved: final.agents,
              sources: final.sources,
              streaming: false,
              isError: false,
            }));
          },
        },
        controller.signal
      );
      if (!finalized) {
        updateLastAssistant((m) => ({ ...m, streaming: false }));
      }
    } catch (err) {
      if (err instanceof AuthError) {
        onLogout();
        return;
      }
      if (err instanceof RateLimitError) {
        updateLastAssistant((m) => ({
          ...m,
          content: err.message,
          streaming: false,
          isError: true,
        }));
        return;
      }
      if (err instanceof DOMException && err.name === "AbortError") {
        updateLastAssistant((m) => ({ ...m, streaming: false }));
        return;
      }
      if (receivedTokens) {
        console.warn("Stream interrompido após tokens; mantendo conteúdo parcial:", err);
        updateLastAssistant((m) => ({ ...m, streaming: false, isError: true }));
        return;
      }
      console.warn("Streaming indisponível; usando fallback POST /chat:", err);
      try {
        const result = await sendChat({ session_id: sessionId, message: text });
        updateLastAssistant(() => ({
          role: "assistant",
          content: result.answer,
          message_id: result.message_id,
          agents_involved: result.agents_involved,
          sources: result.sources,
          isError: false,
        }));
      } catch (fallbackErr) {
        if (fallbackErr instanceof AuthError) {
          onLogout();
          return;
        }
        updateLastAssistant((m) => ({
          ...m,
          content:
            fallbackErr instanceof Error ? fallbackErr.message : "Erro ao processar mensagem",
          streaming: false,
          isError: true,
        }));
      }
    } finally {
      abortRef.current = null;
      setLoading(false);
    }
  };

  const handleFeedback = async (index: number, msg: Message, rating: "up" | "down") => {
    if (msg.feedback || !msg.message_id) return;
    try {
      await sendFeedback({ session_id: sessionId, message_id: msg.message_id, rating });
      setMessages((prev) =>
        prev.map((m, i) => (i === index ? { ...m, feedback: rating } : m))
      );
    } catch (err) {
      console.error("Falha ao enviar feedback:", err);
    }
  };

  return (
    <div className="chat-layout-wrapper">
      {/* Sidebar de Histórico de Conversas */}
      <aside
        className={`chat-sidebar ${sidebarOpen ? "is-open" : ""}`}
        aria-label="Histórico de conversas"
      >
        <div className="sidebar-header">
          <button
            className="sidebar-new-btn"
            onClick={handleNewConversation}
            aria-label="Nova conversa"
          >
            <span aria-hidden="true">➕</span> Nova conversa
          </button>
          <button
            className="sidebar-close-btn"
            onClick={() => setSidebarOpen(false)}
            aria-label="Fechar histórico"
          >
            ✕
          </button>
        </div>

        <div className="sidebar-sessions-list">
          <div className="sidebar-section-title">Conversas Recentes</div>
          {sessions.length === 0 ? (
            <div className="sidebar-empty-text">Nenhuma conversa salva ainda.</div>
          ) : (
            sessions.map((s) => (
              <div
                key={s.id}
                className={`sidebar-session-item ${s.id === sessionId ? "active" : ""}`}
                onClick={() => handleSelectSession(s.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") handleSelectSession(s.id);
                }}
              >
                <div className="session-item-content">
                  <span className="session-icon">💬</span>
                  <span className="session-title" title={s.title}>
                    {s.title}
                  </span>
                </div>
                <button
                  className="session-delete-btn"
                  onClick={(e) => handleDeleteSession(s.id, e)}
                  title="Excluir conversa"
                  aria-label={`Excluir conversa ${s.title}`}
                >
                  🗑️
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* Overlay mobile */}
      {sidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Área Principal de Chat */}
      <div className="chat-main-container">
        <header className="header">
          <div className="header-left">
            <button
              className="sidebar-toggle-btn"
              onClick={() => setSidebarOpen((prev) => !prev)}
              title="Histórico de conversas"
              aria-label="Abrir histórico de conversas"
            >
              ☰
            </button>
            <h1>
              <span className="header-logo-badge">U</span> UsiEdu — Chat
            </h1>
          </div>

          <div className="header-right">
            <button
              className="theme-toggle-btn"
              onClick={toggleTheme}
              title={`Alternar para tema ${theme === "dark" ? "claro" : "escuro"}`}
              aria-label={`Alternar para tema ${theme === "dark" ? "claro" : "escuro"}`}
            >
              {theme === "dark" ? "☀️" : "🌙"}
            </button>

            <Link to="/insights" className="insights-back-link">
              Satisfação
            </Link>

            <span className="header-user">
              <span className="user-avatar">{user.display_name.charAt(0)}</span>
              <span className="user-info-text">
                <strong>{user.display_name}</strong>
                <small className="user-profile-tag">{user.profile}</small>
              </span>
            </span>

            <button
              className="new-chat-btn"
              onClick={handleNewConversation}
              disabled={loading || restoring}
              aria-label="Iniciar nova conversa"
            >
              Nova conversa
            </button>
            <button className="logout-btn" onClick={onLogout}>
              Sair
            </button>
          </div>
        </header>

        <main className="chat-page">
          {/* Região ao vivo para anúncios de acessibilidade */}
          <div className="sr-only" aria-live="polite">
            {loading ? "O assistente está gerando uma resposta..." : ""}
          </div>

          {restoring && (
            <div className="loading-state-box">
              <span className="loading-spinner" aria-hidden="true" />
              <span>Carregando histórico...</span>
            </div>
          )}

          {messages.length === 0 && !restoring && (
            <div className="empty-state">
              <div className="empty-icon-glow">🎓</div>
              <h2>Bem-vindo ao UsiEdu!</h2>
              <p>
                Selecione um cenário abaixo ou digite sua pergunta sobre notas, boletos, ou
                políticas institucionais.
              </p>
            </div>
          )}

          {messages.length > 0 && (
            <div className="messages" role="log" aria-label="Histórico de mensagens">
              {messages.map((msg, i) => (
                <div key={i} className="message-wrapper">
                  <div className={`message ${msg.role} ${msg.isError ? "has-error" : ""}`}>
                    <div className="message-header-bar">
                      <span className="message-sender-name">
                        {msg.role === "assistant" ? "🤖 UsiEdu Assistente" : `👤 ${user.display_name}`}
                      </span>
                      <button
                        type="button"
                        className="message-action-btn copy"
                        onClick={() => handleCopyMessage(i, msg.content)}
                        title="Copiar mensagem"
                        aria-label="Copiar mensagem para área de transferência"
                      >
                        {copiedIndex === i ? "✓ Copiado!" : "Copiar"}
                      </button>
                    </div>

                    <div className="message-body">
                      {msg.role === "assistant" ? (
                        <>
                          <Markdown content={msg.content} />
                          {msg.streaming && (
                            <span className="streaming-cursor" aria-hidden="true" />
                          )}
                        </>
                      ) : (
                        <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>
                      )}
                    </div>

                    {msg.role === "assistant" && msg.agents_involved && (
                      <MessageCard
                        agents_involved={msg.agents_involved}
                        sources={msg.sources || []}
                      />
                    )}

                    {msg.role === "assistant" && msg.isError && msg.originalPrompt && (
                      <div className="message-retry-bar">
                        <span className="retry-warning">⚠️ Resposta incompleta ou erro de rede.</span>
                        <button
                          type="button"
                          className="retry-btn"
                          onClick={() => handleSend(msg.originalPrompt!)}
                          disabled={loading}
                        >
                          🔄 Tentar novamente
                        </button>
                      </div>
                    )}

                    {msg.role === "assistant" && msg.message_id && (
                      <div className="feedback-row">
                        <span className="feedback-label">A resposta ajudou?</span>
                        <button
                          className={`feedback-btn up${msg.feedback === "up" ? " active" : ""}`}
                          disabled={!!msg.feedback}
                          onClick={() => handleFeedback(i, msg, "up")}
                          title="Resposta útil"
                          aria-label="Resposta útil"
                        >
                          👍
                        </button>
                        <button
                          className={`feedback-btn down${msg.feedback === "down" ? " active" : ""}`}
                          disabled={!!msg.feedback}
                          onClick={() => handleFeedback(i, msg, "down")}
                          title="Resposta não útil"
                          aria-label="Resposta não útil"
                        >
                          👎
                        </button>
                        {msg.feedback && (
                          <span className="feedback-thanks">Obrigado pelo feedback!</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="loading" role="status">
                  <span className="typing-dots">
                    <span />
                    <span />
                    <span />
                  </span>
                  Processando
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}

          <div className="scenario-buttons" aria-label="Sugestões de perguntas rápidas">
            {SCENARIOS.filter((s) => {
              if (s.intent === "institucional" && user.profile !== "staff") return false;
              return true;
            }).map((s) => (
              <button
                key={s.label}
                className="scenario-btn"
                onClick={() => handleSend(s.message)}
                disabled={loading}
              >
                <span className="scenario-icon" aria-hidden="true">
                  {s.icon}
                </span>{" "}
                {s.label}
              </button>
            ))}
          </div>

          <form
            className="input-area"
            onSubmit={(e) => {
              e.preventDefault();
              handleSend(input);
            }}
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Digite sua pergunta (ex: notas, boletos, prazos de matrícula)..."
              disabled={loading}
              aria-label="Campo de mensagem para o assistente"
            />
            <button
              type="submit"
              className="send-btn"
              disabled={loading || !input.trim()}
              aria-label="Enviar mensagem"
            >
              ➤
            </button>
          </form>
        </main>
      </div>
    </div>
  );
}