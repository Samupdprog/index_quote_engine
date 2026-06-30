# ============================================================
# validate_windows.ps1 â€” ValidaciÃ³n completa en Windows
# Index Quote Engine â€” Index Clima
# ============================================================
# Ejecutar desde la raiz del proyecto:
#   cd C:\Users\Samuel\index_quote_engine
#   .\scripts\validate_windows.ps1
# ============================================================

param(
    [switch]$SkipDocker,
    [switch]$SkipImport,
    [switch]$SkipAPI,
    [string]$ExcelFile = ""
)

$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot | Split-Path -Parent
Set-Location $ROOT

$PASS = 0
$FAIL = 0
$WARN = 0

function Write-Header($text) {
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host "=" * 60 -ForegroundColor Cyan
}

function Write-OK($text)   { Write-Host "  [OK]  $text" -ForegroundColor Green;  $global:PASS++ }
function Write-FAIL($text) { Write-Host "  [FAIL] $text" -ForegroundColor Red;   $global:FAIL++ }
function Write-WARN($text) { Write-Host "  [WARN] $text" -ForegroundColor Yellow; $global:WARN++ }
function Write-INFO($text) { Write-Host "  [INFO] $text" -ForegroundColor Gray }

# ============================================================
# 1. VERIFICAR ARCHIVOS CRITICOS
# ============================================================
Write-Header "1. Verificando archivos crÃ­ticos"

$critical = @(
    "pyproject.toml",
    "docker-compose.yml",
    "alembic.ini",
    "quote_api\main.py",
    "quote_engine\catalog\service.py",
    "quote_engine\db\repositories\quotes.py",
    "quote_engine\importers\excel_products_importer.py",
    "tests\learning\test_learning.py"
)

foreach ($f in $critical) {
    if (Test-Path $f) { Write-OK $f }
    else              { Write-FAIL "FALTA: $f" }
}

# Verificar que pyproject.toml no estÃ¡ truncado
$toml = Get-Content "pyproject.toml" -Raw
if ($toml -match '\[tool\.setuptools') { Write-OK "pyproject.toml completo" }
else { Write-FAIL "pyproject.toml truncado (falta [tool.setuptools])" }

# Verificar que quote_api/main.py tiene los routers
$main = Get-Content "quote_api\main.py" -Raw
if ($main -match 'include_router\(catalog_router\)') { Write-OK "quote_api/main.py tiene catalog_router" }
else { Write-FAIL "quote_api/main.py incompleto (falta catalog_router)" }

# Verificar fix supplier detection
$imp = Get-Content "quote_engine\importers\excel_products_importer.py" -Raw
if ($imp -match '_match_supplier_col') { Write-OK "Importer: fix supplier col detection presente" }
else { Write-FAIL "Importer: falta _match_supplier_col" }

if ($imp -match '_max_col_needed') { Write-OK "Importer: fix empty rows presente" }
else { Write-FAIL "Importer: falta _max_col_needed guard" }

# Verificar fix confidence
$svc = Get-Content "quote_engine\catalog\service.py" -Raw
if ($svc -match "confidence != .baja.") { Write-OK "CatalogService: fix confianza presente" }
else { Write-FAIL "CatalogService: falta filtro confidence != baja" }

# Verificar fix learning uuid
$learn = Get-Content "tests\learning\test_learning.py" -Raw
if ($learn -match 'import uuid') { Write-OK "tests/learning: fix UUID presente" }
else { Write-FAIL "tests/learning: falta import uuid" }

# ============================================================
# 2. DOCKER / POSTGRESQL
# ============================================================
if (-not $SkipDocker) {
    Write-Header "2. Docker / PostgreSQL"

    try {
        $dcStatus = docker compose ps --format json 2>$null | ConvertFrom-Json
        $pgRunning = $dcStatus | Where-Object { $_.Service -eq "postgres" -and $_.State -eq "running" }
        if ($pgRunning) {
            Write-OK "PostgreSQL container corriendo"
        } else {
            Write-INFO "Levantando PostgreSQL..."
            docker compose up -d postgres
            Start-Sleep 5
            Write-OK "PostgreSQL iniciado"
        }
    } catch {
        Write-WARN "No se pudo verificar Docker: $_"
    }

    # Test conexion Python
    Write-INFO "Probando conexion Python..."
    $connTest = python -c "
import os, sys
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg2://eon:eon_dev_password@localhost:5435/eon_index_clima')
try:
    from sqlalchemy import create_engine, text
    eng = create_engine(os.environ['DATABASE_URL'])
    with eng.connect() as c:
        v = c.execute(text('SELECT version()')).scalar()
    print('OK:', v[:40])
except Exception as e:
    print('FAIL:', e)
    sys.exit(1)
" 2>&1

    if ($LASTEXITCODE -eq 0) { Write-OK "Conexion PostgreSQL: $connTest" }
    else                      { Write-FAIL "Conexion PostgreSQL fallida: $connTest" }

    # Alembic migrations
    Write-INFO "Ejecutando alembic upgrade head..."
    try {
        $env:DATABASE_URL = "postgresql+psycopg2://eon:eon_dev_password@localhost:5435/eon_index_clima"
        alembic upgrade head 2>&1 | Out-Null
        Write-OK "Alembic upgrade head OK"
    } catch {
        Write-WARN "Alembic: $_"
    }
}

# ============================================================
# 3. PYTEST COMPLETO
# ============================================================
Write-Header "3. pytest completo"

Write-INFO "Ejecutando python -m pytest -v --tb=short ..."
python -m pytest tests/ -v --tb=short -q 2>&1 | Tee-Object -FilePath "data\reports\pytest_output.txt" | Select-Object -Last 10

if ($LASTEXITCODE -eq 0) { Write-OK "Todos los tests pasaron" }
else                      { Write-FAIL "Hay tests fallidos â€” ver data\reports\pytest_output.txt" }

# ============================================================
# 4. IMPORTACION EXCEL REAL
# ============================================================
if (-not $SkipImport) {
    Write-Header "4. ImportaciÃ³n Excel real"

    # Buscar Excel en data/raw
    if ($ExcelFile -eq "") {
        $xlsx = Get-ChildItem "data\raw\*.xlsx" | Select-Object -First 1
    } else {
        $xlsx = Get-Item $ExcelFile
    }

    if ($null -eq $xlsx) {
        Write-WARN "No hay Excel en data\raw\. Saltando importaciÃ³n."
    } else {
        Write-INFO "Excel: $($xlsx.Name)"
        New-Item -ItemType Directory -Force "data\reports" | Out-Null

        # Importacion real (con PostgreSQL)
        Write-INFO "Importando con PostgreSQL..."
        $env:DATABASE_URL = "postgresql+psycopg2://eon:eon_dev_password@localhost:5435/eon_index_clima"
        python -m quote_engine.importers.excel_products_importer `
            --file "$($xlsx.FullName)" `
            --report-dir "data\reports" `
            2>&1 | Tee-Object -FilePath "data\reports\import_output.txt" | Select-Object -Last 15

        if ($LASTEXITCODE -eq 0) { Write-OK "ImportaciÃ³n completada" }
        else                      { Write-WARN "ImportaciÃ³n con warnings/errors â€” ver data\reports\import_output.txt" }

        $reports = Get-ChildItem "data\reports\import_report_*.md" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($reports) { Write-OK "Informe: $($reports.Name)" }
    }
}

# ============================================================
# 5. BUSQUEDAS EN CATALOGO
# ============================================================
Write-Header "5. BÃºsquedas en catÃ¡logo"

$queries = @("tuberÃ­a", "canaleta", "cable", "nitrÃ³geno", "split", "bomba condensados")

foreach ($q in $queries) {
    $result = python -c "
import os, sys
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg2://eon:eon_dev_password@localhost:5435/eon_index_clima')
sys.path.insert(0, '.')
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from quote_engine.catalog.service import CatalogService
    eng = create_engine(os.environ['DATABASE_URL'])
    Session = sessionmaker(bind=eng)
    session = Session()
    svc = CatalogService(db_session=session)
    r = svc.search_products('$q', limit=3)
    if r.results:
        best = r.results[0]
        print(f'OK {r.total} resultados | {best.description[:40]} | {best.supplier[:20]} | {best.net_unit_price:.2f} EUR | {best.confidence}')
    else:
        print('SIN RESULTADOS')
    session.close()
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
" 2>&1

    if ($result -match "^OK") { Write-OK "'$q': $result" }
    elseif ($result -match "SIN RESULTADOS") { Write-WARN "'$q': sin resultados en catÃ¡logo" }
    else { Write-FAIL "'$q': $result" }
}

# ============================================================
# 6. PRESUPUESTO DE PRUEBA
# ============================================================
Write-Header "6. Presupuesto de prueba (quote_case en PostgreSQL)"

python -c "
import os, sys, json
from datetime import date
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg2://eon:eon_dev_password@localhost:5435/eon_index_clima')
sys.path.insert(0, '.')

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from quote_engine.catalog.service import CatalogService
    from quote_engine.db.repositories.quotes import save_quote_case, get_quote_case

    eng = create_engine(os.environ['DATABASE_URL'])
    Session = sessionmaker(bind=eng)
    session = Session()
    svc = CatalogService(db_session=session)

    # Buscar productos para el presupuesto
    items = []
    for term in ['split', 'tuberÃ­a cobre', 'canaleta']:
        r = svc.search_products(term, limit=1)
        if r.results:
            p = r.results[0]
            items.append({
                'description': p.description,
                'supplier': p.supplier,
                'quantity': 1.0,
                'unit': p.unit or 'ud',
                'cost_unit': float(p.net_unit_price),
                'cost_total': float(p.net_unit_price),
                'sale_unit_without_tax': round(float(p.net_unit_price) * 1.20, 2),
                'sale_total_without_tax': round(float(p.net_unit_price) * 1.20, 2),
                'sale_mode': 'catalogo',
                'confidence': p.confidence,
                'source': p.reason,
            })
            print(f'  Partida: {p.description[:45]:45} | {p.supplier[:20]:20} | {p.net_unit_price:.2f} EUR | {p.confidence}')

    if not items:
        print('ERROR: No se encontraron productos para el presupuesto')
        sys.exit(1)

    ref = 'PRE-TEST-VALIDACION-2026'
    snap = {'header': {'reference': ref, 'client': 'Test Validacion', 'tax': 7.0}}
    calc = {'lines': items, 'totals': {'cost_subtotal': sum(i['cost_unit'] for i in items)}}

    case_id = save_quote_case(
        db_session=session,
        reference=ref,
        snapshot_dict=snap,
        calculated_dict=calc,
        client_name='Test Validacion',
        status='draft',
    )

    if case_id:
        saved = get_quote_case(session, ref)
        print()
        print(f'  quote_case guardado: id={case_id}, reference={ref}')
        print(f'  Lineas en DB: {saved['line_count']}')
        print('  OK')
    else:
        print('ERROR: save_quote_case devolvio None')
        sys.exit(1)

    session.close()
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
" 2>&1

if ($LASTEXITCODE -eq 0) { Write-OK "Presupuesto de prueba guardado en PostgreSQL" }
else                      { Write-FAIL "Error generando presupuesto de prueba" }

# ============================================================
# 7. ENDPOINTS API
# ============================================================
if (-not $SkipAPI) {
    Write-Header "7. Endpoints API"

    # Iniciar servidor en background
    Write-INFO "Iniciando uvicorn en puerto 8099 (temporal)..."
    $env:DATABASE_URL = "postgresql+psycopg2://eon:eon_dev_password@localhost:5435/eon_index_clima"
    $srv = Start-Process python -ArgumentList "-m", "uvicorn", "quote_api.main:app", "--port", "8099", "--log-level", "warning" `
           -PassThru -RedirectStandardOutput "data\reports\api_server.log" -RedirectStandardError "data\reports\api_server_err.log"
    Start-Sleep 3

    $endpoints = @(
        @{ Path = "/health";               Desc = "Health check" },
        @{ Path = "/eon/tools";            Desc = "EON tools list" },
        @{ Path = "/catalog/search?q=tuberia"; Desc = "Catalogo busqueda" },
        @{ Path = "/quotes/recent";        Desc = "Presupuestos recientes" },
        @{ Path = "/learning/pending";     Desc = "Aprendizajes pendientes" }
    )

    foreach ($ep in $endpoints) {
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:8099$($ep.Path)" -UseBasicParsing -TimeoutSec 5
            Write-OK "$($ep.Desc) $($ep.Path) â†’ $($resp.StatusCode)"
        } catch {
            Write-FAIL "$($ep.Desc) $($ep.Path) â†’ $($_.Exception.Message)"
        }
    }

    # Parar servidor
    $srv | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-INFO "Servidor API detenido"
}

# ============================================================
# RESUMEN FINAL
# ============================================================
Write-Header "RESUMEN"
Write-Host "  Pasados: $PASS" -ForegroundColor Green
Write-Host "  Warnings: $WARN" -ForegroundColor Yellow
Write-Host "  Fallidos: $FAIL" -ForegroundColor $(if ($FAIL -gt 0) { "Red" } else { "Green" })

if ($FAIL -gt 0) {
    Write-Host ""
    Write-Host "  Hay $FAIL comprobacion(es) fallida(s). Revisa los mensajes FAIL arriba." -ForegroundColor Red
    exit 1
} else {
    Write-Host ""
    Write-Host "  Validacion completa OK." -ForegroundColor Green
    exit 0
}


