# Pipeline de RAG e Infraestrutura

> Detalha o pipeline de RAG compartilhado, o banco vetorial, os MCP servers,
> a estratégia de memória, a avaliação de qualidade e a observabilidade.

---

## 1. Pipeline de RAG

### 1.1 Ingestão (offline)

```
Documentos-fonte                Pipeline                        Vector DB
──────────────                  ────────                        ─────────
Regimento UnB          ┐
Calendário 2026.2      │   extração     chunking     embedding
Guia do Servidor       ├──► (PDF/HTML) ─► semântico ─► modelo ──► Qdrant
LDB                    │               (~500-800     local       coleções:
                       ┘                tokens,       (batch)     academico,
                                        overlap 15%)              institucional
```

**Decisões do pipeline:**

| Etapa | Escolha | Justificativa |
|---|---|---|
| Extração | `unstructured` / PyMuPDF | Suporta PDFs institucionais com tabelas |
| Chunking | Semântico por seção, 500–800 tokens, overlap 15% | Preserva coerência de artigos de regimento |
| Metadados | documento, seção, página, data de vigência, público-alvo | Filtragem por perfil e citação de fonte |
| Embeddings | **modelo local via FastEmbed ou sentence-transformers** (ONNX, batch) | Custo zero, sem rate limit, minutos mesmo em CPU |
| Coleções | Separadas por domínio (`academico`, `institucional`, `carreira`, `disciplinas`) | Permite filtrar por perfil de usuário |

> Fontes abertas que alimentam a base de conhecimento do piloto: ver `05-fontes-base-conhecimento.md`.

### 1.2 Performance de ingestão (embedding rápido)

**Contexto:** em projetos com embeddings via API externa, a ingestão pode levar dias
(rate limiting, latência por request, reprocessamento total a cada execução).
A UsiEdu elimina esse problema por design:

| Técnica | Como | Ganho |
|---|---|---|
| **Modelo local, não API** | FastEmbed (ONNX/quantizado, otimizado p/ Qdrant) ou sentence-transformers | Sem rate limit nem custo por token; roda offline |
| **Batching** | `encode()` em lotes de 64–256 chunks | Uso pleno de CPU/GPU; ~10–50x vs. 1 chunk por vez |
| **Idempotência por hash** | ID do chunk = hash do conteúdo (RNF-07) | Reexecuções nunca re-embeddam chunks inalterados |
| **Cache de embeddings em disco** | Hash → vetor já calculado (SQLite/arquivo) | Troca de coleção/Qdrant não re-embeda nada |
| **Ingestão incremental** | `manifest.json` com checksum por documento | Só documentos novos/alterados são processados |
| **GPU opcional** | Se disponível, mesma interface | 10–20x adicional para bases grandes |

**Expectativa realista do piloto:** o núcleo mínimo (4 documentos ≈ 300–800 chunks)
indexa em **minutos** em CPU comum — nunca horas. Se uma execução demorar mais que
~10 min, há algo errado (ex.: download de modelo na primeira execução é normal;
as seguintes usam cache local).

**Se um dia usarmos API de embeddings (produção em escala):** concorrência assíncrona
com semáforo, endpoint de batch do provedor e checkpointing retomável — nunca
processamento sequencial síncrono.

### 1.3 Recuperação (online)

```
pergunta do usuário
        │
        ▼
┌─────────────────┐     ┌────────────────┐     ┌──────────────┐
│ reescrita de    │────►│ busca híbrida  │────►│ reranking    │
│ query (se       │     │ vetor + BM25   │     │ (cross-      │
│ necessário)     │     │ top-20         │     │ encoder)     │
└─────────────────┘     └────────────────┘     │ top-5        │
                                               └──────┬───────┘
                                                      ▼
                                        filtro por perfil (estudante/staff)
                                                      │
                                                      ▼
                                        contexto para o agente especialista
```

**Técnicas de precisão (anti-alucinação — requisito da vaga):**
1. **Busca híbrida**: vetorial (semântica) + BM25 (palavras-chave) — essencial para números de artigos de lei/regimento.
2. **Reranking**: cross-encoder local (ex.: `bge-reranker`) reordena os top-20 antes de enviar ao LLM — custo zero.
3. **Filtro por perfil**: estudante nunca vê documentos internos, e vice-versa (metadados).
4. **Grounding obrigatório**: o prompt do agente instrui a responder apenas com o contexto recuperado e citar fonte; sem fonte, o agente admite não saber.

---

## 2. Vector DB — Qdrant

| Aspecto | Decisão |
|---|---|
| Implantação no piloto | Docker Compose (junto com a API) |
| Coleções | `academico`, `institucional` (piloto); `carreira`, `disciplinas` (roadmap) |
| Distância | Cosine |
| Alternativa documentada | pgvector — caso a empresa prefira Postgres único |

**Índices e otimizações previstas:** payload indexing para filtros por `perfil` e `vigência`; quantização se a base crescer (tokenomics/latência — diferencial da vaga).

---

## 3. MCP (Model Context Protocol)

### 3.1 Onde o MCP entra

Dados **estruturados** (tabelas, registros) não vão para o vector DB — são expostos via MCP servers:

| MCP Server | Fonte (piloto) | Tools expostas |
|---|---|---|
| `processos-mcp` | SQLite com processos/chamados internos | `listar_processos`, `detalhar_processo`, `abrir_solicitacao` |
| `academico-mcp` *(roadmap)* | API acadêmica mockada | `get_notas`, `get_faltas`, `get_matricula` |

### 3.2 Justificativa

- Demonstra o **diferencial MCP** da vaga com caso de uso real.
- Padroniza como futuros sistemas da Cruzeiro do Sul (ERP, CRM acadêmico) seriam conectados aos agentes sem código custom por agente.

---

## 4. Estratégia de Modelos (LLM)

A plataforma usa uma **camada provider-agnostic** (interface LangChain `BaseChatModel`):
`USIEDU_LLM_PROVIDER` seleciona o provedor ativo. O piloto roda **100% via OpenCode Go** (custo zero);
a integração com Gemini/Vertex AI fica implementada e documentada como suporte adicional da mesma
camada (aderência ao ecossistema Google), sem ser o motor do piloto.

### 4.1 OpenCode Go (motor do piloto — custo zero)

Assinatura OpenCode Go ($10/mês, limites em valor de uso) com endpoint OpenAI-compatível
(`https://opencode.ai/zen/go/v1/chat/completions`). Modelos escolhidos por uso:

| Função no piloto | Modelo | Por quê (custo/benefício) |
|---|---|---|
| Roteamento/Supervisor | **DeepSeek V4 Flash** | O mais barato da assinatura ($0.14/$0.28 por 1M tokens), cota de $60/mês — ideal para chamadas volumosas e determinísticas |
| Agentes especialistas + consolidação | **Kimi K2.7 Code** | Modelo de alto nível, forte em raciocínio e tool calling; cota de $60/mês (~6.750 req/mês) — melhor equilíbrio qualidade/custo |
| Alternativa para respostas longas | GLM-5.1 | Boa qualidade geral, mesma cota generosa de $60/mês |

> Modelos **descartados** por custo/benefício: Kimi K3, Grok 4.5 e Qwen3.8 Max
> (cota de apenas $15/mês). Modelos com cota $60/mês multiplicam o rendimento da assinatura em 6x.

### 4.2 Suporte a Gemini (via camada provider-agnostic)

A mesma arquitetura suporta Gemini via `langchain-google-vertexai` trocando apenas variáveis
de ambiente — sem alterar código de agentes. No piloto isso fica como **integração documentada**
(código pronto, configuração opcional), demonstrando a capacidade exigida pela vaga sem
incorrer em custo de API: a apresentação mostra o provider-agnostic em ação.

---

## 5. Memória de Longo Prazo

| Camada | Mecanismo | Uso |
|---|---|---|
| **Sessão** | Checkpointer do LangGraph (SQLite) | Retomar conversa no ponto certo |
| **Perfil persistente** | Store (SQLite no piloto) | Tutor: dificuldades, erros em quizzes, preferências; Jornada: curso, período, histórico de solicitações |
| **Sumarização** | Janela deslizante + resumo periódico | Sessões longas sem estourar contexto (tokenomics) |

Exemplo de entrada no Store do Tutor:
```json
{
  "user_id": "ana-123",
  "namespace": "perfil_aprendizado",
  "value": {
    "topicos_dificeis": ["limites", "derivadas"],
    "acertos_quiz": 0.62,
    "estilo_preferido": "exemplos práticos",
    "atualizado_em": "2026-08-05T10:00:00Z"
  }
}
```

---

## 6. Avaliação de Qualidade

### 6.1 Métricas do piloto (Ragas)

| Métrica | O que mede | Meta sugerida |
|---|---|---|
| `faithfulness` | Resposta fiel ao contexto recuperado (sem alucinação) | ≥ 0.90 |
| `context_precision` | Os trechos recuperados são relevantes? | ≥ 0.80 |
| `context_recall` | Recuperamos tudo que era necessário? | ≥ 0.80 |
| `answer_relevancy` | A resposta responde à pergunta? | ≥ 0.85 |

### 6.2 Dataset de avaliação

- ~30 perguntas (15 estudante / 15 funcionário) com respostas de referência, cobrindo:
  - Perguntas diretas com resposta no documento.
  - Perguntas compostas (multi-agente).
  - Perguntas **sem resposta** nos documentos (testa o "não sei" honesto).
  - Perguntas fora de escopo (testa guardrails).

### 6.3 Qualidade conversacional (métrica da vaga)

LLM-as-judge avalia amostra de conversas em: **clareza, retenção de contexto e assertividade** — as três dimensões citadas explicitamente na descrição da vaga.

### 6.4 Frameworks de avaliação — papel de cada um

| Ferramenta | Papel no piloto | Observação |
|---|---|---|
| **Ragas** | ✅ Principal: métricas de RAG (faithfulness, context precision/recall, answer relevancy) | Não acelera ingestão nem embeddings — avalia qualidade da resposta |
| **LangSmith Datasets & Experiments** | ✅ Complementar: mesmo dataset rodado como experimento no LangSmith | Integra com o tracing já escolhido; regressão visível na plataforma |
| **LLM-as-judge** | ✅ Qualidade conversacional (6.3) | Implementado via LangSmith evaluators ou script próprio |
| TruLens | Roadmap/menção na apresentação | Citado nos diferenciais da vaga; demonstrar conhecimento sem adicionar complexidade ao piloto |
| DeepEval | Alternativa se Ragas falhar | Swap simples: mesmo dataset, métricas equivalentes |

> Nota: avaliação e ingestão são problemas independentes — a seção 1.2 resolve velocidade
de embedding; esta seção 6 resolve medição de qualidade.

---

## 7. Observabilidade

### 7.1 Stack do piloto

| Camada | Ferramenta | O que captura |
|---|---|---|
| Tracing de LLM | **LangSmith** (cloud, free tier) | Cadeia completa: supervisor → agentes → retriever → LLM |
| Métricas de API | Prometheus + Grafana | Latência p50/p95, taxa de erro, throughput |
| Logs | Estruturados (JSON) | Correlação com run_id do LangSmith |

### 7.2 Métricas-chave (KPIs do dashboard Grafana)

- **Latência**: tempo até primeiro token e tempo total por perfil de pergunta.
- **Tokens**: consumo por conversa e por agente (tokenomics).
- **Qualidade**: scores Ragas por execução de avaliação; taxa de respostas "não sei".
- **Saúde**: erros de tool calling, falhas de recuperação RAG, disponibilidade.

---

## 8. Ferramentas de Desenvolvimento e Qualidade

| Ferramenta | Papel | Configuração |
|---|---|---|
| **Ruff** | Lint + formatação do código Python (substitui flake8/black/isort) | `ruff check` + `ruff format` no pré-commit e CI |
| **pytest** | Testes unitários e de integração | Testes de roteamento do supervisor, retriever, tools mockadas e API (sem chamar LLM real nos testes unitários — mocks/fakes) |
| **pytest-asyncio** | Testes assíncronos | Cobertura do grafo LangGraph e endpoints FastAPI |
| **MkDocs (Material)** | Site da documentação | `mkdocs.yml` gerando site navegável a partir de `docs/` |

**Estratégia de testes (pirâmide):**

```
        ╱  e2e (demo manual)  ╲          vídeo de demo / critérios de aceite
       ╱  integração (pytest)   ╲        grafo completo com LLM mockado,
      ╱                           ╲       API FastAPI via httpx
     ╱  unitários (pytest)          ╲    supervisor, chunker, retriever,
    ╱─────────────────────────────────╲  tools, guardrails
```

- Testes **não dependem de chave de API**: o LLM Gemini é substituído por fake determinístico nos testes.
- Metas: cobertura ≥ 80% nos módulos de orquestração/RAG; `ruff check` sem erros no CI.

---

## 9. Estrutura do repositório (proposta)

```
usiedu/
├── docs/                        # esta documentação (fonte do MkDocs)
├── src/
│   ├── api/                     # FastAPI: auth, sessões, chat
│   ├── orchestration/           # grafo LangGraph, supervisor, estado
│   ├── agents/                  # acadêmico, financeiro, documental...
│   ├── rag/                     # ingestão, recuperação, reranking
│   ├── tools/                   # tool calling (APIs mockadas)
│   ├── mcp_servers/             # processos-mcp
│   └── evaluation/              # dataset + scripts Ragas
├── frontend/                    # React + Vite (TypeScript): chat web
├── tests/                       # pytest: unitários + integração
├── knowledge_base/              # documentos-fonte (sintéticos/públicos)
├── mkdocs.yml                   # configuração do site de documentação
├── pyproject.toml               # deps, ruff e pytest configurados aqui
├── docker-compose.yml           # API + frontend + Qdrant + Grafana
└── README.md                    # quickstart + link para demo
```

## 10. Deploy público — Azure Container Apps (T9.4)

O deploy público usa três Container Apps no mesmo ambiente: **frontend**
(externo, HTTPS), **API** (ingress interno) e **Qdrant** (ingress interno). O
frontend nginx faz o proxy dos caminhos de API para `http://<nome-da-api>`;
assim o navegador usa uma única origem e o backend não fica exposto à internet.

O estado do Qdrant fica em Azure Files. Sessões do LangGraph, feedback e cache
semântico ficam em PostgreSQL Flexible Server gerenciado: SQLite/WAL sobre
Azure Files pode bloquear operações concorrentes. A ingestão é um Container
Apps Job manual: ela usa a mesma imagem da API e executa
`scripts/ingest_knowledge_base.py` apenas depois que o Qdrant estiver
disponível.

A API recebe **2 vCPUs e 4 GiB** no manifesto. Os modelos locais de embeddings
e reranking são inicializados no startup; 2 GiB podem causar encerramento do
contêiner com código 137 e interromper o streaming. O job de ingestão continua
em 2 GiB, pois não carrega o reranker.

Os artefatos versionados ficam em `infra/azure/`:

- `registry.bicep`: Azure Container Registry Basic para as imagens privadas.
- `main.bicep`: ambiente Container Apps, Log Analytics, Azure Files, os três
  serviços e o job de ingestão.
- `deploy.ps1`: cria o resource group/registro, constrói e publica imagens,
  provisiona os serviços e informa a URL pública.

As variáveis obrigatórias em produção são configuradas como secrets ou env vars
no template: `JWT_SECRET`, `OPENCODE_GO_API_KEY`, `OPENCODE_GO_BASE_URL`,
`LANGSMITH_*`/`LANGCHAIN_*`, `QDRANT_URL`, `USIEDU_DATABASE_URL`,
`USIEDU_CACHE_*`, `USIEDU_RATE_*` e
`USIEDU_CORS_ORIGINS`. Nunca reutilizar o segredo JWT local e nunca versionar
valores reais em `.env` ou Bicep.

## 11. Guardrails contra prompt injection (T9.3)

Defesa em três camadas, implementada em `src/security/guardrails.py` com
heurísticas determinísticas (regex em constantes nomeadas) — **testável sem LLM**.

| Camada | Onde | Comportamento |
|---|---|---|
| **1. Ingestão** | `src/rag/ingest.py` | Cada chunk passa por `detect_injection`; chunks sinalizados ganham `suspicious=true` e são **excluídos do índice** com log de auditoria (`guardrail_triggered`, `origem=ingest`) |
| **2. Entrada do usuário** | `POST /chat` e `/chat/stream` | O mesmo detector roda na pergunta; se sinalizada, o trace recebe `flagged=true` + `injection_patterns`. A pergunta **não é bloqueada** (risco de falso positivo), apenas observada |
| **3. Saída** | após o grafo, antes de responder | `validate_answer` detecta eco do prompt de sistema, eco de jailbreak ou tentativa de mudança de comportamento ("a partir de agora..."); resposta insegura é substituída por `RESPOSTA_SEGURA_PADRAO` e o evento `guardrail_triggered` é registrado no log JSON e no LangSmith (best-effort) |

**Decisões de política:**
- Respostas bloqueadas pelo guardrail **nunca alimentam o cache semântico** (T9.2).
- No streaming os tokens já emitidos não podem ser desfeitos: o evento `final`
  carrega a resposta segura e o cliente reconcilia o texto pelo campo `answer`.
- Fragmentos de detecção de eco são derivados dos prompts reais na importação
  (sem dessincronização).
- Fixture de teste: `tests/fixtures/documento_malicioso.html` (documento com
  injeção embutida).

---

## 11. Decisões em aberto *(para revisão)*

- [ ] Reranker: manter local (`bge-reranker`) ou testar Vertex AI ranking na comparação final?
- [ ] Grafana/Prometheus entram no piloto ou só na Fase 2 (para reduzir complexidade)?

**Decisões já fechadas:**
- ✅ Motor do piloto: **OpenCode Go** (DeepSeek V4 Flash + Kimi K2.7 Code) — Gemini fora do piloto,
  mantido apenas como provider suportado pela camada de abstração.
