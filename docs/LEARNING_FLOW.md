# LEARNING_FLOW.md — Flujo de correcciones y aprendizaje

---

## Principio fundamental

**Los aprendizajes NUNCA se aprueban automáticamente.** Solo Samuel puede aprobarlos.

---

## Flujo completo

```
1. EON genera presupuesto
       ↓
2. Samuel revisa y corrige algo
       ↓
3. Se registra la corrección (POST /learning/corrections)
       ↓
4. El sistema propone un aprendizaje → status: "pending"
       ↓
5. Samuel ve los pendientes (GET /learning/pending)
       ↓
6. Samuel decide:
   - Aprobar (POST /learning/{id}/approve?approved_by=Samuel)
   - Rechazar (POST /learning/{id}/reject)
       ↓
7. Si aprobado:
   - status → "approved"
   - Se genera nota en Obsidian (si vault configurado)
   - Queda trazado en DB
```

---

## Tipos de aprendizaje

| Tipo | Descripción |
|---|---|
| `pricing_rule` | Regla de margen o precio |
| `transport_rule` | Regla de transporte/desplazamiento |
| `labor_rule` | Regla de mano de obra |
| `material_rule` | Regla de material o pequeño material |
| `exclusion_rule` | Qué debe excluirse en ciertos casos |
| `supplier_preference` | Preferencia de proveedor |
| `template_text` | Texto de plantilla (condiciones, exclusiones) |
| `error_pattern` | Patrón de error recurrente |
| `client_exception` | Excepción específica de cliente |

---

## Ejemplo real

Samuel cambia el transporte de 30 €/día a 15 €/día porque la obra está cerca.

**Corrección registrada:**
```json
{
  "quote_reference": "PRE-2026-0001",
  "field_path": "lines[travel].sale_value",
  "old_value": "30.0",
  "new_value": "15.0",
  "correction_reason": "Obra en radio de 5km",
  "created_by": "Samuel"
}
```

**Aprendizaje propuesto (pendiente):**
```json
{
  "type": "transport_rule",
  "title": "Corrección en lines[travel].sale_value (30.0 → 15.0) — PRE-2026-0001",
  "description": "Originado por corrección #42 en PRE-2026-0001.",
  "proposed_rule": "Motivo: Obra en radio de 5km. Campo corregido de 30.0 a 15.0. Revisar si esta corrección debe convertirse en regla general.",
  "status": "pending"
}
```

**Si Samuel aprueba:**
- La nota aparece en Obsidian en `EON/Aprendizajes_Aprobados/`
- El registro queda en `learning_items` con `status=approved`
- Se puede usar como referencia para futuros presupuestos

---

## Comandos

```powershell
# Registrar corrección
$body = @{
    quote_reference = "PRE-2026-0001"
    field_path = "lines[0].transport"
    old_value = "30"
    new_value = "15"
    correction_reason = "Obra cercana"
} | ConvertTo-Json
Invoke-RestMethod -Method POST http://localhost:8000/learning/corrections -Body $body -ContentType "application/json"

# Ver pendientes
Invoke-RestMethod http://localhost:8000/learning/pending

# Aprobar
Invoke-RestMethod -Method POST "http://localhost:8000/learning/1/approve?approved_by=Samuel"
```

---

## Notas Obsidian generadas

- **Pendiente:** `EON/Aprendizajes_Pendientes/PEND_0001_*.md`
- **Aprobado:** `EON/Aprendizajes_Aprobados/APRO_0001_*.md`
- Las notas no se sobreescriben al crear (se añade sufijo numérico)
- Las aprobadas sí se sobreescriben (para reflejar el estado final)
