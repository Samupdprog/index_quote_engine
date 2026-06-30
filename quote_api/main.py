"""Punto de entrada de la API."""

import json

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .catalog_routes import catalog_router
from .db_routes import db_router
from .eon_routes import eon_router
from .learning_routes import learning_router
from .routes import router
from .workflow_routes import workflow_router


class UTF8JSONResponse(JSONResponse):
    """JSONResponse con charset=utf-8 explicito en Content-Type."""
    media_type = "application/json; charset=utf-8"

    def render(self, content: object) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


app = FastAPI(
    title="Index Quote Engine",
    description="Motor de presupuestos para Index Clima",
    version="0.1.0",
    default_response_class=UTF8JSONResponse,
)

app.include_router(router)
app.include_router(eon_router)
app.include_router(workflow_router)
app.include_router(catalog_router)
app.include_router(learning_router)
app.include_router(db_router)
