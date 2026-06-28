"""Herramientas seguras para EON — fachada sobre el motor de presupuestos.

EON no debe leer/escribir archivos JSON directamente.
Todo acceso al sistema pasa por estas funciones.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import storage as _storage
from .calculator import calculate_quote
from .commands import apply_commands as _apply_commands
from .document_rules import ensure_required_document_sections
from .exporters.holded import export_holded_payload
from .exporters.internal_report import build_internal_report, build_internal_report_html
from .models import QuoteSnapshot
from .search import search_quotes
from .validators import CommandError


# ---------------------------------------------------------------------------
# Helpers de respuesta uniforme
# ---------------------------------------------------------------------------

def _ok(action: str, quote_id: str | None = None, message: str = "", **kwargs: Any) -> dict:
    r: dict[str, Any] = {"ok": True, "action": action}
    if quote_id is not None:
        r["quote_id"] = quote_id
    if message:
        r["message"] = message
    r.update(kwargs)
    return r


def _err(action: str, error: str, quote_id: str | None = None) -> dict:
    r: dict[str, Any] = {"ok": False, "action": action, "error": error}
    if quote_id is not None:
        r["quote_id"] = quote_id
    return r


# ---------------------------------------------------------------------------
# Descripción de herramientas disponibles
# ---------------------------------------------------------------------------

_TOOLS: list[dict] = [
    {
        "name": "eon_search_quotes",
        "description": "Busca presupuestos guardados aplicando filtros opcionales.",
        "params": ["query", "client_name", "supplier", "status", "project_type", "tag",
                   "min_profit", "max_profit", "min_total", "max_total",
                   "has_warnings", "has_problems", "limit", "sort_by", "descending"],
    },
    {
        "name": "eon_get_quote",
        "description": "Carga un presupuesto guardado por su ID.",
        "params": ["quote_id"],
    },
    {
        "name": "eon_summarize_quote",
        "description": "Genera un resumen legible del presupuesto con semáforo y recomendaciones.",
        "params": ["quote_id"],
    },
    {
        "name": "eon_calculate_quote",
        "description": "Calcula totales, líneas e IGIC de un presupuesto guardado.",
        "params": ["quote_id"],
    },
    {
        "name": "eon_duplicate_quote",
        "description": "Crea una copia de un presupuesto con nuevo ID.",
        "params": ["quote_id", "new_quote_id (opcional)", "created_by"],
    },
    {
        "name": "eon_apply_commands",
        "description": (
            "Aplica una lista de comandos a un presupuesto. "
            "Por defecto guarda como copia nueva (save_mode='copy'). "
            "Otros modos: 'overwrite' (sobreescribe original), 'dry_run' (no guarda)."
        ),
        "params": ["quote_id", "commands", "save_mode", "new_quote_id (opcional)", "created_by"],
    },
    {
        "name": "eon_generate_internal_report",
        "description": "Genera el informe interno dict o HTML de un presupuesto.",
        "params": ["quote_id", "html (bool)", "output_path (opcional)"],
    },
    {
        "name": "eon_export_holded_payload",
        "description": "Genera el payload JSON compatible con Holded (sin enviarlo).",
        "params": ["quote_id", "output_path (opcional)"],
    },
    {
        "name": "eon_archive_quote",
        "description": "Archiva un presupuesto (cambia estado a 'archived', no borra).",
        "params": ["quote_id"],
    },
]


def list_eon_tools() -> list[dict]:
    """Devuelve la lista de herramientas disponibles para EON."""
    return _TOOLS


# ---------------------------------------------------------------------------
# Helper: construir resumen desde report
# ---------------------------------------------------------------------------

def _build_summary_from_report(meta: dict, report: dict) -> dict:
    totals = report["totals"]
    lines = report["lines"]
    suppliers = sorted({ln["supplier"] for ln in lines if ln.get("supplier")})
    rs = report["report_status"]

    return {
        "id": meta.get("id"),
        "client_name": report["header"].get("client_name"),
        "status": meta.get("status"),
        "project_type": meta.get("project_type"),
        "tags": meta.get("tags", []),
        "line_count": len(lines),
        "suppliers": suppliers,
        "cost_total": totals["cost_subtotal"],
        "sale_total": totals["sale_subtotal"],
        "final_total": totals["final_total"],
        "gross_profit": totals["gross_profit"],
        "gross_profit_percent": totals["gross_profit_percent"],
        "warnings_count": len(report["warnings"]),
        "problems_count": len(report["problems"]),
        "report_status": rs["status"],
        "report_label": rs["label"],
        "human_summary": report["human_summary"],
        "review_recommendations": report["review_recommendations"],
    }


# ---------------------------------------------------------------------------
# Herramientas
# ---------------------------------------------------------------------------

def eon_search_quotes(filters: dict | None = None) -> dict:
    """Busca presupuestos con filtros opcionales."""
    filters = filters or {}
    allowed = {
        "query", "client_name", "supplier", "status", "project_type", "tag",
        "min_profit", "max_profit", "min_total", "max_total",
        "has_warnings", "has_problems", "limit", "sort_by", "descending",
    }
    clean = {k: v for k, v in filters.items() if k in allowed}
    try:
        results = search_quotes(**clean)
        return _ok(
            "search_quotes",
            message=f"{len(results)} presupuesto{'s' if len(results) != 1 else ''} encontrado{'s' if len(results) != 1 else ''}.",
            data={"results": results, "total": len(results)},
        )
    except Exception as exc:
        return _err("search_quotes", str(exc))


def eon_get_quote(quote_id: str) -> dict:
    """Carga un presupuesto guardado por ID."""
    try:
        doc = _storage.load_quote(quote_id)
    except FileNotFoundError:
        return _err("get_quote", f"Presupuesto '{quote_id}' no encontrado.", quote_id=quote_id)
    except ValueError as exc:
        return _err("get_quote", str(exc), quote_id=quote_id)

    return _ok(
        "get_quote",
        quote_id=quote_id,
        message="Presupuesto cargado correctamente.",
        data={"metadata": doc.get("metadata", {}), "snapshot": doc.get("snapshot", {})},
    )


def eon_summarize_quote(quote_id: str) -> dict:
    """Genera un resumen legible con semáforo y recomendaciones."""
    try:
        doc = _storage.load_quote(quote_id)
    except FileNotFoundError:
        return _err("summarize_quote", f"Presupuesto '{quote_id}' no encontrado.", quote_id=quote_id)
    except ValueError as exc:
        return _err("summarize_quote", str(exc), quote_id=quote_id)

    try:
        snap = QuoteSnapshot.model_validate(doc["snapshot"])
        meta = doc.get("metadata", {})
        report = build_internal_report(snap, metadata=meta)
        summary = _build_summary_from_report(meta, report)
    except Exception as exc:
        return _err("summarize_quote", f"Error al generar resumen: {exc}", quote_id=quote_id)

    return _ok(
        "summarize_quote",
        quote_id=quote_id,
        message="Resumen generado correctamente.",
        data=summary,
    )


def eon_calculate_quote(quote_id: str) -> dict:
    """Calcula totales, líneas e IGIC de un presupuesto guardado."""
    try:
        doc = _storage.load_quote(quote_id)
    except FileNotFoundError:
        return _err("calculate_quote", f"Presupuesto '{quote_id}' no encontrado.", quote_id=quote_id)
    except ValueError as exc:
        return _err("calculate_quote", str(exc), quote_id=quote_id)

    try:
        snap = QuoteSnapshot.model_validate(doc["snapshot"])
        calc = calculate_quote(snap)
    except Exception as exc:
        return _err("calculate_quote", f"Error al calcular: {exc}", quote_id=quote_id)

    return _ok(
        "calculate_quote",
        quote_id=quote_id,
        message="Cálculo completado.",
        data=calc.model_dump(),
    )


def eon_duplicate_quote(
    quote_id: str,
    new_quote_id: str | None = None,
    created_by: str = "EON",
) -> dict:
    """Crea una copia de un presupuesto con nuevo ID."""
    try:
        result_id = _storage.duplicate_quote(quote_id, new_quote_id=new_quote_id)
        _storage.update_quote_metadata(result_id, {"created_by": created_by})
    except FileNotFoundError:
        return _err("duplicate_quote", f"Presupuesto '{quote_id}' no encontrado.", quote_id=quote_id)
    except ValueError as exc:
        return _err("duplicate_quote", str(exc), quote_id=quote_id)

    return _ok(
        "duplicate_quote",
        quote_id=quote_id,
        result_quote_id=result_id,
        message=f"Presupuesto duplicado como '{result_id}'.",
        data={"result_quote_id": result_id},
    )


def eon_apply_commands(
    quote_id: str,
    commands: list[dict],
    save_mode: str = "copy",
    new_quote_id: str | None = None,
    created_by: str = "EON",
) -> dict:
    """Aplica comandos a un presupuesto. Modos: copy (default), overwrite, dry_run."""
    if save_mode not in ("copy", "overwrite", "dry_run"):
        return _err(
            "apply_commands",
            f"save_mode inválido: '{save_mode}'. Opciones: copy, overwrite, dry_run.",
            quote_id=quote_id,
        )

    try:
        doc = _storage.load_quote(quote_id)
    except FileNotFoundError:
        return _err("apply_commands", f"Presupuesto '{quote_id}' no encontrado.", quote_id=quote_id)
    except ValueError as exc:
        return _err("apply_commands", str(exc), quote_id=quote_id)

    try:
        snap = QuoteSnapshot.model_validate(doc["snapshot"])
        new_snap = _apply_commands(snap, commands)
        new_snap = ensure_required_document_sections(new_snap)
        calc = calculate_quote(new_snap)
    except CommandError as exc:
        return _err("apply_commands", f"Comando inválido: {exc}", quote_id=quote_id)
    except Exception as exc:
        return _err("apply_commands", f"Error al aplicar comandos: {exc}", quote_id=quote_id)

    if save_mode == "dry_run":
        return _ok(
            "apply_commands",
            quote_id=quote_id,
            result_quote_id=None,
            save_mode=save_mode,
            message="Comandos aplicados (dry_run — no guardado).",
            data={"summary": calc.totals.model_dump(), "warnings": calc.warnings},
        )

    original_meta = doc.get("metadata", {})
    try:
        if save_mode == "copy":
            result_id = _storage.save_quote(
                new_snap,
                quote_id=new_quote_id,
                created_by=created_by,
                source="eon",
            )
            _storage.update_quote_metadata(result_id, {
                "project_type": original_meta.get("project_type"),
                "tags": original_meta.get("tags", []),
                "status": original_meta.get("status", "draft"),
            })
        else:  # overwrite
            result_id = quote_id
            _storage.save_quote(new_snap, quote_id=quote_id, source="eon")
    except Exception as exc:
        return _err("apply_commands", f"Error al guardar: {exc}", quote_id=quote_id)

    return _ok(
        "apply_commands",
        quote_id=quote_id,
        result_quote_id=result_id,
        save_mode=save_mode,
        message=f"Comandos aplicados y guardados en '{result_id}'.",
        data={"summary": calc.totals.model_dump(), "warnings": calc.warnings},
    )


def eon_generate_internal_report(
    quote_id: str,
    html: bool = False,
    output_path: str | None = None,
) -> dict:
    """Genera el informe interno (dict o HTML) de un presupuesto."""
    try:
        doc = _storage.load_quote(quote_id)
    except FileNotFoundError:
        return _err("generate_internal_report", f"Presupuesto '{quote_id}' no encontrado.", quote_id=quote_id)
    except ValueError as exc:
        return _err("generate_internal_report", str(exc), quote_id=quote_id)

    try:
        snap = QuoteSnapshot.model_validate(doc["snapshot"])
        meta = doc.get("metadata", {})

        if html:
            content = build_internal_report_html(snap, metadata=meta)
            if output_path:
                p = Path(output_path)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
                return _ok(
                    "generate_internal_report",
                    quote_id=quote_id,
                    message=f"Informe HTML guardado en '{output_path}'.",
                    data={"output_path": str(p), "html": content},
                )
            return _ok(
                "generate_internal_report",
                quote_id=quote_id,
                message="Informe HTML generado.",
                data={"html": content},
            )
        else:
            report = build_internal_report(snap, metadata=meta)
            return _ok(
                "generate_internal_report",
                quote_id=quote_id,
                message="Informe interno generado.",
                data=report,
            )
    except Exception as exc:
        return _err("generate_internal_report", f"Error al generar informe: {exc}", quote_id=quote_id)


def eon_export_holded_payload(
    quote_id: str,
    output_path: str | None = None,
) -> dict:
    """Genera el payload JSON compatible con Holded (sin enviarlo)."""
    try:
        doc = _storage.load_quote(quote_id)
    except FileNotFoundError:
        return _err("export_holded_payload", f"Presupuesto '{quote_id}' no encontrado.", quote_id=quote_id)
    except ValueError as exc:
        return _err("export_holded_payload", str(exc), quote_id=quote_id)

    try:
        snap = QuoteSnapshot.model_validate(doc["snapshot"])
        calc = calculate_quote(snap)
        payload = export_holded_payload(snap, calc)
    except Exception as exc:
        return _err("export_holded_payload", f"Error al exportar: {exc}", quote_id=quote_id)

    if output_path:
        try:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            return _err("export_holded_payload", f"Error al escribir archivo: {exc}", quote_id=quote_id)
        return _ok(
            "export_holded_payload",
            quote_id=quote_id,
            message=f"Payload Holded guardado en '{output_path}'.",
            data={"payload": payload, "output_path": output_path},
        )

    return _ok(
        "export_holded_payload",
        quote_id=quote_id,
        message="Payload Holded generado.",
        data={"payload": payload},
    )


def eon_archive_quote(quote_id: str) -> dict:
    """Archiva un presupuesto (cambia estado a 'archived', no borra)."""
    try:
        doc = _storage.archive_quote(quote_id)
    except FileNotFoundError:
        return _err("archive_quote", f"Presupuesto '{quote_id}' no encontrado.", quote_id=quote_id)
    except ValueError as exc:
        return _err("archive_quote", str(exc), quote_id=quote_id)

    return _ok(
        "archive_quote",
        quote_id=quote_id,
        message=f"Presupuesto '{quote_id}' archivado correctamente.",
        data={"status": doc["metadata"]["status"]},
    )
