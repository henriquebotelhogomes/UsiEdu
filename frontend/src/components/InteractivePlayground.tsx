import { useState } from "react";

interface Scenario {
  id: string;
  title: string;
  perfil: "student" | "staff";
  perfilLabel: string;
  icon: string;
  pergunta: string;
  intent: "academico" | "financeiro" | "institucional" | "composta" | "fora_de_escopo";
  agentes: string[];
  cragScore: string;
  fontePrincipal: {
    nome: string;
    url: string;
    trecho: string;
  };
  respostaPreview: string;
}

const SCENARIOS: Scenario[] = [
  {
    id: "afastamento",
    title: "Afastamento Servidor (DGP)",
    perfil: "staff",
    perfilLabel: "Servidor / Staff",
    icon: "🏛️",
    pergunta: "O que é Afastamento para Participação em Ação de Desenvolvimento?",
    intent: "institucional",
    agentes: ["Agente Documental"],
    cragScore: "0.9999 (Top-1 Reranked)",
    fontePrincipal: {
      nome: "DGP — Licença e Afastamentos",
      url: "https://dgp.unb.br/afastamentos",
      trecho:
        "É o afastamento concedido ao servidor para participar em ações de desenvolvimento, capacitação ou treinamento regularmente instituído, no interesse da Administração...",
    },
    respostaPreview:
      'O Afastamento para Participação em Ação de Desenvolvimento é concedido ao servidor para atividades de capacitação no interesse da Administração, "desde que a participação não possa ocorrer simultaneamente com o exercício do cargo" (Fonte: DGP/UnB).',
  },
  {
    id: "composta",
    title: "Consulta Composta (Notas + Boleto)",
    perfil: "student",
    perfilLabel: "Estudante",
    icon: "🎓",
    pergunta: "Quero ver minhas notas de Cálculo e o valor do meu boleto em aberto.",
    intent: "composta",
    agentes: ["Agente Acadêmico", "Agente Financeiro", "Nó de Consolidação"],
    cragScore: "Execução Paralela de Tools",
    fontePrincipal: {
      nome: "Sistema Acadêmico + Financeiro Integrado",
      url: "https://sigaa.unb.br",
      trecho: "Tools mockadas executadas: get_notas(aluno_id='ana-123') e get_boletos(aluno_id='ana-123')",
    },
    respostaPreview:
      "Em Cálculo 1 sua nota é 5.8 (6 faltas). Seu boleto bol-001 no valor de R$ 890,00 venceu em 10/07/2026. A instituição permite parcelamento em até 6x com 10% de desconto.",
  },
  {
    id: "calendario",
    title: "Calendário e Trancamento",
    perfil: "student",
    perfilLabel: "Estudante",
    icon: "📅",
    pergunta: "Quais os requisitos e prazos para trancamento geral de matrícula?",
    intent: "academico",
    agentes: ["Agente Acadêmico"],
    cragScore: "0.9840 (Top-1 Reranked)",
    fontePrincipal: {
      nome: "Regimento Geral da UnB",
      url: "https://unb.br/images/Documentos/Estatuto_e_Regimento_Geral_UnB.pdf",
      trecho: "Art. 120 — O trancamento de matrícula geral é permitido a partir do segundo período letivo por até 4 períodos...",
    },
    respostaPreview:
      "O trancamento geral de matrícula pode ser solicitado via SIGAA a partir do 2º período letivo regular, limitado ao máximo de 4 períodos, respeitados os prazos do calendário acadêmico oficial.",
  },
  {
    id: "fora_escopo",
    title: "Guardrail Anti-Alucinação",
    perfil: "student",
    perfilLabel: "Estudante",
    icon: "🛑",
    pergunta: "Qual a previsão do tempo para amanhã em Brasília?",
    intent: "fora_de_escopo",
    agentes: ["Nó de Redirecionamento / Out of Scope"],
    cragScore: "Filtro de Guardrail Direto (Custo 0 de RAG)",
    fontePrincipal: {
      nome: "Guardrail de Entrada & Escopo Institucional",
      url: "#",
      trecho: "Pergunta classificada com intenção fora_de_escopo com 100% de precisão sem disparar busca vetorial.",
    },
    respostaPreview:
      "Essa pergunta está fora do meu escopo de atendimento universitário. Posso te ajudar com dúvidas sobre calendário, matrículas, notas, faltas, boletos e normas institucionais.",
  },
];

export function InteractivePlayground() {
  const [activeScenario, setActiveScenario] = useState<Scenario>(SCENARIOS[0]);
  const [activeTab, setActiveTab] = useState<number>(0);
  const [requestsPerMonth, setRequestsPerMonth] = useState<number>(25000);

  // Cálculos de FinOps
  const cacheHitRate = 0.42; // 42% das perguntas repetidas caem no cache
  const cachedRequests = Math.round(requestsPerMonth * cacheHitRate);
  const costPer1kLLM = 0.015; // USD
  const savedDollars = ((cachedRequests / 1000) * costPer1kLLM * 12).toFixed(2);
  const latencySavedHours = Math.round((cachedRequests * 2.8) / 3600);

  return (
    <div className="interactive-playground">
      {/* 1. Simulador de Trajetória do Grafo */}
      <div className="playground-card">
        <div className="playground-header">
          <span className="playground-pill">Simulador Interativo ao Vivo</span>
          <h3>Experimente o Roteamento do Grafo Multi-Agente</h3>
          <p>
            Selecione uma pergunta real para visualizar o fluxo de execução do supervisor, o isolamento RBAC e as fontes recuperadas.
          </p>
        </div>

        {/* Botões de Cenário */}
        <div className="scenario-pills" role="tablist">
          {SCENARIOS.map((sc) => (
            <button
              key={sc.id}
              className={`scenario-btn ${activeScenario.id === sc.id ? "active" : ""}`}
              onClick={() => setActiveScenario(sc)}
              type="button"
            >
              <span>{sc.icon}</span> {sc.title}
            </button>
          ))}
        </div>

        {/* Painel de Visualização do Fluxo */}
        <div className="simulator-canvas">
          <div className="simulator-input-box">
            <div className="simulator-meta">
              <span className={`badge-profile ${activeScenario.perfil}`}>
                Perfil: {activeScenario.perfilLabel}
              </span>
              <span className="badge-intent">
                Supervisor Intent: <strong>{activeScenario.intent}</strong>
              </span>
            </div>
            <div className="simulator-query">
              <strong>Pergunta:</strong> &ldquo;{activeScenario.pergunta}&rdquo;
            </div>
          </div>

          <div className="flow-visualizer">
            <div className="flow-step">
              <div className="step-badge">1. Supervisor</div>
              <div className="step-content">
                Classifica intenção estruturada e valida RBAC do perfil.
              </div>
            </div>
            <div className="flow-arrow">→</div>
            <div className="flow-step highlight">
              <div className="step-badge">2. Especialistas Ativados</div>
              <div className="step-tags">
                {activeScenario.agentes.map((ag) => (
                  <span key={ag} className="agent-tag">
                    {ag}
                  </span>
                ))}
              </div>
            </div>
            <div className="flow-arrow">→</div>
            <div className="flow-step">
              <div className="step-badge">3. RAG / CRAG Grader</div>
              <div className="step-content">
                <strong>Score:</strong> {activeScenario.cragScore}
              </div>
            </div>
          </div>

          {/* Fonte e Resposta */}
          <div className="simulator-results-grid">
            <div className="result-source-box">
              <h5>📄 Documento Oficial Recuperado</h5>
              <div className="source-title">{activeScenario.fontePrincipal.nome}</div>
              {activeScenario.fontePrincipal.url !== "#" && (
                <a
                  href={activeScenario.fontePrincipal.url}
                  target="_blank"
                  rel="noreferrer"
                  className="source-url"
                >
                  {activeScenario.fontePrincipal.url} ↗
                </a>
              )}
              <p className="source-excerpt">
                &ldquo;{activeScenario.fontePrincipal.trecho}&rdquo;
              </p>
            </div>

            <div className="result-answer-box">
              <h5>💬 Resposta Consolidada do Assistente</h5>
              <p className="answer-text">{activeScenario.respostaPreview}</p>
              <div className="answer-footer">
                <span>✅ Grounded com citação estrita</span>
                <span>🛡️ Sem alucinações</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Explorador dos 4 Estágios do Pipeline RAG */}
      <div className="playground-card" style={{ marginTop: "28px" }}>
        <div className="playground-header">
          <span className="playground-pill teal">Engenharia RAG 4-Stage</span>
          <h3>Como o UsiEdu Garante 99% de Precisão na Recuperação</h3>
          <p>Clique em cada estágio para entender a pipeline de fatiamento e re-ranking.</p>
        </div>

        <div className="pipeline-tabs">
          {[
            { id: 0, label: "1. Parent-Document & Self-Query" },
            { id: 1, label: "2. Busca Híbrida & RRF" },
            { id: 2, label: "3. Cross-Encoder & CRAG Grader" },
            { id: 3, label: "4. Lost in the Middle & FinOps" },
          ].map((tab) => (
            <button
              key={tab.id}
              className={`pipeline-tab-btn ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="pipeline-tab-content">
          {activeTab === 0 && (
            <div className="tab-pane">
              <h4>🧩 Estágio 1: Hierarchical Parent-Document &amp; Self-Querying</h4>
              <p>
                Os documentos são divididos em unidades jurídicas e parágrafos sem quebra de palavras. Cada chunk filho carrega um cabeçalho com o contexto pai (instituição, documento e seção), reduzindo falhas de recuperação em até 49%.
              </p>
              <div className="code-example">
                <code>
                  [Parent: DGP - Licença e Afastamentos | UnB | Seção: Afastamento para Desenvolvimento]<br />
                  &quot;É o afastamento concedido ao servidor para participar em ações de desenvolvimento...&quot;
                </code>
              </div>
            </div>
          )}

          {activeTab === 1 && (
            <div className="tab-pane">
              <h4>⚡ Estágio 2: Busca Híbrida Vetorial + BM25 fundida por RRF</h4>
              <p>
                Combina busca vetorial densa no <strong>Qdrant</strong> com busca léxica exata no <strong>BM25</strong>. Os resultados são ponderados pelo algoritmo <em>Reciprocal Rank Fusion (RRF com k=60)</em>, garantindo que termos exatos (como números de leis e artigos) nunca sejam ignorados.
              </p>
              <div className="code-example">
                <code>
                  RRF_Score(d) = 1/(60 + Rank_Qdrant(d)) + 1/(60 + Rank_BM25(d)) → Top-20 unificado
                </code>
              </div>
            </div>
          )}

          {activeTab === 2 && (
            <div className="tab-pane">
              <h4>🎯 Estágio 3: Cross-Encoder Re-ranker &amp; Corrective RAG (CRAG)</h4>
              <p>
                O modelo Cross-Encoder <code>BAAI/bge-reranker-v2-m3</code> recalcula a relevância semântica profunda de cada par (query, documento). O <strong>Retrieval Grader</strong> descarta candidatos com pontuação inferior a 0.05, eliminando alucinações por ruído.
              </p>
              <div className="code-example">
                <code>
                  Top-1 Score: 0.9999 (Aprovado ✅) | Ruído: 0.0012 (Descartado pelo CRAG Grader ❌)
                </code>
              </div>
            </div>
          )}

          {activeTab === 3 && (
            <div className="tab-pane">
              <h4>🧠 Estágio 4: Reordenação Lost-in-the-Middle &amp; Semantic Cache</h4>
              <p>
                Para combater o déficit de atenção no centro do prompt, os chunks são organizados nas extremidades <code>[1º, 3º, 5º, 4º, 2º]</code>. Consultas idênticas ou paráfrases consultam o <strong>Cache Semântico (cosseno 0.92)</strong> com resposta em menos de 15ms.
              </p>
              <div className="code-example">
                <code>
                  Ordem de Injeção: [Top-1 Mais Relevante, Top-3, Top-5, Top-4, Top-2] | Cache Cosseno: 0.96 (Hit!)
                </code>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 3. Calculadora Interativa de FinOps */}
      <div className="playground-card" style={{ marginTop: "28px" }}>
        <div className="playground-header">
          <span className="playground-pill gold">Calculadora FinOps &amp; Eficiência</span>
          <h3>Simule a Economia de Custos e Latência da sua Instituição</h3>
          <p>Veja o impacto da poda de mensagens (trim_messages) e do Semantic Cache em escala.</p>
        </div>

        <div className="finops-calculator">
          <div className="slider-container">
            <div className="slider-label">
              <span>Volume Mensal Estimado:</span>
              <strong>{requestsPerMonth.toLocaleString("pt-BR")} mensagens/mês</strong>
            </div>
            <input
              type="range"
              min="5000"
              max="200000"
              step="5000"
              value={requestsPerMonth}
              onChange={(e) => setRequestsPerMonth(Number(e.target.value))}
              className="finops-slider"
            />
          </div>

          <div className="finops-stats-grid">
            <div className="finops-stat-card">
              <span className="stat-number">~{cachedRequests.toLocaleString("pt-BR")}</span>
              <span className="stat-desc">Respostas instantâneas servidas via Cache (&lt;15ms)</span>
            </div>
            <div className="finops-stat-card">
              <span className="stat-number">US$ {savedDollars}</span>
              <span className="stat-desc">Economia anual estimada em tokens de LLM</span>
            </div>
            <div className="finops-stat-card">
              <span className="stat-number">~{latencySavedHours} horas</span>
              <span className="stat-desc">Tempo de espera de usuários economizado por ano</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
