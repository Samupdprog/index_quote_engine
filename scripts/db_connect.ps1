# db_connect.ps1 — Abre psql interactivo dentro del contenedor
# Uso: .\scripts\db_connect.ps1

Set-Location $PSScriptRoot\..

# Carga .env si existe
if (Test-Path ".env") {
    Get-Content ".env" | Where-Object { $_ -match "^[A-Z_]+=.+" } | ForEach-Object {
        $parts = $_ -split "=", 2
        [System.Environment]::SetEnvironmentVariable($parts[0], $parts[1])
    }
}

$db   = $env:POSTGRES_DB   ?? "eon_index_clima"
$user = $env:POSTGRES_USER ?? "eon"

Write-Host "Conectando a $db como $user..." -ForegroundColor Cyan
docker exec -it eon-index-postgres psql -U $user -d $db
