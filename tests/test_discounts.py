"""Tests de cálculo de descuentos."""

import pytest

from quote_engine.discounts import apply_discounts, get_combined_discount_percent


def test_combined_discount_40_5():
    """40+5 = 43%, no 45%."""
    result = get_combined_discount_percent([40, 5])
    assert abs(result - 43.0) < 1e-9


def test_combined_discount_single():
    assert get_combined_discount_percent([30]) == pytest.approx(30.0)


def test_combined_discount_empty():
    assert get_combined_discount_percent([]) == 0.0


def test_combined_discount_zero():
    assert get_combined_discount_percent([0]) == pytest.approx(0.0)


def test_apply_discounts_40_5():
    """PVP 100, descuento 40+5 → 57."""
    result = apply_discounts(100.0, [40, 5])
    assert abs(result - 57.0) < 1e-9


def test_apply_discounts_no_discounts():
    assert apply_discounts(100.0, []) == 100.0


def test_apply_discounts_single():
    assert apply_discounts(200.0, [50]) == pytest.approx(100.0)
