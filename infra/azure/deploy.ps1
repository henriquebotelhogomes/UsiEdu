<#
.SYNOPSIS
  Publica o UsiEdu no Azure Container Apps utilizando GitHub Container Registry (GHCR) e SQLite no Azure Files.

.EXAMPLE
  .\infra\azure\deploy.ps1 -ResourceGroup rg-usiedu -Prefix usiedu -Location brazilsouth
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^[a-z0-9-]{3,20}$')]
    [string]$ResourceGroup,

    [Parameter(Mandatory)]
    [ValidatePattern('^[a-z0-9-]{3,15}$')]
    [string]$Prefix,

    [string]$Location = 'brazilsouth',
    [string]$ImageTag = 'v1',
    [string]$GitHubUser = 'henriquebotelhogomes',
    [string]$OpenCodeApiKey,
    [string]$LangSmithApiKey,
    [string]$JwtSecret
)

$ErrorActionPreference = 'Stop'

function Read-RequiredSecret([string]$Prompt) {
    $value = Read-Host -Prompt $Prompt -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($value)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw 'Azure CLI não encontrado. Instale-o em https://aka.ms/installazurecliwindows.'
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker não encontrado ou não iniciado. Inicie o Docker Desktop antes do deploy.'
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Set-Location $repoRoot

# Carrega chaves de .env se não informadas
$envPath = Join-Path $repoRoot '.env'
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
            $parts = $line.Split('=', 2)
            $k = $parts[0].Trim()
            $v = $parts[1].Split('#')[0].Trim()
            if ($k -eq 'OPENCODE_GO_API_KEY' -and -not $OpenCodeApiKey) { $OpenCodeApiKey = $v }
            if ($k -eq 'LANGSMITH_API_KEY' -and -not $LangSmithApiKey) { $LangSmithApiKey = $v }
            if ($k -eq 'JWT_SECRET' -and -not $JwtSecret) { $JwtSecret = $v }
        }
    }
}

if (-not $OpenCodeApiKey) { $OpenCodeApiKey = Read-RequiredSecret 'OPENCODE_GO_API_KEY' }
if (-not $LangSmithApiKey) { $LangSmithApiKey = Read-RequiredSecret 'LANGSMITH_API_KEY' }
if (-not $JwtSecret) {
    throw 'JWT_SECRET deve ser fornecido explicitamente. Para producao, use o Key Vault e o runbook de migracao.'
}

az extension add --name containerapp --upgrade --only-show-errors | Out-Null
az group create --name $ResourceGroup --location $Location --only-show-errors | Out-Null

$apiImage = "ghcr.io/$($GitHubUser.ToLower())/usiedu-api:$ImageTag"
$frontendImage = "ghcr.io/$($GitHubUser.ToLower())/usiedu-frontend:$ImageTag"

Write-Host "Construindo e enviando imagens para o GHCR: $apiImage e $frontendImage..." -ForegroundColor Cyan

docker build --file Dockerfile.api --tag $apiImage .
docker push $apiImage
docker build --file Dockerfile.frontend --tag $frontendImage .
docker push $frontendImage

Write-Host "Aplicando infraestrutura Bicep no Azure..." -ForegroundColor Cyan

$ghToken = gh auth token

$deploymentJson = az deployment group create `
    --resource-group $ResourceGroup `
    --template-file infra/azure/main.bicep `
    --parameters `
        namePrefix=$Prefix `
        location=$Location `
        apiImage=$apiImage `
        frontendImage=$frontendImage `
        registryLoginServer='ghcr.io' `
        registryUsername=$GitHubUser `
        registryPassword=$ghToken `
        jwtSecret=$JwtSecret `
        opencodeApiKey=$OpenCodeApiKey `
        langsmithApiKey=$LangSmithApiKey `
    --query properties.outputs -o json
if ($LASTEXITCODE -ne 0) {
    throw 'Deploy ARM falhou. Consulte as operacoes do deployment para obter detalhes.'
}

$result = ($deploymentJson -join [Environment]::NewLine) | ConvertFrom-Json
if (-not $result.frontendUrl.value -or -not $result.ingestJobName.value) {
    throw 'Deploy ARM nao retornou os outputs esperados.'
}

Write-Host "Deploy concluído: $($result.frontendUrl.value)" -ForegroundColor Green
Write-Host "Iniciando ingestão de vetores..." -ForegroundColor Cyan
az containerapp job start --name $($result.ingestJobName.value) --resource-group $ResourceGroup
Write-Host "Acompanhe a ingestão com: az containerapp job execution list --name $($result.ingestJobName.value) --resource-group $ResourceGroup"
