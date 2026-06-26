"""Validaciones compartidas para comandos y otros puntos de entrada."""

from __future__ import annotations

from .models import QuoteSnapshot


class CommandError(ValueError):
    """Error de validación en un comando."""


def require_line(snapshot: QuoteSnapshot, line_id: str) -> None:
    ids = {line.id for line in snapshot.lines}
    if line_id not in ids:
        raise CommandError(f"No existe la línea con id '{line_id}'.")


def require_supplier(snapshot: QuoteSnapshot, supplier: str) -> None:
    suppliers = {line.supplier for line in snapshot.lines if line.supplier}
    if supplier not in suppliers:
        raise CommandError(f"No existe el proveedor '{supplier}' en ninguna línea.")


def validate_margin(margin: float) -> None:
    if not (-100 < margin < 10_000):
        raise CommandError(f"Margen {margin}% fuera de rango razonable.")


def validate_tax(tax: float) -> None:
    if not (0 <= tax <= 100):
        raise CommandError(f"IGIC {tax}% fuera de rango [0, 100].")


def validate_quantity(quantity: float) -> None:
    if quantity < 0:
        raise CommandError("La cantidad no puede ser negativa.")


_PATCHABLE_LINE_FIELDS = {
    "type",
    "code",
    "concept",
    "description",
    "quantity",
    "unit",
    "supplier",
    "supplier_invoice",
    "supplier_gross_unit_price",
    "supplier_discounts",
    "supplier_net_unit_cost",
    "total_cost",
    "sale_mode",
    "margin",
    "sale_value",
    "tax",
    "pass_supplier_discount_to_client",
    "notes",
}


def validate_patch_fields(patch: dict) -> None:
    forbidden = set(patch) - _PATCHABLE_LINE_FIELDS
    if forbidden:
        raise CommandError(f"Campos no permitidos en patch: {forbidden}")
