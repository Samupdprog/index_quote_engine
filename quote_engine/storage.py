"""Almacenamiento local de presupuestos como archivos JSON."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .document_rules import ensure_required_document_sections
from .models import QuoteMetadata, QuoteSnapshot

QUOTES_DIR: Path = Path("data/quotes")

_BAD_PATH_CHARS = re.compile(r"[/\\]|\.\.")


def _get_quotes_dir() -> Path:
    QUOTES_DIR.mkdir(parents=True, exist_ok=True)
    return QUOTES_DIR


def _validate_quote_id(quote_id: str) -> None:
    if _BAD_PATH_CHARS.search(quote_id):
        raise ValueError(f"quote_id '{quote_id}' contiene caracteres no permitidos.")


def _quote_path(quote_id: str) -> Path:
    _validate_quote_id(quote_id)
    return _get_quotes_dir() / f"{quote_id}.json"


def _now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def generate_quote_id() -> str:
    """Genera el siguiente ID correlativo para el año actual: PRE-YYYY-NNNN."""
    year = datetime.now().year
    dir_ = _get_quotes_dir()
    nums: list[int] = []
    for p in dir_.glob(f"PRE-{year}-*.json"):
        m = re.match(rf"^PRE-{year}-(\d{{4}})$", p.stem)
        if m:
            nums.append(int(m.group(1)))
    next_num = max(nums, default=0) + 1
    return f"PRE-{year}-{next_num:04d}"


def save_quote(
    snapshot: QuoteSnapshot | dict[str, Any],
    quote_id: str | None = None,
    created_by: str | None = None,
    source: str = "api",
) -> str:
    """Guarda un presupuesto en disco aplicando las reglas documentales.

    Devuelve el quote_id usado. Si el archivo ya existe, preserva created_at.
    """
    if isinstance(snapshot, dict):
        snapshot = QuoteSnapshot.model_validate(snapshot)

    snapshot = ensure_required_document_sections(snapshot)

    if quote_id is None:
        quote_id = generate_quote_id()
    else:
        _validate_quote_id(quote_id)

    path = _quote_path(quote_id)
    now = _now_iso()

    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        existing_meta = existing.get("metadata", {})
        created_at = existing_meta.get("created_at", now)
        metadata: dict[str, Any] = {
            **existing_meta,
            "id": quote_id,
            "updated_at": now,
            "created_at": created_at,
        }
    else:
        metadata = {
            "id": quote_id,
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
            "source": source,
            "status": "draft",
            "project_type": None,
            "tags": [],
            "client_reference": None,
            "internal_notes": None,
            "version": "0.4",
        }

    doc = {
        "metadata": metadata,
        "snapshot": snapshot.model_dump(),
    }

    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

    return quote_id


def load_quote(quote_id: str) -> dict[str, Any]:
    """Carga un presupuesto desde disco. Lanza FileNotFoundError si no existe."""
    _validate_quote_id(quote_id)
    path = _quote_path(quote_id)
    if not path.exists():
        raise FileNotFoundError(f"Presupuesto '{quote_id}' no encontrado.")
    return json.loads(path.read_text(encoding="utf-8"))


def list_quotes(
    status: str | None = None,
    client_name: str | None = None,
    project_type: str | None = None,
    tag: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Lista presupuestos con filtros opcionales. Devuelve resumen, no el snapshot completo."""
    dir_ = _get_quotes_dir()
    results: list[dict[str, Any]] = []
    for path in sorted(dir_.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        meta = doc.get("metadata", {})
        header = doc.get("snapshot", {}).get("header", {})

        if status is not None and meta.get("status") != status:
            continue
        if client_name is not None and client_name.lower() not in (header.get("client_name") or "").lower():
            continue
        if project_type is not None and meta.get("project_type") != project_type:
            continue
        if tag is not None and tag not in meta.get("tags", []):
            continue

        results.append({
            "quote_id": meta.get("id"),
            "client_name": header.get("client_name"),
            "status": meta.get("status"),
            "created_at": meta.get("created_at"),
            "updated_at": meta.get("updated_at"),
            "project_type": meta.get("project_type"),
            "tags": meta.get("tags", []),
        })

    if limit is not None:
        results = results[:limit]
    return results


def duplicate_quote(source_quote_id: str, new_quote_id: str | None = None) -> str:
    """Duplica un presupuesto existente con un nuevo ID y status='draft'."""
    doc = load_quote(source_quote_id)
    snapshot = QuoteSnapshot.model_validate(doc["snapshot"])
    source_meta: dict[str, Any] = doc.get("metadata", {})

    if new_quote_id is None:
        new_quote_id = generate_quote_id()
    else:
        _validate_quote_id(new_quote_id)

    now = _now_iso()
    new_metadata = {
        **source_meta,
        "id": new_quote_id,
        "created_at": now,
        "updated_at": now,
        "status": "draft",
    }

    new_doc = {
        "metadata": new_metadata,
        "snapshot": snapshot.model_dump(),
    }

    path = _quote_path(new_quote_id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(new_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

    return new_quote_id


def update_quote_metadata(quote_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Actualiza campos de metadata. Protege 'id' y 'created_at'."""
    doc = load_quote(quote_id)
    meta = doc.get("metadata", {})

    for protected in ("id", "created_at"):
        updates.pop(protected, None)

    meta.update(updates)
    meta["updated_at"] = _now_iso()
    doc["metadata"] = meta

    path = _quote_path(quote_id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

    return doc


def archive_quote(quote_id: str) -> dict[str, Any]:
    """Cambia el status a 'archived' sin borrar el archivo."""
    return update_quote_metadata(quote_id, {"status": "archived"})
