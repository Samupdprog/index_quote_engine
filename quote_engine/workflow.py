"""Flujo de trabajo completo para presupuestos Index Clima.

Convierte un JSON de entrada en un presupuesto guardado, calculado,
con informe interno HTML y payload Holded exportado.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import storage as _storage
from .calculator import calculate_quote
from .exporters.holded import export_holded_payload
from .exporters.internal_report import build_internal_report, build_internal_report_html
from .models import QuoteSnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok(quote_id: str, message: str, **kwargs: Any) -> dict:
    r: dict[str, Any] = {"ok": True, "action": "quote_workflow", "quote_id": quote_id, "message": message}
    r.update(kwargs)
    return r


def _err(error: str, quote_id: str | None = None) -> dict:
    r: dict[str, Any] = {"ok": False, "action": "quote_workflow", "error": error}
    if quote_id:
        r["quote_id"] = quote_id
    return r


def _default_report_path(quote_id: str) -> Path:
    return Path("data/reports") / f"{quote_id}-report.html"


def _default_holded_path(quote_id: str) -> Path:
    return Path("data/exports") / f"{quote_id}-holded.json"


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def run_quote_workflow(
    input_path: str,
    quote_id: str | None = None,
    created_by: str = "EON",
    source: str = "workflow",
    status: str = "draft",
    project_type: str | None = None,
    tags: list[str] | None = None,
    generate_report: bool = True,
    export_holded: bool = True,
    report_output_path: str | None = None,
    holded_output_path: str | None = None,
) -> dict:
    """Ejecuta el flujo completo sobre un JSON de entrada.

    Pasos:
    1. Lee y valida el JSON de entrada.
    2. Guarda como presupuesto local (aplica reglas documentales).
    3. Calcula totales.
    4. Genera resumen con semáforo y recomendaciones.
    5. Genera informe HTML (si generate_report=True).
    6. Exporta payload Holded (si export_holded=True).
    7. Devuelve resultado completo.
    """
    steps: dict[str, bool] = {
        "loaded_input": False,
        "saved_quote": False,
        "calculated": False,
        "summary_generated": False,
        "report_generated": False,
        "holded_payload_exported": False,
    }

    # -- 1. Leer y parsear el JSON de entrada --
    p = Path(input_path)
    if not p.exists():
        return _err(f"Archivo no encontrado: '{input_path}'")

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return _err(f"JSON inválido en '{input_path}': {exc}")

    try:
        if "snapshot" in raw and isinstance(raw["snapshot"], dict):
            snap = QuoteSnapshot.model_validate(raw["snapshot"])
        else:
            snap = QuoteSnapshot.model_validate(raw)
    except Exception as exc:
        return _err(f"Error al validar el presupuesto: {exc}")

    steps["loaded_input"] = True

    # -- 2. Guardar (storage ya aplica ensure_required_document_sections) --
    try:
        saved_id = _storage.save_quote(snap, quote_id=quote_id, created_by=created_by, source=source)
    except ValueError as exc:
        return _err(f"Error al guardar: {exc}")

    meta_updates: dict[str, Any] = {"status": status}
    if project_type is not None:
        meta_updates["project_type"] = project_type
    if tags is not None:
        meta_updates["tags"] = tags

    _storage.update_quote_metadata(saved_id, meta_updates)
    steps["saved_quote"] = True

    # -- 3. Calcular --
    try:
        doc = _storage.load_quote(saved_id)
        saved_snap = QuoteSnapshot.model_validate(doc["snapshot"])
        calc = calculate_quote(saved_snap)
    except Exception as exc:
        return _err(f"Error al calcular: {exc}", quote_id=saved_id)

    steps["calculated"] = True

    # -- 4. Generar resumen --
    try:
        meta = doc.get("metadata", {})
        report = build_internal_report(saved_snap, metadata=meta)
        totals = report["totals"]
        rs = report["report_status"]
        lines = report["lines"]
        suppliers = sorted({ln["supplier"] for ln in lines if ln.get("supplier")})
        summary = {
            "id": saved_id,
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
    except Exception as exc:
        return _err(f"Error al generar resumen: {exc}", quote_id=saved_id)

    steps["summary_generated"] = True

    # -- 5. Informe HTML --
    actual_report_path: str | None = None
    if generate_report:
        try:
            out_report = Path(report_output_path) if report_output_path else _default_report_path(saved_id)
            out_report.parent.mkdir(parents=True, exist_ok=True)
            html = build_internal_report_html(saved_snap, metadata=meta)
            out_report.write_text(html, encoding="utf-8")
            actual_report_path = str(out_report)
            steps["report_generated"] = True
        except Exception as exc:
            # No interrumpir el workflow por un error de informe
            actual_report_path = None

    # -- 6. Payload Holded --
    actual_holded_path: str | None = None
    if export_holded:
        try:
            out_holded = Path(holded_output_path) if holded_output_path else _default_holded_path(saved_id)
            out_holded.parent.mkdir(parents=True, exist_ok=True)
            payload = export_holded_payload(saved_snap, calc)
            out_holded.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            actual_holded_path = str(out_holded)
            steps["holded_payload_exported"] = True
        except Exception as exc:
            actual_holded_path = None

    return _ok(
        saved_id,
        "Flujo completado correctamente.",
        steps=steps,
        summary=summary,
        report_path=actual_report_path,
        holded_path=actual_holded_path,
        warnings=report["warnings"],
        problems=report["problems"],
        review_recommendations=report["review_recommendations"],
    )
