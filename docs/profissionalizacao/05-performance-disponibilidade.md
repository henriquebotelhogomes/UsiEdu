# P2 — Performance e disponibilidade

| Campo | Valor |
|---|---|
| Estado | Planejado — especificado, não iniciado |
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
primeiro token <3 s. Não há SLO de disponibilidade, carga, orçamento ou
limiares Azure aprovados.

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
| RQ-PERF-02 | Probes devem refletir prontidão real dos modelos e dependências necessárias. | Durante bootstrap/dependência indisponível, a observação definida não marca serviço pronto prematuramente. |
| RQ-PERF-03 | Chamadas LLM, Qdrant e PostgreSQL devem ter timeout, retry e falha explícitos. | Testes induzem timeout/erro e comprovam limite, sem duplicar operação nem travar stream. |
| RQ-PERF-04 | Mudança de escala/aquecimento deve comparar custo e latência. | Experimento controlado registra mesma carga, configuração, custo observável e decisão. |
| RQ-PERF-05 | Não pode haver regressão de disponibilidade conhecida. | Candidato preserva `/health`, fluxo P0 e ausência de exit 137 sob cenário comparável. |

## 5. Decisões, dependências e riscos

| Tipo | Item | Dono / condição | Mitigação ou próximo passo |
|---|---|---|---|
| Decisão tomada | API tem 2 vCPU/4 GiB; Qdrant mantém uma réplica. | `main.bicep` e P0. | Usar como baseline de experimento. |
| Decisão tomada | `minReplicas: 0` é ativo para API/frontend; timeouts nginx são 180 s/300 s. | Bicep e P0. | Medir custo e experiência antes de mudar. |
| Bloqueio arquitetural | Definir SLO, carga de referência, orçamento e limite de retry. | Não estão nos documentos normativos. | Bloqueia promoção de T05.3–T05.5, não coleta de métricas. |
| Bloqueio arquitetural | Decidir se readiness consulta modelos, Qdrant e PostgreSQL ou só processo. | Afeta disponibilidade percebida e custos. | Bloqueia alteração de probe. |
| Risco | Aquecimento ou réplica mínima reduz cold start e aumenta custo. | Crédito Azure é limitado. | Comparar cenário idêntico e registrar custo. |
| Risco | Retry amplifica carga/duplicação. | Chat e stream chamam dependências externas. | Limite, idempotência e teste de falha antes de habilitar. |

## 6. Plano técnico

A futura telemetria deve correlacionar revisão Azure, réplicas, cold/warm,
TTFT, total, memória e erro sem registrar pergunta, token ou segredo. A
medição inicia com `/health`, login e chat, pois P0 já fornece baseline desses
dois primeiros. A carga e percentis só serão comparáveis quando o cenário for
aprovado e repetível.

Probes e políticas de timeout/retry devem respeitar o proxy já existente:
180 s API e 300 s SSE não são metas de produto, apenas limites observados.
Qualquer mudança deve preservar o fallback de `/chat`, não expor API e possuir
rollback de revisão/configuração. Não há variável, endpoint ou migração nova
autorizada por esta especificação.

## 7. Tarefas e microtarefas

- [ ] **T05.1 — Criar protocolo de medição**
  - [ ] Definir carga demo, cold/warm, campos de telemetria e descarte de dados sensíveis.
  - [ ] Teste: script valida schema e separa amostras cold/warm.
  - [ ] Evidência: baseline local/Azure com revisão e configuração.
  - [ ] Commit esperado: `docs(performance): definir protocolo de medicao`.
- [ ] **T05.2 — Medir componentes e fluxo**
  - [ ] Medir startup, memória, TTFT, total e falhas de embedder/reranker/chat.
  - [ ] Teste: repetição do cenário produz relatório agregável.
  - [ ] Evidência: tabela de percentis e eventos 137 para revisão comparável.
  - [ ] Commit esperado: `docs(performance): registrar baseline azure`.
- [ ] **T05.3 — Definir resiliência**
  - [ ] Aprovar timeout/retry/falha por LLM, Qdrant e PostgreSQL.
  - [ ] Teste: dependência lenta/indisponível respeita política e encerra stream corretamente.
  - [ ] Evidência: matriz de falhas, decisão e resultados de teste.
  - [ ] Commit esperado: `docs(performance): definir politica de falhas`.
- [ ] **T05.4 — Validar probes**
  - [ ] Decidir semântica de liveness/readiness e testar bootstrap/dependências.
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
| G0 — Baseline | Concluído parcialmente | P0 oferece health/login; T05.2 completa TTFT/memória/carga. |
| G1 — Especificação | Concluído | Este documento; SLO/carga/probes pendentes bloqueiam mudanças dependentes. |
| G2 — Implementação | Não iniciado | Commits T05.1–T05.5. |
| G3 — Verificação | Não iniciado | Testes de falha, métricas repetíveis e regressão. |
| G4 — Operação | Não iniciado | Experimento Azure com smoke e observação pós-mudança. |
| G5 — Encerramento | Não iniciado | Evidência e checklists legados reconciliados. |

Configuração de réplica, probe, timeout e imagem deve ser revertida à revisão
Azure anterior após experimento malsucedido. Não apagar dados/Qdrant durante
teste de performance; se a carga exigir alteração de corpus, ela depende da
iniciativa P1 de qualidade RAG.

### Definition of Done

- [ ] Linha de base e metas aprovadas distinguem cold/warm e dependências.
- [ ] Probes e política de falhas foram testados com cenários negativos.
- [ ] Estratégia de escala/aquecimento tem comparação custo/latência e rollback.
- [ ] Smoke P0 e logs da revisão não apontam regressão de disponibilidade.
- [ ] Checklists legados só foram atualizados com a evidência da mudança.
