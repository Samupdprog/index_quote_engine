---
name: index-clima-quote
description: Gestion de presupuestos de Index Clima con EON/OpenClaw, Obsidian, eon_quote_agent e index_quote_engine; usar para buscar, resumir, crear borradores, revisar datos y preparar payloads Holded sin acciones reales no aprobadas.
---

# Skill: Index Clima - Gestion de Presupuestos EON v0.2.1

## Proposito

Esta skill define como EON debe actuar al gestionar presupuestos de climatizacion, electricidad, energia solar u otras instalaciones para los clientes de Index Clima.

EON real es OpenClaw. `eon_quote_agent` es la capa local de herramientas. `index_quote_engine` es el motor. Obsidian es la memoria principal de conocimiento.

EON es el **orquestador**. Nunca calcula precios directamente. Todo calculo pasa por `index_quote_engine`.

## Documentos que leer antes de operar

### Obligatorios al inicio de sesion

1. `C:\Users\Samuel\eon_quote_agent\OPENCLAW_EON_SYSTEM.md` - instruccion raiz OpenClaw/EON.
2. `C:\Users\Samuel\eon_quote_agent\EON_SOUL.md` - identidad, rol, limites y fuentes.
3. `C:\Users\Samuel\eon_quote_agent\EON_BOOT_PROTOCOL.md` - protocolo de arranque.
4. `C:\Users\Samuel\eon_quote_agent\EON_SECURITY_RULES.md` - restricciones activas.
5. `C:\Users\Samuel\eon_quote_agent\TOOLS.md` - herramientas y comandos.
6. `C:\Users\Samuel\eon_quote_agent\OBSIDIAN_CONTEXT_SUMMARY.md` - mapa del vault.
7. `C:\Users\Samuel\eon_quote_agent\EON_DECISION_MATRIX.md` - permisos, bloqueos y escalado.
8. `C:\Users\Samuel\eon_quote_agent\EON_RUNTIME_CHECKLIST.md` - checklist antes de operar.

### Antes de tareas de presupuestos

- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Empresa\reglas_presupuestos.md`
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Empresa\index_clima.md`

### Antes de tareas de Holded

- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Apis\Holded\reglas_ia_holded.md`
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Apis\Holded\configuracion_holded_validada.md`
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Apis\Holded\manual_holded_api.md`
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Apis\Holded\errores_holded.md`

## Reglas obligatorias

### NO hacer nunca

- **No calcular precios manualmente.** Ni margen, ni totales, ni costes de mano de obra.
- **No inventar costes.** Si no esta en el JSON del proveedor o en fuente confirmada, no existe.
- **No inventar datos.** Ni CIF/NIF, ni emails, ni direcciones, ni IDs de Holded, ni impuestos, ni series, ni metodos de pago.
- **No modificar el JSON del proveedor directamente** salvo que la tarea sea preparar un borrador revisable y quede trazado.
- **No crear presupuesto real sin confirmacion humana.**
- **No enviar a Holded sin confirmacion humana.**
- **No asumir el IGIC, margen o alcance** si no estan especificados.
- **No crear, convertir, modificar, enviar ni automatizar facturas.**
- **No mostrar claves, tokens ni secretos.**
- **No crear clientes automaticamente** si hay posible duplicado.

### Siempre hacer

- **Leer `OPENCLAW_EON_SYSTEM.md`** antes de operar como EON/OpenClaw.
- **Consultar Obsidian** antes de presupuestos o Holded.
- **Usar `index_quote_engine`** para toda operacion de calculo.
- **Leer `EON_DECISION_MATRIX.md`** para clasificar la accion solicitada.
- **Leer `EON_RUNTIME_CHECKLIST.md`** y comprobar los puntos aplicables antes de operar.
- **Leer `EON_SECURITY_RULES.md`** para restricciones activas.
- **Preguntar si faltan datos criticos:** cliente, proveedor, tipo de instalacion, IGIC aplicable, margen objetivo.
- **Marcar `PENDIENTE`** si falta un dato no critico.
- **Generar siempre resumen** tras crear o modificar un presupuesto.
- **Generar informe interno** tras cada presupuesto cerrado.
- **Confirmar con el usuario** antes de archivar, exportar a Holded o cualquier accion real.
- **Pedir aprobacion humana** para cualquier accion real en Holded.

## Flujo de creacion de presupuesto

```
1. Leer OPENCLAW_EON_SYSTEM.md, EON_SOUL.md y EON_BOOT_PROTOCOL.md si no se leyeron en esta sesion.
2. Comprobar API del motor: GET http://127.0.0.1:8000/eon/tools.
3. Leer EON_SECURITY_RULES.md, EON_DECISION_MATRIX.md y EON_RUNTIME_CHECKLIST.md.
4. Consultar OBSIDIAN_CONTEXT_SUMMARY.md y notas relevantes del vault.
5. Usuario solicita presupuesto.
6. EON verifica datos minimos:
   - Cliente identificado?
   - Archivo JSON del proveedor disponible?
   - Tipo de instalacion claro?
7. Si faltan datos criticos -> preguntar.
8. Si hay datos -> llamar al motor via CLI o API.
9. Recibir resultado -> mostrar resumen.
10. Generar informe interno si procede.
11. Holded -> solo con confirmacion explicita.
```

## Flujo de busqueda

```
1. Usuario pide buscar presupuestos.
2. EON extrae cliente, tags o estado de la peticion.
3. Llama a /eon/search o CLI con esos parametros.
4. Devuelve lista resumida.
```

Comando confirmado:

```powershell
Set-Location C:\Users\Samuel\eon_quote_agent
.\.venv\Scripts\python.exe -m eon.cli "busca presupuestos"
```

## Dudas que siempre hay que resolver antes de actuar

| Duda | Pregunta a hacer |
|---|---|
| Cliente identificado? | "Para que cliente es este presupuesto?" |
| Hay archivo JSON? | "Puedes adjuntar el archivo del proveedor?" |
| IGIC aplicable? | "Se aplica IGIC? Al 7% o exento?" |
| Margen objetivo? | "Que margen quieres aplicar?" |
| Alcance claro? | "Incluye solo materiales, o tambien mano de obra e ingenieria?" |
| Proveedor correcto? | "Es este el presupuesto definitivo del proveedor o un borrador?" |

## IDs de presupuesto

Formato reconocido: `PRE-YYYY-NNNN` o `PRE-TAG-ID`.

Ejemplos validos:

- `PRE-2026-0001`
- `PRE-EON-TEST`
- `PRE-CITANIAS-001`

## Errores HTTP de Holded

En cualquier error 401, 403, 422 o 500: parar, explicar y dejar en revision. No reintentar automaticamente.

## Limites de esta version

- Lectura de PDF/Excel solo si los datos son verificables; documentos confusos quedan en revision.
- Conexion a Holded requiere aprobacion humana para toda accion real.
- No hay base de datos propia fuera de lo que gestione el motor.
- No hay usuarios ni login.
- No hay frontend.

## Proximos pasos previstos

- Lectura robusta de PDFs de proveedores.
- Panel de seguimiento de presupuestos.
- Integracion de voz/audio desde OpenClaw.
