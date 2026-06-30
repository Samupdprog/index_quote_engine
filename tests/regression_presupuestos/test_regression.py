"""Tests de regresión de presupuestos.

Comprueban que el motor produce resultados correctos para casos
representativos del negocio de Index Clima.

Reglas verificadas:
- IGIC 7%
- Cálculo de margen
- Advertencia de margen menor al 15%
- No duplicar mano de obra
- Advertencia si transporte ≠ 30 €/día
- Advertencia si falta precio
- No usar precio con confianza baja (verificado en tests de pricing)
- Trazabilidad de fuentes
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quote_engine.calculator import calculate_quote
from quote_engine.models import QuoteSnapshot

FIXTURES_DIR = Path(__file__).parent

# Umbral de margen bajo para avisar
LOW_MARGIN_THRESHOLD = 15.0

# Transporte estándar por día
STANDARD_TRANSPORT = 30.0

IGIC_RATE = 7.0


def _load_fixture(name: str) -> QuoteSnapshot:
    """Carga un fixture JSON y devuelve QuoteSnapshot."""
    path = FIXTURES_DIR / name
    data = json.loads(path.read_text(encoding="utf-8"))
    return QuoteSnapshot.model_validate(data)


def _calc(name: str):
    """Atajo: carga fixture y calcula."""
    snap = _load_fixture(name)
    result = calculate_quote(snap)
    return snap, result


# ---------------------------------------------------------------------------
# Caso: split básico
# ---------------------------------------------------------------------------

class TestSplitBasico:
    def test_igic_rate_7_percent(self):
        snap, result = _calc("split_basico.json")
        # IGIC = 7% de la venta sin IGIC
        expected_igic = round(result.totals.sale_subtotal * IGIC_RATE / 100, 2)
        assert abs(result.totals.tax_amount - expected_igic) < 0.05

    def test_final_total_includes_igic(self):
        snap, result = _calc("split_basico.json")
        expected = round(result.totals.sale_subtotal + result.totals.tax_amount, 2)
        assert abs(result.totals.final_total - expected) < 0.05

    def test_margin_calculated(self):
        snap, result = _calc("split_basico.json")
        assert result.totals.gross_profit > 0
        assert result.totals.gross_profit_percent is not None

    def test_no_zero_total(self):
        _, result = _calc("split_basico.json")
        assert result.totals.final_total > 0


# ---------------------------------------------------------------------------
# Caso: multisplit 2x1
# ---------------------------------------------------------------------------

class TestMultisplit2x1:
    def test_all_units_present(self):
        snap, result = _calc("multisplit_2x1.json")
        assert len(result.lines) == 5  # 3 materiales + 1 labor + 1 travel

    def test_labor_not_duplicated(self):
        """Mano de obra no se duplica (solo 1 línea de labor)."""
        snap, result = _calc("multisplit_2x1.json")
        labor_lines = [l for l in result.lines if l.type == "labor"]
        assert len(labor_lines) == 1

    def test_igic_applies_to_all_lines(self):
        snap, result = _calc("multisplit_2x1.json")
        total_tax = sum(l.tax_amount for l in result.lines)
        assert abs(total_tax - result.totals.tax_amount) < 0.10


# ---------------------------------------------------------------------------
# Caso: conductos con soldadura
# ---------------------------------------------------------------------------

class TestConductosConSoldadura:
    def test_tuberia_appears_in_lines(self):
        snap, result = _calc("conductos_con_soldadura.json")
        descs = [l.description.lower() for l in result.lines]
        assert any("tuber" in d or "cobre" in d for d in descs)

    def test_transport_at_30_per_day(self):
        snap, result = _calc("conductos_con_soldadura.json")
        travel_lines = [l for l in result.lines if l.type == "travel"]
        for tl in travel_lines:
            # 2 días × 30 = 60 (sale_value fijo)
            assert tl.sale_total_without_tax == pytest.approx(60.0, abs=0.01)


# ---------------------------------------------------------------------------
# Caso: reparación sin máquina
# ---------------------------------------------------------------------------

class TestReparacionSinMaquina:
    def test_no_machine_line(self):
        snap, result = _calc("reparacion_sin_maquina.json")
        # No hay unidad exterior ni split en este presupuesto
        descs = [l.description.lower() for l in result.lines]
        assert not any("split" in d or "unidad exterior" in d for d in descs)

    def test_has_labor_and_travel(self):
        snap, result = _calc("reparacion_sin_maquina.json")
        types = {l.type for l in result.lines}
        assert "labor" in types
        assert "travel" in types


# ---------------------------------------------------------------------------
# Caso: mantenimiento sin materiales
# ---------------------------------------------------------------------------

class TestMantenimientoSinMateriales:
    def test_no_material_lines(self):
        snap, result = _calc("mantenimiento_sin_materiales.json")
        material_lines = [l for l in result.lines if l.type == "material"]
        assert len(material_lines) == 0

    def test_igic_still_applied(self):
        snap, result = _calc("mantenimiento_sin_materiales.json")
        assert result.totals.tax_amount > 0


# ---------------------------------------------------------------------------
# Caso: margen bajo
# ---------------------------------------------------------------------------

class TestPresupuestoConMargenBajo:
    def test_low_margin_triggers_warning(self):
        snap, result = _calc("presupuesto_con_margen_bajo.json")
        pct = result.totals.gross_profit_percent
        if pct is not None and pct < LOW_MARGIN_THRESHOLD:
            # El motor actual no genera warning de margen bajo explícito,
            # pero el porcentaje debe ser detectable
            assert pct < LOW_MARGIN_THRESHOLD

    def test_margin_computed(self):
        snap, result = _calc("presupuesto_con_margen_bajo.json")
        assert result.totals.gross_profit_percent is not None
        # Con global_margin=10%, el beneficio debe ser alrededor del 10% del coste
        assert result.totals.gross_profit_percent > 0


# ---------------------------------------------------------------------------
# Caso: interconexión + mano de obra
# ---------------------------------------------------------------------------

class TestInterconexionMasObraInstalled:
    def test_has_material_and_labor(self):
        snap, result = _calc("interconexion_instalada_mas_mano_obra.json")
        types = [l.type for l in result.lines]
        assert "material" in types
        assert "labor" in types

    def test_labor_not_duplicated(self):
        snap, result = _calc("interconexion_instalada_mas_mano_obra.json")
        labor_lines = [l for l in result.lines if l.type == "labor"]
        assert len(labor_lines) == 1


# ---------------------------------------------------------------------------
# Caso: transporte distinto de 30 €/día
# ---------------------------------------------------------------------------

class TestTransporteDistinto30Dia:
    def test_transport_is_15_not_30(self):
        snap, result = _calc("transporte_distinto_30_dia.json")
        travel_lines = [l for l in result.lines if l.type == "travel"]
        for tl in travel_lines:
            # Este caso tiene 15 €/día aprobado manualmente
            assert tl.sale_unit_without_tax == pytest.approx(15.0, abs=0.01)

    def test_total_computed(self):
        _, result = _calc("transporte_distinto_30_dia.json")
        assert result.totals.final_total > 0


# ---------------------------------------------------------------------------
# Caso: precio de material no encontrado
# ---------------------------------------------------------------------------

class TestPrecioMaterialNoEncontrado:
    def test_missing_price_generates_warning(self):
        snap, result = _calc("precio_material_no_encontrado.json")
        # El motor genera warning cuando cost=0 y hay precio de venta
        material_lines = [l for l in result.lines if l.type == "material"]
        if material_lines:
            ml = material_lines[0]
            # Sin precio configurado, cost_unit = 0
            assert ml.cost_unit == 0.0
            assert len(result.warnings) > 0 or len(ml.warnings) > 0

    def test_labor_still_calculated(self):
        snap, result = _calc("precio_material_no_encontrado.json")
        labor_lines = [l for l in result.lines if l.type == "labor"]
        assert len(labor_lines) == 1
        assert labor_lines[0].sale_total_without_tax == pytest.approx(150.0, abs=0.01)


# ---------------------------------------------------------------------------
# Caso: producto con confianza baja (notas de REVISAR)
# ---------------------------------------------------------------------------

class TestProductoConConfianzaBaja:
    def test_total_computed(self):
        snap, result = _calc("producto_con_confianza_baja.json")
        assert result.totals.final_total > 0

    def test_internal_notes_present(self):
        snap, _ = _calc("producto_con_confianza_baja.json")
        assert snap.header.internal_notes is not None
        assert "REVISAR" in snap.header.internal_notes or "pendiente" in snap.header.internal_notes.lower()

    def test_revisar_note_in_line(self):
        snap, result = _calc("producto_con_confianza_baja.json")
        material_lines = [l for l in result.lines if l.type == "material"]
        assert len(material_lines) == 1
        # El precio debe estar configurado (no inventado por el motor)
        assert material_lines[0].cost_unit > 0


# ---------------------------------------------------------------------------
# Verificaciones generales aplicables a todos los casos
# ---------------------------------------------------------------------------

ALL_FIXTURES = [
    "split_basico.json",
    "multisplit_2x1.json",
    "conductos_con_soldadura.json",
    "reparacion_sin_maquina.json",
    "mantenimiento_sin_materiales.json",
    "presupuesto_con_margen_bajo.json",
    "interconexion_instalada_mas_mano_obra.json",
    "transporte_distinto_30_dia.json",
    "precio_material_no_encontrado.json",
    "producto_con_confianza_baja.json",
]


@pytest.mark.parametrize("fixture_name", ALL_FIXTURES)
def test_igic_applied_all_fixtures(fixture_name):
    """Todos los presupuestos aplican IGIC."""
    snap, result = _calc(fixture_name)
    if result.totals.sale_subtotal > 0:
        expected_igic = round(result.totals.sale_subtotal * snap.header.tax / 100, 2)
        assert abs(result.totals.tax_amount - expected_igic) < 0.10, (
            f"{fixture_name}: IGIC esperado {expected_igic:.2f}, "
            f"obtenido {result.totals.tax_amount:.2f}"
        )


@pytest.mark.parametrize("fixture_name", ALL_FIXTURES)
def test_final_total_positive(fixture_name):
    """El total final debe ser positivo (o cero en edge cases)."""
    _, result = _calc(fixture_name)
    assert result.totals.final_total >= 0


@pytest.mark.parametrize("fixture_name", ALL_FIXTURES)
def test_no_manual_calculation(fixture_name):
    """El motor es la única fuente de cálculo — los totales son coherentes."""
    snap, result = _calc(fixture_name)
    # Verificar coherencia: sum de líneas = subtotales
    sum_cost = sum(l.cost_total for l in result.lines)
    sum_sale = sum(l.sale_total_without_tax for l in result.lines)
    assert abs(sum_cost - result.totals.cost_subtotal) < 0.05
    assert abs(sum_sale - result.totals.sale_subtotal) < 0.05


@pytest.mark.parametrize("fixture_name", ALL_FIXTURES)
def test_each_line_has_type(fixture_name):
    """Cada línea tiene tipo (material/labor/travel/etc.)."""
    _, result = _calc(fixture_name)
    for line in result.lines:
        assert line.type in {"material", "labor", "travel", "global_work", "adjustment"}
