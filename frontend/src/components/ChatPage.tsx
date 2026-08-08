import { useState, useRef, useEffect } from "react";
import type { ChatResponse, LoginResponse } from "../types";
import { sendChat, generateSessionId, sendFeedback } from "../api";
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
}

interface ChatPageProps {
  user: LoginResponse;
  onLogout: () => void;
}

export default function ChatPage({ user, onLogout }: ChatPageProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(generateSessionId);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const result = await sendChat({ session_id: sessionId, message: text });
      const assistantMsg: Message = {
        role: "assistant",
        content: result.answer,
        message_id: result.message_id,
        agents_involved: result.agents_involved,
        sources: result.sources,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg: Message = {
        role: "assistant",
        content: err instanceof Error ? err.message : "Erro ao processar mensagem",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
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
          <span className="header-user">{user.display_name} ({user.profile})</span>
          <button className="logout-btn" onClick={onLogout}>Sair</button>
        </div>
      </header>

      <div className="chat-page">
        {messages.length === 0 && (
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
                  <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>
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