"""Normalización de texto para búsqueda en catálogo."""

from __future__ import annotations

import re
import unicodedata


# Palabras vacías que no aportan a la búsqueda
_STOP_WORDS = {
    "de", "del", "la", "el", "los", "las", "un", "una", "unos", "unas",
    "para", "con", "sin", "en", "a", "y", "o", "e", "u",
    "tipo", "modelo", "serie", "ref", "referencia", "cod", "codigo",
}


def normalize_for_search(text: str) -> str:
    """Normaliza texto para búsqueda: minúsculas, sin tildes, sin stop words."""
    if not text:
        return ""
    text = str(text).strip()

    # Eliminar tildes
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )

    text = text.lower()

    # Eliminar caracteres no alfanuméricos excepto espacios y /
    text = re.sub(r"[^\w\s/]", " ", text)

    # Colapsar espacios
    text = re.sub(r"\s+", " ", text).strip()

    return text


def tokenize(text: str, remove_stop_words: bool = True) -> list[str]:
    """Divide texto normalizado en tokens."""
    normalized = normalize_for_search(text)
    tokens = normalized.split()
    if remove_stop_words:
        tokens = [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]
    return tokens


def similarity_score(query: str, candidate: str) -> float:
    """Calcula score de similitud [0.0, 1.0] entre query y candidato.

    Basado en coincidencia de tokens (Jaccard simplificado).
    """
    q_tokens = set(tokenize(query))
    c_tokens = set(tokenize(candidate))

    if not q_tokens:
        return 0.0

    intersection = q_tokens & c_tokens
    union = q_tokens | c_tokens

    if not union:
        return 0.0

    # Jaccard
    jaccard = len(intersection) / len(union)

    # Bonus si todos los tokens del query están en el candidato
    coverage = len(intersection) / len(q_tokens)

    return (jaccard + coverage) / 2.0


def extract_code(text: str) -> str | None:
    """Intenta extraer un código de producto del texto.

    Busca patrones tipo TUB-CU-3/8, COMP-500, etc.
    """
    # Patrón: letras seguidas de números o /, con guiones
    match = re.search(r"\b([A-Z]{2,}-[A-Z0-9/\-]+)\b", str(text).upper())
    return match.group(1) if match else None
