# ARCHITECTURE.md — Arquitectura del sistema EON Index Quote Engine

---

## Visión general

```
EON (IA) → quote_api (FastAPI) → quote_engine (Motor Python) → PostgreSQL
                                                              → data/quotes/ (JSON)
                                                              → Obsidian (Markdown)
```

**Principio clave: el motor Python es la única fuente de cálculo.**
La IA interpreta, llama a la API, y presenta resultados. Nunca calcula importes directamente.

---

## Capas del sistema

### 1. Motor de cálculo (`quote_engine/calculator.py`)
- Función pura: `QuoteSnapshot → CalculatedQuote`
- Sin efectos secundarios
- Sin acceso a DB ni archivos
- Testeado exhaustivamente

### 2. Catálogo de productos (`quote_engine/catalog/`)
- `service.py` — Búsqueda de productos por texto, código o referencia
- `normalizer.py` — Normalización y tokenización para búsqueda
- `schemas.py` — Schemas Pydantic de resultados
- `catalog_resolver.py` — Integración catálogo + pricing para el motor

### 3. Pricing (`quote_engine/pricing/`)
- `rules.py` — Reglas de validación de precios
- `selector.py` — Selector de mejor precio con trazabilidad
- `schemas.py` — Schema de resultado de selección

### 4. Importadores (`quote_engine/importers/`)
- `excel_products_importer.py` — Importa Excel → PostgreSQL con informe

### 5. Base de datos (`quote_engine/db/`)
- `session.py` — Gestión de conexión SQLAlchemy
- `base.py` — Base declarativa
- `models.py` — Modelos ORM (10 tablas)
- `repositories/quotes.py` — Repositorio de presupuestos históricos

### 6. Aprendizaje (`quote_engine/learning/`)
- `corrections.py` — Registro de correcciones humanas
- `proposer.py` — Proposición de aprendizajes desde correcciones
- `approval.py` — Aprobación humana (bloqueada para IA)

### 7. Obsidian (`quote_engine/obsidian/`)
- `templates.py` — Plantillas Markdown
- `writer.py` — Escritura segura de notas

### 8. API (`quote_api/`)
- `main.py` — App FastAPI
- `routes.py` — Endpoints motor existente
- `eon_routes.py` — Endpoints EON Tools
- `catalog_routes.py` — Endpoints catálogo (nuevo)
- `learning_routes.py` — Endpoints aprendizaje (nuevo)
- `db_routes.py` — Endpoints DB histórico (nuevo)

### 9. CLI (`quote_cli/`)
- `main.py` — 12+ subcomandos

---

## Flujo de un presupuesto

```
1. EON recibe descripción del trabajo
2. EON llama a /eon/quotes o construye QuoteSnapshot
3. Motor calcula: calculate_quote(snapshot) → CalculatedQuote
4. Motor guarda: storage.save_quote() → data/quotes/*.json
5. Motor guarda en DB: save_quote_case() → quote_cases (PostgreSQL)
6. Motor genera informe HTML: build_internal_report()
7. EON presenta resultado al usuario
8. Si hay correcciones: register_correction() → propone learning
9. Samuel aprueba/rechaza learnings
```

---

## Flujo de importación de precios

```
1. Colocar Excel en data/raw/
2. python -m quote_engine.importers.excel_products_importer --file data/raw/xxx.xlsx
3. Importador: detecta hojas → normaliza → guarda en suppliers + products + supplier_prices
4. Genera informe en data/reports/import_report_*.md
5. Precios disponibles en catálogo (/catalog/search)
```

---

## Esquema de base de datos

```
suppliers ──────────────────────────────────────────┐
products ───────────────────────────────────────────┤
                                                     ↓
                                            supplier_prices
                                                     ↑
                                        price_import_batches

quote_cases ────────────────────────────────────────┐
    ├── quote_line_items (→ products, supplier_prices)
    ├── quote_totals
    ├── quote_corrections ────────────────── learning_items
    └── (related) error_cases
```

---

## Reglas de integración

1. `calculator.py` no se modifica sin tests de regresión.
2. `eon_tools.py` es la fachada para EON — no bypass.
3. Los módulos nuevos no rompen los existentes (aditividad).
4. Los aprendizajes nunca se auto-aprueban.
5. Holded no se toca (solo se prepara arquitectura).
6. Los secretos van en `.env`, nunca en código ni JSON.
