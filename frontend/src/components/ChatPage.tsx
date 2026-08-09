import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import type { ChatResponse, StoredUser } from "../types";
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
  { label: "Notas e faltas", message: "Quero ver minhas notas e faltas", intent: "academico" },
  { label: "Boleto e renegociação", message: "Qual o valor do meu boleto? Pode simular renegociação?", intent: "financeiro" },
  { label: "Pergunta composta", message: "Quero ver minhas notas e o valor do boleto", intent: "composta" },
  { label: "Política institucional", message: "Qual a política de uso dos laboratórios?", intent: "institucional" },
];

interface Message {
  role: "user" | "assistant";
  content: string;
  message_id?: string;
  feedback?: "up" | "down";
  agents_involved?: string[];
  sources?: ChatResponse["sources"];
  streaming?: boolean;
}

interface ChatPageProps {
  user: StoredUser;
  onLogout: () => void;
}

export default function ChatPage({ user, onLogout }: ChatPageProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [sessionId, setSessionId] = useState<string>(
    () => getSessionIdFor(user.email) ?? generateSessionId()
  );
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Aborta o stream pendente ao desmontar (navegação para outra rota) (T7.3)
  useEffect(() => () => abortRef.current?.abort(), []);

  // Persiste a sessão ativa por usuário (T7.4 / RF2-04)
  useEffect(() => {
    storeSessionId(user.email, sessionId);
  }, [user.email, sessionId]);

  // Restaura o histórico na montagem (T7.4 / RF2-05). Agentes/fontes são
  // omitidos no histórico — apenas o texto é devolvido pelo backend.
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
          onLogout();
          return;
        }
        // 404 (sessão nova) ou sessão indisponível: conversa vazia
      })
      .finally(() => {
        if (active) setRestoring(false);
      });
    return () => {
      active = false;
    };
    // Roda apenas na montagem; "Nova conversa" troca sessionId e limpa localmente
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleNewConversation = () => {
    abortRef.current?.abort();
    setSessionId(generateSessionId());
    setMessages([]);
    setInput("");
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

  const handleSend = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: Message = { role: "user", content: text };
    const streamingMsg: Message = { role: "assistant", content: "", streaming: true };
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
              // Reconcilia com o texto oficial (a consolidação pode adicionar
              // sufixos que não passaram pelo stream de tokens)
              content: final.answer || m.content,
              message_id: streamMessageId,
              agents_involved: final.agents,
              sources: final.sources,
              streaming: false,
            }));
          },
        },
        controller.signal
      );
      // Stream terminou sem evento final: libera o cursor de digitação
      if (!finalized) {
        updateLastAssistant((m) => ({ ...m, streaming: false }));
      }
    } catch (err) {
      if (err instanceof AuthError) {
        onLogout();
        return;
      }
      if (err instanceof RateLimitError) {
        // 429: exibe a mensagem amigável sem fallback POST (T9.1)
        updateLastAssistant((m) => ({ ...m, content: err.message, streaming: false }));
        return;
      }
      if (err instanceof DOMException && err.name === "AbortError") {
        updateLastAssistant((m) => ({ ...m, streaming: false }));
        return;
      }
      if (receivedTokens) {
        // Já há conteúdo parcial do stream; reenviar duplicaria a mensagem
        // na sessão — mantém o que chegou.
        console.warn("Stream interrompido após tokens; mantendo conteúdo parcial:", err);
        updateLastAssistant((m) => ({ ...m, streaming: false }));
        return;
      }
      // Fallback obrigatório (T7.3): erro de rede/parse usa o POST tradicional
      console.warn("Streaming indisponível; usando fallback POST /chat:", err);
      try {
        const result = await sendChat({ session_id: sessionId, message: text });
        updateLastAssistant(() => ({
          role: "assistant",
          content: result.answer,
          message_id: result.message_id,
          agents_involved: result.agents_involved,
          sources: result.sources,
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
    <>
      <header className="header">
        <h1>UsiEdu — Chat</h1>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link to="/insights" className="insights-back-link">
            Satisfação
          </Link>
          <span className="header-user">{user.display_name} ({user.profile})</span>
          <button
            className="new-chat-btn"
            onClick={handleNewConversation}
            disabled={loading || restoring}
            aria-label="Iniciar nova conversa"
          >
            Nova conversa
          </button>
          <button className="logout-btn" onClick={onLogout}>Sair</button>
        </div>
      </header>

      <div className="chat-page">
        {restoring && <div className="loading">Carregando histórico</div>}

        {messages.length === 0 && !restoring && (
          <div className="empty-state">
            <div className="icon">🎓</div>
            <h2>Bem-vindo ao UsiEdu!</h2>
            <p>Selecione um cenário abaixo ou digite sua pergunta sobre notas, boletos, ou políticas institucionais.</p>
          </div>
        )}

        {messages.length > 0 && (
          <div className="messages">
            {messages.map((msg, i) => (
              <div key={i}>
                <div className={`message ${msg.role}`}>
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
                  {msg.role === "assistant" && msg.agents_involved && (
                    <MessageCard
                      agents_involved={msg.agents_involved}
                      sources={msg.sources || []}
                    />
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
            {loading && <div className="loading">Processando</div>}
            <div ref={messagesEndRef} />
          </div>
        )}

        <div className="scenario-buttons">
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
            placeholder="Digite sua mensagem..."
            disabled={loading}
          />
          <button type="submit" className="send-btn" disabled={loading || !input.trim()}>
            ➤
          </button>
        </form>
      </div>
    </>
  );
}