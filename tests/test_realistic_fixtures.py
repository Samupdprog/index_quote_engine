"""Tests con fixtures realistas de presupuestos HVAC."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quote_engine.calculator import calculate_quote
from quote_engine.commands import apply_command
from quote_engine.exporters.holded import export_holded_payload
from quote_engine.normalizer import normalize_supplier_json

FIXTURES_DIR = Path(__file__).parent.parent / "data" / "fixtures"

ALL_FIXTURES = [
    "factura_frigicoll_split_1x1.json",
    "factura_varios_materiales.json",
    "presupuesto_mano_obra_desplazamiento.json",
    "presupuesto_con_ajustes.json",
    "presupuesto_completo_mixto.json",
]


def _load(filename: str):
    raw = json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))
    return normalize_supplier_json(raw)


# ---------------------------------------------------------------------------
# Carga y cálculo básico
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", ALL_FIXTURES)
def test_fixture_loads(filename):
    snap = _load(filename)
    assert snap is not None
    assert len(snap.lines) > 0


@pytest.mark.parametrize("filename", ALL_FIXTURES)
def test_fixture_calculates(filename):
    snap = _load(filename)
    calc = calculate_quote(snap)
    assert calc is not None
    assert len(calc.lines) == len(snap.lines)


@pytest.mark.parametrize("filename", ALL_FIXTURES)
def test_no_critical_warnings(filename):
    snap = _load(filename)
    calc = calculate_quote(snap)
    all_warnings = calc.warnings + [w for line in calc.lines for w in line.warnings]
    critical = [w for w in all_warnings if "error" in w.lower() or "crítico" in w.lower()]
    assert critical == [], f"Avisos críticos en {filename}: {critical}"


# ---------------------------------------------------------------------------
# Coherencia matemática de totales
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", ALL_FIXTURES)
def test_totals_coherence(filename):
    snap = _load(filename)
    calc = calculate_quote(snap)
    t = calc.totals

    sale_sum = sum(line.sale_total_without_tax for line in calc.lines)
    assert t.sale_subtotal == pytest.approx(sale_sum, abs=0.02)

    tax_sum = sum(line.tax_amount for line in calc.lines)
    assert t.tax_amount == pytest.approx(tax_sum, abs=0.02)

    cost_sum = sum(line.cost_total for line in calc.lines)
    assert t.cost_subtotal == pytest.approx(cost_sum, abs=0.02)

    assert t.final_total == pytest.approx(t.sale_subtotal + t.tax_amount, abs=0.02)


@pytest.mark.parametrize("filename", ALL_FIXTURES)
def test_gross_profit_not_negative_on_material_labor(filename):
    snap = _load(filename)
    calc = calculate_quote(snap)
    for line_snap, line_calc in zip(snap.lines, calc.lines):
        if line_snap.type in ("material", "labor", "travel"):
            assert line_calc.gross_profit >= -0.01, (
                f"Beneficio bruto negativo en línea '{line_snap.description}' "
                f"del fixture {filename}: {line_calc.gross_profit}"
            )


# ---------------------------------------------------------------------------
# Fixture: factura_frigicoll_split_1x1.json
# ---------------------------------------------------------------------------

class TestFrigicollFixture:
    def test_supplier_discount_40_5_applied(self):
        snap = _load("factura_frigicoll_split_1x1.json")
        calc = calculate_quote(snap)
        # Split 2.5kW: PVP=450, desc=40+5 → coste=450×0.60×0.95=256.50
        material = next(l for l, s in zip(calc.lines, snap.lines) if s.id == "fric-001")
        assert material.cost_unit == pytest.approx(256.50, abs=0.01)
        assert material.effective_supplier_discount == pytest.approx(43.0, abs=0.1)

    def test_apply_pass_supplier_discount_to_client(self):
        snap = _load("factura_frigicoll_split_1x1.json")
        snap2 = apply_command(snap, {
            "type": "apply_pass_supplier_discount_to_supplier",
            "supplier": "Frigicoll",
            "enabled": True,
        })
        calc_orig = calculate_quote(snap)
        calc_new = calculate_quote(snap2)
        # Con pass_to_client, la base de venta es el PVP bruto (450 / 520 / 8.50)
        # por tanto el precio de venta sube respecto al modo original (base=coste neto)
        for orig_line, new_line, snap_line in zip(calc_orig.lines, calc_new.lines, snap2.lines):
            if snap_line.type == "material" and snap_line.supplier == "Frigicoll":
                assert new_line.sale_unit_without_tax > orig_line.sale_unit_without_tax

    def test_labor_fixed_unit_45_per_hour(self):
        snap = _load("factura_frigicoll_split_1x1.json")
        calc = calculate_quote(snap)
        labor = next(l for l, s in zip(calc.lines, snap.lines) if s.id == "labor-001")
        assert labor.sale_unit_without_tax == pytest.approx(45.0, abs=0.01)
        assert labor.sale_total_without_tax == pytest.approx(45.0 * 12, abs=0.01)

    def test_travel_fixed_total_60(self):
        snap = _load("factura_frigicoll_split_1x1.json")
        calc = calculate_quote(snap)
        travel = next(l for l, s in zip(calc.lines, snap.lines) if s.id == "travel-001")
        assert travel.sale_total_without_tax == pytest.approx(60.0, abs=0.01)

    def test_holded_export(self):
        snap = _load("factura_frigicoll_split_1x1.json")
        calc = calculate_quote(snap)
        payload = export_holded_payload(snap, calc)
        assert payload["contactName"] == "Comunidad El Pinar"
        assert len(payload["items"]) == len(snap.lines)
        assert payload["totals"]["total"] == pytest.approx(calc.totals.final_total, abs=0.02)


# ---------------------------------------------------------------------------
# Fixture: factura_varios_materiales.json
# ---------------------------------------------------------------------------

class TestVariosMaterialesFixture:
    def test_three_suppliers_present(self):
        snap = _load("factura_varios_materiales.json")
        suppliers = {l.supplier for l in snap.lines if l.supplier}
        assert suppliers == {"Frigicoll", "Carrier", "MEG"}

    def test_apply_margin_to_frigicoll_only(self):
        snap = _load("factura_varios_materiales.json")
        snap2 = apply_command(snap, {
            "type": "apply_margin_to_supplier",
            "supplier": "Frigicoll",
            "margin": 40,
        })
        for line in snap2.lines:
            if line.supplier == "Frigicoll":
                assert line.margin == 40
            elif line.supplier in ("Carrier", "MEG"):
                # Sin tocar
                orig = next(l for l in snap.lines if l.id == line.id)
                assert line.margin == orig.margin

    def test_apply_margin_to_carrier_doesnt_affect_others(self):
        snap = _load("factura_varios_materiales.json")
        snap2 = apply_command(snap, {
            "type": "apply_margin_to_supplier",
            "supplier": "Carrier",
            "margin": 25,
        })
        calc = calculate_quote(snap2)
        for line_snap, line_calc in zip(snap2.lines, calc.lines):
            if line_snap.supplier == "Carrier":
                assert line_snap.margin == 25
            elif line_snap.type == "labor":
                # Labor sin margen de proveedor no se toca
                orig = next(l for l in snap.lines if l.id == line_snap.id)
                assert line_snap.margin == orig.margin

    def test_holded_export_has_all_lines(self):
        snap = _load("factura_varios_materiales.json")
        calc = calculate_quote(snap)
        payload = export_holded_payload(snap, calc)
        assert len(payload["items"]) == len(snap.lines)

    def test_total_is_positive(self):
        snap = _load("factura_varios_materiales.json")
        calc = calculate_quote(snap)
        assert calc.totals.final_total > 0


# ---------------------------------------------------------------------------
# Fixture: presupuesto_mano_obra_desplazamiento.json
# ---------------------------------------------------------------------------

class TestManoObraDesplazamientoFixture:
    def test_no_supplier_lines(self):
        snap = _load("presupuesto_mano_obra_desplazamiento.json")
        suppliers = [l.supplier for l in snap.lines if l.supplier]
        assert suppliers == []

    def test_all_lines_fixed_mode(self):
        snap = _load("presupuesto_mano_obra_desplazamiento.json")
        for line in snap.lines:
            assert line.sale_mode in ("fixed_unit", "fixed_total")

    def test_labor_sale_equals_fixed_value_times_qty(self):
        snap = _load("presupuesto_mano_obra_desplazamiento.json")
        calc = calculate_quote(snap)
        for line_snap, line_calc in zip(snap.lines, calc.lines):
            if line_snap.sale_mode == "fixed_unit":
                expected = (line_snap.sale_value or 0) * line_snap.quantity
                assert line_calc.sale_total_without_tax == pytest.approx(expected, abs=0.01)
            elif line_snap.sale_mode == "fixed_total":
                assert line_calc.sale_total_without_tax == pytest.approx(
                    line_snap.sale_value or 0, abs=0.01
                )

    def test_cost_subtotal_is_zero(self):
        # Sin precios de coste definidos, cost=0 (con aviso)
        snap = _load("presupuesto_mano_obra_desplazamiento.json")
        calc = calculate_quote(snap)
        assert calc.totals.cost_subtotal == pytest.approx(0.0, abs=0.01)

    def test_holded_export(self):
        snap = _load("presupuesto_mano_obra_desplazamiento.json")
        calc = calculate_quote(snap)
        payload = export_holded_payload(snap, calc)
        assert payload["contactName"] == "Talleres Roca S.L."
        assert payload["totals"]["total"] == pytest.approx(calc.totals.final_total, abs=0.02)


# ---------------------------------------------------------------------------
# Fixture: presupuesto_con_ajustes.json
# ---------------------------------------------------------------------------

class TestPresupuestoConAjustesFixture:
    def test_adjustment_lines_present(self):
        snap = _load("presupuesto_con_ajustes.json")
        adj_lines = [l for l in snap.lines if l.type == "adjustment"]
        assert len(adj_lines) == 2

    def test_negative_adjustment_reduces_total(self):
        snap = _load("presupuesto_con_ajustes.json")
        calc = calculate_quote(snap)
        adj = next(
            (l_c for l_s, l_c in zip(snap.lines, calc.lines)
             if l_s.id == "adj-002"),
            None,
        )
        assert adj is not None
        assert adj.sale_total_without_tax == pytest.approx(-250.0, abs=0.01)

    def test_positive_adjustment_adds_to_total(self):
        snap = _load("presupuesto_con_ajustes.json")
        calc = calculate_quote(snap)
        adj = next(
            (l_c for l_s, l_c in zip(snap.lines, calc.lines)
             if l_s.id == "adj-001"),
            None,
        )
        assert adj is not None
        assert adj.sale_total_without_tax == pytest.approx(150.0, abs=0.01)

    def test_final_total_includes_adjustments(self):
        snap = _load("presupuesto_con_ajustes.json")
        calc = calculate_quote(snap)
        # El total de venta incluye el ajuste positivo y el negativo
        net_adj = 150.0 - 250.0  # = -100
        material_lines = [
            l_c for l_s, l_c in zip(snap.lines, calc.lines)
            if l_s.type != "adjustment"
        ]
        material_subtotal = sum(l.sale_total_without_tax for l in material_lines)
        expected_sale = material_subtotal + net_adj
        assert calc.totals.sale_subtotal == pytest.approx(expected_sale, abs=0.02)

    def test_holded_export_includes_adjustments(self):
        snap = _load("presupuesto_con_ajustes.json")
        calc = calculate_quote(snap)
        payload = export_holded_payload(snap, calc)
        assert len(payload["items"]) == len(snap.lines)
        # El total del payload coincide con el calculado
        assert payload["totals"]["total"] == pytest.approx(calc.totals.final_total, abs=0.02)


# ---------------------------------------------------------------------------
# Fixture: presupuesto_completo_mixto.json
# ---------------------------------------------------------------------------

class TestPresupuestoCompletoMixtoFixture:
    def test_loads(self):
        snap = _load("presupuesto_completo_mixto.json")
        assert snap is not None
        assert len(snap.lines) == 10

    def test_calculates(self):
        snap = _load("presupuesto_completo_mixto.json")
        calc = calculate_quote(snap)
        assert len(calc.lines) == len(snap.lines)

    def test_totals_positive(self):
        snap = _load("presupuesto_completo_mixto.json")
        calc = calculate_quote(snap)
        assert calc.totals.final_total > 0
        assert calc.totals.sale_subtotal > 0

    def test_gross_profit_positive(self):
        snap = _load("presupuesto_completo_mixto.json")
        calc = calculate_quote(snap)
        assert calc.totals.gross_profit > 0

    def test_three_suppliers(self):
        snap = _load("presupuesto_completo_mixto.json")
        suppliers = {l.supplier for l in snap.lines if l.supplier}
        assert suppliers == {"Frigicoll", "Carrier", "MEG"}

    def test_frigicoll_chained_discount_40_5(self):
        snap = _load("presupuesto_completo_mixto.json")
        calc = calculate_quote(snap)
        # fri-001: PVP=520, desc=40+5 → coste=520×0.60×0.95=296.40
        line = next(l_c for l_s, l_c in zip(snap.lines, calc.lines) if l_s.id == "fri-001")
        assert line.cost_unit == pytest.approx(296.40, abs=0.01)
        assert line.effective_supplier_discount == pytest.approx(43.0, abs=0.1)

    def test_meg_net_cost_no_pvp(self):
        snap = _load("presupuesto_completo_mixto.json")
        calc = calculate_quote(snap)
        # meg-001: coste neto directo 186€, sin PVP ni descuentos
        line = next(l_c for l_s, l_c in zip(snap.lines, calc.lines) if l_s.id == "meg-001")
        assert line.cost_unit == pytest.approx(186.0, abs=0.01)
        assert line.effective_supplier_discount is None

    def test_specific_igic_line(self):
        snap = _load("presupuesto_completo_mixto.json")
        calc = calculate_quote(snap)
        # meg-002: IGIC=3% específico (no el 7% del header)
        line = next(l_c for l_s, l_c in zip(snap.lines, calc.lines) if l_s.id == "meg-002")
        assert line.tax_rate == pytest.approx(3.0, abs=0.01)

    def test_carrier_own_margin(self):
        snap = _load("presupuesto_completo_mixto.json")
        carr = next(l for l in snap.lines if l.id == "carr-001")
        assert carr.margin == 30  # margen propio, no el global 35

    def test_negative_adjustment_reduces_sale(self):
        snap = _load("presupuesto_completo_mixto.json")
        calc = calculate_quote(snap)
        adj = next(l_c for l_s, l_c in zip(snap.lines, calc.lines) if l_s.id == "adj-001")
        assert adj.sale_total_without_tax == pytest.approx(-400.0, abs=0.01)
        # El subtotal sin ajuste es mayor que el subtotal con ajuste
        subtotal_sin_adj = sum(
            l_c.sale_total_without_tax
            for l_s, l_c in zip(snap.lines, calc.lines)
            if l_s.type != "adjustment"
        )
        assert calc.totals.sale_subtotal == pytest.approx(subtotal_sin_adj - 400.0, abs=0.02)

    def test_apply_margin_to_frigicoll(self):
        snap = _load("presupuesto_completo_mixto.json")
        snap2 = apply_command(snap, {
            "type": "apply_margin_to_supplier",
            "supplier": "Frigicoll",
            "margin": 40,
        })
        calc_orig = calculate_quote(snap)
        calc_new = calculate_quote(snap2)
        # Venta de líneas Frigicoll sube con margen mayor
        for l_s, l_orig, l_new in zip(snap2.lines, calc_orig.lines, calc_new.lines):
            if l_s.supplier == "Frigicoll":
                assert l_new.sale_total_without_tax > l_orig.sale_total_without_tax
        # Carrier y MEG no se tocan
        for line in snap2.lines:
            if line.supplier in ("Carrier", "MEG"):
                orig = next(l for l in snap.lines if l.id == line.id)
                assert line.margin == orig.margin

    def test_apply_pass_discount_frigicoll_increases_sale_and_profit(self):
        snap = _load("presupuesto_completo_mixto.json")
        snap2 = apply_command(snap, {
            "type": "apply_pass_supplier_discount_to_supplier",
            "supplier": "Frigicoll",
            "enabled": True,
        })
        calc_orig = calculate_quote(snap)
        calc_new = calculate_quote(snap2)
        # Líneas Frigicoll con PVP: base de venta pasa de coste neto a PVP bruto → sube
        for l_s, l_orig, l_new in zip(snap2.lines, calc_orig.lines, calc_new.lines):
            if l_s.supplier == "Frigicoll" and l_s.supplier_gross_unit_price is not None:
                assert l_new.sale_total_without_tax > l_orig.sale_total_without_tax
                assert l_new.gross_profit > l_orig.gross_profit

    def test_holded_export_valid(self):
        snap = _load("presupuesto_completo_mixto.json")
        calc = calculate_quote(snap)
        payload = export_holded_payload(snap, calc)
        assert payload["contactName"] == "Comunidad de Propietarios Los Almendros"
        assert len(payload["items"]) == len(snap.lines)
        assert payload["totals"]["total"] == pytest.approx(calc.totals.final_total, abs=0.02)
        assert payload["totals"]["total"] > 0
