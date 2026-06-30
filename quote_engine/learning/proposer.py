"""Proposer de aprendizajes.

Analiza correcciones registradas y propone aprendizajes para revisión humana.
Los aprendizajes propuestos quedan en estado 'pending' hasta que Samuel los aprueba.

REGLA FUNDAMENTAL: Los aprendizajes NUNCA se aprueban automáticamente.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Tipos de aprendizaje reconocidos
LEARNING_TYPES = {
    "pricing_rule",
    "exclusion_rule",
    "transport_rule",
    "labor_rule",
    "material_rule",
    "supplier_preference",
    "template_text",
    "error_pattern",
    "client_exception",
}

# Patrones de campo que sugieren tipos de aprendizaje
_FIELD_TO_TYPE = {
    "transport": "transport_rule",
    "desplazamiento": "transport_rule",
    "mano_obra": "labor_rule",
    "labor": "labor_rule",
    "margin": "pricing_rule",
    "margen": "pricing_rule",
    "supplier": "supplier_preference",
    "proveedor": "supplier_preference",
    "material": "material_rule",
    "exclusion": "exclusion_rule",
}


def _infer_type(field_path: str, old_value: Optional[str], new_value: Optional[str]) -> str:
    """Infiere el tipo de aprendizaje según el campo corregido."""
    fp_lower = field_path.lower()
    for key, learning_type in _FIELD_TO_TYPE.items():
        if key in fp_lower:
            return learning_type
    return "pricing_rule"  # default


def _build_proposed_rule(
    field_path: str,
    old_value: Optional[str],
    new_value: Optional[str],
    correction_reason: Optional[str],
) -> str:
    """Genera un texto descriptivo de la regla propuesta."""
    parts = []
    if correction_reason:
        parts.append(f"Motivo: {correction_reason}.")
    parts.append(
        f"Campo '{field_path}' cambió de {old_value!r} a {new_value!r}."
    )
    parts.append("Revisar si esta corrección debe convertirse en una regla general.")
    return " ".join(parts)


def propose_learning_from_correction(
    db_session,
    correction_id: int,
    auto_propose: bool = True,
) -> Optional[int]:
    """Propone un aprendizaje a partir de una corrección registrada.

    Args:
        db_session: Sesión SQLAlchemy.
        correction_id: ID de la corrección.
        auto_propose: Si True, crea el aprendizaje automáticamente con status='pending'.

    Returns:
        ID del LearningItem creado, o None si no se propone.
    """
    try:
        from quote_engine.db.models import QuoteCase, QuoteCorrection, LearningItem

        correction = db_session.query(QuoteCorrection).filter_by(id=correction_id).first()
        if correction is None:
            logger.warning(f"Corrección {correction_id} no encontrada")
            return None

        case = db_session.query(QuoteCase).filter_by(id=correction.quote_case_id).first()
        case_ref = case.reference if case else None

        learning_type = _infer_type(
            correction.field_path,
            correction.old_value,
            correction.new_value,
        )

        title = (
            f"Corrección en {correction.field_path} "
            f"({correction.old_value!r} → {correction.new_value!r})"
        )
        if case_ref:
            title += f" — {case_ref}"

        proposed_rule = _build_proposed_rule(
            correction.field_path,
            correction.old_value,
            correction.new_value,
            correction.correction_reason,
        )

        if not auto_propose:
            logger.info(f"Aprendizaje propuesto (no guardado): {title}")
            return None

        # Verificar si ya existe un aprendizaje pending para la misma corrección
        existing = db_session.query(LearningItem).filter_by(
            source_quote_case_id=correction.quote_case_id,
            title=title,
            status="pending",
        ).first()

        if existing:
            logger.debug(f"Ya existe aprendizaje pending: {existing.id}")
            return existing.id

        item = LearningItem(
            source_quote_case_id=correction.quote_case_id,
            type=learning_type,
            title=title,
            description=f"Originado por corrección #{correction_id} en {case_ref or 'N/A'}.",
            proposed_rule=proposed_rule,
            status="pending",  # NUNCA se aprueba automáticamente
        )
        db_session.add(item)
        db_session.commit()

        logger.info(
            f"Aprendizaje propuesto: #{item.id} [{learning_type}] status=pending"
        )
        return item.id

    except Exception as exc:
        logger.error(f"Error al proponer aprendizaje: {exc}")
        db_session.rollback()
        return None


def list_pending_learnings(db_session, limit: int = 50) -> list[dict]:
    """Lista aprendizajes pendientes de aprobación."""
    try:
        from quote_engine.db.models import LearningItem

        items = (
            db_session.query(LearningItem)
            .filter_by(status="pending")
            .order_by(LearningItem.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": item.id,
                "type": item.type,
                "title": item.title,
                "description": item.description,
                "proposed_rule": item.proposed_rule,
                "status": item.status,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]

    except Exception as exc:
        logger.error(f"Error al listar aprendizajes pendientes: {exc}")
        return []
