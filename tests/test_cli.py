"""Tests de la CLI (v0.5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import quote_engine.storage as storage_module
from quote_cli.main import main


MINIMAL_SNAPSHOT = {
    "header": {
        "global_margin": 35,
        "tax": 7,
        "client_name": "Cliente Test CLI",
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
            "supplier_discounts": [40, 5],
            "sale_mode": "margin",
            "margin": 35,
            "pass_supplier_discount_to_client": False,
        }
    ],
}


@pytest.fixture(autouse=True)
def isolated_quotes_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirige QUOTES_DIR a un directorio temporal para cada test."""
    quotes_dir = tmp_path / "quotes"
    monkeypatch.setattr(storage_module, "QUOTES_DIR", quotes_dir)
    return quotes_dir


@pytest.fixture()
def snapshot_file(tmp_path: Path) -> Path:
    p = tmp_path / "snapshot.json"
    p.write_text(json.dumps(MINIMAL_SNAPSHOT), encoding="utf-8")
    return p


@pytest.fixture()
def saved_quote_id(snapshot_file: Path) -> str:
    rc = main(["save", str(snapshot_file)])
    assert rc == 0
    quotes = storage_module.list_quotes()
    return quotes[0]["quote_id"]


# ---------------------------------------------------------------------------
# 1. list funciona con carpeta vacía
# ---------------------------------------------------------------------------

def test_list_empty_directory(capsys: pytest.CaptureFixture) -> None:
    rc = main(["list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "No hay" in out


# ---------------------------------------------------------------------------
# 2. save guarda un presupuesto desde JSON
# ---------------------------------------------------------------------------

def test_save_creates_quote(snapshot_file: Path, capsys: pytest.CaptureFixture) -> None:
    rc = main(["save", str(snapshot_file)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Guardado:" in out
    quotes = storage_module.list_quotes()
    assert len(quotes) == 1


# ---------------------------------------------------------------------------
# 3. list muestra el presupuesto guardado
# ---------------------------------------------------------------------------

def test_list_shows_saved_quote(saved_quote_id: str, capsys: pytest.CaptureFixture) -> None:
    rc = main(["list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert saved_quote_id in out


# ---------------------------------------------------------------------------
# 4. show muestra metadata básica
# ---------------------------------------------------------------------------

def test_show_metadata(saved_quote_id: str, capsys: pytest.CaptureFixture) -> None:
    rc = main(["show", saved_quote_id])
    assert rc == 0
    out = capsys.readouterr().out
    assert saved_quote_id in out
    assert "Cliente Test CLI" in out


# ---------------------------------------------------------------------------
# 5. show --json devuelve JSON válido
# ---------------------------------------------------------------------------

def test_show_json(saved_quote_id: str, capsys: pytest.CaptureFixture) -> None:
    rc = main(["show", saved_quote_id, "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "metadata" in parsed
    assert "snapshot" in parsed


# ---------------------------------------------------------------------------
# 6. calculate muestra totales
# ---------------------------------------------------------------------------

def test_calculate_shows_totals(saved_quote_id: str, capsys: pytest.CaptureFixture) -> None:
    rc = main(["calculate", saved_quote_id])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Total cliente:" in out
    assert "Beneficio:" in out


# ---------------------------------------------------------------------------
# 7. calculate --json devuelve JSON válido
# ---------------------------------------------------------------------------

def test_calculate_json(saved_quote_id: str, capsys: pytest.CaptureFixture) -> None:
    rc = main(["calculate", saved_quote_id, "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "totals" in parsed
    assert "lines" in parsed


# ---------------------------------------------------------------------------
# 8. duplicate crea nuevo presupuesto
# ---------------------------------------------------------------------------

def test_duplicate_creates_new(saved_quote_id: str, capsys: pytest.CaptureFixture) -> None:
    rc = main(["duplicate", saved_quote_id])
    assert rc == 0
    out = capsys.readouterr().out
    assert "->" in out
    quotes = storage_module.list_quotes()
    assert len(quotes) == 2


# ---------------------------------------------------------------------------
# 9. archive cambia estado a archived
# ---------------------------------------------------------------------------

def test_archive_changes_status(saved_quote_id: str, capsys: pytest.CaptureFixture) -> None:
    rc = main(["archive", saved_quote_id])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Archivado" in out
    doc = storage_module.load_quote(saved_quote_id)
    assert doc["metadata"]["status"] == "archived"


# ---------------------------------------------------------------------------
# 10. export-holded genera JSON de Holded
# ---------------------------------------------------------------------------

def test_export_holded_json(saved_quote_id: str, capsys: pytest.CaptureFixture) -> None:
    rc = main(["export-holded", saved_quote_id, "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "items" in parsed
    assert "totals" in parsed


# ---------------------------------------------------------------------------
# 11. export-holded --output crea archivo
# ---------------------------------------------------------------------------

def test_export_holded_output_file(
    saved_quote_id: str, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    out_file = tmp_path / "holded.json"
    rc = main(["export-holded", saved_quote_id, "--output", str(out_file)])
    assert rc == 0
    assert out_file.exists()
    parsed = json.loads(out_file.read_text(encoding="utf-8"))
    assert "items" in parsed


# ---------------------------------------------------------------------------
# 12. ID peligroso con ../ falla
# ---------------------------------------------------------------------------

def test_show_path_traversal_fails(capsys: pytest.CaptureFixture) -> None:
    rc = main(["show", "../etc/passwd"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "Error" in err


# ---------------------------------------------------------------------------
# 13. Presupuesto inexistente devuelve error
# ---------------------------------------------------------------------------

def test_show_nonexistent_quote(capsys: pytest.CaptureFixture) -> None:
    rc = main(["show", "PRE-2099-9999"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "Error" in err


# ---------------------------------------------------------------------------
# Extras: save acepta formato completo {metadata, snapshot}
# ---------------------------------------------------------------------------

def test_save_accepts_full_doc_format(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    full_doc = {
        "metadata": {"id": "PRE-2026-0001", "status": "draft"},
        "snapshot": MINIMAL_SNAPSHOT,
    }
    p = tmp_path / "full_doc.json"
    p.write_text(json.dumps(full_doc), encoding="utf-8")
    rc = main(["save", str(p)])
    assert rc == 0


def test_save_with_tags_and_project_type(
    snapshot_file: Path, capsys: pytest.CaptureFixture
) -> None:
    rc = main([
        "save", str(snapshot_file),
        "--project-type", "climatizacion",
        "--tag", "split",
        "--tag", "vivienda",
        "--created-by", "Samuel",
    ])
    assert rc == 0
    quotes = storage_module.list_quotes(project_type="climatizacion")
    assert len(quotes) == 1
    assert "split" in quotes[0]["tags"]
    assert "vivienda" in quotes[0]["tags"]
