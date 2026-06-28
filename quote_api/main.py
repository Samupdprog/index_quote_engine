"""Punto de entrada de la API."""

import json

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .eon_routes import eon_router
from .routes import router


class UTF8JSONResponse(JSONResponse):
    """JSONResponse con charset=utf-8 explícito en Content-Type.

    PowerShell 5.1 no asume UTF-8 por defecto cuando el Content-Type
    es 'application/json' sin charset, lo que causa mojibake en tildes.
    """
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
