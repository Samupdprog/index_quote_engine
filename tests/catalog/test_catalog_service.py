"""Tests del servicio de catálogo."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quote_engine.catalog.normalizer import normalize_for_search, similarity_score, tokenize
from quote_engine.catalog.service import CatalogService
from quote_engine.db.base import Base
from quote_engine.db.models import Product, Supplier, SupplierPrice


@pytest.fixture(scope="module")
def engine():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.rollback()
    db.close()


@pytest.fixture
def populated_session(session):
    """Sesión con datos de prueba poblados."""
    # Proveedores
    frigicoll = Supplier(name="Frigicoll", normalized_name="frigicoll")
    airwell = Supplier(name="Airwell", normalized_name="airwell")
    session.add_all([frigicoll, airwell])
    session.flush()

    # Productos
    split_1x1 = Product(
        description="Split 1x1 Daitsu 9000 BTU",
        normalized_description="split 1x1 daitsu 9000 btu",
        category="climatizacion",
        internal_code="SPLIT-1X1-9K",
    )
    split_2x1 = Product(
        description="Split 2x1 Daitsu 18+12",
        normalized_description="split 2x1 daitsu 18+12",
        category="climatizacion",
    )
    tuberia = Product(
        description="Tubería de cobre 3/8",
        normalized_description="tuberia de cobre 3/8",
        category="materiales",
        unit_calc="m",
    )
    cable = Product(
        description="Cable eléctrico 2.5mm",
        normalized_description="cable electrico 2.5mm",
        category="materiales",
    )
    session.add_all([split_1x1, split_2x1, tuberia, cable])
    session.flush()

    # Precios
    session.add_all([
        SupplierPrice(product_id=split_1x1.id, supplier_id=frigicoll.id,
                      net_unit_price=650.0, confidence="alta", is_current=True,
                      source_file="test.xlsx", source_sheet="Frigicoll"),
        SupplierPrice(product_id=split_2x1.id, supplier_id=frigicoll.id,
                      net_unit_price=1100.0, confidence="alta", is_current=True,
                      source_file="test.xlsx"),
        SupplierPrice(product_id=tuberia.id, supplier_id=frigicoll.id,
                      net_unit_price=2.50, confidence="media", is_current=True),
        SupplierPrice(product_id=cable.id, supplier_id=airwell.id,
                      net_unit_price=1.80, confidence="alta", is_current=True),
        # Precio con confianza baja — no debe aparecer en find_best_price
        SupplierPrice(product_id=split_1x1.id, supplier_id=airwell.id,
                      net_unit_price=500.0, confidence="baja", is_current=True),
    ])
    session.flush()
    yield session


class TestNormalizer:
    def test_normalize_removes_accents(self):
        assert normalize_for_search("Tubería") == "tuberia"

    def test_normalize_lowercase(self):
        assert normalize_for_search("SPLIT 1X1") == "split 1x1"

    def test_tokenize_removes_stop_words(self):
        tokens = tokenize("tubería de cobre")
        assert "de" not in tokens
        assert "tuberia" in tokens
        assert "cobre" in tokens

    def test_similarity_identical(self):
        score = similarity_score("split 1x1", "split 1x1")
        assert score == 1.0

    def test_similarity_partial(self):
        score = similarity_score("split", "split 1x1 daitsu")
        assert 0 < score < 1

    def test_similarity_no_match(self):
        score = similarity_score("nitrógeno", "cable eléctrico")
        assert score < 0.3


class TestCatalogServiceNoDB:
    def test_search_without_db_returns_empty(self):
        service = CatalogService(db_session=None)
        result = service.search_products("split")
        assert result.total == 0
        assert len(result.warnings) > 0
        assert "no disponible" in result.warnings[0].lower()

    def test_get_product_by_code_without_db(self):
        service = CatalogService(db_session=None)
        result = service.get_product_by_code("SPLIT-1X1-9K")
        assert result is None

    def test_find_best_price_without_db(self):
        service = CatalogService(db_session=None)
        result = service.find_best_price("tubería")
        assert result is None


class TestCatalogServiceWithDB:
    def test_search_split_returns_results(self, populated_session):
        service = CatalogService(db_session=populated_session)
        result = service.search_products("split")
        assert result.total > 0
        descriptions = [r.description.lower() for r in result.results]
        assert any("split" in d for d in descriptions)

    def test_search_tuberia_returns_result(self, populated_session):
        service = CatalogService(db_session=populated_session)
        result = service.search_products("tubería")
        assert result.total > 0

    def test_search_cable_returns_result(self, populated_session):
        service = CatalogService(db_session=populated_session)
        result = service.search_products("cable")
        assert result.total > 0

    def test_search_nonexistent_returns_empty(self, populated_session):
        service = CatalogService(db_session=populated_session)
        result = service.search_products("producto que no existe xyz123")
        assert result.total == 0

    def test_search_result_has_source(self, populated_session):
        service = CatalogService(db_session=populated_session)
        result = service.search_products("split 1x1")
        if result.total > 0:
            r = result.results[0]
            assert r.supplier is not None
            assert r.net_unit_price > 0
            assert r.confidence in {"alta", "media", "baja"}
            assert r.reason != ""

    def test_get_product_by_code_exact(self, populated_session):
        service = CatalogService(db_session=populated_session)
        result = service.get_product_by_code("SPLIT-1X1-9K")
        assert result is not None
        assert result.confidence in {"alta", "media"}
        assert result.reason == "código exacto"

    def test_get_product_by_code_not_found(self, populated_session):
        service = CatalogService(db_session=populated_session)
        result = service.get_product_by_code("NO-EXISTE-999")
        assert result is None

    def test_find_best_price_prefers_high_confidence(self, populated_session):
        """find_best_price no debe devolver precios con confianza baja."""
        service = CatalogService(db_session=populated_session)
        result = service.find_best_price("split 1x1")
        if result is not None:
            assert result.confidence != "baja"

    def test_find_best_price_returns_price(self, populated_session):
        service = CatalogService(db_session=populated_session)
        result = service.find_best_price("cable")
        assert result is not None
        assert result.net_unit_price > 0

    def test_has_high_confidence_flag(self, populated_session):
        service = CatalogService(db_session=populated_session)
        result = service.search_products("split 1x1")
        # Split 1x1 tiene precio con confianza alta
        assert result.has_high_confidence is True
