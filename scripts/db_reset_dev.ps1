# db_reset_dev.ps1 — DESTRUYE y recrea la base de datos de desarrollo
# CUIDADO: elimina todos los datos. Solo para desarrollo.
# Uso: .\scripts\db_reset_dev.ps1

Set-Location $PSScriptRoot\..

$confirm = Read-Host "ADVERTENCIA: Esto borrara todos los datos de la BD de desarrollo. Escribe 'SI' para confirmar"
if ($confirm -ne "SI") {
    Write-Host "Operacion cancelada." -ForegroundColor Yellow
    exit 0
}

Write-Host "Parando contenedor..." -ForegroundColor Cyan
docker compose down postgres

Write-Host "Eliminando volumen..." -ForegroundColor Cyan
docker volume rm eon_postgres_data 2>$null

Write-Host "Recreando contenedor..." -ForegroundColor Cyan
docker compose up -d postgres

Write-Host "Esperando healthcheck..." -ForegroundColor Yellow
$maxWait = 30
$waited = 0
do {
    Start-Sleep -Seconds 2
    $waited += 2
    $status = docker inspect --format='{{.State.Health.Status}}' eon-index-postgres 2>$null
} while ($status -ne "healthy" -and $waited -lt $maxWait)

if ($status -eq "healthy") {
    Write-Host "BD recreada y lista." -ForegroundColor Green
    Write-Host "Aplica migraciones con: python -m alembic upgrade head" -ForegroundColor Yellow
} else {
    Write-Warning "PostgreSQL no respondio en $maxWait s."
}
