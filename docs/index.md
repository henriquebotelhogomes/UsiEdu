# UsiEdu — Documentação Técnica e Arquitetural

**UsiEdu** é uma plataforma conversacional multi-agente de padrão **Scale-up Enterprise**, projetada para unificar o atendimento e autosserviço de instituições de ensino superior com respostas determinísticas, fundamentadas e auditáveis.

---

## 🎯 Pilares da Arquitetura

1. **Orquestração Multi-Agente com LangGraph:**
   - Grafo de estados determinístico (`StateGraph`) com supervisor com saída estruturada tipada (`with_structured_output`), checkpointers SQLite/Postgres e suporte a `interrupt_before` para **Human-in-the-Loop (HITL)**.
   - Reducers de estado resilientes a conversas multi-turnos com reset explícito de contexto.

2. **RAG Híbrido em 4 Estágios:**
   - **Busca Densa:** Qdrant Vector DB com embeddings locais otimizados via ONNX.
   - **Busca Esparsa:** BM25 lexical search para precisão em termos regulatórios e leis.
   - **Fusão RRF:** Reciprocal Rank Fusion ($k=60$) combinando os rankings.
   - **Re-ranking:** Cross-Encoder com `BAAI/bge-reranker-base` para seleção cirúrgica dos Top Chunks.

3. **Middleware de Contexto do Sistema (Grounding Universal):**
   - Injeção dinâmica de data/hora oficial no fuso de Brasília, fuso horário, semestre letivo e perfil de sessão antes de qualquer chamada LLM.

4. **FinOps & AI Safety:**
   - Semantic Caching vetorial com limiar de similaridade $\ge 0.92$ (respostas em <15ms e custo zero de tokens).
   - Mascaramento de dados sensíveis (PII Masking) e poda dinâmica de tokens (`trim_messages`).

5. **Qualidade Contínua e LLM-as-a-Judge:**
   - Suíte com mais de **450 testes unitários automatizados** (100% aprovados).
   - Quality Gate de CI/CD baseado no framework **RAGAS** (*Faithfulness $\ge 0.85$*) e **Agent Trajectory Harness**.

---

## 🧭 Navegação Recomendada

| Seção | Descrição |
|---|---|
| [Visão Geral da Arquitetura](01-visao-geral-arquitetura.md) | Topologia de nós, fluxo de dados e decisões arquiteturais |
| [Agentes e Orquestração](02-agentes-e-orquestracao.md) | Papéis dos agentes especialistas, supervisor e consolidação |
| [RAG e Infraestrutura](03-rag-e-infraestrutura.md) | Pipeline de ingestão, chunking semântico e Qdrant |
| [Piloto e Roadmap](04-piloto-e-roadmap.md) | Escopo funcional, público-alvo e cronograma de evolução |
| [Fontes da Base de Conhecimento](05-fontes-base-conhecimento.md) | Documentos institucionais, resoluções e normas |
| [PRD e Requisitos](07-prd-requisitos.md) | Requisitos funcionais, não-funcionais e critérios de aceite |
| [Contratos Técnicos de API](09-contratos-tecnicos.md) | Especificação das rotas REST, schemas Pydantic e SSE |

---

## 🧰 Stack Tecnológica Principal

- **Backend:** Python 3.12, FastAPI, LangGraph, LangChain, Pydantic v2
- **Recuperação:** Qdrant (Vetorial), BM25 (Léxico), FastEmbed, Cross-Encoder Re-ranker
- **Segurança & FinOps:** SQLite Semantic Cache, PII Masking, SlowAPI Rate Limiter
- **Frontend:** React 18, Vite, TypeScript, SSE Streaming, Vitest
- **Qualidade & Observabilidade:** pytest, Ruff, RAGAS (LLM-as-a-Judge), LangSmith Tracing
- **Cloud & Deploy:** Azure Container Apps, Bicep IaC, Docker

---

## 🐙 Repositório Oficial

Código-fonte, issues e releases estão disponíveis em:  
[github.com/henriquebotelhogomes/UsiEdu](https://github.com/henriquebotelhogomes/UsiEdu)
