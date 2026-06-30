"""Cliente HTTP para index_quote_engine."""

from typing import Any

import httpx

from .config import QUOTE_ENGINE_API_URL


class QuoteEngineError(Exception):
    """Error genérico del cliente."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.details: dict = details or {}


class QuoteNotFoundError(QuoteEngineError):
    """El presupuesto solicitado no existe en el motor."""


class QuoteEngineClient:
    def __init__(self, base_url: str = QUOTE_ENGINE_API_URL, timeout: float = 30.0):
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_http_error(r: httpx.Response, path: str) -> None:
        """Convierte HTTPStatusError en QuoteEngineError con details de FastAPI."""
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                details = exc.response.json()
            except Exception:
                details = {}
            raise QuoteEngineError(
                f"Error HTTP {exc.response.status_code} en {path}",
                details=details,
            ) from exc

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self._base}{path}"
        try:
            r = httpx.get(url, params=params, timeout=self._timeout)
        except httpx.ConnectError as exc:
            raise QuoteEngineError(
                f"No se puede conectar al motor en {self._base}. ¿Está arrancado?"
            ) from exc
        except httpx.TimeoutException as exc:
            raise QuoteEngineError("El motor tardó demasiado en responder.") from exc
        if r.status_code == 404:
            raise QuoteNotFoundError(f"Recurso no encontrado: {path}")
        self._check_http_error(r, path)
        return r.json()

    def _post(self, path: str, body: dict | None = None) -> Any:
        url = f"{self._base}{path}"
        try:
            r = httpx.post(url, json=body or {}, timeout=self._timeout)
        except httpx.ConnectError as exc:
            raise QuoteEngineError(
                f"No se puede conectar al motor en {self._base}. ¿Está arrancado?"
            ) from exc
        except httpx.TimeoutException as exc:
            raise QuoteEngineError("El motor tardó demasiado en responder.") from exc
        if r.status_code == 404:
            raise QuoteNotFoundError(f"Recurso no encontrado: {path}")
        self._check_http_error(r, path)
        return r.json()

    # ------------------------------------------------------------------
    # Endpoints EON
    # ------------------------------------------------------------------

    def get_tools(self) -> Any:
        return self._get("/eon/tools")

    def search_quotes(
        self,
        client_name: str | None = None,
        tags: list[str] | None = None,
        status: str | None = None,
    ) -> Any:
        params: dict = {}
        if client_name:
            params["client_name"] = client_name
        if tags:
            params["tags"] = ",".join(tags)
        if status:
            params["status"] = status
        return self._get("/eon/search", params=params or None)

    def get_quote(self, quote_id: str) -> Any:
        return self._get(f"/eon/quotes/{quote_id}")

    def summarize_quote(self, quote_id: str) -> Any:
        return self._get(f"/eon/quotes/{quote_id}/summary")

    def calculate_quote(self, quote_id: str) -> Any:
        return self._post(f"/eon/quotes/{quote_id}/calculate")

    def run_workflow(self, payload: dict) -> Any:
        return self._post("/workflow/quote", payload)

    def generate_report(self, quote_id: str, html: bool = False) -> Any:
        path = f"/eon/quotes/{quote_id}/report/html" if html else f"/eon/quotes/{quote_id}/report"
        return self._get(path)

    def export_holded_payload(self, quote_id: str) -> Any:
        return self._get(f"/eon/quotes/{quote_id}/export/holded")

    def archive_quote(self, quote_id: str) -> Any:
        return self._post(f"/eon/quotes/{quote_id}/archive")
