# Pipeline de RAG e Infraestrutura

> Detalha o pipeline de RAG híbrido avançado (Anthropic Contextual Retrieval + Parent-Document + CRAG + Lost in the Middle Reordering), o banco vetorial, os MCP servers,
> a estratégia de cache semântico com warmup, a avaliação de qualidade contínua e a infraestrutura em nuvem.

---

## 1. Pipeline de RAG de Alta Precisão

### 1.1 Ingestão, Contextual Retrieval e Parent-Document (Small-to-Big)

```
Documentos-fonte                Pipeline                        Vector DB
──────────────                  ────────                        ─────────
Regimento UnB          ┐
Calendário 2026.2      │   extração     chunking        embedding
Guia do Servidor       ├──► (PDF/HTML) ─► Contextual ───► modelo ──► Qdrant
LDB                    │               + Parent-Doc     local       coleções:
                       ┘               (Anthropic)      (batch)     academico,
                                                                    institucional
```

**Decisões do pipeline de ingestão:**

| Etapa | Escolha | Justificativa |
|---|---|---|
| Extração | PyMuPDF / Trafilatura | Suporta PDFs e HTMLs institucionais com detecção de encoding (UTF-8 / Latin-1) |
| **Contextual Retrieval** | Prefixo contextual Anthropic (`_build_context_prefix`) | Ancoragem de metadados pai reduz em até 49% as falhas de recuperação |
| **Parent-Document** | Chunks filhos com `parent_text` preservado nos metadados | Alta sensibilidade na busca vetorial mantendo o contexto pai íntegro |
| Chunking | Semântico por seção, 500–800 tokens, overlap 15% | Preserva coerência de artigos de regimento e normas |
| Metadados | documento, seção, página, data de vigência, público-alvo, parent_text | Filtragem por perfil (student/staff), Self-Querying e citação oficial |
| Embeddings | **FastEmbed / sentence-transformers** (ONNX local em batch) | Custo zero, sem rate limit, minutos mesmo em CPU |
| Coleções | Separadas por domínio (`academico`, `institucional`, `carreira`) | Permite isolamento estrito por perfil de usuário |

#### 1.1.1 Funcionamento do Contextual Retrieval & Parent-Document
Implementado no `DocumentChunker` (`src/rag/chunker.py`), cada fragmento gerado é automaticamente enriquecido com um prefixo estruturado derivado da hierarquia do documento pai, além de armazenar o texto completo da seção pai:
```text
Este trecho pertence ao documento 'Regimento Geral da UnB' da instituição 'UnB', seção 'Art. 15'.

[Texto original do artigo fatiado para indexação precisa...]
```
- **Vetorização e BM25:** Operam sobre o texto contextualizado (`chunk.text`), garantindo que buscas semânticas encontrem trechos mesmo quando pronomes ou referências explícitas à instituição estão ausentes no parágrafo isolado.
- **Hierarchical Parent Context:** O texto integral da seção é retido em `chunk.metadata["parent_text"]` para expansão de contexto durante a geração da resposta.
- **Exibição e Citação:** O texto puro original é preservado em `chunk.metadata["original_text"]` para exibição limpa nas interfaces.

### 1.2 Performance de Ingestão e Otimizações

| Técnica | Como | Ganho |
|---|---|---|
| **Modelo local, não API** | FastEmbed (ONNX/quantizado, otimizado p/ Qdrant) ou sentence-transformers | Sem rate limit nem custo por token; roda offline |
| **Batching** | `encode()` em lotes de 64–256 chunks | Uso pleno de CPU/GPU; ~10–50x vs. 1 chunk por vez |
| **Idempotência por hash** | ID do chunk = hash do conteúdo (RNF-07) | Reexecuções nunca re-embeddam chunks inalterados |
| **Cache de embeddings em disco** | Hash → vetor já calculado (SQLite/arquivo) | Troca de coleção/Qdrant não re-embeda nada |
| **Ingestão incremental** | `manifest.json` com checksum por documento | Só documentos novos/alterados são processados |

### 1.3 Recuperação Online, Self-Querying, Re-ranking e Reorder (Lost in the Middle)

```
Pergunta do Usuário
        │
        ▼
┌───────────────────────────┐     ┌────────────────────────┐     ┌──────────────┐
│ Query Rewriter &          │────►│ Busca Híbrida          │────►│ Re-ranking   │
│ Self-Querying Metadata    │     │ Qdrant (Filtro) + BM25 │     │ Cross-Encoder│
└───────────────────────────┘     │ (Top-20)               │     │ (Top-5)      │
                                  └────────────────────────┘     └──────┬───────┘
                                                                        ▼
                                                                 ┌──────────────┐
                                                                 │ CRAG Grader  │
                                                                 │ (Score >=.35)│
                                                                 └──────┬───────┘
                                                                        ▼
                                                                 ┌──────────────┐
                                                                 │ Reorder      │
                                                                 │ [1,3,5,4,2]  │
                                                                 └──────┬───────┘
                                                                        ▼
                                                         Contexto Relevante Balanceado
```

**Técnicas de precisão e salvaguarda (anti-alucinação):**
1. **Query Rewriting & Resolução Coreferencial (`src/rag/query_rewriter.py`):** Analisa o histórico multi-turno para reescrever perguntas contextuais (*"E até quando posso pagar ele?"* $\rightarrow$ *"Até quando posso pagar o boleto de graduação?"*) antes de consultar os índices.
2. **Self-Querying & Extração de Metadados (`extract_query_metadata`):** Identifica referências a normas e documentos específicos na query do usuário e aplica filtros booleanos pré-HNSW no Qdrant, reduzindo ruídos entre documentos.
3. **Busca Híbrida & RRF:** Vetorial denso (Qdrant) + Léxico esparso (BM25) fundidos via Reciprocal Rank Fusion ($k=60$).
4. **Re-ranking Cross-Encoder:** `BAAI/bge-reranker-v2-m3` reordena os candidatos avaliando os pares query-documento. O checkpoint anterior (`bge-reranker-base`) foi substituído por medição: em prosa jurídica em português ele atribuía score alto a artigos irrelevantes e baixo à passagem que respondia a pergunta, invertendo o ranqueamento (detalhe na nota T10.2 de `docs/08`).
5. **Corrective RAG Grader (`src/rag/crag_grader.py`):** Descarta candidatos com relevância $< 0.05$ (`min_relevance_score`) para não injetar ruído no prompt do LLM. **Limitação medida:** sobre o corpus real a distribuição de scores de ouro e de ruído se sobrepõe (ouro 0.0001–0.995, ruído até 0.9927), então o threshold funciona como poda de candidatos claramente não relacionados, **não** como garantia de recusa — as recusas corretas de `sem_resposta`/`fora_de_escopo` vêm do prompt do agente, não do grader.
6. **Mitigação de Lost in the Middle (`reorder_context`):** Reorganiza os chunks aprovados no padrão `[1º, 3º, 5º, 4º, 2º]`, posicionando os documentos mais importantes nas regiões de maior atenção do LLM (início e fim do prompt).
7. **Grounding Obrigatório:** O agente responde apenas sobre os chunks aprovados no contexto; sem contexto útil, declara honestamente não dispor da informação.

**Evidência de calibração do threshold (Sprint 10.2):** varredura sobre as 30 perguntas do dataset sintético, contando apenas os casos em que nenhum candidato aprovado pelo grader carrega o documento ouro no top-5.

| Checkpoint / threshold | Perguntas respondíveis sem ouro no top-5 | Falsos-aceites (categorias sem ouro) |
|---|---|---|
| `bge-reranker-base` @ 0.35 (configuração antiga) | 8 | 4 / 9 |
| `bge-reranker-v2-m3` @ 0.05 (adotado) | 7 | 4 / 9 |
| `bge-reranker-v2-m3` @ 0.35 | 9 | 2 / 9 |

Manter 0.35 após a troca do modelo era a intuição "mais rígida" e saiu-se pior nas duas curvas: 9 perguntas respondíveis ficavam sem nenhuma fonte aprovada. O ponto adotado domina o antigo (mais cobertura com o mesmo número de falsos-aceites); operar a curva em 0.15–0.2 é a alternativa se a prioridade passar a ser precisos de recusa.

---

## 2. Vector DB — Qdrant

| Aspecto | Decisão |
|---|---|
| Implantação no piloto | Docker Compose (junto com a API) |
| Coleções | `academico`, `institucional` (piloto); `carreira`, `disciplinas` (roadmap) |
| Distância | Cosine |
| Alternativa documentada | pgvector — caso a empresa prefira Postgres único |

---

## 3. MCP (Model Context Protocol)

### 3.1 Onde o MCP entra
Dados **estruturados** (tabelas, registros) não vão para o vector DB — são expostos via MCP servers:

| MCP Server | Fonte (piloto) | Tools expostas |
|---|---|---|
| `processos-mcp` | SQLite com processos/chamados internos | `listar_processos`, `detalhar_processo`, `abrir_solicitacao` |
| `academico-mcp` *(roadmap)* | API acadêmica mockada | `get_notas`, `get_faltas`, `get_matricula` |

---

## 4. Estratégia de Modelos (LLM)

A plataforma usa uma **camada provider-agnostic** (interface LangChain `BaseChatModel`):
`USIEDU_LLM_PROVIDER` seleciona o provedor ativo. O piloto roda **100% via OpenCode Go** (custo zero);
a integração com Gemini/Vertex AI fica implementada e documentada como suporte adicional da mesma camada.

| Função no piloto | Modelo | Por quê (custo/benefício) |
|---|---|---|
| Roteamento/Supervisor | **DeepSeek V4 Flash** | O mais barato da assinatura ($0.14/$0.28 por 1M tokens), cota de $60/mês |
| Agentes especialistas + consolidação | **Kimi K2.7 Code** | Modelo de alto nível, forte em raciocínio e tool calling; cota de $60/mês |
| Alternativa para respostas longas | GLM-5.1 | Boa qualidade geral, mesma cota generosa de $60/mês |

---

## 5. FinOps: Semantic Cache & Cache Warmup

### 5.1 Semantic Cache Vetorial
Consultas institucionais e públicas passam primeiro pelo cache semântico (SQLite local ou Redis):
- **Cálculo de Similaridade:** Embeddings locais e similaridade de cosseno com threshold configurado em **0.92**.
- **Latência & Custo:** Consultas cacheadas retornam em **< 15ms** com **custo zero de tokens**.

### 5.2 Cache Warmup Automatizado (`scripts/warmup_cache.py`)
Script CLI que pré-popula o cache semântico com as 40 perguntas institucionais mais frequentes:
```bash
python scripts/warmup_cache.py --dataset knowledge_base/perguntas_frequentes.json
```

---

## 6. Avaliação Contínua: Geração Sintética & Ragas

### 6.1 Geração Sintética Automatizada (`scripts/generate_synthetic_testset.py`)
O UsiEdu implementa um gerador sintético de datasets baseado nos documentos da base de conhecimento:
- Gera automaticamente 50 casos de teste balanceados:
  - **40% Perguntas Diretas (Direct):** Baseadas em artigos de normas e calendário.
  - **30% Perguntas de Raciocínio (Reasoning):** Interpretação de requisitos e regras.
  - **20% Perguntas Multi-Contexto (Multi-Context):** Articulação entre diferentes seções/documentos.
  - **10% Fora de Escopo e Sem Resposta:** Validação de recusa segura e honestidade.

### 6.2 Quality Gate de Ragas (LLM-as-a-Judge)
```bash
python scripts/run_ragas.py --ci-gate --min-score 0.80
```
- **Faithfulness $\ge 0.85$:** A resposta não contém informações fora do contexto.
- **Answer Relevance $\ge 0.80$:** A resposta aborda diretamente a intenção da pergunta.

---

## 7. Guardrails Anti-Injection (T9.3)

| Camada | Onde | Comportamento |
|---|---|---|
| **1. Ingestão** | `src/rag/ingest.py` | Chunks com padrões de injeção são marcados e descartados |
| **2. Entrada** | `/chat` e `/chat/stream` | PII Masking e detecção de ataques com flags no LangSmith |
| **3. Saída** | Após consolidação | `validate_answer` bloqueia vazamento de system prompt ou eco de jailbreak |

---

## 8. Deploy — Azure Container Apps (T9.4)

O ambiente em nuvem executa 3 Container Apps integrados:
- **Frontend:** Nginx + React (Ingress externo HTTPS)
- **API Backend:** FastAPI + LangGraph (2 vCPUs, 4 GiB de memória)
- **Qdrant Vector DB:** Armazenamento vetorial persistido em Azure Files
