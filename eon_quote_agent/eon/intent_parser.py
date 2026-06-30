"""Parser de intención basado en reglas para EON."""

import re
from .models import ParsedIntent

# Patrón para IDs de presupuesto: PRE-2026-0001, PRE-EON-TEST, etc.
_QUOTE_ID_RE = re.compile(r"\bPRE-[A-Z0-9]+-[A-Z0-9]+\b", re.IGNORECASE)

_CREATE_KEYWORDS = [
    "hazme", "crea", "crear", "nuevo presupuesto", "presupuesto para",
    "hacer presupuesto", "genera presupuesto", "generar presupuesto",
    "abre presupuesto", "abrir presupuesto",
]

_SEARCH_KEYWORDS = [
    "busca", "buscar", "encuentra", "encontrar", "listar", "lista",
    "muéstrame", "mostrar", "ver presupuestos",
]

_SUMMARIZE_KEYWORDS = [
    "resúmeme", "resume", "resumir", "resumen", "dame resumen",
    "qué tiene", "que tiene",
]

_REPORT_KEYWORDS = [
    "informe", "genera informe", "generar informe", "reporte",
    "html", "genera reporte",
]

_EXPORT_KEYWORDS = [
    "holded", "exporta", "exportar", "exportar holded", "export",
]

_ARCHIVE_KEYWORDS = [
    "archiva", "archivar", "archivo presupuesto",
]

_CALCULATE_KEYWORDS = [
    "calcula", "calcular", "recalcula", "recalcular",
]


def _match_any(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in keywords)


def _extract_quote_id(text: str) -> str | None:
    match = _QUOTE_ID_RE.search(text)
    return match.group(0).upper() if match else None


def _extract_client_name(text: str) -> str | None:
    """Heurística simple: texto tras 'para' o 'de' antes del final."""
    patterns = [
        r"(?:para|de|del cliente)\s+([A-Za-záéíóúÁÉÍÓÚñÑüÜ][A-Za-záéíóúÁÉÍÓÚñÑüÜ\s\-&,\.]+?)(?:\s+con|\s+en|\s+sobre|$)",
        r"(?:presupuestos?\s+de)\s+([A-Za-záéíóúÁÉÍÓÚñÑüÜ][A-Za-záéíóúÁÉÍÓÚñÑüÜ\s\-&,\.]+?)(?:\s+con|\s+en|\s+sobre|$)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def parse_intent(text: str) -> ParsedIntent:
    quote_id = _extract_quote_id(text)
    client_name = _extract_client_name(text)

    if _match_any(text, _EXPORT_KEYWORDS):
        missing = [] if quote_id else ["quote_id"]
        return ParsedIntent(
            action="export_holded",
            quote_id=quote_id,
            missing_fields=missing,
        )

    if _match_any(text, _REPORT_KEYWORDS):
        missing = [] if quote_id else ["quote_id"]
        return ParsedIntent(
            action="generate_report",
            quote_id=quote_id,
            missing_fields=missing,
        )

    if _match_any(text, _SUMMARIZE_KEYWORDS):
        missing = [] if quote_id else ["quote_id"]
        return ParsedIntent(
            action="summarize_quote",
            quote_id=quote_id,
            missing_fields=missing,
        )

    if _match_any(text, _CALCULATE_KEYWORDS):
        missing = [] if quote_id else ["quote_id"]
        return ParsedIntent(
            action="calculate_quote",
            quote_id=quote_id,
            missing_fields=missing,
        )

    if _match_any(text, _ARCHIVE_KEYWORDS):
        missing = [] if quote_id else ["quote_id"]
        return ParsedIntent(
            action="archive_quote",
            quote_id=quote_id,
            missing_fields=missing,
        )

    if _match_any(text, _SEARCH_KEYWORDS):
        return ParsedIntent(
            action="search_quotes",
            client_name=client_name,
            quote_id=quote_id,
        )

    if _match_any(text, _CREATE_KEYWORDS):
        missing: list[str] = []
        if not client_name:
            missing.append("client_name")
        return ParsedIntent(
            action="create_quote",
            client_name=client_name,
            needs_files=True,
            missing_fields=missing,
            confidence=0.8,
        )

    return ParsedIntent(
        action="unknown",
        quote_id=quote_id,
        client_name=client_name,
        confidence=0.3,
        missing_fields=["action"],
    )
