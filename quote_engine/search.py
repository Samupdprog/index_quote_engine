"""Búsqueda local de presupuestos sobre archivos JSON en data/quotes/."""

from __future__ import annotations

import json
from typing import Any

from . import storage as _storage
from .exporters.internal_report import build_internal_report
from .models import QuoteSnapshot


# ---------------------------------------------------------------------------
# Construcción de resumen calculado
# ---------------------------------------------------------------------------

def _build_quote_summary(quote_id: str, doc: dict) -> dict:
    """Genera un dict de resumen con totales y semáforo calculados."""
    meta = doc.get("metadata", {})
    snap_data = doc.get("snapshot", {})
    header = snap_data.get("header", {})

    try:
        snap = QuoteSnapshot.model_validate(snap_data)
        report = build_internal_report(snap, metadata=meta)
        totals = report["totals"]
        lines = report["lines"]
        problems = report["problems"]
        warnings_list = report["warnings"]
        rs = report["report_status"]

        suppliers = sorted({ln["supplier"] for ln in lines if ln.get("supplier")})

        return {
            "id": meta.get("id", quote_id),
            "quote_number": header.get("quote_number"),
            "client_name": header.get("client_name"),
            "title": header.get("title"),
            "status": meta.get("status"),
            "project_type": meta.get("project_type"),
            "tags": meta.get("tags", []),
            "created_at": meta.get("created_at"),
            "updated_at": meta.get("updated_at"),
            "line_count": len(lines),
            "supplier_count": len(suppliers),
            "suppliers": suppliers,
            "cost_total": totals["cost_subtotal"],
            "sale_total": totals["sale_subtotal"],
            "final_total": totals["final_total"],
            "gross_profit": totals["gross_profit"],
            "gross_profit_percent": totals["gross_profit_percent"],
            "warnings_count": len(warnings_list),
            "problems_count": len(problems),
            "report_status": rs["label"],
        }
    except Exception:
        # Si el cálculo falla, devuelve datos básicos de metadata
        return {
            "id": meta.get("id", quote_id),
            "quote_number": header.get("quote_number"),
            "client_name": header.get("client_name"),
            "title": header.get("title"),
            "status": meta.get("status"),
            "project_type": meta.get("project_type"),
            "tags": meta.get("tags", []),
            "created_at": meta.get("created_at"),
            "updated_at": meta.get("updated_at"),
            "line_count": len(snap_data.get("lines", [])),
            "supplier_count": 0,
            "suppliers": [],
            "cost_total": 0.0,
            "sale_total": 0.0,
            "final_total": 0.0,
            "gross_profit": 0.0,
            "gross_profit_percent": None,
            "warnings_count": 0,
            "problems_count": 0,
            "report_status": "?",
        }


# ---------------------------------------------------------------------------
# Búsqueda en texto libre
# ---------------------------------------------------------------------------

def _text_search(query: str, doc: dict) -> bool:
    """Retorna True si la query aparece (case-insensitive) en algún campo de texto."""
    q = query.lower()
    meta = doc.get("metadata", {})
    snap_data = doc.get("snapshot", {})
    header = snap_data.get("header", {})

    fields: list[str] = [
        meta.get("id") or "",
        header.get("quote_number") or "",
        header.get("client_name") or "",
        header.get("title") or "",
        header.get("internal_notes") or "",
        meta.get("project_type") or "",
        meta.get("client_reference") or "",
        meta.get("internal_notes") or "",
    ]
    for t in meta.get("tags", []):
        fields.append(t)

    for ln in snap_data.get("lines", []):
        fields.append(ln.get("description") or "")
        fields.append(ln.get("supplier") or "")

    return any(q in f.lower() for f in fields if f)


# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

def quote_matches_filters(
    doc: dict,
    summary: dict,
    *,
    query: str | None = None,
    client_name: str | None = None,
    supplier: str | None = None,
    status: str | None = None,
    project_type: str | None = None,
    tag: str | None = None,
    min_profit: float | None = None,
    max_profit: float | None = None,
    min_total: float | None = None,
    max_total: float | None = None,
    has_warnings: bool | None = None,
    has_problems: bool | None = None,
) -> bool:
    """Retorna True si el presupuesto cumple todos los filtros activos."""
    if query is not None and not _text_search(query, doc):
        return False
    if client_name is not None and client_name.lower() not in (summary["client_name"] or "").lower():
        return False
    if supplier is not None:
        sup_lower = supplier.lower()
        if not any(sup_lower in s.lower() for s in summary["suppliers"]):
            return False
    if status is not None and summary["status"] != status:
        return False
    if project_type is not None and (summary["project_type"] or "").lower() != project_type.lower():
        return False
    if tag is not None:
        tag_lower = tag.lower()
        if not any(tag_lower == t.lower() for t in summary["tags"]):
            return False
    if min_profit is not None and summary["gross_profit"] < min_profit:
        return False
    if max_profit is not None and summary["gross_profit"] > max_profit:
        return False
    if min_total is not None and summary["final_total"] < min_total:
        return False
    if max_total is not None and summary["final_total"] > max_total:
        return False
    if has_warnings is True and summary["warnings_count"] == 0:
        return False
    if has_warnings is False and summary["warnings_count"] > 0:
        return False
    if has_problems is True and summary["problems_count"] == 0:
        return False
    if has_problems is False and summary["problems_count"] > 0:
        return False
    return True


# ---------------------------------------------------------------------------
# Ordenación
# ---------------------------------------------------------------------------

_SORT_FIELDS = frozenset({
    "updated_at", "created_at", "final_total", "gross_profit",
    "gross_profit_percent", "client_name",
})


def _sort_key(summary: dict, field: str) -> Any:
    v = summary.get(field)
    if v is None:
        return "" if field in ("updated_at", "created_at", "client_name") else 0.0
    return v


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def search_quotes(
    query: str | None = None,
    client_name: str | None = None,
    supplier: str | None = None,
    status: str | None = None,
    project_type: str | None = None,
    tag: str | None = None,
    min_profit: float | None = None,
    max_profit: float | None = None,
    min_total: float | None = None,
    max_total: float | None = None,
    has_warnings: bool | None = None,
    has_problems: bool | None = None,
    limit: int | None = None,
    sort_by: str = "updated_at",
    descending: bool = True,
) -> list[dict]:
    """Busca presupuestos locales aplicando filtros y ordenación."""
    quotes_dir = _storage.QUOTES_DIR
    if not quotes_dir.exists():
        return []

    sort_field = sort_by if sort_by in _SORT_FIELDS else "updated_at"
    results: list[dict] = []

    for path in sorted(quotes_dir.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        summary = _build_quote_summary(path.stem, doc)

        if quote_matches_filters(
            doc, summary,
            query=query,
            client_name=client_name,
            supplier=supplier,
            status=status,
            project_type=project_type,
            tag=tag,
            min_profit=min_profit,
            max_profit=max_profit,
            min_total=min_total,
            max_total=max_total,
            has_warnings=has_warnings,
            has_problems=has_problems,
        ):
            results.append(summary)

    results.sort(key=lambda s: _sort_key(s, sort_field), reverse=descending)

    if limit is not None:
        results = results[:limit]

    return results


def find_recent_quotes(limit: int = 10) -> list[dict]:
    """Devuelve los N presupuestos más recientes por updated_at."""
    return search_quotes(sort_by="updated_at", descending=True, limit=limit)


def summarize_search_results(results: list[dict]) -> str:
    """Genera una línea de resumen del número de resultados."""
    n = len(results)
    if n == 0:
        return "No se encontraron presupuestos."
    return f"{n} presupuesto{'s' if n != 1 else ''} encontrado{'s' if n != 1 else ''}."
