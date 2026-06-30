# ARCHITECTURE_STATUS.md — Estado inicial del proyecto
> Generado automáticamente como parte de la FASE 0 del plan EON.
> Fecha: 2026-06-30

---

## 1. Estructura actual del repositorio

```
index_quote_engine/
│
├── pyproject.toml                  ← Paquete Python (setuptools), entry point CLI
├── README.md
├── .gitignore
│
├── config/
│   └── document_defaults.json      ← Defaults para secciones documentales
│
├── data/
│   ├── examples/                   ← JSON de ejemplo (varios tipos de importación)
│   ├── exports/                    ← Payloads Holded generados (.gitkeep, exports reales excluidos)
│   ├── fixtures/                   ← JSON de fixtures para tests realistas
│   ├── quotes/                     ← Presupuestos guardados (.gitkeep + PRE-2026-0001.json)
│   └── reports/                    ← Informes HTML generados
│
├── quote_engine/                   ← Paquete principal del motor
│   ├── __init__.py
│   ├── calculator.py               ← Motor de cálculo (CORE, no tocar sin tests)
│   ├── commands.py                 ← Comandos de modificación de snapshot
│   ├── config.py                   ← Configuración interna
│   ├── discounts.py                ← Cálculo de descuentos en cascada
│   ├── document_rules.py           ← Reglas documentales (secciones obligatorias)
│   ├── eon_tools.py                ← Fachada segura para EON (único punto de entrada)
│   ├── models.py                   ← Modelos Pydantic v2 (QuoteSnapshot, QuoteLine, etc.)
│   ├── normalizer.py               ← Normalización de JSON de proveedor
│   ├── search.py                   ← Búsqueda local sobre archivos JSON
│   ├── storage.py                  ← Almacenamiento local en data/quotes/ (JSON)
│   ├── validators.py               ← Validación de comandos
│   ├── workflow.py                 ← Flujo completo: importar → guardar → calcular → informar
│   └── exporters/
│       ├── holded.py               ← Exportador al formato Holded (sin escritura real)
│       └── internal_report.py      ← Informe interno HTML + dict
│
├── quote_api/                      ← API FastAPI
│   ├── main.py                     ← App FastAPI con UTF8JSONResponse customizada
│   ├── routes.py                   ← Endpoints CRUD + cálculo + exportación
│   ├── eon_routes.py               ← Endpoints /eon/* para EON
│   └── workflow_routes.py          ← Endpoints de flujo completo
│
├── quote_cli/                      ← CLI (entry point: index-quote)
│   ├── main.py                     ← Parser argparse con 12+ subcomandos
│   └── __main__.py
│
└── tests/                          ← Tests pytest (12 archivos)
    ├── test_api.py
    ├── test_calculator.py
    ├── test_cli.py
    ├── test_commands.py
    ├── test_discounts.py
    ├── test_document_rules.py
    ├── test_eon_tools.py
    ├── test_internal_report.py
    ├── test_normalizer.py
    ├── test_realistic_fixtures.py
    ├── test_search.py
    ├── test_storage.py
    └── test_workflow.py
```

---

## 2. Motor actual de presupuestos

**Paquete:** `quote_engine` (importado como `from quote_engine import ...`)

**Flujo de cálculo:**

```
QuoteSnapshot (Pydantic v2)
  └─ quote_engine.calculator.calculate_quote()
       └─ CalculatedQuote (líneas calculadas + totales)
```

**Reglas de cálculo actuales:**
- IGIC configurable por cabecera (default 7%)
- Margen global (`global_margin`, default 35%)
- Modos de venta: `margin`, `markup_unit`, `fixed_unit`, `fixed_total`
- Descuentos en cascada (lista de porcentajes)
- Beneficio = venta sin IGIC − coste
- Redondeo con `Decimal` a 2 decimales (ROUND_HALF_UP)

**Storage actual:**
- JSON plano en `data/quotes/*.json`
- IDs correlativos `PRE-YYYY-NNNN`
- Sin base de datos relacional

**Búsqueda actual:**
- Búsqueda en memoria sobre archivos JSON cargados
- Sin índice, sin FTS, sin PostgreSQL

---

## 3. Puntos de entrada

| Punto de entrada | Descripción |
|---|---|
| `index-quote` CLI | `quote_cli.main:main` — 12 subcomandos |
| FastAPI (uvicorn) | `quote_api.main:app` |
| `/health` | Estado del servicio |
| `/eon/tools` | Lista herramientas EON |
| `/eon/search` | Búsqueda filtrada de presupuestos |
| `/eon/quotes/{id}` | Carga presupuesto |
| `/eon/quotes/{id}/calculate` | Calcula presupuesto |
| `/eon/quotes/{id}/commands` | Aplica comandos de modificación |
| `/eon/quotes/{id}/report` | Genera informe interno |
| `/eon/quotes/{id}/export/holded` | Genera payload Holded |
| `/storage/quotes` | CRUD de presupuestos vía API |
| `/quotes/calculate` | Cálculo sin persistencia |
| `/quotes/import` | Normalización desde JSON proveedor |

---

## 4. Dependencias actuales (pyproject.toml)

**Runtime:**
- `fastapi>=0.111.0`
- `uvicorn[standard]>=0.30.0`
- `pydantic>=2.7.0`

**Dev:**
- `pytest>=8.2.0`
- `pytest-asyncio>=0.23.0`
- `httpx>=0.27.0`
- `ruff>=0.4.0`

**Python requerido:** >=3.11 (venv usa CPython 3.12 Windows)

**Ausentes (pendientes de añadir):**
- `sqlalchemy>=2.0`
- `alembic`
- `psycopg2-binary` o `asyncpg`
- `openpyxl` (importador Excel)
- `python-dotenv`

---

## 5. Riesgos identificados

| Riesgo | Severidad | Mitigación |
|---|---|---|
| Storage JSON no escala para búsquedas complejas | Media | Migrar a PostgreSQL (objetivo del plan) |
| Sin validación de precios de proveedor | Alta | FASE 3 resuelve con importador |
| Sin histórico de precios | Alta | FASE 2 añade `supplier_prices` |
| Sin trazabilidad de fuente por línea de presupuesto | Media | FASE 6 integra catálogo |
| Sin tests de regresión de presupuestos completos | Media | FASE 10 crea 10 casos |
| Precios inventados posibles (sin catálogo) | Alta | FASE 4+5 crean catálogo y reglas |
| Sin sistema de aprendizaje | Media | FASE 8 implementa |
| venv solo Windows (CPython 3.12) | Baja | No afecta al código; usar Linux Python para CI |

---

## 6. Propuesta de integración sin romper lo existente

### Principio: aditividad

Todo lo nuevo se añade en módulos nuevos. Los módulos existentes (`calculator.py`, `models.py`, `storage.py`, `eon_tools.py`, `routes.py`, `eon_routes.py`) **no se modifican destructivamente**. Se extienden o se añaden adaptadores.

### Mapa de integración

```
Nueva estructura añadida (FASES 1-12):
│
├── docker-compose.yml              ← FASE 1
├── .env.example                    ← FASE 1
├── scripts/                        ← FASE 1
│   ├── db_up.ps1
│   ├── db_down.ps1
│   ├── db_logs.ps1
│   └── db_reset_dev.ps1
│
├── migrations/                     ← FASE 2 (Alembic)
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── quote_engine/
│   ├── db/                         ← FASE 2
│   │   ├── session.py              ← Engine + SessionLocal
│   │   ├── base.py                 ← Base declarativa
│   │   ├── models.py               ← Modelos SQLAlchemy (≠ quote_engine/models.py Pydantic)
│   │   └── repositories/          ← Repos por entidad
│   │
│   ├── catalog/                    ← FASE 4
│   │   ├── service.py
│   │   ├── normalizer.py
│   │   └── schemas.py
│   │
│   ├── importers/                  ← FASE 3
│   │   └── excel_products_importer.py
│   │
│   ├── pricing/                    ← FASE 5
│   │   ├── selector.py
│   │   ├── rules.py
│   │   └── schemas.py
│   │
│   ├── learning/                   ← FASE 8
│   │   ├── corrections.py
│   │   ├── proposer.py
│   │   └── approval.py
│   │
│   └── obsidian/                   ← FASE 9
│       ├── writer.py
│       └── templates.py
│
├── tests/
│   ├── catalog/                    ← FASE 4
│   ├── importers/                  ← FASE 3
│   ├── pricing/                    ← FASE 5
│   ├── quotes/                     ← FASE 7
│   ├── learning/                   ← FASE 8
│   └── regression_presupuestos/    ← FASE 10
│
└── docs/
    ├── ARCHITECTURE_STATUS.md      ← FASE 0 (este archivo)
    ├── ARCHITECTURE.md             ← FASE 12
    ├── PHASES.md                   ← FASE 12
    ├── DATABASE.md                 ← FASE 1+2
    ├── IMPORT_EXCEL.md             ← FASE 3
    ├── LEARNING_FLOW.md            ← FASE 8+12
    ├── API.md                      ← FASE 11+12
    ├── OBSIDIAN_STRUCTURE.md       ← FASE 9+12
    └── DEVELOPMENT_COMMANDS.md     ← FASE 12
```

### Regla de oro de integración

- `quote_engine.calculator` es inmutable → el motor de cálculo no se toca.
- `quote_engine.eon_tools` es la fachada → EON solo llama a esta fachada.
- Los nuevos módulos (`db`, `catalog`, `pricing`, `importers`, `learning`, `obsidian`) son independientes y opcionales en esta fase.
- La API existente sigue funcionando igual.
- Los nuevos endpoints se añaden en `quote_api/catalog_routes.py`, `quote_api/learning_routes.py`, etc.

---

## 7. Criterios de aceptación FASE 0

- [x] Estructura actual documentada
- [x] Motor actual identificado (`quote_engine.calculator`)
- [x] Puntos de entrada documentados
- [x] Dependencias actuales listadas
- [x] Riesgos identificados
- [x] Propuesta de integración sin ruptura documentada
- [x] Proyecto sigue funcionando igual que antes (ningún archivo modificado)
