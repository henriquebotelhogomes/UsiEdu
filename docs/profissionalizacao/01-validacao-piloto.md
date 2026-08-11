# P0 — Validação do Piloto Público no Azure

| Campo | Valor |
|---|---|
| Estado | Planejado — não iniciar nova melhoria até encerrar ou registrar bloqueio |
| Prioridade | P0 |
| Dono | Henrique Botelho Gomes |
| Ambiente público | `https://usiedu-frontend.calmtree-d18b7257.brazilsouth.azurecontainerapps.io/` |
| Azure | Resource group `rg-usiedu`; apps `usiedu-api`, `usiedu-frontend`, `usiedu-qdrant`; job `usiedu-ingest` |
| Dependências | Azure CLI autenticada, assinatura Azure for Students, credenciais demo e chave LLM vigente |
| Checklists afetados | `PRD.v2.md` T9.4; `docs/08-plano-execucao.md` T9.4; `docs/04-piloto-e-roadmap.md` seção 5; `docs/07-prd-requisitos.md` seção 7 |
| Atualizado em | 11/08/2026 |

## 1. Contexto e evidências

O deploy público já foi provisionado no Azure Container Apps e o job de
ingestão teve pelo menos uma execução bem-sucedida (`usiedu-ingest-3a8se1l`).
A API sofreu encerramento anterior com código 137 durante o carregamento de
modelos RAG; a configuração foi corrigida para 2 vCPUs e 4 GiB na API. Logs da
revisão posterior registraram inicialização de retrievers e `Application
startup complete`.

Ainda faltam evidências confiáveis para encerrar T9.4: login demo, resposta
RAG transmitida até o fim, feedback, `/insights`, saúde dos serviços e ausência
de nova falha de memória. Documentos legados podem conter texto anterior ao
provisionamento; esta iniciativa deve reconciliá-los somente após validação.

## 2. Objetivo mensurável

Demonstrar que um visitante anônimo consegue abrir a landing, autenticar-se com
um usuário demo, receber uma resposta documental do RAG via streaming,
registrar feedback e visualizar `/insights` por HTTPS, sem encerramento da API.

### Métricas a registrar

| Métrica | Como medir | Critério desta iniciativa |
|---|---|---|
| Disponibilidade do fluxo | Navegador em URL pública | Todas as cinco etapas completam. |
| Job de ingestão | Lista de execuções Azure | Execução mais recente `Succeeded`. |
| Startup da API | Logs do Container App | Sem exit code 137; inicialização concluída. |
| Cold start | Cronômetro do navegador | Registrar tempo de abertura e primeira resposta; sem meta nova nesta P0. |
| Resposta documental | Cenário fixo abaixo | Conteúdo e fonte aparecem ao final do stream. |

## 3. Escopo e não escopo

### Escopo

- Validar o deployment existente e registrar evidências reproduzíveis.
- Diagnosticar e corrigir exclusivamente defeitos que impeçam os critérios de
  aceite da T9.4.
- Atualizar README e checklists legados com o estado comprovado.
- Executar a validação local equivalente quando houver alteração de código.

### Não escopo

- Reprojetar cache, agentes, corpus ou métricas RAG.
- Migrar segredos para Key Vault, criar CI/CD ou alterar estratégia de escala.
- Criar uma nova funcionalidade de chat ou busca web.
- Declarar o piloto institucionalmente pronto além dos critérios desta P0.

## 4. Requisitos e critérios de aceite

| ID | Requisito | Critério verificável |
|---|---|---|
| RQ-P0-01 | Landing HTTPS pública | Dado um navegador anônimo, quando abre a URL, então recebe a landing sem aviso de certificado. |
| RQ-P0-02 | Login demo | Dado `ana@demo.usiedu` e `estudante123`, quando enviados, então a tela de chat é aberta sem spinner permanente. |
| RQ-P0-03 | Stream RAG concluído | Dada a pergunta `quais feriados teremos em 2026?`, quando enviada, então a resposta final contém informação do calendário e ao menos uma fonte; não ficam balões vazios nem requisição pendente. |
| RQ-P0-04 | Feedback e insights | Dada uma resposta concluída, quando o usuário envia 👍 ou 👎 e acessa `/insights`, então recebe confirmação e vê dados sem erro de autenticação. |
| RQ-P0-05 | Ingestão disponível | Dada a execução do job manual, quando consultada, então a execução mais recente termina `Succeeded`. |
| RQ-P0-06 | Saúde operacional | Dado o fluxo anterior, quando os logs e estado da API são consultados, então não há nova falha de memória/exit 137 associada à validação. |
| RQ-P0-07 | Documentação reconciliada | Dadas evidências de RQ-P0-01 a RQ-P0-06, quando T9.4 é encerrada, então os três checklists legados e o README registram URL, resultado e cold start real. |

## 5. Decisões, dependências e riscos

| Tipo | Item | Condição | Próximo passo |
|---|---|---|---|
| Decisão | API com 2 vCPUs / 4 GiB | Par válido no plano Consumption; mitigação do OOM observado | Confirmar no app ativo e nos logs. |
| Decisão | `minReplicas: 0` | Cold start é aceitável para piloto com crédito estudantil | Medir e documentar; não alterar nesta P0. |
| Dependência | Chave OpenCode Go válida | Sem ela o stream pode falhar mesmo com RAG saudável | Conferir logs sem expor segredo. |
| Dependência | Corpus ingerido | Pergunta documental depende de Qdrant preenchido | Conferir job `Succeeded` antes do teste RQ-P0-03. |
| Risco | Cache semântico mascara recuperação RAG | A pergunta pode ser respondida de cache | Usar sessão nova e registrar `from_cache`, se exibido; repetir com paráfrase se necessário. |
| Risco | Rate limit bloqueia testes repetidos | Login/chat retornam 429 | Aguardar a janela ou usar o outro usuário demo; não aumentar limite sem requisito. |

## 6. Plano técnico e evidências esperadas

Não há mudança arquitetural planejada. A verificação cobre:

- frontend público (nginx) e proxy para API interna;
- API FastAPI, banco PostgreSQL, Qdrant e modelos RAG;
- job manual `usiedu-ingest` contra o Qdrant interno;
- logs do Azure como evidência de inicialização e falhas;
- navegador como evidência de fluxo HTTPS completo.

Se uma falha impedir um requisito, abrir uma microtarefa corretiva mínima. Ela
deve conter hipótese, teste que a reproduz e condição objetiva de sucesso antes
de qualquer alteração de infraestrutura ou código.

## 7. Tarefas e microtarefas

- [x] **T-P0.1 — Registrar baseline do ambiente Azure** *(evidência registrada em 11/08/2026, 09:27 BRT)*
  - [x] Consultar assinatura, revisão ativa e configuração de recursos da API.
  - [x] Consultar execuções do job de ingestão e logs recentes da API.
  - [x] Registrar, sem segredos, data/hora, revisão, status e resultados em
    uma seção de evidências desta iniciativa.
  - [x] Teste: os comandos Azure retornam o grupo e recursos esperados.

- [ ] **T-P0.2 — Validar fluxo público completo**
  - [ ] Abrir a landing em janela anônima e registrar a URL HTTPS.
  - [ ] Fazer login como Ana; confirmar que a tela de chat abre.
  - [ ] Em nova sessão, perguntar `quais feriados teremos em 2026?` e aguardar
    o evento final do stream.
  - [ ] Enviar feedback e abrir `/insights` na mesma sessão autenticada.
  - [ ] Teste: validar RQ-P0-01 a RQ-P0-04 no navegador, com screenshot sem
    dados sensíveis se for necessário para evidência.

- [ ] **T-P0.3 — Medir latência e verificar saúde**
  - [ ] Após escala a zero ou período de inatividade conhecido, medir tempo de
    abertura da landing e primeira resposta do chat.
  - [ ] Repetir uma pergunta em seguida e medir a resposta aquecida.
  - [ ] Conferir logs por erro, reinício ou exit 137 após os testes.
  - [ ] Teste: registrar valores e conclusão; esta tarefa não impõe meta de
    desempenho nova.

- [ ] **T-P0.4 — Corrigir bloqueio, se houver**
  - [ ] Classificar a falha: frontend/proxy, autenticação, stream/API, LLM,
    banco/Qdrant, job ou capacidade.
  - [ ] Criar teste de regressão antes da correção quando o defeito for
    reproduzível localmente ou por teste de integração.
  - [ ] Aplicar a menor correção dentro do escopo P0; validar localmente,
    publicar e repetir apenas o cenário afetado no Azure.
  - [ ] Evidência: commit atômico, saída de testes, revisão Azure e resultado
    do cenário repetido.

- [ ] **T-P0.5 — Encerrar T9.4 e reconciliar documentação**
  - [ ] Atualizar README com URL pública, latência observada e instruções de
    atualização já comprovadas.
  - [ ] Atualizar T9.4 no PRD v2, plano de execução, critérios de aceite e
    gate de entrega, mantendo pendências reais como `[~]` com motivo.
  - [ ] Registrar nesta página as evidências finais e comunicar resumo, riscos
    restantes e como repetir testes locais.

## 8. Estratégia de testes e validação

### Comandos Azure (PowerShell)

Os comandos abaixo são somente de leitura, exceto o início explícito do job.
Não copiar saídas que contenham segredo para commit, issue ou screenshot.

```powershell
az containerapp job execution list --name usiedu-ingest --resource-group rg-usiedu --output table

az containerapp show --name usiedu-api --resource-group rg-usiedu `
  --query "{provisioning:properties.provisioningState,revision:properties.latestRevisionName}" `
  --output json

az containerapp logs show --name usiedu-api --resource-group rg-usiedu --tail 200
```

Se o job mais recente não for `Succeeded`, iniciar nova execução somente após
inspecionar a causa da falha:

```powershell
az containerapp job start --name usiedu-ingest --resource-group rg-usiedu
```

### Validação local após alteração de código

No diretório raiz do repositório, com o ambiente Python do projeto ativo:

```powershell
docker compose up -d qdrant
$env:PYTHONPATH = (Get-Location).Path
python scripts/ingest_knowledge_base.py
Remove-Item Env:PYTHONPATH
pytest tests -q --ignore=tests/integration
ruff check .
ruff format --check .
```

Para executar a API localmente em outro terminal:

```powershell
uvicorn src.api.main:app --reload --port 8000
```

O frontend deve apontar para essa API conforme o quickstart do README. Testar
login, a pergunta documental e feedback no navegador local antes de publicar
uma correção de código.

### Matriz de validação

| Camada | Cenário | Evidência |
|---|---|---|
| Unitária | Correção de defeito reproduzível | Teste novo ou atualizado e `pytest` verde. |
| Local | API, Qdrant e cenário afetado | Comandos acima e navegador local. |
| Azure | Job e estado da API | Saídas Azure sem segredo e logs sem exit 137. |
| Pública | Landing → login → chat → feedback → insights | Data/hora, URL, resultado de cada etapa e screenshot opcional. |

## 9. Registro de evidências e encerramento

Adicionar abaixo uma entrada por validação concluída. Nunca registrar tokens,
senhas, JWTs, chaves de LLM ou connection strings.

| Data/hora BRT | Revisão API | Job mais recente | Fluxo público | Cold / aquecido | Logs | Responsável |
|---|---|---|---|---|---|---|
| 11/08/2026 09:27 | `usiedu-api--0000012`; `Succeeded`; 2 vCPUs / 4 GiB; `minReplicas=0`, `maxReplicas=1` | `usiedu-ingest-n8wsoms`; `Succeeded` em 11/08/2026 00:34 UTC | Ainda não validado (T-P0.2) | Ainda não medido (T-P0.3) | Consulta dos 200 logs mais recentes, filtrada por startup/erro/OOM/exit 137, sem ocorrências correspondentes | Henrique |

### Baseline T-P0.1 — 11/08/2026 09:27 BRT

- Assinatura Azure for Students autenticada; resource group `rg-usiedu`
  acessível.
- `usiedu-api` está provisionado com sucesso na revisão
  `usiedu-api--0000012`, com API interna na porta 8000, 2 vCPUs, 4 GiB e
  escala configurada de zero a uma réplica.
- O job manual `usiedu-ingest` tem execução mais recente
  `usiedu-ingest-n8wsoms` com status `Succeeded` em 11/08/2026 00:34 UTC.
- A consulta sanitizada dos 200 logs mais recentes da API não encontrou linhas
  com `Application startup complete`, `ERROR`, `CRITICAL`, `OOM` ou `exit 137`.
  A ausência de `exit 137` após o fluxo público será verificada novamente em
  T-P0.3.

- [ ] RQ-P0-01 a RQ-P0-06 validados com evidências na tabela.
- [ ] `README.md`, `PRD.v2.md`, `docs/08-plano-execucao.md`,
  `docs/04-piloto-e-roadmap.md` e `docs/07-prd-requisitos.md` reconciliados.
- [ ] Testes e Ruff executados na abrangência necessária às alterações.
- [ ] Commit atômico criado para cada microtarefa que alterou arquivos.
- [ ] Resumo entregue ao proprietário: o que mudou, evidências, como testar
  localmente e riscos restantes.
