import { useState } from "react";
import type { Source } from "../types";

interface MessageCardProps {
  agents_involved: string[];
  sources: Source[];
}

export default function MessageCard({ agents_involved, sources }: MessageCardProps) {
  const [expandedAgent, setExpandedAgent] = useState(false);
  const [expandedSource, setExpandedSource] = useState<string | null>(null);

  return (
    <div className="info-cards">
      {agents_involved.length > 0 && (
        <div className="info-card agent" onClick={() => setExpandedAgent(!expandedAgent)}>
          <div className="card-title">Agentes</div>
          <div className="card-subtitle">{agents_involved.join(", ")}</div>
          {expandedAgent && (
            <div className="card-expanded">
              {agents_involved.map((a) => (
                <div key={a}>• {a}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {sources.length > 0 && (
        <div className="info-card source" onClick={() => setExpandedSource(expandedSource === "all" ? null : "all")}>
          <div className="card-title">Fontes</div>
          <div className="card-subtitle">{sources.length} documento(s)</div>
          {expandedSource === "all" && (
            <div className="card-expanded">
              {sources.map((s, i) => (
                <div key={i} style={{ marginBottom: 8 }}>
                  <strong>{s.document}</strong>
                  {s.section && <div>Seção: {s.section}</div>}
                  <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: 2 }}>
                    {s.excerpt.slice(0, 120)}...
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}