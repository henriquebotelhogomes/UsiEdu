import { useState } from "react";
import type { Source } from "../types";

interface MessageCardProps {
  agents_involved: string[];
  sources: Source[];
}

function getAgentMeta(agentName: string) {
  const lower = agentName.toLowerCase();
  if (lower.includes("acad")) {
    return { icon: "🎓", label: "Acadêmico", badgeClass: "badge-academic" };
  }
  if (lower.includes("finan")) {
    return { icon: "💳", label: "Financeiro", badgeClass: "badge-financial" };
  }
  if (lower.includes("doc")) {
    return { icon: "📑", label: "Documental", badgeClass: "badge-documental" };
  }
  if (lower.includes("sup") || lower.includes("cons") || lower.includes("comp")) {
    return { icon: "🧠", label: "Multi-Agente", badgeClass: "badge-multi" };
  }
  return { icon: "🤖", label: agentName, badgeClass: "badge-default" };
}

export default function MessageCard({ agents_involved, sources }: MessageCardProps) {
  const [expandedAgent, setExpandedAgent] = useState(false);
  const [expandedSource, setExpandedSource] = useState<string | null>(null);

  const toggleAgents = () => setExpandedAgent((prev) => !prev);
  const toggleSources = () => setExpandedSource((prev) => (prev === "all" ? null : "all"));

  return (
    <div className="info-cards" role="region" aria-label="Informações da resposta">
      {agents_involved.length > 0 && (
        <div
          className={`info-card agent ${expandedAgent ? "is-expanded" : ""}`}
          onClick={toggleAgents}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              toggleAgents();
            }
          }}
          role="button"
          tabIndex={0}
          aria-expanded={expandedAgent}
          aria-label={`Agentes participantes: ${agents_involved.join(", ")}. Clique para expandir detalhes.`}
        >
          <div className="card-header-row">
            <div className="card-title">
              <span className="card-title-icon">🤖</span> Agentes
            </div>
            <div className="agent-badges-row">
              {agents_involved.map((a) => {
                const meta = getAgentMeta(a);
                return (
                  <span key={a} className={`agent-pill ${meta.badgeClass}`}>
                    <span aria-hidden="true">{meta.icon}</span> {meta.label}
                  </span>
                );
              })}
            </div>
          </div>
          <div className="card-subtitle">{agents_involved.join(", ")}</div>
          {expandedAgent && (
            <div className="card-expanded" role="region" aria-label="Detalhes dos agentes">
              {agents_involved.map((a) => {
                const meta = getAgentMeta(a);
                return (
                  <div key={a} className="agent-detail-item">
                    <span className="agent-detail-bullet">•</span>
                    <strong>{a}</strong>
                    <span className="agent-detail-hint">
                      ({meta.label} — roteamento e execução)
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {sources.length > 0 && (
        <div
          className={`info-card source ${expandedSource === "all" ? "is-expanded" : ""}`}
          onClick={toggleSources}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              toggleSources();
            }
          }}
          role="button"
          tabIndex={0}
          aria-expanded={expandedSource === "all"}
          aria-label={`Fontes consultadas: ${sources.length} documentos. Clique para ver trechos e links oficiais.`}
        >
          <div className="card-header-row">
            <div className="card-title">
              <span className="card-title-icon">📚</span> Fontes
            </div>
            <span className="source-count-badge">
              {sources.length} {sources.length === 1 ? "documento" : "documentos"}
            </span>
          </div>
          <div className="card-subtitle">{sources.length} documento(s)</div>
          {expandedSource === "all" && (
            <div className="card-expanded" role="region" aria-label="Lista de fontes consultadas">
              {sources.map((s, i) => (
                <div key={i} className="fonte-item">
                  <div className="fonte-header">
                    <span className="fonte-icon">📄</span>
                    <strong className="fonte-doc-name">{s.document}</strong>
                  </div>
                  {s.section && (
                    <div className="fonte-section">
                      <span className="fonte-section-tag">Seção:</span> {s.section}
                    </div>
                  )}
                  <div className="fonte-trecho" title={s.excerpt}>
                    &ldquo;{s.excerpt.slice(0, 140)}...&rdquo;
                  </div>
                  {s.url && (
                    <a
                      className="fonte-link"
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Abrir documento oficial ${s.document} em nova aba`}
                      onClick={(e) => e.stopPropagation()}
                    >
                      Ver documento oficial ↗
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}