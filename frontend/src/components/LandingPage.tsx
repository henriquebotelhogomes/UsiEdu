import { Link } from "react-router-dom";

const DOCS_URL = "https://henriquebotelhogomes.github.io/UsiEdu/";
const GITHUB_URL = "https://github.com/henriquebotelhogomes/UsiEdu";

const AGENTES = [
  {
    nome: "Agente Acadêmico",
    fase: "Piloto",
    descricao:
      "Calendário, matrículas, trancamentos e processos de secretaria via RAG, além de notas e faltas integradas por tools.",
  },
  {
    nome: "Agente Financeiro",
    fase: "Piloto",
    descricao:
      "Consulta de boletos, prazos de pagamento e simulação de renegociação com dados mockados e identificação segura do aluno.",
  },
  {
    nome: "Agente Documental",
    fase: "Piloto",
    descricao:
      "Conhecimento institucional para funcionários e docentes: normas, portarias e processos internos com citação estrita de fontes.",
  },
  {
    nome: "Agente Tutor",
    fase: "Fase 2",
    descricao:
      "Apoio pedagógico personalizado com memória de longo prazo e trilhas de aprendizagem adaptativas.",
  },
];

const STACK = [
  ["Backend", "Python 3.12 · FastAPI · LangGraph · LangChain · Pydantic v2"],
  ["LLM", "OpenCode Go (DeepSeek V4 Flash / Kimi K2.7 Code)"],
  ["Vector DB", "Qdrant (Docker HNSW + Payload Filter)"],
  ["Embeddings", "sentence-transformers local (FastEmbed ONNX)"],
  ["Reranker", "BAAI/bge-reranker-base local"],
  ["Observabilidade", "LangSmith Tracing + Distributed Logs"],
  ["Frontend", "React 18 + Vite + TypeScript + SSE Streaming"],
  ["Qualidade", "Ruff · pytest (457 testes - 100%) · RAGAS Gate"],
];

const FONTES = [
  {
    nome: "Regimento Geral da UnB",
    tipo: "PDF",
    descricao:
      "Estatuto e Regimento Geral — base das regras acadêmicas e administrativas respondidas pelos agentes.",
    publico: "Estudante · Funcionário",
    download: "/documentos/regimento_geral_unb.pdf",
    urlOficial: "https://unb.br/images/Documentos/Estatuto_e_Regimento_Geral_UnB.pdf",
  },
  {
    nome: "Calendário de Graduação 2026.2",
    tipo: "PDF",
    descricao:
      "Calendário Universitário de Graduação — datas, prazos de matrícula e feriados do semestre.",
    publico: "Estudante",
    download: "/documentos/calendario_graduacao_2026_2.pdf",
    urlOficial:
      "https://saa.unb.br/wp-content/uploads/2026/06/2026_2_Calend_Ativ_Grad_15_06_2026.pdf",
  },
  {
    nome: "Guia do Servidor UnB",
    tipo: "HTML",
    descricao:
      "Decanato de Gestão de Pessoas — normas, direitos e processos internos para servidores.",
    publico: "Funcionário",
    urlOficial: "https://dgp.unb.br/servidor/guia-servidor",
  },
  {
    nome: "LDB — Lei nº 9.394/1996",
    tipo: "HTML",
    descricao:
      "Diretrizes e bases da educação nacional — camada de legislação federal do RAG.",
    publico: "Estudante",
    urlOficial: "https://www.planalto.gov.br/ccivil_03/leis/l9394.htm",
  },
];

export default function LandingPage() {
  return (
    <div className="landing">
      {/* Navbar */}
      <nav className="landing-nav">
        <div className="landing-nav-inner">
          <Link to="/" className="landing-logo">
            <span className="landing-logo-mark">U</span> UsiEdu
          </Link>
          <div className="landing-links">
            <a href="#funcionalidades">Funcionalidades</a>
            <a href="#agentes">Agentes</a>
            <a href="#arquitetura">Arquitetura</a>
            <a href="#fontes">Fontes</a>
            <a href="#stack">Stack</a>
            <a href={DOCS_URL} target="_blank" rel="noreferrer">
              Documentação
            </a>
            <a href={GITHUB_URL} target="_blank" rel="noreferrer">
              GitHub
            </a>
          </div>
          <Link to="/login" className="landing-cta-login">
            Entrar
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <header className="landing-hero">
        <div className="landing-hero-content">
          <span className="landing-badge">
            Série B / Scale-up Enterprise
          </span>
          <h1>
            Plataforma multi-agente de IA conversacional para a jornada universitária
          </h1>
          <p>
            Orquestração determinística com <strong>LangGraph</strong>, RAG híbrido de 4 estágios com{" "}
            <strong>Qdrant + BM25 + Re-ranker</strong>, Middleware de Contexto do Sistema e respostas auditáveis com citação oficial.
          </p>
          <div className="landing-hero-actions">
            <Link to="/login" className="btn-primary">
              Experimentar o assistente
            </Link>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer"
              className="btn-ghost"
            >
              Ver no GitHub
            </a>
          </div>
          <div className="landing-chips">
            <span>Python 3.12</span>
            <span>FastAPI</span>
            <span>LangGraph</span>
            <span>Qdrant</span>
            <span>Semantic Cache</span>
            <span>Human-in-the-Loop</span>
            <span>RAGAS Gate</span>
          </div>
        </div>
      </header>

      {/* Funcionalidades (duplo público) */}
      <section id="funcionalidades" className="landing-section">
        <h2>Dois públicos, uma plataforma integrada</h2>
        <p className="landing-section-sub">
          Um supervisor cognitivo estruturado roteia cada pergunta para o agente especialista certo com isolamento de contexto.
        </p>
        <div className="landing-grid-2">
          <div className="landing-card">
            <div className="landing-card-icon navy">🎓</div>
            <h3>Para Estudantes</h3>
            <p>
              Assistente de jornada acadêmica e financeira: dúvidas sobre calendário,
              matrícula e regimento respondidas com base em documentos
              oficiais, além de consulta de notas, faltas e simulação de renegociação
              de boletos. Perguntas compostas são resolvidas de forma colaborativa e paralela.
            </p>
          </div>
          <div className="landing-card">
            <div className="landing-card-icon teal">🏛️</div>
            <h3>Para Funcionários &amp; Docentes</h3>
            <p>
              Assistente de conhecimento institucional: normas, portarias e
              processos internos recuperados por busca híbrida (vetorial +
              BM25 + Cross-Encoder Re-ranker) e respondidos sempre com citação obrigatória do documento
              e da seção de origem.
            </p>
          </div>
        </div>
      </section>

      {/* Agentes */}
      <section id="agentes" className="landing-section alt">
        <h2>Especialização e Autonomia Multi-Agente</h2>
        <p className="landing-section-sub">
          Múltiplos agentes orquestrados por um nó supervisor central tipado com Pydantic, cada um com suas ferramentas e bases especializadas.
        </p>
        <div className="landing-grid-4">
          {AGENTES.map((agente) => (
            <div
              key={agente.nome}
              className={`landing-card small ${agente.fase === "Fase 2" ? "future" : ""}`}
            >
              <span className="landing-fase">{agente.fase}</span>
              <h4>{agente.nome}</h4>
              <p>{agente.descricao}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Arquitetura */}
      <section id="arquitetura" className="landing-section">
        <div className="landing-split">
          <div>
            <h2>Orquestração com LangGraph: Muito além de um simples wrapper</h2>
            <p>
              O grafo <strong>LangGraph</strong> executa o fluxo com gerenciamento de estado persistente,
              roteamento via <code>with_structured_output</code>, injeção de contexto temporal e pontos de interrupção
              para <strong>Human-in-the-Loop (HITL)</strong> em ações sensíveis.
            </p>
            <ul className="landing-list">
              <li><strong>Contextual Retrieval (Anthropic):</strong> Prefixos contextuais com metadados do documento pai no chunk (reduz falhas em até 49%)</li>
              <li><strong>Query Rewriting &amp; Coreferência:</strong> Resolução de pronomes no histórico antes do Qdrant/BM25</li>
              <li><strong>Corrective RAG (CRAG):</strong> Retrieval Grader com pontuação de corte para eliminar ruídos pós-reranking</li>
              <li><strong>Semantic Cache Warmup:</strong> Catálogo de perguntas institucionais pré-aquecidas com latência &lt;15ms</li>
              <li><strong>Geração Sintética &amp; Ragas:</strong> Dataset sintético automatizado de 50 perguntas balanceadas para CI/CD</li>
              <li><strong>Middleware Universal:</strong> Injeção de data/hora oficial de Brasília, fuso horário e perfil de sessão</li>
              <li><strong>Human-in-the-Loop (HITL):</strong> Pausa determinística no grafo para aprovação humana em ações críticas</li>
            </ul>
          </div>
          <div className="landing-split-img">
            <img
              src="/images/arquitetura.jpg"
              alt="Diagrama de arquitetura da UsiEdu"
            />
          </div>
        </div>
      </section>

      {/* Pipeline RAG */}
      <section className="landing-section dark">
        <h2>Pipeline RAG de Última Geração (CRAG + Anthropic Standard)</h2>
        <p className="landing-section-sub">
          Recuperação corrigida com rastreabilidade, reescrita coreferencial, re-ranking e avaliação contínua.
        </p>
        <div className="landing-grid-3">
          <div className="landing-step">
            <span>01</span>
            <h4>Contextual Retrieval &amp; Rewriting</h4>
            <p>
              Ancoragem hierárquica do documento pai no chunk e reescrita de query com resolução de pronomes antes da busca.
            </p>
          </div>
          <div className="landing-step">
            <span>02</span>
            <h4>Busca Híbrida &amp; CRAG Grader</h4>
            <p>
              Qdrant + BM25 fundidos via RRF, re-ranking via Cross-Encoder e Retrieval Grader descartando ruído com score &lt; 0.35.
            </p>
          </div>
          <div className="landing-step">
            <span>03</span>
            <h4>Geração, Cache &amp; Ragas</h4>
            <p>
              Streaming SSE, Semantic Cache pré-aquecido, citação estrita de fontes e validação contínua com Ragas Quality Gate.
            </p>
          </div>
        </div>
      </section>

      {/* Fontes da base de conhecimento */}
      <section id="fontes" className="landing-section">
        <h2>Fontes da Base de Conhecimento</h2>
        <p className="landing-section-sub">
          Documentos oficiais reais (UnB + legislação federal) que alimentam o
          RAG — baixe os PDFs ou acesse as fontes originais.
        </p>
        <div className="landing-grid-2">
          {FONTES.map((fonte) => (
            <div key={fonte.nome} className="landing-card small fonte-card">
              <div className="fonte-header">
                <span className={`fonte-badge ${fonte.tipo === "PDF" ? "pdf" : "html"}`}>
                  {fonte.tipo}
                </span>
                <span className="fonte-publico">{fonte.publico}</span>
              </div>
              <h4>{fonte.nome}</h4>
              <p>{fonte.descricao}</p>
              <div className="fonte-actions">
                {fonte.download ? (
                  <a href={fonte.download} download className="btn-download">
                    ⬇ Baixar {fonte.tipo}
                  </a>
                ) : (
                  <a
                    href={fonte.urlOficial}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-download"
                  >
                    Acessar documento
                  </a>
                )}
                <a
                  href={fonte.urlOficial}
                  target="_blank"
                  rel="noreferrer"
                  className="fonte-oficial"
                >
                  Fonte oficial ↗
                </a>
              </div>
            </div>
          ))}
        </div>
        <p className="fontes-note">
          A UnB é usada como stand-in de uma instituição real — mesma
          engenharia e mesma dificuldade de uma base proprietária. Catálogo
          completo na{" "}
          <a href={`${DOCS_URL}05-fontes-base-conhecimento/`} target="_blank" rel="noreferrer">
            documentação técnica
          </a>
          .
        </p>
      </section>

      {/* Stack */}
      <section id="stack" className="landing-section alt">
        <h2>Stack Tecnológico &amp; Qualidade</h2>
        <div className="landing-split">
          <div className="landing-table-wrap">
            <table className="landing-table">
              <thead>
                <tr>
                  <th>Camada</th>
                  <th>Tecnologia</th>
                </tr>
              </thead>
              <tbody>
                {STACK.map(([camada, tech]) => (
                  <tr key={camada}>
                    <td>{camada}</td>
                    <td>{tech}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div>
            <div className="landing-quality-badges">
              <div className="quality-badge">
                <strong>457</strong> testes unitários (100% aprovados)
              </div>
              <div className="quality-badge">
                <strong>RAGAS</strong> Quality Gate automatizado
              </div>
              <div className="quality-badge">
                <strong>CI/CD</strong> GitHub Actions + Ruff Linter
              </div>
              <div className="quality-badge">
                <strong>MkDocs</strong> documentação navegável completa
              </div>
            </div>
            <p className="landing-quality-note">
              Qualidade validada por suítes contínuas de regressão, testes de trajetória de agentes e LLM-as-a-Judge.
            </p>
            <a
              href={DOCS_URL}
              target="_blank"
              rel="noreferrer"
              className="btn-primary"
            >
              Ler a documentação técnica
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="landing-nav-inner footer-inner">
          <span className="landing-logo">
            <span className="landing-logo-mark">U</span> UsiEdu
          </span>
          <span className="footer-license">
            © 2026 — Licença MIT · Plataforma Multi-Agente Universitária
          </span>
          <div className="footer-links">
            <Link to="/insights">Satisfação</Link>
            <a href={DOCS_URL} target="_blank" rel="noreferrer">
              Documentação
            </a>
            <a href={GITHUB_URL} target="_blank" rel="noreferrer">
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
