# index_quote_engine · v0.8

Motor de generación y cálculo de presupuestos para **Index Clima**.

> **Estado:** MVP estable. Sin base de datos, sin frontend, sin Holded real.

---

## Qué hace

- Importa JSON de proveedor con alias de campos en español e inglés.
- Calcula costes, venta, IGIC, beneficio y márgenes por línea y totales.
- Descuentos encadenados (40+5 = 43 %, no 45 %).
- Edita el presupuesto mediante comandos inmutables.
- Exporta un payload JSON compatible con Holded (sin enviar nada todavía).
- API REST con FastAPI · documentación automática en `/docs`.
- CLI para operar sin Swagger: `python -m quote_cli` o `index-quote`.
- Guarda y recupera presupuestos como archivos JSON locales (`data/quotes/`).
- Informe interno HTML: semáforo visual (OK/REVISAR/PELIGRO), tarjetas de KPIs, resumen rápido, recomendaciones de revisión, tabla de líneas.
- **Búsqueda local avanzada**: busca por cliente, proveedor, texto libre, estado, tipo, tags, beneficio, total, warnings y problemas — sin base de datos.
- **Herramientas para EON**: fachada segura para que EON opere el sistema sin tocar JSON directamente.

## Qué NO hace todavía

- Base de datos.
- Login / usuarios.
- Frontend React/Next.
- Integración real con Holded (solo genera el payload).
- Autosave, CRM, gestión de trabajos, OpenClaw, EON.

---

## Instalación

Requiere [uv](https://github.com/astral-sh/uv):

```bash
# Desde la raíz del proyecto
uv venv --python 3.12
uv pip install -e ".[dev]"
```

Sin uv (Python 3.11+ en PATH):

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e ".[dev]"
```

---

## Ejecutar tests

```bash
.venv\Scripts\pytest -v          # Windows
.venv/bin/pytest -v              # Linux / Mac
```

Resultado esperado: **300 passed** (v0.8).

---

## Informe interno HTML

El informe interno es una herramienta **para uso exclusivo de Index Clima**. No es el presupuesto del cliente ni un PDF final. Sirve para revisar costes, beneficios, proveedores y detectar problemas antes de enviar el presupuesto.

```bash
# Generar informe en HTML
python -m quote_cli report PRE-2026-0001 --output data/reports/PRE-2026-0001-report.html

# Ver resumen en texto (sin --output)
python -m quote_cli report PRE-2026-0001
```

El informe incluye:

- **Semáforo** `OK` / `REVISAR` / `PELIGRO` con motivo
- **Tarjetas KPI**: Total cliente, Coste total, Beneficio, % Beneficio, Problemas, Warnings
- **Resumen rápido**: 4-6 frases en lenguaje natural sobre el presupuesto
- **Qué revisar**: lista concreta de acciones si hay problemas
- Metadata del presupuesto (ID, estado, fechas, tipo, tags)
- Totales detallados (coste, venta, IGIC, total cliente, beneficio, %)
- **Resumen por proveedor**: coste total, venta, beneficio, % y número de líneas
- **Tabla de líneas** completa con coste unitario/total, venta unitario/total, IGIC, beneficio
- Color coding: rojo para beneficio negativo, amarillo/naranja para coste 0, margen bajo
- Notas internas

Los archivos HTML son standalone, sin CDN ni dependencias externas.

---

## Uso por CLI

El programa puede usarse desde terminal sin Swagger ni servidor.

```bash
# Guardar un presupuesto desde JSON
python -m quote_cli save data/examples/storage_quote_example.json --created-by Samuel --source cli

# Listar presupuestos guardados
python -m quote_cli list
python -m quote_cli list --status draft
python -m quote_cli list --client "Comunidad" --limit 5

# Ver detalle de un presupuesto
python -m quote_cli show PRE-2026-0001
python -m quote_cli show PRE-2026-0001 --json

# Calcular totales
python -m quote_cli calculate PRE-2026-0001
python -m quote_cli calculate PRE-2026-0001 --json

# Duplicar
python -m quote_cli duplicate PRE-2026-0001
python -m quote_cli duplicate PRE-2026-0001 --new-id PRE-2026-0002

# Archivar (sin borrar)
python -m quote_cli archive PRE-2026-0001

# Exportar payload Holded
python -m quote_cli export-holded PRE-2026-0001
python -m quote_cli export-holded PRE-2026-0001 --output data/exports/PRE-2026-0001-holded.json

# Informe interno HTML
python -m quote_cli report PRE-2026-0001
python -m quote_cli report PRE-2026-0001 --output data/reports/PRE-2026-0001-report.html
```

Si el paquete está instalado con `pip install -e .`, también está disponible como:

```bash
index-quote list
index-quote show PRE-2026-0001
```

---

## Arrancar la API

```bash
.venv\Scripts\uvicorn quote_api.main:app --reload --host 127.0.0.1 --port 8000
```

## Abrir Swagger

Una vez arrancada la API, abre en el navegador:

```
http://127.0.0.1:8000/docs
```

---

## Endpoints disponibles

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Estado del servicio |
| `POST` | `/quotes/import` | Importar JSON de proveedor |
| `POST` | `/quotes/calculate` | Calcular snapshot |
| `POST` | `/quotes/command` | Aplicar un comando |
| `POST` | `/quotes/commands` | Aplicar lista de comandos |
| `POST` | `/quotes/export/holded` | Exportar payload Holded |
| `POST` | `/quotes/export/internal-report` | Informe interno (dict) |
| `POST` | `/quotes/export/internal-report/html` | Informe interno (HTML) |
| `POST` | `/storage/quotes` | Guardar presupuesto |
| `GET` | `/storage/quotes` | Listar presupuestos guardados |
| `GET` | `/storage/quotes/{id}` | Cargar presupuesto por ID |
| `POST` | `/storage/quotes/{id}/duplicate` | Duplicar presupuesto |
| `PATCH` | `/storage/quotes/{id}/metadata` | Actualizar metadata |
| `POST` | `/storage/quotes/{id}/archive` | Archivar presupuesto |
| `GET` | `/storage/quotes/{id}/report` | Informe interno (dict) |
| `GET` | `/storage/quotes/{id}/report/html` | Informe interno (HTML) |

---

## Ejemplo: `/quotes/import`

```bash
curl -X POST http://127.0.0.1:8000/quotes/import \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_json": [
      {
        "descripcion": "Split Daikin 1x1",
        "cantidad": 2,
        "proveedor": "Frigicoll",
        "pvpProveedor": 500,
        "descuentosProveedor": [40, 5],
        "margen": 35
      }
    ],
    "defaults": { "global_margin": 35, "tax": 7, "include_tax": false }
  }'
```

Respuesta (valores calculados):

```json
{
  "snapshot": { ... },
  "calculated": {
    "lines": [{
      "cost_unit": 285.0,
      "cost_total": 570.0,
      "effective_supplier_discount": 43.0,
      "sale_total_without_tax": 769.5,
      "tax_amount": 53.87,
      "client_total": 823.37,
      "gross_profit": 199.5,
      "gross_profit_percent": 35.0
    }],
    "totals": {
      "cost_subtotal": 570.0,
      "sale_subtotal": 769.5,
      "tax_amount": 53.87,
      "final_total": 823.37,
      "gross_profit": 199.5
    }
  },
  "warnings": []
}
```

---

## Ejemplo: `/quotes/command`

```json
{
  "snapshot": { ... },
  "command": {
    "type": "set_line_margin",
    "line_id": "UUID-DE-LA-LINEA",
    "margin": 40
  }
}
```

Otros comandos disponibles:

```json
{ "type": "set_global_margin", "margin": 35 }
{ "type": "set_global_tax", "tax": 7 }
{ "type": "set_include_tax", "include_tax": false }
{ "type": "apply_margin_to_supplier", "supplier": "Frigicoll", "margin": 35 }
{ "type": "apply_tax_to_supplier", "supplier": "Frigicoll", "tax": 7 }
{ "type": "apply_pass_supplier_discount_to_supplier", "supplier": "Frigicoll", "enabled": true }
{ "type": "apply_patch_to_supplier", "supplier": "Frigicoll", "patch": { "margin": 35, "sale_mode": "margin" } }
{ "type": "add_line", "line": { "description": "Mano de obra", "quantity": 8, "sale_mode": "fixed_unit", "sale_value": 45 } }
{ "type": "update_line", "line_id": "UUID", "patch": { "quantity": 3 } }
{ "type": "delete_line", "line_id": "UUID" }
```

### Varios comandos de golpe

```json
{
  "snapshot": { ... },
  "commands": [
    { "type": "set_global_margin", "margin": 35 },
    { "type": "apply_margin_to_supplier", "supplier": "Frigicoll", "margin": 30 }
  ]
}
```

---

## Ejemplo: `/quotes/export/holded`

```json
{
  "snapshot": { ... }
}
```

Respuesta (payload listo para Holded, sin enviar nada):

```json
{
  "contactName": "Comunidad El Pinar",
  "contactTaxId": "H12345678",
  "date": "2024-01-15",
  "quoteNumber": "2024-001",
  "items": [
    {
      "name": "Split Daikin 1x1 2.5kW",
      "units": 2.0,
      "subtotal": 769.5,
      "tax": 7.0,
      "total": 823.37
    }
  ],
  "totals": {
    "subtotal": 769.5,
    "tax": 53.87,
    "total": 823.37
  }
}
```

---

## Descuentos encadenados

```
40% + 5%  →  efectivo = (1 - 0.60 × 0.95) × 100 = 43 %   ≠ 45 %
```

## Modos de venta (`sale_mode`)

| Modo | Cálculo |
|---|---|
| `margin` | `venta = coste × (1 + margen/100)` |
| `markup_unit` | `venta = (coste_unitario + sale_value) × cantidad` |
| `fixed_unit` | `venta = sale_value × cantidad` |
| `fixed_total` | `venta = sale_value` (ignora cantidad) |

## `pass_supplier_discount_to_client`

Cuando está activo, la base de venta es el **PVP bruto del proveedor** (no el coste neto).  
Útil cuando el cliente paga según tarifa oficial aunque la empresa tenga descuento interno.

---

## Alias de campos aceptados en importación

| Campo interno | Alias |
|---|---|
| `description` | `descripcion`, `concepto`, `nombre`, `name` |
| `quantity` | `cantidad`, `qty` |
| `supplier` | `proveedor`, `proveedorNombre` |
| `supplier_gross_unit_price` | `pvpProveedor`, `tarifaProveedor`, `pvp` |
| `supplier_net_unit_cost` | `costeUnitario`, `netoProveedor`, `neto` |
| `supplier_discounts` | `descuentosProveedor`, `descuentos`, `dto` |
| `margin` | `margen` |
| `tax` | `igic` |

---

## Herramientas para EON

A partir de v0.8, el motor expone una capa de herramientas seguras para que EON pueda operar sin tocar archivos JSON directamente. EON no debe leer ni escribir en `data/quotes/` manualmente — todo pasa por estas funciones.

Las herramientas disponibles son:

| Herramienta | Descripción |
|---|---|
| `eon_search_quotes` | Busca presupuestos con filtros opcionales |
| `eon_get_quote` | Carga un presupuesto por ID |
| `eon_summarize_quote` | Resumen legible con semáforo y recomendaciones |
| `eon_calculate_quote` | Calcula totales, líneas e IGIC |
| `eon_duplicate_quote` | Crea una copia con nuevo ID |
| `eon_apply_commands` | Aplica comandos en modo `copy`, `overwrite` o `dry_run` |
| `eon_generate_internal_report` | Informe interno dict o HTML |
| `eon_export_holded_payload` | Payload JSON para Holded (sin enviar) |
| `eon_archive_quote` | Archiva un presupuesto |

Por defecto, `eon_apply_commands` usa `save_mode="copy"` — crea una nueva copia en lugar de sobrescribir el original. Esto protege el presupuesto base ante cambios accidentales.

Ejemplos conceptuales:

```python
from quote_engine.eon_tools import *

# Buscar presupuestos de un cliente
result = eon_search_quotes({"client_name": "Citanias", "status": "draft"})

# Duplicar antes de modificar
result = eon_duplicate_quote("PRE-2026-0001")
new_id = result["result_quote_id"]

# Aplicar cambios en copia (por defecto)
result = eon_apply_commands("PRE-2026-0001", [
    {"type": "set_global_margin", "margin": 38}
])
# result["result_quote_id"] → nuevo presupuesto con los cambios

# Probar cambios sin guardar
result = eon_apply_commands("PRE-2026-0001", [...], save_mode="dry_run")

# Generar informe
result = eon_generate_internal_report("PRE-2026-0001", html=True)

# Exportar a Holded
result = eon_export_holded_payload("PRE-2026-0001")
```

Endpoints de API:

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/eon/tools` | Lista todas las herramientas |
| `GET` | `/eon/search` | Búsqueda con filtros |
| `GET` | `/eon/quotes/{id}` | Carga presupuesto |
| `GET` | `/eon/quotes/{id}/summary` | Resumen con semáforo |
| `GET` | `/eon/quotes/{id}/calculate` | Cálculo de totales |
| `POST` | `/eon/quotes/{id}/duplicate` | Duplicar |
| `POST` | `/eon/quotes/{id}/commands` | Aplicar comandos |
| `GET` | `/eon/quotes/{id}/report` | Informe interno |
| `GET` | `/eon/quotes/{id}/report/html` | Informe HTML |
| `GET` | `/eon/quotes/{id}/export/holded` | Payload Holded |
| `POST` | `/eon/quotes/{id}/archive` | Archivar |

CLI:

```bash
# Ver herramientas disponibles
python -m quote_cli eon-tools

# Resumen de un presupuesto
python -m quote_cli eon-summary PRE-2026-0001
python -m quote_cli eon-summary PRE-2026-0001 --json
```

---

## Búsqueda local de presupuestos

A partir de v0.7 es posible buscar entre los presupuestos guardados sin base de datos. La búsqueda lee directamente los archivos JSON de `data/quotes/`, calcula totales y semáforo en tiempo real, y aplica los filtros sobre los resultados.

Sirve para que EON (u otros operadores) puedan localizar presupuestos antiguos por cliente, proveedor, rango de beneficio, estado, etc.

```bash
# Búsqueda por texto libre (cliente, proveedor, descripción de línea, tags...)
python -m quote_cli search citanias
python -m quote_cli search "bomba calor"

# Filtros específicos
python -m quote_cli search --client Citanias
python -m quote_cli search --supplier Frigicoll
python -m quote_cli search --status accepted
python -m quote_cli search --project-type climatizacion
python -m quote_cli search --tag split

# Filtros numéricos
python -m quote_cli search --min-profit 500
python -m quote_cli search --max-total 2000

# Filtros de calidad
python -m quote_cli search --has-problems
python -m quote_cli search --has-warnings

# Combinados
python -m quote_cli search citanias --status draft --min-profit 300 --limit 5

# Últimos presupuestos actualizados
python -m quote_cli recent
python -m quote_cli recent --limit 5
python -m quote_cli recent --json

# Salida JSON
python -m quote_cli search --supplier Frigicoll --json
```

Salida de texto:
```
3 presupuestos encontrados

PRE-2026-0001 | draft | Citanias Obras Y Servicios Slu | Total: 878.93 € | Beneficio: 210.50 € | Estado: OK
PRE-2026-0002 | accepted | Citanias Obras Y Servicios Slu | Total: 556.40 € | Beneficio: 120.00 € | Estado: REVISAR
```

Los endpoints de API equivalentes son:

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/storage/search` | Búsqueda con filtros (query params) |
| `GET` | `/storage/recent` | Últimos presupuestos |

Parámetros de `/storage/search`: `q`, `client`, `supplier`, `status`, `project_type`, `tag`, `min_profit`, `max_profit`, `min_total`, `max_total`, `has_warnings`, `has_problems`, `sort_by`, `descending`, `limit`.

---

## Guardado local de presupuestos

A partir de v0.4 los presupuestos se pueden guardar y recuperar como archivos JSON locales. No se usa base de datos.

**Dónde se guardan**

```
data/quotes/PRE-2026-0001.json
data/quotes/PRE-2026-0002.json
...
```

**Cómo se identifican**

Cada presupuesto recibe un ID correlativo con formato `PRE-YYYY-NNNN`. Se genera automáticamente al guardar o se puede indicar uno explícito.

**Metadata incluida**

```json
{
  "metadata": {
    "id": "PRE-2026-0001",
    "created_at": "2026-06-28T18:30:00",
    "updated_at": "2026-06-28T18:45:00",
    "created_by": "EON",
    "source": "api",
    "status": "draft",
    "project_type": "climatizacion",
    "tags": ["split", "vivienda"],
    "client_reference": null,
    "internal_notes": null,
    "version": "0.4"
  },
  "snapshot": { ... }
}
```

`status` puede ser: `draft`, `sent`, `accepted`, `rejected`, `archived`.  
`created_at` nunca cambia. `updated_at` se actualiza en cada guardado.

**Endpoints de almacenamiento**

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/storage/quotes` | Guardar presupuesto |
| `GET` | `/storage/quotes` | Listar (con filtros opcionales) |
| `GET` | `/storage/quotes/{id}` | Cargar por ID |
| `POST` | `/storage/quotes/{id}/duplicate` | Duplicar |
| `PATCH` | `/storage/quotes/{id}/metadata` | Actualizar metadata |
| `POST` | `/storage/quotes/{id}/archive` | Archivar |

Los presupuestos archivados no se borran físicamente; solo cambia el `status`.

**Sin base de datos**

Todo se guarda como JSON legible en `data/quotes/`. No se requiere MongoDB, PostgreSQL ni SQLite.

---

## Archivos de ejemplo

```
data/examples/
├── basic_supplier_import.json          — importación básica con 3 líneas
├── command_set_margin.json             — cambiar margen de una línea
├── command_apply_supplier_margin.json  — aplicar margen a proveedor
├── command_pass_supplier_discount.json — repercutir descuento de proveedor al cliente
├── holded_export_example.json          — payload de exportación Holded
└── storage_quote_example.json          — presupuesto guardado con metadata (v0.4)
```

---

## Estructura del proyecto

```
index_quote_engine/
├── quote_engine/          — librería Python pura (núcleo)
│   ├── models.py          — QuoteSnapshot, QuoteLine, CalculatedQuote, QuoteMetadata
│   ├── discounts.py       — descuentos encadenados
│   ├── calculator.py      — calculate_quote()
│   ├── normalizer.py      — normalize_supplier_json()
│   ├── commands.py        — apply_command() / apply_commands()
│   ├── validators.py      — validaciones compartidas
│   ├── document_rules.py  — reglas documentales obligatorias
│   ├── storage.py         — guardado/carga local de presupuestos
│   └── exporters/
│       ├── holded.py
│       └── internal_report.py
├── quote_api/             — FastAPI (sin lógica de negocio en endpoints)
│   ├── main.py
│   └── routes.py
├── quote_cli/             — CLI (argparse, sin dependencias extra)
│   ├── __init__.py
│   ├── __main__.py        — permite `python -m quote_cli`
│   └── main.py            — list, show, calculate, save, duplicate, archive, export-holded, report
├── tests/                 — 195 tests (pytest)
├── data/
│   ├── quotes/            — presupuestos guardados (PRE-YYYY-NNNN.json)
│   ├── examples/          — JSONs de ejemplo
│   ├── exports/           — exportaciones futuras
│   └── reports/           — informes futuros
├── pyproject.toml
└── README.md
```
