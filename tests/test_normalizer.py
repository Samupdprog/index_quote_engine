"""Tests del normalizador de JSON de proveedor."""

import pytest

from quote_engine.normalizer import normalize_supplier_json, parse_json_with_recovery


RAW_LIST = [
    {
        "descripcion": "Split Daikin 1x1",
        "cantidad": 2,
        "proveedor": "Frigicoll",
        "pvpProveedor": 500,
        "descuentosProveedor": [40, 5],
        "margen": 35,
    }
]


def test_normalize_list_of_lines():
    snap = normalize_supplier_json(RAW_LIST)
    assert len(snap.lines) == 1
    line = snap.lines[0]
    assert line.description == "Split Daikin 1x1"
    assert line.quantity == 2.0
    assert line.supplier == "Frigicoll"
    assert line.supplier_gross_unit_price == 500.0
    assert line.supplier_discounts == [40, 5]
    assert line.margin == 35.0


def test_normalize_alias_descripcion():
    data = [{"descripcion": "Test", "cantidad": 1}]
    snap = normalize_supplier_json(data)
    assert snap.lines[0].description == "Test"


def test_normalize_alias_cantidad():
    data = [{"description": "X", "qty": 5}]
    snap = normalize_supplier_json(data)
    assert snap.lines[0].quantity == 5.0


def test_normalize_alias_pvpProveedor():
    data = [{"description": "X", "pvpProveedor": 200}]
    snap = normalize_supplier_json(data)
    assert snap.lines[0].supplier_gross_unit_price == 200.0


def test_normalize_alias_descuentosProveedor():
    data = [{"description": "X", "descuentosProveedor": [30]}]
    snap = normalize_supplier_json(data)
    assert snap.lines[0].supplier_discounts == [30.0]


def test_normalize_discounts_string_format():
    """Acepta descuentos como string '40+5'."""
    data = [{"description": "X", "descuentos": "40+5"}]
    snap = normalize_supplier_json(data)
    assert snap.lines[0].supplier_discounts == [40.0, 5.0]


def test_normalize_from_json_string():
    import json
    raw = json.dumps(RAW_LIST)
    snap = normalize_supplier_json(raw)
    assert len(snap.lines) == 1


def test_normalize_from_dict_with_lines():
    data = {
        "header": {"client_name": "Empresa X"},
        "lines": RAW_LIST,
    }
    snap = normalize_supplier_json(data)
    assert snap.header.client_name == "Empresa X"
    assert len(snap.lines) == 1


def test_normalize_defaults_applied():
    snap = normalize_supplier_json(
        [{"description": "X"}],
        defaults={"global_margin": 40, "tax": 10},
    )
    assert snap.header.global_margin == 40.0
    assert snap.header.tax == 10.0


def test_parse_json_with_recovery_removes_code_fences():
    raw = "```json\n[{\"description\": \"X\"}]\n```"
    result = parse_json_with_recovery(raw)
    assert isinstance(result, list)
    assert result[0]["description"] == "X"


def test_parse_json_with_recovery_trailing_comma():
    raw = '[{"a": 1,}]'
    result = parse_json_with_recovery(raw)
    assert result[0]["a"] == 1


def test_parse_invalid_json_raises():
    with pytest.raises(ValueError, match="JSON inválido"):
        parse_json_with_recovery("esto no es JSON {{{")
