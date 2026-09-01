import { Link } from "react-router-dom";
import { InteractivePlayground } from "./InteractivePlayground";

const DOCS_URL = "https://henriquebotelhogomes.github.io/UsiEdu/";
const GITHUB_URL = "https://github.com/henriquebotelhogomes/UsiEdu";

const AGENTES = [
  {
    nome: "Agente Acadêmico",
    fase: "Piloto",
    descricao:
      "Calendário letivo, matrículas, trancamentos e processos de secretaria via RAG, além de notas e faltas integradas por tools.",
  },
  {
    nome: "Agente Financeiro",
    fase: "Piloto",
    descricao:
      "Consulta de boletos, prazos de vencimento e simulação de renegociação com dados mockados e identificação segura do aluno.",
  },
  {
    nome: "Agente Documental",
    fase: "Piloto",
    descricao:
      "Conhecimento institucional amplo para servidores e docentes: afastamentos, licenças, perícia, adicionais e Lei 8.112 com citação estrita de fontes.",
  },
  {
    nome: "Agente Tutor",
    fase: "Fase 2",
    descricao:
      "Apoio pedagógico personalizado com memória de longo prazo (Store) e trilhas de aprendizagem adaptativas.",
  },
];

const STACK = [
  ["Backend", "Python 3.12 · FastAPI · LangGraph · LangChain · Pydantic v2"],
  ["LLM Motor", "OpenCode Go (DeepSeek V4 Flash com reasoning)"],
  ["Vector DB", "Qdrant (HNSW + Filtro RBAC por Perfil + Storage Resiliente)"],
  ["Embeddings", "paraphrase-multilingual-MiniLM-L12-v2 local"],
  ["Re-ranker", "BAAI/bge-reranker-v2-m3 (Cross-Encoder multilingue)"],
  ["Observabilidade", "LangSmith Tracing + Logs JSON Estruturados"],
  ["Frontend", "React 18 + Vite + TypeScript + SSE Streaming"],
  ["Qualidade", "Ruff · pytest (538 testes - 100% verde) · LLM-as-a-Judge"],
];

const FONTES = [
  {
    nome: "DGP — Licença e Afastamentos",
    tipo: "HTML",
    descricao:
      "Diretrizes e procedimentos para afastamento de capacitação, pós-graduação stricto sensu e estudo no exterior.",
    publico: "Funcionário / Docente",
    urlOficial: "https://dgp.unb.br/afastamentos",
  },
  {
    nome: "Lei nº 8.112/1990 Consolidada",
    tipo: "HTML",
    descricao:
      "Regime Jurídico dos Servidores Públicos Civis da União — direitos, deveres, licenças e adicionais.",
    publico: "Funcionário / Docente",
    urlOficial: "https://www.planalto.gov.br/ccivil_03/leis/l8112cons.htm",
  },
  {
    nome: "Regimento Geral da UnB",
    tipo: "PDF",
    descricao:
      "Estatuto e Regimento Geral — base das regras acadêmicas, trancamentos e regime disciplinar.",
    publico: "Estudante · Funcionário",
    download: "/documentos/regimento_geral_unb.pdf",
    urlOficial: "https://unb.br/images/Documentos/Estatuto_e_Regimento_Geral_UnB.pdf",
  },
  {
    nome: "Calendário de Graduação 2026.2",
    tipo: "PDF",
    descricao:
      "Calendário Universitário de Graduação — datas letivas, períodos de matrícula e feriados oficiais.",
    publico: "Estudante",
    download: "/documentos/calendario_graduacao_2026_2.pdf",
    urlOficial:
      "https://saa.unb.br/wp-content/uploads/2026/06/2026_2_Calend_Ativ_Grad_15_06_2026.pdf",
  },
  {
    nome: "Guia do Servidor UnB",
    tipo: "HTML",
    descricao:
      "Decanato de Gestão de Pessoas — normas, avaliação de desempenho, progressão e processos administrativos.",
    publico: "Funcionário / Docente",
    urlOficial: "https://dgp.unb.br/servidor/guia-servidor",
  },
  {
    nome: "FAQ SAA (Perguntas Frequentes)",
    tipo: "HTML",
    descricao:
      "Secretaria de Administração Acadêmica — aproveitamento de estudos, registro e emissão de declarações.",
    publico: "Estudante",
    urlOficial: "https://saa.unb.br/perguntas-frequentes/",
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
            <a href="#playground">Playground Interativo</a>
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
            <span>Parent-Document RAG</span>
            <span>Self-Querying</span>
            <span>Lost-in-the-Middle Reorder</span>
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
              oficiais, além de consulta de notas, faltas e boletos.
            </p>
          </div>
          <div className="landing-card">
            <div className="landing-card-icon gold">🏛️</div>
            <h3>Para Funcionários e Docentes</h3>
            <p>
              Acesso exclusivo a normas internas, portarias e processos
              administrativos via Agente Documental, com isolamento seguro de
              perfil e citações auditáveis.
            </p>
          </div>
        </div>
      </section>

      {/* Seção Agentes */}
      <section id="agentes" className="landing-section dark">
        <h2>Agentes Especialistas no Grafo</h2>
        <p className="landing-section-sub">
          Cada agente possui escopo delimitado, ferramentas próprias e base de
          conhecimento indexada.
        </p>
        <div className="landing-grid-4">
          {AGENTES.map((agente) => (
            <div key={agente.nome} className="landing-card small">
              <span className={`agente-fase ${agente.fase === "Piloto" ? "piloto" : "fase2"}`}>
                {agente.fase}
              </span>
              <h4>{agente.nome}</h4>
              <p>{agente.descricao}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Arquitetura */}
      <section id="arquitetura" className="landing-section">
        <div className="landing-split">
          <div className="landing-split-text">
            <h2>Arquitetura Multi-Agente &amp; RAG Enterprise</h2>
            <p>
              O UsiEdu foi projetado seguindo as melhores práticas de IA corporativa:
            </p>
            <ul className="landing-feature-list">
              <li><strong>Parent-Document Retrieval:</strong> Chunks filhos para matching vetorial preciso com injeção do contexto pai integral</li>
              <li><strong>Lost in the Middle Reordering:</strong> Reorganização [1º, 3º, 5º, 4º, 2º] maximizando a atenção do LLM sobre os documentos-chave</li>
              <li><strong>Self-Querying &amp; Filtragem Pré-HNSW:</strong> Extração automática de metadados para filtro booleano antes do cálculo vetorial</li>
              <li><strong>Query Rewriting &amp; Coreferência:</strong> Resolução de pronomes no histórico antes do Qdrant/BM25</li>
              <li><strong>Corrective RAG (CRAG):</strong> Retrieval Grader com pontuação de corte para eliminar ruídos pós-reranking</li>
              <li><strong>Semantic Cache Warmup:</strong> Catálogo de perguntas pré-aquecidas com limiar 0.92 e latência &lt;15ms</li>
              <li><strong>Poda Dinâmica (trim_messages):</strong> Controle rigoroso de tokens e custos para conversas multi-turnos</li>
              <li><strong>Human-in-the-Loop com AsyncSqliteSaver:</strong> Persistência assíncrona com interrupção para autorização humana</li>
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

      {/* Playground Interativo */}
      <section id="playground" className="landing-section alt">
        <h2>Playground &amp; Simulador de Arquitetura</h2>
        <p className="landing-section-sub">
          Experimente em tempo real a lógica de roteamento, extração de fontes e controle de FinOps.
        </p>
        <InteractivePlayground />
      </section>

      {/* Pipeline RAG */}
      <section className="landing-section dark">
        <h2>Pipeline RAG de Última Geração (CRAG + Anthropic Standard)</h2>
        <p className="landing-section-sub">
          Recuperação hierárquica corrigida com rastreabilidade, reescrita coreferencial, re-ranking e avaliação contínua.
        </p>
        <div className="landing-grid-3">
          <div className="landing-step">
            <span>01</span>
            <h4>Parent-Document &amp; Self-Querying</h4>
            <p>
              Ancoragem contextual hierárquica, extração de filtros pré-HNSW e reescrita de query com resolução de pronomes antes da busca.
            </p>
          </div>
          <div className="landing-step">
            <span>02</span>
            <h4>Busca Híbrida, Rerank &amp; Reorder</h4>
            <p>
              Qdrant + BM25 fundidos via RRF, re-ranking Cross-Encoder, CRAG Grader e mitigação de Lost in the Middle nas extremidades do contexto.
            </p>
          </div>
          <div className="landing-step">
            <span>03</span>
            <h4>Geração, FinOps &amp; Ragas</h4>
            <p>
              Streaming SSE, Semantic Cache (0.92) com Warmup, trim_messages e validação contínua com Ragas Quality Gate.
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
                <strong>538</strong> testes unitários backend + 24 frontend (100% verde)
              </div>
              <div className="quality-badge">
                <strong>830</strong> chunks indexados (35 documentos oficiais)
              </div>
              <div className="quality-badge">
                <strong>LLM-as-a-Judge</strong> Faithfulness 0.933 · Relevancy 0.933 · Recall 0.900
              </div>
              <div className="quality-badge">
                <strong>CI/CD</strong> GitHub Actions + Ruff Linter + MkDocs
              </div>
            </div>
            <p className="landing-quality-note">
              Qualidade comprovada por avaliação semântica contínua com LLM-as-a-Judge por rubricas, testes de regressão com contratos criptográficos e RBAC com isolamento estrito de coleções.
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
