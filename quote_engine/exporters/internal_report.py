"""Exportador de informe interno (dict y HTML)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..calculator import calculate_quote
from ..models import CalculatedQuote, QuoteSnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _esc(text: Any) -> str:
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _pct_str(v: float | None) -> str:
    return f"{v:.1f}%" if v is not None else "N/A"


def _build_supplier_summary(lines_data: list[dict]) -> list[dict]:
    acc: dict[str, dict] = {}
    for ln in lines_data:
        key = ln["supplier"] or "(sin proveedor)"
        if key not in acc:
            acc[key] = {"cost_total": 0.0, "sale_total": 0.0, "profit": 0.0, "lines": 0}
        acc[key]["cost_total"] += ln["cost_total"]
        acc[key]["sale_total"] += ln["sale_total_without_tax"]
        acc[key]["profit"] += ln["gross_profit"]
        acc[key]["lines"] += 1

    result = []
    for name, d in acc.items():
        profit_pct = (d["profit"] / d["sale_total"] * 100) if d["sale_total"] else None
        result.append({
            "supplier": name,
            "cost_total": round(d["cost_total"], 2),
            "sale_total": round(d["sale_total"], 2),
            "profit": round(d["profit"], 2),
            "profit_percent": round(profit_pct, 2) if profit_pct is not None else None,
            "line_count": d["lines"],
        })
    return result


def _detect_problems(lines_data: list[dict]) -> list[dict]:
    problems = []
    for ln in lines_data:
        desc = ln["description"] or "(sin descripción)"
        if ln["cost_total"] == 0:
            problems.append({"line": desc, "issue": "coste 0"})
        if ln["gross_profit"] < 0:
            problems.append({"line": desc, "issue": f"beneficio negativo ({ln['gross_profit']:.2f} €)"})
        elif ln["gross_profit_percent"] is not None and 0 < ln["gross_profit_percent"] < 10:
            problems.append({"line": desc, "issue": f"margen bajo ({ln['gross_profit_percent']:.1f}%)"})
        if ln["type"] == "material" and not ln["supplier"]:
            problems.append({"line": desc, "issue": "material sin proveedor"})
        if ln["warnings"]:
            for w in ln["warnings"]:
                problems.append({"line": desc, "issue": f"warning: {w}"})
    return problems


# ---------------------------------------------------------------------------
# API de bajo nivel (compatibilidad existente — reciben snapshot + calculated)
# ---------------------------------------------------------------------------

def export_internal_report_dict(
    snapshot: QuoteSnapshot,
    calculated: CalculatedQuote,
) -> dict:
    """Devuelve el informe interno como dict estructurado."""
    header = snapshot.header
    totals = calculated.totals

    lines_data = []
    for cl in calculated.lines:
        lines_data.append({
            "line_id": cl.line_id,
            "description": cl.description,
            "type": cl.type,
            "quantity": cl.quantity,
            "unit": cl.unit,
            "supplier": cl.supplier,
            "cost_unit": cl.cost_unit,
            "cost_total": cl.cost_total,
            "supplier_gross_total": cl.supplier_gross_total,
            "supplier_saving": cl.supplier_saving,
            "effective_supplier_discount": cl.effective_supplier_discount,
            "sale_unit_without_tax": cl.sale_unit_without_tax,
            "sale_total_without_tax": cl.sale_total_without_tax,
            "tax_rate": cl.tax_rate,
            "tax_amount": cl.tax_amount,
            "client_total": cl.client_total,
            "gross_profit": cl.gross_profit,
            "gross_profit_percent": cl.gross_profit_percent,
            "applied_margin": cl.applied_margin,
            "warnings": cl.warnings,
        })

    return {
        "header": {
            "quote_number": header.quote_number,
            "client_name": header.client_name,
            "title": header.title,
            "date": header.date,
            "global_margin": header.global_margin,
            "tax": header.tax,
            "include_tax": header.include_tax,
        },
        "totals": {
            "cost_subtotal": totals.cost_subtotal,
            "supplier_gross_subtotal": totals.supplier_gross_subtotal,
            "supplier_saving_total": totals.supplier_saving_total,
            "sale_subtotal": totals.sale_subtotal,
            "tax_amount": totals.tax_amount,
            "final_total": totals.final_total,
            "gross_profit": totals.gross_profit,
            "gross_profit_percent": totals.gross_profit_percent,
        },
        "lines": lines_data,
        "warnings": calculated.warnings,
    }


def export_internal_report_html(
    snapshot: QuoteSnapshot,
    calculated: CalculatedQuote,
) -> str:
    """HTML básico del informe interno (compatibilidad existente)."""
    return build_internal_report_html(snapshot, calculated=calculated)


# ---------------------------------------------------------------------------
# API de alto nivel (calculan internamente — solo necesitan snapshot)
# ---------------------------------------------------------------------------

def build_internal_report(
    snapshot: QuoteSnapshot,
    metadata: dict[str, Any] | None = None,
) -> dict:
    """Genera el informe completo calculando internamente.

    Incluye resumen por proveedor, detección de problemas y metadata opcional.
    """
    calculated = calculate_quote(snapshot)
    base = export_internal_report_dict(snapshot, calculated)
    supplier_summary = _build_supplier_summary(base["lines"])
    problems = _detect_problems(base["lines"])

    return {
        "metadata": metadata or {},
        "header": base["header"],
        "totals": base["totals"],
        "supplier_summary": supplier_summary,
        "lines": base["lines"],
        "problems": problems,
        "warnings": base["warnings"],
        "internal_notes": snapshot.header.internal_notes,
    }


def build_internal_report_html(
    snapshot: QuoteSnapshot,
    metadata: dict[str, Any] | None = None,
    calculated: CalculatedQuote | None = None,
) -> str:
    """Genera el informe interno en HTML standalone (sin CDN, sin dependencias)."""
    if calculated is None:
        calculated = calculate_quote(snapshot)

    report = build_internal_report(snapshot, metadata=metadata)
    header = report["header"]
    totals = report["totals"]
    lines = report["lines"]
    supplier_summary = report["supplier_summary"]
    problems = report["problems"]
    meta = report["metadata"]

    # ── Filas de líneas ──────────────────────────────────────────────────
    def _row_class(ln: dict) -> str:
        if ln["gross_profit"] < 0:
            return ' class="row-danger"'
        if ln["cost_total"] == 0:
            return ' class="row-warn"'
        if ln["type"] == "material" and not ln["supplier"]:
            return ' class="row-warn"'
        if ln["gross_profit_percent"] is not None and 0 < ln["gross_profit_percent"] < 10:
            return ' class="row-low"'
        return ""

    line_rows = ""
    for ln in lines:
        lp = _pct_str(ln["gross_profit_percent"])
        cls = _row_class(ln)
        warns = " ⚠" if ln["warnings"] else ""
        line_rows += (
            f"<tr{cls}>"
            f"<td>{_esc(ln['description'])}{warns}</td>"
            f"<td>{_esc(ln['type'])}</td>"
            f"<td>{_esc(ln['supplier'])}</td>"
            f"<td>{ln['quantity']} {_esc(ln['unit'])}</td>"
            f"<td>{ln['cost_unit']:.2f} €</td>"
            f"<td>{ln['cost_total']:.2f} €</td>"
            f"<td>{ln['sale_unit_without_tax']:.2f} €</td>"
            f"<td>{ln['sale_total_without_tax']:.2f} €</td>"
            f"<td>{ln['tax_rate']:.1f}%</td>"
            f"<td>{ln['client_total']:.2f} €</td>"
            f"<td>{ln['gross_profit']:.2f} €</td>"
            f"<td>{lp}</td>"
            f"</tr>\n"
        )

    # ── Resumen por proveedor ────────────────────────────────────────────
    sup_rows = ""
    for s in supplier_summary:
        sup_rows += (
            f"<tr>"
            f"<td>{_esc(s['supplier'])}</td>"
            f"<td>{s['cost_total']:.2f} €</td>"
            f"<td>{s['sale_total']:.2f} €</td>"
            f"<td>{s['profit']:.2f} €</td>"
            f"<td>{_pct_str(s['profit_percent'])}</td>"
            f"<td>{s['line_count']}</td>"
            f"</tr>\n"
        )

    # ── Problemas ────────────────────────────────────────────────────────
    problems_html = ""
    if problems:
        items = "".join(
            f"<li><b>{_esc(p['line'])}</b> — {_esc(p['issue'])}</li>" for p in problems
        )
        problems_html = f'<div class="problems"><h3>⚠ Problemas detectados</h3><ul>{items}</ul></div>'

    # ── Warnings globales ────────────────────────────────────────────────
    warnings_html = ""
    if report["warnings"]:
        items = "".join(f"<li>{_esc(w)}</li>" for w in report["warnings"])
        warnings_html = f'<div class="problems"><h3>Warnings del motor</h3><ul>{items}</ul></div>'

    # ── Notas internas ───────────────────────────────────────────────────
    notes_html = ""
    if report["internal_notes"]:
        notes_html = (
            f'<div class="notes"><h3>Notas internas</h3>'
            f'<p>{_esc(report["internal_notes"])}</p></div>'
        )

    # ── Metadata section ─────────────────────────────────────────────────
    meta_rows = ""
    if meta:
        fields = [
            ("ID", meta.get("id")),
            ("Estado", meta.get("status")),
            ("Creado", meta.get("created_at")),
            ("Actualizado", meta.get("updated_at")),
            ("Tipo proyecto", meta.get("project_type")),
            ("Tags", ", ".join(meta.get("tags", [])) or None),
            ("Autor", meta.get("created_by")),
        ]
        for label, val in fields:
            if val:
                meta_rows += f"<tr><th>{label}</th><td>{_esc(val)}</td></tr>"

    meta_html = ""
    if meta_rows:
        meta_html = f"""
  <table class="meta-table">
    {meta_rows}
  </table>"""

    title = header.get("quote_number") or meta.get("id") or "Presupuesto"
    client = header.get("client_name") or "(sin cliente)"
    pct_total = _pct_str(totals["gross_profit_percent"])

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Informe Interno — {_esc(title)}</title>
  <style>
    body {{ font-family: sans-serif; font-size: 13px; padding: 24px; color: #222; }}
    h1 {{ font-size: 20px; margin-bottom: 4px; }}
    h2 {{ font-size: 15px; margin: 24px 0 8px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }}
    h3 {{ font-size: 13px; margin: 12px 0 6px; }}
    p {{ margin: 4px 0; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 12px; }}
    th, td {{ border: 1px solid #ccc; padding: 5px 8px; text-align: right; }}
    th {{ background: #f0f0f0; text-align: center; font-weight: 600; }}
    td:first-child, td:nth-child(2), td:nth-child(3) {{ text-align: left; }}
    .meta-table th {{ text-align: left; width: 140px; background: #f8f8f8; }}
    .meta-table td {{ text-align: left; }}
    .totals-table {{ width: auto; }}
    .totals-table td {{ font-weight: 600; }}
    .row-danger {{ background: #fde8e8; }}
    .row-warn   {{ background: #fff8e1; }}
    .row-low    {{ background: #fff3cd; }}
    .problems {{ background: #fff3cd; border: 1px solid #f0ad4e; border-radius: 4px;
                  padding: 10px 14px; margin: 12px 0; }}
    .problems ul {{ margin: 4px 0; padding-left: 20px; }}
    .notes {{ background: #f0f4ff; border: 1px solid #b0c4de; border-radius: 4px;
               padding: 10px 14px; margin: 12px 0; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px;
               font-size: 11px; font-weight: 600; background: #e0e0e0; color: #444; }}
    .internal-stamp {{ color: #999; font-size: 11px; float: right; }}
  </style>
</head>
<body>
  <span class="internal-stamp">USO INTERNO — Index Clima</span>
  <h1>Informe Interno — {_esc(title)}</h1>
  <p><b>Cliente:</b> {_esc(client)} &nbsp;|&nbsp; <b>Fecha:</b> {_esc(header.get('date'))} &nbsp;|&nbsp; <b>Título:</b> {_esc(header.get('title'))}</p>
  {meta_html}

  <h2>Totales</h2>
  <table class="totals-table" style="width:auto">
    <tr><td>Coste total</td><td>{totals['cost_subtotal']:.2f} €</td></tr>
    <tr><td>Tarifa bruta proveedor</td><td>{totals['supplier_gross_subtotal']:.2f} €</td></tr>
    <tr><td>Ahorro proveedor</td><td>{totals['supplier_saving_total']:.2f} €</td></tr>
    <tr><td>Venta sin IGIC</td><td>{totals['sale_subtotal']:.2f} €</td></tr>
    <tr><td>IGIC</td><td>{totals['tax_amount']:.2f} €</td></tr>
    <tr><td><b>Total cliente</b></td><td><b>{totals['final_total']:.2f} €</b></td></tr>
    <tr><td>Beneficio bruto</td><td>{totals['gross_profit']:.2f} €</td></tr>
    <tr><td>% Beneficio</td><td>{pct_total}</td></tr>
  </table>

  {problems_html}
  {warnings_html}

  <h2>Resumen por proveedor</h2>
  <table>
    <thead>
      <tr>
        <th>Proveedor</th><th>Coste total</th><th>Venta total</th>
        <th>Beneficio</th><th>% Benef.</th><th>Líneas</th>
      </tr>
    </thead>
    <tbody>
      {sup_rows}
    </tbody>
  </table>

  <h2>Líneas</h2>
  <table>
    <thead>
      <tr>
        <th>Descripción</th><th>Tipo</th><th>Proveedor</th><th>Cantidad</th>
        <th>Coste ud.</th><th>Coste total</th>
        <th>Venta ud.</th><th>Venta total</th>
        <th>IGIC%</th><th>Total cliente</th>
        <th>Beneficio</th><th>% Benef.</th>
      </tr>
    </thead>
    <tbody>
      {line_rows}
    </tbody>
  </table>

  {notes_html}
</body>
</html>"""


def save_internal_report_html(
    snapshot: QuoteSnapshot,
    output_path: str | Path,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Genera el HTML y lo guarda en disco. Devuelve la ruta como string."""
    html = build_internal_report_html(snapshot, metadata=metadata)
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    return str(p)
