"""Configuración centralizada de Index Clima.

Punto único de acceso a datos de empresa y banco. La fuente de verdad es
config/document_defaults.json (puede sobreescribirse con variables de entorno).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_JSON_PATH = Path(__file__).parent.parent / "config" / "document_defaults.json"

_DEFAULTS = {
    "bank": {"entity": "BBVA", "iban": "ES00 0182 XXXX XXXX XXXX XXXX", "holder": "Index Clima S.L."},
    "company": {"name": "Index Clima S.L.", "email": "info@indexclima.com"},
}


def _load() -> dict:
    try:
        return json.loads(_JSON_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return _DEFAULTS


_cfg = _load()

BBVA_IBAN: str = os.getenv("INDEXCLIMA_BBVA_IBAN", _cfg.get("bank", _DEFAULTS["bank"])["iban"])
COMPANY_NAME: str = _cfg.get("company", _DEFAULTS["company"])["name"]
COMPANY_EMAIL: str = _cfg.get("company", _DEFAULTS["company"])["email"]
BANK_ENTITY: str = _cfg.get("bank", _DEFAULTS["bank"])["entity"]
