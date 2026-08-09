import { Link } from "react-router-dom";

const DOCS_URL = "https://henriquebotelhogomes.github.io/UsiEdu/";
const GITHUB_URL = "https://github.com/henriquebotelhogomes/UsiEdu";

const AGENTES = [
  {
    nome: "Agente Acadêmico",
    fase: "Piloto",
    descricao:
      "Calendário, matrículas, trancamentos e processos de secretaria via RAG, além de notas e faltas por tools.",
  },
  {
    nome: "Agente Financeiro",
    fase: "Piloto",
    descricao:
      "Consulta de boletos e simulação de renegociação com dados mockados e identificação segura do aluno.",
  },
  {
    nome: "Agente Documental",
    fase: "Piloto",
    descricao:
      "Conhecimento institucional para funcionários e docentes: normas, políticas e processos com citação de fonte.",
  },
  {
    nome: "Agente Tutor",
    fase: "Fase 2",
    descricao:
      "Apoio pedagógico personalizado com memória de longo prazo e trilhas de aprendizagem adaptativas.",
  },
];

const STACK = [
  ["Backend", "Python 3.12 · FastAPI · LangGraph · LangChain"],
  ["LLM", "DeepSeek V4 Flash (OpenCode Go)"],
  ["Vector DB", "Qdrant (Docker)"],
  ["Embeddings", "sentence-transformers local (ONNX)"],
  ["Reranker", "bge-reranker-base local"],
  ["Observabilidade", "LangSmith"],
  ["Frontend", "React + Vite + TypeScript"],
  ["Qualidade", "Ruff · pytest (96,7% cobertura) · GitHub Actions"],
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
            Projeto piloto — candidatura Engenheiro(a) de IA
          </span>
          <h1>
            Plataforma multi-agente de IA conversacional para a jornada do
            estudante e do colaborador
          </h1>
          <p>
            Orquestração com <strong>LangGraph</strong>, RAG híbrido com{" "}
            <strong>Qdrant</strong> e respostas rastreáveis com citação de
            fontes oficiais — sem alucinação.
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
            <span>React + Vite</span>
            <span>LangSmith</span>
          </div>
        </div>
      </header>

      {/* Funcionalidades (duplo público) */}
      <section id="funcionalidades" className="landing-section">
        <h2>Dois públicos, uma plataforma</h2>
        <p className="landing-section-sub">
          Um supervisor único roteia cada pergunta para o agente especialista
          certo.
        </p>
        <div className="landing-grid-2">
          <div className="landing-card">
            <div className="landing-card-icon navy">🎓</div>
            <h3>Para Estudantes</h3>
            <p>
              Assistente de jornada acadêmica: dúvidas sobre calendário,
              matrícula e regimento respondidas com base em documentos
              oficiais, e vida financeira com consulta de boletos e simulação
              de renegociação. Perguntas compostas são resolvidas por agentes
              em colaboração.
            </p>
          </div>
          <div className="landing-card">
            <div className="landing-card-icon teal">🏛️</div>
            <h3>Para Funcionários &amp; Docentes</h3>
            <p>
              Assistente de conhecimento institucional: normas, políticas e
              processos internos recuperados por busca híbrida (vetorial +
              BM25 + reranking) e respondidos sempre com citação do documento
              e da seção de origem.
            </p>
          </div>
        </div>
      </section>

      {/* Agentes */}
      <section id="agentes" className="landing-section alt">
        <h2>Especialização por agentes</h2>
        <p className="landing-section-sub">
          Múltiplas IAs coordenadas por um supervisor, cada uma com seu
          domínio de conhecimento e ferramentas.
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
            <h2>Orquestração supervisor: além de um wrapper de LLM</h2>
            <p>
              O grafo <strong>LangGraph</strong> classifica a intenção da
              pergunta no <strong>supervisor</strong>, aplica guardrails
              (fora de escopo, recusa honesta quando o documento não responde)
              e roteia para o agente especialista, que consulta a base de
              conhecimento via RAG híbrido antes de responder.
            </p>
            <ul className="landing-list">
              <li>Busca híbrida: vetorial + BM25 + reranking local</li>
              <li>Citação explícita de fonte em cada resposta</li>
              <li>Memória de conversa por sessão (checkpointer SQLite)</li>
              <li>Tracing completo no LangSmith: supervisor → agente → LLM</li>
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
        <h2>Pipeline RAG de alta precisão</h2>
        <p className="landing-section-sub">
          Recuperação com rastreabilidade e avaliação contínua.
        </p>
        <div className="landing-grid-3">
          <div className="landing-step">
            <span>01</span>
            <h4>Ingestão</h4>
            <p>
              Documentos oficiais (PDF/HTML) processados e fatiados com
              overlap, embeddings locais com sentence-transformers (ONNX).
            </p>
          </div>
          <div className="landing-step">
            <span>02</span>
            <h4>Recuperação</h4>
            <p>
              Qdrant com busca semântica + BM25, reranking com
              bge-reranker-base e janela deslizante sobre os trechos mais
              relevantes.
            </p>
          </div>
          <div className="landing-step">
            <span>03</span>
            <h4>Resposta</h4>
            <p>
              Geração fiel ao contexto com citação de fonte; quando não há
              resposta no documento, o agente admite não saber — sem
              alucinar.
            </p>
          </div>
        </div>
      </section>

      {/* Fontes da base de conhecimento */}
      <section id="fontes" className="landing-section">
        <h2>Fontes da base de conhecimento</h2>
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
        <h2>Stack e qualidade</h2>
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
                <strong>206</strong> testes passando
              </div>
              <div className="quality-badge">
                <strong>96,7%</strong> cobertura (orquestração/RAG)
              </div>
              <div className="quality-badge">
                <strong>CI</strong> GitHub Actions + Ruff
              </div>
              <div className="quality-badge">
                <strong>MkDocs</strong> documentação navegável
              </div>
            </div>
            <p className="landing-quality-note">
              Avaliação com Ragas e tracing LangSmith documentados na seção de
              avaliação do projeto.
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
            © 2026 — Licença MIT · Projeto piloto para candidatura Cruzeiro do
            Sul Educacional
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
