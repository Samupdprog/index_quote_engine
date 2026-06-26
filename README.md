# index_quote_engine · MVP 0.1

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

Resultado esperado: **54 passed**.

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

## Archivos de ejemplo

```
data/examples/
├── basic_supplier_import.json         — importación básica con 3 líneas
├── command_set_margin.json            — cambiar margen de una línea
├── command_apply_supplier_margin.json — aplicar margen a proveedor
├── command_pass_supplier_discount.json — repercutir descuento de proveedor al cliente
└── holded_export_example.json         — payload de exportación Holded
```

---

## Estructura del proyecto

```
index_quote_engine/
├── quote_engine/          — librería Python pura (núcleo)
│   ├── models.py          — QuoteSnapshot, QuoteLine, CalculatedQuote
│   ├── discounts.py       — descuentos encadenados
│   ├── calculator.py      — calculate_quote()
│   ├── normalizer.py      — normalize_supplier_json()
│   ├── commands.py        — apply_command() / apply_commands()
│   ├── validators.py      — validaciones compartidas
│   └── exporters/
│       ├── holded.py
│       └── internal_report.py
├── quote_api/             — FastAPI (sin lógica de negocio en endpoints)
│   ├── main.py
│   └── routes.py
├── tests/                 — 54 tests (pytest)
├── data/examples/         — JSONs de ejemplo
├── pyproject.toml
└── README.md
```
