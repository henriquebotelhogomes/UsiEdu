import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { FeedbackRecentItem, FeedbackStats, StoredUser } from "../types";
import { AuthError, getFeedbackRecent, getFeedbackStats } from "../api";

interface InsightsPageProps {
  user: StoredUser;
  onLogout: () => void;
}

const PERFIL_LABEL: Record<string, string> = {
  student: "Estudante",
  staff: "Colaborador",
};

function formatarData(iso: string): string {
  const data = new Date(iso);
  return Number.isNaN(data.getTime()) ? iso : data.toLocaleString("pt-BR");
}

export default function InsightsPage({ user, onLogout }: InsightsPageProps) {
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [recent, setRecent] = useState<FeedbackRecentItem[]>([]);
  const [filterRating, setFilterRating] = useState<"all" | "up" | "down">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([getFeedbackStats(), getFeedbackRecent(20)])
      .then(([s, r]) => {
        if (!active) return;
        setStats(s);
        setRecent(r.items);
      })
      .catch((err: unknown) => {
        if (!active) return;
        if (err instanceof AuthError) {
          onLogout();
          return;
        }
        setError(err instanceof Error ? err.message : "Erro ao carregar dados");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [onLogout]);

  const satisfacaoPct = stats && stats.total > 0 ? Math.round(stats.satisfaction * 100) : null;

  const filteredRecent = recent.filter((item) => {
    if (filterRating === "all") return true;
    return item.rating === filterRating;
  });

  return (
    <>
      <header className="header">
        <h1>UsiEdu — Satisfação</h1>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link to="/chat" className="insights-back-link" aria-label="Voltar ao chat">
            ← Voltar ao chat
          </Link>
          <span className="header-user">
            {user.display_name} ({user.profile})
          </span>
          <button className="logout-btn" onClick={onLogout} aria-label="Sair da conta">
            Sair
          </button>
        </div>
      </header>

      <div className="insights-page">
        {loading && <div className="loading" role="status">Carregando métricas</div>}
        {error && <div className="insights-error" role="alert">{error}</div>}

        {!loading && !error && stats && (
          <>
            <div className="insights-cards">
              <div className="insights-card total">
                <div className="insights-card-header">
                  <span className="insights-card-icon">📊</span>
                  <span className="insights-card-label">Total de avaliações</span>
                </div>
                <div className="insights-card-value">{stats.total}</div>
              </div>

              <div className="insights-card up">
                <div className="insights-card-header">
                  <span className="insights-card-icon">👍</span>
                  <span className="insights-card-label">Respostas aprovadas</span>
                </div>
                <div className="insights-card-value">{stats.up}</div>
              </div>

              <div className="insights-card down">
                <div className="insights-card-header">
                  <span className="insights-card-icon">👎</span>
                  <span className="insights-card-label">Respostas reprovadas</span>
                </div>
                <div className="insights-card-value">{stats.down}</div>
              </div>

              <div className="insights-card satisfaction">
                <div className="insights-card-header">
                  <span className="insights-card-icon">⭐</span>
                  <span className="insights-card-label">Taxa de satisfação</span>
                </div>
                <div className="insights-card-value">
                  {satisfacaoPct === null ? "—" : `${satisfacaoPct}%`}
                </div>
                {satisfacaoPct !== null && (
                  <div className="csat-progress-bar" role="progressbar" aria-valuenow={satisfacaoPct} aria-valuemin={0} aria-valuemax={100}>
                    <div className="csat-progress-fill" style={{ width: `${satisfacaoPct}%` }} />
                  </div>
                )}
              </div>
            </div>

            <div className="rag-quality-banner" style={{ margin: "24px 0", padding: "16px 20px", background: "rgba(99, 102, 241, 0.08)", border: "1px solid rgba(99, 102, 241, 0.2)", borderRadius: 12 }}>
              <h3 style={{ margin: "0 0 8px 0", fontSize: "1rem", color: "var(--color-primary, #4f46e5)", display: "flex", alignItems: "center", gap: 8 }}>
                <span>🛡️</span> Salvaguardas &amp; Qualidade Contínua (CRAG + Ragas)
              </h3>
              <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--color-text-muted, #64748b)", lineHeight: 1.5 }}>
                • <strong>CRAG Grader:</strong> Candidatos com pontuação de relevância abaixo de 0.35 são descartados automaticamente.<br/>
                • <strong>Contextual Retrieval:</strong> Chunks ancorados no documento pai reduzem erros de recuperação em até 49%.<br/>
                • <strong>Semantic Cache Warmup:</strong> Catálogo institucional pré-carregado responde perguntas frequentes em &lt;15ms.<br/>
                • <strong>Dataset Sintético:</strong> 50 casos de teste gerados automaticamente cobrindo perguntas diretas, raciocínio e fora de escopo.
              </p>
            </div>

            <div className="insights-section-header">
              <h2 className="insights-section-title">Últimos feedbacks</h2>
              <div className="insights-filter-chips" role="group" aria-label="Filtrar por avaliação">
                <button
                  className={`filter-chip ${filterRating === "all" ? "active" : ""}`}
                  onClick={() => setFilterRating("all")}
                  aria-pressed={filterRating === "all"}
                >
                  Todos ({recent.length})
                </button>
                <button
                  className={`filter-chip ${filterRating === "up" ? "active" : ""}`}
                  onClick={() => setFilterRating("up")}
                  aria-pressed={filterRating === "up"}
                >
                  👍 Úteis ({recent.filter((r) => r.rating === "up").length})
                </button>
                <button
                  className={`filter-chip ${filterRating === "down" ? "active" : ""}`}
                  onClick={() => setFilterRating("down")}
                  aria-pressed={filterRating === "down"}
                >
                  👎 Ajustar ({recent.filter((r) => r.rating === "down").length})
                </button>
              </div>
            </div>

            {filteredRecent.length === 0 ? (
              <div className="empty-state insights-empty">
                <div className="icon">💬</div>
                <h2>
                  {recent.length === 0
                    ? "Ainda não há feedback registrado"
                    : "Nenhum feedback neste filtro"}
                </h2>
                <p>
                  {recent.length === 0
                    ? "Avalie respostas no chat com 👍/👎 para vê-las aqui."
                    : "Não há registros para a categoria selecionada."}
                </p>
              </div>
            ) : (
              <div className="insights-table-container">
                <table className="insights-table">
                  <thead>
                    <tr>
                      <th>Data</th>
                      <th>Perfil</th>
                      <th>Avaliação</th>
                      <th>Comentário</th>
                      <th>Ref.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRecent.map((item) => (
                      <tr key={`${item.message_ref}-${item.created_at}`}>
                        <td className="insights-cell-date">{formatarData(item.created_at)}</td>
                        <td>
                          <span className={`profile-badge ${item.profile}`}>
                            {PERFIL_LABEL[item.profile] ?? item.profile}
                          </span>
                        </td>
                        <td>
                          <span className={`rating-pill ${item.rating}`}>
                            {item.rating === "up" ? "👍 Positivo" : "👎 Negativo"}
                          </span>
                        </td>
                        <td className="insights-cell-comment">{item.comment ?? "—"}</td>
                        <td>
                          <code className="insights-ref">{item.message_ref}</code>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}

