"""Configuración de EON cargada desde variables de entorno."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

QUOTE_ENGINE_API_URL: str = os.getenv("QUOTE_ENGINE_API_URL", "http://127.0.0.1:8000")
EON_DEFAULT_CREATED_BY: str = os.getenv("EON_DEFAULT_CREATED_BY", "EON")
EON_DEFAULT_SOURCE: str = os.getenv("EON_DEFAULT_SOURCE", "eon")
