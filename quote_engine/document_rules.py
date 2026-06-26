"""Reglas documentales obligatorias para presupuestos de Index Clima."""

from __future__ import annotations

from .config import BANK_ENTITY, BBVA_IBAN, COMPANY_EMAIL, COMPANY_NAME
from .models import QuoteSnapshot


# ─── Textos estándar ────────────────────────────────────────────────────────

PROTECCION_DATOS_TEXT: str = (
    f"PROTECCIÓN DE DATOS: En cumplimiento del Reglamento (UE) 2016/679 (RGPD) y la "
    f"Ley Orgánica 3/2018 (LOPDGDD), le informamos de que sus datos personales serán "
    f"tratados por {COMPANY_NAME} para la gestión de la relación comercial. "
    f"Puede ejercer sus derechos de acceso, rectificación, supresión y portabilidad "
    f"dirigiéndose a {COMPANY_EMAIL}."
)

CONDICIONES_PAGO_TEXT: str = (
    f"CONDICIONES DE PAGO\n"
    f"Transferencia bancaria.\n"
    f"{BANK_ENTITY}: {BBVA_IBAN}"
)

# Marcadores para detectar si cada bloque ya existe (comparación insensible a mayúsculas)
_MARKER_PROTECCION = "protección de datos"
_MARKER_BBVA = "bbva"
_MARKER_TRANSFERENCIA = "transferencia bancaria"

# Nombres de Citanias reconocidos (minúsculas, coincidencia parcial con "citanias" en el nombre)
_CITANIAS_KEYWORD = "citanias"


# ─── Detección interna ──────────────────────────────────────────────────────

def _has_section(text: str, marker: str) -> bool:
    return marker in text.lower()


def _has_data_protection(text: str) -> bool:
    return _has_section(text, _MARKER_PROTECCION)


def _has_payment_info(text: str) -> bool:
    return _has_section(text, _MARKER_BBVA) or _has_section(text, _MARKER_TRANSFERENCIA)


# ─── API pública ────────────────────────────────────────────────────────────

def build_default_conditions() -> str:
    """Devuelve el bloque completo de condiciones estándar."""
    return f"{PROTECCION_DATOS_TEXT}\n\n{CONDICIONES_PAGO_TEXT}"


def ensure_required_document_sections(snapshot: QuoteSnapshot) -> QuoteSnapshot:
    """Devuelve un snapshot nuevo con las secciones obligatorias añadidas si faltan.

    No modifica el snapshot original. Si ya tiene ambas secciones, devuelve el mismo objeto.
    """
    existing = snapshot.header.conditions or ""
    additions: list[str] = []

    if not _has_data_protection(existing):
        additions.append(PROTECCION_DATOS_TEXT)

    if not _has_payment_info(existing):
        additions.append(CONDICIONES_PAGO_TEXT)

    if not additions:
        return snapshot

    parts = [existing] if existing.strip() else []
    parts.extend(additions)
    new_conditions = "\n\n".join(parts)

    new_header = snapshot.header.model_copy(update={"conditions": new_conditions})
    return QuoteSnapshot(header=new_header, lines=list(snapshot.lines))


def validate_document_rules(snapshot: QuoteSnapshot) -> list[str]:
    """Devuelve lista de reglas obligatorias ausentes. Lista vacía = todo OK."""
    issues: list[str] = []
    conditions = snapshot.header.conditions or ""

    if not _has_data_protection(conditions):
        issues.append("Falta cláusula de protección de datos.")

    if not _has_payment_info(conditions):
        issues.append("Falta información de transferencia bancaria / IBAN.")

    return issues


def detect_client_profile(snapshot: QuoteSnapshot) -> str:
    """Detecta el perfil del cliente. Devuelve 'citanias' o 'default'."""
    name = (snapshot.header.client_name or "").lower()
    if _CITANIAS_KEYWORD in name:
        return "citanias"
    return "default"


# ─── Helper Citanias ────────────────────────────────────────────────────────

def format_citanias_line(
    intervencion: int | str,
    tienda: str,
    ubicacion: str,
    trabajo: str,
    descripcion: str = "",
) -> dict[str, str]:
    """Construye concept y description para una línea de presupuesto Citanias.

    Estructura del concept:
        Intervención <número> - Tienda <código> - <ubicación> - <trabajo>

    Devuelve un dict con 'concept' y 'description' listo para asignar a QuoteLine.
    """
    concept = f"Intervención {intervencion} - Tienda {tienda} - {ubicacion} - {trabajo}"
    return {"concept": concept, "description": descripcion}
