"""Aprobación de aprendizajes.

Solo Samuel (humano) puede aprobar aprendizajes.
Los aprendizajes aprobados pueden disparar acciones adicionales
(nota Obsidian, regla interna, test de regresión).

REGLA CRÍTICA: approve_learning() NUNCA se llama automáticamente por la IA.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def approve_learning(
    db_session,
    learning_id: int,
    approved_by: str = "Samuel",
    generate_obsidian_note: bool = True,
) -> Optional[dict]:
    """Aprueba un aprendizaje pendiente.

    Args:
        db_session: Sesión SQLAlchemy.
        learning_id: ID del LearningItem a aprobar.
        approved_by: Nombre del aprobador (debe ser humano, no 'EON' ni 'auto').
        generate_obsidian_note: Si True, genera nota Markdown en Obsidian.

    Returns:
        Dict con el aprendizaje aprobado, o None si hay error.
    """
    # Protección: la IA no debe aprobar
    if approved_by.lower() in {"eon", "auto", "system", "ia", "bot", "gpt", "claude"}:
        logger.error(
            f"Intento de aprobación automática bloqueado. approved_by={approved_by!r}. "
            "Solo un humano puede aprobar aprendizajes."
        )
        return None

    try:
        from quote_engine.db.models import LearningItem

        item = db_session.query(LearningItem).filter_by(id=learning_id).first()
        if item is None:
            logger.warning(f"LearningItem {learning_id} no encontrado")
            return None

        if item.status == "approved":
            logger.info(f"LearningItem {learning_id} ya estaba aprobado")
            return _item_to_dict(item)

        if item.status != "pending":
            logger.warning(
                f"LearningItem {learning_id} en estado {item.status!r}, no se puede aprobar"
            )
            return None

        item.status = "approved"
        item.approved_by = approved_by
        item.approved_at = datetime.now()
        db_session.commit()

        result = _item_to_dict(item)
        logger.info(f"Aprendizaje #{learning_id} aprobado por {approved_by!r}")

        # Disparar acciones post-aprobación
        if generate_obsidian_note:
            _try_generate_obsidian_note(item)

        return result

    except Exception as exc:
        logger.error(f"Error al aprobar aprendizaje {learning_id}: {exc}")
        db_session.rollback()
        return None


def reject_learning(
    db_session,
    learning_id: int,
    rejected_by: str = "Samuel",
) -> Optional[dict]:
    """Rechaza un aprendizaje pendiente."""
    try:
        from quote_engine.db.models import LearningItem

        item = db_session.query(LearningItem).filter_by(id=learning_id).first()
        if item is None:
            return None

        item.status = "rejected"
        item.approved_by = rejected_by
        item.approved_at = datetime.now()
        db_session.commit()

        logger.info(f"Aprendizaje #{learning_id} rechazado por {rejected_by!r}")
        return _item_to_dict(item)

    except Exception as exc:
        logger.error(f"Error al rechazar aprendizaje {learning_id}: {exc}")
        db_session.rollback()
        return None


def _item_to_dict(item) -> dict:
    return {
        "id": item.id,
        "type": item.type,
        "title": item.title,
        "description": item.description,
        "proposed_rule": item.proposed_rule,
        "status": item.status,
        "approved_by": item.approved_by,
        "approved_at": item.approved_at.isoformat() if item.approved_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _try_generate_obsidian_note(item) -> None:
    """Intenta generar una nota Obsidian para el aprendizaje aprobado."""
    try:
        from quote_engine.obsidian.writer import write_approved_learning_note
        write_approved_learning_note(item)
    except Exception as exc:
        logger.warning(f"No se pudo generar nota Obsidian para aprendizaje #{item.id}: {exc}")
