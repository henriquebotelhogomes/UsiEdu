# P0 - Validacao do Piloto Publico no Azure

> Registro operacional de evidencia da P0. Este arquivo registra somente fatos
> observados no Azure; nao define uma nova arquitetura, nao contem segredos e
> nao altera o escopo do piloto.

## T-P0.1 - Baseline do Azure

**Status:** concluida em 2026-08-11 09:41 BRT.

### Evidencia observada

| Item | Estado observado |
|---|---|
| Grupo de recursos | `rg-usiedu` em `brazilsouth` |
| Ambiente Container Apps | `usiedu-env`, provisionamento concluido |
| Frontend publico | `https://usiedu-frontend.calmtree-d18b7257.brazilsouth.azurecontainerapps.io/` |
| API | `usiedu-api`, ingress interno, revisao `usiedu-api--0000012` provisionada e escalada a zero |
| Qdrant | `usiedu-qdrant`, ingress interno, revisao `usiedu-qdrant--lt691co` em execucao com uma replica |
| Frontend | `usiedu-frontend`, revisao `usiedu-frontend--0000006` provisionada e escalada a zero |
| Ingestao | job `usiedu-ingest`; ultima execucao em 2026-08-11 00:34-00:36 UTC com status `Succeeded` |
| Estado transacional | PostgreSQL Flexible Server 16, estado `Ready`, SKU `Standard_B1ms`, 32 GiB |
| Imagens | ACR contem os repositorios privados `usiedu-api` e `usiedu-frontend` |

### Riscos e bloqueios conhecidos

- O ambiente escala frontend e API a zero; P0.2 precisa medir a primeira requisicao
  sem confundir cold start com indisponibilidade.
- O historico do job de ingestao contem cinco execucoes antigas com falha antes da
  ultima sequencia bem-sucedida. P0.3 deve verificar logs e procurar explicitamente
  encerramentos com codigo 137.
- Os artefatos `PLANO_PROFISSIONALIZACAO.md`,
  `docs/profissionalizacao/README.md` e
  `docs/profissionalizacao/00-prd-programa.md`, citados como fontes normativas
  da P0, nao existem neste checkout nem em `origin/main`. A validacao funcional
  dependente do runbook ausente permanece bloqueada ate que sua fonte seja
  restaurada ou fornecida.

### Reproducao sem segredos

```powershell
az containerapp list --resource-group rg-usiedu `
  --query "[].{name:name,state:properties.provisioningState,revision:properties.latestRevisionName,fqdn:properties.configuration.ingress.fqdn,external:properties.configuration.ingress.external}" `
  -o table

az containerapp job execution list --name usiedu-ingest --resource-group rg-usiedu `
  --query "[].{name:name,status:properties.status,start:properties.startTime,end:properties.endTime}" `
  -o table

az postgres flexible-server show --name usiedu-pg-j6p4znlvml25e --resource-group rg-usiedu `
  --query "{state:state,version:version,sku:sku.name,storageGb:storage.storageSizeGb}" -o json
```

## T-P0.2 - Fluxo funcional publico

**Status:** concluida com falha em 2026-08-11.

| Etapa | Resultado | Evidencia |
|---|---|---|
| Landing HTTPS | aprovada | A pagina publica carregou em `https://usiedu-frontend.calmtree-d18b7257.brazilsouth.azurecontainerapps.io/` e exibiu a navegacao e o CTA de acesso. |
| Health pela origem publica | aprovada | `GET /health` retornou HTTP 200 e `status: ok` em 24,30 s durante o acionamento inicial. |
| Login demo | falhou | A selecao da conta demo visivel na tela preencheu o formulario, mas o envio terminou em `Erro de autenticacao`. |
| Chat RAG, feedback e `/insights` | nao executados | Dependem de uma sessao autenticada; bloqueados pela falha de login. |

O navegador usado para a evidencia foi uma sessao isolada e a selecao da conta
demo foi feita pela propria tela, sem registrar senha ou token. A falha atende
ao gatilho de T-P0.4, mas a coleta de latencia e logs de T-P0.3 deve preceder
o diagnostico e a correcao.

## T-P0.3 - Latencia e observabilidade

**Status:** concluida com falha em 2026-08-11.

| Verificacao | Resultado | Evidencia |
|---|---|---|
| Resposta aquecida | aprovada isoladamente | Tres chamadas consecutivas a `GET /health` retornaram HTTP 200 em 164 ms, 51 ms e 58 ms; apos a recuperacao do cold start, outra chamada retornou 200 em 250 ms. |
| Cold start | falhou | A primeira chamada apos periodo superior ao cooldown de 300 s retornou HTTP 504 em 81,72 s. O frontend registrou timeout do upstream; novas replicas de frontend e API foram criadas durante a tentativa e a API ficou pronta somente no fim do timeout. |
| Reinicio da replica atual | aprovado isoladamente | A replica recuperada da API estava `Running`, `ready: true` e com `restartCount: 0`. |
| Exit 137 e OOM | falhou | Consulta agregada dos ultimos tres dias encontrou 13 eventos com `137` nos logs de sistema da API e 1 no console; nao houve ocorrencia textual de `OOM`. |

Comandos de evidencia sem segredos:

```powershell
az containerapp show --name usiedu-api --resource-group rg-usiedu `
  --query "{scale:properties.template.scale,revision:properties.latestRevisionName}" -o json

az containerapp logs show --name usiedu-api --resource-group rg-usiedu `
  --type system --tail 200

$workspaceId = az monitor log-analytics workspace show --resource-group rg-usiedu `
  --workspace-name usiedu-logs --query customerId -o tsv
az monitor log-analytics query --workspace $workspaceId --analytics-query `
  "ContainerAppSystemLogs_CL | where TimeGenerated > ago(3d) | where ContainerAppName_s == 'usiedu-api' | summarize total=count(), exit137=countif(Log_s has '137'), oom=countif(Log_s has 'OOM')" -o json
```

O 504 em cold start e os eventos 137 impedem o aceite T9.4 e exigem T-P0.4:
diagnostico, teste de regressao e a menor correcao possivel.

## T-P0.4 - Diagnostico e correcao minima

**Status:** concluida em 2026-08-11.

### Diagnostico

- Os eventos exit 137 pertencem somente as revisoes `usiedu-api--0000006`,
  `usiedu-api--0000007` e `usiedu-api--0000011`. A revisao atual
  `usiedu-api--0000012`, com 2 vCPU e 4 GiB, retornou zero eventos 137 na
  consulta equivalente.
- O timeout ativo e independente da autenticacao: o nginx retornou 504 para
  `POST /auth/login` antes de receber o header da API, enquanto a API registrou
  HTTP 200 para a mesma solicitacao apos terminar o bootstrap.
- O `proxy_read_timeout` padrao de 60 s e menor que o cold start observado. A
  primeira correcao para 120 s ainda foi insuficiente para a nova ativacao da
  API; o limite final de 180 s cobre a ativacao observada sem alterar a API,
  autenticacao ou topologia Azure.

### Correcao e teste de regressao

- `tests/unit/test_deploy_config.py::test_frontend_proxy_allows_api_cold_start`
  foi criado antes da implementacao, falhou sem a diretiva e passou depois dela.
  A segunda iteracao exigiu 180 s, tambem falhou antes da mudanca e passou apos
  a implementacao.
- `frontend/nginx/default.conf.template` declara
  `proxy_read_timeout 180s;`; o streaming conserva o timeout especifico de
  300 s.
- A normalizacao de `TIMESTAMPTZ` do PostgreSQL em `/feedback/recent` tambem
  recebeu teste de regressao antes da implementacao; isso corrigiu o 500 de
  `/insights` que SQLite nao reproduzia.
- Commits de correcao: `0b3e284`, `d562c21` e `f361433`.

### Publicacao e revalidacao

As imagens foram publicadas depois que Docker Desktop foi iniciado:

| Componente | Revisao publicada | Imagem |
|---|---|---|
| Frontend | `usiedu-frontend--0000008` | `usiedu-frontend:p0-proxy-timeout-180` |
| API | `usiedu-api--0000013` | `usiedu-api:p0-feedback-timestamp` |

Com API e frontend escalados a zero, o login demo retornou HTTP 200 em
aproximadamente 95 s. O fluxo landing HTTPS -> login demo -> chat RAG composto
com fontes/agentes -> feedback -> `/insights` foi aprovado na URL publica. As
respostas aquecidas de `GET /health` foram 212 ms, 45 ms e 45 ms. A consulta
de logs da revisao `usiedu-api--0000013` retornou zero eventos exit 137.

## T-P0.5 - Reconciliacao documental

**Status:** concluida em 2026-08-11.

README, PRD e checklists legados foram atualizados somente apos a revalidacao
da revisao publicada. T9.4 permanece rastreavel pelos criterios de aceite, sem
ocultar o cold start configurado de ate 180 s.
