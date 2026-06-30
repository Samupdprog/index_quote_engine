# test_holded_readonly.ps1
# Prueba de conectividad solo lectura con Holded usando .env.local protegido.
# No imprime el token. No escribe en Holded.

$envFile = Join-Path $PSScriptRoot "..\.env.local"

if (-not (Test-Path $envFile)) {
    Write-Host "[ERROR] No se encontro .env.local en: $envFile" -ForegroundColor Red
    exit 1
}

$rawText = [System.IO.File]::ReadAllText($envFile, [System.Text.Encoding]::UTF8).Trim()
$apiKey = ($rawText -split "`n" | Where-Object { $_ -match '^HOLDED_API_KEY=' }) -replace '^HOLDED_API_KEY=', '' -replace '\r', ''
$apiKey = $apiKey.Trim()

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host "[ERROR] HOLDED_API_KEY no encontrado o vacio en .env.local" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Prueba solo lectura Holded ===" -ForegroundColor Cyan
Write-Host "Endpoint: GET /api/invoices/v1/documents/estimate?limit=1"
Write-Host "Token: *** (oculto)"
Write-Host ""

try {
    $headers = @{ "key" = $apiKey }
    $response = Invoke-WebRequest -Uri "https://api.holded.com/api/invoices/v1/documents/estimate?limit=1" `
        -Method GET `
        -Headers $headers `
        -TimeoutSec 15 `
        -UseBasicParsing

    $statusCode = $response.StatusCode
    Write-Host "[OK] HTTP Status: $statusCode" -ForegroundColor Green

    try {
        $body = $response.Content | ConvertFrom-Json
        if ($body -is [System.Array]) {
            Write-Host "[OK] Elementos devueltos: $($body.Count)" -ForegroundColor Green
        } elseif ($body.PSObject.Properties.Name -contains 'data') {
            $count = if ($body.data -is [System.Array]) { $body.data.Count } else { 1 }
            Write-Host "[OK] Elementos devueltos: $count" -ForegroundColor Green
        } else {
            Write-Host "[OK] Respuesta recibida (estructura no array)." -ForegroundColor Green
        }
    } catch {
        Write-Host "[OK] Respuesta recibida (no JSON o formato inesperado)." -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "Autenticacion: OK" -ForegroundColor Green
    Write-Host "Escritura realizada: NO" -ForegroundColor Green

} catch {
    $err = $_.Exception
    if ($err.Response) {
        $statusCode = [int]$err.Response.StatusCode
        Write-Host "[FAIL] HTTP Status: $statusCode" -ForegroundColor Red

        switch ($statusCode) {
            401 { Write-Host "Token invalido o expirado. Revisa que el token nuevo sea correcto." -ForegroundColor Red }
            403 { Write-Host "Permisos insuficientes. Revisa los permisos del token en Holded." -ForegroundColor Red }
            default { Write-Host "Error inesperado. Codigo: $statusCode" -ForegroundColor Red }
        }
    } else {
        Write-Host "[FAIL] Error de conexion: $($err.Message)" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "Autenticacion: FAIL" -ForegroundColor Red
    Write-Host "Escritura realizada: NO" -ForegroundColor Green
}

$apiKey = $null
[System.GC]::Collect()
