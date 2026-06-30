# IMPORT_EXCEL.md — Importador de Excel de productos

El importador lee el archivo Excel de productos consolidados y lo importa a PostgreSQL manteniendo historial completo de precios.

---

## Archivo de entrada esperado

```
data/raw/Productos_Consolidados_Index_Clima_actualizado_v5_comparativa.xlsx
```

Si el archivo tiene otro nombre, pásalo con `--file`.

**Estructura esperada del Excel:**
- Una o más hojas con productos por proveedor
- Cada hoja debe tener al menos columnas de descripción y precio neto
- El importador detecta automáticamente las columnas por nombre

**Nombres de columna reconocidos:**

| Tipo | Variantes reconocidas |
|---|---|
| Descripción | Descripcion, Artículo, Producto, Referencia, Concepto, Item, Material |
| Precio neto | Precio neto, P. Neto, Neto, Net, Precio final, Coste neto |
| Precio bruto | Tarifa, PVP, Precio bruto, Precio tarifa, Bruto |
| Descuento | Dto, Dto%, Descuento, Desc%, Discount |
| Unidad | Unidad, Ud, Unid. |
| Cantidad | Cantidad, Qty, Cant., Uds |
| Fecha | Fecha, Date, Fecha factura |
| Documento | Factura, Albarán, Nº Factura |

---

## Comandos

### Importar con base de datos activa

```powershell
# 1. Arrancar PostgreSQL
.\scripts\db_up.ps1

# 2. Aplicar migraciones
python -m alembic upgrade head

# 3. Importar Excel
python -m quote_engine.importers.excel_products_importer --file data/raw/archivo.xlsx
```

### Dry-run (sin escribir en DB)

```powershell
python -m quote_engine.importers.excel_products_importer --file data/raw/archivo.xlsx --dry-run
```

### Forzar reimportación (mismo archivo ya importado)

```powershell
python -m quote_engine.importers.excel_products_importer --file data/raw/archivo.xlsx --force
```

### Con logging detallado

```powershell
python -m quote_engine.importers.excel_products_importer --file data/raw/archivo.xlsx -v
```

---

## Informe de importación

Cada importación genera un informe Markdown en:

```
data/reports/import_report_YYYYMMDD_HHMMSS.md
```

El informe incluye:
- Proveedores detectados
- Productos detectados (los primeros 50)
- Precios creados y actualizados
- Productos dudosos
- Filas ignoradas
- Errores y warnings
- Productos sin código interno
- Productos con unidades de empaque (rollo, bobina, caja)
- Precios negativos (posibles abonos)
- Posibles duplicados de producto

---

## Reglas de importación

**Histórico:** Los precios anteriores nunca se eliminan. Cuando llega un nuevo precio para el mismo producto+proveedor, el precio anterior se marca como `is_current=False`.

**Confianza:**
- `alta` — Tiene precio bruto, descuento y fecha de documento
- `media` — Solo precio neto, o sin fecha
- `baja` — Datos incompletos o incongruentes

**Precios con confianza baja** no se usan automáticamente en presupuestos.

**Cambios de precio:** Si el precio nuevo difiere más del 30% del último precio conocido, se genera un warning.

**Unidades de empaque** (rollo, bobina, caja, pack) se marcan como dudosas porque pueden necesitar un `conversion_factor` para calcular precio por metro/unidad.

**Precios negativos:** Se registran como posibles abonos pero no se usan como precio actual.

**Hash deduplicación:** El importador calcula SHA-256 del archivo. Si el mismo archivo ya fue importado, se omite (salvo `--force`).

---

## Variables de entorno necesarias

```
POSTGRES_PASSWORD=tu_contraseña
POSTGRES_USER=eon
POSTGRES_DB=eon_index_clima
POSTGRES_PORT=5435
```

Sin estas variables, el importador funciona en modo dry-run automáticamente.
