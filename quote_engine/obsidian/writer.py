"""Escritor de notas Markdown para Obsidian.

REGLAS DE SEGURIDAD:
- No se guardan secretos en las notas.
- No se destruyen notas existentes (solo se crean nuevas o se añade contenido).
- No se modifica documentación crítica sin backup.
- No se escribe si el vault no está configurado.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from .templates import (
    template_approved_learning,
    template_error_case,
    template_import_summary,
    template_pending_learning,
    template_quote_summary,
)

logger = logging.getLogger(__name__)

# Estructura de directorios del vault Obsidian
VAULT_STRUCTURE = {
    "root": "",
    "eon_map": "EON",
    "reglas_validadas": "EON/Reglas_Validadas",
    "plantillas": "EON/Plantillas",
    "procedimientos": "EON/Procedimientos",
    "aprendizajes_pendientes": "EON/Aprendizajes_Pendientes",
    "aprendizajes_aprobados": "EON/Aprendizajes_Aprobados",
    "errores_corregidos": "EON/Errores_Corregidos",
    "presupuestos_casos": "EON/Presupuestos_Casos",
    "tests": "EON/Tests",
    "productos": "Productos",
    "holded": "Holded",
}


def get_vault_path() -> Optional[Path]:
    """Obtiene la ruta del vault Obsidian desde variables de entorno."""
    vault = os.getenv("OBSIDIAN_VAULT")
    if not vault:
        return None
    p = Path(vault)
    if not p.exists():
        logger.warning(f"Vault Obsidian no encontrado: {p}")
        return None
    return p


def _ensure_dir(vault: Path, subdir: str) -> Path:
    """Crea el directorio si no existe."""
    d = vault / subdir
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_filename(name: str) -> str:
    """Genera un nombre de archivo seguro."""
    safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in name)
    return safe.strip().replace(" ", "_")[:80]


def _write_note(path: Path, content: str, overwrite: bool = False) -> bool:
    """Escribe una nota. Si ya existe y overwrite=False, añade sufijo numérico."""
    if path.exists() and not overwrite:
        # Nunca sobreescribir sin confirmación — añadir sufijo
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 1
        while path.exists():
            path = parent / f"{stem}_{counter}{suffix}"
            counter += 1

    try:
        path.write_text(content, encoding="utf-8")
        logger.info(f"Nota escrita: {path}")
        return True
    except Exception as exc:
        logger.error(f"Error al escribir nota {path}: {exc}")
        return False


def write_pending_learning_note(item) -> bool:
    """Escribe nota de aprendizaje pendiente."""
    vault = get_vault_path()
    if vault is None:
        logger.debug("Vault no configurado, saltando nota de aprendizaje pendiente")
        return False

    folder = _ensure_dir(vault, VAULT_STRUCTURE["aprendizajes_pendientes"])
    filename = f"PEND_{item.id:04d}_{_safe_filename(item.title)}.md"

    content = template_pending_learning(
        learning_id=item.id,
        learning_type=item.type,
        title=item.title,
        description=item.description,
        proposed_rule=item.proposed_rule,
    )

    return _write_note(folder / filename, content, overwrite=False)


def write_approved_learning_note(item) -> bool:
    """Escribe nota de aprendizaje aprobado."""
    vault = get_vault_path()
    if vault is None:
        logger.debug("Vault no configurado, saltando nota de aprendizaje aprobado")
        return False

    folder = _ensure_dir(vault, VAULT_STRUCTURE["aprendizajes_aprobados"])
    filename = f"APRO_{item.id:04d}_{_safe_filename(item.title)}.md"

    approved_at = None
    if item.approved_at:
        approved_at = item.approved_at.strftime("%Y-%m-%d %H:%M") if hasattr(item.approved_at, "strftime") else str(item.approved_at)

    content = template_approved_learning(
        learning_id=item.id,
        learning_type=item.type,
        title=item.title,
        description=item.description,
        proposed_rule=item.proposed_rule,
        approved_by=item.approved_by or "Desconocido",
        approved_at=approved_at,
    )

    return _write_note(folder / filename, content, overwrite=True)


def write_quote_summary_note(
    reference: str,
    client_name: Optional[str] = None,
    total_with_igic: Optional[float] = None,
    benefit: Optional[float] = None,
    margin_percent: Optional[float] = None,
    warnings: Optional[list] = None,
    status: str = "draft",
    quote_type: Optional[str] = None,
) -> bool:
    """Escribe resumen de presupuesto en Obsidian."""
    vault = get_vault_path()
    if vault is None:
        return False

    folder = _ensure_dir(vault, VAULT_STRUCTURE["presupuestos_casos"])
    filename = f"{reference}.md"

    content = template_quote_summary(
        reference=reference,
        client_name=client_name,
        total_with_igic=total_with_igic,
        benefit=benefit,
        margin_percent=margin_percent,
        warnings=warnings or [],
        status=status,
        quote_type=quote_type,
    )

    return _write_note(folder / filename, content, overwrite=True)


def write_import_summary_note(
    source_file: str,
    suppliers: list[str],
    products_count: int,
    prices_count: int,
    warnings_count: int,
    errors_count: int,
) -> bool:
    """Escribe resumen de importación en Obsidian."""
    vault = get_vault_path()
    if vault is None:
        return False

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = _ensure_dir(vault, VAULT_STRUCTURE["procedimientos"])
    filename = f"Import_{timestamp}.md"

    content = template_import_summary(
        source_file=source_file,
        suppliers=suppliers,
        products_count=products_count,
        prices_count=prices_count,
        warnings_count=warnings_count,
        errors_count=errors_count,
    )

    return _write_note(folder / filename, content, overwrite=False)


def ensure_vault_structure() -> bool:
    """Crea la estructura base del vault si no existe."""
    vault = get_vault_path()
    if vault is None:
        return False

    for key, subdir in VAULT_STRUCTURE.items():
        if subdir:
            _ensure_dir(vault, subdir)

    # Crear índice si no existe
    index_path = vault / "00_INDICE_GENERAL_EON.md"
    if not index_path.exists():
        content = _INDICE_CONTENT
        _write_note(index_path, content, overwrite=False)

    # Crear mapa EON si no existe
    eon_map_path = vault / "EON" / "00_Mapa_EON.md"
    if not eon_map_path.exists():
        _write_note(eon_map_path, _EON_MAP_CONTENT, overwrite=False)

    logger.info(f"Estructura del vault verificada: {vault}")
    return True


_INDICE_CONTENT = """# Índice General EON — Index Clima

Sistema de conocimiento y memoria de EON.

## Secciones

- [[EON/00_Mapa_EON|Mapa EON]]
- [[EON/Reglas_Validadas|Reglas Validadas]]
- [[EON/Aprendizajes_Pendientes|Aprendizajes Pendientes]]
- [[EON/Aprendizajes_Aprobados|Aprendizajes Aprobados]]
- [[EON/Errores_Corregidos|Errores Corregidos]]
- [[EON/Presupuestos_Casos|Presupuestos y Casos]]
- [[Productos/Politica_Precios|Política de Precios]]
- [[Productos/Proveedores|Proveedores]]

---
*Este archivo es generado por EON. No editar manualmente los bloques automáticos.*
"""

_EON_MAP_CONTENT = """# Mapa EON

EON es el asistente de presupuestos de Index Clima.

## Reglas fundamentales

1. La IA no calcula importes manualmente
2. Todo cálculo pasa por `index_quote_engine`
3. No inventar precios, cantidades ni datos fiscales
4. Si falta dato crítico → preguntar
5. Si falta dato no crítico → continuar y marcar PENDIENTE
6. Todo aprendizaje crítico queda pendiente hasta aprobación de Samuel

## Módulos principales

- `quote_engine.calculator` — Motor de cálculo (CORE)
- `quote_engine.catalog` — Catálogo de productos y precios
- `quote_engine.pricing` — Reglas de selección de proveedor
- `quote_engine.learning` — Correcciones y aprendizajes
- `quote_engine.db` — Base de datos PostgreSQL

## Comandos principales

```powershell
# Arrancar BD
.\\scripts\\db_up.ps1

# Importar Excel
python -m quote_engine.importers.excel_products_importer --file data/raw/archivo.xlsx

# API
python -m uvicorn quote_api.main:app --reload

# Tests
python -m pytest
```
"""
