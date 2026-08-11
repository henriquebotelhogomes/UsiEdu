# P1 — Integração, entrega e rollback

| Campo | Valor |
|---|---|
| Estado | Planejado — especificado, não iniciado |
| Prioridade | P1 |
| Dono | Henrique Botelho Gomes |
| Dependências | [PRD do programa](00-prd-programa.md), `infra/azure/`, `.github/workflows/ci.yml`, `.github/workflows/docs.yml`, Dockerfiles e `docker-compose.yml` |
| Documentos normativos | `PLANO_PROFISSIONALIZACAO.md`; `PRD.v2.md` T9.4; `docs/03-rag-e-infraestrutura.md` § 10; `docs/04-piloto-e-roadmap.md` § 5; `docs/07-prd-requisitos.md` RF-01–05, RF-32 e § 7; `docs/08-plano-execucao.md` T9.4; `docs/09-contratos-tecnicos.md` § 2 |
| Checklists legados afetados | `docs/08-plano-execucao.md` T9.4; `docs/04-piloto-e-roadmap.md` § 5; `docs/07-prd-requisitos.md` § 7. Não alterar status enquanto só houver especificação. |
| Atualizado em | 2026-08-11 |

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
verificado de retorno à revisão anterior. Não há SLO, prazo ou plataforma de
scan aprovados; serão definidos antes dos gates dependentes.

## 3. Escopo e não escopo

### Escopo

- Testes frontend → nginx → API, API → PostgreSQL e API → Qdrant.
- E2E login → chat → feedback → `/insights`.
- Workflow GitHub Actions para build, teste, scan, publicação e deploy Azure.
- Tags de imagem derivadas do commit, aprovação pública e rollback verificável.

### Não escopo

- Implementar mudança de produto ou alterar contratos de chat.
- Migrar de Azure Container Apps, introduzir Kubernetes ou alterar credenciais.
- Publicar workflow, imagem ou infraestrutura como parte desta especificação.

## 4. Requisitos e critérios de aceite

| ID | Requisito | Critério de aceite verificável |
|---|---|---|
| RQ-DEL-01 | Limites entre frontend/nginx/API, PostgreSQL e Qdrant devem ter testes. | Dado o ambiente de teste, quando um limite ficar indisponível, então o teste distingue a falha e não mascara resposta indevida. |
| RQ-DEL-02 | O fluxo público principal deve ter E2E automatizado ou evidência manual justificada. | Quando executado contra ambiente autorizado, então login, chat, feedback e `/insights` concluem com dados demo. |
| RQ-DEL-03 | Toda imagem candidata deve ter identificador imutável rastreável ao commit. | Quando o workflow publicar uma imagem, então tag e digest constam do artefato de deploy. |
| RQ-DEL-04 | Deploy público deve depender de aprovação explícita. | Sem aprovação do ambiente configurado, o job de produção não inicia. |
| RQ-DEL-05 | O retorno deve ser testado sem reconstruir a imagem. | Dado falha pós-deploy, quando o runbook for executado, então tráfego retorna à revisão/digest anterior e smoke test passa. |
| RQ-DEL-06 | Imagens candidatas devem passar por scan com política documentada. | Achado que viola severidade aprovada bloqueia promoção e gera evidência. |

## 5. Decisões, dependências e riscos

| Tipo | Item | Dono / condição | Mitigação ou próximo passo |
|---|---|---|---|
| Decisão tomada | Azure Container Apps, ACR e Bicep são a base vigente. | `infra/azure/`. | Reutilizar sem alterar topologia nesta iniciativa. |
| Decisão tomada | API e Qdrant permanecem internos; frontend é a origem pública. | `main.bicep` e P0. | E2E deve usar a origem pública, não expor API. |
| Bloqueio arquitetural | Definir autenticação GitHub→Azure (OIDC ou credencial gerenciada), permissões mínimas e ambiente de aprovação. | Requer decisão de segurança. | Bloqueia T03.4, não testes locais. |
| Bloqueio arquitetural | Definir scanner, severidade bloqueante e tratamento de exceções. | Não há ferramenta/política no repositório. | Bloqueia T03.3. |
| Bloqueio arquitetural | Validar retenção e ativação de revisões anteriores sob `activeRevisionsMode: Single`. | Azure deve ser verificado no ambiente real. | Bloqueia T03.5 até runbook testado. |
| Risco | Teste E2E consumir LLM, sofrer cold start ou rate limit. | API escala a zero e tem limites. | Usar ambiente/dados demo controlados e registrar custo/tempo. |
| Risco | Tag mutável publicar código diferente do validado. | `v1` é default atual. | Promover somente digest produzido pelo candidato aprovado. |

## 6. Plano técnico

Os testes devem partir dos contratos REST atuais: login, `/chat` ou
`/chat/stream`, `/feedback`, `/feedback/stats`, `/feedback/recent` e
`/insights`. O banco de teste não pode usar o PostgreSQL público nem dados
reais; Qdrant deve ser isolado. O teste frontend/proxy deve verificar que
SSE não recebe buffering, sem depender de LLM externo.

O workflow futuro deverá separar validação de build, scan, publicação e
produção. O deploy recebe tag/digest imutável, nunca segredo no YAML ou log. A
aprovação, identidade Azure, política do scanner e rollback precisam de decisão
explícita antes da configuração. O runbook deve identificar revisão/digest
anterior, mover tráfego conforme o modo de revisões validado, fazer smoke de
`/health` e do fluxo autenticado e registrar resultado.

## 7. Tarefas e microtarefas

- [ ] **T03.1 — Cobrir limites de integração**
  - [ ] Criar fixtures isoladas para nginx/API, PostgreSQL e Qdrant.
  - [ ] Teste: sucesso e indisponibilidade de cada limite, incluindo proxy SSE.
  - [ ] Evidência: saída do teste e contratos exercitados.
  - [ ] Commit esperado: `test(entrega): cobrir limites de integracao`.
- [ ] **T03.2 — Automatizar fluxo E2E**
  - [ ] Implementar cenário demo login → chat → feedback → insights sem registrar token/senha.
  - [ ] Teste: fluxo completo e mensagem de falha útil quando serviço dependente cair.
  - [ ] Evidência: relatório E2E com URL/ambiente mascarados quando necessário.
  - [ ] Commit esperado: `test(entrega): adicionar fluxo e2e`.
- [ ] **T03.3 — Definir política de imagem**
  - [ ] Escolher scanner e política de severidade, preservando exceções auditáveis.
  - [ ] Teste: imagem com achado de teste falha a política.
  - [ ] Evidência: decisão, relatório de scan e retenção de digest.
  - [ ] Commit esperado: `docs(entrega): definir politica de imagens`.
- [ ] **T03.4 — Criar pipeline de promoção**
  - [ ] Configurar identidade Azure aprovada, tags por commit/digest e aprovação de produção.
  - [ ] Teste: dry-run/candidato bloqueado sem aprovação e deploy autorizado em ambiente definido.
  - [ ] Evidência: logs sem segredos, SHA/digest e revisão Azure.
  - [ ] Commit esperado: `ci(entrega): automatizar promocao azure`.
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
| E2E | Login, chat, feedback e insights. | Sim, após T03.2 | Runner definido no repositório, com dados demo. |
| CI | Build, lint, pytest, E2E permitido, scan e promoção. | Sim | Artefatos do GitHub Actions. |
| Azure | Candidato aprovado e rollback. | Manual/automatizado após decisão | Revisão, digest, `/health` e E2E público. |

## 9. Encerramento

### Gates e reversibilidade

| Gate | Estado documental atual | Condição / evidência futura |
|---|---|---|
| G0 — Baseline | Concluído | Workflows, Bicep e P0 inventariados. |
| G1 — Especificação | Concluído | Este documento define o escopo; as decisões T03.3–T03.5 bloqueiam somente os trabalhos dependentes. |
| G2 — Implementação | Não iniciado | Commits T03.1–T03.5. |
| G3 — Verificação | Não iniciado | Testes, scan e artefatos de pipeline verdes. |
| G4 — Operação | Não iniciado | Deploy aprovado e rollback exercitado em Azure. |
| G5 — Encerramento | Não iniciado | Checklists legados reconciliados com evidência. |

Rollback deve reutilizar imagem por digest/revisão anterior, não reconstruir ou
alterar banco/Qdrant. Migrações de dados não pertencem ao escopo; se passarem a
ser necessárias, exigem plano próprio de compatibilidade e restauração.

### Definition of Done

- [ ] Testes de integração e E2E aprovados no nível definido.
- [ ] Imagens imutáveis, scan e aprovação pública operando sem expor segredos.
- [ ] Deploy e rollback Azure reproduzidos com evidência de revisão/digest.
- [ ] CI, runbook e documentação atualizados.
- [ ] Checklists legados mudaram apenas no commit da evidência correspondente.
