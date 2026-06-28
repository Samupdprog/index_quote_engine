"""Endpoints de la API para EON — /eon/..."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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

eon_router = APIRouter(prefix="/eon", tags=["EON"])


class EonCommandsRequest(BaseModel):
    commands: list[dict[str, Any]]
    save_mode: str = "copy"
    new_quote_id: str | None = None
    created_by: str = "EON"


class EonDuplicateRequest(BaseModel):
    new_quote_id: str | None = None
    created_by: str = "EON"


def _raise_if_error(result: dict) -> None:
    if not result.get("ok"):
        error = result.get("error", "Error desconocido")
        status = 404 if "no encontrado" in error.lower() else 422
        raise HTTPException(status_code=status, detail=error)


@eon_router.get("/tools")
def get_eon_tools() -> dict:
    return {"tools": list_eon_tools(), "total": len(list_eon_tools())}


@eon_router.get("/search")
def eon_search(
    q: str | None = None,
    client_name: str | None = None,
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
    filters: dict = {k: v for k, v in {
        "query": q,
        "client_name": client_name,
        "supplier": supplier,
        "status": status,
        "project_type": project_type,
        "tag": tag,
        "min_profit": min_profit,
        "max_profit": max_profit,
        "min_total": min_total,
        "max_total": max_total,
        "has_warnings": has_warnings,
        "has_problems": has_problems,
        "sort_by": sort_by,
        "descending": descending,
        "limit": limit,
    }.items() if v is not None}
    result = eon_search_quotes(filters)
    _raise_if_error(result)
    return result


@eon_router.get("/quotes/{quote_id}")
def eon_get(quote_id: str) -> dict:
    result = eon_get_quote(quote_id)
    _raise_if_error(result)
    return result


@eon_router.get("/quotes/{quote_id}/summary")
def eon_summary(quote_id: str) -> dict:
    result = eon_summarize_quote(quote_id)
    _raise_if_error(result)
    return result


@eon_router.get("/quotes/{quote_id}/calculate")
def eon_calculate(quote_id: str) -> dict:
    result = eon_calculate_quote(quote_id)
    _raise_if_error(result)
    return result


@eon_router.post("/quotes/{quote_id}/duplicate")
def eon_duplicate(quote_id: str, body: EonDuplicateRequest) -> dict:
    result = eon_duplicate_quote(quote_id, new_quote_id=body.new_quote_id, created_by=body.created_by)
    _raise_if_error(result)
    return result


@eon_router.post("/quotes/{quote_id}/commands")
def eon_commands(quote_id: str, body: EonCommandsRequest) -> dict:
    result = eon_apply_commands(
        quote_id,
        commands=body.commands,
        save_mode=body.save_mode,
        new_quote_id=body.new_quote_id,
        created_by=body.created_by,
    )
    _raise_if_error(result)
    return result


@eon_router.get("/quotes/{quote_id}/report")
def eon_report(quote_id: str) -> dict:
    result = eon_generate_internal_report(quote_id, html=False)
    _raise_if_error(result)
    return result


@eon_router.get("/quotes/{quote_id}/report/html")
def eon_report_html(quote_id: str) -> dict:
    result = eon_generate_internal_report(quote_id, html=True)
    _raise_if_error(result)
    return result


@eon_router.get("/quotes/{quote_id}/export/holded")
def eon_holded(quote_id: str) -> dict:
    result = eon_export_holded_payload(quote_id)
    _raise_if_error(result)
    return result


@eon_router.post("/quotes/{quote_id}/archive")
def eon_archive(quote_id: str) -> dict:
    result = eon_archive_quote(quote_id)
    _raise_if_error(result)
    return result
