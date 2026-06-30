# DEVELOPMENT_COMMANDS.md — Comandos de desarrollo

Comandos listos para copiar y ejecutar en PowerShell (Windows).

---

## Base de datos PostgreSQL

```powershell
# Arrancar
docker compose up -d postgres
.\scripts\db_up.ps1          # con espera de healthcheck

# Parar
docker compose stop postgres
.\scripts\db_down.ps1

# Ver logs
.\scripts\db_logs.ps1
.\scripts\db_logs.ps1 -Follow

# Conectar psql
.\scripts\db_connect.ps1

# Reset desarrollo (DESTRUYE datos)
.\scripts\db_reset_dev.ps1
```

---

## Migraciones (Alembic)

```powershell
# Aplicar todas las migraciones
python -m alembic upgrade head

# Ver estado actual
python -m alembic current

# Ver historial
python -m alembic history

# Revertir última migración
python -m alembic downgrade -1

# Generar nueva migración automática (tras cambiar db/models.py)
python -m alembic revision --autogenerate -m "descripcion_del_cambio"
```

---

## Importador Excel

```powershell
# Importar con DB activa
python -m quote_engine.importers.excel_products_importer --file data/raw/archivo.xlsx

# Dry-run (sin escribir en DB)
python -m quote_engine.importers.excel_products_importer --file data/raw/archivo.xlsx --dry-run

# Forzar reimportación
python -m quote_engine.importers.excel_products_importer --file data/raw/archivo.xlsx --force

# Con log detallado
python -m quote_engine.importers.excel_products_importer --file data/raw/archivo.xlsx -v
```

---

## API

```powershell
# Arrancar API con recarga automática
python -m uvicorn quote_api.main:app --reload --host 127.0.0.1 --port 8000

# Verificar estado
Invoke-RestMethod http://localhost:8000/health

# Ver herramientas EON
Invoke-RestMethod http://localhost:8000/eon/tools

# Buscar en catálogo
Invoke-RestMethod "http://localhost:8000/catalog/search?q=split"

# Listar aprendizajes pendientes
Invoke-RestMethod http://localhost:8000/learning/pending

# Aprobar aprendizaje (solo Samuel)
Invoke-RestMethod -Method POST "http://localhost:8000/learning/1/approve?approved_by=Samuel"
```

---

## Tests

```powershell
# Todos los tests
python -m pytest

# Tests de regresión de presupuestos
python -m pytest tests/regression_presupuestos -v

# Tests de DB (usando SQLite en memoria)
python -m pytest tests/test_db_models.py -v

# Tests de pricing
python -m pytest tests/pricing/ -v

# Tests de catálogo
python -m pytest tests/catalog/ -v

# Tests de aprendizaje
python -m pytest tests/learning/ -v

# Tests del importador Excel
python -m pytest tests/importers/ -v

# Con cobertura
python -m pytest --tb=short -q
```

---

## CLI

```powershell
# Listar presupuestos
index-quote list

# Ver presupuesto
index-quote show PRE-2026-0001

# Calcular
index-quote calculate PRE-2026-0001

# Guardar desde JSON
index-quote save data/fixtures/presupuesto_completo_mixto.json

# Workflow completo
index-quote workflow data/fixtures/presupuesto_completo_mixto.json

# Herramientas EON
index-quote eon-tools

# Buscar presupuestos
index-quote search "split"
index-quote recent --limit 10
```

---

## Instalación de dependencias nuevas

```powershell
# En el venv del proyecto
pip install sqlalchemy alembic psycopg2-binary python-dotenv openpyxl

# O reinstalar todo desde pyproject.toml
pip install -e ".[dev]"
```

---

## Variables de entorno

```powershell
# Copiar plantilla
Copy-Item .env.example .env

# Editar .env con tu editor
notepad .env
```
