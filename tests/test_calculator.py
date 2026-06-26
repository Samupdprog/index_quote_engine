"""Tests del motor de cálculo."""

import pytest

from quote_engine.calculator import calculate_quote
from quote_engine.models import QuoteHeader, QuoteLine, QuoteSnapshot


def _make_snapshot(**line_kwargs) -> QuoteSnapshot:
    header = QuoteHeader(global_margin=35.0, tax=7.0, include_tax=False)
    line = QuoteLine(
        description="Split Daikin 1x1",
        supplier="Frigicoll",
        **line_kwargs,
    )
    return QuoteSnapshot(header=header, lines=[line])


class TestMaterialLine:
    def test_cost_unit_from_gross_and_discounts(self):
        """PVP 100, desc 40+5, qty 2 → cost_unit=57, cost_total=114."""
        snap = _make_snapshot(
            quantity=2,
            supplier_gross_unit_price=100.0,
            supplier_discounts=[40, 5],
            sale_mode="margin",
            margin=35,
        )
        calc = calculate_quote(snap)
        line = calc.lines[0]
        assert line.cost_unit == pytest.approx(57.0, abs=0.01)
        assert line.cost_total == pytest.approx(114.0, abs=0.01)

    def test_sale_without_tax_margin_mode(self):
        """cost_unit 57, margen 35% → sale_unit = 57*1.35 = 76.95, total = 153.9."""
        snap = _make_snapshot(
            quantity=2,
            supplier_gross_unit_price=100.0,
            supplier_discounts=[40, 5],
            sale_mode="margin",
            margin=35,
        )
        calc = calculate_quote(snap)
        line = calc.lines[0]
        assert line.sale_unit_without_tax == pytest.approx(76.95, abs=0.01)
        assert line.sale_total_without_tax == pytest.approx(153.9, abs=0.01)

    def test_pass_supplier_discount_to_client_uses_gross(self):
        """Con pass_supplier_discount_to_client=True, base = PVP bruto (100), no neto (57)."""
        snap = _make_snapshot(
            quantity=1,
            supplier_gross_unit_price=100.0,
            supplier_discounts=[40, 5],
            sale_mode="margin",
            margin=35,
            pass_supplier_discount_to_client=True,
        )
        calc = calculate_quote(snap)
        line = calc.lines[0]
        # base = 100, venta = 100 * 1.35 = 135
        assert line.sale_unit_without_tax == pytest.approx(135.0, abs=0.01)

    def test_igic_global_applied_when_line_has_no_tax(self):
        """Sin tax en línea, se usa el global (7%)."""
        snap = _make_snapshot(
            quantity=1,
            supplier_gross_unit_price=100.0,
            supplier_discounts=[40, 5],
            sale_mode="margin",
            margin=35,
        )
        calc = calculate_quote(snap)
        line = calc.lines[0]
        assert line.tax_rate == 7.0

    def test_igic_line_overrides_global(self):
        """IGIC de línea sobreescribe el global."""
        snap = _make_snapshot(
            quantity=1,
            supplier_gross_unit_price=100.0,
            supplier_discounts=[40, 5],
            sale_mode="margin",
            margin=35,
            tax=21.0,
        )
        calc = calculate_quote(snap)
        line = calc.lines[0]
        assert line.tax_rate == 21.0

    def test_fixed_unit_mode(self):
        """fixed_unit: sale_unit = sale_value, total = sale_value * qty."""
        snap = _make_snapshot(
            quantity=3,
            supplier_gross_unit_price=50.0,
            sale_mode="fixed_unit",
            sale_value=80.0,
        )
        calc = calculate_quote(snap)
        line = calc.lines[0]
        assert line.sale_unit_without_tax == pytest.approx(80.0)
        assert line.sale_total_without_tax == pytest.approx(240.0)

    def test_fixed_total_mode(self):
        """fixed_total: sale_total = sale_value independiente de cantidad."""
        snap = _make_snapshot(
            quantity=5,
            supplier_gross_unit_price=50.0,
            sale_mode="fixed_total",
            sale_value=1000.0,
        )
        calc = calculate_quote(snap)
        line = calc.lines[0]
        assert line.sale_total_without_tax == pytest.approx(1000.0)

    def test_cost_from_supplier_net(self):
        """Si hay supplier_net_unit_cost, se usa directamente."""
        snap = _make_snapshot(
            quantity=1,
            supplier_gross_unit_price=200.0,
            supplier_discounts=[40],
            supplier_net_unit_cost=110.0,
            sale_mode="margin",
            margin=30,
        )
        calc = calculate_quote(snap)
        line = calc.lines[0]
        assert line.cost_unit == pytest.approx(110.0)

    def test_cost_from_total_cost(self):
        """Si solo hay total_cost, cost_unit = total_cost / qty."""
        snap = _make_snapshot(
            quantity=4,
            total_cost=200.0,
            sale_mode="fixed_unit",
            sale_value=70.0,
        )
        calc = calculate_quote(snap)
        line = calc.lines[0]
        assert line.cost_unit == pytest.approx(50.0)

    def test_no_price_generates_warning(self):
        """Sin precio, coste 0 y warning."""
        snap = _make_snapshot(quantity=1, sale_mode="fixed_unit", sale_value=100.0)
        calc = calculate_quote(snap)
        line = calc.lines[0]
        assert line.cost_unit == 0.0
        assert len(line.warnings) > 0

    def test_gross_profit_zero_cost(self):
        """Coste 0 → gross_profit_percent es None."""
        snap = _make_snapshot(quantity=1, sale_mode="fixed_unit", sale_value=100.0)
        calc = calculate_quote(snap)
        line = calc.lines[0]
        assert line.gross_profit_percent is None

    def test_include_tax_false_adds_igic_to_total(self):
        snap = _make_snapshot(
            quantity=1,
            supplier_gross_unit_price=100.0,
            supplier_discounts=[40, 5],
            sale_mode="margin",
            margin=35,
        )
        calc = calculate_quote(snap)
        line = calc.lines[0]
        # include_tax=False → client_total = sale + tax
        expected = round(line.sale_total_without_tax + line.tax_amount, 2)
        assert line.client_total == pytest.approx(expected, abs=0.01)

    def test_include_tax_true_no_extra_igic(self):
        header = QuoteHeader(global_margin=35.0, tax=7.0, include_tax=True)
        line = QuoteLine(
            description="Test",
            supplier="X",
            quantity=1,
            supplier_gross_unit_price=100.0,
            supplier_discounts=[40, 5],
            sale_mode="margin",
            margin=35,
        )
        snap = QuoteSnapshot(header=header, lines=[line])
        calc = calculate_quote(snap)
        cl = calc.lines[0]
        assert cl.client_total == pytest.approx(cl.sale_total_without_tax, abs=0.01)


class TestTotals:
    def test_totals_aggregation(self):
        header = QuoteHeader(global_margin=35.0, tax=7.0)
        lines = [
            QuoteLine(
                description=f"Item {i}",
                quantity=1,
                supplier_gross_unit_price=100.0,
                supplier_discounts=[40, 5],
                sale_mode="margin",
                margin=35,
            )
            for i in range(3)
        ]
        snap = QuoteSnapshot(header=header, lines=lines)
        calc = calculate_quote(snap)
        assert calc.totals.cost_subtotal == pytest.approx(3 * 57.0, abs=0.01)
        assert calc.totals.sale_subtotal == pytest.approx(3 * 76.95, abs=0.02)
