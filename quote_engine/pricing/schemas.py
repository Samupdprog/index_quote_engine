"""Schemas de resultado del selector de precios."""

from __future__ import annotations

from typing import Optional, Any
from pydantic import BaseModel


class PriceSelectionResult(BaseModel):
    """Resultado de la selección de precio para una línea de presupuesto."""
    selected: bool
    price: Optional[float] = None
    supplier: Optional[str] = None
    confidence: Optional[str] = None   # alta | media | baja
    warnings: list[str] = []
    reason: str = ""
    source: dict[str, Any] = {}
    requires_review: bool = False      # True si confianza media o precio antiguo
