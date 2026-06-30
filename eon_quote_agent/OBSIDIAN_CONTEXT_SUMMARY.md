# Resumen de contexto Obsidian para EON

Fecha de revisión: 2026-06-28

Modo de trabajo usado: lectura sobre vaults de Obsidian. No se modificaron, movieron, copiaron ni borraron notas del vault.

## Vaults encontrados

1. `D:\INDEX_CLIMA_CONOCIMIENTO_IA`
   - Nombre de vault: `INDEX_CLIMA_CONOCIMIENTO_IA`
   - Carpeta `.obsidian`: `D:\INDEX_CLIMA_CONOCIMIENTO_IA\.obsidian`
   - Markdown aproximados: 70 en total.
   - Markdown propios relevantes excluyendo `.venv`: 25.

No se encontraron vaults bajo `C:\Users\Samuel` con la búsqueda solicitada. La búsqueda en `D:\` encontró el vault anterior.

## Notas relevantes principales

### Empresa y reglas de negocio

- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Empresa\index_clima.md`
  - Manual base de empresa: identidad, servicios, proceso general de presupuesto, diferencia entre documento visible para cliente y control interno, reglas generales para IA, datos que preguntar y datos que no asumir.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Empresa\reglas_presupuestos.md`
  - Reglas de presupuestos: cliente obligatorio o cliente de prueba, búsqueda de clientes, estados, tipos de línea, presupuestos de proveedor, descuentos, partida global, mano de obra, desplazamiento, presupuesto provisional, proformas, versionado, origen de datos y reglas antes de Holded.

### Holded

- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Apis\Holded\manual_holded_api.md`
  - Manual operativo de Holded API: autenticación, permisos, fechas, paginación, errores, contactos, impuestos, métodos de pago, productos, series, presupuestos, proformas, facturas y checklist de envío.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Apis\Holded\configuracion_holded_validada.md`
  - Fuente de verdad prevista para valores reales de Holded: impuestos, series, métodos de pago, contactos, presupuestos, proformas, sincronización y checklists. Hay varios valores aún pendientes de validación.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Apis\Holded\reglas_ia_holded.md`
  - Reglas de permisos para IA/OpenClaw con Holded. Define lo permitido, lo que requiere aprobación humana y lo prohibido.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Apis\Holded\errores_holded.md`
  - Guía de errores Holded: códigos HTTP, errores específicos del proyecto, reintentos, duplicados, logs y mensajes humanos recomendados.

### EON / OpenClaw / Modelos

- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Eon\eon_informacion.md`
  - Identidad, rol, permisos, prohibiciones, documentos principales, vault, modelos, routing, reglas Holded, logs y herramientas.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Eon\eon_skill_operativa.md`
  - Instrucciones operativas para EON: consulta del vault, selección de modelo, logs, UTF-8, PowerShell, comandos seguros, aprobación humana, tratamiento de secretos, presupuestos/proformas y Holded.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Eon\eon_estado_actual.md`
  - Estado actual: audio local, warnings, seguridad pendiente y proyecto generador de presupuestos.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Eon\eon_routing_modelos.md`
  - Routing entre modelo principal, fallback y modelo local. Qwen local se limita a tareas simples, internas y reversibles.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Eon\eon_fallos_y_lecciones.md`
  - Lecciones operativas: problemas de UTF-8 en PowerShell, `ConvertFrom-Json`, diagnósticos demasiado largos, timeouts, propuestas largas y notificaciones.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Eon\Logs\2026\06\2026-06-24_configuracion_openclaw.md`
  - Registro de configuración OpenClaw, acciones, errores, riesgos, decisiones y pendientes.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Eon\Logs\2026\06\2026-06-24_audio_openclaw.md`
  - Contexto de audio local y pruebas.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Eon\Logs\2026\06\2026-06-24_configuracion_final_modelos_audio.md`
  - Configuración final de modelos/audio.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Eon\QwenTTS_Pruebas\README_prueba_qwen_tts.md`
  - Pruebas de Qwen TTS.

### Generador de presupuestos IA

- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Presupuestos_IA\PLAN_MAESTRO_GENERADOR_PRESUPUESTOS_IA.md`
  - Visión, principios, alcance, contratos, convenciones numéricas, estados, Holded, arquitectura, persistencia y siguiente paso autorizado.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Presupuestos_IA\AUDITORIA_SPEC_GENERADOR_PRESUPUESTOS.md`
  - Auditoría técnica de especificación: incoherencias, riesgos, decisiones adoptadas, correcciones aplicadas y pendientes.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Presupuestos_IA\specs\requirements.md`
  - Requisitos funcionales: creación de borradores, validación, recálculo, duplicados, partida global, IGIC, aprobación, proformas y exportaciones.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Presupuestos_IA\specs\design.md`
  - Diseño técnico: FastAPI, Pydantic v2, contratos por fase, serialización Decimal, motor de cálculo, endpoints, Holded, Excel, persistencia futura, logs y pruebas.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Presupuestos_IA\specs\tasks.md`
  - Tareas por sprint: backend mínimo, schemas, utilidades Decimal, calculador, validador, endpoints `/budgets/validate` y `/budgets/recalculate`, tests y backlog.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Presupuestos_IA\ejemplos\json_presupuesto_ejemplos.md`
  - Ejemplos JSON de presupuestos. Es útil para validar contratos y comportamiento del motor.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Presupuestos_IA\ejemplos\presupuestos_index_clima.md`
  - Referencia auditada de presupuestos reales o históricos. No copiar datos de clientes en respuestas salvo que Samuel lo pida y sea necesario.
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Presupuestos_IA\logs\2026-06-24_inicio_generador_presupuestos.md`
  - Registro de inicio del proyecto de generador de presupuestos.

## Temas útiles para EON

- EON debe actuar como asistente interno de Index Clima: profesional, prudente, objetivo y sin inventar datos.
- La base de conocimiento principal está en `D:\INDEX_CLIMA_CONOCIMIENTO_IA`.
- Para presupuestos y proformas, separar siempre documento visible para cliente y control interno.
- Los costes, márgenes, desglose interno y datos sensibles no deben aparecer en documentos de cliente.
- Los datos desconocidos deben marcarse como `PENDIENTE` en texto o notas, no como valores numéricos.
- Si falta información crítica, EON debe preguntar o dejar el borrador como pendiente.
- Qwen/local se reserva para tareas simples, internas y reversibles; no debe decidir importes ni configuración crítica.
- Hay documentación de audio/local TTS y OpenClaw, pero su relevancia para presupuestos es secundaria.

## Reglas y decisiones sobre Index Clima y presupuestos

- Un presupuesto no es definitivo hasta revisión y aprobación humana.
- Para documentos reales debe existir cliente identificado o validado.
- Si no hay cliente, se puede usar cliente de prueba solo para borrador, no para envío real.
- Antes de crear cliente nuevo, hay que buscar posibles duplicados.
- EON no debe inventar CIF/NIF, direcciones, emails, precios, cantidades, descuentos, impuestos, series ni IDs de Holded.
- Si hay documentos de proveedor poco claros, deben quedar pendientes de revisión.
- La partida global se permite cuando el trabajo se explica mejor como resultado completo, pero requiere revisión.
- Las líneas informativas pueden ir a cero; una línea con precio desconocido debe ser `pendiente` con valores nulos, no una línea a cero.
- Los estados recomendados incluyen `borrador`, `pendiente_datos`, `pendiente_revision`, `validado_interno`, `aprobado`, `enviado_holded` y `error_sync`.
- No hay transición automática a `aprobado`; debe existir aprobación humana.
- Un documento `enviado_holded` no debe modificarse directamente; cualquier cambio requiere nueva versión interna o documento relacionado.

## Reglas y decisiones sobre Holded

- Facturas totalmente bloqueadas para IA por ahora: no crear, convertir, modificar, enviar, eliminar, descargar ni automatizar facturas.
- La IA puede trabajar con contactos, presupuestos, proformas, productos/servicios, impuestos, métodos de pago, series y PDFs de presupuestos/proformas según flujo y permisos.
- Acciones reales en Holded requieren validaciones previas y, en casos críticos, aprobación humana.
- No se deben usar impuestos, series ni métodos de pago sin ID real validado.
- Mientras falten IDs reales de Holded, `can_sync_holded` debe ser `false` y la salida debe quedar como borrador/revisión.
- Para Holded, el porcentaje visible de IGIC no sustituye al ID real del impuesto.
- El cliente Holded debe usar una allowlist de recursos permitidos y bloquear rutas relacionadas con facturas.
- Se deben registrar logs de sincronización con payload saneado, endpoint, respuesta y estado.

## Conexión útil con `index_quote_engine`

- El motor actual encaja con la especificación documentada: backend FastAPI, Pydantic v2 y cálculo con `Decimal`.
- El motor debe ser la fuente de cálculo; EON no debe calcular importes manualmente.
- Contratos útiles esperados por documentación:
  - `AIBudgetDraft`: propuesta de IA/OCR/texto con fuentes, supuestos, confianza y pendientes.
  - `BudgetDraft`: borrador editable y validable; usa strings decimales y permite `null` controlado.
  - `BudgetValidated`: salida calculada/validada sin campos críticos pendientes.
  - `BudgetHoldedPayload`: adaptador para presupuesto/proforma de Holded.
- Endpoints documentados relevantes para alinear con el motor:
  - `/budgets/validate`
  - `/budgets/recalculate`
  - `/holded/contacts/search`
  - `/holded/contacts/prepare-create`
  - `/holded/budgets/prepare-payload`
  - `/holded/budgets/sync-approved`
- En la instalación local de EON, la API activa se verificó en `http://127.0.0.1:8000` y el CLI debe ejecutarse desde `C:\Users\Samuel\eon_quote_agent` usando preferentemente `.\.venv\Scripts\python.exe -m eon.cli`.
- Al convertir contexto de Obsidian a operaciones del motor, EON debe producir o revisar JSON de entrada, pasar el cálculo/validación al motor y devolver advertencias/pendientes, no totales calculados a mano.

## Información sensible detectada

Sí hay indicios de información sensible o de seguridad en el vault, especialmente en:

- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Eon\Logs\2026\06\2026-06-24_configuracion_openclaw.md`
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Apis\Holded\manual_holded_api.md`
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Apis\Holded\errores_holded.md`
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Eon\eon_estado_actual.md`
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Eon\eon_skill_operativa.md`
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Eon\eon_routing_modelos.md`
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Eon\Logs\README_logs.md`
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Eon\Logs\2026\06\2026-06-24_configuracion_final_modelos_audio.md`
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Eon\eon_informacion.md`
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Presupuestos_IA\specs\design.md`
- `D:\INDEX_CLIMA_CONOCIMIENTO_IA\Apis\Holded\configuracion_holded_validada.md`

No se incluyen claves, contraseñas, tokens ni valores secretos en este resumen.

## Cosas que faltan o conviene preguntar a Samuel

- Confirmar IDs reales y validados de Holded para IGIC, series de presupuesto/proforma y métodos de pago.
- Confirmar si el motor `index_quote_engine` ya implementa todos los contratos documentados o solo una parte.
- Confirmar ruta y formato de almacenamiento real de presupuestos guardados que usa el motor.
- Confirmar si los ejemplos JSON de `Presupuestos_IA\ejemplos` deben incorporarse como fixtures de prueba del motor.
- Confirmar si EON debe leer automáticamente ciertas notas antes de cada presupuesto o solo cuando la tarea lo requiera.
- Confirmar criterio final de aprobación humana: quién aprueba y cómo debe quedar registrado.
- Confirmar qué acciones sobre Holded se permitirán más adelante y cuáles seguirán bloqueadas.
- Confirmar si se debe ignorar por defecto contenido dentro de `.venv` en futuras búsquedas del vault.

## Recomendación operativa

Antes de crear o revisar presupuestos:

1. Usar este resumen como mapa inicial.
2. Abrir las notas concretas necesarias del vault, no todo el vault.
3. Para cálculos o validaciones, usar siempre `index_quote_engine` mediante el CLI de EON.
4. Marcar datos ausentes como `PENDIENTE` y bloquear sincronización si faltan IDs reales de Holded.
5. No ejecutar acciones reales en Holded sin aprobación humana explícita.
6. Mantener facturas fuera de alcance.
