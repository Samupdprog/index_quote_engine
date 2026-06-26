"""Motor de cálculo de presupuestos."""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal

from .discounts import apply_discounts, get_combined_discount_percent
from .models import (
    CalculatedLine,
    CalculatedQuote,
    QuoteLine,
    QuoteSnapshot,
    QuoteTotals,
)


def _round2(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _calculate_line(line: QuoteLine, snapshot: QuoteSnapshot) -> CalculatedLine:
    warnings: list[str] = []
    header = snapshot.header

    quantity = line.quantity

    # --- Descuento efectivo ---
    effective_discount: float | None = None
    if line.supplier_discounts:
        effective_discount = get_combined_discount_percent(line.supplier_discounts)

    # --- Coste unitario ---
    gross_unit = line.supplier_gross_unit_price
    cost_unit: float

    if line.supplier_net_unit_cost is not None:
        cost_unit = line.supplier_net_unit_cost
    elif gross_unit is not None:
        cost_unit = apply_discounts(gross_unit, line.supplier_discounts)
    elif line.total_cost is not None:
        cost_unit = line.total_cost / quantity if quantity else 0.0
    else:
        cost_unit = 0.0
        warnings.append(f"Línea '{line.description}': sin precio de coste; se asume 0.")

    cost_unit = _round2(cost_unit)
    cost_total = _round2(cost_unit * quantity)

    # --- Tarifa bruta proveedor ---
    supplier_gross_total: float | None = None
    supplier_saving: float | None = None
    if gross_unit is not None:
        supplier_gross_total = _round2(gross_unit * quantity)
        supplier_saving = _round2(supplier_gross_total - cost_total)

    # --- IGIC ---
    tax_rate = line.tax if line.tax is not None else header.tax

    # --- Margen aplicado ---
    applied_margin = line.margin if line.margin is not None else header.global_margin

    # --- Base de venta ---
    if line.pass_supplier_discount_to_client and gross_unit is not None:
        sale_base_unit = gross_unit
    else:
        sale_base_unit = cost_unit

    # --- Precio de venta sin IGIC ---
    mode = line.sale_mode
    sale_unit_without_tax: float
    sale_total_without_tax: float

    if mode == "margin":
        sale_unit_without_tax = _round2(sale_base_unit * (1.0 + applied_margin / 100.0))
        sale_total_without_tax = _round2(sale_unit_without_tax * quantity)

    elif mode == "markup_unit":
        sv = line.sale_value or 0.0
        sale_unit_without_tax = _round2(sale_base_unit + sv)
        sale_total_without_tax = _round2(sale_unit_without_tax * quantity)

    elif mode == "fixed_unit":
        sv = line.sale_value or 0.0
        sale_unit_without_tax = _round2(sv)
        sale_total_without_tax = _round2(sale_unit_without_tax * quantity)

    elif mode == "fixed_total":
        sv = line.sale_value or 0.0
        sale_total_without_tax = _round2(sv)
        sale_unit_without_tax = _round2(sale_total_without_tax / quantity) if quantity else 0.0

    else:
        sale_unit_without_tax = 0.0
        sale_total_without_tax = 0.0
        warnings.append(f"Línea '{line.description}': sale_mode '{mode}' desconocido.")

    # --- IGIC y total cliente ---
    tax_amount = _round2(sale_total_without_tax * tax_rate / 100.0)

    if header.include_tax:
        client_total = sale_total_without_tax
    else:
        client_total = _round2(sale_total_without_tax + tax_amount)

    # --- Beneficio ---
    gross_profit = _round2(sale_total_without_tax - cost_total)
    if cost_total != 0:
        gross_profit_percent = _round2(gross_profit / cost_total * 100.0)
    else:
        gross_profit_percent = None
        if sale_total_without_tax != 0:
            warnings.append(
                f"Línea '{line.description}': coste 0, no se puede calcular % beneficio."
            )

    return CalculatedLine(
        line_id=line.id,
        description=line.description,
        type=line.type,
        quantity=quantity,
        unit=line.unit,
        supplier=line.supplier,
        supplier_gross_unit_price=gross_unit,
        supplier_gross_total=supplier_gross_total,
        effective_supplier_discount=effective_discount,
        cost_unit=cost_unit,
        cost_total=cost_total,
        supplier_saving=supplier_saving,
        sale_mode=mode,
        applied_margin=applied_margin if mode == "margin" else None,
        sale_unit_without_tax=sale_unit_without_tax,
        sale_total_without_tax=sale_total_without_tax,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        client_total=client_total,
        gross_profit=gross_profit,
        gross_profit_percent=gross_profit_percent,
        warnings=warnings,
    )


def calculate_quote(snapshot: QuoteSnapshot) -> CalculatedQuote:
    """Calcula el presupuesto completo a partir del snapshot."""
    all_warnings: list[str] = []
    calculated_lines: list[CalculatedLine] = []

    for line in snapshot.lines:
        cl = _calculate_line(line, snapshot)
        calculated_lines.append(cl)
        all_warnings.extend(cl.warnings)

    # --- Totales ---
    cost_subtotal = _round2(sum(cl.cost_total for cl in calculated_lines))
    sale_subtotal = _round2(sum(cl.sale_total_without_tax for cl in calculated_lines))
    tax_amount = _round2(sum(cl.tax_amount for cl in calculated_lines))

    supplier_gross_subtotal = _round2(
        sum(cl.supplier_gross_total or 0.0 for cl in calculated_lines)
    )
    supplier_saving_total = _round2(
        sum(cl.supplier_saving or 0.0 for cl in calculated_lines)
    )

    if snapshot.header.include_tax:
        final_total = sale_subtotal
    else:
        final_total = _round2(sale_subtotal + tax_amount)

    gross_profit = _round2(sale_subtotal - cost_subtotal)
    gross_profit_percent = (
        _round2(gross_profit / cost_subtotal * 100.0) if cost_subtotal != 0 else None
    )

    totals = QuoteTotals(
        cost_subtotal=cost_subtotal,
        supplier_gross_subtotal=supplier_gross_subtotal,
        supplier_saving_total=supplier_saving_total,
        sale_subtotal=sale_subtotal,
        tax_amount=tax_amount,
        final_total=final_total,
        gross_profit=gross_profit,
        gross_profit_percent=gross_profit_percent,
    )

    return CalculatedQuote(
        snapshot=snapshot,
        lines=calculated_lines,
        totals=totals,
        warnings=all_warnings,
    )
