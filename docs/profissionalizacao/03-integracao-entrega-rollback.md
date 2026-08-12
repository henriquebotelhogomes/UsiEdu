# P1 — Integração, entrega e rollback

| Campo | Valor |
|---|---|
| Estado | Em andamento — T03.1–T03.3 concluídas; T03.4 teve execução hospedada bloqueada antes do push; T03.5 não iniciada |
| Prioridade | P1 |
| Dono | Henrique Botelho Gomes |
| Dependências | [PRD do programa](00-prd-programa.md), `infra/azure/`, `.github/workflows/ci.yml`, `.github/workflows/docs.yml`, Dockerfiles e `docker-compose.yml` |
| Documentos normativos | `PLANO_PROFISSIONALIZACAO.md`; `PRD.v2.md` T9.4; `docs/03-rag-e-infraestrutura.md` § 10; `docs/04-piloto-e-roadmap.md` § 5; `docs/07-prd-requisitos.md` RF-01–05, RF-32 e § 7; `docs/08-plano-execucao.md` T9.4; `docs/09-contratos-tecnicos.md` § 2 |
| Checklists legados afetados | `docs/08-plano-execucao.md` T9.4; `docs/04-piloto-e-roadmap.md` § 5; `docs/07-prd-requisitos.md` § 7. Não alterar status enquanto só houver especificação. |
| Atualizado em | 2026-08-12 |

## 1. Contexto e evidências

O CI existente em `.github/workflows/ci.yml` executa `ruff check .`,
`ruff format --check .` e `pytest -v --tb=short` em push/PR para `main`. O
workflow de documentação publica MkDocs em push de arquivos de docs para
`main`; não há workflow versionado para build/deploy Azure, testes de
integração entre serviços, aprovação de produção ou scan de imagem.

O deploy atual é manual por `infra/azure/deploy.ps1`. Seu valor padrão de
`ImageTag` é `v1`; ele constrói e publica imagens no ACR e aplica Bicep. O
Container Apps usa revisão ativa única e 100% do tráfego na última revisão. A
P0 publicou frontend `0000008` e API `0000013`, validando o fluxo público,
mas não constituiu um procedimento de rollback testado.

## 2. Objetivo mensurável

Disponibilizar uma entrega rastreável do commit ao Azure: cada candidato deve
ter imagens identificadas por commit imutável, testes de integração e E2E
definidos, aprovação explícita antes do ambiente público e procedimento
verificado de retorno à revisão anterior. A política provisória usa OIDC
federado, GitHub Environment `production` e Trivy; a execução hospedada
bloqueou a promoção antes do push e o experimento de rollback permanece pendente.

## 3. Escopo e não escopo

### Escopo

- Testes frontend → nginx → API, API → PostgreSQL e API → Qdrant.
- E2E login → chat → feedback → `/insights`.
- Workflow GitHub Actions para build, teste, scan, publicação e deploy Azure.
- Tags de imagem derivadas do commit, aprovação pública e rollback verificável.
- Identidade federada OIDC de GitHub para Azure, limitada ao deploy aprovado.

### Não escopo

- Implementar mudança de produto ou alterar contratos de chat.
- Migrar de Azure Container Apps, introduzir Kubernetes ou alterar segredos e
  credenciais runtime existentes; a identidade federada OIDC deste escopo é a
  exceção necessária para o deploy.
- Publicar workflow, imagem ou infraestrutura como parte desta especificação.

## 4. Requisitos e critérios de aceite

| ID | Requisito | Critério de aceite verificável |
|---|---|---|
| RQ-DEL-01 | Limites entre frontend/nginx/API, PostgreSQL e Qdrant devem ter testes. | Dado o ambiente de teste, quando um limite ficar indisponível, então o teste distingue a falha e não mascara resposta indevida. |
| RQ-DEL-02 | O fluxo público principal deve ter E2E automatizado ou evidência manual justificada. | Quando executado contra ambiente autorizado, então login, chat, feedback e `/insights` concluem com dados demo. |
| RQ-DEL-03 | Toda imagem candidata deve ter identificador imutável rastreável ao commit. | Quando o workflow publicar uma imagem, então tag e digest constam do artefato de deploy. |
| RQ-DEL-04 | Deploy público deve usar OIDC federado, menor privilégio e GitHub Environment `production` com aprovação manual. | Sem aprovação, o job não inicia; nenhuma credencial Azure persistente é usada como secret. |
| RQ-DEL-05 | O retorno deve ser testado sem reconstruir a imagem. | Dado falha pós-deploy, quando o runbook em modo Single for executado, então tráfego retorna ao digest/revisão anterior validada, preservada antes do experimento, e o smoke passa. |
| RQ-DEL-06 | Imagens candidatas devem passar por Trivy. | CRITICAL e HIGH com correção disponível bloqueiam promoção; exceção versionada contém justificativa, dono e validade máxima de 30 dias. |

## 5. Decisões, dependências e riscos

| Tipo | Item | Dono / condição | Mitigação ou próximo passo |
|---|---|---|---|
| Decisão tomada | Azure Container Apps, ACR e Bicep são a base vigente. | `infra/azure/`. | Reutilizar sem alterar topologia nesta iniciativa. |
| Decisão tomada | API e Qdrant permanecem internos; frontend é a origem pública. | `main.bicep` e P0. | E2E deve usar a origem pública, não expor API. |
| Decisão aplicada | GitHub→Azure usa OIDC federado, menor privilégio e Environment `production` com aprovação manual; credencial Azure persistente não pode ser secret. | Aplicação Entra `usiedu-github-production`, subject com IDs estáveis `repo:henriquebotelhogomes@43866427/UsiEdu@1324468469:environment:production` e aprovador do repositório. | `AcrPush` está limitado a `usieduacr650206`; `Container Apps Contributor`, limitado individualmente a `usiedu-api` e `usiedu-frontend`. |
| Decisão provisória | Trivy é o scanner; CRITICAL e HIGH com correção disponível bloqueiam. Exceção é versionada, justificada, tem dono e vence em no máximo 30 dias. | Política `image-promotion-v1`, autoensaio sintético e scan real versionados; o cache de análise fica desabilitado para cada candidato. | A execução hospedada bloqueou antes do push ao reportar versões antigas incompatíveis com o log de build; a repetição com análise sem cache é necessária antes de qualquer publicação. |
| Gate explícito de execução | `activeRevisionsMode: Single` é factual no Bicep, mas a reversão operacional só vale após experimento Azure. | Exige uma revisão/digest anterior validada e uma janela controlada. | Antes de automatizar, escrever/executar runbook no modo Single, preservar digest e evidenciar retorno em T03.5. |
| Risco | Teste E2E consumir LLM, sofrer cold start ou rate limit. | API escala a zero e tem limites. | Usar ambiente/dados demo controlados e registrar custo/tempo. |
| Risco | Tag mutável publicar código diferente do validado. | `v1` é default atual. | Promover somente digest produzido pelo candidato aprovado. |

## 6. Plano técnico

Os testes devem partir dos contratos REST documentados: login, `/chat` ou
`/chat/stream` e `/health`. antes de automatizar feedback ou `/insights`. T03.2 reconciliou
`/feedback`, `/feedback/stats` e `/feedback/recent` em
`docs/09-contratos-tecnicos.md`. O banco de teste não pode usar o PostgreSQL
público nem dados reais; Qdrant deve ser isolado. O teste frontend/proxy deve
verificar que SSE não recebe buffering, sem depender de LLM externo.

O workflow `.github/workflows/promote-azure.yml` separa build, scan, política,
publicação e
produção. O deploy recebe tag/digest imutável, nunca segredo no YAML ou log,
autentica por OIDC federado e usa Environment `production` com aprovação
manual. A identidade OIDC e Environment `production` configurados dão suporte
ao contrato, mas a execução hospedada depende de push autorizado para `main`;
ela ainda não foi alegada nem exercitada. O runbook no modo Single deve
preservar e identificar a
revisão/digest anterior validada, retornar a ela sem reconstrução, fazer smoke
de `/health` e do fluxo autenticado e registrar resultado.

## 7. Tarefas e microtarefas

- [x] **T03.1 — Cobrir limites de integração**
  - [x] Criar fixtures isoladas para nginx/API, PostgreSQL e Qdrant. *(`tests/integration/test_delivery_boundaries.py` usa FastAPI/LLM fake, PostgreSQL mockado no limite do driver e Qdrant local em memória.)*
  - [x] Teste: sucesso e indisponibilidade de cada limite, incluindo proxy SSE. *(O contrato nginx exige proxy HTTP/1.1, `proxy_buffering off`, cache desativado e streaming em chunks; falhas de API, PostgreSQL e Qdrant permanecem distinguíveis.)*
  - [x] Evidência: saída do teste e contratos exercitados. *(32 testes direcionados aprovados, incluindo os 5 limites de integração e regressão completa do retriever.)*
  - [x] Commit esperado: `test(entrega): cobrir limites de integracao`.
- [x] **T03.2 — Automatizar fluxo E2E**
  - [x] Implementar cenário demo login → chat → feedback → insights sem registrar token/senha. *(`frontend/src/__tests__/demo-flow.e2e.test.tsx` percorre a UI com serviços determinísticos e exporta apenas método/rota.)*
  - [x] Teste: fluxo completo e mensagem de falha útil quando serviço dependente cair. *(O cenário cobre sucesso via SSE, avaliação positiva, cards/recentes e indisponibilidade 503 com fallback para `/chat`.)*
  - [x] Evidência: relatório E2E com URL/ambiente mascarados quando necessário. *(O job `frontend` publica `frontend-e2e-evidence`; o relatório não contém corpo, senha ou JWT.)*
  - [x] Commit esperado: `test(entrega): adicionar fluxo e2e`.
- [x] **T03.3 — Definir política de imagem**
  - [x] Registrar Trivy, bloqueio CRITICAL/HIGH com correção disponível e exceção versionada, justificada, com dono e validade máxima de 30 dias. *(`src/delivery/image_policy_v1.json` fixa a política e inicia sem exceções.)*
  - [x] Teste: imagem com achado de teste falha a política. *(`tests/unit/test_image_policy.py` cobre HIGH/CRITICAL corrigível, achado sem correção, exceções e digest inválido.)*
  - [x] Evidência: decisão, relatório de scan e retenção de digest. *(O CI publica os relatórios sintéticos pass/block com digest imutável; o primeiro relatório Trivy de imagem real permanece para T03.4.)*
  - [x] Commit esperado: `docs(entrega): definir politica de imagens`.
- [~] **T03.4 — Criar pipeline de promoção**
  - [x] Configurar identidade OIDC federada de menor privilégio, tags por commit/digest e Environment `production`. *(O contrato versionado usa apenas variáveis e `id-token: write`; a proteção disponível no repositório foi aplicada sem segredo persistente.)*
  - [~] Teste: contrato local garante execução manual em `main`, gate `production`, scan e política antes do push, com cache do Trivy desabilitado para cada candidato.
  - [~] Evidência: a execução hospedada bloqueou a promoção antes do push; o build registrou `msgpack 1.2.1` e `setuptools 84.0.0`, enquanto o relatório Trivy listou versões antigas. A nova execução sem cache deverá confirmar o relatório da imagem recém-construída.
  - [x] Commit: `ci(entrega): automatizar promocao azure`.
- [ ] **T03.5 — Exercitar rollback**
  - [ ] Escrever e executar runbook com revisão/digest anterior conhecido.
  - [ ] Teste: retorno controlado seguido de health e fluxo E2E.
  - [ ] Evidência: antes/depois de tráfego, revisão e smoke test.
  - [ ] Commit esperado: `docs(entrega): registrar rollback azure`.

## 8. Estratégia de testes e validação

| Camada | Cenário | Automação | Comando / evidência |
|---|---|---|---|
| Unitária | Validação de tag, seleção de digest e scripts de deploy. | Sim | Testes direcionados sem Azure. |
| Integração | nginx/API, API/PostgreSQL, API/Qdrant e SSE. | Sim | Pytest/compose em serviços isolados. |
| E2E | Login, chat, feedback e insights. | Sim | Vitest `demo-flow.e2e.test.tsx`, dados demo e serviços fake; relatório sanitizado no CI. |
| CI | Build, lint, pytest, E2E permitido, scan e promoção. | Sim | Artefatos do GitHub Actions. |
| Azure | Candidato aprovado e rollback. | Manual/automatizado após decisão | Revisão, digest, `/health` e E2E público. |

## 9. Encerramento

### Gates e reversibilidade

| Gate | Estado documental atual | Condição / evidência futura |
|---|---|---|
| G0 — Baseline | Concluído | Workflows, Bicep e P0 inventariados. |
| G1 — Especificação | Concluído | Este documento define Trivy, OIDC, aprovação e rollback; a execução hospedada e o experimento operacional permanecem separados. |
| G2 — Implementação | Em andamento | T03.1–T03.3 concluídas; T03.4 está versionada e T03.5 permanece. |
| G3 — Verificação | Em andamento | Limites, E2E, política e contrato da promoção possuem autoensaios; o scan real bloqueou antes do push e requer repetição sem cache antes da promoção. |
| G4 — Operação | Não iniciado | Deploy aprovado e rollback exercitado em Azure. |
| G5 — Encerramento | Não iniciado | Checklists legados reconciliados com evidência. |

Rollback deve reutilizar imagem por digest/revisão anterior, não reconstruir ou
alterar banco/Qdrant. Migrações de dados não pertencem ao escopo; se passarem a
ser necessárias, exigem plano próprio de compatibilidade e restauração.

### Definition of Done

- [ ] Testes de integração e E2E aprovados no nível definido.
- [ ] Imagens imutáveis, Trivy, exceções temporárias auditáveis e aprovação pública operando sem expor segredos ou credenciais Azure persistentes.
- [ ] Deploy e rollback Azure reproduzidos com evidência de revisão/digest.
- [ ] CI, runbook e documentação atualizados.
- [ ] Checklists legados mudaram apenas no commit da evidência correspondente.
