"""Tests del módulo de almacenamiento local (v0.4)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

import quote_engine.storage as storage_module
from quote_engine.models import QuoteSnapshot
from quote_engine.storage import (
    archive_quote,
    duplicate_quote,
    generate_quote_id,
    list_quotes,
    load_quote,
    save_quote,
    update_quote_metadata,
)


# ---------------------------------------------------------------------------
# Fixture: snapshot mínimo reutilizable
# ---------------------------------------------------------------------------

@pytest.fixture()
def minimal_snapshot() -> QuoteSnapshot:
    return QuoteSnapshot.model_validate({
        "header": {
            "global_margin": 35,
            "tax": 7,
            "client_name": "Cliente Test",
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
    })


@pytest.fixture(autouse=True)
def isolated_quotes_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirige QUOTES_DIR a un directorio temporal para cada test."""
    quotes_dir = tmp_path / "quotes"
    monkeypatch.setattr(storage_module, "QUOTES_DIR", quotes_dir)
    return quotes_dir


# ---------------------------------------------------------------------------
# 1. Guarda un presupuesto y crea archivo JSON
# ---------------------------------------------------------------------------

def test_save_creates_json_file(minimal_snapshot: QuoteSnapshot, tmp_path: Path) -> None:
    quote_id = save_quote(minimal_snapshot)
    quotes_dir = storage_module.QUOTES_DIR
    expected_path = quotes_dir / f"{quote_id}.json"
    assert expected_path.exists(), f"No se creó el archivo {expected_path}"
    doc = json.loads(expected_path.read_text(encoding="utf-8"))
    assert "metadata" in doc
    assert "snapshot" in doc


# ---------------------------------------------------------------------------
# 2. Carga el presupuesto guardado
# ---------------------------------------------------------------------------

def test_load_returns_saved_quote(minimal_snapshot: QuoteSnapshot) -> None:
    quote_id = save_quote(minimal_snapshot)
    doc = load_quote(quote_id)
    assert doc["metadata"]["id"] == quote_id
    assert doc["snapshot"]["header"]["client_name"] == "Cliente Test"


# ---------------------------------------------------------------------------
# 3. Añade metadata si falta (snapshot sin metadata previa)
# ---------------------------------------------------------------------------

def test_save_adds_metadata_automatically(minimal_snapshot: QuoteSnapshot) -> None:
    quote_id = save_quote(minimal_snapshot, created_by="EON", source="api")
    doc = load_quote(quote_id)
    meta = doc["metadata"]
    assert meta["created_by"] == "EON"
    assert meta["source"] == "api"
    assert meta["status"] == "draft"
    assert meta["version"] == "0.4"
    assert "created_at" in meta
    assert "updated_at" in meta


# ---------------------------------------------------------------------------
# 4. Conserva created_at al actualizar
# ---------------------------------------------------------------------------

def test_created_at_preserved_on_update(minimal_snapshot: QuoteSnapshot) -> None:
    quote_id = save_quote(minimal_snapshot)
    doc_first = load_quote(quote_id)
    created_at_first = doc_first["metadata"]["created_at"]

    time.sleep(1.1)

    save_quote(minimal_snapshot, quote_id=quote_id)
    doc_second = load_quote(quote_id)
    assert doc_second["metadata"]["created_at"] == created_at_first


# ---------------------------------------------------------------------------
# 5. Actualiza updated_at al guardar de nuevo
# ---------------------------------------------------------------------------

def test_updated_at_changes_on_resave(minimal_snapshot: QuoteSnapshot) -> None:
    quote_id = save_quote(minimal_snapshot)
    updated_at_first = load_quote(quote_id)["metadata"]["updated_at"]

    time.sleep(1.1)

    save_quote(minimal_snapshot, quote_id=quote_id)
    updated_at_second = load_quote(quote_id)["metadata"]["updated_at"]
    assert updated_at_second > updated_at_first


# ---------------------------------------------------------------------------
# 6. Lista presupuestos
# ---------------------------------------------------------------------------

def test_list_quotes_returns_all(minimal_snapshot: QuoteSnapshot) -> None:
    id1 = save_quote(minimal_snapshot)
    id2 = save_quote(minimal_snapshot)
    results = list_quotes()
    ids = [r["quote_id"] for r in results]
    assert id1 in ids
    assert id2 in ids
    assert len(results) == 2


# ---------------------------------------------------------------------------
# 7. Filtra por status
# ---------------------------------------------------------------------------

def test_list_quotes_filter_by_status(minimal_snapshot: QuoteSnapshot) -> None:
    id_draft = save_quote(minimal_snapshot)
    id_sent = save_quote(minimal_snapshot)
    update_quote_metadata(id_sent, {"status": "sent"})

    drafts = list_quotes(status="draft")
    sents = list_quotes(status="sent")

    assert any(r["quote_id"] == id_draft for r in drafts)
    assert all(r["status"] == "draft" for r in drafts)
    assert any(r["quote_id"] == id_sent for r in sents)
    assert all(r["status"] == "sent" for r in sents)


# ---------------------------------------------------------------------------
# 8. Filtra por client_name
# ---------------------------------------------------------------------------

def test_list_quotes_filter_by_client_name(minimal_snapshot: QuoteSnapshot) -> None:
    save_quote(minimal_snapshot)

    other = QuoteSnapshot.model_validate({
        "header": {"client_name": "Empresa XYZ", "global_margin": 35, "tax": 7, "include_tax": False},
        "lines": [],
    })
    save_quote(other)

    results = list_quotes(client_name="Cliente Test")
    assert len(results) == 1
    assert results[0]["client_name"] == "Cliente Test"


# ---------------------------------------------------------------------------
# 9. Filtra por project_type
# ---------------------------------------------------------------------------

def test_list_quotes_filter_by_project_type(minimal_snapshot: QuoteSnapshot) -> None:
    id1 = save_quote(minimal_snapshot)
    id2 = save_quote(minimal_snapshot)
    update_quote_metadata(id1, {"project_type": "climatizacion"})
    update_quote_metadata(id2, {"project_type": "ventilacion"})

    results = list_quotes(project_type="climatizacion")
    assert len(results) == 1
    assert results[0]["project_type"] == "climatizacion"


# ---------------------------------------------------------------------------
# 10. Filtra por tag
# ---------------------------------------------------------------------------

def test_list_quotes_filter_by_tag(minimal_snapshot: QuoteSnapshot) -> None:
    id1 = save_quote(minimal_snapshot)
    id2 = save_quote(minimal_snapshot)
    update_quote_metadata(id1, {"tags": ["split", "vivienda"]})
    update_quote_metadata(id2, {"tags": ["industrial"]})

    results = list_quotes(tag="split")
    assert len(results) == 1
    assert results[0]["quote_id"] == id1


# ---------------------------------------------------------------------------
# 11. Duplica presupuesto con nuevo ID
# ---------------------------------------------------------------------------

def test_duplicate_quote_creates_new_file(minimal_snapshot: QuoteSnapshot) -> None:
    original_id = save_quote(minimal_snapshot)
    new_id = duplicate_quote(original_id)

    assert new_id != original_id
    doc_new = load_quote(new_id)
    assert doc_new["metadata"]["id"] == new_id
    assert doc_new["metadata"]["status"] == "draft"
    assert doc_new["snapshot"]["header"]["client_name"] == "Cliente Test"
    # El original sigue existiendo
    doc_orig = load_quote(original_id)
    assert doc_orig["metadata"]["id"] == original_id


# ---------------------------------------------------------------------------
# 12. Archiva presupuesto sin borrarlo
# ---------------------------------------------------------------------------

def test_archive_quote_changes_status_only(minimal_snapshot: QuoteSnapshot) -> None:
    quote_id = save_quote(minimal_snapshot)
    archive_quote(quote_id)

    doc = load_quote(quote_id)
    assert doc["metadata"]["status"] == "archived"
    # El archivo sigue existiendo
    path = storage_module.QUOTES_DIR / f"{quote_id}.json"
    assert path.exists()


# ---------------------------------------------------------------------------
# 13. Rechaza IDs peligrosos con ../
# ---------------------------------------------------------------------------

def test_rejects_path_traversal_id(minimal_snapshot: QuoteSnapshot) -> None:
    with pytest.raises(ValueError, match="no permitidos"):
        save_quote(minimal_snapshot, quote_id="../etc/passwd")


def test_rejects_slash_in_id(minimal_snapshot: QuoteSnapshot) -> None:
    with pytest.raises(ValueError, match="no permitidos"):
        save_quote(minimal_snapshot, quote_id="quotes/evil")


# ---------------------------------------------------------------------------
# 14. Al guardar, aplica reglas documentales obligatorias
# ---------------------------------------------------------------------------

def test_save_applies_document_rules(minimal_snapshot: QuoteSnapshot) -> None:
    # El snapshot minimal no tiene conditions (protección de datos)
    assert minimal_snapshot.header.conditions is None
    quote_id = save_quote(minimal_snapshot)
    doc = load_quote(quote_id)
    conditions = doc["snapshot"]["header"].get("conditions") or ""
    assert "protección de datos" in conditions.lower()
    assert "transferencia bancaria" in conditions.lower() or "bbva" in conditions.lower()


# ---------------------------------------------------------------------------
# 15. Fixtures anteriores — QuoteSnapshot sigue funcionando sin metadata
# ---------------------------------------------------------------------------

def test_existing_snapshot_still_works() -> None:
    """Un snapshot antiguo sin metadata debe seguir siendo válido."""
    snap = QuoteSnapshot.model_validate({
        "header": {"global_margin": 35, "tax": 7, "include_tax": False},
        "lines": [],
    })
    assert snap.header.global_margin == 35


def test_save_and_load_existing_fixture() -> None:
    """Fixture completo mixto cargado desde disco sigue pasando tras guardarlo."""
    fixture_path = Path("data/fixtures/presupuesto_completo_mixto.json")
    if not fixture_path.exists():
        pytest.skip("Fixture no disponible")
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    snap = QuoteSnapshot.model_validate(raw)
    quote_id = save_quote(snap)
    doc = load_quote(quote_id)
    restored = QuoteSnapshot.model_validate(doc["snapshot"])
    assert len(restored.lines) == len(snap.lines)


# ---------------------------------------------------------------------------
# Extras: generate_quote_id y limit en list_quotes
# ---------------------------------------------------------------------------

def test_generate_quote_id_is_sequential(minimal_snapshot: QuoteSnapshot) -> None:
    id1 = save_quote(minimal_snapshot)
    id2 = save_quote(minimal_snapshot)
    # Ambos empiezan con PRE- y el segundo tiene número mayor
    num1 = int(id1.split("-")[-1])
    num2 = int(id2.split("-")[-1])
    assert num2 == num1 + 1


def test_list_quotes_limit(minimal_snapshot: QuoteSnapshot) -> None:
    for _ in range(5):
        save_quote(minimal_snapshot)
    results = list_quotes(limit=3)
    assert len(results) == 3
