"""Tests del flujo de trabajo completo (v0.9)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import quote_engine.storage as storage_module
from quote_engine.workflow import run_quote_workflow
from quote_api.main import app

api_client = TestClient(app)

MINIMAL_SNAP = {
    "header": {
        "global_margin": 35,
        "tax": 7,
        "client_name": "Workflow Test Client",
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

FULL_DOC = {
    "metadata": {
        "id": "PRE-TEST-WORKFLOW",
        "status": "draft",
        "project_type": "climatizacion",
        "tags": ["test"],
    },
    "snapshot": MINIMAL_SNAP,
}


@pytest.fixture(autouse=True)
def isolated_quotes_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    quotes_dir = tmp_path / "quotes"
    monkeypatch.setattr(storage_module, "QUOTES_DIR", quotes_dir)
    return quotes_dir


@pytest.fixture()
def snap_file(tmp_path: Path) -> Path:
    p = tmp_path / "snap.json"
    p.write_text(json.dumps(MINIMAL_SNAP), encoding="utf-8")
    return p


@pytest.fixture()
def full_doc_file(tmp_path: Path) -> Path:
    p = tmp_path / "full_doc.json"
    p.write_text(json.dumps(FULL_DOC), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 1. Carga JSON de entrada
# ---------------------------------------------------------------------------

def test_workflow_loads_json(snap_file: Path, tmp_path: Path) -> None:
    result = run_quote_workflow(
        str(snap_file),
        generate_report=False,
        export_holded=False,
    )
    assert result["ok"] is True
    assert result["steps"]["loaded_input"] is True


def test_workflow_loads_full_doc_format(full_doc_file: Path) -> None:
    result = run_quote_workflow(
        str(full_doc_file),
        generate_report=False,
        export_holded=False,
    )
    assert result["ok"] is True
    assert result["steps"]["loaded_input"] is True


# ---------------------------------------------------------------------------
# 2. Guardado de presupuesto
# ---------------------------------------------------------------------------

def test_workflow_saves_quote(snap_file: Path) -> None:
    result = run_quote_workflow(
        str(snap_file),
        generate_report=False,
        export_holded=False,
    )
    assert result["ok"] is True
    assert result["steps"]["saved_quote"] is True
    quotes = storage_module.list_quotes()
    assert len(quotes) == 1


def test_workflow_uses_explicit_id(snap_file: Path) -> None:
    result = run_quote_workflow(
        str(snap_file),
        quote_id="PRE-WF-0001",
        generate_report=False,
        export_holded=False,
    )
    assert result["ok"] is True
    assert result["quote_id"] == "PRE-WF-0001"


# ---------------------------------------------------------------------------
# 3. Cálculo
# ---------------------------------------------------------------------------

def test_workflow_calculates_totals(snap_file: Path) -> None:
    result = run_quote_workflow(
        str(snap_file),
        generate_report=False,
        export_holded=False,
    )
    assert result["ok"] is True
    assert result["steps"]["calculated"] is True
    s = result["summary"]
    assert s["final_total"] > 0
    assert s["gross_profit"] > 0


# ---------------------------------------------------------------------------
# 4. Resumen EON
# ---------------------------------------------------------------------------

def test_workflow_generates_summary(snap_file: Path) -> None:
    result = run_quote_workflow(
        str(snap_file),
        generate_report=False,
        export_holded=False,
    )
    assert result["ok"] is True
    assert result["steps"]["summary_generated"] is True
    s = result["summary"]
    assert "human_summary" in s
    assert "review_recommendations" in s
    assert "report_label" in s
    assert s["client_name"] == "Workflow Test Client"


# ---------------------------------------------------------------------------
# 5. Informe HTML
# ---------------------------------------------------------------------------

def test_workflow_generates_html_report(snap_file: Path, tmp_path: Path) -> None:
    report_path = tmp_path / "report.html"
    result = run_quote_workflow(
        str(snap_file),
        generate_report=True,
        export_holded=False,
        report_output_path=str(report_path),
    )
    assert result["ok"] is True
    assert result["steps"]["report_generated"] is True
    assert result["report_path"] == str(report_path)
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "Workflow Test Client" in content


# ---------------------------------------------------------------------------
# 6. Payload Holded
# ---------------------------------------------------------------------------

def test_workflow_exports_holded(snap_file: Path, tmp_path: Path) -> None:
    holded_path = tmp_path / "holded.json"
    result = run_quote_workflow(
        str(snap_file),
        generate_report=False,
        export_holded=True,
        holded_output_path=str(holded_path),
    )
    assert result["ok"] is True
    assert result["steps"]["holded_payload_exported"] is True
    assert result["holded_path"] == str(holded_path)
    assert holded_path.exists()
    payload = json.loads(holded_path.read_text(encoding="utf-8"))
    assert "items" in payload
    assert "totals" in payload


# ---------------------------------------------------------------------------
# 7. --no-report
# ---------------------------------------------------------------------------

def test_workflow_no_report(snap_file: Path, tmp_path: Path) -> None:
    result = run_quote_workflow(
        str(snap_file),
        generate_report=False,
        export_holded=False,
    )
    assert result["ok"] is True
    assert result["steps"]["report_generated"] is False
    assert result["report_path"] is None


# ---------------------------------------------------------------------------
# 8. --no-holded
# ---------------------------------------------------------------------------

def test_workflow_no_holded(snap_file: Path) -> None:
    result = run_quote_workflow(
        str(snap_file),
        generate_report=False,
        export_holded=False,
    )
    assert result["ok"] is True
    assert result["steps"]["holded_payload_exported"] is False
    assert result["holded_path"] is None


# ---------------------------------------------------------------------------
# 9. Archivo inexistente → error claro
# ---------------------------------------------------------------------------

def test_workflow_missing_file() -> None:
    result = run_quote_workflow(
        "ruta/que/no/existe.json",
        generate_report=False,
        export_holded=False,
    )
    assert result["ok"] is False
    assert "error" in result
    assert "no encontrado" in result["error"].lower()


# ---------------------------------------------------------------------------
# 10. JSON inválido → error claro
# ---------------------------------------------------------------------------

def test_workflow_invalid_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("esto no es json {{{{", encoding="utf-8")
    result = run_quote_workflow(
        str(bad),
        generate_report=False,
        export_holded=False,
    )
    assert result["ok"] is False
    assert "error" in result


# ---------------------------------------------------------------------------
# 11. CLI workflow
# ---------------------------------------------------------------------------

def test_cli_workflow_text(snap_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    from quote_cli.main import main
    report_path = tmp_path / "r.html"
    holded_path = tmp_path / "h.json"
    rc = main([
        "workflow", str(snap_file),
        "--report-output", str(report_path),
        "--holded-output", str(holded_path),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Workflow completado" in out
    assert "Total cliente:" in out


# ---------------------------------------------------------------------------
# 12. CLI workflow --json
# ---------------------------------------------------------------------------

def test_cli_workflow_json(snap_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    from quote_cli.main import main
    report_path = tmp_path / "r.html"
    holded_path = tmp_path / "h.json"
    rc = main([
        "workflow", str(snap_file),
        "--report-output", str(report_path),
        "--holded-output", str(holded_path),
        "--json",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["ok"] is True
    assert "quote_id" in parsed
    assert "summary" in parsed


# ---------------------------------------------------------------------------
# 13. CLI workflow crea archivo HTML
# ---------------------------------------------------------------------------

def test_cli_workflow_creates_html(snap_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    from quote_cli.main import main
    report_path = tmp_path / "report.html"
    holded_path = tmp_path / "h.json"
    rc = main([
        "workflow", str(snap_file),
        "--report-output", str(report_path),
        "--holded-output", str(holded_path),
    ])
    assert rc == 0
    assert report_path.exists()
    assert "<!DOCTYPE html>" in report_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 14. CLI workflow crea payload Holded
# ---------------------------------------------------------------------------

def test_cli_workflow_creates_holded(snap_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    from quote_cli.main import main
    report_path = tmp_path / "r.html"
    holded_path = tmp_path / "holded.json"
    rc = main([
        "workflow", str(snap_file),
        "--report-output", str(report_path),
        "--holded-output", str(holded_path),
    ])
    assert rc == 0
    assert holded_path.exists()
    payload = json.loads(holded_path.read_text(encoding="utf-8"))
    assert "items" in payload


# ---------------------------------------------------------------------------
# 15. API /workflow/quote
# ---------------------------------------------------------------------------

def test_api_workflow_quote(snap_file: Path, tmp_path: Path) -> None:
    report_path = tmp_path / "r.html"
    holded_path = tmp_path / "h.json"
    body = {
        "input_path": str(snap_file),
        "created_by": "test",
        "source": "api_test",
        "generate_report": True,
        "export_holded": True,
        "report_output_path": str(report_path),
        "holded_output_path": str(holded_path),
    }
    r = api_client.post("/workflow/quote", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "quote_id" in data
    assert "summary" in data


def test_api_workflow_quote_missing_file(isolated_quotes_dir: Path) -> None:
    body = {
        "input_path": "no_existe.json",
        "generate_report": False,
        "export_holded": False,
    }
    r = api_client.post("/workflow/quote", json=body)
    assert r.status_code == 422


def test_api_workflow_no_report_no_holded(snap_file: Path) -> None:
    body = {
        "input_path": str(snap_file),
        "generate_report": False,
        "export_holded": False,
    }
    r = api_client.post("/workflow/quote", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["steps"]["report_generated"] is False
    assert data["steps"]["holded_payload_exported"] is False
