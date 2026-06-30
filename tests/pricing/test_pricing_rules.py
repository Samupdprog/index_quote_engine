"""Tests de reglas de pricing y selector de precios."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import pytest

from quote_engine.catalog.schemas import ProductSearchResult
from quote_engine.pricing.rules import (
    DEFAULT_RULES,
    MediumConfidenceReviewRule,
    NoLowConfidenceAutoRule,
    NoNegativePriceRule,
    PriceChangeRule,
    StalenessPriceRule,
    UnitConversionRule,
)
from quote_engine.pricing.schemas import PriceSelectionResult
from quote_engine.pricing.selector import PriceSelector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_candidate(
    description: str = "Split 1x1",
    supplier: str = "Frigicoll",
    net_unit_price: float = 650.0,
    confidence: str = "alta",
    unit: Optional[str] = "ud",
    document_date: Optional[date] = None,
    product_id: int = 1,
    supplier_price_id: int = 1,
) -> ProductSearchResult:
    return ProductSearchResult(
        product_id=product_id,
        supplier_price_id=supplier_price_id,
        description=description,
        supplier=supplier,
        net_unit_price=net_unit_price,
        unit=unit,
        confidence=confidence,
        reason="test",
        document_date=document_date or date.today(),
    )


# ---------------------------------------------------------------------------
# Tests de reglas individuales
# ---------------------------------------------------------------------------

class TestNoNegativePriceRule:
    rule = NoNegativePriceRule()

    def test_positive_price_passes(self):
        c = make_candidate(net_unit_price=100.0)
        passed, warnings = self.rule.check(c, {})
        assert passed is True
        assert warnings == []

    def test_zero_price_passes(self):
        c = make_candidate(net_unit_price=0.0)
        passed, warnings = self.rule.check(c, {})
        assert passed is True

    def test_negative_price_rejected(self):
        c = make_candidate(net_unit_price=-50.0)
        passed, warnings = self.rule.check(c, {})
        assert passed is False
        assert len(warnings) > 0
        assert "negativo" in warnings[0].lower() or "abono" in warnings[0].lower()


class TestNoLowConfidenceAutoRule:
    rule = NoLowConfidenceAutoRule()

    def test_alta_confidence_passes(self):
        c = make_candidate(confidence="alta")
        passed, warnings = self.rule.check(c, {})
        assert passed is True

    def test_media_confidence_passes(self):
        c = make_candidate(confidence="media")
        passed, warnings = self.rule.check(c, {})
        assert passed is True

    def test_baja_confidence_rejected(self):
        c = make_candidate(confidence="baja")
        passed, warnings = self.rule.check(c, {})
        assert passed is False
        assert "baja" in warnings[0].lower()


class TestStalenessPriceRule:
    rule = StalenessPriceRule()

    def test_recent_date_no_warning(self):
        c = make_candidate(document_date=date.today())
        passed, warnings = self.rule.check(c, {})
        assert passed is True
        assert warnings == []

    def test_old_date_generates_warning(self):
        old_date = date.today() - timedelta(days=600)  # ~20 meses
        c = make_candidate(document_date=old_date)
        passed, warnings = self.rule.check(c, {})
        assert passed is True  # No rechaza, solo advierte
        assert len(warnings) > 0

    def test_no_date_no_warning(self):
        c = make_candidate(document_date=None)
        passed, warnings = self.rule.check(c, {})
        assert passed is True
        assert warnings == []


class TestUnitConversionRule:
    rule = UnitConversionRule()

    def test_normal_unit_no_warning(self):
        c = make_candidate(unit="ud")
        passed, warnings = self.rule.check(c, {"requested_unit": "ud"})
        assert passed is True
        assert warnings == []

    def test_rollo_unit_warns(self):
        c = make_candidate(unit="rollo")
        passed, warnings = self.rule.check(c, {})
        assert passed is True  # No rechaza
        assert len(warnings) > 0
        assert "conversion_factor" in warnings[0].lower() or "rollo" in warnings[0].lower()

    def test_mismatched_units_warns(self):
        c = make_candidate(unit="rollo")
        passed, warnings = self.rule.check(c, {"requested_unit": "m"})
        assert passed is True
        assert len(warnings) >= 1


class TestMediumConfidenceReviewRule:
    rule = MediumConfidenceReviewRule()

    def test_alta_no_warning(self):
        c = make_candidate(confidence="alta")
        passed, warnings = self.rule.check(c, {})
        assert passed is True
        assert warnings == []

    def test_media_generates_revisar_warning(self):
        c = make_candidate(confidence="media")
        passed, warnings = self.rule.check(c, {})
        assert passed is True
        assert len(warnings) > 0
        assert "REVISAR" in warnings[0] or "media" in warnings[0].lower()


class TestPriceChangeRule:
    rule = PriceChangeRule()

    def test_no_previous_price_no_warning(self):
        c = make_candidate(net_unit_price=100.0)
        passed, warnings = self.rule.check(c, {})
        assert passed is True
        assert warnings == []

    def test_small_change_no_warning(self):
        c = make_candidate(net_unit_price=105.0)
        passed, warnings = self.rule.check(c, {"previous_price": 100.0})
        assert passed is True
        assert warnings == []

    def test_large_change_warns(self):
        c = make_candidate(net_unit_price=200.0)
        passed, warnings = self.rule.check(c, {"previous_price": 100.0})
        assert passed is True  # No rechaza
        assert len(warnings) > 0


# ---------------------------------------------------------------------------
# Tests del selector
# ---------------------------------------------------------------------------

class TestPriceSelector:
    def test_select_empty_candidates(self):
        selector = PriceSelector()
        result = selector.select([])
        assert result.selected is False
        assert "Sin candidatos" in result.reason

    def test_select_single_high_confidence(self):
        selector = PriceSelector()
        c = make_candidate(confidence="alta", net_unit_price=650.0)
        result = selector.select([c])
        assert result.selected is True
        assert result.price == 650.0
        assert result.confidence == "alta"
        assert result.requires_review is False

    def test_select_rejects_low_confidence(self):
        selector = PriceSelector()
        c = make_candidate(confidence="baja")
        result = selector.select([c])
        assert result.selected is False

    def test_select_rejects_negative_price(self):
        selector = PriceSelector()
        c = make_candidate(net_unit_price=-50.0)
        result = selector.select([c])
        assert result.selected is False

    def test_select_prefers_high_confidence_over_cheaper_medium(self):
        """Alta confianza a mayor precio gana sobre media a menor precio."""
        selector = PriceSelector()
        high = make_candidate(confidence="alta", net_unit_price=700.0, product_id=1)
        medium = make_candidate(confidence="media", net_unit_price=500.0, product_id=2)
        result = selector.select([high, medium])
        assert result.selected is True
        assert result.confidence == "alta"
        assert result.price == 700.0

    def test_select_medium_confidence_requires_review(self):
        selector = PriceSelector()
        c = make_candidate(confidence="media")
        result = selector.select([c])
        assert result.selected is True
        assert result.requires_review is True

    def test_select_prefers_preferred_supplier(self):
        selector = PriceSelector()
        frigicoll = make_candidate(
            supplier="Frigicoll", confidence="alta", net_unit_price=700.0, product_id=1
        )
        airwell = make_candidate(
            supplier="Airwell", confidence="alta", net_unit_price=600.0, product_id=2
        )
        result = selector.select([frigicoll, airwell], preferred_supplier="Frigicoll")
        assert result.selected is True
        assert result.supplier == "Frigicoll"

    def test_select_cheapest_when_no_preferred(self):
        selector = PriceSelector()
        expensive = make_candidate(
            supplier="Frigicoll", confidence="alta", net_unit_price=700.0, product_id=1
        )
        cheap = make_candidate(
            supplier="Airwell", confidence="alta", net_unit_price=600.0, product_id=2
        )
        result = selector.select([expensive, cheap])
        assert result.selected is True
        assert result.price == 600.0

    def test_result_has_source_trazability(self):
        selector = PriceSelector()
        c = make_candidate(
            confidence="alta",
            net_unit_price=650.0,
            product_id=42,
            supplier_price_id=99,
        )
        result = selector.select([c])
        assert result.selected is True
        assert result.source["product_id"] == 42
        assert result.source["supplier_price_id"] == 99

    def test_old_price_requires_review(self):
        selector = PriceSelector()
        old_date = date.today() - timedelta(days=600)
        c = make_candidate(confidence="alta", document_date=old_date)
        result = selector.select([c])
        # El precio antiguo genera warning pero se selecciona
        assert result.selected is True
        assert any("desactualizado" in w for w in result.warnings)
