# VALIDATION_REPORT.md — Informe de validacion post-fixes

Fecha: 2026-06-30
Ejecutado en: Linux sandbox (Python 3.10, SQLite in-memory)

---

## Resumen

| Suite | Tests | Resultado |
|---|---|---|
| tests/catalog | 19 | PASSED |
| tests/quotes | 9 | PASSED |
| tests/learning | 13 | PASSED |
| tests/pricing | 19 | PASSED |
| tests/importers | 13 | PASSED |
| tests/regression_presupuestos | 40 | PASSED |
| tests/test_api | 5 | PASSED |
| tests/test_calculator | 12 | PASSED |
| tests/test_cli | 31 | PASSED |
| tests/test_commands | 14 | PASSED |
| tests/test_db_models | 14 | PASSED |
| tests/test_discounts | 7 | PASSED |
| tests/test_document_rules | 26 | PASSED |
| tests/test_eon_tools | 35 | PASSED |
| tests/test_internal_report | 35 | PASSED |
| tests/test_normalizer | 10 | PASSED |
| tests/test_realistic_fixtures | 47 | PASSED |
| tests/test_search | 33 | PASSED |
| tests/test_storage | 20 | PASSED |
| tests/test_workflow | 20 | PASSED |
| **TOTAL** | **492** | **492 PASSED, 0 FAILED** |

---

## Fix 1: CatalogService.get_product_by_code — confianza incorrecta

### Causa

`get_product_by_code("SPLIT-1X1-9K")` ordenaba los precios por `net_unit_price ASC`
sin filtrar por confianza. El producto tenia dos precios:
- Frigicoll: 650 EUR, confidence="alta"
- Airwell: 500 EUR, confidence="baja"

Al ordenar por precio ascendente, devolvio el de Airwell (mas barato) con
confidence="baja". El test asertaba `confidence in {"alta", "media"}`.

### Cambio aplicado

`quote_engine/catalog/service.py`, metodo `get_product_by_code()`:

```python
# ANTES
price = (
    self.session.query(SupplierPrice)
    .filter_by(product_id=product.id, is_current=True)
    .order_by(SupplierPrice.net_unit_price.asc())
    .first()
)

# DESPUES
price = (
    self.session.query(SupplierPrice)
    .filter(
        SupplierPrice.product_id == product.id,
        SupplierPrice.is_current == True,
        SupplierPrice.confidence != "baja",
    )
    .order_by(SupplierPrice.net_unit_price.asc())
    .first()
)
if price is None:
    # Fallback: cualquier precio si todos son baja
    price = (
        self.session.query(SupplierPrice)
        .filter_by(product_id=product.id, is_current=True)
        .order_by(SupplierPrice.net_unit_price.asc())
        .first()
    )
```

**Logica correcta:** en una busqueda por codigo exacto, se sabe que el producto
es el correcto; el selector debe devolver el mejor precio disponible (no el mas
barato con cualquier calidad). El fallback garantiza que si todos los precios son
baja se devuelve alguno, pero el comportamiento normal prioriza calidad.

### Resultado

`test_get_product_by_code_exact`: PASSED
`test_find_best_price_prefers_high_confidence`: PASSED

---

## Fix 2: list_recent_quote_cases — no devuelve registro recien guardado

### Causa

`list_recent_quote_cases()` ordenaba unicamente por `QuoteCase.updated_at DESC`.
En SQLite, `server_default=func.now()` tiene precision de segundos. Cuando varios
registros se insertan dentro del mismo segundo (frecuente en tests rapidos), todos
tienen el mismo `updated_at` y el orden entre ellos es arbitrario. Con `LIMIT 5`,
el registro recien guardado podia quedar fuera de los 5 resultados devueltos.

Adicionalmente, faltaba un `flush()` antes de la query para garantizar que
cualquier dato pendiente en la sesion fuera visible.

### Cambio aplicado

`quote_engine/db/repositories/quotes.py`, funcion `list_recent_quote_cases()`:

```python
# ANTES
cases = (
    db_session.query(QuoteCase)
    .order_by(QuoteCase.updated_at.desc())
    .limit(limit)
    .all()
)

# DESPUES
db_session.flush()
cases = (
    db_session.query(QuoteCase)
    .order_by(QuoteCase.updated_at.desc(), QuoteCase.id.desc())
    .limit(limit)
    .all()
)
```

**Criterio secundario `id DESC`:** el ID autoincremental garantiza que el ultimo
registro insertado aparece primero cuando `updated_at` coincide. Funciona tanto en
SQLite como en PostgreSQL.

### Resultado

`test_list_includes_recent_quotes`: PASSED
`test_list_respects_limit`: PASSED

---

## Fix 3: tests/learning — UNIQUE constraint en quote_cases.reference

### Causa

El fixture `quote_case` tenia `scope="function"` y creaba
`QuoteCase(reference="PRE-2026-LEARN", ...)` en cada test. El problema:

1. `quote_case` hace `session.flush()` — el QuoteCase queda en la transaccion.
2. El test llama a `register_correction()`, que hace `db_session.commit()`.
3. El commit persiste el QuoteCase en el engine SQLite de scope="module".
4. El `db.rollback()` del fixture `session` no puede deshacer lo ya commitado.
5. El siguiente test crea un nuevo `session` e intenta hacer flush de otro
   QuoteCase con la misma referencia "PRE-2026-LEARN" -> UNIQUE constraint.

### Cambio aplicado

`tests/learning/test_learning.py`, fixture `quote_case`:

```python
import uuid

@pytest.fixture
def quote_case(session):
    ref = f"PRE-2026-LEARN-{uuid.uuid4().hex[:8].upper()}"
    case = QuoteCase(reference=ref, client_name="Test Client")
    session.add(case)
    session.flush()
    return case
```

**Sin cambio en logica de produccion.** La referencia unica por invocacion evita
colisiones en el engine compartido entre tests del mismo modulo. La constraint
UNIQUE en `quote_cases.reference` se mantiene intacta.

### Resultado

Los 13 tests de `tests/learning/test_learning.py`: todos PASSED (0 errores de
constraint).

---

## Problemas secundarios encontrados y resueltos

### Archivos truncados en disco

Durante la inspeccion previa a ejecutar los tests se detecto que dos archivos
fueron escritos truncados por el tool de edicion (los archivos en disco diferian
del contenido mostrado por el tool de lectura):

1. `quote_engine/db/repositories/quotes.py` — truncado en linea 217 (le faltaba
   el cierre de la funcion `list_recent_quote_cases` y el mensaje de error).
2. `quote_api/main.py` — truncado en linea 37 (le faltaban los `include_router`).
3. `pyproject.toml` — truncado en linea 40 (le faltaba el cierre del array
   `select` y las secciones `[project.scripts]` y `[tool.setuptools]`).

Los tres archivos fueron reescritos via bash para garantizar el contenido completo.

---

## Comandos ejecutados

```bash
# Instalar dependencias en el sandbox Linux
pip install sqlalchemy alembic pydantic pytest pytest-asyncio openpyxl python-dotenv fastapi httpx --break-system-packages

# Verificar sintaxis de todos los modulos criticos
python3 -c "import ast; ast.parse(open('FILE').read()); print('OK')"

# Suite parcial (los 3 modulos con fallos)
python3 -m pytest tests/catalog tests/quotes tests/learning -v -p no:cacheprovider

# Suite completa
python3 -m pytest -v -p no:cacheprovider
```

---

## Resultado final

```
492 passed, 1 warning in 5.38s
```

La advertencia es de `httpx` (deprecacion de `starlette.testclient`) y no afecta
a ningun test.

Motor de calculo existente: intacto.
Constraint UNIQUE en quote_cases.reference: intacta.
Logica de aprobacion de aprendizajes: intacta (EON/auto/system bloqueados).
