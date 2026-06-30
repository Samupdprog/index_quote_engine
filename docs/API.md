# API.md — API interna para EON

La API es una interfaz JSON local para que EON pueda generar, revisar y mejorar presupuestos.

**No hay frontend.** La API devuelve JSON.

**Base URL:** `http://localhost:8000`

---

## Arrancar la API

```powershell
python -m uvicorn quote_api.main:app --reload --host 127.0.0.1 --port 8000
```

Documentación interactiva (Swagger): `http://localhost:8000/docs`

---

## Endpoints

### Estado

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio |
| GET | `/eon/tools` | Lista todas las herramientas EON disponibles |

### Presupuestos (motor existente)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/quotes/calculate` | Calcula sin persistir |
| POST | `/quotes/import` | Importa desde JSON proveedor |
| POST | `/quotes/command` | Aplica un comando de modificación |
| POST | `/quotes/commands` | Aplica múltiples comandos |

### Storage JSON (existente)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/storage/quotes` | Guarda presupuesto como JSON |
| GET | `/storage/quotes` | Lista presupuestos JSON |
| GET | `/storage/quotes/{id}` | Carga presupuesto JSON |
| GET | `/storage/recent` | Últimos presupuestos |
| GET | `/storage/search` | Búsqueda en presupuestos JSON |

### EON Tools (fachada)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/eon/search` | Búsqueda filtrada |
| GET | `/eon/quotes/{id}` | Carga presupuesto |
| GET | `/eon/quotes/{id}/summary` | Resumen EON |
| GET | `/eon/quotes/{id}/calculate` | Calcula presupuesto |
| POST | `/eon/quotes/{id}/commands` | Aplica comandos |
| GET | `/eon/quotes/{id}/report` | Informe interno |
| GET | `/eon/quotes/{id}/export/holded` | Payload Holded |
| POST | `/eon/quotes/{id}/archive` | Archiva presupuesto |

### Catálogo (nuevo)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/catalog/search?q=` | Busca productos en catálogo |
| GET | `/catalog/product/{code}` | Busca por código interno |
| GET | `/catalog/best-price?q=` | Mejor precio disponible |
| POST | `/catalog/import-excel` | Importa Excel de productos |

### Base de datos — Presupuestos históricos (nuevo)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/db/quotes` | Guarda presupuesto en PostgreSQL |
| GET | `/db/quotes` | Lista últimos casos en DB |
| GET | `/db/quotes/{reference}` | Recupera caso de DB |

### Aprendizaje (nuevo)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/learning/pending` | Lista aprendizajes pendientes |
| POST | `/learning/{id}/approve` | Aprueba aprendizaje (solo humanos) |
| POST | `/learning/{id}/reject` | Rechaza aprendizaje |
| POST | `/learning/corrections` | Registra corrección |

---

## Ejemplos de uso

### Buscar en catálogo

```powershell
Invoke-RestMethod "http://localhost:8000/catalog/search?q=split%201x1&limit=5"
```

### Importar Excel

```powershell
$body = @{file_path="data/raw/archivo.xlsx"; dry_run=$true} | ConvertTo-Json
Invoke-RestMethod -Method POST http://localhost:8000/catalog/import-excel -Body $body -ContentType "application/json"
```

### Registrar corrección

```powershell
$body = @{
    quote_reference = "PRE-2026-0001"
    field_path = "lines[0].transport"
    old_value = "30"
    new_value = "15"
    correction_reason = "Obra cercana"
    created_by = "Samuel"
} | ConvertTo-Json
Invoke-RestMethod -Method POST http://localhost:8000/learning/corrections -Body $body -ContentType "application/json"
```

### Aprobar aprendizaje

```powershell
Invoke-RestMethod -Method POST "http://localhost:8000/learning/1/approve?approved_by=Samuel"
```

---

## Notas de seguridad

- Los aprendizajes solo pueden aprobarse con `approved_by` que no sea `eon`, `auto`, `system`, `ia`, `bot`.
- La API no escribe en Holded.
- La API no elimina datos de producción.
- Los secretos nunca aparecen en respuestas JSON.
