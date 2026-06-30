"""Registro de correcciones en presupuestos.

Cada vez que Samuel corrige algo en un presupuesto generado por EON,
se registra una corrección que puede dar lugar a un aprendizaje.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def register_correction(
    db_session,
    quote_reference: str,
    field_path: str,
    old_value: Optional[str],
    new_value: Optional[str],
    correction_reason: Optional[str] = None,
    created_by: str = "Samuel",
) -> Optional[int]:
    """Registra una corrección en un presupuesto.

    Args:
        db_session: Sesión SQLAlchemy.
        quote_reference: Referencia del presupuesto (ej. PRE-2026-0001).
        field_path: Ruta del campo corregido (ej. 'lines[0].transport').
        old_value: Valor anterior (como string).
        new_value: Valor nuevo (como string).
        correction_reason: Motivo de la corrección.
        created_by: Quién realiza la corrección.

    Returns:
        ID de la corrección creada, o None si hay error.
    """
    try:
        from quote_engine.db.models import QuoteCase, QuoteCorrection

        case = db_session.query(QuoteCase).filter_by(reference=quote_reference).first()
        if case is None:
            logger.warning(
                f"No se puede registrar corrección: presupuesto {quote_reference!r} no encontrado en DB"
            )
            return None

        correction = QuoteCorrection(
            quote_case_id=case.id,
            field_path=field_path,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            correction_reason=correction_reason,
            created_by=created_by,
        )
        db_session.add(correction)
        db_session.commit()

        logger.info(
            f"Corrección registrada: {quote_reference!r} / {field_path}: "
            f"{old_value!r} → {new_value!r}"
        )
        return correction.id

    except Exception as exc:
        logger.error(f"Error al registrar corrección: {exc}")
        db_session.rollback()
        return None


def list_corrections(db_session, quote_reference: str) -> list[dict]:
    """Lista las correcciones de un presupuesto."""
    try:
        from quote_engine.db.models import QuoteCase, QuoteCorrection

        case = db_session.query(QuoteCase).filter_by(reference=quote_reference).first()
        if case is None:
            return []

        corrections = (
            db_session.query(QuoteCorrection)
            .filter_by(quote_case_id=case.id)
            .order_by(QuoteCorrection.created_at.desc())
            .all()
        )

        return [
            {
                "id": c.id,
                "field_path": c.field_path,
                "old_value": c.old_value,
                "new_value": c.new_value,
                "correction_reason": c.correction_reason,
                "created_by": c.created_by,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in corrections
        ]

    except Exception as exc:
        logger.error(f"Error al listar correcciones: {exc}")
        return []
