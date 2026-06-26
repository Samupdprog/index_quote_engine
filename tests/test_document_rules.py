"""Tests de reglas documentales obligatorias (v0.3)."""

from __future__ import annotations

import pytest

from quote_engine.calculator import calculate_quote
from quote_engine.config import BBVA_IBAN, BANK_ENTITY
from quote_engine.document_rules import (
    CONDICIONES_PAGO_TEXT,
    PROTECCION_DATOS_TEXT,
    build_default_conditions,
    detect_client_profile,
    ensure_required_document_sections,
    format_citanias_line,
    validate_document_rules,
)
from quote_engine.exporters.holded import export_holded_payload
from quote_engine.models import QuoteHeader, QuoteLine, QuoteSnapshot


# ─── Helpers ────────────────────────────────────────────────────────────────

def _snap(client_name: str | None = None, conditions: str | None = None) -> QuoteSnapshot:
    header = QuoteHeader(client_name=client_name, conditions=conditions)
    return QuoteSnapshot(header=header)


def _snap_with_line(client_name: str | None = None) -> QuoteSnapshot:
    header = QuoteHeader(client_name=client_name, global_margin=35.0, tax=7.0)
    lines = [
        QuoteLine(
            id="l1",
            description="Equipo test",
            quantity=1,
            supplier_gross_unit_price=100.0,
            supplier_discounts=[],
            sale_mode="margin",
            margin=35.0,
        )
    ]
    return QuoteSnapshot(header=header, lines=lines)


# ─── build_default_conditions ───────────────────────────────────────────────

class TestBuildDefaultConditions:
    def test_contains_proteccion_datos(self):
        result = build_default_conditions()
        assert "PROTECCIÓN DE DATOS" in result

    def test_contains_bbva(self):
        result = build_default_conditions()
        assert BANK_ENTITY in result

    def test_contains_iban(self):
        result = build_default_conditions()
        assert BBVA_IBAN in result

    def test_contains_transferencia(self):
        result = build_default_conditions()
        assert "Transferencia bancaria" in result


# ─── ensure_required_document_sections ─────────────────────────────────────

class TestEnsureRequiredDocumentSections:
    def test_adds_proteccion_when_missing(self):
        snap = _snap()
        result = ensure_required_document_sections(snap)
        assert "PROTECCIÓN DE DATOS" in result.header.conditions

    def test_adds_transferencia_when_missing(self):
        snap = _snap()
        result = ensure_required_document_sections(snap)
        assert "Transferencia bancaria" in result.header.conditions

    def test_adds_bbva_when_missing(self):
        snap = _snap()
        result = ensure_required_document_sections(snap)
        assert BANK_ENTITY in result.header.conditions

    def test_no_duplicate_proteccion(self):
        snap = _snap(conditions=PROTECCION_DATOS_TEXT)
        result = ensure_required_document_sections(snap)
        count = result.header.conditions.lower().count("protección de datos")
        assert count == 1

    def test_no_duplicate_bbva(self):
        snap = _snap(conditions=CONDICIONES_PAGO_TEXT)
        result = ensure_required_document_sections(snap)
        count = result.header.conditions.lower().count("bbva")
        assert count == 1

    def test_no_duplicate_when_both_present(self):
        full = build_default_conditions()
        snap = _snap(conditions=full)
        result = ensure_required_document_sections(snap)
        assert result is snap  # mismo objeto — no se modifica nada

    def test_does_not_mutate_original(self):
        snap = _snap()
        ensure_required_document_sections(snap)
        assert snap.header.conditions is None

    def test_preserves_existing_text(self):
        existing = "Texto previo del cliente."
        snap = _snap(conditions=existing)
        result = ensure_required_document_sections(snap)
        assert existing in result.header.conditions


# ─── validate_document_rules ────────────────────────────────────────────────

class TestValidateDocumentRules:
    def test_empty_conditions_returns_issues(self):
        snap = _snap()
        issues = validate_document_rules(snap)
        assert len(issues) > 0

    def test_missing_proteccion_reported(self):
        snap = _snap(conditions=CONDICIONES_PAGO_TEXT)
        issues = validate_document_rules(snap)
        assert any("protección" in i.lower() for i in issues)

    def test_missing_payment_reported(self):
        snap = _snap(conditions=PROTECCION_DATOS_TEXT)
        issues = validate_document_rules(snap)
        assert any("transferencia" in i.lower() or "iban" in i.lower() for i in issues)

    def test_full_conditions_no_issues(self):
        snap = _snap(conditions=build_default_conditions())
        issues = validate_document_rules(snap)
        assert issues == []


# ─── detect_client_profile ──────────────────────────────────────────────────

class TestDetectClientProfile:
    def test_detects_citanias_exact(self):
        snap = _snap(client_name="Citanias")
        assert detect_client_profile(snap) == "citanias"

    def test_detects_citanias_full_name(self):
        snap = _snap(client_name="Citanias Obras Y Servicios Slu")
        assert detect_client_profile(snap) == "citanias"

    def test_detects_citanias_case_insensitive(self):
        snap = _snap(client_name="CITANIAS OBRAS Y SERVICIOS SLU")
        assert detect_client_profile(snap) == "citanias"

    def test_normal_client_is_default(self):
        snap = _snap(client_name="Empresa Normal S.L.")
        assert detect_client_profile(snap) == "default"

    def test_none_client_is_default(self):
        snap = _snap(client_name=None)
        assert detect_client_profile(snap) == "default"

    def test_empty_string_is_default(self):
        snap = _snap(client_name="")
        assert detect_client_profile(snap) == "default"


# ─── format_citanias_line ───────────────────────────────────────────────────

class TestFormatCitaniasLine:
    def test_returns_concept_and_description(self):
        result = format_citanias_line(1, "MAD-001", "Madrid Centro", "Instalación Split", "Descripción detallada del alcance")
        assert "concept" in result
        assert "description" in result

    def test_concept_contains_all_parts(self):
        result = format_citanias_line("3", "BCN-005", "Barcelona", "Cambio filtros", "Alcance completo")
        assert "Intervención 3" in result["concept"]
        assert "Tienda BCN-005" in result["concept"]
        assert "Barcelona" in result["concept"]
        assert "Cambio filtros" in result["concept"]

    def test_description_set_correctly(self):
        result = format_citanias_line(2, "SEV-002", "Sevilla", "Revisión", "Descripción del trabajo")
        assert result["description"] == "Descripción del trabajo"


# ─── export_holded_payload incluye condiciones documentales ─────────────────

class TestExportHoldedPayloadDocumentRules:
    def test_notes_include_proteccion_datos(self):
        snap = _snap_with_line()
        calculated = calculate_quote(snap)
        payload = export_holded_payload(snap, calculated)
        assert payload["notes"] is not None
        assert "PROTECCIÓN DE DATOS" in payload["notes"]

    def test_notes_include_transferencia_bancaria(self):
        snap = _snap_with_line()
        calculated = calculate_quote(snap)
        payload = export_holded_payload(snap, calculated)
        assert "Transferencia bancaria" in payload["notes"]

    def test_notes_include_bbva(self):
        snap = _snap_with_line()
        calculated = calculate_quote(snap)
        payload = export_holded_payload(snap, calculated)
        assert BANK_ENTITY in payload["notes"]

    def test_no_duplicate_when_conditions_present(self):
        full = build_default_conditions()
        snap = _snap_with_line()
        snap = QuoteSnapshot(header=snap.header.model_copy(update={"conditions": full}), lines=snap.lines)
        calculated = calculate_quote(snap)
        payload = export_holded_payload(snap, calculated)
        assert payload["notes"].lower().count("protección de datos") == 1
        assert payload["notes"].lower().count("bbva") == 1

    def test_original_snapshot_not_mutated(self):
        snap = _snap_with_line()
        calculated = calculate_quote(snap)
        export_holded_payload(snap, calculated)
        assert snap.header.conditions is None
