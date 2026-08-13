# P1 — Segurança e continuidade operacional

| Campo | Valor |
|---|---|
| Estado | Em andamento — T04.1–T04.3 concluídas; T04.4–T04.5 pendentes |
| Prioridade | P1 |
| Dono | Henrique Botelho Gomes |
| Dependências | [PRD do programa](00-prd-programa.md), `infra/azure/main.bicep`, `infra/azure/deploy.ps1`, `src/security/guardrails.py`, `src/observability/` |
| Documentos normativos | `PLANO_PROFISSIONALIZACAO.md`; `PRD.v2.md` RF2-09–11 e T9.4; `docs/03-rag-e-infraestrutura.md` §§ 7, 10 e 11; `docs/04-piloto-e-roadmap.md` §§ 5 e 7; `docs/07-prd-requisitos.md` RNF-05–06; `docs/08-plano-execucao.md` T9.1–T9.4; `docs/09-contratos-tecnicos.md` §§ 2–3 |
| Checklists legados afetados | `docs/08-plano-execucao.md` T9.4; `docs/04-piloto-e-roadmap.md` § 5; `docs/07-prd-requisitos.md` § 7. Não alterar status nesta especificação. |
| Atualizado em | 2026-08-12 |

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
documentado. A configuração técnica atual inclui retenção PostgreSQL de sete
dias, ausência de HA/geo-backup e Log Analytics com 30 dias no Bicep; isso não
é política LGPD aprovada. Para o piloto, RPO de 24 h e RTO de 4 h são decisões
provisórias revisáveis; retenção jurídica, orçamento aprovado e dados jurídicos
não são inventados.

## 3. Escopo e não escopo

### Escopo

- Azure Key Vault + Managed Identity, com retirada da dependência operacional
  de ACR admin após migração validada.
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
| RQ-SEC-03 | Telemetria deve ter inventário e minimização; retenção só é declarada quando aprovada. | Para cada campo enviado a logs/LangSmith, então há finalidade, classificação e mascaramento/remoção. Até revisão, só metadados operacionais mínimos de dados demo/sintéticos (revisão, timestamps, status) são permitidos; pergunta/resposta, token, senha, JWT e identificadores pessoais são vedados em novos campos/uso externo. |
| RQ-SEC-04 | O piloto não pode admitir usuários externos nem dados pessoais até haver política aprovada, canal formal e controlador identificado. | Enquanto o gate vigorar, somente contas demo e dados sintéticos são aceitos; a publicação de política só ocorre após fatos jurídicos reais. |
| RQ-SEC-05 | Estado PostgreSQL e Qdrant deve ser recuperável para o RPO provisório de 24 h e RTO provisório de 4 h. | Exercício restaura cópia autorizada e comprova integridade por consulta/smoke sem sobrescrever produção, registrando tempos contra os objetivos. |
| RQ-SEC-06 | Falhas e custo devem ser detectáveis. | Simulação/consulta controlada produz alerta de API, ingestão e banco por GitHub issue/Action e Azure Monitor; o limite financeiro usa orçamento Azure factual ou permanece parametrizável. |

## 5. Decisões, dependências e riscos

| Tipo | Item | Dono / condição | Mitigação ou próximo passo |
|---|---|---|---|
| Decisão tomada | Dados do piloto são demo; PII real não é requisito. | RNF-05. | Não introduzir PII para validar telemetria. |
| Decisão tomada | PostgreSQL é o estado transacional; Qdrant usa Azure Files. | `docs/03` § 10 e Bicep. | Exercícios devem cobrir ambos. |
| Decisão tomada | Backup PostgreSQL configurado: 7 dias; geo-backup e HA desabilitados. | `main.bicep`. | Tratar como baseline, não como garantia de recuperação testada. |
| Decisão provisória | Segredos usam Azure Key Vault + Managed Identity; a dependência operacional de ACR admin é eliminada somente após migração validada. | Revisar após identidade, RBAC mínimo e pull de imagem com MI validados no Azure. | T04.1/T04.2 podem inventariar e desenhar migração sem valores; aplicação para no acesso Azure. |
| Gate explícito legal | Sem controlador jurídico identificado, canal formal e política/retenção aprovada, o piloto fica restrito a conta demo e dados sintéticos; não admite usuários externos ou dados pessoais. | Revisar somente com fatos jurídicos aprovados, sem inferir e-mail, controlador ou prazo. | T04.3 pode inventariar/minimizar e preparar conteúdo local; para antes de publicar política ou ampliar o público. O LangSmith existente deve ser auditado antes de ampliar payloads, não é aprovação para novos dados. |
| Decisão provisória | RPO é 24 h e RTO é 4 h para PostgreSQL e Qdrant no piloto. | Revisar após primeiro restore isolado, mudança de arquitetura ou exigência de produto. | T04.4 pode criar o protocolo e medir; a aprovação final depende da evidência de restore. |
| Decisão provisória | Alertas técnicos usam GitHub issue/Action e Azure Monitor. | Revisar quando canal formal de operação for aprovado. | T04.5 pode desenhar e testar alertas nesses canais sem inventar e-mail/Teams. |
| Gate explícito financeiro | Usar orçamento Azure existente somente se verificado; caso contrário, o teto financeiro fica parametrizável. | Requer acesso à assinatura/configuração Azure. | A ausência de valor não bloqueia testes técnicos, apenas a ativação de alerta financeiro com limiar concreto. |
| Risco | Rotação inesperada de JWT encerra todas as sessões. | Deploy atual pode gerar segredo. | Separar provisionamento de rotação e testar continuidade. |
| Risco | Restore incompleto deixa Qdrant e PostgreSQL inconsistentes. | Estados são diferentes. | Exercício isolado e checklist de consistência. |

## 6. Plano técnico

A futura implementação começará por inventário sem valores de segredo:
`deploy.ps1`, parâmetros Bicep, variáveis do Container App, GitHub Actions,
logs JSON e configuração LangSmith. A migração de segredo só ocorre após
definir identidade e permissões de menor privilégio em Key Vault/Managed
Identity; nenhum segredo será copiado para documento, output de CI ou comando
histórico. A configuração atual de ACR admin, factual no Bicep e no script de
deploy, só será removida após pull autenticado por MI comprovado.

O teste de recuperação deve usar cópia/ambiente isolado. Para PostgreSQL,
registrar origem, ponto de recuperação e consulta de integridade. Para Qdrant,
registrar método de backup do Azure Files, versão do manifest e consulta de
coleção. A consistência entre corpus/manifest e coleção deve ser verificada
antes de qualquer retorno. O exercício compara o tempo observado com RPO 24 h
e RTO 4 h. Alertas precisam usar métricas/logs realmente disponíveis no Azure,
GitHub issue/Action e Azure Monitor; nenhum e-mail, Teams ou orçamento é
presumido.

### Inventário T04.1

O inventário versionado em `src/security/operational_inventory_v1.json` registra
quatro superfícies classificadas sem valores: segredos runtime, telemetria,
estado persistente e permissões de entrega. Ele referencia a configuração Bicep,
o caminho de deploy, workflows OIDC, configurações locais e módulos de API,
feedback, cache e tracing.

O diagnóstico é rastreável e preserva os gates: a migração Key Vault/Managed
Identity e a retirada do ACR admin foram validadas na execução aprovada
`31659709461`; a minimização de payloads LangSmith, política pública e usuários
externos seguem bloqueados pelo gate legal; o restore isolado segue para T04.4.
Como proteção imediata, o formatter JSON mascara recursivamente campos de
segredo antes de serializar logs. O bootstrap manual agora exige JWT explícito,
evitando gerar uma chave que invalidaria sessões em um deploy normal.

### Runbook T04.2

`infra/azure/security-foundation.bicep` cria, sem parâmetros de segredo, um
Key Vault com RBAC, uma identidade atribuída pelo usuário e somente os papéis
`AcrPull` e `Key Vault Secrets User` para o runtime. O deployment principal do
workflow recebe `Key Vault Secrets Officer` no cofre e `Container Apps
Contributor` apenas no ambiente gerenciado, além de `Container Apps Jobs
Contributor` somente no job de ingestão. O ACR recebe `Contributor` somente no
recurso do registry, pois é o menor papel built-in disponível para desativar o
admin após o smoke; esses papéis permitem copiar os valores ativos e atribuir a
identidade sem os registrar.

Após aplicar essa fundação e configurar as referências não secretas de cofre e
identidade como variáveis de Actions, o workflow manual
`.github/workflows/migrate-azure-secrets.yml` exige `main` e aprovação do
Environment `production`. Ele lê os segredos ativos em memória, preserva o
mesmo JWT, grava as versões no Key Vault, muda API/frontend para pull com
identidade e referências `keyvaultref`, configura também o job de ingestão,
reinicia a revisão da API, executa health público e só então desativa o ACR
admin. A extensão beta de Container Apps pode retornar erro após atribuir uma
identidade ao job; o runbook só continua após consultar o ARM e confirmar a
identidade, mantendo falhas reais bloqueantes. O artefato contém identificadores
de execução, cofre e identidade, nunca valores de segredo.

A execução aprovada `31659709461` concluiu a migração, o reinício, o smoke e a
desativação do ACR admin. A verificação posterior confirmou a identidade de
runtime e o registry autenticado por identidade na API, frontend e job; nenhuma
das três configurações mantém `registry-password`; o ACR permanece com admin
desativado; e `/health` retornou `status: ok`. O artefato sanitizado da execução
registra somente o SHA, o ID da execução, o cofre e a identidade. Valores de
segredo não foram lidos para evidência.

Rotação é uma operação separada e aprovada: publicar uma nova versão no Key
Vault, atualizar uma única referência, validar login e health e manter a versão
anterior durante a janela de reversão. Se a validação falhar, a referência volta
para a versão anterior; nenhum segredo é impresso em logs ou evidência.

## 7. Tarefas e microtarefas

- [x] **T04.1 — Inventariar superfície operacional**
  - [x] Mapear segredos, fluxos de dados, logs, LangSmith, persistência e permissões sem valores. *(`src/security/operational_inventory_v1.json` classifica as quatro superfícies e referencia cada caminho técnico sem registrar valores.)*
  - [x] Teste: busca automatizada detecta segredo simulado e valida mascaramento de log. *(`tests/unit/test_operational_hygiene.py` cobre atribuições simuladas, campos recursivos e o formatter JSON.)*
  - [x] Evidência: inventário classificado e revisão de campos enviados. *(Os campos sensíveis são substituídos por `[REDACTED]` antes da serialização; os gates de Key Vault/MI, privacidade e restore permanecem rastreados no inventário.)*
  - [x] Commit: `docs(seguranca): inventariar superficie operacional`.
- [x] **T04.2 — Definir gestão de segredos e JWT**
  - [x] Registrar migração para Key Vault/Managed Identity, menor privilégio, rotação, contingência e retirada de ACR admin após validação.
  - [x] Teste: o contrato determinístico exige que o bootstrap receba JWT explícito, a promoção só atualize imagens e o runbook preserve o valor ativo; rotação continua operação separada e aprovada.
  - [x] Evidência: execução `31659709461`, artefato sanitizado, referências Key Vault/MI e health público aprovados; nenhum valor foi registrado.
  - [x] Commit: `fix(azure): impedir jwt automatico`.
- [x] **T04.3 — Formalizar dados e privacidade**
  - [x] Aplicar a restrição demo/sintética e inventariar minimização; política pública, controlador, canal formal, retenção e usuários externos permanecem bloqueados até fatos aprovados.
  - [x] Teste: payload sintético e identificadores não aparecem em campos proibidos de log/trace; o cliente LangSmith e o feedback ocultam conteúdo.
  - [x] Evidência: execução aprovada `31661521278` confirmou as quatro flags de ocultação e health `ok`; o artefato sanitizado não contém payload, resposta, identificador pessoal ou segredo.
  - [x] Commit: `fix(privacidade): minimizar telemetria externa`.
- [ ] **T04.4 — Exercitar recuperação**
  - [ ] Criar runbooks de backup/restore isolados para PostgreSQL e Qdrant.
  - [ ] Teste: restore controlado, consulta de banco, coleção e smoke RAG.
  - [ ] Evidência: tempo observado, integridade e diferenças conhecidas.
  - [ ] Commit esperado: `docs(operacao): testar recuperacao de dados`.
- [ ] **T04.5 — Configurar alertas aprovados**
  - [ ] Usar GitHub issue/Action e Azure Monitor para alertas técnicos; usar orçamento Azure somente se factual, mantendo teto financeiro parametrizável caso contrário.
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
| G1 — Especificação | Concluído | Este documento define Key Vault/MI, RPO/RTO, alertas e gate legal; acesso Azure, fato jurídico e orçamento concreto bloqueiam somente as execuções dependentes. |
| G2 — Implementação | Em andamento | T04.1–T04.3 concluídas; T04.4–T04.5 permanecem. |
| G3 — Verificação | Em andamento | T04.1 cobre mascaramento; T04.2 cobre migração, JWT, health e ACR; T04.3 cobre logs e tracing minimizados; restore e alertas permanecem. |
| G4 — Operação | Em andamento | Migração e minimização Azure aprovadas e validadas; exercícios de recuperação e alertas permanecem. |
| G5 — Encerramento | Não iniciado | Evidências e checklists legados reconciliados. |

Reversão de secret store/identidade deve preservar o segredo ativo até uma
migração validada; rotação possui rollback somente enquanto a política permitir
aceitar a chave anterior. Restores nunca são revertidos sobre produção sem
procedimento aprovado: validar em cópia isolada primeiro.

### Definition of Done

- [x] Segredos, JWT, dados/telemetria e privacidade possuem decisões, gate legal e evidência sem declarar fato jurídico inexistente.
- [ ] Restore de PostgreSQL e Qdrant foi exercitado isoladamente.
- [ ] Alertas aprovados foram disparados de modo controlado.
- [ ] Nenhum segredo ou PII foi introduzido em código, documentação ou evidência.
- [ ] Checklists legados só foram atualizados junto da implementação validada.
