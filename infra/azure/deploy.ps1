<#
.SYNOPSIS
  Publica o UsiEdu no Azure Container Apps.

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
    [string]$OpenCodeApiKey,
    [string]$LangSmithApiKey,
    [string]$JwtSecret,
    [string]$PostgresAdminPassword
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

az extension add --name containerapp --upgrade --only-show-errors | Out-Null
az group create --name $ResourceGroup --location $Location --only-show-errors | Out-Null

$registryName = ("{0}acr{1}" -f $Prefix.Replace('-', ''), (Get-Random -Minimum 100000 -Maximum 999999)).ToLower()
$registry = az deployment group create `
    --resource-group $ResourceGroup `
    --template-file infra/azure/registry.bicep `
    --parameters registryName=$registryName location=$Location `
    --query properties.outputs.loginServer.value -o tsv

az acr login --name $registryName --only-show-errors | Out-Null
$apiImage = "$registry/usiedu-api:$ImageTag"
$frontendImage = "$registry/usiedu-frontend:$ImageTag"

docker build --file Dockerfile.api --tag $apiImage .
docker push $apiImage
docker build --file Dockerfile.frontend --tag $frontendImage .
docker push $frontendImage

$registryCredentials = az acr credential show --name $registryName --query '{username:username,password:passwords[0].value}' -o json | ConvertFrom-Json
if (-not $OpenCodeApiKey) { $OpenCodeApiKey = Read-RequiredSecret 'OPENCODE_GO_API_KEY' }
if (-not $LangSmithApiKey) { $LangSmithApiKey = Read-RequiredSecret 'LANGSMITH_API_KEY' }
if (-not $JwtSecret) {
    $JwtSecret = python -c "import secrets; print(secrets.token_urlsafe(32))"
    Write-Host 'JWT_SECRET gerado para este deploy. Guarde-o em um gerenciador de segredos.' -ForegroundColor Yellow
}
if (-not $PostgresAdminPassword) {
    $PostgresAdminPassword = python -c "import secrets; print(secrets.token_urlsafe(32))"
    Write-Host 'Senha PostgreSQL gerada para este deploy. Guarde-a em um gerenciador de segredos.' -ForegroundColor Yellow
}

$deploymentJson = az deployment group create `
    --resource-group $ResourceGroup `
    --template-file infra/azure/main.bicep `
    --parameters `
        namePrefix=$Prefix `
        location=$Location `
        apiImage=$apiImage `
        frontendImage=$frontendImage `
        registryLoginServer=$registry `
        registryUsername=$($registryCredentials.username) `
        registryPassword=$($registryCredentials.password) `
        jwtSecret=$JwtSecret `
        opencodeApiKey=$OpenCodeApiKey `
        langsmithApiKey=$LangSmithApiKey `
        postgresAdminPassword=$PostgresAdminPassword `
    --query properties.outputs -o json
if ($LASTEXITCODE -ne 0) {
    throw 'Deploy ARM falhou. Consulte as operacoes do deployment para obter detalhes.'
}

$result = ($deploymentJson -join [Environment]::NewLine) | ConvertFrom-Json
if (-not $result.frontendUrl.value -or -not $result.ingestJobName.value) {
    throw 'Deploy ARM nao retornou os outputs esperados.'
}

Write-Host "Deploy concluído: $($result.frontendUrl.value)" -ForegroundColor Green
Write-Host "Execute agora: az containerapp job start --name $($result.ingestJobName.value) --resource-group $ResourceGroup"
Write-Host "Depois, acompanhe: az containerapp job execution list --name $($result.ingestJobName.value) --resource-group $ResourceGroup"
