"""Normalización e importación de JSON de proveedor."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from .models import QuoteHeader, QuoteLine, QuoteSnapshot


# ---------------------------------------------------------------------------
# Alias de campos aceptados
# ---------------------------------------------------------------------------

_DESCRIPTION_KEYS = ("descripcion", "description", "concepto", "nombre", "name")
_CONCEPT_KEYS = ("concepto", "concept", "codigo_nombre")
_QUANTITY_KEYS = ("cantidad", "quantity", "qty")
_UNIT_KEYS = ("unidad", "unit")
_SUPPLIER_KEYS = ("proveedor", "supplier", "proveedorNombre", "supplier_name")
_CODE_KEYS = ("codigo", "code", "referencia", "ref")
_GROSS_PRICE_KEYS = (
    "pvpProveedor",
    "supplier_gross_unit_price",
    "tarifaProveedor",
    "pvp",
    "precio_tarifa",
)
_NET_COST_KEYS = (
    "costeUnitario",
    "supplier_net_unit_cost",
    "netoProveedor",
    "neto",
    "coste_unitario",
)
_TOTAL_COST_KEYS = ("precio", "totalCost", "total_cost", "costeTotal", "coste_total")
_DISCOUNTS_KEYS = (
    "descuentosProveedor",
    "discounts",
    "descuentos",
    "dto",
    "descuento",
    "supplier_discounts",
)
_MARGIN_KEYS = ("margen", "margin")
_TAX_KEYS = ("igic", "tax", "iva")
_SALE_MODE_KEYS = ("sale_mode", "modoVenta", "modo_venta")
_SALE_VALUE_KEYS = ("sale_value", "valorVenta", "valor_venta")
_TYPE_KEYS = ("type", "tipo", "tipo_linea")
_NOTES_KEYS = ("notes", "notas")
_PASS_DISCOUNT_KEYS = (
    "pass_supplier_discount_to_client",
    "pasarDescuentoCliente",
    "pasar_descuento_cliente",
)


def _first(d: dict, keys: tuple[str, ...], default: Any = None) -> Any:
    for k in keys:
        if k in d:
            return d[k]
    return default


def _parse_discounts(raw: Any) -> list[float]:
    if raw is None:
        return []
    if isinstance(raw, (int, float)):
        return [float(raw)]
    if isinstance(raw, str):
        # "40+5" o "40,5" o "40;5"
        raw = raw.replace("+", ",").replace(";", ",")
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        try:
            return [float(p) for p in parts]
        except ValueError:
            return []
    if isinstance(raw, list):
        result = []
        for item in raw:
            result.extend(_parse_discounts(item))
        return result
    return []


# ---------------------------------------------------------------------------
# Limpieza de JSON crudo
# ---------------------------------------------------------------------------

def _sanitize_raw(raw: str) -> str:
    # Quitar BOM
    raw = raw.lstrip("﻿")
    # Quitar code fences ```json ... ```
    raw = re.sub(r"```(?:json)?\s*", "", raw)
    raw = raw.strip()
    # Convertir comillas tipográficas
    raw = raw.replace("“", '"').replace("”", '"')
    raw = raw.replace("‘", "'").replace("’", "'")
    # Quitar comas finales antes de } o ]
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    return raw


def parse_json_with_recovery(raw: str | list | dict) -> list | dict:
    """Acepta string JSON, lista o dict directamente."""
    if isinstance(raw, (list, dict)):
        return raw
    if not isinstance(raw, str):
        raise ValueError(f"Tipo no soportado: {type(raw)}")
    clean = _sanitize_raw(raw)
    try:
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido después del saneado: {exc}") from exc


# ---------------------------------------------------------------------------
# Normalización de una línea
# ---------------------------------------------------------------------------

def _normalize_line(raw_line: dict, defaults: dict | None = None) -> QuoteLine:
    defaults = defaults or {}

    description = _first(raw_line, _DESCRIPTION_KEYS, "")
    concept = _first(raw_line, _CONCEPT_KEYS)
    quantity = float(_first(raw_line, _QUANTITY_KEYS, 1))
    unit = str(_first(raw_line, _UNIT_KEYS, "ud"))
    supplier = _first(raw_line, _SUPPLIER_KEYS)
    code = _first(raw_line, _CODE_KEYS)

    gross_price_raw = _first(raw_line, _GROSS_PRICE_KEYS)
    gross_price = float(gross_price_raw) if gross_price_raw is not None else None

    net_cost_raw = _first(raw_line, _NET_COST_KEYS)
    net_cost = float(net_cost_raw) if net_cost_raw is not None else None

    total_cost_raw = _first(raw_line, _TOTAL_COST_KEYS)
    total_cost = float(total_cost_raw) if total_cost_raw is not None else None

    discounts = _parse_discounts(_first(raw_line, _DISCOUNTS_KEYS))

    margin_raw = _first(raw_line, _MARGIN_KEYS, defaults.get("global_margin"))
    margin = float(margin_raw) if margin_raw is not None else None

    tax_raw = _first(raw_line, _TAX_KEYS)
    tax = float(tax_raw) if tax_raw is not None else None

    sale_mode = _first(raw_line, _SALE_MODE_KEYS, "margin")
    sale_value_raw = _first(raw_line, _SALE_VALUE_KEYS)
    sale_value = float(sale_value_raw) if sale_value_raw is not None else None

    line_type = _first(raw_line, _TYPE_KEYS, "material")
    # Validar tipo
    valid_types = {"material", "labor", "travel", "global_work", "adjustment"}
    if line_type not in valid_types:
        line_type = "material"

    notes = _first(raw_line, _NOTES_KEYS)
    pass_discount = bool(_first(raw_line, _PASS_DISCOUNT_KEYS, False))

    line_id = raw_line.get("id") or str(uuid.uuid4())

    return QuoteLine(
        id=line_id,
        type=line_type,
        code=code,
        concept=concept,
        description=str(description),
        quantity=quantity,
        unit=unit,
        supplier=supplier,
        supplier_gross_unit_price=gross_price,
        supplier_discounts=discounts,
        supplier_net_unit_cost=net_cost,
        total_cost=total_cost,
        sale_mode=sale_mode,
        margin=margin,
        sale_value=sale_value,
        tax=tax,
        pass_supplier_discount_to_client=pass_discount,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Punto de entrada público
# ---------------------------------------------------------------------------

def normalize_supplier_json(
    data: str | list | dict,
    defaults: dict | None = None,
) -> QuoteSnapshot:
    """Normaliza un JSON de proveedor en un QuoteSnapshot.

    Acepta:
    - Lista de líneas directamente.
    - Dict con clave 'lines' (y opcionalmente 'header').
    """
    defaults = defaults or {}
    parsed = parse_json_with_recovery(data)

    raw_lines: list[dict]
    raw_header: dict = {}

    if isinstance(parsed, list):
        raw_lines = parsed
    elif isinstance(parsed, dict):
        raw_lines = parsed.get("lines", parsed.get("lineas", []))
        raw_header = parsed.get("header", parsed.get("cabecera", {}))
    else:
        raise ValueError("El JSON debe ser una lista o un objeto con clave 'lines'.")

    # Construir header
    header_data: dict = {}
    if defaults:
        if "global_margin" in defaults:
            header_data["global_margin"] = defaults["global_margin"]
        if "tax" in defaults:
            header_data["tax"] = defaults["tax"]
        if "include_tax" in defaults:
            header_data["include_tax"] = defaults["include_tax"]
        if "quote_number" in defaults:
            header_data["quote_number"] = defaults["quote_number"]
        if "client_name" in defaults:
            header_data["client_name"] = defaults["client_name"]
        if "title" in defaults:
            header_data["title"] = defaults["title"]

    # raw_header sobreescribe defaults
    header_data.update(raw_header)
    header = QuoteHeader(**header_data)

    lines = [_normalize_line(line, defaults) for line in raw_lines if isinstance(line, dict)]

    return QuoteSnapshot(header=header, lines=lines)
