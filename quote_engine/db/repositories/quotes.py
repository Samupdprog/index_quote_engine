"""Repositorio de casos de presupuesto (quote_cases).

Guarda, recupera y lista presupuestos historicos en PostgreSQL.
Los presupuestos JSON siguen existiendo en data/quotes/ (compatibilidad).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional, Any

logger = logging.getLogger(__name__)


def save_quote_case(
    db_session,
    reference: str,
    snapshot_dict: dict,
    calculated_dict: Optional[dict] = None,
    client_name: Optional[str] = None,
    client_location: Optional[str] = None,
    quote_type: Optional[str] = None,
    status: str = "draft",
    warnings: Optional[list] = None,
    pending_data: Optional[list] = None,
) -> Optional[int]:
    """Guarda un presupuesto como caso historico en la DB."""
    try:
        from quote_engine.db.models import QuoteCase, QuoteLineItem, QuoteTotalRecord

        existing = db_session.query(QuoteCase).filter_by(reference=reference).first()

        now = datetime.now()
        warnings_json = json.dumps(warnings or [], ensure_ascii=False)
        extracted_json = json.dumps(snapshot_dict, ensure_ascii=False)

        if existing is not None:
            existing.client_name = client_name or existing.client_name
            existing.client_location = client_location or existing.client_location
            existing.quote_type = quote_type or existing.quote_type
            existing.status = status
            existing.extracted_data_json = extracted_json
            existing.warnings_json = warnings_json
            existing.updated_at = now
            db_session.flush()
            case_id = existing.id

            db_session.query(QuoteLineItem).filter_by(quote_case_id=case_id).delete()
            db_session.query(QuoteTotalRecord).filter_by(quote_case_id=case_id).delete()
        else:
            case = QuoteCase(
                reference=reference,
                client_name=client_name,
                client_location=client_location,
                quote_type=quote_type,
                status=status,
                extracted_data_json=extracted_json,
                warnings_json=warnings_json,
            )
            db_session.add(case)
            db_session.flush()
            case_id = case.id

        if calculated_dict and "lines" in calculated_dict:
            for line in calculated_dict["lines"]:
                item = QuoteLineItem(
                    quote_case_id=case_id,
                    description=line.get("description", ""),
                    quantity=line.get("quantity", 1.0),
                    unit=line.get("unit"),
                    category=line.get("type"),
                    internal_unit_cost=line.get("cost_unit"),
                    client_unit_price=line.get("sale_unit_without_tax"),
                    internal_total_cost=line.get("cost_total"),
                    client_total_price=line.get("sale_total_without_tax"),
                    confidence="alta",
                    source_reason=line.get("sale_mode"),
                )
                db_session.add(item)

        if calculated_dict and "totals" in calculated_dict:
            t = calculated_dict["totals"]
            totals_record = QuoteTotalRecord(
                quote_case_id=case_id,
                internal_total_cost=t.get("cost_subtotal"),
                client_total_without_igic=t.get("sale_subtotal"),
                igic_rate=snapshot_dict.get("header", {}).get("tax", 7.0),
                igic_amount=t.get("tax_amount"),
                client_total_with_igic=t.get("final_total"),
                benefit=t.get("gross_profit"),
                margin_percent=t.get("gross_profit_percent"),
            )
            db_session.add(totals_record)

        db_session.commit()
        logger.info("Presupuesto %r guardado en DB (case_id=%s)", reference, case_id)
        return case_id

    except Exception as exc:
        logger.error("Error al guardar presupuesto %r en DB: %s", reference, exc)
        db_session.rollback()
        return None


def get_quote_case(db_session, reference: str) -> Optional[dict]:
    """Recupera un caso de presupuesto por referencia."""
    try:
        from quote_engine.db.models import QuoteCase, QuoteLineItem, QuoteTotalRecord

        case = db_session.query(QuoteCase).filter_by(reference=reference).first()
        if case is None:
            return None

        lines = db_session.query(QuoteLineItem).filter_by(quote_case_id=case.id).all()
        totals = db_session.query(QuoteTotalRecord).filter_by(quote_case_id=case.id).first()

        return {
            "id": case.id,
            "reference": case.reference,
            "client_name": case.client_name,
            "client_location": case.client_location,
            "quote_type": case.quote_type,
            "status": case.status,
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "updated_at": case.updated_at.isoformat() if case.updated_at else None,
            "warnings": json.loads(case.warnings_json) if case.warnings_json else [],
            "line_count": len(lines),
            "totals": {
                "internal_total_cost": totals.internal_total_cost if totals else None,
                "client_total_without_igic": totals.client_total_without_igic if totals else None,
                "igic_rate": totals.igic_rate if totals else None,
                "igic_amount": totals.igic_amount if totals else None,
                "client_total_with_igic": totals.client_total_with_igic if totals else None,
                "benefit": totals.benefit if totals else None,
                "margin_percent": totals.margin_percent if totals else None,
            } if totals else None,
            "lines": [
                {
                    "id": li.id,
                    "description": li.description,
                    "quantity": li.quantity,
                    "unit": li.unit,
                    "category": li.category,
                    "internal_unit_cost": li.internal_unit_cost,
                    "client_unit_price": li.client_unit_price,
                    "internal_total_cost": li.internal_total_cost,
                    "client_total_price": li.client_total_price,
                    "confidence": li.confidence,
                    "source_reason": li.source_reason,
                }
                for li in lines
            ],
        }

    except Exception as exc:
        logger.error("Error al recuperar presupuesto %r: %s", reference, exc)
        return None


def list_recent_quote_cases(db_session, limit: int = 20) -> list:
    """Lista los casos de presupuesto mas recientes."""
    try:
        from quote_engine.db.models import QuoteCase, QuoteTotalRecord

        db_session.flush()
        cases = (
            db_session.query(QuoteCase)
            .order_by(QuoteCase.updated_at.desc(), QuoteCase.id.desc())
            .limit(limit)
            .all()
        )

        result = []
        for case in cases:
            totals = db_session.query(QuoteTotalRecord).filter_by(quote_case_id=case.id).first()
            result.append({
                "id": case.id,
                "reference": case.reference,
                "client_name": case.client_name,
                "status": case.status,
                "created_at": case.created_at.isoformat() if case.created_at else None,
                "updated_at": case.updated_at.isoformat() if case.updated_at else None,
                "client_total_with_igic": totals.client_total_with_igic if totals else None,
                "margin_percent": totals.margin_percent if totals else None,
            })

        return result

    except Exception as exc:
        logger.error("Error al listar presupuestos: %s", exc)
        return []
