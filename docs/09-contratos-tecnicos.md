# Contratos Técnicos e Convenções

> Especificação exata de interfaces, dados e convenções. Um implementador (humano ou IA)
> que ler os docs 01–09 deve conseguir construir o piloto **sem precisar tomar decisões
> de design**. Se algo aqui conflitar com outro doc, este documento prevalece para
> interfaces; o PRD prevalece para comportamento.

---

## 1. Regras para agentes de IA implementadores

1. Ler na ordem: doc 07 (PRD) → doc 08 (plano) → este documento → demais.
2. Implementar **somente** requisitos RF/RNF numerados; citar o ID do requisito no PR
   ou commit (ex.: `feat: filtro de coleção por perfil (RF-22)`).
3. Nunca criar dependência nova sem registrá-la aqui (seção 8) e no `pyproject.toml`.
4. Toda função pública com type hints completos; docstring apenas quando o comportamento
   não for óbvio.
5. Dúvida de design não documentada → **parar e perguntar** (regra 4 do doc 08).
6. **Manter os checklists sempre atualizados**: ao concluir uma tarefa/microtarefa,
   marcar o checkbox no doc 08 imediatamente (no mesmo commit); ao iniciar uma sessão,
   ler o estado dos checklists antes de qualquer ação (doc 08 regra 6).
   Isso vale também para os checklists de aceite (doc 04 seção 5) e gate de entrega
   (doc 07 seção 7) conforme forem sendo validados.
7. **Verificação antes de declarar pronto** (doc 08 regra 7): testes determinísticos verdes
   → autorevisão apenas do diff da tarefa contra o DoD → evidência registrada. Nunca
   retestar o projeto inteiro de forma genérica.
8. **Recomendar 3 modelos antes de cada tarefa** (doc 08 regra 8): sempre apresentar
   3 opções de LLM disponíveis no Qoder classificadas por complexidade × custo de tokens,
   com a recomendação destacada. A decisão final é do usuário.

## 2. Contrato da API REST (FastAPI, prefixo `/api/v1`)

### 2.1 Endpoints

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| POST | `/auth/login` | não | Autentica e retorna JWT |
| POST | `/chat` | sim | Envia mensagem e recebe resposta (fallback obrigatório do streaming) |
| POST | `/chat/stream` | sim | Streama a resposta via SSE (T7.3); body idêntico a `ChatRequest` |
| GET | `/chat/history?session_id={id}` | sim | Retorna histórico da sessão (T7.4): 404 se inexistente, 403 se pertence a outro usuário |
| POST | `/feedback` | sim | Registra avaliação `up`/`down` de uma resposta |
| GET | `/feedback/stats` | sim | Retorna totais e taxa agregada de satisfação |
| GET | `/feedback/recent?limit={1..100}` | sim | Retorna os feedbacks mais recentes sem expor `message_id` |
| GET | `/health` | não | Liveness: `{ "status": "ok" }` |
| GET | `/ready` | não | Readiness rasa: `{ "status": "ready" }` somente após processo, configuração e modelos serem inicializados; não consulta LLM, Qdrant ou PostgreSQL |

### 2.2 Schemas (Pydantic)

```python
# auth
class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str  # JWT, expira em 1h
    token_type: str = "bearer"
    profile: Literal["student", "staff"]
    display_name: str


# chat
class ChatRequest(BaseModel):
    session_id: str  # uuid fornecido pelo cliente
    message: str  # máx. 2000 caracteres


class Source(BaseModel):
    document: str  # ex.: "Regimento Geral da UnB"
    section: str | None  # ex.: "Título III, Cap. II, Art. 112"
    excerpt: str  # trecho recuperado
    url: str | None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    agents_involved: list[str]  # ex.: ["academico", "financeiro"]
    sources: list[Source]
    intent: Literal["academico", "financeiro", "institucional", "composta", "fora_de_escopo"]


# histórico (T7.4)
class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: str | None = None  # o checkpointer não persiste timestamp


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatHistoryMessage]  # agentes/fontes omitidos: só texto


# feedback
class FeedbackRequest(BaseModel):
    session_id: str
    message_id: str  # run_id recebido no evento SSE meta
    rating: Literal["up", "down"]
    comment: str | None = None  # máximo de 500 caracteres


class FeedbackResponse(BaseModel):
    status: str = "ok"
    feedback_id: int


class FeedbackStats(BaseModel):
    total: int
    up: int
    down: int
    satisfaction: float  # up / total em [0, 1]; zero quando total = 0


class FeedbackRecentItem(BaseModel):
    rating: Literal["up", "down"]
    comment: str | None
    profile: str
    created_at: str  # ISO 8601
    message_ref: str  # primeiros 8 hex de sha256(message_id)


class FeedbackRecentResponse(BaseModel):
    items: list[FeedbackRecentItem]  # mais recentes primeiro
```

### 2.2.1 Eventos SSE do `POST /chat/stream` (T7.3)

Linhas `data: {json}\n\n` com o tipo no campo `event`:

| Evento | Payload | Quando |
|---|---|---|
| `meta` | `{session_id, message_id}` | início (`message_id` = `run_id` do LangSmith, usado no feedback) |
| `token` | `{delta}` | cada chunk do LLM dos agentes finais (supervisor nunca é streamado) |
| `final` | `{agents, sources, usage, answer}` | fim do grafo (`answer` é extra ao contrato do PRD: reconcilia o texto final) |
| `error` | `{detail}` | qualquer exceção (fecha o stream) |

O frontend usa `fetch` + `ReadableStream` (SSE sobre POST; `EventSource` é GET-only)
e faz fallback automático para `POST /chat` em erro de rede/parse antes de receber tokens.
Nginx exige `proxy_buffering off` no `location /chat/stream`.

### 2.3 Erros padronizados

```json
{ "error": { "code": "UNAUTHORIZED", "message": "..." } }
```
Códigos: `UNAUTHORIZED` (401), `FORBIDDEN` (403), `VALIDATION` (422),
`SESSION_NOT_FOUND` (404), `LLM_UNAVAILABLE` (503), `INTERNAL` (500).

## 3. Variáveis de ambiente (`.env.example`)

```ini
# LLM — provider ativo
USIEDU_LLM_PROVIDER=opencode-go        # opencode-go | gemini
OPENCODE_GO_API_KEY=                    # chave da assinatura OpenCode Go
OPENCODE_GO_BASE_URL=https://opencode.ai/zen/go/v1
USIEDU_ROUTER_MODEL=deepseek-v4-flash   # supervisor/roteamento
USIEDU_AGENT_MODEL=kimi-k2.7-code       # agentes/consolidação
# Gemini (opcional, stub)
GOOGLE_APPLICATION_CREDENTIALS=

# Vector DB
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_ACADEMICO=academico
QDRANT_COLLECTION_INSTITUCIONAL=institucional

# Auth
JWT_SECRET=                             # gerar: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_EXPIRES_MINUTES=60

# Observabilidade
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=usiedu-pilot
# Alias LangChain aceito pela biblioteca e configurado no Azure
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=usiedu-pilot

# Modelos locais
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
RERANKER_MODEL=BAAI/bge-reranker-v2-m3

# App
USIEDU_ENV=dev                          # dev | test | prod
LOG_LEVEL=INFO
USIEDU_CORS_ORIGINS=http://localhost:5173,http://localhost:5174
# Produção: URL PostgreSQL com sslmode=require. Ausente = fallback SQLite local.
USIEDU_DATABASE_URL=
USIEDU_FEEDBACK_DB=usiedu_feedback.db
USIEDU_CHECKPOINTER_DB=usiedu_checkpoints.db
```

## 4. Modelos de dados mockados (`src/tools/mock_data.py`)

```python
STUDENTS = {
    "ana-123": {
        "nome": "Ana Souza",
        "curso": "ADS",
        "periodo": 1,
        "notas": {"calculo-1": 5.8, "programacao-1": 9.1},
        "faltas": {"calculo-1": 6, "programacao-1": 0},
    },
}
BOLETOS = {
    "ana-123": [
        {"id": "bol-001", "valor": 890.00, "vencimento": "2026-07-10", "status": "vencido"},
    ],
}
POLITICA_RENEGOCIACAO = {
    "desconto_maximo_percentual": 10,  # aplicado apenas a juros/multa
    "parcelas_maximas": 6,
    "condicao": "apenas boletos vencidos há menos de 30 dias",
}
```

Todas as tools dos agentes são funções assíncronas puras sobre esses dados —
nunca há I/O real fora do Qdrant.

## 5. Estrutura do grafo LangGraph (contrato)

```
Nós: supervisor_node | academico_node | financeiro_node |
     documental_node | consolidation_node
Arestas: START → supervisor
         supervisor → {academico|financeiro|documental|END} (condicional por intenção/perfil)
         supervisor → [academico, financeiro] em paralelo (intenção composta)
         {agentes} → consolidation
         consolidation → supervisor (se needs_more_info e ciclos < 2) | END
Checkpointer: SQLite, chave thread_id = session_id
```

Saída estruturada do supervisor (validada com Pydantic):

```python
class SupervisorDecision(BaseModel):
    intent: Literal["academico", "financeiro", "institucional", "composta", "fora_de_escopo"]
    plan: list[str] | None  # sub-tarefas, apenas para intent="composta"
    reasoning: str  # breve justificativa (aparece no trace)
```

## 6. Convenções de código

| Tema | Regra |
|---|---|
| Estilo | Ruff (default + `I` de isort); `ruff format` obrigatório |
| Tipos | `mypy --strict` desejável; mínimo: type hints em assinaturas públicas |
| Assincronia | Toda I/O assíncrona (`async def`); nada de `time.sleep` |
| Nomes | snake_case (funções/vars), PascalCase (classes); agentes = `*_node` |
| Prompts | Templates em `src/agents/prompts/*.py` como constantes nomeadas; nunca inline |
| Commits | Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`) com ID do RF |
| Branches | `main` protegida; uma branch por tarefa do doc 08 (ex.: `t1-2-ingestao`) |
| Testes | Nome `test_<unidade>_<comportamento>`; LLM sempre fake em testes |

## 7. Estrutura de diretórios (canônica — complementar ao doc 03)

```
src/
├── api/
│   ├── main.py              # app FastAPI, CORS, rotas
│   ├── auth.py              # login, JWT
│   ├── chat.py              # endpoint /chat
│   └── schemas.py           # modelos Pydantic da seção 2
├── orchestration/
│   ├── state.py             # AgentState
│   ├── graph.py             # montagem do grafo
│   ├── supervisor.py        # supervisor_node + SupervisorDecision
│   └── consolidation.py
├── agents/
│   ├── academico.py | financeiro.py | documental.py
│   └── prompts/             # templates de prompt
├── rag/
│   ├── ingest.py            # CLI: python -m src.rag.ingest
│   ├── chunker.py | embedder.py | retriever.py
├── tools/
│   ├── mock_data.py
│   └── academico_tools.py | financeiro_tools.py
├── llm/
│   └── provider.py          # get_chat_model()
└── evaluation/
    ├── dataset.jsonl        # 30 perguntas + referências
    └── run_ragas.py

tests/
├── unit/        # chunker, retriever, supervisor (LLM fake), tools
├── integration/ # grafo completo (LLM fake), API via httpx
└── conftest.py  # fixtures: fake LLM, qdrant em memória
```

## 8. Dependências principais (backend)

| Pacote | Uso |
|---|---|
| `fastapi`, `uvicorn`, `python-jose`, `passlib` | API + JWT |
| `langgraph`, `langchain`, `langchain-core` | Orquestração |
| `langchain-openai` | Cliente OpenAI-compatible p/ OpenCode Go |
| `langsmith` | Tracing |
| `qdrant-client` | Vector DB |
| `fastembed` (preferido) ou `sentence-transformers` | Embeddings + reranker locais, ONNX/batch (doc 03 seção 1.2) |
| `rank-bm25` | Componente BM25 da busca híbrida |
| `pymupdf`, `trafilatura` | Extração PDF/HTML |
| `ragas`, `datasets` | Avaliação |
| `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx` | Testes |
| `ruff`, `mkdocs-material` | Qualidade + docs |

Frontend: `react`, `react-dom`, `vite`, `typescript` (sem UI kit obrigatório;
CSS puro ou Tailwind à escolha do implementador). Renderização Markdown das
respostas (T7.1): `react-markdown`, `remark-gfm`, `remark-breaks`. Testes de
componente: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`,
`jsdom` (dev).

## 9. Definition of Done global

Uma funcionalidade está pronta quando:
1. Requisito RF correspondente atendido;
2. Testes criados/atualizados passando;
3. `ruff check` + `ruff format` limpos;
4. Sem variáveis de ambiente novas fora do `.env.example`;
5. Documentação relevante atualizada (se o comportamento mudou).

## 10. Modelos recomendados para implementar o projeto (agentes de dev)

O trabalho de desenvolvimento é feito na **IDE Qoder**, onde cada modelo consome
créditos por um multiplicador (x). Não confundir com os modelos de runtime do
produto (OpenCode Go, seção 3 do `.env.example`).

**Catálogo verificado no Qoder (2026-08):**

| Modelo | Multiplicador | Papel recomendado |
|---|---|---|
| **Qwen3.7-Max** | 0.1x | Inteligência de flagship a custo mínimo — melhor custo/benefício geral |
| **DeepSeek-V4-Flash** | 0.1x | Volume: boilerplate, testes, scripts de ingestão |
| **Kimi-K2.7-Code** | 0.3x | Implementador principal de coding (sprints 2–4) |
| **GLM-5.2** | 0.5x | Co-implementador e revisor de lógica complexa |
| **DeepSeek-V4-Pro** | 0.5x | Raciocínio forte intermediário |
| **Kimi-K3** | 0.8x | Premium para tarefas difíceis |
| **Qwen3.8-Max** | promoção | Premium via promoção ativa: raciocínio difícil e revisões críticas |
| **Qwen3.7-Plus** | custom | Configurável na aba Custom (frontend/docs) |

| Modo | Multiplicador |
|---|---|
| Lite | 0.0x |
| Efficient | 0.3x |
| Auto | 1.0x |
| Performance | 1.1x |
| Ultimate | 1.6x |

**Classificação de complexidade para recomendação de modelo (doc 08 regra 8):**

| Complexidade | Tipo de tarefa | Modelos indicados |
|---|---|---|
| Simples | Boilerplate, configs, arquivos de teste, docs, scripts | Qwen3.7-Max (0.1x), DeepSeek-V4-Flash (0.1x) |
| Média | Implementação padrão de módulo, integração de componentes | Kimi-K2.7-Code (0.3x), GLM-5.2 (0.5x), DeepSeek-V4-Pro (0.5x) |
| Complexa | Grafo LangGraph, debug difícil, prompts, revisões críticas | Qwen3.8-Max (promoção), modo Ultimate (1.6x), Kimi-K3 (0.8x) |

> Antes de cada tarefa, apresentar **3 opções** desta tabela adequadas ao caso,
> com promoções ativas e créditos em conta. A escolha final é sempre do usuário.

**Estratégia de roteamento por tarefa:**
- Boilerplate/testes/scripts → 0.1x (Qwen3.7-Max ou DeepSeek-V4-Flash)
- Lógica de agentes/grafo → Kimi-K2.7-Code (0.3x) ou GLM-5.2 (0.5x)
- Raciocínio difícil e revisões críticas → Qwen3.8-Max (promoção) ou Ultimate (1.6x)
- Revisão final de cada sprint → modelo forte diferente do que implementou (olhar fresco)
- Nunca usar modelo caro para tarefas que um 0.1x resolve
