"""Exportador de informe interno (dict y HTML simple)."""

from __future__ import annotations

from ..models import CalculatedQuote, QuoteSnapshot


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
    """Devuelve el informe interno como HTML simple."""
    data = export_internal_report_dict(snapshot, calculated)
    header = data["header"]
    totals = data["totals"]
    lines = data["lines"]

    pct = (
        f"{totals['gross_profit_percent']:.1f}%"
        if totals["gross_profit_percent"] is not None
        else "N/A"
    )

    rows = ""
    for ln in lines:
        lp = (
            f"{ln['gross_profit_percent']:.1f}%"
            if ln["gross_profit_percent"] is not None
            else "N/A"
        )
        rows += (
            f"<tr>"
            f"<td>{ln['description']}</td>"
            f"<td>{ln['type']}</td>"
            f"<td>{ln['supplier'] or ''}</td>"
            f"<td>{ln['quantity']} {ln['unit']}</td>"
            f"<td>{ln['cost_total']:.2f} €</td>"
            f"<td>{ln['sale_total_without_tax']:.2f} €</td>"
            f"<td>{ln['tax_rate']:.1f}%</td>"
            f"<td>{ln['tax_amount']:.2f} €</td>"
            f"<td>{ln['client_total']:.2f} €</td>"
            f"<td>{ln['gross_profit']:.2f} €</td>"
            f"<td>{lp}</td>"
            f"<td>{ln['supplier_saving'] or 0:.2f} €</td>"
            f"</tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Informe Interno — {header.get('quote_number') or 'Presupuesto'}</title>
  <style>
    body {{ font-family: sans-serif; font-size: 13px; padding: 20px; }}
    h1 {{ font-size: 18px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ccc; padding: 6px 8px; text-align: right; }}
    th {{ background: #f0f0f0; text-align: center; }}
    td:first-child, td:nth-child(2), td:nth-child(3) {{ text-align: left; }}
    .totals {{ margin-top: 20px; font-size: 14px; }}
    .totals td {{ font-weight: bold; }}
  </style>
</head>
<body>
  <h1>Informe Interno — {header.get('quote_number') or ''} {header.get('client_name') or ''}</h1>
  <p><b>Fecha:</b> {header.get('date') or ''} | <b>Título:</b> {header.get('title') or ''}</p>

  <table>
    <thead>
      <tr>
        <th>Descripción</th><th>Tipo</th><th>Proveedor</th><th>Cant.</th>
        <th>Coste</th><th>Venta (s/IGIC)</th><th>IGIC%</th><th>IGIC</th>
        <th>Total Cliente</th><th>Beneficio</th><th>% Benef.</th><th>Ahorro Prov.</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>

  <div class="totals">
    <table style="width: auto; margin-top: 16px;">
      <tr><td>Coste total</td><td>{totals['cost_subtotal']:.2f} €</td></tr>
      <tr><td>Tarifa bruta proveedor</td><td>{totals['supplier_gross_subtotal']:.2f} €</td></tr>
      <tr><td>Ahorro proveedor</td><td>{totals['supplier_saving_total']:.2f} €</td></tr>
      <tr><td>Venta sin IGIC</td><td>{totals['sale_subtotal']:.2f} €</td></tr>
      <tr><td>IGIC</td><td>{totals['tax_amount']:.2f} €</td></tr>
      <tr><td><b>Total cliente</b></td><td><b>{totals['final_total']:.2f} €</b></td></tr>
      <tr><td>Beneficio bruto</td><td>{totals['gross_profit']:.2f} €</td></tr>
      <tr><td>% Beneficio</td><td>{pct}</td></tr>
    </table>
  </div>
</body>
</html>"""
