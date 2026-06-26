"""Lógica de descuentos de proveedor."""

from __future__ import annotations


def get_combined_discount_percent(discounts: list[float]) -> float:
    """Calcula el descuento efectivo de una cadena de descuentos.

    Fórmula: efectivo = (1 - ∏(1 - dᵢ/100)) × 100
    Ejemplo: [40, 5] → 43.0  (no 45)
    """
    if not discounts:
        return 0.0
    factor = 1.0
    for d in discounts:
        factor *= 1.0 - d / 100.0
    return round((1.0 - factor) * 100.0, 10)


def apply_discounts(gross_price: float, discounts: list[float]) -> float:
    """Devuelve el precio neto tras aplicar la cadena de descuentos."""
    if not discounts:
        return gross_price
    factor = 1.0
    for d in discounts:
        factor *= 1.0 - d / 100.0
    return gross_price * factor
