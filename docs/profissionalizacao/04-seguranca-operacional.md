# P1 — Segurança e continuidade operacional

| Campo | Valor |
|---|---|
| Estado | Planejado — especificado, não iniciado |
| Prioridade | P1 |
| Dono | Henrique Botelho Gomes |
| Dependências | [PRD do programa](00-prd-programa.md), `infra/azure/main.bicep`, `infra/azure/deploy.ps1`, `src/security/guardrails.py`, `src/observability/` |
| Documentos normativos | `PLANO_PROFISSIONALIZACAO.md`; `PRD.v2.md` RF2-09–11 e T9.4; `docs/03-rag-e-infraestrutura.md` §§ 7, 10 e 11; `docs/04-piloto-e-roadmap.md` §§ 5 e 7; `docs/07-prd-requisitos.md` RNF-05–06; `docs/08-plano-execucao.md` T9.1–T9.4; `docs/09-contratos-tecnicos.md` §§ 2–3 |
| Checklists legados afetados | `docs/08-plano-execucao.md` T9.4; `docs/04-piloto-e-roadmap.md` § 5; `docs/07-prd-requisitos.md` § 7. Não alterar status nesta especificação. |
| Atualizado em | 2026-08-11 |

## 1. Contexto e evidências

O piloto usa JWT de uma hora e dados demo; RNF-05 veda dados pessoais reais.
Rate limiting e guardrails determinísticos já existem. A API tem tracing
LangSmith/LangChain habilitado e logs JSON; portanto, payloads e metadados
precisam de revisão de minimização antes de ampliar o uso externo.

No Azure, `main.bicep` recebe segredos como parâmetros seguros e cria secrets
no Container App, mas o deploy atual gera `JWT_SECRET` e senha PostgreSQL se
omitidos. Isso pode invalidar sessões a cada deploy. O ACR usa admin user;
PostgreSQL Flexible Server possui retenção de backup de sete dias, sem backup
georredundante, HA desabilitada e regra `allow-azure-services`. Qdrant persiste
em Azure Files. Não há evidência versionada de restore de PostgreSQL/Qdrant,
política LGPD/privacidade, Key Vault, Managed Identity, alertas de orçamento
ou alertas operacionais.

## 2. Objetivo mensurável

Antes de tratar o piloto como operação contínua, demonstrar que segredos,
telemetria e dados têm proprietário e política; que JWT não muda
involuntariamente; e que PostgreSQL e Qdrant podem ser restaurados em exercício
documentado. Os únicos valores atuais suportados são retenção PostgreSQL de
sete dias e ausência de HA/geo-backup. RPO, RTO, retenção de logs e orçamento
não foram aprovados e não serão inventados.

## 3. Escopo e não escopo

### Escopo

- Key Vault/Managed Identity quando a decisão e permissões forem aprovadas.
- Persistência, rotação e impacto de sessão do segredo JWT.
- Inventário/minimização de dados em logs e LangSmith, privacidade e LGPD.
- Backup e restauração de PostgreSQL e do volume Qdrant.
- Alertas de orçamento, API, ingestão e banco.

### Não escopo

- Coletar dados pessoais reais para testar a política.
- Alterar guardrails, autenticação de produto, RBAC institucional, SSO ou
multi-tenancy.
- Declarar conformidade LGPD ou SLA sem responsável legal e evidência.

## 4. Requisitos e critérios de aceite

| ID | Requisito | Critério de aceite verificável |
|---|---|---|
| RQ-SEC-01 | Segredos não devem ser versionados, logados ou entregues por parâmetro inseguro de pipeline. | Scan do repositório/pipeline não encontra valor real; referências apontam para mecanismo aprovado. |
| RQ-SEC-02 | JWT deve sobreviver a deploy normal e ter rotação controlada. | Dado deploy sem rotação, então token válido mantém o comportamento esperado; dada rotação aprovada, então impacto e comunicação são registrados. |
| RQ-SEC-03 | Telemetria deve ter inventário, minimização e retenção definida. | Para cada campo enviado a logs/LangSmith, então há finalidade, classificação, mascaramento/remoção e prazo aprovados. |
| RQ-SEC-04 | Privacidade e LGPD do piloto externo devem ter política publicada. | Documento identifica controlador/canal, bases/retensão aplicáveis e fluxo de solicitação, após revisão do responsável. |
| RQ-SEC-05 | Estado PostgreSQL e Qdrant deve ser recuperável. | Exercício restaura cópia autorizada e comprova integridade por consulta/smoke sem sobrescrever produção. |
| RQ-SEC-06 | Falhas e custo devem ser detectáveis. | Simulação/consulta controlada produz alerta de API, ingestão, banco e orçamento nos canais aprovados. |

## 5. Decisões, dependências e riscos

| Tipo | Item | Dono / condição | Mitigação ou próximo passo |
|---|---|---|---|
| Decisão tomada | Dados do piloto são demo; PII real não é requisito. | RNF-05. | Não introduzir PII para validar telemetria. |
| Decisão tomada | PostgreSQL é o estado transacional; Qdrant usa Azure Files. | `docs/03` § 10 e Bicep. | Exercícios devem cobrir ambos. |
| Decisão tomada | Backup PostgreSQL configurado: 7 dias; geo-backup e HA desabilitados. | `main.bicep`. | Tratar como baseline, não como garantia de recuperação testada. |
| Bloqueio arquitetural | Escolher Key Vault, Managed Identity, permissões e migração de ACR admin. | Requer acesso/decisão Azure. | Bloqueia T04.2. |
| Bloqueio legal | Definir controlador, retenção, canal de privacidade e revisão LGPD. | Dono do produto/responsável jurídico. | Bloqueia publicação de política e dados externos além do demo. |
| Bloqueio operacional | Aprovar RPO/RTO, orçamento e canais de alerta. | Não há limiares no repositório. | Bloqueia limiares finais de T04.4–T04.5. |
| Risco | Rotação inesperada de JWT encerra todas as sessões. | Deploy atual pode gerar segredo. | Separar provisionamento de rotação e testar continuidade. |
| Risco | Restore incompleto deixa Qdrant e PostgreSQL inconsistentes. | Estados são diferentes. | Exercício isolado e checklist de consistência. |

## 6. Plano técnico

A futura implementação começará por inventário sem valores de segredo:
`deploy.ps1`, parâmetros Bicep, variáveis do Container App, GitHub Actions,
logs JSON e configuração LangSmith. A migração de segredo só ocorre após
definir identidade e permissões de menor privilégio; nenhum segredo será
copiado para documento, output de CI ou comando histórico.

O teste de recuperação deve usar cópia/ambiente isolado. Para PostgreSQL,
registrar origem, ponto de recuperação e consulta de integridade. Para Qdrant,
registrar método de backup do Azure Files, versão do manifest e consulta de
coleção. A consistência entre corpus/manifest e coleção deve ser verificada
antes de qualquer retorno. Alertas precisam usar métricas/logs realmente
disponíveis no Azure; nenhum destino, limiar ou orçamento é presumido.

## 7. Tarefas e microtarefas

- [ ] **T04.1 — Inventariar superfície operacional**
  - [ ] Mapear segredos, fluxos de dados, logs, LangSmith, persistência e permissões sem valores.
  - [ ] Teste: busca automatizada detecta segredo simulado e valida mascaramento de log.
  - [ ] Evidência: inventário classificado e revisão de campos enviados.
  - [ ] Commit esperado: `docs(seguranca): inventariar superficie operacional`.
- [ ] **T04.2 — Definir gestão de segredos e JWT**
  - [ ] Aprovar Key Vault/identidade e registrar rotação, contingência e impacto de sessão.
  - [ ] Teste: deploy sem rotação preserva JWT; rotação controlada invalida apenas conforme política.
  - [ ] Evidência: runbook sem valores, permissões e logs de teste mascarados.
  - [ ] Commit esperado: `sec(operacao): gerir segredos e jwt`.
- [ ] **T04.3 — Formalizar dados e privacidade**
  - [ ] Obter decisão de retenção/LGPD e aplicar minimização aprovada à telemetria.
  - [ ] Teste: payload sintético não aparece em campos proibidos de log/trace.
  - [ ] Evidência: política aprovada e relatório de revisão.
  - [ ] Commit esperado: `docs(seguranca): definir privacidade do piloto`.
- [ ] **T04.4 — Exercitar recuperação**
  - [ ] Criar runbooks de backup/restore isolados para PostgreSQL e Qdrant.
  - [ ] Teste: restore controlado, consulta de banco, coleção e smoke RAG.
  - [ ] Evidência: tempo observado, integridade e diferenças conhecidas.
  - [ ] Commit esperado: `docs(operacao): testar recuperacao de dados`.
- [ ] **T04.5 — Configurar alertas aprovados**
  - [ ] Definir orçamento, métricas, canais e escalonamento.
  - [ ] Teste: simular falha/API, job de ingestão, banco e custo quando suportado.
  - [ ] Evidência: regras, notificações de teste e owner.
  - [ ] Commit esperado: `ops(seguranca): adicionar alertas operacionais`.

## 8. Estratégia de testes e validação

| Camada | Cenário | Automação | Comando / evidência |
|---|---|---|---|
| Unitária | Mascaramento, configuração e política de JWT. | Sim | Pytest direcionado, sem segredo real. |
| Integração | Deploy controlado e persistência de sessão; restore isolado. | Parcial | Ambiente não público com dados demo. |
| CI | Scan de segredo e validações estáticas. | Sim, após T04.2 | Relatório do workflow sem conteúdo sensível. |
| Azure | Backup/restore, Key Vault/identidade e alertas. | Manual/automatizado após aprovação | Logs de operação, alertas de teste e smoke. |

## 9. Encerramento

### Gates e reversibilidade

| Gate | Estado documental atual | Condição / evidência futura |
|---|---|---|
| G0 — Baseline | Concluído | Bicep, deploy e P0 inventariados. |
| G1 — Especificação | Concluído | Este documento; bloqueios legal/arquitetural explícitos. |
| G2 — Implementação | Não iniciado | Commits T04.1–T04.5. |
| G3 — Verificação | Não iniciado | Testes de mascaramento, JWT, restore e alertas. |
| G4 — Operação | Não iniciado | Exercícios Azure e alertas aprovados. |
| G5 — Encerramento | Não iniciado | Evidências e checklists legados reconciliados. |

Reversão de secret store/identidade deve preservar o segredo ativo até uma
migração validada; rotação possui rollback somente enquanto a política permitir
aceitar a chave anterior. Restores nunca são revertidos sobre produção sem
procedimento aprovado: validar em cópia isolada primeiro.

### Definition of Done

- [ ] Segredos, JWT, dados/telemetria e privacidade possuem decisões e evidência.
- [ ] Restore de PostgreSQL e Qdrant foi exercitado isoladamente.
- [ ] Alertas aprovados foram disparados de modo controlado.
- [ ] Nenhum segredo ou PII foi introduzido em código, documentação ou evidência.
- [ ] Checklists legados só foram atualizados junto da implementação validada.
