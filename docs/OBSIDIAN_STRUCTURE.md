# OBSIDIAN_STRUCTURE.md — Estructura del vault Obsidian

Obsidian es la **memoria humana** de EON, no una base de datos. Los datos estructurados van en PostgreSQL; las notas, reglas, aprendizajes y procedimientos van en Obsidian.

---

## Vault por defecto

```
D:\INDEX_CLIMA_CONOCIMIENTO_IA
```

Configurable via variable de entorno `OBSIDIAN_VAULT` en `.env`.

---

## Estructura de carpetas

```
D:\INDEX_CLIMA_CONOCIMIENTO_IA\
│
├── 00_INDICE_GENERAL_EON.md           ← Índice general (auto-generado)
│
├── EON\
│   ├── 00_Mapa_EON.md                 ← Mapa del sistema EON (auto-generado)
│   ├── Reglas_Validadas\              ← Reglas aprobadas por Samuel
│   ├── Plantillas\                    ← Plantillas de presupuesto
│   ├── Procedimientos\                ← Procedimientos validados + resúmenes de importación
│   ├── Aprendizajes_Pendientes\       ← Aprendizajes esperando aprobación (PEND_*)
│   ├── Aprendizajes_Aprobados\        ← Aprendizajes aprobados por Samuel (APRO_*)
│   ├── Errores_Corregidos\            ← Errores documentados
│   ├── Presupuestos_Casos\            ← Resúmenes de presupuestos (PRE-YYYY-NNNN.md)
│   └── Tests\                         ← Tests y casos de prueba
│
├── Productos\
│   ├── Politica_Precios.md            ← Política de precios y márgenes
│   ├── Reglas_Comparativa_Proveedores.md ← Reglas para comparar proveedores
│   └── Proveedores.md                 ← Lista de proveedores
│
└── Holded\                            ← Reservado para integración futura Holded
```

---

## Crear estructura inicial

```python
from quote_engine.obsidian.writer import ensure_vault_structure
ensure_vault_structure()
```

O con variable de entorno configurada:

```powershell
$env:OBSIDIAN_VAULT = "D:\INDEX_CLIMA_CONOCIMIENTO_IA"
python -c "from quote_engine.obsidian.writer import ensure_vault_structure; ensure_vault_structure()"
```

---

## Notas generadas automáticamente

| Tipo | Directorio | Nombre |
|---|---|---|
| Aprendizaje pendiente | `EON/Aprendizajes_Pendientes/` | `PEND_0001_Titulo.md` |
| Aprendizaje aprobado | `EON/Aprendizajes_Aprobados/` | `APRO_0001_Titulo.md` |
| Resumen presupuesto | `EON/Presupuestos_Casos/` | `PRE-2026-0001.md` |
| Resumen importación | `EON/Procedimientos/` | `Import_20260630_120000.md` |

---

## Reglas de escritura

- Las notas pendientes **no se sobreescriben** (se añade sufijo `_1`, `_2`...).
- Las notas aprobadas **sí se actualizan** (reflejan el estado final).
- Los resúmenes de presupuesto se sobreescriben (siempre el estado más reciente).
- Nunca se guardan secretos (contraseñas, tokens, CIF) en notas Obsidian.
- No se modifica documentación crítica sin crear nueva nota.

---

## Integración

La integración Obsidian es **opcional y no bloqueante**. Si el vault no está configurado o no existe, las funciones de escritura devuelven `False` silenciosamente sin afectar al motor.
