"""Cliente seguro de lectura para Holded API v2."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values


BASE_URL = "https://api.holded.com"
API_PREFIX = "/api/v2"
DEFAULT_TIMEOUT = 20.0
ENV_FILE = Path(__file__).resolve().parents[2] / ".env.local"
TOKEN_RE = re.compile(r"[\s\u200b\u200c\u200d\ufeff]+")


class HoldedClientError(RuntimeError):
    """Error controlado del cliente Holded sin datos sensibles."""


class HoldedAuthError(HoldedClientError):
    """Error de autenticacion o permisos. No se debe reintentar en bucle."""


def _clean_token(value: str | None) -> str:
    if not value:
        return ""
    return TOKEN_RE.sub("", value.strip())


def _load_api_key() -> str:
    token = _clean_token(os.getenv("HOLDED_API_KEY"))
    if token:
        return token

    if ENV_FILE.exists():
        values = dotenv_values(ENV_FILE)
        token = _clean_token(values.get("HOLDED_API_KEY"))
        if token:
            return token

    raise HoldedAuthError("HOLDED_API_KEY no esta disponible para el cliente local.")


def _client() -> httpx.Client:
    token = _load_api_key()
    return httpx.Client(
        base_url=BASE_URL,
        timeout=DEFAULT_TIMEOUT,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )


def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    if not path.startswith(API_PREFIX):
        raise HoldedClientError("El cliente Holded solo permite rutas API v2.")

    with _client() as client:
        response = client.request(method, path, **kwargs)

    if response.status_code in {401, 403}:
        raise HoldedAuthError(f"Holded devolvio {response.status_code}. Revisar credenciales o permisos.")
    if response.status_code >= 400:
        raise HoldedClientError(f"Holded devolvio {response.status_code}: {_safe_error_detail(response)}")
    return response


def _safe_error_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text[:250]

    if isinstance(data, dict):
        for key in ("detail", "title", "message", "error"):
            value = data.get(key)
            if value:
                return str(value)[:250]
    return str(data)[:250]


def _json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        raise HoldedClientError("Holded no devolvio JSON valido.") from exc


def holded_healthcheck() -> dict[str, Any]:
    """Comprueba lectura basica de presupuestos sin devolver secretos."""

    data = holded_list_latest_estimates(limit=1)
    count = len(data.get("items", data) if isinstance(data, dict) else data)
    return {
        "ok": True,
        "api": "v2",
        "base_url": BASE_URL,
        "endpoint": f"{API_PREFIX}/estimates",
        "items_seen": count,
    }


def holded_list_latest_estimates(limit: int = 1) -> Any:
    """Lista presupuestos recientes usando GET /api/v2/estimates."""

    if limit < 1:
        raise ValueError("limit debe ser mayor que cero.")
    response = _request("GET", f"{API_PREFIX}/estimates", params={"limit": limit})
    return _json(response)


def holded_get_estimate(estimate_id: str) -> Any:
    """Obtiene un presupuesto por ID usando GET /api/v2/estimates/{id}."""

    if not estimate_id:
        raise ValueError("estimate_id es obligatorio.")
    response = _request("GET", f"{API_PREFIX}/estimates/{estimate_id}")
    return _json(response)


def holded_download_estimate_pdf(estimate_id: str, output_dir: str | Path) -> Path:
    """Descarga el PDF de un presupuesto y devuelve la ruta local."""

    if not estimate_id:
        raise ValueError("estimate_id es obligatorio.")

    response = _request("GET", f"{API_PREFIX}/estimates/{estimate_id}/pdf")
    content = response.content
    if not content:
        raise HoldedClientError("Holded devolvio un PDF vacio.")

    document_number = "sin_numero"
    try:
        estimate = holded_get_estimate(estimate_id)
        document_number = _safe_filename(str(_pick(estimate, "document_number", "docNumber", "number", "num") or document_number))
    except HoldedClientError:
        document_number = "sin_numero"

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    pdf_path = output_path / f"presupuesto_{document_number}_{_safe_filename(estimate_id)}.pdf"
    pdf_path.write_bytes(content)
    return pdf_path.resolve()


def _pick(data: Any, *keys: str) -> Any:
    if isinstance(data, dict):
        for key in keys:
            if key in data and data[key] not in (None, ""):
                return data[key]
        for container_key in ("data", "estimate", "item"):
            value = data.get(container_key)
            nested = _pick(value, *keys)
            if nested not in (None, ""):
                return nested
    return None


def _safe_filename(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return clean.strip("._") or "sin_valor"

