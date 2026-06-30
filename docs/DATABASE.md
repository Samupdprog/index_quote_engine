# DATABASE.md — Base de datos PostgreSQL

EON usa PostgreSQL 16 via Docker Compose. Los datos persisten en un volumen Docker nombrado `eon_postgres_data`.

---

## Arrancar la base de datos

```powershell
# Opción 1 — script
.\scripts\db_up.ps1

# Opción 2 — manual
docker compose up -d postgres
```

El script espera automáticamente hasta que el healthcheck reporta `healthy`.

---

## Parar la base de datos (conserva datos)

```powershell
.\scripts\db_down.ps1
# o
docker compose stop postgres
```

---

## Resetear en desarrollo (DESTRUYE todos los datos)

```powershell
.\scripts\db_reset_dev.ps1
```

Pide confirmación. Solo para desarrollo. Tras el reset, aplica migraciones:

```powershell
python -m alembic upgrade head
```

---

## Variables de entorno

Copia `.env.example` como `.env` y ajusta:

| Variable | Default | Descripción |
|---|---|---|
| `POSTGRES_DB` | `eon_index_clima` | Nombre de la base de datos |
| `POSTGRES_USER` | `eon` | Usuario PostgreSQL |
| `POSTGRES_PASSWORD` | — | Contraseña (obligatorio cambiar) |
| `POSTGRES_PORT` | `5435` | Puerto local (evita conflictos con otras instancias) |
| `DATABASE_URL` | (construida) | URL SQLAlchemy completa (opcional override) |

```powershell
Copy-Item .env.example .env
# Editar .env con tu editor
```

---

## Comprobar conexión

```powershell
# Ver estado del contenedor
docker ps --filter name=eon-index-postgres

# Ver healthcheck
docker inspect --format='{{.State.Health.Status}}' eon-index-postgres

# Abrir psql interactivo
.\scripts\db_connect.ps1

# Ver logs
.\scripts\db_logs.ps1
.\scripts\db_logs.ps1 -Follow   # en tiempo real
```

---

## Aplicar migraciones

```powershell
# Desde el directorio raíz del proyecto
python -m alembic upgrade head

# Ver historial de migraciones
python -m alembic history

# Ver migración actual
python -m alembic current

# Revertir una migración
python -m alembic downgrade -1
```

---

## Conexión desde Python

```python
from quote_engine.db.session import get_db, engine

# Verificar conexión
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print("BD conectada:", result.scalar())
```

---

## Estructura de tablas

Ver `docs/ARCHITECTURE.md` para el esquema completo. Tablas principales:

- `suppliers` — Proveedores
- `products` — Productos/materiales
- `supplier_prices` — Historial de precios por proveedor
- `price_import_batches` — Registro de importaciones
- `quote_cases` — Presupuestos históricos
- `quote_line_items` — Partidas de presupuesto
- `quote_totals` — Totales calculados
- `quote_corrections` — Correcciones manuales
- `learning_items` — Aprendizajes pendientes/aprobados
- `error_cases` — Errores documentados
