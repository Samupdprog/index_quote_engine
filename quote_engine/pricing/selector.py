"""Selector de precios con trazabilidad completa.

Aplica las reglas de pricing sobre los candidatos del catálogo
y devuelve siempre un resultado trazable.

El selector NO calcula importes — solo selecciona el precio adecuado.
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from .rules import DEFAULT_RULES, PricingRule
from .schemas import PriceSelectionResult

if TYPE_CHECKING:
    from quote_engine.catalog.schemas import ProductSearchResult

logger = logging.getLogger(__name__)


class PriceSelector:
    """Selecciona el mejor precio de entre un conjunto de candidatos."""

    def __init__(self, rules: Optional[list[PricingRule]] = None):
        self.rules = rules if rules is not None else DEFAULT_RULES

    def select(
        self,
        candidates: list["ProductSearchResult"],
        context: Optional[dict] = None,
        preferred_supplier: Optional[str] = None,
    ) -> PriceSelectionResult:
        """Selecciona el mejor precio aplicando las reglas configuradas.

        Args:
            candidates: Lista de candidatos del catálogo.
            context: Contexto adicional (requested_unit, previous_price, etc.).
            preferred_supplier: Nombre del proveedor preferente.

        Returns:
            PriceSelectionResult con trazabilidad completa.
        """
        if context is None:
            context = {}

        if not candidates:
            return PriceSelectionResult(
                selected=False,
                reason="Sin candidatos en catálogo",
                warnings=["No se encontraron productos en el catálogo para esta descripción."],
            )

        all_warnings: list[str] = []
        valid_candidates: list["ProductSearchResult"] = []

        for candidate in candidates:
            passed = True
            candidate_warnings: list[str] = []

            for rule in self.rules:
                rule_passed, rule_warnings = rule.check(candidate, context)
                candidate_warnings.extend(rule_warnings)
                if not rule_passed:
                    passed = False
                    logger.debug(
                        f"Candidato {candidate.description!r} rechazado por regla {rule.name!r}"
                    )
                    break

            all_warnings.extend(candidate_warnings)

            if passed:
                valid_candidates.append(candidate)

        if not valid_candidates:
            return PriceSelectionResult(
                selected=False,
                reason="Todos los candidatos fueron rechazados por las reglas de pricing",
                warnings=all_warnings,
            )

        # Ordenar: primero confianza alta, luego precio más bajo
        def _sort_key(c: "ProductSearchResult"):
            conf_order = {"alta": 0, "media": 1, "baja": 2}
            return (conf_order.get(c.confidence, 9), c.net_unit_price)

        valid_candidates.sort(key=_sort_key)

        # Proveedor preferente
        selected = None
        if preferred_supplier:
            from quote_engine.importers.excel_products_importer import normalize_supplier_name
            pref_norm = normalize_supplier_name(preferred_supplier)
            for c in valid_candidates:
                if normalize_supplier_name(c.supplier) == pref_norm:
                    selected = c
                    break

        if selected is None:
            selected = valid_candidates[0]

        requires_review = selected.confidence == "media" or any(
            "REVISAR" in w or "desactualizado" in w for w in all_warnings
        )

        source = {
            "product_id": selected.product_id,
            "supplier_price_id": selected.supplier_price_id,
            "source_file": selected.source_file,
            "source_sheet": selected.source_sheet,
            "source_row": selected.source_row,
            "document_date": str(selected.document_date) if selected.document_date else None,
            "original_confidence": selected.confidence,
            "original_reason": selected.reason,
        }

        return PriceSelectionResult(
            selected=True,
            price=selected.net_unit_price,
            supplier=selected.supplier,
            confidence=selected.confidence,
            warnings=all_warnings,
            reason=selected.reason,
            source=source,
            requires_review=requires_review,
        )

    def select_from_catalog(
        self,
        query: str,
        catalog_service,
        context: Optional[dict] = None,
        preferred_supplier: Optional[str] = None,
    ) -> PriceSelectionResult:
        """Busca en el catálogo y selecciona el mejor precio.

        Atajo conveniente: busca + selecciona en una sola llamada.
        """
        search_result = catalog_service.search_products(query, limit=20)
        candidates = search_result.results

        result = self.select(candidates, context=context, preferred_supplier=preferred_supplier)

        # Añadir warnings del catálogo
        result.warnings = search_result.warnings + result.warnings

        return result


# Instancia por defecto
default_selector = PriceSelector()
