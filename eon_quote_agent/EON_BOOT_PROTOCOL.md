# EON_BOOT_PROTOCOL.md - Protocolo de arranque v0.2.9

Este protocolo define los pasos que EON debe seguir al iniciar una sesion de trabajo relacionada con presupuestos, Holded o documentacion de Index Clima.

## Secuencia de arranque

### 0. Leer instruccion raiz OpenClaw/EON

```
C:\Users\Samuel\eon_quote_agent\OPENCLAW_EON_SYSTEM.md
```

Confirmar que OpenClaw actua como EON y que `eon_quote_agent` es solo la capa local de herramientas.

### 1. Comprobar API del motor

```
GET http://127.0.0.1:8000/eon/tools
```

- Si responde: motor disponible. Continuar.
- Si no responde: avisar al usuario. No intentar calculos manuales.

### 2. Comprobar CLI de EON

```powershell
Set-Location C:\Users\Samuel\eon_quote_agent
.\.venv\Scripts\python.exe -m eon.cli "busca presupuestos"
```

- Si responde: CLI operativo.
- Si falla: verificar que `.venv` existe y tiene `httpx` instalado.
- No usar Python global si falta `httpx`.

### 3. Leer TOOLS.md

```
C:\Users\Samuel\eon_quote_agent\TOOLS.md
```

Confirmar rutas, comandos y notas operativas actualizadas.

### 4. Leer OBSIDIAN_CONTEXT_SUMMARY.md

```
C:\Users\Samuel\eon_quote_agent\OBSIDIAN_CONTEXT_SUMMARY.md
```

Obtener mapa del vault, notas relevantes y decisiones registradas.

### 5. Leer notas del vault segun la tarea

Solo abrir las notas que la tarea requiera:

- **Presupuestos:** `Empresa\reglas_presupuestos.md`, `Empresa\index_clima.md`
- **Holded:** `Apis\Holded\reglas_ia_holded.md`, `Apis\Holded\configuracion_holded_validada.md`, `Apis\Holded\manual_holded_api.md`, `Apis\Holded\errores_holded.md`
- **EON/configuracion:** `Eon\eon_informacion.md`, `Eon\eon_skill_operativa.md`
- **Especificaciones del motor:** `Presupuestos_IA\specs\requirements.md`, `Presupuestos_IA\specs\design.md`

No leer todo el vault. No abrir notas irrelevantes para la tarea actual.

### 6. Leer EON_SECURITY_RULES.md

```
C:\Users\Samuel\eon_quote_agent\EON_SECURITY_RULES.md
```

Confirmar restricciones activas antes de operar.

### 7. Leer matriz y checklist

```
C:\Users\Samuel\eon_quote_agent\EON_DECISION_MATRIX.md
C:\Users\Samuel\eon_quote_agent\EON_RUNTIME_CHECKLIST.md
```

Clasificar la accion solicitada antes de operar.

### 8. Confirmar estado

Antes de operar, EON debe tener claro:

- [ ] Motor API disponible (o avisado si no).
- [ ] CLI operativo (o avisado si no).
- [ ] Documentos de referencia leidos segun tarea.
- [ ] Restricciones de seguridad confirmadas.
- [ ] Accion clasificada.
- [ ] Facturas bloqueadas.
- [ ] Aprobacion humana confirmada si toca Holded real.
- [ ] Credenciales de integracion en almacen seguro (no texto plano). Ver `EON_SECRET_HANDLING_POLICY.md`.

Si todo esta en orden, proceder. Si hay fallos, informar al usuario antes de continuar.

## Cuando ejecutar este protocolo

- Al iniciar cualquier tarea de presupuestos.
- Al iniciar cualquier tarea de Holded.
- Al iniciar revision de documentacion de Index Clima.
- No es necesario repetirlo si la sesion ya lo completo y no ha cambiado el contexto.
