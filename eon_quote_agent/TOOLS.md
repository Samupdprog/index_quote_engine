# TOOLS.md - Herramientas y comandos de EON

## Regla raiz OpenClaw/EON

Antes de operar como EON, leer `OPENCLAW_EON_SYSTEM.md`.

## Motor de presupuestos

- **Proyecto:** `C:\Users\Samuel\index_quote_engine`
- **API local:** `http://127.0.0.1:8000`
- **Verificar disponibilidad:** `GET http://127.0.0.1:8000/eon/tools`

Para presupuestos, EON no calcula manualmente. Todo pasa por el motor.

## CLI de EON

**Comando correcto:**

```powershell
# Desde C:\Users\Samuel\eon_quote_agent
.\.venv\Scripts\python.exe -m eon.cli "<peticion>"
```

**No usar Python global** si no tiene `httpx` instalado. Usar siempre el `.venv` del proyecto.

### Ejemplos

```powershell
.\.venv\Scripts\python.exe -m eon.cli "busca presupuestos"
.\.venv\Scripts\python.exe -m eon.cli "busca presupuestos de Citanias"
.\.venv\Scripts\python.exe -m eon.cli "resumeme PRE-XXXX"
.\.venv\Scripts\python.exe -m eon.cli "hazme un presupuesto para Citanias" --file "ruta.json"
```

## Herramientas disponibles en el motor

| Herramienta | Descripcion |
|---|---|
| `eon_search_quotes` | Busca presupuestos con filtros |
| `eon_get_quote` | Carga un presupuesto por ID |
| `eon_summarize_quote` | Resumen legible con semaforo |
| `eon_calculate_quote` | Calcula totales, lineas e IGIC |
| `eon_duplicate_quote` | Copia un presupuesto con nuevo ID |
| `eon_apply_commands` | Aplica comandos a un presupuesto |
| `eon_generate_internal_report` | Informe interno (dict o HTML) |
| `eon_export_holded_payload` | Payload JSON para Holded (sin enviar) |
| `eon_archive_quote` | Archiva un presupuesto |

## Endpoints API

### Verificados y disponibles ahora

```
GET  /eon/tools                         - Lista de herramientas
GET  /eon/search?q=...                  - Busqueda de presupuestos
POST /workflow/quote                    - Workflow completo de presupuesto
GET  /eon/quotes/{id}/summary           - Resumen de presupuesto
GET  /eon/quotes/{id}/report            - Informe de presupuesto
GET  /eon/quotes/{id}/report/html       - Informe HTML de presupuesto
GET  /eon/quotes/{id}/export/holded     - Export Holded sin enviar
```

### Pendientes de confirmar

```
POST /budgets/validate                  - Validar borrador
POST /budgets/recalculate               - Recalcular presupuesto
GET  /holded/contacts/search?q=...      - Buscar contactos Holded
POST /holded/contacts/prepare-create    - Preparar creacion de contacto
POST /holded/budgets/prepare-payload    - Preparar payload Holded
POST /holded/budgets/sync-approved      - Sincronizar aprobado
```

### Bloqueados hasta aprobacion humana

```
Crear cliente real en Holded
Crear presupuesto real en Holded
Crear proforma real en Holded
```

Facturas: prohibidas.

## Vault de Obsidian

- **Ruta:** `D:\INDEX_CLIMA_CONOCIMIENTO_IA`
- **Resumen:** `C:\Users\Samuel\eon_quote_agent\OBSIDIAN_CONTEXT_SUMMARY.md`
- Consultar antes de tareas de presupuestos o Holded.
- No modificar notas del vault salvo peticion explicita de Samuel.

## Documentos de configuracion EON

- `OPENCLAW_EON_SYSTEM.md` - Instruccion raiz OpenClaw/EON
- `EON_SOUL.md` - Identidad y comportamiento
- `EON_BOOT_PROTOCOL.md` - Protocolo de arranque
- `EON_MEMORY_MAP.md` - Mapa de recursos
- `EON_SECURITY_RULES.md` - Reglas de seguridad
- `EON_DECISION_MATRIX.md` - Matriz de decision
- `EON_RUNTIME_CHECKLIST.md` - Checklist operativo
