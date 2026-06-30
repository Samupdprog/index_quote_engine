"""Tests de capa DB — modelos SQLAlchemy.

Estos tests usan SQLite en memoria para no requerir PostgreSQL en CI.
Comprueban que los modelos se definen correctamente y las tablas se crean.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from quote_engine.db.base import Base
from quote_engine.db.models import (
    ErrorCase,
    LearningItem,
    PriceImportBatch,
    Product,
    QuoteCase,
    QuoteCorrection,
    QuoteLineItem,
    QuoteTotalRecord,
    Supplier,
    SupplierPrice,
)


@pytest.fixture(scope="module")
def engine():
    """Engine SQLite en memoria para tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    """Sesión de test con rollback automático."""
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.rollback()
    db.close()


class TestTablesExist:
    """Verifica que todas las tablas se crean correctamente."""

    EXPECTED_TABLES = {
        "suppliers",
        "products",
        "supplier_prices",
        "price_import_batches",
        "quote_cases",
        "quote_line_items",
        "quote_totals",
        "quote_corrections",
        "learning_items",
        "error_cases",
    }

    def test_all_tables_created(self, engine):
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert self.EXPECTED_TABLES == tables, f"Tablas faltantes: {self.EXPECTED_TABLES - tables}"


class TestSupplierModel:
    def test_create_supplier(self, session):
        supplier = Supplier(name="Frigicoll", normalized_name="frigicoll")
        session.add(supplier)
        session.flush()

        assert supplier.id is not None
        assert supplier.is_active is True
        assert supplier.name == "Frigicoll"

    def test_supplier_required_fields(self, session):
        with pytest.raises(Exception):
            supplier = Supplier()  # name es obligatorio
            session.add(supplier)
            session.flush()


class TestProductModel:
    def test_create_product(self, session):
        product = Product(
            description="Tubería de cobre 3/8",
            normalized_description="tuberia cobre 3/8",
            category="materiales",
        )
        session.add(product)
        session.flush()

        assert product.id is not None
        assert product.is_active is True

    def test_product_with_code(self, session):
        product = Product(
            internal_code="TUB-CU-3/8",
            description="Tubería de cobre 3/8",
            normalized_description="tuberia cobre 3/8",
        )
        session.add(product)
        session.flush()
        assert product.internal_code == "TUB-CU-3/8"


class TestSupplierPriceModel:
    def test_create_price(self, session):
        supplier = Supplier(name="Test", normalized_name="test")
        product = Product(description="Test producto", normalized_description="test producto")
        session.add_all([supplier, product])
        session.flush()

        price = SupplierPrice(
            product_id=product.id,
            supplier_id=supplier.id,
            net_unit_price=12.50,
            confidence="alta",
        )
        session.add(price)
        session.flush()

        assert price.id is not None
        assert price.net_unit_price == 12.50
        assert price.is_current is True
        assert price.currency == "EUR"

    def test_price_confidence_values(self, session):
        """Confidence puede ser alta/media/baja."""
        supplier = Supplier(name="S2", normalized_name="s2")
        product = Product(description="P2", normalized_description="p2")
        session.add_all([supplier, product])
        session.flush()

        for conf in ["alta", "media", "baja"]:
            price = SupplierPrice(
                product_id=product.id,
                supplier_id=supplier.id,
                net_unit_price=1.0,
                confidence=conf,
            )
            session.add(price)
            session.flush()
            assert price.confidence == conf


class TestQuoteCaseModel:
    def test_create_quote_case(self, session):
        case = QuoteCase(reference="PRE-2026-TEST", client_name="Cliente Test")
        session.add(case)
        session.flush()

        assert case.id is not None
        assert case.status == "draft"
        assert case.reference == "PRE-2026-TEST"

    def test_quote_case_with_line_items(self, session):
        case = QuoteCase(reference="PRE-2026-TEST2", client_name="Cliente 2")
        session.add(case)
        session.flush()

        line = QuoteLineItem(
            quote_case_id=case.id,
            description="Split 1x1",
            quantity=1.0,
            unit="ud",
            internal_unit_cost=500.0,
            client_unit_price=750.0,
        )
        session.add(line)
        session.flush()

        assert line.id is not None
        assert line.quote_case_id == case.id

    def test_quote_case_with_totals(self, session):
        case = QuoteCase(reference="PRE-2026-TEST3")
        session.add(case)
        session.flush()

        totals = QuoteTotalRecord(
            quote_case_id=case.id,
            internal_total_cost=500.0,
            client_total_without_igic=750.0,
            igic_rate=7.0,
            igic_amount=52.50,
            client_total_with_igic=802.50,
            benefit=250.0,
            margin_percent=50.0,
        )
        session.add(totals)
        session.flush()

        assert totals.id is not None
        assert totals.client_total_with_igic == 802.50


class TestLearningItemModel:
    def test_create_learning_item(self, session):
        item = LearningItem(
            type="transport_rule",
            title="Transporte reducido",
            description="Samuel cambió transporte de 30 a 15 €/día",
            proposed_rule="Si obra cercana, permitir transporte reducido",
            status="pending",
        )
        session.add(item)
        session.flush()

        assert item.id is not None
        assert item.status == "pending"
        assert item.approved_by is None

    def test_learning_item_not_auto_approved(self, session):
        """Un aprendizaje nunca se aprueba automáticamente."""
        item = LearningItem(
            type="pricing_rule",
            title="Test",
            status="pending",
        )
        session.add(item)
        session.flush()

        assert item.status == "pending"
        assert item.approved_at is None


class TestQuoteCorrectionModel:
    def test_create_correction(self, session):
        case = QuoteCase(reference="PRE-2026-CORR")
        session.add(case)
        session.flush()

        corr = QuoteCorrection(
            quote_case_id=case.id,
            field_path="lines[0].transport",
            old_value="30.0",
            new_value="15.0",
            correction_reason="Obra cercana",
            created_by="Samuel",
        )
        session.add(corr)
        session.flush()

        assert corr.id is not None
        assert corr.created_by == "Samuel"


class TestDBConnectionCheck:
    def test_session_can_execute_query(self, session):
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1
