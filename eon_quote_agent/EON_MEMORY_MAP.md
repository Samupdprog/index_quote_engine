# EON_MEMORY_MAP.md - Mapa de recursos v0.2.1

## Rutas principales

| Recurso | Ruta |
|---|---|
| Motor de presupuestos | `C:\Users\Samuel\index_quote_engine` |
| Agente/herramientas EON | `C:\Users\Samuel\eon_quote_agent` |
| Vault Obsidian | `D:\INDEX_CLIMA_CONOCIMIENTO_IA` |
| API local del motor | `http://127.0.0.1:8000` |
| Workspace OpenClaw | `C:\Users\Samuel\.openclaw\workspace` |

## Documentos de EON

| Documento | Ruta | Contenido |
|---|---|---|
| OPENCLAW_EON_SYSTEM.md | `eon_quote_agent\OPENCLAW_EON_SYSTEM.md` | Instruccion raiz para OpenClaw/EON |
| EON_SOUL.md | `eon_quote_agent\EON_SOUL.md` | Identidad, rol, limites, fuentes |
| EON_BOOT_PROTOCOL.md | `eon_quote_agent\EON_BOOT_PROTOCOL.md` | Protocolo de arranque |
| EON_MEMORY_MAP.md | `eon_quote_agent\EON_MEMORY_MAP.md` | Este mapa de recursos |
| EON_SECURITY_RULES.md | `eon_quote_agent\EON_SECURITY_RULES.md` | Reglas de seguridad |
| OBSIDIAN_CONTEXT_SUMMARY.md | `eon_quote_agent\OBSIDIAN_CONTEXT_SUMMARY.md` | Resumen del vault |
| TOOLS.md | `eon_quote_agent\TOOLS.md` | Herramientas y comandos |
| EON_DECISION_MATRIX.md | `eon_quote_agent\EON_DECISION_MATRIX.md` | Matriz de permisos y decisiones |
| EON_RUNTIME_CHECKLIST.md | `eon_quote_agent\EON_RUNTIME_CHECKLIST.md` | Checklist antes de operar |
| EON_BEHAVIOR_TESTS.md | `eon_quote_agent\EON_BEHAVIOR_TESTS.md` | Prueba de comportamiento |
| SKILL.md | `eon_quote_agent\skills\index-clima-quote\SKILL.md` | Skill de presupuestos |

## Documentos de Holded (vault)

| Documento | Ruta en vault |
|---|---|
| Reglas IA Holded | `Apis\Holded\reglas_ia_holded.md` |
| Configuracion validada | `Apis\Holded\configuracion_holded_validada.md` |
| Manual API Holded | `Apis\Holded\manual_holded_api.md` |
| Errores Holded | `Apis\Holded\errores_holded.md` |

## Documentos de presupuestos (vault)

| Documento | Ruta en vault |
|---|---|
| Reglas de presupuestos | `Empresa\reglas_presupuestos.md` |
| Manual de empresa | `Empresa\index_clima.md` |
| Plan maestro generador | `Presupuestos_IA\PLAN_MAESTRO_GENERADOR_PRESUPUESTOS_IA.md` |
| Requisitos funcionales | `Presupuestos_IA\specs\requirements.md` |
| Diseno tecnico | `Presupuestos_IA\specs\design.md` |
| Tareas por sprint | `Presupuestos_IA\specs\tasks.md` |
| Ejemplos JSON | `Presupuestos_IA\ejemplos\json_presupuesto_ejemplos.md` |

## Documentos de EON en vault

| Documento | Ruta en vault |
|---|---|
| Informacion EON | `Eon\eon_informacion.md` |
| Skill operativa | `Eon\eon_skill_operativa.md` |
| Estado actual | `Eon\eon_estado_actual.md` |
| Routing de modelos | `Eon\eon_routing_modelos.md` |
| Fallos y lecciones | `Eon\eon_fallos_y_lecciones.md` |

## Copias de respaldo (Downloads)

| Documento | Ruta |
|---|---|
| index_clima.md | `C:\Users\Samuel\Downloads\index_clima.md` |
| reglas_presupuestos.md | `C:\Users\Samuel\Downloads\reglas_presupuestos.md` |
| manual_holded_api.md | `C:\Users\Samuel\Downloads\manual_holded_api.md` |
| configuracion_holded_validada.md | `C:\Users\Samuel\Downloads\configuracion_holded_validada.md` |
| reglas_ia_holded.md | `C:\Users\Samuel\Downloads\reglas_ia_holded.md` |
| errores_holded.md | `C:\Users\Samuel\Downloads\errores_holded.md` |

## Comandos utiles

### CLI de EON

```powershell
# Desde C:\Users\Samuel\eon_quote_agent
.\.venv\Scripts\python.exe -m eon.cli "busca presupuestos"
.\.venv\Scripts\python.exe -m eon.cli "busca presupuestos de Citanias"
.\.venv\Scripts\python.exe -m eon.cli "resumeme PRE-XXXX"
.\.venv\Scripts\python.exe -m eon.cli "hazme un presupuesto para Citanias" --file "ruta.json"
```

## Endpoints API

### Verificados y disponibles ahora

```
GET  http://127.0.0.1:8000/eon/tools
GET  http://127.0.0.1:8000/eon/search?q=...
POST http://127.0.0.1:8000/workflow/quote
GET  http://127.0.0.1:8000/eon/quotes/{id}/summary
GET  http://127.0.0.1:8000/eon/quotes/{id}/report
GET  http://127.0.0.1:8000/eon/quotes/{id}/report/html
GET  http://127.0.0.1:8000/eon/quotes/{id}/export/holded
```

Estos endpoints son locales del motor/herramientas. Si alguno falla en runtime, no calcular manualmente.

### Pendientes de confirmar

```
POST http://127.0.0.1:8000/budgets/validate
POST http://127.0.0.1:8000/budgets/recalculate
GET  http://127.0.0.1:8000/eon/quotes/{id}
POST http://127.0.0.1:8000/eon/quotes/{id}/calculate
GET  http://127.0.0.1:8000/holded/contacts/search?q=...
POST http://127.0.0.1:8000/holded/contacts/prepare-create
POST http://127.0.0.1:8000/holded/budgets/prepare-payload
POST http://127.0.0.1:8000/holded/budgets/sync-approved
```

No listar endpoints de Holded como disponibles hasta que se prueben en el entorno real y quede documentado.

### Bloqueados hasta aprobacion humana

```
Crear cliente real en Holded
Crear presupuesto real en Holded
Crear proforma real en Holded
Cualquier accion real que escriba en Holded
Cualquier accion relacionada con facturas
```

Las facturas permanecen prohibidas aunque haya aprobacion operativa general.
