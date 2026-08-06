# UsiEdu - Script de desenvolvimento local
# Uso: powershell -File scripts/dev.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== UsiEdu - Ambiente de Desenvolvimento ===" -ForegroundColor Cyan

# 1. Subir Qdrant
Write-Host ""
Write-Host "[1/3] Subindo Qdrant..." -ForegroundColor Yellow
docker compose up -d qdrant

# 2. Aguardar Qdrant ficar pronto
Write-Host "[2/3] Aguardando Qdrant ficar pronto..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
do {
    $attempt++
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:6333/healthz" -TimeoutSec 2 -ErrorAction Stop
        $healthy = $true
    } catch {
        $healthy = $false
        Start-Sleep -Seconds 2
    }
} while (-not $healthy -and $attempt -lt $maxAttempts)

if ($healthy) {
    Write-Host "  Qdrant pronto!" -ForegroundColor Green
} else {
    Write-Host "  AVISO: Qdrant nao respondeu em tempo." -ForegroundColor Red
    Write-Host "  Verifique: docker compose logs qdrant" -ForegroundColor Red
    exit 1
}

# 3. Iniciar API (quando implementada)
Write-Host "[3/3] Verificando API..." -ForegroundColor Yellow
$apiMain = Join-Path $PSScriptRoot "..\src\api\main.py"
if (Test-Path $apiMain) {
    Write-Host "  Iniciando FastAPI..." -ForegroundColor Green
    Set-Location (Join-Path $PSScriptRoot "..")
    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
} else {
    Write-Host "  API ainda nao implementada (serah criada na Sprint 2)." -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "=== Qdrant disponivel em http://localhost:6333 ===" -ForegroundColor Cyan
    Write-Host "=== Ambiente pronto para desenvolvimento! ===" -ForegroundColor Green
}
