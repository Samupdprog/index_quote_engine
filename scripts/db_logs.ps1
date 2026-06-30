# db_logs.ps1 — Muestra los logs de PostgreSQL
# Uso: .\scripts\db_logs.ps1 [-Follow]

param(
    [switch]$Follow
)

Set-Location $PSScriptRoot\..

if ($Follow) {
    docker compose logs -f postgres
} else {
    docker compose logs --tail=50 postgres
}
