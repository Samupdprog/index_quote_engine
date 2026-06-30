# PHASES.md — Fases de implementación del sistema EON

Registro completo de las 12 fases del plan EON ejecutadas sobre el proyecto `index_quote_engine`.

---

## FASE 0 — Auditoría del estado inicial

**Objetivo:** Documentar el estado real del proyecto antes de tocar nada.

**Entregables:**
- `docs/ARCHITECTURE_STATUS.md` — Auditoría completa del estado del proyecto

**Estado:** ✅ Completada

**Resumen:** Se auditaron todos los módulos existentes: `calculator.py`, `models.py`, `storage.py`, `eon_tools.py`, `quote_api/`, `quote_cli/`. Se identificaron dependencias, riesgos y puntos de integración. El motor de cálculo se declaró zona protegida.

---

## FASE 1 — Docker + PostgreSQL

**Objetivo:** Infraestructura de base de datos local con Docker.

**Entregables:**
- `docker-compose.yml` — PostgreSQL 16, puerto 5435, volumen persistente
- `.env.example` — Variables de entorno documentadas
- `scripts/db_up.ps1`, `db_down.ps1`, `db_logs.ps1`, `db_reset_dev.ps1`, `db_connect.ps1`
- `docs/DATABASE.md` — Guía completa de gestión de DB

**Estado:** ✅ Completada

**Notas:**
- Puerto 5435 para evitar conflictos con instalaciones locales de PostgreSQL
- `db_reset_dev.ps1` requiere confirmación explícita "SI" antes de destruir datos
- Todos los scripts son no-destructivos por defecto

---

## FASE 2 — SQLAlchemy + Alembic + Modelos ORM

**Objetivo:** Capa de persistencia Python sobre PostgreSQL.

**Entregables:**
- `quote_engine/db/session.py` — Gestión de conexión con degradación elegante
- `quote_engine/db/base.py` — Base declarativa SQLAlchemy 2.x
- `quote_engine/db/models.py` — 10 modelos ORM
- `alembic.ini` — Configuración de migraciones
- `migrations/env.py` — Entorno de migraciones
- `migrations/versions/0001_initial_schema.py` — Migración inicial completa
- `pyproject.toml` actualizado con nuevas dependencias

**Estado:** ✅ Completada

**Modelos creados:** `Supplier`, `Product`, `SupplierPrice`, `PriceImportBatch`, `QuoteCase`, `QuoteLineItem`, `QuoteTotalRecord`, `QuoteCorrection`, `LearningItem`, `ErrorCase`

**Principio clave:** Si no hay DB configurada (sin contraseña en .env), el motor devuelve `None` en lugar de lanzar error. Toda la arquitectura soporta modo sin DB.

---

## FASE 3 — Importador Excel de productos

**Objetivo:** Importar tarifas de proveedores en formato Excel a la DB.

**Entregables:**
- `quote_engine/importers/excel_products_importer.py`
- `tests/fixtures_excel/test_productos.xlsx`
- `tests/importers/test_excel_importer.py`

**Estado:** ✅ Completada

**Características:**
- Detección automática de columnas por palabras clave
- Deduplicación por hash SHA-256 del archivo
- Modo dry-run (sin escritura en DB)
- Modo force (reimportación aunque ya exista el hash)
- Alerta de cambios de precio > 30%
- Informe Markdown generado en `data/reports/`
- CLI: `python -m quote_engine.importers.excel_products_importer --file archivo.xlsx`

---

## FASE 4 — Catálogo de productos y búsqueda

**Objetivo:** Servicio de búsqueda de productos con similitud textual.

**Entregables:**
- `quote_engine/catalog/normalizer.py` — Normalización NFD + tokenización con stop words
- `quote_engine/catalog/schemas.py` — Schemas de resultados
- `quote_engine/catalog/service.py` — Servicio de búsqueda

**Estado:** ✅ Completada

**Algoritmo de búsqueda:** Jaccard sobre tokens normalizados + factor de cobertura. Umbral mínimo de similitud: 0.3. Penaliza precios con más de 18 meses de antigüedad.

---

## FASE 5 — Reglas de precios y selector

**Objetivo:** Sistema de validación y selección de precios con trazabilidad.

**Entregables:**
- `quote_engine/pricing/rules.py` — 6 reglas aplicables
- `quote_engine/pricing/selector.py` — Selector con prioridad y trazabilidad
- `quote_engine/pricing/schemas.py` — Schema de resultado

**Estado:** ✅ Completada

**Reglas implementadas:**

| Regla | Acción |
|---|---|
| `NoNegativePriceRule` | Rechaza precio < 0 |
| `NoLowConfidenceAutoRule` | Rechaza confianza "baja" |
| `StalenessPriceRule` | Advierte si > 18 meses |
| `UnitConversionRule` | Advierte si unidad no es unitaria |
| `MediumConfidenceReviewRule` | Marca "REVISAR" si confianza "media" |
| `PriceChangeRule` | Advierte si cambio > 30% vs precio anterior |

---

## FASE 6 — Integración catálogo + motor

**Objetivo:** Conectar el catálogo de precios con el motor de presupuestos.

**Entregables:**
- `quote_engine/catalog/catalog_resolver.py`

**Estado:** ✅ Completada

**Función:** `CatalogResolver.resolve_line()` busca en catálogo, aplica reglas de precios, devuelve resultado con trazabilidad completa (fuente, confianza, advertencias). Sin DB → devuelve resultado vacío, no lanza error.

---

## FASE 7 — Historial de presupuestos en DB

**Objetivo:** Persistir presupuestos calculados en PostgreSQL para histórico y aprendizaje.

**Entregables:**
- `quote_engine/db/repositories/quotes.py`

**Estado:** ✅ Completada

**Funciones:** `save_quote_case()`, `get_quote_case()`, `list_recent_quote_cases()`

---

## FASE 8 — Sistema de correcciones y aprendizaje

**Objetivo:** Registrar correcciones humanas y proponer aprendizajes que solo Samuel puede aprobar.

**Entregables:**
- `quote_engine/learning/corrections.py`
- `quote_engine/learning/proposer.py`
- `quote_engine/learning/approval.py`

**Estado:** ✅ Completada

**Regla crítica:** `approved_by` no puede ser `eon`, `auto`, `system`, `ia`, `bot`, `gpt`, `claude`. El bloqueo existe en el módulo Python y en el endpoint de la API (HTTP 403). Verificado con test de regresión.

---

## FASE 9 — Integración con Obsidian

**Objetivo:** Escritura de notas en vault Obsidian de forma opcional y no bloqueante.

**Entregables:**
- `quote_engine/obsidian/templates.py` — 5 plantillas Markdown
- `quote_engine/obsidian/writer.py` — Escritura segura

**Estado:** ✅ Completada

**Principio:** Si `OBSIDIAN_VAULT` no está configurado o el directorio no existe, todas las funciones devuelven `False` sin afectar al motor. Nunca se guardan secretos en notas Obsidian.

---

## FASE 10 — Tests de regresión de presupuestos

**Objetivo:** Suite de regresión que garantiza que el motor no se rompe.

**Entregables:**
- `tests/regression_presupuestos/` — 10 fixtures JSON
- `tests/regression_presupuestos/test_regression.py`

**Estado:** ✅ Completada

**Fixtures cubiertos:** split básico, multisplit 2×1, conductos con soldadura, reparación sin máquina, mantenimiento sin materiales, presupuesto con margen bajo, interconexión instalada + mano de obra, transporte a 30 días, precio no encontrado, producto con confianza baja.

**Invariantes verificadas:** IGIC 7%, total final positivo, suma de líneas = subtotales, cada línea tiene tipo válido.

---

## FASE 11 — API interna

**Objetivo:** Exponer todos los módulos nuevos como endpoints REST.

**Entregables:**
- `quote_api/catalog_routes.py` — 4 endpoints catálogo
- `quote_api/learning_routes.py` — 4 endpoints aprendizaje
- `quote_api/db_routes.py` — 3 endpoints DB histórico
- `quote_api/main.py` — actualizado con nuevos routers

**Estado:** ✅ Completada

**Documentación interactiva:** `http://localhost:8000/docs` (Swagger UI)

---

## FASE 12 — Documentación final

**Objetivo:** Documentar todo el sistema para referencia futura de EON y Samuel.

**Entregables:**
- `docs/ARCHITECTURE.md` — Arquitectura del sistema
- `docs/PHASES.md` — Este archivo
- `docs/DATABASE.md` — Gestión de DB (completado en FASE 1)
- `docs/IMPORT_EXCEL.md` — Importador Excel (completado en FASE 3)
- `docs/LEARNING_FLOW.md` — Flujo de correcciones y aprendizaje
- `docs/API.md` — Referencia de todos los endpoints
- `docs/OBSIDIAN_STRUCTURE.md` — Estructura del vault Obsidian
- `docs/DEVELOPMENT_COMMANDS.md` — Comandos PowerShell de desarrollo

**Estado:** ✅ Completada

---

## Estado global del sistema

| Módulo | Estado |
|---|---|
| Motor de cálculo existente | ✅ Intacto |
| EON Tools existente | ✅ Intacto |
| CLI existente | ✅ Intacto |
| API existente | ✅ Intacto |
| PostgreSQL + Docker | ✅ Listo |
| Modelos ORM + migraciones | ✅ Listos |
| Importador Excel | ✅ Listo |
| Catálogo de productos | ✅ Listo |
| Reglas de precios | ✅ Listas |
| Historial en DB | ✅ Listo |
| Correcciones + aprendizaje | ✅ Listo |
| Obsidian (opcional) | ✅ Listo |
| Tests de regresión | ✅ Listos |
| API interna | ✅ Lista |
| Documentación | ✅ Completa |

---

## Pendiente de primera ejecución

```powershell
# 1. Instalar dependencias nuevas
pip install -e ".[dev]"

# 2. Copiar .env
Copy-Item .env.example .env
# Editar .env con tu contraseña de PostgreSQL

# 3. Arrancar PostgreSQL
docker compose up -d postgres

# 4. Aplicar migraciones
python -m alembic upgrade head

# 5. Importar primer Excel de precios
python -m quote_engine.importers.excel_products_importer --file data/raw/tu_tarifa.xlsx --dry-run

# 6. Arrancar API
python -m uvicorn quote_api.main:app --reload --host 127.0.0.1 --port 8000

# 7. Ejecutar tests
python -m pytest tests/regression_presupuestos -v
```
