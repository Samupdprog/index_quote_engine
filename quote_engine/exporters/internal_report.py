"""Exportador de informe interno (dict y HTML)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..calculator import calculate_quote
from ..models import CalculatedQuote, QuoteSnapshot


# ---------------------------------------------------------------------------
# Helpers básicos
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


def _eur(v: float) -> str:
    return f"{v:.2f} €"


# ---------------------------------------------------------------------------
# Helpers de análisis
# ---------------------------------------------------------------------------

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
    return problems


def get_report_status(report: dict) -> dict:
    """Devuelve el semáforo del informe: ok / review / danger."""
    totals = report["totals"]
    problems = report["problems"]
    warnings = report["warnings"]

    # PELIGRO
    if totals["gross_profit"] < 0:
        return {"status": "danger", "label": "PELIGRO", "reason": "El beneficio total es negativo."}
    if totals["final_total"] < totals["cost_subtotal"] and totals["cost_subtotal"] > 0:
        return {"status": "danger", "label": "PELIGRO", "reason": "El total cliente es menor que el coste total."}
    if any("negativo" in p["issue"] for p in problems):
        return {"status": "danger", "label": "PELIGRO", "reason": "Hay líneas con beneficio negativo."}

    # REVISAR
    if any("coste 0" in p["issue"] for p in problems):
        return {"status": "review", "label": "REVISAR", "reason": "Hay líneas con coste 0 que deben revisarse."}
    if any("sin proveedor" in p["issue"] for p in problems):
        return {"status": "review", "label": "REVISAR", "reason": "Hay materiales sin proveedor asignado."}
    if any("margen bajo" in p["issue"] for p in problems):
        return {"status": "review", "label": "REVISAR", "reason": "Hay líneas con margen bajo."}
    if warnings:
        return {"status": "review", "label": "REVISAR", "reason": "Hay warnings del motor pendientes."}
    if problems:
        return {"status": "review", "label": "REVISAR", "reason": "Hay elementos que requieren atención."}

    # OK
    return {"status": "ok", "label": "OK", "reason": "No se detectaron problemas críticos."}


def _build_human_summary(report: dict) -> list[str]:
    totals = report["totals"]
    lines = report["lines"]
    supplier_summary = report["supplier_summary"]
    problems = report["problems"]

    summary: list[str] = []

    summary.append(f"El total cliente es {_eur(totals['final_total'])}.")

    pct = totals["gross_profit_percent"]
    if pct is not None:
        summary.append(f"El beneficio es {_eur(totals['gross_profit'])} ({pct:.1f}%).")
    else:
        summary.append(f"El beneficio es {_eur(totals['gross_profit'])}.")

    real_suppliers = [s for s in supplier_summary if s["supplier"] != "(sin proveedor)"]
    if real_suppliers:
        main_sup = max(real_suppliers, key=lambda s: s["cost_total"])
        summary.append(f"El proveedor principal es {main_sup['supplier']}.")

    n = len(lines)
    summary.append(f"El presupuesto tiene {n} {'línea' if n == 1 else 'líneas'}.")

    zero_cost = sum(1 for p in problems if "coste 0" in p["issue"])
    if zero_cost:
        summary.append(
            f"Hay {zero_cost} {'línea' if zero_cost == 1 else 'líneas'} con coste 0 "
            f"que {'debe' if zero_cost == 1 else 'deben'} revisarse."
        )

    neg = sum(1 for p in problems if "negativo" in p["issue"])
    if neg:
        summary.append(f"Hay {neg} {'línea' if neg == 1 else 'líneas'} con beneficio negativo.")

    return summary


def _build_review_recommendations(report: dict) -> list[str]:
    problems = report["problems"]
    warnings = report["warnings"]
    recs: list[str] = []

    if any("coste 0" in p["issue"] for p in problems):
        recs.append("Revisar líneas con coste 0 antes de enviar.")
    if any("sin proveedor" in p["issue"] for p in problems):
        recs.append("Confirmar que todos los materiales tienen proveedor asignado.")
    if any("margen bajo" in p["issue"] for p in problems):
        recs.append("Revisar líneas con margen inferior al 10%.")
    if any("negativo" in p["issue"] for p in problems):
        recs.append("Corregir líneas con beneficio negativo.")
    if warnings:
        recs.append("Revisar los warnings del motor de cálculo.")

    return recs


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
    """HTML del informe interno (compatibilidad existente)."""
    return build_internal_report_html(snapshot, calculated=calculated)


# ---------------------------------------------------------------------------
# API de alto nivel (calculan internamente — solo necesitan snapshot)
# ---------------------------------------------------------------------------

def build_internal_report(
    snapshot: QuoteSnapshot,
    metadata: dict[str, Any] | None = None,
) -> dict:
    """Genera el informe completo con semáforo, resumen humano y recomendaciones."""
    calculated = calculate_quote(snapshot)
    base = export_internal_report_dict(snapshot, calculated)
    supplier_summary = _build_supplier_summary(base["lines"])
    problems = _detect_problems(base["lines"])

    report: dict[str, Any] = {
        "metadata": metadata or {},
        "header": base["header"],
        "totals": base["totals"],
        "supplier_summary": supplier_summary,
        "lines": base["lines"],
        "problems": problems,
        "warnings": base["warnings"],
        "internal_notes": snapshot.header.internal_notes,
    }

    report["report_status"] = get_report_status(report)
    report["human_summary"] = _build_human_summary(report)
    report["review_recommendations"] = _build_review_recommendations(report)

    return report


# ---------------------------------------------------------------------------
# Generación HTML
# ---------------------------------------------------------------------------

_STATUS_CSS = {
    "ok":     ("status-ok",     "#e8f5e9", "#2e7d32", "#4caf50"),
    "review": ("status-review", "#fff8e1", "#e65100", "#ff9800"),
    "danger": ("status-danger", "#fce4ec", "#b71c1c", "#e57373"),
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
    rs = report["report_status"]
    human_summary = report["human_summary"]
    review_recs = report["review_recommendations"]

    status_key = rs["status"]
    _, st_bg, st_fg, st_border = _STATUS_CSS.get(status_key, _STATUS_CSS["ok"])

    # ── Título / IDs ─────────────────────────────────────────────────────
    title = meta.get("id") or header.get("quote_number") or "Presupuesto sin ID"
    quote_number = header.get("quote_number")
    client = header.get("client_name") or "(sin cliente)"
    pct_total = _pct_str(totals["gross_profit_percent"])

    # ── Metadata table ───────────────────────────────────────────────────
    meta_rows = ""
    if meta:
        fields = [
            ("ID guardado", meta.get("id")),
            ("Estado", meta.get("status")),
            ("Creado", meta.get("created_at")),
            ("Actualizado", meta.get("updated_at")),
            ("Tipo proyecto", meta.get("project_type")),
            ("Tags", ", ".join(meta.get("tags", [])) or None),
            ("Autor", meta.get("created_by")),
        ]
        for label, val in fields:
            if val:
                meta_rows += f"<tr><th>{_esc(label)}</th><td>{_esc(val)}</td></tr>"
    if quote_number:
        meta_rows += f"<tr><th>Número presupuesto</th><td>{_esc(quote_number)}</td></tr>"

    meta_html = (
        f'<table class="meta-table">{meta_rows}</table>' if meta_rows else ""
    )

    # ── Tarjetas ─────────────────────────────────────────────────────────
    profit_pct_val = totals["gross_profit_percent"]
    profit_card_cls = (
        "card-danger" if totals["gross_profit"] < 0
        else "card-warn" if (profit_pct_val is not None and profit_pct_val < 10)
        else "card-ok"
    )
    problems_card_cls = "card-danger" if problems else "card-ok"
    warnings_card_cls = "card-warn" if report["warnings"] else "card-ok"

    cards_html = f"""
<div class="cards">
  <div class="card">
    <div class="card-label">Total cliente</div>
    <div class="card-value">{_eur(totals['final_total'])}</div>
  </div>
  <div class="card">
    <div class="card-label">Coste total</div>
    <div class="card-value">{_eur(totals['cost_subtotal'])}</div>
  </div>
  <div class="card {profit_card_cls}">
    <div class="card-label">Beneficio</div>
    <div class="card-value">{_eur(totals['gross_profit'])}</div>
  </div>
  <div class="card {profit_card_cls}">
    <div class="card-label">% Beneficio</div>
    <div class="card-value">{pct_total}</div>
  </div>
  <div class="card {problems_card_cls}">
    <div class="card-label">Problemas</div>
    <div class="card-value">{len(problems)}</div>
  </div>
  <div class="card {warnings_card_cls}">
    <div class="card-label">Warnings</div>
    <div class="card-value">{len(report['warnings'])}</div>
  </div>
</div>"""

    # ── Resumen rápido ───────────────────────────────────────────────────
    summary_items = "".join(f"<li>{_esc(s)}</li>" for s in human_summary)
    summary_html = f'<ul class="summary-list">{summary_items}</ul>'

    # ── Qué revisar ──────────────────────────────────────────────────────
    if review_recs:
        rec_items = "".join(f"<li>{_esc(r)}</li>" for r in review_recs)
        review_html = f'<ul class="review-list">{rec_items}</ul>'
    else:
        review_html = '<p class="no-issues">No hay revisiones críticas detectadas.</p>'

    # ── Problemas detectados ─────────────────────────────────────────────
    problems_html = ""
    if problems:
        items = "".join(
            f"<li><b>{_esc(p['line'])}</b> — {_esc(p['issue'])}</li>" for p in problems
        )
        problems_html = f'<div class="alert-box alert-warn"><h3>⚠ Problemas detectados</h3><ul>{items}</ul></div>'

    # ── Warnings del motor ───────────────────────────────────────────────
    warnings_html = ""
    if report["warnings"]:
        items = "".join(f"<li>{_esc(w)}</li>" for w in report["warnings"])
        warnings_html = f'<div class="alert-box alert-warn"><h3>Warnings del motor</h3><ul>{items}</ul></div>'

    # ── Notas internas ───────────────────────────────────────────────────
    notes_html = ""
    if report["internal_notes"]:
        notes_html = (
            f'<div class="alert-box alert-info"><h3>Notas internas</h3>'
            f'<p>{_esc(report["internal_notes"])}</p></div>'
        )

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

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Informe Interno — {_esc(title)}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{ font-family: sans-serif; font-size: 13px; padding: 24px; color: #222;
            max-width: 1200px; margin: 0 auto; }}
    h1 {{ font-size: 22px; margin: 0 0 4px; }}
    h2 {{ font-size: 15px; margin: 28px 0 10px; border-bottom: 2px solid #e0e0e0;
          padding-bottom: 4px; color: #333; }}
    h3 {{ font-size: 13px; margin: 8px 0 6px; }}
    p {{ margin: 4px 0; }}
    a {{ color: inherit; }}

    /* Cabecera */
    .header-block {{ margin-bottom: 20px; }}
    .stamp {{ color: #999; font-size: 11px; float: right; margin-top: 4px; }}
    .sub-info {{ color: #555; margin-top: 6px; }}

    /* Semáforo */
    .status-badge {{
      display: inline-block; padding: 5px 16px; border-radius: 20px;
      font-size: 14px; font-weight: 700; letter-spacing: 0.5px;
      background: {st_bg}; color: {st_fg}; border: 1px solid {st_border};
      margin: 8px 0;
    }}
    .status-reason {{ font-size: 12px; color: #555; margin: 2px 0 10px; }}

    /* Metadata */
    .meta-table {{ border-collapse: collapse; margin: 12px 0; width: auto; }}
    .meta-table th, .meta-table td {{ border: 1px solid #ddd; padding: 4px 10px;
                                       text-align: left; font-size: 12px; }}
    .meta-table th {{ background: #f5f5f5; width: 140px; font-weight: 600; }}

    /* Tarjetas */
    .cards {{ display: flex; gap: 10px; flex-wrap: wrap; margin: 16px 0; }}
    .card {{ flex: 1; min-width: 110px; border: 1px solid #ddd; border-radius: 8px;
              padding: 14px 12px; text-align: center; background: #fafafa; }}
    .card-label {{ font-size: 11px; color: #777; text-transform: uppercase;
                    letter-spacing: 0.3px; margin-bottom: 6px; }}
    .card-value {{ font-size: 20px; font-weight: 700; color: #222; }}
    .card-ok    {{ background: #f1f8f1; border-color: #81c784; }}
    .card-ok .card-value {{ color: #2e7d32; }}
    .card-warn  {{ background: #fff8e1; border-color: #ffb74d; }}
    .card-warn .card-value {{ color: #e65100; }}
    .card-danger {{ background: #fce4ec; border-color: #e57373; }}
    .card-danger .card-value {{ color: #b71c1c; }}

    /* Resumen rápido y Qué revisar */
    .summary-list, .review-list {{ margin: 6px 0; padding-left: 22px; line-height: 1.7; }}
    .no-issues {{ color: #2e7d32; font-weight: 600; margin: 6px 0; }}

    /* Alertas */
    .alert-box {{ border-radius: 6px; padding: 10px 14px; margin: 12px 0; }}
    .alert-warn {{ background: #fff8e1; border: 1px solid #ffb74d; }}
    .alert-info {{ background: #e8f4fd; border: 1px solid #90caf9; }}
    .alert-box ul {{ margin: 4px 0; padding-left: 20px; line-height: 1.7; }}

    /* Tablas de datos */
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 12px; }}
    th, td {{ border: 1px solid #ddd; padding: 5px 8px; text-align: right; }}
    th {{ background: #f5f5f5; text-align: center; font-weight: 600; font-size: 12px; }}
    td:first-child, td:nth-child(2), td:nth-child(3) {{ text-align: left; }}
    .totals-table {{ width: auto; }}
    .totals-table td {{ font-weight: 600; }}
    .row-danger {{ background: #fce4ec; }}
    .row-warn   {{ background: #fff8e1; }}
    .row-low    {{ background: #fff3cd; }}
  </style>
</head>
<body>

  <!-- CABECERA -->
  <div class="header-block">
    <span class="stamp">USO INTERNO — Index Clima</span>
    <h1>Informe Interno — {_esc(title)}</h1>
    <div class="status-badge">{_esc(rs['label'])}</div>
    <p class="status-reason">{_esc(rs['reason'])}</p>
    <p class="sub-info">
      <b>Cliente:</b> {_esc(client)}
      &nbsp;|&nbsp; <b>Fecha:</b> {_esc(header.get('date'))}
      &nbsp;|&nbsp; <b>Título:</b> {_esc(header.get('title'))}
    </p>
    {meta_html}
  </div>

  <!-- TARJETAS -->
  <h2>Estado del presupuesto</h2>
  {cards_html}

  <!-- RESUMEN RÁPIDO -->
  <h2>Resumen rápido</h2>
  {summary_html}

  <!-- QUÉ REVISAR -->
  <h2>Qué revisar</h2>
  {review_html}

  {problems_html}
  {warnings_html}

  <!-- TOTALES DETALLADOS -->
  <h2>Totales detallados</h2>
  <table class="totals-table" style="width:auto">
    <tr><td>Coste total</td><td>{_eur(totals['cost_subtotal'])}</td></tr>
    <tr><td>Tarifa bruta proveedor</td><td>{_eur(totals['supplier_gross_subtotal'])}</td></tr>
    <tr><td>Ahorro proveedor</td><td>{_eur(totals['supplier_saving_total'])}</td></tr>
    <tr><td>Venta sin IGIC</td><td>{_eur(totals['sale_subtotal'])}</td></tr>
    <tr><td>IGIC</td><td>{_eur(totals['tax_amount'])}</td></tr>
    <tr><td><b>Total cliente</b></td><td><b>{_eur(totals['final_total'])}</b></td></tr>
    <tr><td>Beneficio bruto</td><td>{_eur(totals['gross_profit'])}</td></tr>
    <tr><td>% Beneficio</td><td>{pct_total}</td></tr>
  </table>

  <!-- RESUMEN POR PROVEEDOR -->
  <h2>Resumen por proveedor</h2>
  <table>
    <thead>
      <tr>
        <th>Proveedor</th><th>Coste total</th><th>Venta total</th>
        <th>Beneficio</th><th>% Benef.</th><th>Líneas</th>
      </tr>
    </thead>
    <tbody>{sup_rows}</tbody>
  </table>

  <!-- LÍNEAS -->
  <h2>Líneas del presupuesto</h2>
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
    <tbody>{line_rows}</tbody>
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
