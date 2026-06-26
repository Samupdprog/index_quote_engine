"""Tests del sistema de comandos."""

import pytest

from quote_engine.commands import apply_command, apply_commands
from quote_engine.models import QuoteHeader, QuoteLine, QuoteSnapshot
from quote_engine.validators import CommandError


def _base_snapshot() -> QuoteSnapshot:
    header = QuoteHeader(global_margin=35.0, tax=7.0)
    lines = [
        QuoteLine(
            id="line-1",
            description="Split Daikin",
            supplier="Frigicoll",
            quantity=2,
            supplier_gross_unit_price=500.0,
            supplier_discounts=[40, 5],
            sale_mode="margin",
            margin=35,
        ),
        QuoteLine(
            id="line-2",
            description="Mano de obra",
            type="labor",
            quantity=8,
            unit="h",
            sale_mode="fixed_unit",
            sale_value=45.0,
        ),
    ]
    return QuoteSnapshot(header=header, lines=lines)


class TestApplyMarginToSupplier:
    def test_only_modifies_target_supplier(self):
        snap = _base_snapshot()
        result = apply_command(snap, {
            "type": "apply_margin_to_supplier",
            "supplier": "Frigicoll",
            "margin": 40.0,
        })
        frigicoll_lines = [l for l in result.lines if l.supplier == "Frigicoll"]
        other_lines = [l for l in result.lines if l.supplier != "Frigicoll"]
        assert all(l.margin == 40.0 for l in frigicoll_lines)
        # La línea de mano de obra no debe cambiar margen
        assert all(l.margin != 40.0 for l in other_lines if l.margin is not None)

    def test_raises_if_supplier_not_found(self):
        snap = _base_snapshot()
        with pytest.raises(CommandError):
            apply_command(snap, {
                "type": "apply_margin_to_supplier",
                "supplier": "Inexistente",
                "margin": 35,
            })


class TestSetGlobalMargin:
    def test_updates_header(self):
        snap = _base_snapshot()
        result = apply_command(snap, {"type": "set_global_margin", "margin": 50.0})
        assert result.header.global_margin == 50.0

    def test_invalid_margin_raises(self):
        snap = _base_snapshot()
        with pytest.raises(CommandError):
            apply_command(snap, {"type": "set_global_margin", "margin": 99999.0})


class TestSetGlobalTax:
    def test_updates_tax(self):
        snap = _base_snapshot()
        result = apply_command(snap, {"type": "set_global_tax", "tax": 10.0})
        assert result.header.tax == 10.0

    def test_invalid_tax_raises(self):
        snap = _base_snapshot()
        with pytest.raises(CommandError):
            apply_command(snap, {"type": "set_global_tax", "tax": 150.0})


class TestUpdateLine:
    def test_update_description(self):
        snap = _base_snapshot()
        result = apply_command(snap, {
            "type": "update_line",
            "line_id": "line-1",
            "patch": {"description": "Daikin modificado"},
        })
        line = next(l for l in result.lines if l.id == "line-1")
        assert line.description == "Daikin modificado"

    def test_raises_if_line_not_found(self):
        snap = _base_snapshot()
        with pytest.raises(CommandError):
            apply_command(snap, {
                "type": "update_line",
                "line_id": "no-existe",
                "patch": {"description": "X"},
            })

    def test_raises_on_forbidden_field(self):
        snap = _base_snapshot()
        with pytest.raises(CommandError):
            apply_command(snap, {
                "type": "update_line",
                "line_id": "line-1",
                "patch": {"id": "hacked"},
            })


class TestDeleteLine:
    def test_removes_line(self):
        snap = _base_snapshot()
        result = apply_command(snap, {"type": "delete_line", "line_id": "line-1"})
        assert all(l.id != "line-1" for l in result.lines)
        assert len(result.lines) == 1

    def test_raises_if_not_found(self):
        snap = _base_snapshot()
        with pytest.raises(CommandError):
            apply_command(snap, {"type": "delete_line", "line_id": "nope"})


class TestAddLine:
    def test_adds_line(self):
        snap = _base_snapshot()
        result = apply_command(snap, {
            "type": "add_line",
            "line": {"description": "Nueva línea", "quantity": 1, "sale_mode": "fixed_unit", "sale_value": 100},
        })
        assert len(result.lines) == 3
        assert result.lines[-1].description == "Nueva línea"


class TestApplyPassDiscountToSupplier:
    def test_sets_flag(self):
        snap = _base_snapshot()
        result = apply_command(snap, {
            "type": "apply_pass_supplier_discount_to_supplier",
            "supplier": "Frigicoll",
            "enabled": True,
        })
        frigicoll = [l for l in result.lines if l.supplier == "Frigicoll"]
        assert all(l.pass_supplier_discount_to_client is True for l in frigicoll)


class TestApplyPatchToSupplier:
    def test_patches_multiple_fields(self):
        snap = _base_snapshot()
        result = apply_command(snap, {
            "type": "apply_patch_to_supplier",
            "supplier": "Frigicoll",
            "patch": {
                "sale_mode": "margin",
                "margin": 42.0,
                "pass_supplier_discount_to_client": True,
            },
        })
        for line in result.lines:
            if line.supplier == "Frigicoll":
                assert line.margin == 42.0
                assert line.pass_supplier_discount_to_client is True


class TestApplyCommands:
    def test_applies_in_order(self):
        snap = _base_snapshot()
        cmds = [
            {"type": "set_global_margin", "margin": 50.0},
            {"type": "set_global_tax", "tax": 10.0},
        ]
        result = apply_commands(snap, cmds)
        assert result.header.global_margin == 50.0
        assert result.header.tax == 10.0


class TestUnknownCommand:
    def test_raises(self):
        snap = _base_snapshot()
        with pytest.raises(CommandError):
            apply_command(snap, {"type": "comando_inventado"})
