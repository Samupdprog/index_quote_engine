"""Tests del parser de intención."""

import pytest
from eon.intent_parser import parse_intent


def test_detect_search_intent():
    intent = parse_intent("busca presupuestos de Citanias")
    assert intent.action == "search_quotes"
    assert intent.client_name == "Citanias"


def test_detect_summarize_intent():
    intent = parse_intent("resúmeme PRE-2026-0001")
    assert intent.action == "summarize_quote"
    assert intent.quote_id == "PRE-2026-0001"


def test_detect_generate_report_intent():
    intent = parse_intent("genera informe de PRE-2026-0001")
    assert intent.action == "generate_report"
    assert intent.quote_id == "PRE-2026-0001"


def test_detect_export_holded_intent():
    intent = parse_intent("exporta a Holded PRE-2026-0001")
    assert intent.action == "export_holded"
    assert intent.quote_id == "PRE-2026-0001"


def test_detect_archive_intent():
    intent = parse_intent("archiva PRE-2026-0001")
    assert intent.action == "archive_quote"
    assert intent.quote_id == "PRE-2026-0001"


def test_detect_create_intent():
    intent = parse_intent("hazme un presupuesto para Citanias")
    assert intent.action == "create_quote"
    assert intent.client_name == "Citanias"


def test_extract_quote_id_varied_format():
    intent = parse_intent("resúmeme PRE-EON-TEST")
    assert intent.quote_id == "PRE-EON-TEST"


def test_extract_quote_id_uppercase_normalization():
    intent = parse_intent("resúmeme pre-2026-0002")
    assert intent.quote_id == "PRE-2026-0002"


def test_missing_quote_id_in_summarize():
    intent = parse_intent("resúmeme el presupuesto")
    assert intent.action == "summarize_quote"
    assert "quote_id" in intent.missing_fields


def test_missing_quote_id_in_report():
    intent = parse_intent("genera el informe")
    assert intent.action == "generate_report"
    assert "quote_id" in intent.missing_fields


def test_unknown_intent():
    intent = parse_intent("hola qué tal")
    assert intent.action == "unknown"
