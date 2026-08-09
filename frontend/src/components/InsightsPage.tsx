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

  return (
    <>
      <header className="header">
        <h1>UsiEdu — Satisfação</h1>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link to="/chat" className="insights-back-link">
            ← Voltar ao chat
          </Link>
          <span className="header-user">
            {user.display_name} ({user.profile})
          </span>
          <button className="logout-btn" onClick={onLogout}>
            Sair
          </button>
        </div>
      </header>

      <div className="insights-page">
        {loading && <div className="loading">Carregando métricas</div>}
        {error && <div className="insights-error">{error}</div>}

        {!loading && !error && stats && (
          <>
            <div className="insights-cards">
              <div className="insights-card">
                <div className="insights-card-value">{stats.total}</div>
                <div className="insights-card-label">Total de avaliações</div>
              </div>
              <div className="insights-card up">
                <div className="insights-card-value">👍 {stats.up}</div>
                <div className="insights-card-label">Respostas aprovadas</div>
              </div>
              <div className="insights-card down">
                <div className="insights-card-value">👎 {stats.down}</div>
                <div className="insights-card-label">Respostas reprovadas</div>
              </div>
              <div className="insights-card satisfaction">
                <div className="insights-card-value">
                  {satisfacaoPct === null ? "—" : `${satisfacaoPct}%`}
                </div>
                <div className="insights-card-label">Taxa de satisfação</div>
              </div>
            </div>

            <h2 className="insights-section-title">Últimos feedbacks</h2>
            {recent.length === 0 ? (
              <div className="empty-state insights-empty">
                <div className="icon">💬</div>
                <h2>Ainda não há feedback registrado</h2>
                <p>Avalie respostas no chat com 👍/👎 para vê-las aqui.</p>
              </div>
            ) : (
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
                  {recent.map((item) => (
                    <tr key={`${item.message_ref}-${item.created_at}`}>
                      <td className="insights-cell-date">{formatarData(item.created_at)}</td>
                      <td>{PERFIL_LABEL[item.profile] ?? item.profile}</td>
                      <td>{item.rating === "up" ? "👍" : "👎"}</td>
                      <td className="insights-cell-comment">{item.comment ?? "—"}</td>
                      <td>
                        <code className="insights-ref">{item.message_ref}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
      </div>
    </>
  );
}
