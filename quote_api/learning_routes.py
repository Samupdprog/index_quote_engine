"""Endpoints de aprendizaje — /learning/..."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

learning_router = APIRouter(prefix="/learning", tags=["Learning"])


def _get_db():
    """Obtiene sesión DB o None."""
    from quote_engine.db.session import get_session_factory
    factory = get_session_factory()
    if factory is None:
        return None
    return factory()


@learning_router.get("/pending")
def list_pending() -> dict:
    """Lista aprendizajes pendientes de aprobación."""
    from quote_engine.learning.proposer import list_pending_learnings

    session = _get_db()
    if session is None:
        return {"items": [], "total": 0, "warning": "Base de datos no disponible"}

    try:
        items = list_pending_learnings(session)
        return {"items": items, "total": len(items)}
    finally:
        session.close()


@learning_router.post("/{learning_id}/approve")
def approve_learning_endpoint(
    learning_id: int,
    approved_by: str = "Samuel",
) -> dict:
    """Aprueba un aprendizaje pendiente (solo humanos)."""
    from quote_engine.learning.approval import approve_learning

    if approved_by.lower() in {"eon", "auto", "system", "ia", "bot"}:
        raise HTTPException(
            status_code=403,
            detail="Los aprendizajes solo pueden ser aprobados por un humano, no por sistemas automáticos.",
        )

    session = _get_db()
    if session is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")

    try:
        result = approve_learning(session, learning_id, approved_by=approved_by)
        if result is None:
            raise HTTPException(
                status_code=404 if True else 422,
                detail=f"No se pudo aprobar el aprendizaje {learning_id}",
            )
        return result
    finally:
        session.close()


@learning_router.post("/{learning_id}/reject")
def reject_learning_endpoint(
    learning_id: int,
    rejected_by: str = "Samuel",
) -> dict:
    """Rechaza un aprendizaje pendiente."""
    from quote_engine.learning.approval import reject_learning

    session = _get_db()
    if session is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")

    try:
        result = reject_learning(session, learning_id, rejected_by=rejected_by)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Aprendizaje {learning_id} no encontrado")
        return result
    finally:
        session.close()


class CorrectionRequest(BaseModel):
    quote_reference: str
    field_path: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    correction_reason: Optional[str] = None
    created_by: str = "Samuel"
    auto_propose_learning: bool = True


@learning_router.post("/corrections")
def register_correction_endpoint(body: CorrectionRequest) -> dict:
    """Registra una corrección en un presupuesto y opcionalmente propone aprendizaje."""
    from quote_engine.learning.corrections import register_correction
    from quote_engine.learning.proposer import propose_learning_from_correction

    session = _get_db()
    if session is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")

    try:
        corr_id = register_correction(
            db_session=session,
            quote_reference=body.quote_reference,
            field_path=body.field_path,
            old_value=body.old_value,
            new_value=body.new_value,
            correction_reason=body.correction_reason,
            created_by=body.created_by,
        )
        if corr_id is None:
            raise HTTPException(
                status_code=404,
                detail=f"Presupuesto {body.quote_reference!r} no encontrado en DB",
            )

        learning_id = None
        if body.auto_propose_learning:
            learning_id = propose_learning_from_correction(session, corr_id)

        return {
            "ok": True,
            "correction_id": corr_id,
            "learning_proposed": learning_id is not None,
            "learning_id": learning_id,
            "message": (
                f"Corrección registrada. Aprendizaje #{learning_id} propuesto (pendiente de aprobación)."
                if learning_id else "Corrección registrada."
            ),
        }
    finally:
        session.close()
