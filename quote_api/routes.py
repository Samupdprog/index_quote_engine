"""Rutas de la API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from quote_engine.calculator import calculate_quote
from quote_engine.commands import apply_command, apply_commands
from quote_engine.exporters.holded import export_holded_payload
from quote_engine.exporters.internal_report import (
    export_internal_report_dict,
    export_internal_report_html,
)
from quote_engine.models import QuoteSnapshot
from quote_engine.normalizer import normalize_supplier_json
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
