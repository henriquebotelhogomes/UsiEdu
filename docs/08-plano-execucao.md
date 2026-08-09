# Plano de Execução — Fases, Sprints e Tarefas

> Quebra operacional do piloto em **sprints de 1 semana** (dedicação parcial ~10–15 h/semana).
> Cada tarefa tem microtarefas acionáveis e Definition of Done (DoD).
> Regra de ouro: **uma sprint não começa sem a anterior concluída** (dependências abaixo).

---

## Mapa de dependências

```
Sprint 0 (fundação) ──► Sprint 1 (RAG) ──► Sprint 2 (orquestração)
                                                   │
                     ┌─────────────────────────────┤
                     ▼                             ▼
              Sprint 3 (multi-agente)       Sprint 4 (staff + auth)
                     └────────────┬───────────────┘
                                  ▼
                          Sprint 5 (frontend + tracing)
                                  ▼
                          Sprint 6 (avaliação + entrega)
```

---

## Sprint 0 — Fundação do repositório (3–5 dias)

**Épico:** ambiente de desenvolvimento completo e reprodutível.

- [x] **T0.1 — Estrutura do repositório**
  - [x] Criar estrutura conforme doc 03 seção 9 (`src/`, `frontend/`, `tests/`, `docs/`, `knowledge_base/`)
  - [x] `pyproject.toml`: dependências (fastapi, uvicorn, langgraph, langchain, qdrant-client, sentence-transformers, ragas, pytest, ruff) + config de ruff e pytest
  - [x] `.env.example` com todas as variáveis (ver doc 09)
  - [x] `.gitignore`, README com quickstart
- [x] **T0.2 — Qualidade de código**
  - [x] Ruff configurado (check + format) rodando sem erros no esqueleto
  - [x] Pytest configurado com 1 teste de sanidade passando
  - [x] GitHub Actions: CI com `ruff check` + `pytest` em todo PR
- [x] **T0.3 — Infra local**
  - [x] `docker-compose.yml` com Qdrant
  - [x] Script `make dev` / `scripts/dev.ps1` subindo tudo

**DoD da sprint:** `git clone` + comandos do README deixam ambiente funcional; CI verde.

---

## Sprint 1 — Pipeline RAG (5–7 dias)

**Épico:** documentos da UnB indexados e recuperáveis com precisão.

- [x] **T1.1 — Aquisição dos documentos (RF-23)**
  - [x] Baixar Regimento Geral UnB (PDF), Calendário 2026.2 (PDF), Guia do Servidor (HTML→PDF), LDB (HTML)
  - [x] Salvar em `knowledge_base/` com `manifest.json` (url, checksum, público-alvo)
- [x] **T1.2 — Ingestão (RF-20)**
  - [x] Extração: PyMuPDF para PDFs; trafilatura/bs4 para HTML
  - [x] Chunking semântico por seção (500–800 tokens, overlap 15%)
  - [x] Embeddings locais com **batching** (FastEmbed ONNX ou sentence-transformers) — ver doc 03 seção 1.2
  - [x] Cache de embeddings em disco + ingestão incremental (manifest com checksum)
  - [x] Gravação no Qdrant: coleções `academico` e `institucional` com metadados completos
  - [x] Idempotência: hash do chunk como ID (RNF-07)
  - [x] Verificação: ingestão completa do núcleo mínimo em < 10 min (CPU)
- [x] **T1.3 — Recuperação (RF-21, RF-22)**
  - [x] Busca vetorial top-20 + BM25 (Qdrant sparse ou rank_bm25)
  - [x] Reranker local (bge-reranker) → top-5
  - [x] Filtro por perfil via metadados
- [x] **T1.4 — Testes do pipeline**
  - [x] Unitários: chunker, montagem de metadados, filtro por perfil
  - [x] Script manual de sanity: 10 perguntas → trechos recuperados coerentes

**DoD da sprint:** `python -m src.rag.ingest` indexa os 4 documentos; retriever retorna trechos corretos para 10 perguntas de sanity; cobertura ≥ 80% em `rag/`.

---

## Sprint 2 — Orquestração base (5–7 dias)

**Épico:** grafo LangGraph com Supervisor e 1 agente funcional.

- [x] **T2.1 — Camada de LLM provider-agnostic (doc 03 seção 4)**
  - [x] Factory `get_chat_model(provider)`: `opencode-go` (endpoint OpenAI-compatible) e `gemini` (stub documentado)
  - [x] DeepSeek V4 Flash para roteamento; Kimi K2.7 Code para agentes
  - [x] Testes com fake LLM determinístico (sem rede)
- [x] **T2.2 — Estado e grafo**
  - [x] `AgentState` conforme doc 02 seção 1.2
  - [x] Nós: `supervisor_node`, `academico_node`, `consolidation_node`; aresta cíclica com limite de 2 ciclos (RF-11)
  - [x] Checkpointer SQLite por `thread_id` (RF-03)
- [x] **T2.3 — Supervisor (RF-06, RF-07, RF-10)**
  - [x] Classificação de intenção com saída estruturada
  - [x] Guardrail de escopo com resposta padrão
- [x] **T2.4 — Agente Acadêmico (RF-12 a RF-14)**
  - [x] Integração com retriever + prompt com grounding e citação obrigatória
  - [x] Tools mockadas `get_notas`, `get_faltas` (dados em `src/tools/mock_data.py`)
- [x] **T2.5 — Testes**
  - [x] Grafo com LLM fake: roteamento correto, ciclo, guardrail
  - [x] Cobertura ≥ 80% em `orchestration/`

**DoD da sprint:** conversa funcional com perfil estudante sobre temas acadêmicos, com fontes citadas; testes verdes.

---

## Sprint 3 — Multi-agente colaborativo (5–7 dias)

**Épico:** cenário-estrela — pergunta composta resolvida por 2 agentes.

- [x] **T3.1 — Agente Financeiro (RF-15 a RF-17)**
  - [x] Tools `get_boletos`, `simular_renegociacao` com dados mockados
  - [x] Documento de política financeira mockada indexado na coleção `academico` (público estudante)
- [x] **T3.2 — Plan-and-Solve (RF-08, RF-09)**
  - [x] Supervisor gera plano para intenção `composta`
  - [x] Execução paralela (asyncio) das sub-tarefas independentes
  - [x] Consolidação em resposta única
- [x] **T3.3 — Metadados de resposta (RF-04, RF-05)**
  - [x] API retorna `agents_involved` e `sources` junto ao texto
- [x] **T3.4 — Testes**
  - [x] Cenário composto com LLM fake: plano, delegações, consolidação
  - [x] Teste de não-contradição entre resultados de agentes

**DoD da sprint:** US-01 demonstrável manualmente; suíte completa verde.

---

## Sprint 4 — Perfil staff + autenticação (4–6 dias)

**Épico:** segundo perfil completo e proteção por JWT.

- [x] **T4.1 — Auth (RF-01, RF-02)**
  - [x] `POST /auth/login` com usuários demo fixos; JWT 1 h
  - [x] Middleware validando token e extraindo perfil
- [x] **T4.2 — Agente Documental (RF-18, RF-19)**
  - [x] RAG na coleção `institucional` + citação obrigatória
- [x] **T4.3 — Isolamento por perfil (RF-02, RF-22)**
  - [x] Supervisor só enxerga agentes do perfil; retriever filtra coleção
  - [x] Testes de segurança: estudante não acessa documentos institucionais
- [x] **T4.4 — Testes de API**
  - [x] httpx/TestClient: login, chat autenticado, 401 sem token

**DoD da sprint:** US-02 demonstrável; testes de isolamento passando.

---

## Sprint 5 — Frontend + observabilidade (5–7 dias)

**Épico:** experiência de demo polida e rastreável.

- [x] **T5.1 — Frontend React + Vite (RF-24 a RF-27)**
  - [x] Scaffold Vite + TypeScript; consumo da API com proxy
  - [x] Tela de login com usuários demo visíveis
  - [x] Chat com streaming SSE
  - [x] Cards de fontes e agentes por resposta
  - [x] Botões dos 4 cenários de demo
- [x] **T5.2 — LangSmith (RF-30)**
  - [x] Tracing em todos os nós; run names com perfil + intenção
- [x] **T5.3 — Logs (RF-31)**
  - [x] Logging JSON estruturado com trace_id
- [x] **T5.4 — Docker Compose completo (RNF-03)**
  - [x] Serviços: api, frontend (build), qdrant
  - [x] Teste do zero: máquina limpa → `docker compose up` → demo funcionando

**DoD da sprint:** fluxo completo navegável no browser; traces visíveis no LangSmith.

---

## Sprint 6 — Avaliação, docs e entrega (5–7 dias)

**Épico:** provar qualidade e preparar envio.

- [x] **T6.1 — Dataset de avaliação (RF-28)**
  - [x] 30 perguntas + respostas de referência (incluindo sem-resposta e fora de escopo)
- [x] **T6.2 — Relatório Ragas (RF-29)**
  - [x] Script de eval; metas do doc 03 seção 6.1
  - [x] Iterar chunking/prompts até metas atingidas
- [x] **T6.3 — MkDocs (RF-33)**
  - [x] `mkdocs.yml` (Material) com os docs 01–10; build validado
- [x] **T6.4 — Vídeo de demo**
  - [x] Roteiro conforme doc 04 seção 8 (11 min); gravar US-01 a US-05
- [x] **T6.5 — Checklist final**
  - [x] Rodar checklist de aceite do doc 07 seção 7 item a item

**DoD da sprint:** todos os gates de entrega do PRD fechados; pacote pronto para envio.

---

## Sprint 7 — Qualidade Percebida (UX do chat) — PRD v2

**Épico:** o chat deve parecer um produto comercial, não um protótipo (`PRD.v2.md` seção 4).
**Ordem sugerida:** T7.1 → T7.2 → T7.4 → T7.3.

- [x] **T7.1 — Renderização Markdown nas respostas (RF2-01)**
  - [x] Instalar `react-markdown`, `remark-gfm`, `remark-breaks` no `frontend/`
  - [x] Criar `Markdown.tsx` com mapeamento de componentes (h1–h4, listas, tabela, code, links `target="_blank" rel="noopener noreferrer"`)
  - [x] Substituir renderização de texto em `ChatPage.tsx` (apenas mensagens do assistente)
  - [x] Estilos `.markdown-body` em `App.css`
  - [x] Teste unitário do componente (vitest + testing-library: 6 testes — lista, link seguro, tabela GFM, sem execução de HTML cru)
  - [x] Teste manual no navegador: resposta real com negrito/itálico renderizada sem marcadores `**`/`###` visíveis; feedback 👍 funcional
- [x] **T7.2 — Fontes clicáveis com trecho em destaque (RF2-02)**
  - [x] Verificado em runtime (payload Qdrant + navegador) que `url_fonte` vem preenchida nos 4 documentos — sem backend change
  - [x] Link condicional "Ver documento oficial ↗" (`target="_blank" rel="noopener noreferrer"` + `aria-label`) no `MessageCard.tsx`
  - [x] Estilos `.fonte-trecho` (fundo sutil + borda esquerda) e `.fonte-link` em `App.css`
  - [x] Teste unitário do card (vitest + user-event: 3 testes — link seguro, ausência de link sem url, trecho em destaque)
  - [x] Teste manual no navegador: 5 fontes com links corretos (planalto.gov.br e saa.unb.br) e trechos destacados
- [x] **T7.4 — Sessão persistente e histórico ao recarregar (RF2-04, RF2-05)**
  - [x] Backend: `GET /chat/history` lê o estado da thread via `aget_state` e converte `messages` (posse validada por `user_id` do estado: 403 para sessão alheia, 404 para inexistente; `user_email` gravado nos metadados do checkpoint)
  - [x] Backend: testes (5) — 401 sem token, 500 sem grafo, 404 sessão inexistente, histórico próprio na ordem, sessão de outro usuário 403
  - [x] Frontend: helpers de localStorage (`usiedu_token`, `usiedu_user`, `usiedu_session_id:<email>`); `App` restaura sessão na montagem, `ChatPage` restaura histórico via `GET /chat/history` (agentes/fontes omitidos — documentado)
  - [x] Frontend: botão "Nova conversa" (novo id de sessão + limpa mensagens) e tratamento de 401 (`AuthError` limpa storage e redireciona ao login)
  - [x] Proxy Vite (bypass de GET `/chat` serve o SPA) e nginx (`error_page 405 = @spa`) para deep-link/reload; doc 09 seção 2 atualizado com o endpoint/schemas
  - [x] Testes unitários frontend (vitest: 6 testes dos helpers de persistência) e teste manual no navegador: histórico restaurado após reload sem novo login (5/5 critérios)
- [x] **T7.3 — Streaming de respostas via SSE (RF2-03)**
  - [x] Backend: `src/api/chat_stream.py` (`POST /chat/stream`, `StreamingResponse` SSE) + `src/api/chat_common.py` (estado inicial e `RunnableConfig` com `run_id` compartilhados com o `/chat`)
  - [x] Backend: agentes (`academico`/`financeiro`/`documental`) migrados para `astream`; filtro por `langgraph_node` streama só a resposta final (supervisor excluído); eventos `meta` → `token`(s) → `final` (com `answer` para reconciliação) → `error`
  - [x] Backend: 4 testes (`tests/unit/test_chat_stream.py`) — ordem/concatenação dos eventos, 401, 500, evento `error`; `FakeChatModel` ganhou `_stream`/`_astream` determinísticos
  - [x] Frontend: `sendChatStream` (fetch + ReadableStream + parser SSE com buffer) e `ChatPage` com `streaming=true`, cursor piscante, `final` preenche agentes/fontes/`message_id`; fallback para `POST /chat` em erro antes de tokens; AbortController limpo no desmonte
  - [x] Proxy: entrada `/chat/stream` no Vite e `location /chat/stream` no nginx (`proxy_buffering off`, `proxy_cache off`, `X-Accel-Buffering: no`); doc 09 seção 2 atualizado (endpoint + tabela de eventos SSE)
  - [x] Testes unitários frontend (vitest: 4 testes do parser SSE) e teste manual no navegador: cursor visível durante o stream, 191 tokens progressivos sem buffering (direto e via proxy), agentes/fontes/feedback ao final, 👍 funcional, histórico persiste após reload

**DoD da sprint:** chat com formatação rica, fontes clicáveis, streaming e histórico persistente; suíte completa verde.

---

## Sprint 8 — Avaliação Contínua (PRD v2)

- [x] **T8.1 — Exportar 👎 para o dataset de avaliação**
  - [x] `scripts/export_feedback_to_eval.py` (CLI `--db`/`--out`/`--checkpointer-db`/`--dry-run`): lê só `rating='down'`, deduplica por `message_id` (reexecutar não duplica — verificado: 2ª execução = 0 novos) e anexa a `src/evaluation/feedback_negativo.jsonl` (dataset versionado, commitado)
  - [x] Pergunta e resposta rejeitada recuperadas do checkpointer: metadados do checkpoint trazem o `message_id` da execução; snapshot mais recente com o id contém a última `HumanMessage` (pergunta) e `AIMessage` (resposta); sem checkpoint disponível, exporta com `question: null`
  - [x] `run_ragas.py`: parâmetro `feedback_path`/CLI `--feedback`; casos com pergunta são reexecutados no grafo e comparados com a rejeitada (Jaccard ≥ 0,95 → "repete resposta rejeitada"; abaixo → "alterada — revisão manual"); `question: null` contabilizado como pulado; casos fora do agregado Ragas principal
  - [x] Relatório ganha seção "Casos de feedback negativo (T8.1)" — validado com 👎 real (similaridade 0,06 → resposta alterada)
  - [x] Testes: 8 em `tests/unit/test_export_feedback.py` (filtro down, idempotência, dry-run, JSONL válido, recuperação via checkpointer real em tmp, sessão inexistente, CLI) + 5 em `tests/unit/test_evaluation.py` (Jaccard, seção vazia/com casos, reavaliação, pulo sem pergunta)
  - [x] Fluxo documentado em `docs/04-piloto-e-roadmap.md` seção 3.1 (item 5)
- [ ] **T8.2 — Página de satisfação `/insights`**

**DoD da sprint:** cada 👎 vira caso de regressão automático; satisfação visível em `/insights`.

---

## Regras de execução (para qualquer implementador)

1. **Uma tarefa por vez**; microtarefas são commits.
2. **Teste antes do polish**: funcionalidade só é dada como pronta com teste.
3. **Nunca ampliar escopo**: requisitos fora do PRD vão para a lista de backlog, não para o código.
4. **Bloqueio > improviso**: se uma decisão não está documentada, registrar a dúvida e parar — não inventar.
5. Cada sprint encerra com: `ruff check` limpo, `pytest` verde, README atualizado se necessário.
6. **Checklists sempre atualizados (regra obrigatória)**:
   - Ao concluir qualquer tarefa/microtarefa, marcar o checkbox correspondente **imediatamente**
     (no mesmo commit da entrega, nunca "depois").
   - Os checklists são a **fonte única de verdade do progresso**: doc 08 (sprints/tarefas),
     doc 04 seção 5 (critérios de aceite) e doc 07 seção 7 (gate de entrega).
   - Se uma tarefa mudar de escopo, for adiada ou cancelada, atualizar o item com a nova
     situação (ex.: `[~] adiada para Fase 2 — motivo`) em vez de deixá-la ambígua.
   - Ao iniciar qualquer sessão de trabalho, **ler primeiro o estado atual dos checklists**
     para saber exatamente onde o projeto parou.
7. **Verificação antes de declarar "pronto" (regra obrigatória, em camadas)**:
   - **Camada 1 — determinística (sem tokens):** rodar `pytest`, `ruff check` e smoke test
     do que foi alterado; todos verdes.
   - **Camada 2 — autorevisão direcionada:** revisar **apenas o diff da tarefa** contra o
     DoD dela e os RFs citados — nunca reanalisar o projeto inteiro.
   - **Camada 3 — evidência:** só marcar o checkbox após registrar a evidência (saída dos
     testes) no commit ou no relatório da tarefa. "Pronto" sem evidência = não pronto.
8. **Recomendação de modelo antes de cada tarefa (regra obrigatória)**:
   - Antes de iniciar qualquer tarefa/microtarefa, o assistente deve apresentar **3 opções
     de modelos LLM disponíveis no Qoder** para executá-la, com a indicação da recomendada.
   - A recomendação segue a classificação complexidade × custo de tokens:
     - **Tarefa simples** (boilerplate, config, testes repetitivos) → modelos baratos que
       executem corretamente;
     - **Tarefa média** (implementação padrão) → modelos intermediários;
     - **Tarefa complexa** (lógica de orquestração, debug difícil, arquitetura de prompts,
       revisões críticas) → modelos premium (ex.: Qwen 3.8 Max via promoção, modo Ultimate,
       Kimi-K3) — ver multiplicadores reais do Qoder no doc 09 seção 10.
   - Considerar sempre promoções ativas (ex.: Qwen 3.8 Max via promoção) e cotas restantes
     (doc 09 seção 10). A decisão final é sempre do usuário.
