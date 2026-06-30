# db_up.ps1 — Arranca PostgreSQL con Docker Compose
# Uso: .\scripts\db_up.ps1

Set-Location $PSScriptRoot\..

Write-Host "Arrancando PostgreSQL (eon-index-postgres)..." -ForegroundColor Cyan
docker compose up -d postgres

if ($LASTEXITCODE -ne 0) {
    Write-Error "Error al arrancar PostgreSQL."
    exit 1
}

Write-Host "Esperando healthcheck..." -ForegroundColor Yellow
$maxWait = 30
$waited = 0
do {
    Start-Sleep -Seconds 2
    $waited += 2
    $status = docker inspect --format='{{.State.Health.Status}}' eon-index-postgres 2>$null
    Write-Host "  Estado: $status ($waited s)" -ForegroundColor Gray
} while ($status -ne "healthy" -and $waited -lt $maxWait)

if ($status -eq "healthy") {
    Write-Host "PostgreSQL listo." -ForegroundColor Green
} else {
    Write-Warning "PostgreSQL no reportó 'healthy' en $maxWait s. Comprueba: docker logs eon-index-postgres"
}
