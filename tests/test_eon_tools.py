"""Tests de las herramientas EON (v0.8)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import quote_engine.storage as storage_module
from quote_engine.eon_tools import (
    eon_apply_commands,
    eon_archive_quote,
    eon_calculate_quote,
    eon_duplicate_quote,
    eon_export_holded_payload,
    eon_generate_internal_report,
    eon_get_quote,
    eon_search_quotes,
    eon_summarize_quote,
    list_eon_tools,
)
from quote_engine.models import QuoteSnapshot
from quote_api.main import app

api_client = TestClient(app)

MINIMAL_SNAP = {
    "header": {
        "global_margin": 35,
        "tax": 7,
        "client_name": "EON Test Client",
        "include_tax": False,
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
            "supplier_discounts": [40],
            "sale_mode": "margin",
            "margin": 35,
            "pass_supplier_discount_to_client": False,
        }
    ],
}


@pytest.fixture(autouse=True)
def isolated_quotes_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    quotes_dir = tmp_path / "quotes"
    monkeypatch.setattr(storage_module, "QUOTES_DIR", quotes_dir)
    return quotes_dir


@pytest.fixture()
def saved_id() -> str:
    snap = QuoteSnapshot.model_validate(MINIMAL_SNAP)
    return storage_module.save_quote(snap, created_by="test")


# ---------------------------------------------------------------------------
# 1. list_eon_tools
# ---------------------------------------------------------------------------

def test_list_eon_tools_nonempty() -> None:
    tools = list_eon_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0
    for t in tools:
        assert "name" in t
        assert "description" in t


# ---------------------------------------------------------------------------
# 2. eon_search_quotes
# ---------------------------------------------------------------------------

def test_eon_search_quotes_empty() -> None:
    result = eon_search_quotes()
    assert result["ok"] is True
    assert result["data"]["total"] == 0


def test_eon_search_quotes_finds(saved_id: str) -> None:
    result = eon_search_quotes({"client_name": "EON Test"})
    assert result["ok"] is True
    assert result["data"]["total"] == 1


def test_eon_search_quotes_bad_filter(saved_id: str) -> None:
    # filtros desconocidos se ignoran, no rompen
    result = eon_search_quotes({"campo_inexistente": "valor"})
    assert result["ok"] is True


# ---------------------------------------------------------------------------
# 3. eon_get_quote
# ---------------------------------------------------------------------------

def test_eon_get_quote_ok(saved_id: str) -> None:
    result = eon_get_quote(saved_id)
    assert result["ok"] is True
    assert result["quote_id"] == saved_id
    assert "metadata" in result["data"]
    assert "snapshot" in result["data"]


# ---------------------------------------------------------------------------
# 4. eon_get_quote — error claro
# ---------------------------------------------------------------------------

def test_eon_get_quote_not_found() -> None:
    result = eon_get_quote("PRE-9999-9999")
    assert result["ok"] is False
    assert "error" in result
    assert "quote_id" in result


# ---------------------------------------------------------------------------
# 5. eon_summarize_quote
# ---------------------------------------------------------------------------

def test_eon_summarize_quote_ok(saved_id: str) -> None:
    result = eon_summarize_quote(saved_id)
    assert result["ok"] is True
    d = result["data"]
    assert "final_total" in d
    assert "gross_profit" in d
    assert "human_summary" in d
    assert "review_recommendations" in d
    assert "report_status" in d
    assert isinstance(d["human_summary"], list)


def test_eon_summarize_quote_not_found() -> None:
    result = eon_summarize_quote("PRE-0000-0000")
    assert result["ok"] is False


# ---------------------------------------------------------------------------
# 6. eon_calculate_quote
# ---------------------------------------------------------------------------

def test_eon_calculate_quote_ok(saved_id: str) -> None:
    result = eon_calculate_quote(saved_id)
    assert result["ok"] is True
    assert "totals" in result["data"]
    assert "lines" in result["data"]
    assert result["data"]["totals"]["final_total"] > 0


def test_eon_calculate_quote_not_found() -> None:
    result = eon_calculate_quote("PRE-0000-0001")
    assert result["ok"] is False


# ---------------------------------------------------------------------------
# 7. eon_duplicate_quote
# ---------------------------------------------------------------------------

def test_eon_duplicate_quote_ok(saved_id: str) -> None:
    result = eon_duplicate_quote(saved_id)
    assert result["ok"] is True
    new_id = result["result_quote_id"]
    assert new_id != saved_id
    quotes = storage_module.list_quotes()
    assert len(quotes) == 2


def test_eon_duplicate_quote_not_found() -> None:
    result = eon_duplicate_quote("PRE-0000-0002")
    assert result["ok"] is False


# ---------------------------------------------------------------------------
# 8. eon_apply_commands — dry_run
# ---------------------------------------------------------------------------

def test_eon_apply_commands_dry_run(saved_id: str) -> None:
    cmds = [{"type": "set_global_margin", "margin": 40}]
    result = eon_apply_commands(saved_id, cmds, save_mode="dry_run")
    assert result["ok"] is True
    assert result["save_mode"] == "dry_run"
    assert result["result_quote_id"] is None
    # No debe crear nuevos presupuestos
    assert len(storage_module.list_quotes()) == 1


# ---------------------------------------------------------------------------
# 9. eon_apply_commands — copy
# ---------------------------------------------------------------------------

def test_eon_apply_commands_copy(saved_id: str) -> None:
    cmds = [{"type": "set_global_margin", "margin": 40}]
    result = eon_apply_commands(saved_id, cmds, save_mode="copy")
    assert result["ok"] is True
    assert result["save_mode"] == "copy"
    new_id = result["result_quote_id"]
    assert new_id != saved_id
    assert len(storage_module.list_quotes()) == 2


# ---------------------------------------------------------------------------
# 10. eon_apply_commands — overwrite
# ---------------------------------------------------------------------------

def test_eon_apply_commands_overwrite(saved_id: str) -> None:
    cmds = [{"type": "set_global_margin", "margin": 40}]
    result = eon_apply_commands(saved_id, cmds, save_mode="overwrite")
    assert result["ok"] is True
    assert result["result_quote_id"] == saved_id
    # Sigue siendo solo 1
    assert len(storage_module.list_quotes()) == 1


# ---------------------------------------------------------------------------
# 11. eon_apply_commands — comando inválido
# ---------------------------------------------------------------------------

def test_eon_apply_commands_invalid_command(saved_id: str) -> None:
    cmds = [{"type": "comando_que_no_existe"}]
    result = eon_apply_commands(saved_id, cmds, save_mode="dry_run")
    assert result["ok"] is False
    assert "error" in result


def test_eon_apply_commands_invalid_save_mode(saved_id: str) -> None:
    cmds = [{"type": "set_global_margin", "margin": 40}]
    result = eon_apply_commands(saved_id, cmds, save_mode="invalid_mode")
    assert result["ok"] is False


# ---------------------------------------------------------------------------
# 12. eon_generate_internal_report — dict
# ---------------------------------------------------------------------------

def test_eon_generate_internal_report_dict(saved_id: str) -> None:
    result = eon_generate_internal_report(saved_id, html=False)
    assert result["ok"] is True
    assert "totals" in result["data"]
    assert "lines" in result["data"]
    assert "problems" in result["data"]


# ---------------------------------------------------------------------------
# 13. eon_generate_internal_report — html
# ---------------------------------------------------------------------------

def test_eon_generate_internal_report_html(saved_id: str) -> None:
    result = eon_generate_internal_report(saved_id, html=True)
    assert result["ok"] is True
    html = result["data"]["html"]
    assert "<!DOCTYPE html>" in html
    assert "EON Test Client" in html


def test_eon_generate_internal_report_html_to_file(saved_id: str, tmp_path: Path) -> None:
    out = tmp_path / "report.html"
    result = eon_generate_internal_report(saved_id, html=True, output_path=str(out))
    assert result["ok"] is True
    assert out.exists()
    assert "output_path" in result["data"]


# ---------------------------------------------------------------------------
# 14. eon_export_holded_payload
# ---------------------------------------------------------------------------

def test_eon_export_holded_payload_ok(saved_id: str) -> None:
    result = eon_export_holded_payload(saved_id)
    assert result["ok"] is True
    payload = result["data"]["payload"]
    assert "items" in payload
    assert "totals" in payload


def test_eon_export_holded_payload_to_file(saved_id: str, tmp_path: Path) -> None:
    out = tmp_path / "holded.json"
    result = eon_export_holded_payload(saved_id, output_path=str(out))
    assert result["ok"] is True
    assert out.exists()
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert "items" in parsed


def test_eon_export_holded_payload_not_found() -> None:
    result = eon_export_holded_payload("PRE-0000-0003")
    assert result["ok"] is False


# ---------------------------------------------------------------------------
# 15. eon_archive_quote
# ---------------------------------------------------------------------------

def test_eon_archive_quote_ok(saved_id: str) -> None:
    result = eon_archive_quote(saved_id)
    assert result["ok"] is True
    doc = storage_module.load_quote(saved_id)
    assert doc["metadata"]["status"] == "archived"


def test_eon_archive_quote_not_found() -> None:
    result = eon_archive_quote("PRE-0000-0004")
    assert result["ok"] is False


# ---------------------------------------------------------------------------
# 16. API /eon/tools
# ---------------------------------------------------------------------------

def test_api_eon_tools() -> None:
    r = api_client.get("/eon/tools")
    assert r.status_code == 200
    data = r.json()
    assert "tools" in data
    assert data["total"] > 0


# ---------------------------------------------------------------------------
# 17. API /eon/search
# ---------------------------------------------------------------------------

def test_api_eon_search_empty(isolated_quotes_dir: Path) -> None:
    r = api_client.get("/eon/search")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["data"]["total"] == 0


def test_api_eon_search_with_quotes(saved_id: str) -> None:
    r = api_client.get("/eon/search", params={"client_name": "EON Test"})
    assert r.status_code == 200
    data = r.json()
    assert data["data"]["total"] == 1


# ---------------------------------------------------------------------------
# 18. API /eon/quotes/{id}/summary
# ---------------------------------------------------------------------------

def test_api_eon_summary_ok(saved_id: str) -> None:
    r = api_client.get(f"/eon/quotes/{saved_id}/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "final_total" in data["data"]
    assert "human_summary" in data["data"]


def test_api_eon_summary_not_found(isolated_quotes_dir: Path) -> None:
    r = api_client.get("/eon/quotes/PRE-9999-9999/summary")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 19. API /eon/quotes/{id}/commands
# ---------------------------------------------------------------------------

def test_api_eon_commands_dry_run(saved_id: str) -> None:
    body = {
        "commands": [{"type": "set_global_margin", "margin": 40}],
        "save_mode": "dry_run",
    }
    r = api_client.post(f"/eon/quotes/{saved_id}/commands", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["save_mode"] == "dry_run"


def test_api_eon_commands_copy(saved_id: str) -> None:
    body = {
        "commands": [{"type": "set_global_margin", "margin": 38}],
        "save_mode": "copy",
    }
    r = api_client.post(f"/eon/quotes/{saved_id}/commands", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["result_quote_id"] != saved_id


# ---------------------------------------------------------------------------
# 20. CLI eon-tools
# ---------------------------------------------------------------------------

def test_cli_eon_tools(capsys: pytest.CaptureFixture) -> None:
    from quote_cli.main import main
    rc = main(["eon-tools"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Herramientas EON" in out
    assert "eon_search_quotes" in out


# ---------------------------------------------------------------------------
# 21. CLI eon-summary
# ---------------------------------------------------------------------------

def test_cli_eon_summary(saved_id: str, capsys: pytest.CaptureFixture) -> None:
    from quote_cli.main import main
    rc = main(["eon-summary", saved_id])
    assert rc == 0
    out = capsys.readouterr().out
    assert "EON Test Client" in out
    assert "Total cliente:" in out


def test_cli_eon_summary_json(saved_id: str, capsys: pytest.CaptureFixture) -> None:
    from quote_cli.main import main
    rc = main(["eon-summary", saved_id, "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["ok"] is True


def test_cli_eon_summary_not_found(capsys: pytest.CaptureFixture) -> None:
    from quote_cli.main import main
    rc = main(["eon-summary", "PRE-9999-9999"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "Error" in err
