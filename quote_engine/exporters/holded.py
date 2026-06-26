"""Exportador de payload compatible con Holded.

No envía nada a Holded. Solo genera el dict listo para enviar.
"""

from __future__ import annotations

from ..document_rules import ensure_required_document_sections
from ..models import CalculatedLine, CalculatedQuote, QuoteSnapshot


def _format_item(cl: CalculatedLine) -> dict:
    return {
        "name": cl.description,
        "desc": "",
        "units": cl.quantity,
        "subtotal": cl.sale_total_without_tax,
        "tax": cl.tax_rate,
        "total": cl.client_total,
        "_meta": {
            "line_id": cl.line_id,
            "type": cl.type,
            "supplier": cl.supplier,
            "cost_total": cl.cost_total,
            "gross_profit": cl.gross_profit,
            "sale_mode": cl.sale_mode,
        },
    }


def export_holded_payload(
    snapshot: QuoteSnapshot,
    calculated: CalculatedQuote,
) -> dict:
    """Genera un payload compatible con la API de Holded (sin enviarlo).

    Las condiciones/observaciones incluyen siempre protección de datos y
    transferencia bancaria, añadiéndolas si no estaban presentes.
    """
    enriched = ensure_required_document_sections(snapshot)
    header = enriched.header
    items = [_format_item(cl) for cl in calculated.lines]

    return {
        "contactName": header.client_name,
        "contactTaxId": header.client_tax_id,
        "contactAddress": header.client_address,
        "date": header.date,
        "quoteNumber": header.quote_number,
        "title": header.title,
        "notes": header.conditions,
        "internalNotes": header.internal_notes,
        "currency": "EUR",
        "items": items,
        "totals": {
            "subtotal": calculated.totals.sale_subtotal,
            "tax": calculated.totals.tax_amount,
            "total": calculated.totals.final_total,
        },
    }
