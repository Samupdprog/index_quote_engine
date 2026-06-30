"""Resolvedor de catálogo para el motor de presupuestos.

Integra catálogo + pricing sin tocar el motor de cálculo (calculator.py).
El motor sigue siendo la única fuente de cálculo de importes.

Uso:
    resolver = CatalogResolver(catalog_service, selector)
    resolved = resolver.resolve_line(line_description, quantity, unit)
    # resolved contiene price, supplier, confidence, warnings, source
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from quote_engine.catalog.service import CatalogService
    from quote_engine.pricing.selector import PriceSelector
    from quote_engine.pricing.schemas import PriceSelectionResult

logger = logging.getLogger(__name__)


class CatalogResolver:
    """Resuelve precios de catálogo para líneas de presupuesto."""

    def __init__(self, catalog_service: "CatalogService", selector: "PriceSelector"):
        self.catalog = catalog_service
        self.selector = selector

    def resolve_line(
        self,
        description: str,
        quantity: Optional[float] = None,
        unit: Optional[str] = None,
        preferred_supplier: Optional[str] = None,
        previous_price: Optional[float] = None,
    ) -> "PriceSelectionResult":
        """Busca y selecciona el mejor precio para una descripción de línea.

        Args:
            description: Descripción del producto/material.
            quantity: Cantidad (para contexto de selección).
            unit: Unidad solicitada (para detectar incompatibilidades).
            preferred_supplier: Nombre del proveedor preferente.
            previous_price: Precio anterior conocido (para detectar cambios).

        Returns:
            PriceSelectionResult con trazabilidad completa.
        """
        context = {}
        if unit:
            context["requested_unit"] = unit
        if previous_price is not None:
            context["previous_price"] = previous_price
        if quantity is not None:
            context["quantity"] = quantity

        return self.selector.select_from_catalog(
            query=description,
            catalog_service=self.catalog,
            context=context,
            preferred_supplier=preferred_supplier,
        )

    def resolve_lines_batch(
        self,
        lines: list[dict],
        preferred_supplier: Optional[str] = None,
    ) -> list[dict]:
        """Resuelve múltiples líneas de presupuesto.

        Args:
            lines: Lista de dicts con keys: description, quantity, unit, previous_price (opcional).
            preferred_supplier: Proveedor preferente global.

        Returns:
            Lista de dicts con el resultado de resolución para cada línea.
        """
        results = []
        for line in lines:
            desc = line.get("description", "")
            if not desc:
                results.append({
                    "description": desc,
                    "resolved": False,
                    "reason": "Sin descripción",
                    "warnings": [],
                })
                continue

            selection = self.resolve_line(
                description=desc,
                quantity=line.get("quantity"),
                unit=line.get("unit"),
                preferred_supplier=preferred_supplier,
                previous_price=line.get("previous_price"),
            )

            results.append({
                "description": desc,
                "resolved": selection.selected,
                "price": selection.price,
                "supplier": selection.supplier,
                "confidence": selection.confidence,
                "reason": selection.reason,
                "requires_review": selection.requires_review,
                "warnings": selection.warnings,
                "source": selection.source,
            })

        return results


def build_resolver(db_session=None) -> CatalogResolver:
    """Construye un CatalogResolver con la configuración por defecto."""
    from quote_engine.catalog.service import CatalogService
    from quote_engine.pricing.selector import PriceSelector

    catalog = CatalogService(db_session=db_session)
    selector = PriceSelector()
    return CatalogResolver(catalog_service=catalog, selector=selector)
