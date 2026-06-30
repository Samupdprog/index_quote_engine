"""Schemas Pydantic del catálogo de productos."""

from __future__ import annotations

from typing import Optional
from datetime import date

from pydantic import BaseModel


class ProductSearchResult(BaseModel):
    """Resultado de búsqueda de producto con precio."""
    product_id: Optional[int] = None
    supplier_price_id: Optional[int] = None
    description: str
    supplier: str
    net_unit_price: float
    gross_unit_price: Optional[float] = None
    discount_percent: Optional[float] = None
    unit: Optional[str] = None
    confidence: str  # alta | media | baja
    reason: str       # Por qué se seleccionó este resultado
    source_file: Optional[str] = None
    source_sheet: Optional[str] = None
    source_row: Optional[int] = None
    document_date: Optional[date] = None
    is_current: bool = True


class CatalogSearchResponse(BaseModel):
    """Respuesta de búsqueda en catálogo."""
    query: str
    results: list[ProductSearchResult]
    total: int
    has_high_confidence: bool
    warnings: list[str] = []
