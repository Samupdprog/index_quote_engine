"""Tests del orquestador EON."""

import pytest
from unittest.mock import MagicMock, patch

from eon.orchestrator import handle_user_request
from eon.quote_engine_client import QuoteEngineError, QuoteNotFoundError


def _mock_client(**overrides):
    client = MagicMock()
    client.search_quotes.return_value = {"results": [{"id": "PRE-2026-0001"}]}
    client.summarize_quote.return_value = {"summary": "Total: 10.000 €"}
    client.generate_report.return_value = {"report": "ok"}
    client.export_holded_payload.return_value = {"holded_invoice": {}}
    client.archive_quote.return_value = {"archived": True}
    client.run_workflow.return_value = {"quote_id": "PRE-2026-0002", "status": "created"}
    for k, v in overrides.items():
        setattr(client, k, v)
    return client


class TestOrchestrator:

    def test_search_calls_client(self):
        client = _mock_client()
        result = handle_user_request("busca presupuestos de Citanias", client=client)
        assert result.success is True
        assert result.action == "search_quotes"
        client.search_quotes.assert_called_once()

    def test_summarize_calls_client(self):
        client = _mock_client()
        result = handle_user_request("resúmeme PRE-2026-0001", client=client)
        assert result.success is True
        assert result.action == "summarize_quote"
        client.summarize_quote.assert_called_once_with("PRE-2026-0001")

    def test_generate_report_calls_client(self):
        client = _mock_client()
        result = handle_user_request("genera informe de PRE-2026-0001", client=client)
        assert result.success is True
        assert result.action == "generate_report"
        client.generate_report.assert_called_once_with("PRE-2026-0001")

    def test_create_without_file_asks_for_file(self):
        client = _mock_client()
        result = handle_user_request("hazme un presupuesto para Citanias", client=client)
        assert result.success is False
        assert result.action == "create_quote"
        assert any(q.field == "supplier_files" for q in result.questions)
        client.run_workflow.assert_not_called()

    def test_create_with_file_calls_workflow(self):
        client = _mock_client()
        result = handle_user_request(
            "hazme un presupuesto para Citanias con este JSON",
            files=["data/input.json"],
            client=client,
        )
        assert result.success is True
        assert result.action == "create_quote"
        client.run_workflow.assert_called_once()

    def test_summarize_without_id_asks_for_id(self):
        client = _mock_client()
        result = handle_user_request("resúmeme el presupuesto", client=client)
        assert result.success is False
        assert any(q.field == "quote_id" for q in result.questions)
        client.summarize_quote.assert_not_called()

    def test_connection_error_returns_failure(self):
        client = _mock_client()
        client.search_quotes.side_effect = QuoteEngineError("No conecta")
        result = handle_user_request("busca presupuestos de Citanias", client=client)
        assert result.success is False
        assert "motor" in result.summary.lower() or result.error

    def test_quote_not_found_returns_failure(self):
        client = _mock_client()
        client.summarize_quote.side_effect = QuoteNotFoundError("Not found")
        result = handle_user_request("resúmeme PRE-2026-9999", client=client)
        assert result.success is False
        assert "PRE-2026-9999" in result.summary

    def test_unknown_intent_returns_failure(self):
        client = _mock_client()
        result = handle_user_request("hola qué tal", client=client)
        assert result.success is False
        assert result.action == "unknown"

    def test_create_with_file_payload_has_input_path(self):
        """El payload enviado al workflow debe contener input_path con la ruta del archivo."""
        client = _mock_client()
        handle_user_request(
            "hazme un presupuesto para Citanias",
            files=["data/input.json"],
            client=client,
        )
        payload = client.run_workflow.call_args[0][0]
        assert "input_path" in payload
        assert payload["input_path"] == "data/input.json"
        assert "supplier_files" not in payload

    def test_http_error_returns_controlled_failure(self):
        """Un error HTTP 422 del motor se muestra como EONResult controlado, sin traceback."""
        client = _mock_client()
        client.run_workflow.side_effect = QuoteEngineError(
            "Error HTTP 422 en /workflow/quote",
            details={"detail": [{"msg": "field required", "loc": ["body", "input_path"]}]},
        )
        result = handle_user_request(
            "hazme un presupuesto para Citanias",
            files=["data/input.json"],
            client=client,
        )
        assert result.success is False
        assert "422" in result.error
        assert result.details.get("detail") is not None
