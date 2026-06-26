"""Tests de la API FastAPI."""

import pytest
from fastapi.testclient import TestClient

from quote_api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_import_quote():
    payload = {
        "supplier_json": [
            {
                "descripcion": "Split Daikin 1x1",
                "cantidad": 2,
                "proveedor": "Frigicoll",
                "pvpProveedor": 500,
                "descuentosProveedor": [40, 5],
                "margen": 35,
            }
        ],
        "defaults": {"global_margin": 35, "tax": 7},
    }
    r = client.post("/quotes/import", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "snapshot" in data
    assert "calculated" in data
    assert len(data["snapshot"]["lines"]) == 1


def test_calculate_quote():
    snap = {
        "header": {"global_margin": 35, "tax": 7, "include_tax": False},
        "lines": [
            {
                "id": "l1",
                "type": "material",
                "description": "Test",
                "quantity": 1,
                "unit": "ud",
                "supplier": "X",
                "supplier_gross_unit_price": 100,
                "supplier_discounts": [40, 5],
                "sale_mode": "margin",
                "margin": 35,
                "pass_supplier_discount_to_client": False,
                "supplier_discounts": [40, 5],
            }
        ],
    }
    r = client.post("/quotes/calculate", json={"snapshot": snap})
    assert r.status_code == 200
    calc = r.json()["calculated"]
    assert calc["lines"][0]["cost_unit"] == pytest.approx(57.0, abs=0.01)


def test_command_endpoint():
    snap = {
        "header": {"global_margin": 35, "tax": 7, "include_tax": False},
        "lines": [
            {
                "id": "l1",
                "type": "material",
                "description": "Test",
                "quantity": 1,
                "unit": "ud",
                "supplier": "Frigicoll",
                "supplier_gross_unit_price": 100,
                "supplier_discounts": [],
                "sale_mode": "margin",
                "margin": 35,
                "pass_supplier_discount_to_client": False,
            }
        ],
    }
    cmd = {"type": "set_global_margin", "margin": 50.0}
    r = client.post("/quotes/command", json={"snapshot": snap, "command": cmd})
    assert r.status_code == 200
    result = r.json()
    assert result["snapshot"]["header"]["global_margin"] == 50.0


def test_export_holded():
    snap = {
        "header": {
            "global_margin": 35,
            "tax": 7,
            "include_tax": False,
            "client_name": "Empresa Test",
        },
        "lines": [
            {
                "id": "l1",
                "type": "material",
                "description": "Equipo",
                "quantity": 1,
                "unit": "ud",
                "supplier_gross_unit_price": 100,
                "supplier_discounts": [],
                "sale_mode": "margin",
                "margin": 35,
                "pass_supplier_discount_to_client": False,
            }
        ],
    }
    r = client.post("/quotes/export/holded", json={"snapshot": snap})
    assert r.status_code == 200
    data = r.json()
    assert data["contactName"] == "Empresa Test"
    assert len(data["items"]) == 1
