"""Endpoints del catálogo de productos — /catalog/..."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

catalog_router = APIRouter(prefix="/catalog", tags=["Catalog"])


def _get_catalog_service():
    """Obtiene el CatalogService con sesión DB si disponible."""
    from quote_engine.catalog.service import CatalogService
    from quote_engine.db.session import get_session_factory

    factory = get_session_factory()
    if factory is None:
        return CatalogService(db_session=None)
    session = factory()
    return CatalogService(db_session=session)


@catalog_router.get("/search")
def catalog_search(
    q: str,
    category: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Busca productos en el catálogo por texto libre."""
    if not q.strip():
        raise HTTPException(status_code=422, detail="El parámetro 'q' no puede estar vacío")

    service = _get_catalog_service()
    result = service.search_products(q, category=category, limit=limit)
    return result.model_dump()


@catalog_router.get("/product/{code}")
def catalog_get_by_code(code: str) -> dict:
    """Obtiene un producto por código interno exacto."""
    service = _get_catalog_service()
    result = service.get_product_by_code(code)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Producto con código {code!r} no encontrado")
    return result.model_dump()


@catalog_router.get("/best-price")
def catalog_best_price(
    q: str,
    preferred_supplier: Optional[str] = None,
) -> dict:
    """Devuelve el mejor precio disponible para un producto."""
    from quote_engine.pricing.selector import PriceSelector

    service = _get_catalog_service()
    selector = PriceSelector()
    result = selector.select_from_catalog(
        query=q,
        catalog_service=service,
        preferred_supplier=preferred_supplier,
    )
    return result.model_dump()


class ImportExcelRequest(BaseModel):
    file_path: str
    force: bool = False
    dry_run: bool = False


@catalog_router.post("/import-excel")
def catalog_import_excel(body: ImportExcelRequest) -> dict:
    """Importa un archivo Excel de productos a la base de datos."""
    from quote_engine.importers.excel_products_importer import ExcelProductsImporter
    from quote_engine.db.session import get_session_factory
    from pathlib import Path

    path = Path(body.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {body.file_path}")

    session = None
    if not body.dry_run:
        factory = get_session_factory()
        if factory:
            session = factory()

    try:
        importer = ExcelProductsImporter(db_session=session)
        report = importer.run(path, force=body.force, report_output_dir="data/reports")
        return {
            "ok": True,
            "total_rows": report.total_rows,
            "created_products": report.created_products,
            "created_prices": report.created_prices,
            "warnings_count": report.warnings_count,
            "errors_count": report.errors_count,
            "suppliers_detected": report.suppliers_detected,
            "warnings": report.warnings[:20],  # primeros 20
            "errors": report.errors[:10],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if session:
            session.close()
