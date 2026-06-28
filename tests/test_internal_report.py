"""Tests del informe interno HTML (v0.6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quote_engine.exporters.internal_report import (
    build_internal_report,
    build_internal_report_html,
    export_internal_report_dict,
    get_report_status,
    save_internal_report_html,
)
from quote_engine.calculator import calculate_quote
from quote_engine.models import QuoteSnapshot


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def snap_two_suppliers() -> QuoteSnapshot:
    return QuoteSnapshot.model_validate({
        "header": {
            "global_margin": 35,
            "tax": 7,
            "client_name": "Empresa Test S.L.",
            "include_tax": False,
            "internal_notes": "Nota interna de prueba",
        },
        "lines": [
            {
                "id": "l1",
                "type": "material",
                "description": "Split Daikin 1x1",
                "quantity": 1,
                "unit": "ud",
                "supplier": "Frigicoll",
                "supplier_gross_unit_price": 500.0,
                "supplier_discounts": [40, 5],
                "sale_mode": "margin",
                "margin": 35,
                "pass_supplier_discount_to_client": False,
            },
            {
                "id": "l2",
                "type": "material",
                "description": "Bomba de calor Carrier",
                "quantity": 1,
                "unit": "ud",
                "supplier": "Carrier",
                "supplier_gross_unit_price": 1200.0,
                "supplier_discounts": [32],
                "sale_mode": "margin",
                "margin": 35,
                "pass_supplier_discount_to_client": False,
            },
            {
                "id": "l3",
                "type": "labor",
                "description": "Mano de obra",
                "quantity": 8,
                "unit": "h",
                "sale_mode": "fixed_unit",
                "sale_value": 45.0,
            },
        ],
    })


@pytest.fixture()
def snap_with_problems() -> QuoteSnapshot:
    """Snapshot con una línea de coste 0 y otra con beneficio negativo."""
    return QuoteSnapshot.model_validate({
        "header": {
            "global_margin": 35,
            "tax": 7,
            "client_name": "Test Problemas",
            "include_tax": False,
        },
        "lines": [
            {
                "id": "l1",
                "type": "material",
                "description": "Línea sin coste",
                "quantity": 1,
                "unit": "ud",
                "sale_mode": "fixed_unit",
                "sale_value": 50.0,
            },
            {
                "id": "l2",
                "type": "material",
                "description": "Línea negativa",
                "quantity": 1,
                "unit": "ud",
                "supplier": "Proveedor X",
                "supplier_gross_unit_price": 200.0,
                "supplier_discounts": [],
                "sale_mode": "fixed_total",
                "sale_value": 100.0,
            },
        ],
    })


# ---------------------------------------------------------------------------
# 1. Genera informe interno dict
# ---------------------------------------------------------------------------

def test_build_internal_report_dict(snap_two_suppliers: QuoteSnapshot) -> None:
    report = build_internal_report(snap_two_suppliers)
    assert "header" in report
    assert "totals" in report
    assert "lines" in report
    assert "supplier_summary" in report
    assert "problems" in report
    assert "warnings" in report


# ---------------------------------------------------------------------------
# 2. Genera HTML válido
# ---------------------------------------------------------------------------

def test_build_internal_report_html_is_valid(snap_two_suppliers: QuoteSnapshot) -> None:
    html = build_internal_report_html(snap_two_suppliers)
    assert html.strip().startswith("<!DOCTYPE html>")
    assert "</html>" in html


# ---------------------------------------------------------------------------
# 3. HTML contiene cliente
# ---------------------------------------------------------------------------

def test_html_contains_client(snap_two_suppliers: QuoteSnapshot) -> None:
    html = build_internal_report_html(snap_two_suppliers)
    assert "Empresa Test S.L." in html


# ---------------------------------------------------------------------------
# 4. HTML contiene total cliente
# ---------------------------------------------------------------------------

def test_html_contains_total_cliente(snap_two_suppliers: QuoteSnapshot) -> None:
    html = build_internal_report_html(snap_two_suppliers)
    assert "Total cliente" in html


# ---------------------------------------------------------------------------
# 5. HTML contiene beneficio
# ---------------------------------------------------------------------------

def test_html_contains_beneficio(snap_two_suppliers: QuoteSnapshot) -> None:
    html = build_internal_report_html(snap_two_suppliers)
    assert "Beneficio" in html


# ---------------------------------------------------------------------------
# 6. HTML contiene resumen por proveedor
# ---------------------------------------------------------------------------

def test_html_contains_supplier_summary(snap_two_suppliers: QuoteSnapshot) -> None:
    html = build_internal_report_html(snap_two_suppliers)
    assert "Frigicoll" in html
    assert "Carrier" in html
    assert "Resumen por proveedor" in html


# ---------------------------------------------------------------------------
# 7. HTML contiene tabla de líneas
# ---------------------------------------------------------------------------

def test_html_contains_line_table(snap_two_suppliers: QuoteSnapshot) -> None:
    html = build_internal_report_html(snap_two_suppliers)
    assert "Split Daikin 1x1" in html
    assert "Bomba de calor Carrier" in html
    assert "Mano de obra" in html
    assert "Líneas" in html


# ---------------------------------------------------------------------------
# 8. HTML contiene warnings si existen
# ---------------------------------------------------------------------------

def test_html_no_warnings_when_clean(snap_two_suppliers: QuoteSnapshot) -> None:
    html = build_internal_report_html(snap_two_suppliers)
    # Sin problemas no debe mostrar la sección de problemas detectados
    report = build_internal_report(snap_two_suppliers)
    if not report["problems"] and not report["warnings"]:
        assert "Problemas detectados" not in html


def test_html_shows_warnings_when_present(snap_with_problems: QuoteSnapshot) -> None:
    html = build_internal_report_html(snap_with_problems)
    # Debe haber alguna señal de problema (coste 0 o beneficio negativo)
    assert "coste 0" in html or "negativo" in html or "⚠" in html


# ---------------------------------------------------------------------------
# 9. Detecta línea con coste 0
# ---------------------------------------------------------------------------

def test_detects_zero_cost_line(snap_with_problems: QuoteSnapshot) -> None:
    report = build_internal_report(snap_with_problems)
    issues = [p["issue"] for p in report["problems"]]
    assert any("coste 0" in i for i in issues)


# ---------------------------------------------------------------------------
# 10. Detecta línea con beneficio negativo
# ---------------------------------------------------------------------------

def test_detects_negative_profit_line(snap_with_problems: QuoteSnapshot) -> None:
    report = build_internal_report(snap_with_problems)
    issues = [p["issue"] for p in report["problems"]]
    assert any("negativo" in i for i in issues)


# ---------------------------------------------------------------------------
# 11. Resumen por proveedor agrupa correctamente
# ---------------------------------------------------------------------------

def test_supplier_summary_groups(snap_two_suppliers: QuoteSnapshot) -> None:
    report = build_internal_report(snap_two_suppliers)
    summary = report["supplier_summary"]
    names = [s["supplier"] for s in summary]
    assert "Frigicoll" in names
    assert "Carrier" in names
    # Mano de obra sin proveedor -> "(sin proveedor)"
    assert "(sin proveedor)" in names
    for s in summary:
        assert s["line_count"] >= 1
        assert "cost_total" in s
        assert "profit" in s


# ---------------------------------------------------------------------------
# 12. save_internal_report_html crea archivo
# ---------------------------------------------------------------------------

def test_save_internal_report_html(snap_two_suppliers: QuoteSnapshot, tmp_path: Path) -> None:
    out = tmp_path / "report.html"
    result = save_internal_report_html(snap_two_suppliers, out)
    assert Path(result).exists()
    content = Path(result).read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "Empresa Test S.L." in content


# ---------------------------------------------------------------------------
# 13. HTML incluye notas internas si existen
# ---------------------------------------------------------------------------

def test_html_includes_internal_notes(snap_two_suppliers: QuoteSnapshot) -> None:
    html = build_internal_report_html(snap_two_suppliers)
    assert "Nota interna de prueba" in html


# ---------------------------------------------------------------------------
# 14. HTML incluye metadata si se pasa
# ---------------------------------------------------------------------------

def test_html_includes_metadata() -> None:
    snap = QuoteSnapshot.model_validate({
        "header": {"global_margin": 35, "tax": 7, "include_tax": False, "client_name": "X"},
        "lines": [],
    })
    meta = {"id": "PRE-2026-0001", "status": "draft", "tags": ["split"]}
    html = build_internal_report_html(snap, metadata=meta)
    assert "PRE-2026-0001" in html
    assert "draft" in html


# ---------------------------------------------------------------------------
# 15. Compatibilidad: export_internal_report_dict sigue funcionando
# ---------------------------------------------------------------------------

def test_export_internal_report_dict_compat(snap_two_suppliers: QuoteSnapshot) -> None:
    calculated = calculate_quote(snap_two_suppliers)
    report = export_internal_report_dict(snap_two_suppliers, calculated)
    assert "header" in report
    assert "totals" in report
    assert "lines" in report
    assert len(report["lines"]) == 3


# ---------------------------------------------------------------------------
# v0.6.1 — tests nuevos
# ---------------------------------------------------------------------------

def test_html_title_prioritizes_metadata_id() -> None:
    """El título H1 debe usar metadata.id aunque exista quote_number."""
    snap = QuoteSnapshot.model_validate({
        "header": {
            "global_margin": 35, "tax": 7, "include_tax": False,
            "client_name": "X", "quote_number": "PRE-2026-0001",
        },
        "lines": [],
    })
    meta = {"id": "PRE-TEST-REPORT", "status": "draft"}
    html = build_internal_report_html(snap, metadata=meta)
    # El h1 debe contener el metadata.id
    assert "Informe Interno — PRE-TEST-REPORT" in html


def test_html_shows_metadata_id(snap_two_suppliers: QuoteSnapshot) -> None:
    meta = {"id": "PRE-TEST-REPORT", "status": "draft"}
    html = build_internal_report_html(snap_two_suppliers, metadata=meta)
    assert "PRE-TEST-REPORT" in html


def test_html_shows_quote_number_if_present() -> None:
    """Si header.quote_number existe, debe aparecer como 'Número presupuesto'."""
    snap = QuoteSnapshot.model_validate({
        "header": {
            "global_margin": 35, "tax": 7, "include_tax": False,
            "client_name": "Comunidad Las Mimosas", "quote_number": "PRE-2026-0001",
        },
        "lines": [],
    })
    meta = {"id": "PRE-TEST-REPORT", "status": "draft"}
    html = build_internal_report_html(snap, metadata=meta)
    assert "Número presupuesto" in html
    assert "PRE-2026-0001" in html


def test_html_no_quote_number_section_when_absent() -> None:
    """Si no hay quote_number, no debe aparecer la línea de número presupuesto."""
    snap = QuoteSnapshot.model_validate({
        "header": {"global_margin": 35, "tax": 7, "include_tax": False, "client_name": "X"},
        "lines": [],
    })
    html = build_internal_report_html(snap, metadata={"id": "PRE-TEST-001"})
    assert "Número presupuesto" not in html


def test_warnings_not_duplicated_in_problems() -> None:
    """Los warnings del motor NO deben aparecer dentro de 'Problemas detectados'."""
    snap = QuoteSnapshot.model_validate({
        "header": {"global_margin": 35, "tax": 7, "include_tax": False},
        "lines": [
            {
                "id": "l1", "type": "material", "description": "Línea sin coste",
                "quantity": 1, "unit": "ud",
                "sale_mode": "fixed_unit", "sale_value": 50.0,
            },
        ],
    })
    report = build_internal_report(snap)
    # Los problems solo deben ser los estructurales (coste 0, etc.)
    # No deben contener entradas con prefijo "warning:"
    problem_issues = [p["issue"] for p in report["problems"]]
    assert not any(i.startswith("warning:") for i in problem_issues)


def test_zero_cost_still_detected_as_problem() -> None:
    """Coste 0 sigue siendo detectado como problema (no afectado por el cambio)."""
    snap = QuoteSnapshot.model_validate({
        "header": {"global_margin": 35, "tax": 7, "include_tax": False},
        "lines": [
            {
                "id": "l1", "type": "material", "description": "Sin coste",
                "quantity": 1, "unit": "ud",
                "sale_mode": "fixed_unit", "sale_value": 50.0,
            },
        ],
    })
    report = build_internal_report(snap)
    issues = [p["issue"] for p in report["problems"]]
    assert any("coste 0" in i for i in issues)


# ---------------------------------------------------------------------------
# v0.6.2 — semáforo, resumen humano y recomendaciones
# ---------------------------------------------------------------------------

def test_report_ok_when_no_problems() -> None:
    """Presupuesto sin problemas → semáforo OK."""
    snap = QuoteSnapshot.model_validate({
        "header": {"global_margin": 35, "tax": 7, "include_tax": False, "client_name": "Clean"},
        "lines": [
            {
                "id": "l1", "type": "material", "description": "Split limpio",
                "quantity": 1, "unit": "ud",
                "supplier": "Frigicoll",
                "supplier_gross_unit_price": 500.0,
                "supplier_discounts": [40],
                "sale_mode": "margin", "margin": 35,
                "pass_supplier_discount_to_client": False,
            },
        ],
    })
    report = build_internal_report(snap)
    rs = report["report_status"]
    assert rs["status"] == "ok"
    assert rs["label"] == "OK"


def test_report_danger_negative_profit() -> None:
    """Presupuesto con beneficio total negativo → semáforo PELIGRO."""
    snap = QuoteSnapshot.model_validate({
        "header": {"global_margin": 35, "tax": 7, "include_tax": False},
        "lines": [
            {
                "id": "l1", "type": "material", "description": "Línea negativa",
                "quantity": 1, "unit": "ud",
                "supplier": "X",
                "supplier_gross_unit_price": 300.0,
                "supplier_discounts": [],
                "sale_mode": "fixed_total",
                "sale_value": 100.0,
            },
        ],
    })
    report = build_internal_report(snap)
    rs = report["report_status"]
    assert rs["status"] == "danger"
    assert rs["label"] == "PELIGRO"


def test_report_review_when_zero_cost() -> None:
    """Presupuesto con coste 0 (y sin beneficio negativo) → semáforo REVISAR."""
    snap = QuoteSnapshot.model_validate({
        "header": {"global_margin": 35, "tax": 7, "include_tax": False},
        "lines": [
            {
                "id": "l1", "type": "material", "description": "Sin coste",
                "quantity": 1, "unit": "ud",
                "sale_mode": "fixed_unit", "sale_value": 50.0,
            },
        ],
    })
    report = build_internal_report(snap)
    rs = report["report_status"]
    assert rs["status"] == "review"
    assert rs["label"] == "REVISAR"


def test_get_report_status_standalone(snap_with_problems: QuoteSnapshot) -> None:
    """get_report_status funciona con un report dict."""
    report = build_internal_report(snap_with_problems)
    rs = get_report_status(report)
    assert rs["status"] in ("ok", "review", "danger")
    assert "label" in rs
    assert "reason" in rs


def test_build_internal_report_has_new_fields(snap_two_suppliers: QuoteSnapshot) -> None:
    """build_internal_report devuelve los tres nuevos campos."""
    report = build_internal_report(snap_two_suppliers)
    assert "report_status" in report
    assert "human_summary" in report
    assert "review_recommendations" in report
    assert isinstance(report["human_summary"], list)
    assert isinstance(report["review_recommendations"], list)


def test_human_summary_contains_total(snap_two_suppliers: QuoteSnapshot) -> None:
    """El resumen humano menciona el total cliente."""
    report = build_internal_report(snap_two_suppliers)
    joined = " ".join(report["human_summary"])
    assert "total cliente" in joined.lower() or "€" in joined


def test_review_recommendations_empty_when_ok(snap_two_suppliers: QuoteSnapshot) -> None:
    """Sin problemas, review_recommendations está vacío."""
    report = build_internal_report(snap_two_suppliers)
    if report["report_status"]["status"] == "ok":
        assert report["review_recommendations"] == []


def test_review_recommendations_nonempty_with_problems(snap_with_problems: QuoteSnapshot) -> None:
    """Con problemas detectados, review_recommendations no está vacío."""
    report = build_internal_report(snap_with_problems)
    assert len(report["review_recommendations"]) > 0


def test_html_contains_status_badge(snap_two_suppliers: QuoteSnapshot) -> None:
    """El HTML contiene el badge de semáforo."""
    html = build_internal_report_html(snap_two_suppliers)
    assert "status-badge" in html
    assert any(label in html for label in ("OK", "REVISAR", "PELIGRO"))


def test_html_contains_cards(snap_two_suppliers: QuoteSnapshot) -> None:
    """El HTML contiene la sección de tarjetas."""
    html = build_internal_report_html(snap_two_suppliers)
    assert "cards" in html
    assert "card-label" in html
    assert "card-value" in html


def test_html_contains_resumen_rapido(snap_two_suppliers: QuoteSnapshot) -> None:
    """El HTML contiene la sección Resumen rápido."""
    html = build_internal_report_html(snap_two_suppliers)
    assert "Resumen rápido" in html


def test_html_contains_que_revisar(snap_two_suppliers: QuoteSnapshot) -> None:
    """El HTML contiene la sección Qué revisar."""
    html = build_internal_report_html(snap_two_suppliers)
    assert "Qué revisar" in html
