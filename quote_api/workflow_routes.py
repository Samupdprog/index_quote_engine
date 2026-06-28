"""Endpoints de workflow — /workflow/..."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from quote_engine.workflow import run_quote_workflow

workflow_router = APIRouter(prefix="/workflow", tags=["Workflow"])


class WorkflowRequest(BaseModel):
    input_path: str
    quote_id: str | None = None
    created_by: str = "EON"
    source: str = "workflow"
    status: str = "draft"
    project_type: str | None = None
    tags: list[str] | None = None
    generate_report: bool = True
    export_holded: bool = True
    report_output_path: str | None = None
    holded_output_path: str | None = None


@workflow_router.post("/quote")
def workflow_quote(body: WorkflowRequest) -> dict:
    result = run_quote_workflow(
        input_path=body.input_path,
        quote_id=body.quote_id,
        created_by=body.created_by,
        source=body.source,
        status=body.status,
        project_type=body.project_type,
        tags=body.tags,
        generate_report=body.generate_report,
        export_holded=body.export_holded,
        report_output_path=body.report_output_path,
        holded_output_path=body.holded_output_path,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=422, detail=result.get("error", "Error en workflow"))
    return result
