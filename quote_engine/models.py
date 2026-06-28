"""Modelos de datos del motor de presupuestos."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


LineType = Literal["material", "labor", "travel", "global_work", "adjustment"]
SaleMode = Literal["margin", "markup_unit", "fixed_unit", "fixed_total"]
QuoteStatus = Literal["draft", "sent", "accepted", "rejected", "archived"]


# ---------------------------------------------------------------------------
# Metadata de presupuesto guardado
# ---------------------------------------------------------------------------


class QuoteMetadata(BaseModel):
    id: str
    created_at: str
    updated_at: str
    created_by: str | None = None
    source: str = "api"
    status: QuoteStatus = "draft"
    project_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    client_reference: str | None = None
    internal_notes: str | None = None
    version: str = "0.4"


# ---------------------------------------------------------------------------
# Snapshot — datos de entrada (sin cálculos derivados)
# ---------------------------------------------------------------------------


class QuoteHeader(BaseModel):
    schema_version: int = 1
    quote_number: str | None = None
    client_name: str | None = None
    client_tax_id: str | None = None
    client_address: str | None = None
    date: str | None = None
    title: str | None = None
    validity: str = "30 días"
    payment: str = "50% a la firma y 50% al finalizar"
    global_margin: float = 35.0
    tax: float = 7.0
    include_tax: bool = False
    conditions: str | None = None
    internal_notes: str | None = None


class QuoteLine(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: LineType = "material"
    code: str | None = None
    concept: str | None = None
    description: str = ""
    quantity: float = 1.0
    unit: str = "ud"

    # Proveedor / compra
    supplier: str | None = None
    supplier_invoice: str | None = None
    supplier_gross_unit_price: float | None = None
    supplier_discounts: list[float] = Field(default_factory=list)
    supplier_net_unit_cost: float | None = None
    total_cost: float | None = None

    # Venta
    sale_mode: SaleMode = "margin"
    margin: float | None = None
    sale_value: float | None = None
    tax: float | None = None
    pass_supplier_discount_to_client: bool = False

    # Extra
    notes: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_not_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("quantity no puede ser negativa")
        return v

    @field_validator("supplier_discounts")
    @classmethod
    def discounts_in_range(cls, v: list[float]) -> list[float]:
        for d in v:
            if not (0 <= d < 100):
                raise ValueError(f"Descuento {d} fuera del rango [0, 100)")
        return v


class QuoteSnapshot(BaseModel):
    header: QuoteHeader = Field(default_factory=QuoteHeader)
    lines: list[QuoteLine] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Resultado calculado — nunca se persiste en el snapshot
# ---------------------------------------------------------------------------


class CalculatedLine(BaseModel):
    line_id: str
    description: str
    type: LineType
    quantity: float
    unit: str
    supplier: str | None

    # Proveedor
    supplier_gross_unit_price: float | None
    supplier_gross_total: float | None
    effective_supplier_discount: float | None
    cost_unit: float
    cost_total: float
    supplier_saving: float | None

    # Venta
    sale_mode: SaleMode
    applied_margin: float | None
    sale_unit_without_tax: float
    sale_total_without_tax: float
    tax_rate: float
    tax_amount: float
    client_total: float

    # Beneficio
    gross_profit: float
    gross_profit_percent: float | None

    warnings: list[str] = Field(default_factory=list)


class QuoteTotals(BaseModel):
    cost_subtotal: float
    supplier_gross_subtotal: float
    supplier_saving_total: float
    sale_subtotal: float
    tax_amount: float
    final_total: float
    gross_profit: float
    gross_profit_percent: float | None


class CalculatedQuote(BaseModel):
    snapshot: QuoteSnapshot
    lines: list[CalculatedLine]
    totals: QuoteTotals
    warnings: list[str] = Field(default_factory=list)
