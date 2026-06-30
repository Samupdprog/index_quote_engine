"""Reglas de pricing para EON.

Estas reglas validan y filtran los candidatos de precio antes de seleccionar uno.
Nunca calculan importes — solo aprueban, rechazan o advierten sobre candidatos.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from quote_engine.catalog.schemas import ProductSearchResult

logger = logging.getLogger(__name__)

# Umbral de antigüedad de precio (meses)
PRICE_STALENESS_MONTHS = 18

# Cambio de precio que dispara advertencia
PRICE_CHANGE_WARNING_THRESHOLD = 0.30  # 30%

# Unidades que requieren factor de conversión
UNITS_REQUIRING_CONVERSION = {"rollo", "bobina", "caja", "pack", "lote"}


class PricingRule:
    """Clase base para una regla de pricing."""
    name: str = "base_rule"
    description: str = ""

    def check(
        self,
        candidate: "ProductSearchResult",
        context: dict,
    ) -> tuple[bool, list[str]]:
        """Verifica la regla.

        Returns:
            (passed, warnings) — passed=False rechaza el candidato.
        """
        return True, []


class NoNegativePriceRule(PricingRule):
    """Regla 6: No usar precios negativos como precio actual."""
    name = "no_negative_price"
    description = "Los precios negativos no se usan. Pueden ser abonos."

    def check(self, candidate, context):
        if candidate.net_unit_price < 0:
            return False, [
                f"Precio negativo ({candidate.net_unit_price}) para "
                f"{candidate.description!r} ({candidate.supplier}). "
                "Posible abono — no se usa."
            ]
        return True, []


class NoLowConfidenceAutoRule(PricingRule):
    """Regla 4: No usar automáticamente precios con confianza baja."""
    name = "no_low_confidence_auto"
    description = "Precios con confianza baja no se usan automáticamente."

    def check(self, candidate, context):
        if candidate.confidence == "baja":
            return False, [
                f"Precio de {candidate.description!r} ({candidate.supplier}) "
                "tiene confianza BAJA — no se usa automáticamente."
            ]
        return True, []


class StalenessPriceRule(PricingRule):
    """Regla 5: Marcar advertencia si el precio tiene fecha antigua."""
    name = "staleness_warning"
    description = f"Precios con más de {PRICE_STALENESS_MONTHS} meses generan advertencia."

    def check(self, candidate, context):
        warnings = []
        if candidate.document_date:
            threshold = date.today() - timedelta(days=PRICE_STALENESS_MONTHS * 30)
            if candidate.document_date < threshold:
                warnings.append(
                    f"Precio de {candidate.description!r} ({candidate.supplier}) "
                    f"puede estar desactualizado (fecha: {candidate.document_date})"
                )
        return True, warnings  # No rechaza, solo advierte


class UnitConversionRule(PricingRule):
    """Regla 8/9: No mezclar unidades sin conversion_factor."""
    name = "unit_conversion"
    description = "Unidades de empaque requieren conversion_factor para mezclar con unidades de cálculo."

    def check(self, candidate, context):
        warnings = []
        unit = (candidate.unit or "").lower()
        requested_unit = context.get("requested_unit", "").lower()

        if unit in UNITS_REQUIRING_CONVERSION:
            warnings.append(
                f"Unidad {unit!r} en {candidate.description!r} puede requerir "
                "conversion_factor (rollo→m, caja→ud, etc.)"
            )

        if requested_unit and unit and unit != requested_unit:
            if unit in UNITS_REQUIRING_CONVERSION or requested_unit in UNITS_REQUIRING_CONVERSION:
                warnings.append(
                    f"Unidad solicitada {requested_unit!r} ≠ unidad de precio {unit!r}. "
                    "Verificar conversión."
                )

        return True, warnings  # No rechaza, solo advierte


class MediumConfidenceReviewRule(PricingRule):
    """Regla 3: Marcar REVISAR si confianza media."""
    name = "medium_confidence_review"
    description = "Precios con confianza media se permiten pero se marcan para revisar."

    def check(self, candidate, context):
        if candidate.confidence == "media":
            return True, [
                f"Precio de {candidate.description!r} tiene confianza MEDIA — marcar REVISAR."
            ]
        return True, []


class PriceChangeRule(PricingRule):
    """Regla 7: Advertir si el precio cambió mucho respecto al histórico."""
    name = "price_change_warning"
    description = f"Cambios de precio >{PRICE_CHANGE_WARNING_THRESHOLD*100:.0f}% generan advertencia."

    def check(self, candidate, context):
        previous_price = context.get("previous_price")
        if previous_price and previous_price > 0:
            change = abs(candidate.net_unit_price - previous_price) / previous_price
            if change > PRICE_CHANGE_WARNING_THRESHOLD:
                return True, [
                    f"Cambio de precio significativo en {candidate.description!r}: "
                    f"{previous_price:.2f} → {candidate.net_unit_price:.2f} "
                    f"({change * 100:.1f}%)"
                ]
        return True, []


# Reglas por defecto (en orden de evaluación)
DEFAULT_RULES: list[PricingRule] = [
    NoNegativePriceRule(),
    NoLowConfidenceAutoRule(),
    StalenessPriceRule(),
    UnitConversionRule(),
    MediumConfidenceReviewRule(),
    PriceChangeRule(),
]
