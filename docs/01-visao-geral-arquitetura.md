# UsiEdu — Documentação de Arquitetura

> **Projeto piloto para candidatura — Engenheiro(a) de IA | Cruzeiro do Sul Educacional**
> Plataforma multi-agente de IA conversacional para a jornada do estudante e do colaborador.

---

## 1. Visão Geral

### 1.1 Propósito

A **UsiEdu** é uma plataforma unificada de agentes de IA que atende dois públicos da instituição:

- **Estudantes**: assistente de jornada acadêmica (dúvidas acadêmicas, financeiras e de carreira) e tutor pedagógico personalizado.
- **Funcionários e docentes**: assistente de conhecimento institucional (normas, políticas, processos internos).

As três funcionalidades compartilham uma **infraestrutura única**: orquestração LangGraph, pipeline de RAG, banco vetorial, camada de tool calling e observabilidade — mudando apenas quais agentes cada perfil acessa.

### 1.2 Problema que resolve

| Dor | Público | Solução |
|---|---|---|
| Atendimento lento e setorizado (financeiro/acadêmico) | Estudante | Orquestração multi-agente com resposta única e coerente |
| Evasão por atrito burocrático | Estudante | Autoatendimento 24/7 imediato |
| Estudo genérico, sem adaptação ao ritmo do aluno | Estudante | Tutor com memória de longo prazo e plano de estudo adaptativo |
| Conhecimento institucional espalhado (PDFs, intranet, e-mails) | Funcionário/Docente | RAG com citação de fonte sobre documentos oficiais |
| Processos internos burocráticos | Funcionário | Agente de processos com tool calling em sistemas |

### 1.3 Pilares técnicos (alinhados à vaga)

1. **Orquestração multi-agente** com LangGraph (fluxos stateful e cíclicos).
2. **Colaboração entre agentes (A2A)** usando o protocolo Agent-to-Agent do ecossistema Google.
3. **RAG de alta precisão** com vector DB (Qdrant/pgvector) e citação de fontes.
4. **Motor cognitivo Gemini via Vertex AI**.
5. **Tool calling** para consumo de APIs e bancos de dados.
6. **MCP (Model Context Protocol)** para conectar fontes de dados estruturadas.
7. **Memória de longo prazo** para sessões prolongadas (checkpointing + store persistente).
8. **Avaliação contínua** (Ragas + LLM-as-judge) e **observabilidade** (LangSmith + Grafana).

---

## 2. Personas e Perfis de Usuário

### 2.1 Estudante (persona: "Ana, 19 anos, caloura de ADS")

- Acessa a plataforma via chat (web).
- Usa o **Assistente de Jornada** para dúvidas acadêmicas, financeiras e de carreira.
- Usa o **Tutor Pedagógico** para estudar disciplinas, fazer quizzes e acompanhar seu progresso.

### 2.2 Funcionário/Docente (persona: "Carlos, 38 anos, coordenador de curso")

- Acessa a plataforma via chat (web) com autenticação corporativa.
- Usa o **Assistente Institucional** para consultar normas, políticas e abrir/simular processos internos.

### 2.3 Matriz perfil × agentes

| Agente | Estudante | Funcionário/Docente |
|---|:---:|:---:|
| Router/Supervisor | ✅ | ✅ |
| Agente Acadêmico | ✅ | — |
| Agente Financeiro | ✅ | — |
| Agente de Carreira | ✅ | — |
| Tutor Pedagógico | ✅ | — |
| Agente Documental (institucional) | — | ✅ |
| Agente de Processos | — | ✅ |

---

## 3. Arquitetura de Alto Nível

```
┌────────────────────────────────────────────────────────────────┐
│                   Frontend (React + Vite)                       │
│               autenticação + perfil (estudante/colaborador)     │
└──────────────────────────┬─────────────────────────────────────┘
                           │ REST/WebSocket
┌──────────────────────────▼─────────────────────────────────────┐
│                     API Gateway (FastAPI)                       │
│        autenticação · sessões · roteamento por perfil           │
└──────────────────────────┬─────────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────┐
│              Orquestrador Supervisor (LangGraph)                │
│  classificação de intenção · planejamento · delegação ·         │
│  consolidação de respostas · guardrails                         │
└───────┬──────────┬──────────┬──────────┬──────────┬────────────┘
        │          │          │          │          │
   ┌────▼───┐ ┌────▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────────┐
   │Acadêmi-│ │Financei-│ │Carreira│ │ Tutor  │ │Documental/ │
   │   co   │ │   ro    │ │        │ │Pedagóg.│ │ Processos  │
   └────┬───┘ └────┬────┘ └───┬────┘ └───┬────┘ └───┬────────┘
        │          │          │          │          │
┌───────▼──────────▼──────────▼──────────▼──────────▼────────────┐
│                  Camada de Infraestrutura Compartilhada          │
│                                                                  │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────┐  │
│  │ Pipeline    │ │ Vector DB    │ │ MCP Servers  │ │ Gemini │  │
│  │ RAG         │ │ (Qdrant/     │ │ (dados       │ │ Vertex │  │
│  │ (ingestão,  │ │  pgvector)   │ │ estruturados)│ │   AI   │  │
│  │ chunking,   │ │              │ │              │ │        │  │
│  │ embeddings) │ │              │ │              │ │        │  │
│  └─────────────┘ └──────────────┘ └──────────────┘ └────────┘  │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐              │
│  │ Memória     │ │ Avaliação    │ │ Observabil.  │              │
│  │ longo prazo │ │ (Ragas,      │ │ (LangSmith,  │              │
│  │ (store)     │ │  LLM-judge)  │ │  Grafana)    │              │
│  └─────────────┘ └──────────────┘ └──────────────┘              │
└──────────────────────────────────────────────────────────────────┘
```

### 3.1 Decisões arquiteturais principais

| Decisão | Escolha | Justificativa |
|---|---|---|
| Linguagem | Python 3.12+, assíncrono | Requisito da vaga; desempenho em I/O concorrente |
| API | FastAPI | Requisito da vaga; async nativo, OpenAPI automático |
| Orquestração | LangGraph (grafo supervisor) | Fluxos cíclicos e stateful; requisito central |
| LLM (runtime) | **OpenCode Go** (DeepSeek V4 Flash + Kimi K2.7 Code) com camada provider-agnostic que também suporta Gemini/Vertex | Custo zero na assinatura atual; abstração de provider demonstra integração com o ecossistema Google sem custo extra |
| Vector DB | Qdrant (piloto) | Auto-hospedável via Docker, fácil de demonstrar |
| Dados estruturados | MCP server (SQLite no piloto) | Demonstra o diferencial MCP da vaga |
| Protocolo entre agentes | A2A (Google) | Diferencial forte citado nominalmente na vaga |
| Memória | LangGraph Store + SQLite/Postgres | Memória persistente entre sessões (diferencial) |
| Observabilidade | LangSmith + Grafana | Tracing de LLM (citado na vaga) + métricas de infra |
| Frontend | React + Vite (TypeScript) | SPA moderna e leve; chat via API FastAPI |
| Documentação | MkDocs (Material theme) | Site navegável desta documentação, publicado junto ao piloto |
| Qualidade de código | Ruff (lint + format) + pytest | Padrão de engenharia: código limpo e testado |

---

## 4. Catálogo de Agentes

> Detalhes de prompts, estado e fluxo de cada agente: ver `02-agentes-e-orquestracao.md`.

### 4.1 Supervisor (Router)

- **Papel**: porta de entrada de toda conversa. Classifica intenção, monta plano (quando necessário), delega a agentes especialistas e consolida respostas.
- **Padrão de raciocínio**: ReAct para delegação simples; Plan-and-Solve para perguntas compostas.
- **Guardrails**: recusa assuntos fora do escopo institucional; nunca inventa políticas — exige fonte recuperada.

### 4.2 Agente Acadêmico (estudante)

- **Ferramentas**: RAG sobre regimento, calendário, ementas; tool calling em API acadêmica mockada (notas, faltas, matrícula).
- **Exemplo**: "Posso fazer avaliação substitutiva? Qual o prazo?" → RAG no regimento + resposta com citação.

### 4.3 Agente Financeiro (estudante)

- **Ferramentas**: API financeira mockada (boletos, simulação de renegociação).
- **Exemplo**: "Meu boleto venceu, consigo desconto?" → consulta status e propõe opções.

### 4.4 Agente de Carreira (estudante)

- **Ferramentas**: RAG sobre eventos, estágios, programas de bolsas.
- **Exemplo**: sugere monitoria e eventos da área do curso do aluno.

### 4.5 Tutor Pedagógico (estudante)

- **Ferramentas**: RAG sobre material da disciplina; gerador de quizzes; **memória de longo prazo** do perfil de aprendizado.
- **Exemplo**: adapta explicações com base nas dificuldades registradas; gera plano de revisão espaçada.

### 4.6 Agente Documental (funcionário/docente)

- **Ferramentas**: RAG sobre políticas internas, manuais, FAQ de RH/TI, regimentos docentes.
- **Exemplo**: "Como solicito reembolso de certificação?" → política exata + fluxo, com citação de fonte.

### 4.7 Agente de Processos (funcionário/docente)

- **Ferramentas**: MCP server sobre base estruturada de processos/chamados; tool calling para "abrir" solicitações mockadas.
- **Exemplo**: preenche formulário de solicitação automaticamente e retorna protocolo.

---

## 5. Piloto vs. Roadmap

> Detalhamento completo: ver `04-piloto-e-roadmap.md`.

### 5.1 Escopo do piloto (o que será enviado à empresa)

1. **Documento de arquitetura completo** (este repositório de docs).
2. **Fatia vertical funcional**:
   - Login simples com perfil (estudante/colaborador).
   - Estudante: Supervisor + Agente Acadêmico + Agente Financeiro colaborando.
   - Funcionário: Supervisor + Agente Documental (RAG institucional).
   - Infra compartilhada: 1 pipeline RAG, vector DB, observabilidade básica.
3. **Avaliação mínima**: dataset de ~30 perguntas com métricas Ragas (faithfulness, context precision).

### 5.2 Roadmap pós-piloto

- Fase 2: Tutor Pedagógico com memória de longo prazo; Agente de Carreira; Agente de Processos com MCP.
- Fase 3: Migração da comunicação entre agentes para protocolo A2A completo; avaliação contínua em produção; otimização de tokenomics.

---

## 6. Índice da documentação

| Documento | Conteúdo |
|---|---|
| `01-visao-geral-arquitetura.md` | Este documento: visão, personas, arquitetura |
| `02-agentes-e-orquestracao.md` | Agentes, grafo LangGraph, fluxos A2A, estado compartilhado |
| `03-rag-e-infraestrutura.md` | Pipeline de RAG, vector DB, MCP, memória, avaliação, observabilidade |
| `04-piloto-e-roadmap.md` | Escopo do piloto, critérios de aceite, roadmap, riscos |
| `05-fontes-base-conhecimento.md` | Catálogo de fontes abertas para a base de conhecimento do RAG |
| `06-visao-escala-global.md` | Gap analysis: o que faltaria para a UsiEdu como startup global |
| `07-prd-requisitos.md` | PRD: requisitos funcionais/não-funcionais, user stories, critérios de aceite |
| `08-plano-execucao.md` | Fases, sprints, tarefas e microtarefas com Definition of Done |
| `09-contratos-tecnicos.md` | API, env vars, modelos de dados, convenções e regras para implementadores |
