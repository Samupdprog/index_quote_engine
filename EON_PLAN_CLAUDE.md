# Proyecto EON / Index Quote Engine — Arquitectura con Docker, base de datos y aprendizaje progresivo

Quiero que trabajes sobre el proyecto actual del generador de presupuestos de EON / Index Clima.

Objetivo general: convertir el generador de presupuestos en un sistema sólido, ampliable y fiable, con Docker, PostgreSQL, importación de Excel, histórico de presupuestos, trazabilidad de precios, correcciones, aprendizajes aprobables y tests. De momento NO vamos a hacer frontend. EON usará el motor/API para generar, revisar y mejorar presupuestos.

No me pidas autorización para cada fase. Ejecuta el plan completo por fases, haciendo cambios razonables y seguros en el repositorio. Solo debes parar si una acción implica borrar datos reales, tocar secretos, hacer escrituras en Holded, modificar facturas, eliminar archivos importantes sin backup o cambiar algo destructivo en producción.

## Contexto operativo

EON es un asistente interno de Index Clima. Su trabajo principal es ayudar a generar presupuestos/proformas de instalaciones, reparaciones, mantenimientos y suministros.

Reglas importantes:

* La IA no debe calcular importes manualmente.
* Todo cálculo debe pasar por el motor Python `index_quote_engine`.
* No inventar precios.
* No inventar cantidades.
* No inventar clientes, CIF, direcciones ni datos fiscales.
* Si falta un dato crítico, preguntar.
* Si falta un dato no crítico, continuar y marcar `PENDIENTE`.
* Obsidian se usará como memoria de conocimiento, reglas, procedimientos, aprendizajes y errores.
* La base de datos será la fuente estructurada de productos, precios, proveedores, presupuestos, partidas, correcciones y aprendizajes.
* Holded no se toca en esta fase salvo dejar preparada arquitectura futura. Nada de escrituras reales en Holded.

## Decisión técnica

Usar PostgreSQL con Docker Compose dentro del proyecto del generador de presupuestos.

No usar SQLite como base principal en esta fase.

La arquitectura deseada es:

```txt
index_quote_engine
│
├── docker-compose.yml
├── .env.example
├── data
│   ├── raw
│   ├── staging
│   ├── processed
│   └── reports
│
├── src / app / index_quote_engine
│   ├── db
│   ├── catalog
│   ├── importers
│   ├── pricing
│   ├── quotes
│   ├── learning
│   ├── validation
│   ├── renderers
│   └── api
│
├── migrations
│
├── tests
│   ├── catalog
│   ├── importers
│   ├── pricing
│   ├── quotes
│   ├── learning
│   └── regression_presupuestos
│
└── docs
    ├── ARCHITECTURE.md
    ├── PHASES.md
    ├── DATABASE.md
    ├── IMPORT_EXCEL.md
    ├── LEARNING_FLOW.md
    └── OBSIDIAN_STRUCTURE.md
```

Adapta los nombres a la estructura real del repo si ya existe una convención, pero mantén esta separación lógica.

---

# FASE 0 — Auditoría inicial del proyecto

Antes de modificar, inspecciona el proyecto actual.

Tareas:

1. Detectar estructura actual del repositorio.
2. Detectar si ya existe FastAPI, CLI, motor de cálculo, tests, requirements, pyproject o similar.
3. Detectar cómo se llama actualmente el paquete principal.
4. Detectar si ya hay endpoints tipo `/eon/tools`.
5. Detectar dónde se debe integrar el nuevo módulo de base de datos.
6. Crear un documento:

```txt
docs/ARCHITECTURE_STATUS.md
```

Debe incluir:

* estructura actual encontrada;
* motor actual de presupuestos;
* puntos de entrada;
* dependencias actuales;
* riesgos;
* propuesta de integración sin romper lo existente.

Criterio de aceptación:

* El proyecto sigue funcionando igual que antes.
* No se rompe ningún comando existente.
* Queda documentado el estado inicial.

---

# FASE 1 — Docker Compose con PostgreSQL

Crear Docker Compose para base de datos PostgreSQL.

Archivos esperados:

```txt
docker-compose.yml
.env.example
scripts/db_up.ps1
scripts/db_down.ps1
scripts/db_logs.ps1
scripts/db_reset_dev.ps1
```

Si el proyecto usa Linux/Mac también, añade equivalentes `.sh`, pero prioriza Windows/PowerShell.

Docker Compose debe incluir:

* servicio `postgres`;
* base de datos `eon_index_clima`;
* usuario configurable;
* contraseña configurable;
* volumen persistente;
* healthcheck;
* puerto local configurable, por ejemplo `5435:5432`, para evitar conflictos.

Ejemplo conceptual:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: eon-index-postgres
    environment:
      POSTGRES_DB: eon_index_clima
      POSTGRES_USER: eon
      POSTGRES_PASSWORD: eon_dev_password
    ports:
      - "5435:5432"
    volumes:
      - eon_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U eon -d eon_index_clima"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  eon_postgres_data:
```

No guardar secretos reales. Solo `.env.example`.

Crear documentación:

```txt
docs/DATABASE.md
```

Debe explicar:

* cómo arrancar la base;
* cómo pararla;
* cómo resetear en desarrollo;
* variables de entorno;
* cómo comprobar conexión.

Criterio de aceptación:

* `docker compose up -d` arranca PostgreSQL.
* Hay healthcheck.
* El proyecto tiene `.env.example`.
* No hay secretos reales versionados.

---

# FASE 2 — Capa de base de datos y migraciones

Añadir SQLAlchemy 2.x y Alembic, salvo que el proyecto ya use otra herramienta equivalente.

Crear módulo:

```txt
db/
  session.py
  base.py
  models.py
  repositories/
```

Crear migraciones para estas tablas principales:

## suppliers

```txt
id
name
normalized_name
contact_name
phone
email
notes
is_active
created_at
updated_at
```

## products

```txt
id
internal_code
supplier_reference
description
normalized_description
category
subcategory
unit_purchase
unit_calc
conversion_factor
is_active
created_at
updated_at
```

## supplier_prices

```txt
id
product_id
supplier_id
source_type
source_file
source_sheet
source_row
document_number
document_date
quantity
gross_unit_price
discount_percent
net_unit_price
line_total
igic_rate
igic_included
currency
confidence
is_current
created_at
updated_at
```

## price_import_batches

```txt
id
source_file
source_hash
imported_at
status
total_rows
created_products
updated_products
created_prices
warnings_count
errors_count
report_path
```

## quote_cases

```txt
id
reference
client_name
client_location
quote_type
status
input_original
extracted_data_json
pending_data_json
warnings_json
created_at
updated_at
approved_at
```

## quote_line_items

```txt
id
quote_case_id
product_id
supplier_price_id
category
description
quantity
unit
internal_unit_cost
client_unit_price
internal_total_cost
client_total_price
confidence
source_reason
created_at
updated_at
```

## quote_totals

```txt
id
quote_case_id
internal_total_cost
client_total_without_igic
igic_rate
igic_amount
client_total_with_igic
benefit
margin_percent
created_at
updated_at
```

## quote_corrections

```txt
id
quote_case_id
field_path
old_value
new_value
correction_reason
created_by
created_at
```

## learning_items

```txt
id
source_quote_case_id
type
title
description
proposed_rule
status
approved_by
approved_at
created_at
updated_at
```

## error_cases

```txt
id
title
description
cause
solution
status
related_quote_case_id
created_at
updated_at
```

Criterio de aceptación:

* Se puede ejecutar migración desde cero.
* Se puede conectar a PostgreSQL.
* Hay tests mínimos de conexión y creación de tablas.
* La documentación indica cómo correr migraciones.

---

# FASE 3 — Importador del Excel de productos

Crear un importador robusto para el Excel actual de productos consolidados/comparativa.

Ubicación sugerida:

```txt
importers/excel_products_importer.py
```

Entrada:

```txt
data/raw/Productos_Consolidados_Index_Clima_actualizado_v5_comparativa.xlsx
```

Si el archivo no existe, crear instrucciones claras en `docs/IMPORT_EXCEL.md`.

El importador debe:

1. Leer todas las hojas relevantes del Excel.
2. Detectar hojas:

   * productos consolidados;
   * comparativa proveedores;
   * detalle comparativa;
   * cualquier hoja útil existente.
3. Normalizar nombres de productos.
4. Normalizar proveedores.
5. Detectar precios netos unitarios.
6. Detectar descuentos.
7. Detectar fechas.
8. Detectar cantidades.
9. Guardar cada importación como batch.
10. Guardar datos en staging o directamente como precios históricos, pero sin marcar todo como actual sin comprobar.
11. Calcular hash del archivo para evitar importaciones duplicadas.
12. Generar informe de importación en:

```txt
data/reports/import_report_<fecha>.md
```

El informe debe incluir:

* productos detectados;
* proveedores detectados;
* precios creados;
* precios actualizados;
* productos dudosos;
* filas ignoradas;
* errores;
* advertencias;
* productos sin código;
* productos con unidades dudosas;
* precios negativos;
* posibles abonos;
* posibles duplicados.

Reglas importantes:

* No sobrescribir precios anteriores destructivamente.
* Mantener histórico.
* Si cambia mucho un precio, marcar advertencia.
* Si la unidad cambia, marcar advertencia.
* Si la confianza es baja, no usar automáticamente en presupuestos.

Crear comando CLI:

```bash
python -m index_quote_engine.importers.excel_products_importer --file data/raw/archivo.xlsx
```

O adaptarlo al CLI existente.

Criterio de aceptación:

* El importador corre sin romper el proyecto.
* Genera informe.
* Inserta proveedores/productos/precios.
* Mantiene histórico.
* Tiene tests con un Excel pequeño de fixture.

---

# FASE 4 — Servicio de catálogo y búsqueda de productos

Crear una capa de catálogo para que el motor no busque directamente en tablas.

Módulo sugerido:

```txt
catalog/
  service.py
  normalizer.py
  schemas.py
```

Debe exponer funciones como:

```python
search_products(query: str, category: str | None = None)
get_product_by_code(code: str)
find_best_price(product_query: str, quantity: float | None = None)
```

La búsqueda debe usar prioridad:

1. código exacto;
2. referencia proveedor exacta;
3. descripción normalizada exacta;
4. similitud por texto;
5. categoría + similitud.

Cada resultado debe devolver:

```json
{
  "product_id": "...",
  "description": "...",
  "supplier": "...",
  "net_unit_price": 0,
  "unit": "...",
  "confidence": "alta|media|baja",
  "reason": "...",
  "source_file": "...",
  "source_sheet": "...",
  "source_row": 0,
  "document_date": "..."
}
```

Criterio de aceptación:

* Buscar "tubería", "canaleta", "nitrógeno", "cable" devuelve resultados razonables si existen.
* Cada resultado tiene fuente y confianza.
* Si no hay resultado claro, no inventa precio.

---

# FASE 5 — Reglas de pricing y selección de proveedor

Crear módulo:

```txt
pricing/
  selector.py
  rules.py
  schemas.py
```

Reglas:

1. Si hay coincidencia exacta por código y precio actual, usarlo.
2. Si hay varios proveedores con confianza alta, elegir el precio neto más bajo salvo que exista proveedor preferente.
3. Si hay confianza media, permitir usarlo pero marcar `REVISAR`.
4. Si hay confianza baja, no usar automáticamente.
5. Si el precio tiene fecha antigua, marcar advertencia.
6. Si el precio es negativo, no usar como precio actual salvo que esté marcado como abono.
7. Si hay diferencia de precio muy alta respecto al histórico, marcar advertencia.
8. No mezclar unidades sin conversion_factor.
9. No convertir rollos/metros sin regla definida.
10. No añadir margen extra al pequeño material si ya viene como precio cliente.

Debe devolver siempre trazabilidad:

```json
{
  "selected": true,
  "price": 0,
  "supplier": "",
  "confidence": "",
  "warnings": [],
  "reason": "",
  "source": {}
}
```

Criterio de aceptación:

* Hay tests para selección de proveedor.
* Hay tests para confianza alta/media/baja.
* Hay tests para precio antiguo.
* Hay tests para precio negativo.
* Hay tests para unidad dudosa.

---

# FASE 6 — Integración con `index_quote_engine`

Integrar la base de datos y el catálogo en el motor actual de presupuestos.

El motor debe seguir siendo la única fuente de cálculo.

La IA/EON solo interpreta y llama al motor.

El motor debe generar siempre dos salidas:

## 1. Presupuesto visible cliente

Debe contener:

* cliente;
* ubicación;
* fecha;
* descripción del trabajo;
* equipos incluidos;
* instalación incluida;
* materiales principales;
* mano de obra;
* desplazamiento;
* exclusiones;
* base imponible;
* IGIC;
* total con IGIC.

## 2. Ficha interna

Debe contener:

* coste real de máquinas;
* coste real de materiales;
* precio cobrado por materiales;
* coste real mano de obra por empleado;
* venta mano de obra;
* transporte;
* portes;
* nitrógeno;
* extras;
* coste total;
* precio cliente sin IGIC;
* precio cliente con IGIC;
* beneficio;
* margen;
* avisos;
* datos pendientes;
* fuentes usadas.

El resultado técnico del motor debe incluir:

```json
{
  "quote_case_id": "...",
  "client_quote": {},
  "internal_sheet": {},
  "line_items": [],
  "totals": {},
  "warnings": [],
  "pending_data": [],
  "sources": [],
  "confidence_summary": {}
}
```

Criterio de aceptación:

* Presupuesto básico funciona.
* Si falta precio, lo marca.
* Si falta dato crítico, lo indica.
* Si hay dato no crítico, continúa con `PENDIENTE`.
* No se calcula nada manualmente fuera del motor.
* Todas las partidas tienen fuente o quedan como pendientes.

---

# FASE 7 — Guardar presupuestos como casos históricos

Cada presupuesto generado debe guardarse en `quote_cases`.

Guardar:

* input original;
* datos extraídos;
* partidas;
* precios usados;
* fuentes;
* avisos;
* pendientes;
* totales;
* resultado cliente;
* ficha interna.

Crear funciones:

```python
save_quote_case(...)
get_quote_case(reference)
list_recent_quote_cases(limit=20)
```

Crear endpoint o comando CLI para consultar últimos casos.

Criterio de aceptación:

* Cada presupuesto genera un caso.
* Se puede recuperar.
* Se puede listar.
* Se puede ver qué precios usó y de dónde salieron.

---

# FASE 8 — Sistema de correcciones y aprendizaje

Crear módulo:

```txt
learning/
  corrections.py
  proposer.py
  approval.py
```

Flujo:

1. EON genera presupuesto.
2. Samuel corrige algo.
3. Se registra corrección.
4. El sistema compara valor anterior vs nuevo.
5. Propone aprendizaje.
6. El aprendizaje queda en estado `pending`.
7. Solo si Samuel lo aprueba, pasa a `approved`.
8. Un aprendizaje aprobado puede crear:

   * nota en Obsidian;
   * regla interna;
   * test de regresión;
   * aviso futuro.

No aplicar automáticamente reglas críticas sin aprobación.

Tipos de aprendizaje:

```txt
pricing_rule
exclusion_rule
transport_rule
labor_rule
material_rule
supplier_preference
template_text
error_pattern
client_exception
```

Ejemplo de aprendizaje:

```json
{
  "type": "transport_rule",
  "title": "Transporte reducido en obras cercanas",
  "description": "Samuel cambió transporte de 30 €/día a 15 €/día por cercanía.",
  "proposed_rule": "Si la obra está muy cerca y Samuel lo indica, permitir transporte reducido y registrar motivo.",
  "status": "pending"
}
```

Criterio de aceptación:

* Se puede registrar corrección.
* Se propone aprendizaje.
* No se aprueba solo.
* Se puede aprobar.
* El aprendizaje queda trazado.

---

# FASE 9 — Integración con Obsidian

No usar Obsidian como base de datos. Usarlo como memoria humana.

Crear estructura recomendada si no existe:

```txt
D:\INDEX_CLIMA_CONOCIMIENTO_IA
│
├── 00_INDICE_GENERAL_EON.md
│
├── EON
│   ├── 00_Mapa_EON.md
│   ├── Reglas_Validadas
│   ├── Plantillas
│   ├── Procedimientos
│   ├── Aprendizajes_Pendientes
│   ├── Aprendizajes_Aprobados
│   ├── Errores_Corregidos
│   ├── Presupuestos_Casos
│   └── Tests
│
├── Productos
│   ├── Politica_Precios.md
│   ├── Reglas_Comparativa_Proveedores.md
│   └── Proveedores.md
│
└── Holded
```

Crear módulo:

```txt
obsidian/
  writer.py
  templates.py
  indexer.py
```

Debe poder generar notas Markdown, pero no modificar documentación crítica sin backup.

Notas automáticas permitidas:

* aprendizaje pendiente;
* aprendizaje aprobado;
* error corregido;
* resumen de presupuesto;
* informe de importación;
* procedimiento validado.

Crear o actualizar:

```txt
00_INDICE_GENERAL_EON.md
EON/00_Mapa_EON.md
Productos/Politica_Precios.md
Productos/Reglas_Comparativa_Proveedores.md
```

Criterio de aceptación:

* Se puede generar nota de aprendizaje pendiente.
* Se puede generar nota de aprendizaje aprobado.
* Se puede generar resumen de presupuesto.
* No se guardan secretos.
* No se destruyen notas existentes.

---

# FASE 10 — Tests de regresión de presupuestos

Crear carpeta:

```txt
tests/regression_presupuestos
```

Crear casos mínimos:

```txt
split_basico.json
multisplit_2x1.json
conductos_con_soldadura.json
reparacion_sin_maquina.json
mantenimiento_sin_materiales.json
presupuesto_con_margen_bajo.json
interconexion_instalada_mas_mano_obra.json
transporte_distinto_30_dia.json
precio_material_no_encontrado.json
producto_con_confianza_baja.json
```

Cada caso debe comprobar:

* aplica IGIC 7 %;
* calcula margen;
* avisa margen menor al 15 %;
* no duplica mano de obra;
* avisa si transporte no sigue 30 €/día;
* avisa si falta precio;
* avisa si falta máquina cuando debería haber máquina;
* no usa precio con confianza baja;
* mantiene trazabilidad de fuentes.

Crear comando:

```bash
pytest tests/regression_presupuestos
```

Criterio de aceptación:

* Tests pasan.
* Si se cambia una regla y rompe algo, los tests lo detectan.

---

# FASE 11 — API interna para EON

Si ya existe FastAPI, ampliar. Si no existe, crear API simple.

Endpoints sugeridos:

```txt
GET  /eon/tools
GET  /health
GET  /catalog/search?q=
POST /catalog/import-excel
POST /quotes/draft
GET  /quotes/recent
GET  /quotes/{reference}
POST /quotes/{reference}/corrections
POST /learning/{id}/approve
GET  /learning/pending
```

No crear frontend.

La API debe devolver JSON claro para que EON/OpenClaw pueda usarlo.

Criterio de aceptación:

* API arranca.
* `/health` responde.
* `/eon/tools` lista capacidades.
* Se puede crear borrador de presupuesto.
* Se puede buscar producto.
* Se puede listar aprendizajes pendientes.

---

# FASE 12 — Documentación final

Crear o actualizar:

```txt
docs/ARCHITECTURE.md
docs/PHASES.md
docs/DATABASE.md
docs/IMPORT_EXCEL.md
docs/LEARNING_FLOW.md
docs/API.md
docs/OBSIDIAN_STRUCTURE.md
docs/DEVELOPMENT_COMMANDS.md
```

Debe incluir comandos listos para copiar:

```powershell
docker compose up -d
docker compose down
python -m alembic upgrade head
python -m pytest
python -m index_quote_engine.importers.excel_products_importer --file data/raw/archivo.xlsx
python -m index_quote_engine.api
```

Adapta los comandos reales a la estructura del proyecto.

---

# Reglas de seguridad y calidad

Durante todo el trabajo:

* No tocar `.env` real si existe.
* No mostrar secretos.
* No escribir en Holded.
* No tocar facturas.
* No eliminar datos sin backup.
* No romper comandos existentes.
* No cambiar reglas críticas sin test.
* No mezclar Obsidian con base de datos.
* No permitir que el LLM calcule importes.
* Todos los cálculos pasan por Python.
* Todo precio usado debe tener fuente o quedar como pendiente.
* Todo aprendizaje crítico queda pendiente hasta aprobación humana.

---

# Entregable final esperado

Al terminar, quiero que el proyecto tenga:

1. PostgreSQL en Docker funcionando.
2. Migraciones de base de datos.
3. Importador de Excel.
4. Catálogo de productos/precios.
5. Selector de precios con confianza.
6. Integración con el motor de presupuestos.
7. Histórico de presupuestos.
8. Sistema de correcciones.
9. Sistema de aprendizajes pendientes/aprobados.
10. Integración básica con Obsidian.
11. Tests de regresión.
12. API interna para EON.
13. Documentación clara.

Trabaja por fases. Al completar cada fase:

* ejecuta tests disponibles;
* documenta qué cambiaste;
* deja comandos para comprobarlo;
* continúa con la siguiente fase salvo bloqueo real.

No hagas frontend todavía.
