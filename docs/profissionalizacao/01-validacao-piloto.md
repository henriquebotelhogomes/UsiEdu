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
