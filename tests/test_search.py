"""Tests de la búsqueda local de presupuestos (v0.7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import quote_engine.storage as storage_module
from quote_engine.models import QuoteSnapshot
from quote_engine.search import find_recent_quotes, search_quotes, summarize_search_results
from quote_api.main import app

api_client = TestClient(app)


# ---------------------------------------------------------------------------
# Snapshots de referencia
# ---------------------------------------------------------------------------

SNAP_ALPHA = {
    "header": {
        "global_margin": 35, "tax": 7, "include_tax": False,
        "client_name": "Empresa Alpha SL",
        "title": "Instalación split vivienda",
    },
    "lines": [
        {
            "id": "a1", "type": "material", "description": "Split Daikin 1x1",
            "quantity": 1, "unit": "ud", "supplier": "Frigicoll",
            "supplier_gross_unit_price": 500.0, "supplier_discounts": [40],
            "sale_mode": "margin", "margin": 35,
            "pass_supplier_discount_to_client": False,
        },
    ],
}

SNAP_BETA = {
    "header": {
        "global_margin": 40, "tax": 7, "include_tax": False,
        "client_name": "Beta Constructora",
        "title": "VRV Industrial Carrier",
    },
    "lines": [
        {
            "id": "b1", "type": "material", "description": "Bomba Calor Carrier 10kW",
            "quantity": 1, "unit": "ud", "supplier": "Carrier",
            "supplier_gross_unit_price": 1000.0, "supplier_discounts": [30],
            "sale_mode": "margin", "margin": 40,
            "pass_supplier_discount_to_client": False,
        },
    ],
}

SNAP_GAMMA = {
    "header": {
        "global_margin": 35, "tax": 7, "include_tax": False,
        "client_name": "Gamma SL",
        "title": "Proyecto climatización",
    },
    "lines": [
        {
            "id": "g1", "type": "material", "description": "Equipo sin coste",
            "quantity": 1, "unit": "ud",
            "sale_mode": "fixed_unit", "sale_value": 200.0,
        },
    ],
}

SNAP_DELTA = {
    "header": {
        "global_margin": 35, "tax": 7, "include_tax": False,
        "client_name": "Delta Corp",
        "title": "Obra con pérdida",
    },
    "lines": [
        {
            "id": "d1", "type": "material", "description": "Material costoso",
            "quantity": 1, "unit": "ud", "supplier": "Frigicoll",
            "supplier_gross_unit_price": 500.0, "supplier_discounts": [],
            "sale_mode": "fixed_total", "sale_value": 200.0,
        },
    ],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_quotes_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    quotes_dir = tmp_path / "quotes"
    monkeypatch.setattr(storage_module, "QUOTES_DIR", quotes_dir)
    return quotes_dir


@pytest.fixture()
def four_quotes() -> tuple[str, str, str, str]:
    """Guarda 4 presupuestos con características distintas y devuelve sus IDs."""
    snap_a = QuoteSnapshot.model_validate(SNAP_ALPHA)
    id_a = storage_module.save_quote(snap_a, created_by="test")
    storage_module.update_quote_metadata(id_a, {
        "project_type": "climatizacion", "tags": ["split", "vivienda"],
        "status": "draft",
    })

    snap_b = QuoteSnapshot.model_validate(SNAP_BETA)
    id_b = storage_module.save_quote(snap_b, created_by="test")
    storage_module.update_quote_metadata(id_b, {
        "project_type": "industrial", "tags": ["vrv", "carrier"],
        "status": "accepted",
    })

    snap_g = QuoteSnapshot.model_validate(SNAP_GAMMA)
    id_g = storage_module.save_quote(snap_g, created_by="test")
    storage_module.update_quote_metadata(id_g, {
        "project_type": "climatizacion", "tags": ["bomba"],
        "status": "draft",
    })

    snap_d = QuoteSnapshot.model_validate(SNAP_DELTA)
    id_d = storage_module.save_quote(snap_d, created_by="test")
    storage_module.update_quote_metadata(id_d, {
        "project_type": "residencial", "tags": [],
        "status": "sent",
    })

    return (id_a, id_b, id_g, id_d)


# ---------------------------------------------------------------------------
# 1. Búsqueda vacía
# ---------------------------------------------------------------------------

def test_search_empty_dir() -> None:
    results = search_quotes()
    assert results == []


# ---------------------------------------------------------------------------
# 2. Búsqueda por cliente
# ---------------------------------------------------------------------------

def test_search_by_client(four_quotes: tuple) -> None:
    results = search_quotes(client_name="Alpha")
    assert len(results) == 1
    assert results[0]["client_name"] == "Empresa Alpha SL"


# ---------------------------------------------------------------------------
# 3. Búsqueda por proveedor
# ---------------------------------------------------------------------------

def test_search_by_supplier(four_quotes: tuple) -> None:
    results = search_quotes(supplier="Frigicoll")
    ids_found = {r["id"] for r in results}
    id_a, _, _, id_d = four_quotes
    assert id_a in ids_found
    assert id_d in ids_found


def test_search_by_supplier_partial(four_quotes: tuple) -> None:
    results = search_quotes(supplier="carri")
    assert len(results) == 1
    assert results[0]["client_name"] == "Beta Constructora"


# ---------------------------------------------------------------------------
# 4. Texto libre en descripción de línea
# ---------------------------------------------------------------------------

def test_search_query_finds_line_description(four_quotes: tuple) -> None:
    results = search_quotes(query="Daikin")
    assert any("Alpha" in r["client_name"] for r in results)


def test_search_query_case_insensitive(four_quotes: tuple) -> None:
    results = search_quotes(query="daikin")
    assert any("Alpha" in r["client_name"] for r in results)


def test_search_query_finds_in_title(four_quotes: tuple) -> None:
    results = search_quotes(query="VRV Industrial")
    assert any("Beta" in r["client_name"] for r in results)


# ---------------------------------------------------------------------------
# 5. Búsqueda por status
# ---------------------------------------------------------------------------

def test_search_by_status(four_quotes: tuple) -> None:
    results = search_quotes(status="accepted")
    assert len(results) == 1
    assert results[0]["status"] == "accepted"


# ---------------------------------------------------------------------------
# 6. Búsqueda por project_type
# ---------------------------------------------------------------------------

def test_search_by_project_type(four_quotes: tuple) -> None:
    results = search_quotes(project_type="climatizacion")
    assert len(results) == 2


# ---------------------------------------------------------------------------
# 7. Búsqueda por tag
# ---------------------------------------------------------------------------

def test_search_by_tag(four_quotes: tuple) -> None:
    results = search_quotes(tag="split")
    assert len(results) == 1
    assert "split" in results[0]["tags"]


def test_search_by_tag_case_insensitive(four_quotes: tuple) -> None:
    results = search_quotes(tag="VRV")
    assert len(results) == 1


# ---------------------------------------------------------------------------
# 8. Filtro min_profit
# ---------------------------------------------------------------------------

def test_search_min_profit(four_quotes: tuple) -> None:
    # Beta tiene beneficio ~466 €, Alpha ~161 €
    results = search_quotes(min_profit=300)
    assert all(r["gross_profit"] >= 300 for r in results)


# ---------------------------------------------------------------------------
# 9. Filtro max_profit
# ---------------------------------------------------------------------------

def test_search_max_profit(four_quotes: tuple) -> None:
    results = search_quotes(max_profit=300)
    assert all(r["gross_profit"] <= 300 for r in results)


# ---------------------------------------------------------------------------
# 10. Filtro min_total
# ---------------------------------------------------------------------------

def test_search_min_total(four_quotes: tuple) -> None:
    # Beta final_total ~1248 €
    results = search_quotes(min_total=1000)
    assert all(r["final_total"] >= 1000 for r in results)
    assert any("Beta" in r["client_name"] for r in results)


# ---------------------------------------------------------------------------
# 11. Filtro max_total
# ---------------------------------------------------------------------------

def test_search_max_total(four_quotes: tuple) -> None:
    results = search_quotes(max_total=600)
    assert all(r["final_total"] <= 600 for r in results)


# ---------------------------------------------------------------------------
# 12. Filtro has_warnings
# ---------------------------------------------------------------------------

def test_search_has_warnings_no_match(four_quotes: tuple) -> None:
    # Ninguno de los 4 snapshots debería generar warnings del motor
    results = search_quotes(has_warnings=True)
    assert all(r["warnings_count"] > 0 for r in results)


# ---------------------------------------------------------------------------
# 13. Filtro has_problems
# ---------------------------------------------------------------------------

def test_search_has_problems_true(four_quotes: tuple) -> None:
    results = search_quotes(has_problems=True)
    assert all(r["problems_count"] > 0 for r in results)
    # Gamma (coste 0) y Delta (beneficio negativo) deben aparecer
    clients = {r["client_name"] for r in results}
    assert "Gamma SL" in clients
    assert "Delta Corp" in clients


def test_search_has_problems_false(four_quotes: tuple) -> None:
    results = search_quotes(has_problems=False)
    assert all(r["problems_count"] == 0 for r in results)


# ---------------------------------------------------------------------------
# 14. Recent devuelve por updated_at
# ---------------------------------------------------------------------------

def test_find_recent_quotes(four_quotes: tuple) -> None:
    results = find_recent_quotes(limit=10)
    assert len(results) == 4
    # Debe estar ordenado por updated_at descendente
    dates = [r["updated_at"] for r in results if r["updated_at"]]
    assert dates == sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# 15. Límite de resultados
# ---------------------------------------------------------------------------

def test_search_limit(four_quotes: tuple) -> None:
    results = search_quotes(limit=2)
    assert len(results) == 2


def test_recent_limit(four_quotes: tuple) -> None:
    results = find_recent_quotes(limit=2)
    assert len(results) == 2


# ---------------------------------------------------------------------------
# 16. Ordenación por gross_profit
# ---------------------------------------------------------------------------

def test_search_sort_by_gross_profit(four_quotes: tuple) -> None:
    results = search_quotes(sort_by="gross_profit", descending=True)
    profits = [r["gross_profit"] for r in results]
    assert profits == sorted(profits, reverse=True)


# ---------------------------------------------------------------------------
# 17. Ordenación asc/desc
# ---------------------------------------------------------------------------

def test_search_sort_ascending(four_quotes: tuple) -> None:
    results = search_quotes(sort_by="final_total", descending=False)
    totals = [r["final_total"] for r in results]
    assert totals == sorted(totals)


def test_search_sort_descending(four_quotes: tuple) -> None:
    results = search_quotes(sort_by="final_total", descending=True)
    totals = [r["final_total"] for r in results]
    assert totals == sorted(totals, reverse=True)


# ---------------------------------------------------------------------------
# summarize_search_results
# ---------------------------------------------------------------------------

def test_summarize_empty() -> None:
    assert "No se encontraron" in summarize_search_results([])


def test_summarize_one() -> None:
    r = summarize_search_results([{"id": "x"}])
    assert "1 presupuesto" in r


def test_summarize_many() -> None:
    r = summarize_search_results([{"id": "x"}, {"id": "y"}])
    assert "2 presupuestos" in r


# ---------------------------------------------------------------------------
# Resumen contiene campos esperados
# ---------------------------------------------------------------------------

def test_search_result_structure(four_quotes: tuple) -> None:
    results = search_quotes()
    assert len(results) == 4
    for r in results:
        assert "id" in r
        assert "client_name" in r
        assert "status" in r
        assert "final_total" in r
        assert "gross_profit" in r
        assert "gross_profit_percent" in r
        assert "suppliers" in r
        assert "supplier_count" in r
        assert "line_count" in r
        assert "warnings_count" in r
        assert "problems_count" in r
        assert "report_status" in r


# ---------------------------------------------------------------------------
# API: GET /storage/search
# ---------------------------------------------------------------------------

def test_api_search_empty(isolated_quotes_dir: Path) -> None:
    r = api_client.get("/storage/search")
    assert r.status_code == 200
    data = r.json()
    assert data["results"] == []
    assert data["total"] == 0


def test_api_search_by_client(four_quotes: tuple) -> None:
    r = api_client.get("/storage/search", params={"client": "Alpha"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["results"][0]["client_name"] == "Empresa Alpha SL"


def test_api_search_by_supplier(four_quotes: tuple) -> None:
    r = api_client.get("/storage/search", params={"supplier": "Carrier"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1


def test_api_search_by_status(four_quotes: tuple) -> None:
    r = api_client.get("/storage/search", params={"status": "accepted"})
    assert r.status_code == 200
    data = r.json()
    assert all(res["status"] == "accepted" for res in data["results"])


def test_api_search_text_query(four_quotes: tuple) -> None:
    r = api_client.get("/storage/search", params={"q": "Daikin"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1


def test_api_search_with_limit(four_quotes: tuple) -> None:
    r = api_client.get("/storage/search", params={"limit": 2})
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) == 2


# ---------------------------------------------------------------------------
# API: GET /storage/recent
# ---------------------------------------------------------------------------

def test_api_recent_empty(isolated_quotes_dir: Path) -> None:
    r = api_client.get("/storage/recent")
    assert r.status_code == 200
    data = r.json()
    assert data["results"] == []
    assert data["total"] == 0


def test_api_recent_returns_quotes(four_quotes: tuple) -> None:
    r = api_client.get("/storage/recent")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 4


def test_api_recent_with_limit(four_quotes: tuple) -> None:
    r = api_client.get("/storage/recent", params={"limit": 2})
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) == 2
    assert data["total"] == 2
