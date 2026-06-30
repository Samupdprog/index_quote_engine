"""Plantillas Markdown para notas Obsidian."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Any


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def template_pending_learning(
    learning_id: int,
    learning_type: str,
    title: str,
    description: Optional[str],
    proposed_rule: Optional[str],
    source_quote: Optional[str] = None,
) -> str:
    """Genera nota Markdown para un aprendizaje pendiente."""
    lines = [
        f"# Aprendizaje Pendiente — {title}",
        "",
        f"**Estado:** #pendiente",
        f"**Tipo:** #{learning_type}",
        f"**ID:** {learning_id}",
        f"**Fecha:** {_now()}",
    ]
    if source_quote:
        lines.append(f"**Origen:** [[Presupuestos_Casos/{source_quote}]]")
    lines += [
        "",
        "## Descripción",
        "",
        description or "(sin descripción)",
        "",
        "## Regla propuesta",
        "",
        proposed_rule or "(sin regla propuesta)",
        "",
        "## Estado de revisión",
        "",
        "- [ ] Revisado por Samuel",
        "- [ ] Aprobado → ejecutar `python -m index-quote learning approve <id>`",
        "- [ ] Rechazado",
        "",
        "---",
        f"*Generado automáticamente por EON el {_now()}. No editar manualmente.*",
    ]
    return "\n".join(lines)


def template_approved_learning(
    learning_id: int,
    learning_type: str,
    title: str,
    description: Optional[str],
    proposed_rule: Optional[str],
    approved_by: str,
    approved_at: Optional[str] = None,
) -> str:
    """Genera nota Markdown para un aprendizaje aprobado."""
    lines = [
        f"# Aprendizaje Aprobado — {title}",
        "",
        f"**Estado:** #aprobado",
        f"**Tipo:** #{learning_type}",
        f"**ID:** {learning_id}",
        f"**Aprobado por:** {approved_by}",
        f"**Aprobado el:** {approved_at or _now()}",
        "",
        "## Descripción",
        "",
        description or "(sin descripción)",
        "",
        "## Regla aprobada",
        "",
        proposed_rule or "(sin regla)",
        "",
        "## Aplicación",
        "",
        "- Revisar si requiere actualización de código",
        "- Añadir test de regresión si aplica",
        "- Actualizar `Productos/Politica_Precios.md` si afecta a precios",
        "",
        "---",
        f"*Aprobado por {approved_by}. Generado por EON el {_now()}.*",
    ]
    return "\n".join(lines)


def template_quote_summary(
    reference: str,
    client_name: Optional[str],
    total_with_igic: Optional[float],
    benefit: Optional[float],
    margin_percent: Optional[float],
    warnings: list[str],
    status: str = "draft",
    quote_type: Optional[str] = None,
) -> str:
    """Genera nota Markdown de resumen de presupuesto."""
    total_str = f"{total_with_igic:.2f} €" if total_with_igic is not None else "PENDIENTE"
    benefit_str = f"{benefit:.2f} €" if benefit is not None else "PENDIENTE"
    margin_str = f"{margin_percent:.1f}%" if margin_percent is not None else "PENDIENTE"

    lines = [
        f"# Presupuesto {reference}",
        "",
        f"**Cliente:** {client_name or 'Sin cliente'}",
        f"**Estado:** #{status}",
        f"**Tipo:** {quote_type or 'Sin tipo'}",
        f"**Fecha:** {_now()}",
        "",
        "## Totales",
        "",
        f"| Concepto | Valor |",
        f"|---|---|",
        f"| Total con IGIC | **{total_str}** |",
        f"| Beneficio | {benefit_str} |",
        f"| Margen | {margin_str} |",
        "",
    ]

    if warnings:
        lines += [
            "## Avisos",
            "",
        ]
        for w in warnings:
            lines.append(f"- ⚠ {w}")
        lines.append("")

    lines += [
        "## Enlace",
        "",
        f"Ver detalle: `index-quote show {reference}`",
        "",
        "---",
        f"*Generado por EON el {_now()}.*",
    ]
    return "\n".join(lines)


def template_error_case(
    title: str,
    description: Optional[str],
    cause: Optional[str],
    solution: Optional[str],
    related_quote: Optional[str] = None,
) -> str:
    """Genera nota Markdown de error documentado."""
    lines = [
        f"# Error Documentado — {title}",
        "",
        f"**Estado:** #abierto",
        f"**Fecha:** {_now()}",
    ]
    if related_quote:
        lines.append(f"**Presupuesto:** [[Presupuestos_Casos/{related_quote}]]")
    lines += [
        "",
        "## Descripción",
        "",
        description or "(sin descripción)",
        "",
        "## Causa",
        "",
        cause or "(sin causa identificada)",
        "",
        "## Solución",
        "",
        solution or "(pendiente de resolución)",
        "",
        "---",
        f"*Documentado por EON el {_now()}.*",
    ]
    return "\n".join(lines)


def template_import_summary(
    source_file: str,
    suppliers: list[str],
    products_count: int,
    prices_count: int,
    warnings_count: int,
    errors_count: int,
) -> str:
    """Genera nota Markdown de resumen de importación."""
    lines = [
        f"# Importación de Productos — {_now()}",
        "",
        f"**Archivo:** `{source_file}`",
        "",
        "## Resumen",
        "",
        f"| Concepto | Valor |",
        f"|---|---|",
        f"| Proveedores | {len(suppliers)} |",
        f"| Productos | {products_count} |",
        f"| Precios | {prices_count} |",
        f"| Warnings | {warnings_count} |",
        f"| Errores | {errors_count} |",
        "",
    ]

    if suppliers:
        lines += ["## Proveedores importados", ""]
        for s in suppliers:
            lines.append(f"- {s}")
        lines.append("")

    lines += [
        "---",
        f"*Importado por EON el {_now()}.*",
    ]
    return "\n".join(lines)
