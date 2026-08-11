# P1 — Qualidade mensurável do RAG

| Campo | Valor |
|---|---|
| Estado | Planejado — especificado, não iniciado |
| Prioridade | P1 |
| Dono | Henrique Botelho Gomes |
| Dependências | [PRD do programa](00-prd-programa.md), `src/evaluation/relatorio_ragas.md`, `src/evaluation/dataset.jsonl`, `knowledge_base/manifest.json` |
| Documentos normativos | `PLANO_PROFISSIONALIZACAO.md`; `docs/03-rag-e-infraestrutura.md` §§ 1 e 6; `docs/04-piloto-e-roadmap.md` § 3.1; `docs/07-prd-requisitos.md` RF-10, RF-14 e RF-18–29; `docs/08-plano-execucao.md` T6.1–T6.2; `docs/09-contratos-tecnicos.md` |
| Checklists legados afetados | `docs/04-piloto-e-roadmap.md` § 5, “Relatório Ragas…”; `docs/07-prd-requisitos.md` § 7, “Relatório Ragas…”; `docs/08-plano-execucao.md` T6.1 e T6.2. Não alterar status nesta especificação. |
| Atualizado em | 2026-08-11 |

## 1. Contexto e evidências

O relatório Ragas+LLM de 06/08/2026 avaliou 30 perguntas e registrou
faithfulness 0,565, context precision 0,645, context recall 0,645 e answer
relevancy 0,565, abaixo das metas de 0,90/0,80/0,80/0,85. Ele identifica quatro
perguntas `fora_de_escopo` com redirecionamento correto do RF-10, quatro
`sem_resposta` com 1,000 em todas as métricas e lacuna real de corpus staff em
q018–q022. Excluindo `fora_de_escopo`, o próprio relatório estima cerca de 0,65
para faithfulness/relevancy e 0,70 para precision/recall.

O plano legado já determina separar `fora_de_escopo` e `sem_resposta`, mapear
notas zero, ampliar somente corpus autorizado, criar gate de regressão e
comparar o juiz econômico com um juiz mais forte. O RAG vigente é híbrido
(vetor + BM25 top-20, reranker top-5) e o corpus é versionado por
`knowledge_base/manifest.json`.

## 2. Objetivo mensurável

Produzir uma avaliação reproduzível, com dataset e recortes versionados, na
qual as perguntas RAG respondíveis sejam reportadas separadamente e atinjam:

| Métrica | Baseline 06/08/2026 | Meta do programa |
|---|---:|---:|
| Faithfulness | 0,565 agregado | ≥ 0,90 no recorte RAG respondível |
| Context precision | 0,645 agregado | ≥ 0,80 |
| Context recall | 0,645 agregado | ≥ 0,80 |
| Answer relevancy | 0,565 agregado | ≥ 0,85 no recorte RAG respondível |

Não há prazo aprovado. A composição exata do recorte RAG respondível é uma
decisão bloqueante; métricas de categorias excluídas continuam obrigatórias,
não podendo ocultar regressões.

## 3. Escopo e não escopo

### Escopo

- Versionar a taxonomia e o recorte de avaliação, incluindo relatórios próprios
  para `fora_de_escopo` e `sem_resposta`.
- Classificar cada nota zero como fonte ausente, recuperação inadequada, resposta
  insuficiente ou inadequação de métrica.
- Ingerir apenas documentos institucionais autorizados e rastreáveis.
- Criar gate de regressão antes de alterar prompt, chunking, embedding ou
  reranker e comparar juiz econômico com alternativa mais forte.

### Não escopo

- Declarar as metas atingidas sem relatório reproduzível.
- Alterar agentes, prompts, chunking, embedding, reranker ou corpus nesta
  iniciativa documental.
- Substituir a recusa honesta do RF-14 ou o redirecionamento do RF-10 para
  melhorar artificialmente uma métrica.

## 4. Requisitos e critérios de aceite

| ID | Requisito | Critério de aceite verificável |
|---|---|---|
| RQ-RAG-01 | Dataset, categoria, versão do corpus e modo do juiz devem constar do relatório. | Dado um relatório, quando auditado, então cada score tem dataset/commit, manifest e configuração identificáveis. |
| RQ-RAG-02 | `fora_de_escopo` e `sem_resposta` devem ser relatados fora do agregado RAG respondível. | Quando a avaliação rodar, então há agregados separados e nenhum item muda de categoria sem diff versionado. |
| RQ-RAG-03 | Toda nota zero deve ter diagnóstico rastreável. | Para q001–q030, então a planilha/dataset de diagnóstico aponta uma das quatro causas e a evidência consultada. |
| RQ-RAG-04 | Mudanças do pipeline devem passar por regressão. | Antes de merge de mudança em prompt/chunking/embedding/reranker, então o job compara baseline e candidato e falha conforme limiar aprovado. |
| RQ-RAG-05 | A expansão de corpus deve ser autorizada e reproduzível. | Quando um documento entrar, então origem, checksum, público-alvo e resultado de ingestão constam do manifest e do relatório. |
| RQ-RAG-06 | A escolha de juiz deve ser fundamentada. | A comparação usa o mesmo dataset e registra modelo/configuração, custo observável, repetição e divergências de score. |

## 5. Decisões, dependências e riscos

| Tipo | Item | Dono / condição | Mitigação ou próximo passo |
|---|---|---|---|
| Decisão tomada | Metas e baseline são os do relatório de 06/08/2026. | `00-prd-programa.md` § 4. | Não recalcular nem trocar baseline sem preservar o relatório original. |
| Decisão tomada | `fora_de_escopo` e `sem_resposta` não compõem o agregado RAG respondível, mas terão relatório próprio. | Plano legado § 3.1 e PRD do programa § 4. | Versionar a regra antes de executar o gate. |
| Bloqueio arquitetural | Definir se perguntas `tool` e `composta` entram no recorte RAG respondível e qual assertiva mede as categorias excluídas. | Dono do produto deve aprovar a taxonomia. | Bloqueia T02.3 e o limiar do gate, não a coleta de baseline. |
| Bloqueio arquitetural | Escolher juiz mais forte, credencial, orçamento e número de repetições. | Não há decisão nem segredo no repositório. | Bloqueia T02.5; comparação local/determinística pode ser preparada. |
| Risco | Corpus novo pode introduzir conteúdo não autorizado ou piorar recuperação. | Fonte e público-alvo devem ser revisados. | Manifest, checksum, ingestão incremental e regressão antes/depois. |
| Risco | Score do juiz variar mais que a mudança avaliada. | Avaliação LLM não é determinística. | Registrar repetições e divergência; não promover resultado sem análise. |

## 6. Plano técnico

O ponto de partida é `src/evaluation/dataset.jsonl`,
`src/evaluation/run_ragas.py`, `src/evaluation/feedback_negativo.jsonl` e
`knowledge_base/manifest.json`. A futura implementação deve manter o dataset
versionado no Git, gerar relatório Markdown e preservar o agregado histórico.
Documentos adicionados devem passar pelo pipeline idempotente de
`src/rag/ingest.py`; não é permitido reindexar destrutivamente sem estratégia
de restauração da coleção e do manifest.

O gate será configurado somente após T02.3. Ele deve executar sem modificar o
corpus de produção, comparar candidato e baseline versionados e publicar
artefato no CI. Não há variável de ambiente, migração nem contrato HTTP novo
especificado nesta etapa.

## 7. Tarefas e microtarefas

- [ ] **T02.1 — Congelar baseline e diagnóstico**
  - [ ] Versionar a taxonomia e mapear q001–q030, começando por q018–q022 e as categorias especiais.
  - [ ] Teste: validar schema e unicidade de IDs do dataset/diagnóstico.
  - [ ] Evidência: relatório comparando o novo inventário com `relatorio_ragas.md`.
  - [ ] Commit esperado: `docs(rag): registrar baseline e diagnostico`.
- [ ] **T02.2 — Cobrir lacunas autorizadas do corpus**
  - [ ] Para cada fonte aprovada, registrar origem, checksum, público e perguntas cobertas antes da ingestão.
  - [ ] Teste: ingestão idempotente e consultas de recuperação para as perguntas mapeadas.
  - [ ] Evidência: manifest, log de ingestão e resultados antes/depois.
  - [ ] Commit esperado: `feat(rag): adicionar corpus autorizado`.
- [ ] **T02.3 — Definir recortes e critérios de categorias especiais**
  - [ ] Obter decisão explícita sobre `tool`, `composta`, `fora_de_escopo` e `sem_resposta`.
  - [ ] Teste: casos de categoria exercitam o agregador correto.
  - [ ] Evidência: decisão registrada e relatório com todos os recortes.
  - [ ] Commit esperado: `docs(rag): definir recortes de avaliacao`.
- [ ] **T02.4 — Criar regressão automatizada**
  - [ ] Implementar comparação baseline/candidato sem alterar o agregado histórico.
  - [ ] Teste: regressão simulada falha e melhora dentro do limiar aprovado passa.
  - [ ] Evidência: artefato de CI com dataset, manifest, scores e decisão.
  - [ ] Commit esperado: `test(rag): adicionar gate de regressao`.
- [ ] **T02.5 — Comparar juízes**
  - [ ] Rodar os juízes aprovados com mesmo dataset e registrar custo, repetição e variabilidade.
  - [ ] Teste: validação de configuração impede comparar datasets ou recortes distintos.
  - [ ] Evidência: tabela de comparação e decisão de manutenção/troca.
  - [ ] Commit esperado: `docs(rag): comparar juizes de avaliacao`.

## 8. Estratégia de testes e validação

| Camada | Cenário | Automação | Comando / evidência |
|---|---|---|---|
| Unitária | Taxonomia, schema, agregação e limite do gate. | Sim | `pytest` direcionado à avaliação. |
| Integração | Ingestão autorizada e recuperação das perguntas cobertas. | Sim | CLI de ingestão em coleção isolada e testes de retriever. |
| CI | Baseline versus candidato. | Sim, após T02.4 | Artefato versionado do job, sem segredo em log. |
| Azure | Reingestão somente após validação local/CI. | Manual | Job `usiedu-ingest`, logs e smoke de Qdrant; não executar sem aprovação da fonte. |

## 9. Encerramento

### Gates e reversibilidade

| Gate | Estado documental atual | Condição / evidência futura |
|---|---|---|
| G0 — Baseline | Concluído | Relatório Ragas de 06/08/2026 e inventário T02.1. |
| G1 — Especificação | Concluído | Este documento define o escopo; a decisão T02.3 bloqueia somente a implementação do recorte e do gate. |
| G2 — Implementação | Não iniciado | Commits T02.1–T02.5 e testes correspondentes. |
| G3 — Verificação | Não iniciado | Pytest/Ruff, relatório reproduzível e gate executado. |
| G4 — Operação | Não iniciado | Ingestão Azure e avaliação pós-deploy, se corpus mudar. |
| G5 — Encerramento | Não iniciado | Checklists legados atualizados apenas com evidência. |

Dataset, manifest e configuração de avaliação devem ser reversíveis por commit.
Antes de reingestão em Azure, preservar o manifest e a coleção/revisão que
permita retorno; o mecanismo concreto de snapshot/coleção ainda não foi
decidido e bloqueia somente a publicação de corpus.

### Definition of Done

- [ ] Metas calculadas no recorte aprovado e categorias especiais publicadas separadamente.
- [ ] Todo zero diagnosticado e toda fonte adicionada autorizada/rastreável.
- [ ] Gate de regressão e testes relevantes verdes, com relatório reproduzível.
- [ ] Validação local, CI e Azure (se aplicável) registrada sem segredos.
- [ ] Checklists legados alterados somente no commit que muda o respectivo status.
- [ ] Resumo final informa mudança, comandos, evidências, riscos e bloqueios restantes.
