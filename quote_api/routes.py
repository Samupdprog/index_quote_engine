"""Rutas de la API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from quote_engine.calculator import calculate_quote
from quote_engine.commands import apply_command, apply_commands
from quote_engine.exporters.holded import export_holded_payload
from quote_engine.exporters.internal_report import (
    build_internal_report,
    build_internal_report_html,
    export_internal_report_dict,
    export_internal_report_html,
)
from quote_engine.models import QuoteSnapshot
from quote_engine.normalizer import normalize_supplier_json
from quote_engine import storage
from quote_engine.search import find_recent_quotes, search_quotes
from quote_engine.validators import CommandError

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas de request/response
# ---------------------------------------------------------------------------

class ImportRequest(BaseModel):
    supplier_json: Any  # lista o dict o string JSON
    defaults: dict[str, Any] | None = None


class CalculateRequest(BaseModel):
    snapshot: QuoteSnapshot


class CommandRequest(BaseModel):
    snapshot: QuoteSnapshot
    command: dict[str, Any]


class CommandsRequest(BaseModel):
    snapshot: QuoteSnapshot
    commands: list[dict[str, Any]]


class ExportRequest(BaseModel):
    snapshot: QuoteSnapshot


class SaveQuoteRequest(BaseModel):
    snapshot: QuoteSnapshot
    quote_id: str | None = None
    created_by: str | None = None
    source: str = "api"


class ListQuotesQuery(BaseModel):
    status: str | None = None
    client_name: str | None = None
    project_type: str | None = None
    tag: str | None = None
    limit: int | None = None


class MetadataUpdateRequest(BaseModel):
    updates: dict[str, Any]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "index_quote_engine"}


@router.post("/quotes/import")
def import_quote(body: ImportRequest) -> dict:
    try:
        snapshot = normalize_supplier_json(body.supplier_json, body.defaults)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    calculated = calculate_quote(snapshot)
    return {
        "snapshot": snapshot.model_dump(),
        "calculated": calculated.model_dump(),
        "warnings": calculated.warnings,
    }


@router.post("/quotes/calculate")
def calculate(body: CalculateRequest) -> dict:
    calculated = calculate_quote(body.snapshot)
    return {"calculated": calculated.model_dump()}


@router.post("/quotes/command")
def single_command(body: CommandRequest) -> dict:
    try:
        new_snapshot = apply_command(body.snapshot, body.command)
    except CommandError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    calculated = calculate_quote(new_snapshot)
    return {
        "snapshot": new_snapshot.model_dump(),
        "calculated": calculated.model_dump(),
        "warnings": calculated.warnings,
    }


@router.post("/quotes/commands")
def multi_commands(body: CommandsRequest) -> dict:
    try:
        new_snapshot = apply_commands(body.snapshot, body.commands)
    except CommandError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    calculated = calculate_quote(new_snapshot)
    return {
        "snapshot": new_snapshot.model_dump(),
        "calculated": calculated.model_dump(),
        "warnings": calculated.warnings,
    }


@router.post("/quotes/export/holded")
def export_holded(body: ExportRequest) -> dict:
    calculated = calculate_quote(body.snapshot)
    payload = export_holded_payload(body.snapshot, calculated)
    return payload


@router.post("/quotes/export/internal-report")
def export_internal(body: ExportRequest) -> dict:
    calculated = calculate_quote(body.snapshot)
    report = export_internal_report_dict(body.snapshot, calculated)
    return report


@router.post("/quotes/export/internal-report/html")
def export_internal_html(body: ExportRequest) -> dict:
    calculated = calculate_quote(body.snapshot)
    html = export_internal_report_html(body.snapshot, calculated)
    return {"html": html}


# ---------------------------------------------------------------------------
# Storage endpoints
# ---------------------------------------------------------------------------

@router.post("/storage/quotes")
def storage_save_quote(body: SaveQuoteRequest) -> dict:
    try:
        quote_id = storage.save_quote(
            body.snapshot,
            quote_id=body.quote_id,
            created_by=body.created_by,
            source=body.source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    doc = storage.load_quote(quote_id)
    return {"quote_id": quote_id, "metadata": doc["metadata"]}


@router.get("/storage/quotes")
def storage_list_quotes(
    status: str | None = None,
    client_name: str | None = None,
    project_type: str | None = None,
    tag: str | None = None,
    limit: int | None = None,
) -> dict:
    results = storage.list_quotes(
        status=status,
        client_name=client_name,
        project_type=project_type,
        tag=tag,
        limit=limit,
    )
    return {"quotes": results, "total": len(results)}


@router.get("/storage/quotes/{quote_id}")
def storage_get_quote(quote_id: str) -> dict:
    try:
        doc = storage.load_quote(quote_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return doc


@router.post("/storage/quotes/{quote_id}/duplicate")
def storage_duplicate_quote(quote_id: str, new_id: str | None = None) -> dict:
    try:
        new_quote_id = storage.duplicate_quote(quote_id, new_quote_id=new_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    doc = storage.load_quote(new_quote_id)
    return {"quote_id": new_quote_id, "metadata": doc["metadata"]}


@router.patch("/storage/quotes/{quote_id}/metadata")
def storage_update_metadata(quote_id: str, body: MetadataUpdateRequest) -> dict:
    try:
        doc = storage.update_quote_metadata(quote_id, body.updates)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"quote_id": quote_id, "metadata": doc["metadata"]}


@router.post("/storage/quotes/{quote_id}/archive")
def storage_archive_quote(quote_id: str) -> dict:
    try:
        doc = storage.archive_quote(quote_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"quote_id": quote_id, "status": doc["metadata"]["status"]}


@router.get("/storage/quotes/{quote_id}/report")
def storage_report_dict(quote_id: str) -> dict:
    try:
        doc = storage.load_quote(quote_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    snap = QuoteSnapshot.model_validate(doc["snapshot"])
    return build_internal_report(snap, metadata=doc.get("metadata"))


@router.get("/storage/search")
def storage_search(
    q: str | None = None,
    client: str | None = None,
    supplier: str | None = None,
    status: str | None = None,
    project_type: str | None = None,
    tag: str | None = None,
    min_profit: float | None = None,
    max_profit: float | None = None,
    min_total: float | None = None,
    max_total: float | None = None,
    has_warnings: bool | None = None,
    has_problems: bool | None = None,
    sort_by: str = "updated_at",
    descending: bool = True,
    limit: int | None = None,
) -> dict:
    results = search_quotes(
        query=q,
        client_name=client,
        supplier=supplier,
        status=status,
        project_type=project_type,
        tag=tag,
        min_profit=min_profit,
        max_profit=max_profit,
        min_total=min_total,
        max_total=max_total,
        has_warnings=has_warnings,
        has_problems=has_problems,
        sort_by=sort_by,
        descending=descending,
        limit=limit,
    )
    return {"results": results, "total": len(results)}


@router.get("/storage/recent")
def storage_recent(limit: int = 10) -> dict:
    results = find_recent_quotes(limit=limit)
    return {"results": results, "total": len(results)}


@router.get("/storage/quotes/{quote_id}/report/html")
def storage_report_html(quote_id: str) -> dict:
    try:
        doc = storage.load_quote(quote_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    snap = QuoteSnapshot.model_validate(doc["snapshot"])
    html = build_internal_report_html(snap, metadata=doc.get("metadata"))
    return {"html": html}
