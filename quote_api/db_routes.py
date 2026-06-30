"""Endpoints de acceso a DB — /db/quotes/..."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from quote_engine.models import QuoteSnapshot

db_router = APIRouter(prefix="/db", tags=["Database"])


def _get_db():
    from quote_engine.db.session import get_session_factory
    factory = get_session_factory()
    if factory is None:
        return None
    return factory()


class SaveQuoteDBRequest(BaseModel):
    snapshot: QuoteSnapshot
    reference: Optional[str] = None
    client_name: Optional[str] = None
    client_location: Optional[str] = None
    quote_type: Optional[str] = None
    status: str = "draft"
    warnings: list[str] = []


@db_router.post("/quotes")
def db_save_quote(body: SaveQuoteDBRequest) -> dict:
    """Guarda un presupuesto como caso histórico en PostgreSQL."""
    from quote_engine.calculator import calculate_quote
    from quote_engine.db.repositories.quotes import save_quote_case
    from quote_engine import storage

    # Calcular
    calculated = calculate_quote(body.snapshot)

    # Determinar referencia
    reference = body.reference
    if not reference:
        reference = storage.generate_quote_id()

    session = _get_db()
    if session is None:
        raise HTTPException(status_code=503, detail="Base de datos no configurada")

    try:
        case_id = save_quote_case(
            db_session=session,
            reference=reference,
            snapshot_dict=body.snapshot.model_dump(),
            calculated_dict=calculated.model_dump(),
            client_name=body.client_name or body.snapshot.header.client_name,
            client_location=body.client_location,
            quote_type=body.quote_type,
            status=body.status,
            warnings=body.warnings or calculated.warnings,
        )
        if case_id is None:
            raise HTTPException(status_code=500, detail="Error al guardar en DB")

        return {
            "ok": True,
            "reference": reference,
            "case_id": case_id,
            "status": body.status,
        }
    finally:
        session.close()


@db_router.get("/quotes/{reference}")
def db_get_quote(reference: str) -> dict:
    """Recupera un caso de presupuesto de PostgreSQL."""
    from quote_engine.db.repositories.quotes import get_quote_case

    session = _get_db()
    if session is None:
        raise HTTPException(status_code=503, detail="Base de datos no configurada")

    try:
        case = get_quote_case(session, reference)
        if case is None:
            raise HTTPException(status_code=404, detail=f"Presupuesto {reference!r} no encontrado en DB")
        return case
    finally:
        session.close()


@db_router.get("/quotes")
def db_list_quotes(limit: int = 20) -> dict:
    """Lista los últimos casos de presupuesto en PostgreSQL."""
    from quote_engine.db.repositories.quotes import list_recent_quote_cases

    session = _get_db()
    if session is None:
        raise HTTPException(status_code=503, detail="Base de datos no configurada")

    try:
        cases = list_recent_quote_cases(session, limit=limit)
        return {"cases": cases, "total": len(cases)}
    finally:
        session.close()
