# P1 — Qualidade mensurável do RAG

| Campo | Valor |
|---|---|
| Estado | Em andamento — T02.1/T02.1b concluídas; T02.2 parcial; T02.3 concluída; T02.4–T02.5 não iniciadas |
| Prioridade | P1 |
| Dono | Henrique Botelho Gomes |
| Dependências | [PRD do programa](00-prd-programa.md), `src/evaluation/relatorio_ragas.md`, `src/evaluation/dataset.jsonl`, `knowledge_base/manifest.json` |
| Documentos normativos | `PLANO_PROFISSIONALIZACAO.md`; `docs/03-rag-e-infraestrutura.md` §§ 1 e 6; `docs/04-piloto-e-roadmap.md` § 3.1; `docs/07-prd-requisitos.md` RF-10, RF-14 e RF-18–29; `docs/08-plano-execucao.md` T6.1–T6.2; `docs/09-contratos-tecnicos.md` |
| Checklists legados afetados | `docs/04-piloto-e-roadmap.md` § 5, “Relatório Ragas…”; `docs/07-prd-requisitos.md` § 7, “Relatório Ragas…”; `docs/08-plano-execucao.md` T6.1 e T6.2. Não alterar status nesta especificação. |
| Atualizado em | 2026-08-11 |

## 1. Contexto e evidências

O relatório de 06/08/2026 declara o modo `Ragas+LLM`, avaliou 30 perguntas e
registrou faithfulness 0,565, context precision 0,645, context recall 0,645 e
answer relevancy 0,565, abaixo das metas de 0,90/0,80/0,80/0,85. Ele contém
quatro casos `fora_de_escopo`, quatro `sem_resposta` e cinco zeros em q018–q022.
Como a execução histórica não preservou respostas, contextos ou erros por caso,
esses scores não demonstram o comportamento do redirecionamento, a qualidade da
recusa ou uma causa de corpus.

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

Não há prazo aprovado. A composição provisória do recorte RAG respondível e os
relatórios complementares são definidos em
[07 — Decisões provisórias](07-decisoes-provisorias.md). Métricas fora do
agregado continuam obrigatórias e não podem ocultar regressões.

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
| RQ-RAG-02 | `tool`, `fora_de_escopo` e `sem_resposta` ficam fora do agregado RAG respondível; `composta` entra nele somente nas subperguntas que exigem recuperação e também recebe sub-relatório. | Quando a avaliação rodar, então há agregado RAG por subpergunta recuperável, assertivas determinísticas de `tool`, sub-relatório de `composta` e relatórios separados para as demais categorias, sem mudança de categoria sem diff versionado. |
| RQ-RAG-03 | Toda nota zero deve ter diagnóstico rastreável. | Para q001–q030, então a planilha/dataset de diagnóstico aponta uma das quatro causas e a evidência consultada. |
| RQ-RAG-04 | Mudanças do pipeline devem passar por regressão. | Antes de merge de mudança em prompt/chunking/embedding/reranker, então o job compara baseline e candidato e falha conforme limiar aprovado. |
| RQ-RAG-05 | A expansão de corpus deve ser autorizada e reproduzível. | Quando um documento entrar, então origem, checksum, público-alvo e resultado de ingestão constam do manifest e do relatório. |
| RQ-RAG-06 | A escolha de juiz deve ser fundamentada. | A comparação usa o mesmo dataset/recorte, três repetições, temperatura 0 quando suportada, custo observado/estimado até US$ 5 e divergências de score. |

## 5. Decisões, dependências e riscos

| Tipo | Item | Dono / condição | Mitigação ou próximo passo |
|---|---|---|---|
| Decisão tomada | Metas e baseline são os do relatório de 06/08/2026. | `00-prd-programa.md` § 4. | Não recalcular nem trocar baseline sem preservar o relatório original. |
| Decisão provisória | `tool` fica fora do agregado RAG e recebe assertiva determinística própria; `composta` entra no agregado quando ao menos uma subpergunta exige recuperação e sempre recebe sub-relatório; `fora_de_escopo` mede redirecionamento correto sem RAG/agentes; `sem_resposta` mede recusa honesta sem fonte inventada. | Revisar se a taxonomia, o contrato de roteamento ou o dataset versionado mudar. | T02.3 pode definir campos, agregadores e testes; só a alteração de comportamento espera implementação posterior. |
| Decisão provisória | `kimi-k2.7-code`, configurado como modelo de agente no Bicep pelo provedor `opencode-go`, é o candidato provisório a juiz forte; DeepSeek V4 Flash é o comparador econômico. O repositório ainda não configura um juiz independente. | Revisar se o provedor/modelo deixar de ser suportado, não permitir configuração comparável ou a comparação mostrar inadequação. | T02.5 deve adicionar configuração/proveniência explícita do juiz, sem criar segredo novo, e comparar no mesmo dataset/recorte, três repetições, temperatura 0 quando suportada e teto de US$ 5. |
| Gate explícito de execução | A corrida de T02.5 depende de uma credencial `OPENCODE_GO_API_KEY` autorizada, acesso ao provedor, configuração explícita do juiz e custo observável/estimável dentro do teto. | Não registrar, criar ou inferir credencial. | Preparar configuração, validação de paridade e relatório; parar antes da chamada externa se faltar acesso. Isso não bloqueia T02.1–T02.4 documental/local. |
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
artefato no CI. `tool` deve validar o resultado determinístico/autorização sem
score RAG; `composta` deve publicar o sub-relatório além da contribuição RAG;
`fora_de_escopo` deve comprovar redirecionamento e zero chamada de RAG/agente;
`sem_resposta`, recusa honesta e ausência de fonte inventada. Não há variável
de ambiente, migração nem contrato HTTP novo especificado nesta etapa.

Para remover ambiguidade antes da implementação, T02.3 deve versionar em cada
caso `composta` uma lista ordenada de subperguntas com `id`, `categoria`,
`requires_retrieval` e expectativa. O agregado RAG calcula cada métrica como a
média simples das subperguntas com `requires_retrieval=true`; uma pergunta
`direct` é uma única subpergunta recuperável. q008 tem duas subperguntas
`tool` e não entra no agregado; q023 entra somente pela norma de teletrabalho,
mantendo o boleto no sub-relatório `tool`; q030 entra pelas duas subperguntas
de recuperação. Esse schema é decisão documental para a futura versão do
dataset, não altera o JSONL atual.

## 7. Tarefas e microtarefas

- [x] **T02.1 — Congelar baseline e diagnóstico**
  - [x] Versionar a taxonomia e mapear q001–q030, começando por q018–q022 e as categorias especiais. *(Inventario: `src/evaluation/baseline_diagnostico_2026-08-06.json`, schema 2.0.0.)*
  - [x] Teste: validar schema e unicidade de IDs do dataset/diagnóstico. *(`tests/unit/test_rag_baseline_diagnostico.py`.)*
  - [x] Evidência: relatório comparando o novo inventário com `relatorio_ragas.md`. *(`src/evaluation/evidencia_baseline_2026-08-06.md`; a lacuna histórica permanece explicitamente registrada, sem reconstrução fictícia.)*
  - [x] Commits: `e011601`, `f90200a`, `6b0ef79`, `5c595d5` e `1622aca`.
- [x] **T02.1b — Gerar novo baseline auditável**
  - [x] Fixar commit, dataset, manifest, modelos, parâmetros, mecanismo de score e orçamento antes da execução.
  - [x] Teste: validar schema por caso, IDs, hashes, agregados, custo e diagnóstico dos zeros.
  - [x] Evidência: `src/evaluation/baseline_runs/2026-08-11/`, com respostas, fontes, erros, duração, tokens, custo, relatório e proveniência.
  - [x] Commit esperado: `docs(rag): publicar baseline auditavel`.
- [~] **T02.2 — Cobrir lacunas autorizadas do corpus**
  - [x] Para cada fonte aprovada, registrar origem, checksum, público e perguntas cobertas antes da ingestão. *(`src/evaluation/corpus_t02_2.json`; fontes versionadas primeiro no commit `691f579`.)*
  - [x] Teste: ingestão idempotente e consultas de recuperação para as perguntas mapeadas. *(Coleção isolada `t02_2_corpus_20260811`: 44 pontos na primeira passagem e zero na segunda.)*
  - [x] Evidência: manifest, log de ingestão e resultados antes/depois. *(`src/evaluation/evidencia_corpus_t02_2.json` e `tests/unit/test_rag_corpus_t02_2.py`.)*
  - [~] Cobertura factual: q018 e q019 estão cobertas; q020 permanece parcialmente coberta pela página legislativa do DGP; q021 exige identificar a secretaria; q022 possui apenas regulamento de unidade, sem política geral comprovada.
  - [x] Commit esperado: `feat(rag): adicionar corpus autorizado`.
- [x] **T02.3 — Definir recortes e critérios de categorias especiais**
  - [x] Registrar a decisão provisória sobre `tool`, `composta`, `fora_de_escopo` e `sem_resposta` e os campos por caso. *(`src/evaluation/recortes_avaliacao_v1.json`, schema e taxonomia 1.0.0.)*
  - [x] Teste: casos de categoria exercitam o agregador correto. *(`tests/unit/test_evaluation_slices.py`; implementação somente de avaliação em `src/evaluation/slices.py`.)*
  - [x] Evidência: decisão registrada e relatório com todos os recortes. *(`src/evaluation/evidencia_recortes_t02_3.json`: 30 casos, 33 subperguntas, sem recalcular scores.)*
  - [x] Commit esperado: `docs(rag): definir recortes de avaliacao`.
- [ ] **T02.4 — Criar regressão automatizada**
  - [ ] Implementar comparação baseline/candidato sem alterar o agregado histórico.
  - [ ] Teste: regressão simulada falha e melhora dentro do limiar aprovado passa.
  - [ ] Evidência: artefato de CI com dataset, manifest, scores e decisão.
  - [ ] Commit esperado: `test(rag): adicionar gate de regressao`.
- [ ] **T02.5 — Comparar juízes**
  - [ ] Preparar e, com credencial autorizada, rodar DeepSeek V4 Flash versus Kimi K2.7 Code no mesmo dataset/recorte, três vezes, temperatura 0 quando suportada e até US$ 5 no total.
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
| G0 — Baseline | Concluído | O histórico permanece como legado incompleto e imutável; o baseline auditável de 11/08/2026 é a nova referência, com commit, dataset, manifest, configuração, respostas, fontes, erros, duração, tokens, custo e hashes versionados. |
| G1 — Especificação | Concluído | Este documento e a decisão provisória definem o recorte e o protocolo; o acesso autorizado ao provedor bloqueia apenas a execução externa de T02.5. |
| G2 — Implementação | Não iniciado | Commits T02.1–T02.5 e testes correspondentes. |
| G3 — Verificação | Não iniciado | Pytest/Ruff, relatório reproduzível e gate executado. |
| G4 — Operação | Não iniciado | Ingestão Azure e avaliação pós-deploy, se corpus mudar. |
| G5 — Encerramento | Não iniciado | Checklists legados atualizados apenas com evidência. |

Dataset, manifest e configuração de avaliação devem ser reversíveis por commit.
Antes de reingestão em Azure, preservar o manifest e a coleção/revisão que
permita retorno; o mecanismo concreto de snapshot/coleção ainda não foi
decidido e bloqueia somente a publicação de corpus.

### Definition of Done

- [ ] Metas calculadas no recorte provisório revisável e categorias especiais publicadas separadamente.
- [ ] Todo zero diagnosticado e toda fonte adicionada autorizada/rastreável.
- [ ] Gate de regressão e testes relevantes verdes, com relatório reproduzível.
- [ ] Validação local, CI e Azure (se aplicável) registrada sem segredos.
- [ ] Checklists legados alterados somente no commit que muda o respectivo status.
- [ ] Resumo final informa mudança, comandos, evidências, riscos e bloqueios restantes.
