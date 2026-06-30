# set_holded_secret_local.ps1
# Configura HOLDED_API_KEY en .env.local de forma segura (entrada oculta, permisos restringidos).

$envFile = Join-Path $PSScriptRoot "..\\.env.local"
$gitignore = Join-Path $PSScriptRoot "..\\.gitignore"

if (Test-Path $gitignore) {
    $gitignoreContent = Get-Content $gitignore -Raw
    if ($gitignoreContent -notmatch '\.env\.local') {
        Write-Host "[ERROR] .gitignore no excluye .env.local. Anadelo antes de continuar." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[ERROR] No se encontro .gitignore. Crea uno que excluya .env.local antes de continuar." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Configurar HOLDED_API_KEY ===" -ForegroundColor Cyan
Write-Host "Introduce el token de Holded. No se mostrara en pantalla."
Write-Host ""

Write-Host "HOLDED_API_KEY: " -NoNewline
$chars = New-Object System.Collections.Generic.List[char]
while ($true) {
    $key = [System.Console]::ReadKey($true)
    if ($key.Key -eq 'Enter') { break }
    if ($key.Key -eq 'Backspace') {
        if ($chars.Count -gt 0) {
            $chars.RemoveAt($chars.Count - 1)
            Write-Host "`b `b" -NoNewline
        }
        continue
    }
    $c = $key.KeyChar
    if ([int]$c -ge 32 -and [int]$c -le 126) {
        $chars.Add($c)
        Write-Host "*" -NoNewline
    }
}
Write-Host ""
$plainToken = -join $chars
$chars.Clear()

if ([string]::IsNullOrWhiteSpace($plainToken)) {
    Write-Host "[ERROR] Token vacio. No se ha guardado nada." -ForegroundColor Red
    exit 1
}

[System.IO.File]::WriteAllText($envFile, "HOLDED_API_KEY=$plainToken", (New-Object System.Text.UTF8Encoding $false))
$plainToken = $null
[System.GC]::Collect()

$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls $envFile /inheritance:r /grant "${currentUser}:(F)" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[AVISO] No se pudieron restringir permisos automaticamente. Revisa manualmente." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[OK] HOLDED_API_KEY guardada en .env.local" -ForegroundColor Green
Write-Host "[OK] Permisos restringidos a: $currentUser" -ForegroundColor Green
Write-Host "[OK] .gitignore excluye .env.local" -ForegroundColor Green
Write-Host ""
Write-Host "Siguiente paso: verificar conectividad con Holded (solo lectura)."
