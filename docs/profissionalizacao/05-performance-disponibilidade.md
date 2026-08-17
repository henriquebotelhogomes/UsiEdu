# P2 — Performance e disponibilidade

| Campo | Valor |
|---|---|
| Estado | Em andamento — T05.1 concluída; T05.2–T05.5 planejadas |
| Prioridade | P2 |
| Dono | Henrique Botelho Gomes |
| Dependências | [PRD do programa](00-prd-programa.md), [validação P0](01-validacao-piloto.md), `infra/azure/main.bicep`, `frontend/nginx/default.conf.template` |
| Documentos normativos | `PLANO_PROFISSIONALIZACAO.md`; `PRD.v2.md` RNF2-01 e T9.4; `docs/03-rag-e-infraestrutura.md` §§ 1.2, 7 e 10; `docs/04-piloto-e-roadmap.md` § 5; `docs/07-prd-requisitos.md` RNF-01 e RNF-03; `docs/08-plano-execucao.md` T9.4; `docs/09-contratos-tecnicos.md` §§ 2–3 |
| Checklists legados afetados | `docs/08-plano-execucao.md` T9.4; `docs/04-piloto-e-roadmap.md` § 5; `docs/07-prd-requisitos.md` § 7. Não alterar status nesta especificação. |
| Atualizado em | 2026-08-11 |

## 1. Contexto e evidências

O Azure atual configura API com 2 vCPU/4 GiB, mínimo 0 e máximo 1 réplica;
frontend com 0,25 vCPU/0,5 GiB, mínimo 0/máximo 1; Qdrant com 0,5 vCPU/1 GiB e
uma réplica mínima. Embedding e reranker locais são inicializados no startup.
O P0 atribuiu os antigos exit 137 às revisões de API com menos memória; a
revisão 0000013, com 2 vCPU/4 GiB, teve zero eventos 137 na consulta
equivalente.

Na validação de 11/08/2026, login após escala a zero levou cerca de 95 s;
`/health` aquecido mediu 212, 45 e 45 ms. Antes da correção, um cold start
retornou 504 em 81,72 s. O nginx usa 180 s para API e 300 s no streaming.
RNF-01 do piloto define p95 local de pergunta composta inferior a 20 s; PRD v2
define primeiro token inferior a 3 s, mas não há medição Azure atual de TTFT
p95, consumo de memória por modelo, throughput, disponibilidade ou retry.

## 2. Objetivo mensurável

Estabelecer uma linha de base repetível de memória, cold/warm start, primeiro
token, tempo total e falhas para API, embedder e reranker; então validar probes,
timeouts/retries e política de escala contra metas aprovadas. Metas existentes
que devem ser medidas, não presumidas como atingidas, são p95 local <20 s e
primeiro token <3 s. Para o piloto, o SLO mensal provisório é 99% no fluxo
público, excluída manutenção documentada; a carga de referência é cinco
usuários concorrentes e rajada de dez. Ainda não há baseline suficiente para
fixar SLO de primeira resposta/chat.

Para este SLO, uma transação pública é bem-sucedida quando o monitor sintético
conclui login demo e uma interação de chat até resposta final sem erro 5xx; a
taxa mensal é transações bem-sucedidas ÷ transações tentadas fora das janelas
de manutenção documentadas. A fonte será Azure Monitor e/ou GitHub Action
quando configurados; antes disso o SLO é não mensurável, não uma alegação de
conformidade.

## 3. Escopo e não escopo

### Escopo

- Medição Azure de memória/latência de embedder, reranker e fluxo de chat.
- Startup, readiness, liveness e comportamento em cold start.
- Timeout, retry e falha para LLM, Qdrant e PostgreSQL.
- Avaliação de `minReplicas: 0`, aquecimento, imagem/cache/modelo mais leve.

### Não escopo

- Trocar provedor LLM, modelo, arquitetura RAG ou capacidade sem experimento.
- Declarar alta disponibilidade, SLA ou autoscaling além do Container Apps
atual.
- Implementar observabilidade, probes ou mudanças de escala nesta documentação.

## 4. Requisitos e critérios de aceite

| ID | Requisito | Critério de aceite verificável |
|---|---|---|
| RQ-PERF-01 | Métricas devem separar cold/warm, perfil e dependência. | Cada amostra registra revisão, réplicas, modelo, cenário e timestamps sem payload sensível. |
| RQ-PERF-02 | Readiness deve ser rasa: processo, configuração e modelos carregados; saúde de LLM/Qdrant/PostgreSQL deve ser telemetria separada (ou endpoint futuro documentado em `docs/09`). | Readiness não consulta diretamente essas dependências e não flapa; bootstrap local ainda não recebe tráfego antes de processo/configuração/modelos prontos. |
| RQ-PERF-03 | Chamadas LLM, Qdrant e PostgreSQL devem ter timeout, retry e falha explícitos. | Há no máximo um retry com exponential backoff+jitter apenas em operação idempotente; não há retry automático após início de stream ou escrita não idempotente. |
| RQ-PERF-04 | Mudança de escala/aquecimento deve comparar custo e latência. | Experimento controlado registra mesma carga, configuração, custo observável e decisão. |
| RQ-PERF-05 | Não pode haver regressão de disponibilidade conhecida. | Candidato preserva SLO mensal provisório de 99% no fluxo público, excluída manutenção documentada, `/health`, fluxo P0 e ausência de exit 137 sob cenário comparável. |

## 5. Decisões, dependências e riscos

| Tipo | Item | Dono / condição | Mitigação ou próximo passo |
|---|---|---|---|
| Decisão tomada | API tem 2 vCPU/4 GiB; Qdrant mantém uma réplica. | `main.bicep` e P0. | Usar como baseline de experimento. |
| Decisão tomada | `minReplicas: 0` é ativo para API/frontend; timeouts nginx são 180 s/300 s. | Bicep e P0. | Medir custo e experiência antes de mudar. |
| Decisão provisória | SLO mensal de 99%: transações sintéticas bem-sucedidas de login demo + chat final ÷ tentativas fora de manutenção documentada; carga de referência de cinco usuários concorrentes e rajada de dez. | Revisar após T05.1/T05.2 ou mudança relevante de tráfego/arquitetura. | T05.1 pode medir e T05.5 comparar nessa carga; sem Azure Monitor/GitHub Action configurado o SLO é não mensurável, e não fixa ainda SLO de primeira resposta/chat. |
| Decisão provisória | Cold start de login ≤180 s e health aquecido p95 ≤500 ms, coerentes com a P0. | Revisar após baseline repetível. | T05.1/T05.2 registram amostras; primeira resposta/chat só ganha limite após medição suficiente. |
| Decisão provisória | No máximo um retry com exponential backoff+jitter para operação idempotente; zero retry automático após início de stream ou escrita não idempotente. | Revisar após matriz de falhas e testes negativos. | T05.3 pode especificar/testar a matriz; qualquer mudança de runtime permanece P2. |
| Decisão provisória | Readiness é rasa (processo, configuração e modelos carregados); dependências são observadas em telemetria separada. Um endpoint adicional só pode ser criado após registrar seu contrato em `docs/09`. | Revisar se a plataforma exigir semântica diferente comprovada. | T05.4 pode desenhar/testar sem acoplar readiness a LLM/Qdrant/PostgreSQL; não declara endpoint novo nesta etapa. |
| Risco | Aquecimento ou réplica mínima reduz cold start e aumenta custo. | Crédito Azure é limitado. | Comparar cenário idêntico e registrar custo. |
| Risco | Retry amplifica carga/duplicação. | Chat e stream chamam dependências externas. | Limite, idempotência e teste de falha antes de habilitar. |

## 6. Plano técnico

A futura telemetria deve correlacionar revisão Azure, réplicas, cold/warm,
TTFT, total, memória e erro sem registrar pergunta, token ou segredo. A
medição inicia com `/health`, login e chat, pois P0 já fornece baseline dos dois
primeiros. T05.1 mede a primeira resposta/chat antes de definir seu SLO; o
cenário inicial usa cinco usuários concorrentes e rajada de dez.

Probes e políticas de timeout/retry devem respeitar o proxy já existente:
180 s API e 300 s SSE não são metas de produto, apenas limites observados.
Readiness não consulta LLM, Qdrant ou PostgreSQL, para evitar flapping; um
endpoint ou telemetria separados relatam tais dependências. Retry automático é
único, com exponential backoff+jitter, apenas para operação idempotente, e não
ocorre depois do primeiro token nem em escrita não idempotente.
Qualquer mudança deve preservar o fallback de `/chat`, não expor API e possuir
rollback de revisão/configuração. Não há variável, endpoint ou migração nova
autorizada por esta especificação.

O protocolo versionado `src/observability/performance_protocol_v1.json` fixa a
carga de cinco usuários concorrentes e rajada de dez, os cenários `health`,
`login` e `chat`, e os campos sanitizados por amostra: revisão, réplicas,
modelos, timestamps, status HTTP, latências total/TTFT, estado agregado das
dependências e sinal de exit 137. O validador
`src/observability/performance_protocol.py` exige amostras cold e warm,
separa-as deterministicamente e recusa pergunta, resposta, token, segredo,
JWT, e-mail e identificadores de sessão. O autoensaio versionado cobre somente
o schema e não constitui baseline local ou Azure.

O workflow manual protegido
`.github/workflows/measure-azure-performance-baseline.yml` aguarda a API
escalar a zero antes de medir o primeiro `/health` cold. Em seguida, mede login
e uma rajada de dez chats em duas ondas de cinco sessões virtuais concorrentes
que compartilham a conta demo protegida; isso respeita o limite de dez chats
por minuto da conta e não é apresentado como cinco identidades distintas. A
pergunta acadêmica escolhida não é cacheável; o coletor aborta se o stream
indicar `from_cache`. A evidência contém somente métricas sanitizadas, nunca
credencial, JWT, sessão, pergunta ou resposta.

O primeiro baseline Azure, run `32068963046`, foi executado na revisão
`usiedu-api--0000016`, com 2 vCPU, 4 GiB, mínimo de zero e máximo de uma
réplica. A amostra cold de `/health` levou 108156,511 ms (108,157 s); o login
warm levou 129,399 ms. As dez amostras de chat warm, em duas ondas de cinco
sessões virtuais, retornaram HTTP 200: p95 de TTFT de 117392,377 ms (117,392
s) e p95 total de 119296,793 ms (119,297 s). A consulta de logs na janela da execução encontrou zero eventos
137. Esses números são uma baseline factual, não um SLO de chat: o limite de
primeira resposta permanece pendente de decisão após comparações em T05.2.

Para completar T05.2, a instrumentação local passou a emitir somente eventos
agregados de `embedder` e `reranker`: componente, operação, backend, quantidade
de itens, duração e resultado `success` ou `error`. Query, documento, resposta,
vetor e detalhe de exceção são proibidos. Esses eventos ainda aguardam
publicação e uma nova medição Azure; portanto, não constituem evidência factual
de componente nesta versão do documento.

## 7. Tarefas e microtarefas

- [x] **T05.1 — Criar protocolo de medição**
  - [x] Definir cinco usuários concorrentes, rajada de dez, cold/warm, campos de telemetria e descarte de dados sensíveis; o SLO de primeira resposta/chat continua sem valor até decisão após baseline factual.
  - [x] Teste: o script valida schema, separa amostras cold/warm e rejeita conteúdo sensível.
  - [x] Evidência: baseline Azure do run `32068963046`, com revisão, configuração e relatório sanitizado.
  - [x] Commits: `docs(performance): definir protocolo de medicao`, `feat(performance): medir baseline cold e warm` e `fix(performance): isolar coletor de baseline`.
- [ ] **T05.2 — Medir componentes e fluxo**
  - [ ] Medir startup, memória, TTFT, total e falhas de embedder/reranker/chat.
  - [ ] Teste: repetição do cenário produz relatório agregável.
  - [ ] Evidência: tabela de percentis e eventos 137 para revisão comparável.
  - [ ] Commit esperado: `docs(performance): registrar baseline azure`.
- [ ] **T05.3 — Definir resiliência**
  - [ ] Registrar timeout/retry/falha por LLM, Qdrant e PostgreSQL, com no máximo um retry idempotente e nenhum após stream/escrita não idempotente.
  - [ ] Teste: dependência lenta/indisponível respeita política e encerra stream corretamente.
  - [ ] Evidência: matriz de falhas, decisão e resultados de teste.
  - [ ] Commit esperado: `docs(performance): definir politica de falhas`.
- [ ] **T05.4 — Validar probes**
  - [ ] Validar readiness rasa de processo/configuração/modelos e observação separada das dependências.
  - [ ] Teste: serviço não recebe tráfego antes da condição de prontidão aprovada.
  - [ ] Evidência: configuração, logs e smoke Azure.
  - [ ] Commit esperado: `ops(performance): validar probes azure`.
- [ ] **T05.5 — Comparar escala e aquecimento**
  - [ ] Comparar `minReplicas`, imagem/cache, aquecimento ou modelo mais leve sem combinar variáveis.
  - [ ] Teste: carga aprovada antes/depois e rollback da configuração.
  - [ ] Evidência: latência, custo observável, decisão e revisão.
  - [ ] Commit esperado: `perf(azure): comparar estrategias de cold start`.

## 8. Estratégia de testes e validação

| Camada | Cenário | Automação | Comando / evidência |
|---|---|---|---|
| Unitária | Cálculo de métricas, timeout e backoff. | Sim | Pytest direcionado com relógio/dependência fake. |
| Integração | LLM/Qdrant/PostgreSQL lentos ou indisponíveis. | Sim | Compose/fixtures isoladas, sem serviço público. |
| CI | Relatório de regressão quando carga determinística for definida. | Sim, após T05.1 | Artefato com cenário e revisão. |
| Azure | Cold/warm, probes, memória e rollback de configuração. | Manual/automatizado após decisão | Log Analytics, revisão e smoke P0. |

## 9. Encerramento

### Gates e reversibilidade

| Gate | Estado documental atual | Condição / evidência futura |
|---|---|---|
| G0 — Baseline | Concluído parcialmente | T05.1 oferece baseline cold/warm de health, login e chat; T05.2 completa memória e componentes. |
| G1 — Especificação | Concluído | Este documento define SLO/carga, retry e probes provisórios; medição Azure bloqueia somente o SLO de primeira resposta/chat e mudanças dependentes. |
| G2 — Implementação | Não iniciado | Commits T05.1–T05.5. |
| G3 — Verificação | Não iniciado | Testes de falha, métricas repetíveis e regressão. |
| G4 — Operação | Não iniciado | Experimento Azure com smoke e observação pós-mudança. |
| G5 — Encerramento | Não iniciado | Evidência e checklists legados reconciliados. |

Configuração de réplica, probe, timeout e imagem deve ser revertida à revisão
Azure anterior após experimento malsucedido. Não apagar dados/Qdrant durante
teste de performance; se a carga exigir alteração de corpus, ela depende da
iniciativa P1 de qualidade RAG.

### Definition of Done

- [x] Linha de base distingue cold/warm e dependências; SLO de primeira resposta/chat só é fixado após T05.1.
- [ ] Probes e política de falhas foram testados com cenários negativos.
- [ ] Estratégia de escala/aquecimento tem comparação custo/latência e rollback.
- [ ] Smoke P0 e logs da revisão não apontam regressão de disponibilidade.
- [ ] Checklists legados só foram atualizados com a evidência da mudança.
