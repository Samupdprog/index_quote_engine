"""Servicio de catálogo — búsqueda de productos y precios.

El catálogo es la única capa que accede a la DB para buscar productos.
El motor de presupuestos (calculator.py) no accede a la DB directamente.

Prioridad de búsqueda:
    1. código exacto (internal_code)
    2. referencia proveedor exacta (supplier_reference)
    3. descripción normalizada exacta
    4. similitud por tokens
    5. categoría + similitud
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from .normalizer import normalize_for_search, similarity_score
from .schemas import CatalogSearchResponse, ProductSearchResult

logger = logging.getLogger(__name__)

# Umbral de similitud mínima para incluir un resultado
MIN_SIMILARITY = 0.3

# Precio antiguo: más de 18 meses sin actualización
PRICE_STALENESS_MONTHS = 18


def _is_stale(document_date: Optional[date]) -> bool:
    """True si la fecha del precio es anterior a PRICE_STALENESS_MONTHS."""
    if document_date is None:
        return False
    threshold = date.today() - timedelta(days=PRICE_STALENESS_MONTHS * 30)
    return document_date < threshold


def _orm_price_to_result(price, reason: str) -> ProductSearchResult:
    """Convierte un objeto ORM SupplierPrice a ProductSearchResult."""
    product = price.product
    supplier = price.supplier
    doc_date = None
    if price.document_date:
        doc_date = price.document_date.date() if isinstance(price.document_date, datetime) else price.document_date

    return ProductSearchResult(
        product_id=product.id,
        supplier_price_id=price.id,
        description=product.description,
        supplier=supplier.name,
        net_unit_price=price.net_unit_price,
        gross_unit_price=price.gross_unit_price,
        discount_percent=price.discount_percent,
        unit=product.unit_calc,
        confidence=price.confidence,
        reason=reason,
        source_file=price.source_file,
        source_sheet=price.source_sheet,
        source_row=price.source_row,
        document_date=doc_date,
        is_current=price.is_current,
    )


class CatalogService:
    """Servicio de búsqueda en catálogo de productos."""

    def __init__(self, db_session=None):
        """
        db_session: sesión SQLAlchemy. Si None, el servicio devuelve resultados vacíos
                    (modo sin-DB).
        """
        self.session = db_session

    def _is_available(self) -> bool:
        return self.session is not None

    def search_products(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> CatalogSearchResponse:
        """Busca productos en el catálogo por texto libre.

        Retorna resultados ordenados por confianza y similitud.
        """
        warnings: list[str] = []

        if not self._is_available():
            return CatalogSearchResponse(
                query=query,
                results=[],
                total=0,
                has_high_confidence=False,
                warnings=["Catálogo no disponible: base de datos no configurada"],
            )

        results: list[ProductSearchResult] = []
        query_norm = normalize_for_search(query)

        try:
            from quote_engine.db.models import Product, SupplierPrice

            # Cargar todos los productos activos con sus precios actuales
            # Para datasets grandes, esto se optimizaría con FTS o índices
            products = (
                self.session.query(Product)
                .filter(Product.is_active == True)  # noqa: E712
                .all()
            )

            scored: list[tuple[float, str, Product]] = []
            for product in products:
                if category and product.category and normalize_for_search(product.category) != normalize_for_search(category):
                    continue

                # Calcular similitud
                score = similarity_score(query, product.description)
                if score >= MIN_SIMILARITY:
                    reason = "similitud por texto"
                elif query_norm in normalize_for_search(product.description):
                    score = 0.5
                    reason = "coincidencia parcial"
                else:
                    continue

                scored.append((score, reason, product))

            # Ordenar por score descendente
            scored.sort(key=lambda x: x[0], reverse=True)

            for score, reason, product in scored[:limit]:
                # Obtener el precio actual más relevante
                current_price = (
                    self.session.query(SupplierPrice)
                    .filter_by(product_id=product.id, is_current=True)
                    .filter(SupplierPrice.confidence != "baja")
                    .order_by(SupplierPrice.net_unit_price.asc())  # el más barato
                    .first()
                )

                if current_price is None:
                    # Sin precio actual, buscar cualquier precio
                    current_price = (
                        self.session.query(SupplierPrice)
                        .filter_by(product_id=product.id)
                        .order_by(SupplierPrice.created_at.desc())
                        .first()
                    )
                    if current_price:
                        reason += " (precio histórico)"

                if current_price is None:
                    continue

                result = _orm_price_to_result(current_price, reason)

                # Avisar si precio antiguo
                if result.document_date and _is_stale(result.document_date):
                    result.confidence = "media"
                    warnings.append(
                        f"Precio de {result.description!r} ({result.supplier}) "
                        f"puede estar desactualizado (fecha: {result.document_date})"
                    )

                results.append(result)

        except Exception as exc:
            logger.error(f"Error en búsqueda de catálogo: {exc}")
            warnings.append(f"Error en búsqueda: {exc}")

        has_high = any(r.confidence == "alta" for r in results)

        return CatalogSearchResponse(
            query=query,
            results=results,
            total=len(results),
            has_high_confidence=has_high,
            warnings=warnings,
        )

    def get_product_by_code(self, code: str) -> Optional[ProductSearchResult]:
        """Busca un producto por código interno exacto."""
        if not self._is_available():
            return None

        try:
            from quote_engine.db.models import Product, SupplierPrice

            product = (
                self.session.query(Product)
                .filter(Product.internal_code == code, Product.is_active == True)  # noqa: E712
                .first()
            )
            if product is None:
                return None

            # Preferir precios con confianza alta o media antes que baja
            price = (
                self.session.query(SupplierPrice)
                .filter(
                    SupplierPrice.product_id == product.id,
                    SupplierPrice.is_current == True,  # noqa: E712
                    SupplierPrice.confidence != "baja",
                )
                .order_by(SupplierPrice.net_unit_price.asc())
                .first()
            )
            if price is None:
                # Fallback: cualquier precio si todos son baja
                price = (
                    self.session.query(SupplierPrice)
                    .filter_by(product_id=product.id, is_current=True)
                    .order_by(SupplierPrice.net_unit_price.asc())
                    .first()
                )
            if price is None:
                return None

            return _orm_price_to_result(price, "código exacto")

        except Exception as exc:
            logger.error(f"Error al buscar por código {code!r}: {exc}")
            return None

    def get_product_by_supplier_reference(
        self, reference: str, supplier_name: Optional[str] = None
    ) -> Optional[ProductSearchResult]:
        """Busca un producto por referencia de proveedor."""
        if not self._is_available():
            return None

        try:
            from quote_engine.db.models import Product, Supplier, SupplierPrice

            q = self.session.query(Product).filter(
                Product.supplier_reference == reference,
                Product.is_active == True,  # noqa: E712
            )
            products = q.all()
            if not products:
                return None

            product = products[0]
            price_q = self.session.query(SupplierPrice).filter_by(
                product_id=product.id, is_current=True
            )
            if supplier_name:
                from quote_engine.importers.excel_products_importer import normalize_supplier_name
                norm = normalize_supplier_name(supplier_name)
                price_q = price_q.join(Supplier).filter(Supplier.normalized_name == norm)

            price = price_q.order_by(SupplierPrice.net_unit_price.asc()).first()
            if price is None:
                return None

            return _orm_price_to_result(price, "referencia proveedor exacta")

        except Exception as exc:
            logger.error(f"Error al buscar por referencia {reference!r}: {exc}")
            return None

    def find_best_price(
        self,
        product_query: str,
        quantity: Optional[float] = None,
        preferred_supplier: Optional[str] = None,
    ) -> Optional[ProductSearchResult]:
        """Busca el mejor precio para un producto.

        Prioridad:
        1. Proveedor preferente con confianza alta
        2. Precio más bajo con confianza alta
        3. Precio más bajo con confianza media (marcado REVISAR)
        4. Ningún resultado → None
        """
        if not self._is_available():
            return None

        response = self.search_products(product_query, limit=20)
        if not response.results:
            return None

        # Filtrar por confianza
        high_conf = [r for r in response.results if r.confidence == "alta"]
        medium_conf = [r for r in response.results if r.confidence == "media"]

        # Proveedor preferente con confianza alta
        if preferred_supplier and high_conf:
            from quote_engine.importers.excel_products_importer import normalize_supplier_name
            pref_norm = normalize_supplier_name(preferred_supplier)
            for result in high_conf:
                from quote_engine.importers.excel_products_importer import normalize_supplier_name as ns
                if ns(result.supplier) == pref_norm:
                    result.reason = f"proveedor preferente ({result.supplier})"
                    return result

        # Precio mínimo con confianza alta
        if high_conf:
            best = min(high_conf, key=lambda r: r.net_unit_price)
            best.reason = f"mejor precio con confianza alta (de {len(high_conf)} candidatos)"
            return best

        # Precio mínimo con confianza media
        if medium_conf:
            best = min(medium_conf, key=lambda r: r.net_unit_price)
            best.reason = f"mejor precio con confianza media — REVISAR (de {len(medium_conf)} candidatos)"
            return best

        return None


# ---------------------------------------------------------------------------
# Instancia global opcional (se configura con set_default_session)
# ---------------------------------------------------------------------------

_default_service: Optional[CatalogService] = None


def get_catalog_service() -> CatalogService:
    """Devuelve el servicio de catálogo configurado, o uno vacío si no hay DB."""
    global _default_service
    if _default_service is not None:
        return _default_service
    return CatalogService(db_session=None)


def configure_catalog(db_session) -> None:
    """Configura el servicio de catálogo con una sesión de DB."""
    global _default_service
    _default_service = CatalogService(db_session=db_session)
