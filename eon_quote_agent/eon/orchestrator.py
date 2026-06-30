"""Orquestador principal de EON."""

from .intent_parser import parse_intent
from .models import ClarifyingQuestion, EONResult, UserRequest
from .quote_engine_client import QuoteEngineClient, QuoteEngineError, QuoteNotFoundError


def handle_user_request(
    text: str,
    files: list[str] | None = None,
    client: QuoteEngineClient | None = None,
) -> EONResult:
    request = UserRequest(text=text, files=files or [])
    intent = parse_intent(request.text)
    _client = client or QuoteEngineClient()

    # Intención desconocida
    if intent.action == "unknown":
        return EONResult(
            success=False,
            action="unknown",
            summary=(
                "No he entendido qué quieres hacer. "
                "Puedes pedirme crear, buscar, resumir, generar informe, "
                "exportar o archivar un presupuesto."
            ),
        )

    # Faltan campos necesarios para cualquier acción
    if intent.missing_fields:
        questions = _build_questions(intent.action, intent.missing_fields, request.files)
        return EONResult(
            success=False,
            action=intent.action,
            questions=questions,
            summary="Necesito más información antes de continuar.",
        )

    # --- Acciones ---
    try:
        if intent.action == "search_quotes":
            data = _client.search_quotes(client_name=intent.client_name, tags=intent.tags)
            return EONResult(
                success=True,
                action="search_quotes",
                data=data,
                summary=_summarize_search(data, intent.client_name),
            )

        if intent.action == "summarize_quote":
            data = _client.summarize_quote(intent.quote_id)  # type: ignore[arg-type]
            return EONResult(
                success=True,
                action="summarize_quote",
                data=data,
                summary=str(data),
            )

        if intent.action == "calculate_quote":
            data = _client.calculate_quote(intent.quote_id)  # type: ignore[arg-type]
            return EONResult(
                success=True,
                action="calculate_quote",
                data=data,
                summary=str(data),
            )

        if intent.action == "generate_report":
            data = _client.generate_report(intent.quote_id)  # type: ignore[arg-type]
            return EONResult(
                success=True,
                action="generate_report",
                data=data,
                summary="Informe generado correctamente.",
            )

        if intent.action == "export_holded":
            data = _client.export_holded_payload(intent.quote_id)  # type: ignore[arg-type]
            return EONResult(
                success=True,
                action="export_holded",
                data=data,
                summary="Payload Holded generado. Requiere confirmación humana antes de enviar.",
            )

        if intent.action == "archive_quote":
            data = _client.archive_quote(intent.quote_id)  # type: ignore[arg-type]
            return EONResult(
                success=True,
                action="archive_quote",
                data=data,
                summary=f"Presupuesto {intent.quote_id} archivado.",
            )

        if intent.action == "create_quote":
            # Necesita archivo JSON del proveedor
            if not request.files:
                return EONResult(
                    success=False,
                    action="create_quote",
                    questions=[
                        ClarifyingQuestion(
                            field="supplier_files",
                            question=(
                                "¿Puedes adjuntar el archivo JSON del proveedor "
                                "para crear el presupuesto?"
                            ),
                        )
                    ],
                    summary="Necesito el archivo JSON del proveedor para continuar.",
                )
            payload = _build_workflow_payload(intent, request.files)
            data = _client.run_workflow(payload)
            return EONResult(
                success=True,
                action="create_quote",
                data=data,
                summary="Presupuesto creado correctamente a través del motor.",
            )

    except QuoteNotFoundError as exc:
        return EONResult(
            success=False,
            action=intent.action,
            error=str(exc),
            summary=f"No encontré el presupuesto {intent.quote_id}.",
            details=exc.details,
        )
    except QuoteEngineError as exc:
        return EONResult(
            success=False,
            action=intent.action,
            error=str(exc),
            summary="Error al conectar con el motor de presupuestos.",
            details=exc.details,
        )

    return EONResult(
        success=False,
        action=intent.action,
        summary=f"Acción '{intent.action}' no implementada aún.",
    )


# ------------------------------------------------------------------
# Helpers privados
# ------------------------------------------------------------------

def _build_questions(
    action: str, missing: list[str], files: list[str]
) -> list[ClarifyingQuestion]:
    questions = []
    for field in missing:
        if field == "quote_id":
            questions.append(
                ClarifyingQuestion(
                    field="quote_id",
                    question="¿Cuál es el ID del presupuesto? (ej. PRE-2026-0001)",
                )
            )
        elif field == "client_name":
            questions.append(
                ClarifyingQuestion(
                    field="client_name",
                    question="¿Para qué cliente es el presupuesto?",
                )
            )
        elif field == "supplier_files" and not files:
            questions.append(
                ClarifyingQuestion(
                    field="supplier_files",
                    question="¿Puedes adjuntar el archivo JSON del proveedor?",
                )
            )
    return questions


def _summarize_search(data: object, client_name: str | None) -> str:
    label = f"de '{client_name}'" if client_name else ""
    if isinstance(data, list):
        n = len(data)
        return f"Encontré {n} presupuesto{'s' if n != 1 else ''} {label}.".strip()
    if isinstance(data, dict):
        items = data.get("results") or data.get("quotes") or []
        n = len(items) if isinstance(items, list) else "?"
        return f"Encontré {n} presupuesto{'s' if n != 1 else ''} {label}.".strip()
    return "Búsqueda completada."


def _build_workflow_payload(intent, files: list[str]) -> dict:
    return {
        "input_path": files[0],
        "quote_id": None,
        "created_by": "EON",
        "source": "eon",
        "status": "draft",
        "project_type": intent.project_type,
        "tags": intent.tags,
        "generate_report": True,
        "export_holded": True,
        "report_output_path": None,
        "holded_output_path": None,
    }
