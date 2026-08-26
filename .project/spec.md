# Especificação do Sistema UsiEdu (.project/spec.md)

## 1. Contratos da API REST
- `POST /auth/login`: Autenticação e emissão de JWT com perfil (`student` / `staff`).
- `POST /chat`: Envio síncrono de mensagem com execução do StateGraph e retorno estruturado.
- `POST /chat/stream`: Streaming Server-Sent Events (SSE) token a token via `astream_events(v2)`.
- `POST /chat/resume`: Retomada de threads pausadas por aprovação humana (*Human-in-the-Loop*).
- `GET /chat/history`: Leitura do histórico persistido na thread do checkpointer.
- `POST /feedback`: Registro de feedback humano (👍/👎 + comentário) vinculado a run_id do LangSmith.
- `GET /health`: Healthcheck do sistema com métricas de cache e conexões ativas.

## 2. Estrutura de Pastas
```
UsiEdu/
├── .project/                  # Metadados e especificações do projeto
├── .github/workflows/         # Pipelines CI/CD (Quality Gate, Lint, Deploy)
├── frontend/                  # SPA React + Vite + TypeScript
├── infra/azure/               # Templates IaC Bicep e scripts de deploy
├── knowledge_base/            # Documentos HTML/PDF institucionais
├── scripts/                   # Utilitários de CLI (RAGAS, Ingest, Capturas)
├── src/
│   ├── agents/                # Prompts e nós especialistas (acadêmico, financeiro, documental)
│   ├── api/                   # Rotas FastAPI, schemas Pydantic e middlewares
│   ├── evaluation/            # Avaliação de qualidade RAGAS e baselines
│   ├── llm/                   # Providers de LLM e modelos fake para testes
│   ├── observability/         # Logging estruturado e tracing LangSmith
│   ├── orchestration/         # StateGraph, Supervisor, Consolidação e AgentState
│   ├── rag/                   # Embedder, Qdrant, BM25, Reranker e Semantic Cache
│   ├── security/              # Guardrails, sanitização PII e filtros de injeção
│   ├── storage/               # Conexões de banco SQLite e PostgreSQL
│   └── tools/                 # Ferramentas nativas decoradas com @tool
└── tests/
    ├── unit/                  # Suíte de >300 testes unitários automatizados
    └── integration/           # Testes ponta a ponta com dependências reais
```
