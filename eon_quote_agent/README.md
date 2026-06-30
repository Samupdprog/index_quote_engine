# EON/OpenClaw v0.2.1 - Operativa Index Clima

Este repositorio contiene la capa local de herramientas de EON para Index Clima. El README v0.1 describia EON como si este repositorio fuera todo el agente; en v0.2.1 la arquitectura queda separada asi:

- **OpenClaw/EON** es el agente vivo con IA, audio, contexto operativo y acceso a Obsidian.
- **`eon_quote_agent`** es la capa local de herramientas, CLI y reglas de orquestacion.
- **`index_quote_engine`** es el motor de calculo y validacion de presupuestos.
- **Obsidian** es la memoria principal de conocimiento interno.

EON no calcula precios manualmente. EON no inventa datos. EON no toca facturas. EON usa el motor y deja acciones reales de Holded bloqueadas hasta aprobacion humana.

## Documentos raiz

Antes de operar como EON/OpenClaw, leer:

- `OPENCLAW_EON_SYSTEM.md`
- `EON_SOUL.md`
- `EON_BOOT_PROTOCOL.md`
- `EON_SECURITY_RULES.md`
- `TOOLS.md`
- `OBSIDIAN_CONTEXT_SUMMARY.md`
- `EON_DECISION_MATRIX.md`
- `EON_RUNTIME_CHECKLIST.md`

## Que hace esta capa local

- Parsea intenciones en espanol para buscar, resumir y crear borradores de presupuesto.
- Llama a `index_quote_engine` via HTTP.
- Usa el CLI correcto desde el entorno virtual del proyecto.
- Devuelve resumen claro y marca datos pendientes.
- Prepara informacion revisable para Holded sin ejecutar acciones reales salvo aprobacion humana.

## Que no hace

- No calcula importes, margenes, impuestos, subtotales ni totales manualmente.
- No inventa precios, clientes, CIF/NIF, direcciones, IDs ni datos fiscales.
- No crea, modifica, convierte, envia ni automatiza facturas.
- No ejecuta Holded real sin aprobacion humana previa y explicita.
- No modifica el vault de Obsidian salvo peticion explicita.

## Conexion a `index_quote_engine`

EON espera que `index_quote_engine` este corriendo en `http://127.0.0.1:8000` o en la URL definida en `.env`.

Comprobacion:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/eon/tools
```

Endpoints locales verificados/documentados en esta version:

| Accion | Endpoint |
|---|---|
| Herramientas disponibles | `GET /eon/tools` |
| Buscar presupuestos | `GET /eon/search` |
| Validar borrador | `POST /budgets/validate` |
| Recalcular presupuesto | `POST /budgets/recalculate` |

Los endpoints de Holded no se asumen disponibles hasta prueba real documentada y aprobacion humana.

## Variables de entorno

Copia `.env.example` a `.env` y ajusta los valores:

```env
QUOTE_ENGINE_API_URL=http://127.0.0.1:8000
EON_DEFAULT_CREATED_BY=EON
EON_DEFAULT_SOURCE=eon
```

## Instalacion

```powershell
Set-Location C:\Users\Samuel\eon_quote_agent
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## CLI

Usar siempre el Python del entorno del proyecto:

```powershell
Set-Location C:\Users\Samuel\eon_quote_agent

# Buscar presupuestos
.\.venv\Scripts\python.exe -m eon.cli "busca presupuestos"

# Resumir un presupuesto
.\.venv\Scripts\python.exe -m eon.cli "resumeme PRE-2026-0001"

# Crear presupuesto con archivo JSON
.\.venv\Scripts\python.exe -m eon.cli "hazme un presupuesto para Citanias" --file data/input.json

# Salida JSON
.\.venv\Scripts\python.exe -m eon.cli "genera informe de PRE-2026-0001" --json
```

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Proximos pasos

- Lectura de PDFs de proveedores.
- Conexion real a Holded con flujo de confirmacion humana.
- Panel de seguimiento de presupuestos abiertos.
- Integracion de voz/audio desde OpenClaw.
