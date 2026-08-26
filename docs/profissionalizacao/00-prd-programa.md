# PRD — Programa de Profissionalização do UsiEdu

| Campo | Valor |
|---|---|
| Estado | Ativo |
| Dono do produto | Henrique Botelho Gomes |
| Documento mestre | arquivo raiz `PLANO_PROFISSIONALIZACAO.md` |
| Ambiente público atual | `https://usiedu-frontend.calmtree-d18b7257.brazilsouth.azurecontainerapps.io/` |
| Atualizado em | 11/08/2026 |

## 1. Problema e objetivo

O UsiEdu já é um piloto público e um portfólio técnico sólido, porém requer
evidências de confiabilidade, operação, segurança, qualidade RAG e experiência
de uso para se aproximar de uma solução institucional.

O objetivo deste programa é evoluir esses aspectos sem ampliar o escopo do
produto de forma oportunista. Cada iniciativa deve produzir um resultado
mensurável, um conjunto de testes proporcional ao risco e uma evidência de
validação local ou pública.

## 2. Escopo e prioridades

| Prioridade | Iniciativa | Resultado esperado |
|---|---|---|
| P0 | Validação do piloto publicado | Fluxo público validado e evidências atualizadas. |
| P1 | Qualidade mensurável do RAG | Métricas interpretáveis, corpus coberto e gate contra regressão. |
| P1 | Integração, entrega e rollback | Deploy repetível, testado e reversível. |
| P1 | Segurança e continuidade operacional | Segredos, dados e recuperação tratados explicitamente. |
| P2 | Performance e disponibilidade | Latência, memória e falhas medidas e controladas. |
| P2 | Produto e experiência | Falhas compreensíveis, acessibilidade e apresentação refinadas. |

### Fora de escopo

- Novos agentes, integrações externas ou funcionalidades de negócio sem item
  aprovado no PRD ou backlog.
- Tornar o piloto uma plataforma institucional multi-tenant, com SSO ou
  requisitos de Kubernetes.
- Declarar metas RAG atingidas sem relatório reproduzível e dataset versionado.

## 3. Requisitos do programa

### RQ-PRO-01 — Rastreabilidade

Cada iniciativa deve relacionar objetivo, requisitos, microtarefas, testes,
evidência, commits e condição de encerramento.

### RQ-PRO-02 — Uma fonte de progresso

`docs/08-plano-execucao.md`, `docs/04-piloto-e-roadmap.md` e
`docs/07-prd-requisitos.md` permanecem as fontes de verdade para andamento,
aceite do piloto e gate de entrega. Ao mudar um status legado, uma iniciativa
deve atualizar o item correspondente no mesmo commit e citar a evidência.

### RQ-PRO-03 — Execução autônoma com prestação de contas

Não há checkpoint de aprovação manual entre microtarefas. Ao encerrar uma
tarefa, o implementador deve informar ao proprietário:

1. o que foi alterado;
2. quais testes e validações passaram;
3. como reproduzir a validação localmente, quando aplicável;
4. quais riscos, bloqueios ou decisões permaneceram.

Uma decisão de arquitetura sem resposta documentada deve ser registrada como
bloqueio; a implementação não deve inventar uma solução.

### RQ-PRO-04 — Qualidade antes de declaração de conclusão

Toda alteração de código deve ser guiada por teste criado ou atualizado antes
da implementação. A verificação mínima é:

1. teste determinístico do comportamento alterado;
2. `ruff check .` e `ruff format --check .` limpos;
3. suíte `pytest` pertinente, ampliada para a suíte completa quando a mudança
   afetar contrato transversal ou antes de encerrar a iniciativa;
4. revisão do diff apenas contra os requisitos e DoD da tarefa;
5. evidência registrada no checklist ou relatório da tarefa.

### RQ-PRO-05 — Commits e escopo

Uma microtarefa concluída corresponde a um commit atômico no formato
`<tipo>(<escopo>): <resumo sem acentos>`. Trabalho fora da iniciativa deve ir
para o backlog, nunca entrar de forma incidental no mesmo commit.

### RQ-PRO-06 — Política de modelo implementador

Enquanto o proprietário não mudar esta decisão, o modelo de implementação é
**GPT-5.6 Terra**. Não é necessário perguntar a cada tarefa qual modelo usar.
Essa decisão substitui, para este programa, a recomendação de modelos da regra
8 de `docs/08-plano-execucao.md`; as demais regras desse documento continuam
obrigatórias.

## 4. Métricas e critérios globais

| Área | Linha de base conhecida | Direção de sucesso |
|---|---|---|
| Disponibilidade do piloto | Azure publicado; houve OOM anterior e streams interrompidos | Fluxo público completo e estável, com evidência. |
| RAG — faithfulness | 0,565 | >= 0,90 no recorte de perguntas RAG respondíveis. |
| RAG — context precision / recall | 0,645 / 0,645 | >= 0,80 em cada métrica. |
| RAG — answer relevancy | 0,565 | >= 0,85 no recorte de perguntas RAG respondíveis. |
| Segurança | Segredos no deploy e observabilidade ativa | Segredos gerenciados, dados revisados e recuperação testada. |
| Entrega | CI valida qualidade e testes; deploy é manual | Build, teste, deploy e rollback reproduzíveis. |

Os valores RAG vêm de `src/evaluation/relatorio_ragas.md`, de 06/08/2026, em
modo Ragas+LLM. Perguntas `fora_de_escopo` e `sem_resposta` não podem ser
usadas para esconder regressões: devem ter relatórios separados.

## 5. Gates de execução

| Gate | Condição para avançar | Evidência mínima |
|---|---|---|
| G0 — Baseline | Estado atual compreendido | URL, configuração, logs ou relatório existentes. |
| G1 — Especificação | Escopo, não escopo, requisitos e aceite definidos | Documento da iniciativa revisado contra fontes. |
| G2 — Implementação | Microtarefas concluídas | Commits atômicos e testes novos/atualizados. |
| G3 — Verificação | Qualidade e comportamento validados | Saída de testes, Ruff e smoke test. |
| G4 — Operação | Mudança publicada ou avaliada no ambiente alvo | URL, logs, métricas ou registro de deploy. |
| G5 — Encerramento | Checklist legado reconciliado | Evidência vinculada e resumo entregue ao proprietário. |

## 6. Template obrigatório de iniciativa

Toda iniciativa nova deve nascer a partir de
[`TEMPLATE_INICIATIVA.md`](TEMPLATE_INICIATIVA.md). Se uma seção não puder ser
preenchida com fatos do repositório, ela deve explicitar a dúvida e bloquear a
microtarefa dependente.

## 7. Referências normativas

- `PRD.v2.md` — requisitos do piloto e Sprint 9.
- `docs/08-plano-execucao.md` — regras de execução e checklists de progresso.
- `docs/04-piloto-e-roadmap.md` — critérios de aceite do piloto.
- `docs/07-prd-requisitos.md` — gate de entrega.
- `docs/09-contratos-tecnicos.md` — contratos e variáveis de ambiente.
- `docs/03-rag-e-infraestrutura.md` — arquitetura e políticas RAG.
