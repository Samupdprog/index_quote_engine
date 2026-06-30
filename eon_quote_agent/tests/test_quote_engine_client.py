"""Tests del cliente QuoteEngineClient con mocks HTTP."""

import pytest
import httpx
from unittest.mock import patch, MagicMock

from eon.quote_engine_client import QuoteEngineClient, QuoteEngineError, QuoteNotFoundError


def _mock_response(json_data, status_code=200):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    return mock


def _mock_error_response(json_data, status_code):
    """Mock que hace que raise_for_status() lance HTTPStatusError."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status.side_effect = httpx.HTTPStatusError(
        f"{status_code} Error",
        request=MagicMock(),
        response=mock,
    )
    return mock


class TestQuoteEngineClient:
    def setup_method(self):
        self.client = QuoteEngineClient(base_url="http://test-engine:8000")

    def test_get_tools_ok(self):
        with patch("httpx.get", return_value=_mock_response({"tools": ["search"]})):
            result = self.client.get_tools()
        assert "tools" in result

    def test_search_quotes_ok(self):
        payload = {"results": [{"id": "PRE-2026-0001"}]}
        with patch("httpx.get", return_value=_mock_response(payload)):
            result = self.client.search_quotes(client_name="Citanias")
        assert result["results"][0]["id"] == "PRE-2026-0001"

    def test_get_quote_ok(self):
        payload = {"id": "PRE-2026-0001", "client": "Citanias"}
        with patch("httpx.get", return_value=_mock_response(payload)):
            result = self.client.get_quote("PRE-2026-0001")
        assert result["id"] == "PRE-2026-0001"

    def test_get_quote_not_found_raises(self):
        mock = _mock_response({}, status_code=404)
        with patch("httpx.get", return_value=mock):
            with pytest.raises(QuoteNotFoundError):
                self.client.get_quote("PRE-2026-9999")

    def test_connection_error_raises_quote_engine_error(self):
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(QuoteEngineError, match="conectar"):
                self.client.get_tools()

    def test_timeout_raises_quote_engine_error(self):
        with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(QuoteEngineError, match="tardó"):
                self.client.search_quotes()

    def test_summarize_quote_ok(self):
        payload = {"summary": "Total: 10.000 €"}
        with patch("httpx.get", return_value=_mock_response(payload)):
            result = self.client.summarize_quote("PRE-2026-0001")
        assert "summary" in result

    def test_run_workflow_ok(self):
        payload = {"quote_id": "PRE-2026-0002", "status": "created"}
        with patch("httpx.post", return_value=_mock_response(payload)):
            result = self.client.run_workflow({"client_name": "Citanias"})
        assert result["status"] == "created"

    def test_export_holded_payload_ok(self):
        payload = {"holded_invoice": {}}
        with patch("httpx.get", return_value=_mock_response(payload)):
            result = self.client.export_holded_payload("PRE-2026-0001")
        assert "holded_invoice" in result

    def test_archive_quote_ok(self):
        payload = {"archived": True}
        with patch("httpx.post", return_value=_mock_response(payload)):
            result = self.client.archive_quote("PRE-2026-0001")
        assert result["archived"] is True

    def test_http_422_raises_quote_engine_error(self):
        """HTTP 422 del motor se convierte en QuoteEngineError, no en traceback."""
        detail = {"detail": [{"msg": "field required", "loc": ["body", "input_path"]}]}
        mock = _mock_error_response(detail, 422)
        with patch("httpx.post", return_value=mock):
            with pytest.raises(QuoteEngineError, match="422"):
                self.client.run_workflow({})

    def test_http_422_includes_details(self):
        """Los details de FastAPI quedan accesibles en el error."""
        detail = {"detail": [{"msg": "field required"}]}
        mock = _mock_error_response(detail, 422)
        with patch("httpx.post", return_value=mock):
            with pytest.raises(QuoteEngineError) as exc_info:
                self.client.run_workflow({})
        assert exc_info.value.details == detail

    def test_http_500_raises_quote_engine_error(self):
        mock = _mock_error_response({"detail": "Internal Server Error"}, 500)
        with patch("httpx.get", return_value=mock):
            with pytest.raises(QuoteEngineError, match="500"):
                self.client.get_tools()
