# db_down.ps1 — Para PostgreSQL (mantiene los datos)
# Uso: .\scripts\db_down.ps1

Set-Location $PSScriptRoot\..

Write-Host "Parando PostgreSQL..." -ForegroundColor Cyan
docker compose stop postgres
Write-Host "PostgreSQL parado. Los datos se conservan en el volumen." -ForegroundColor Green
