"""Tests del repositorio de presupuestos en DB."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quote_engine.db.base import Base
from quote_engine.db.repositories.quotes import (
    get_quote_case,
    list_recent_quote_cases,
    save_quote_case,
)


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


SAMPLE_SNAPSHOT = {
    "header": {
        "client_name": "Cliente Test",
        "tax": 7.0,
        "global_margin": 35.0,
    },
    "lines": [
        {
            "id": "line-1",
            "description": "Split 1x1",
            "quantity": 1.0,
            "unit": "ud",
            "type": "material",
        }
    ],
}

SAMPLE_CALCULATED = {
    "lines": [
        {
            "line_id": "line-1",
            "description": "Split 1x1",
            "quantity": 1.0,
            "unit": "ud",
            "type": "material",
            "cost_unit": 650.0,
            "cost_total": 650.0,
            "sale_unit_without_tax": 877.50,
            "sale_total_without_tax": 877.50,
            "sale_mode": "margin",
        }
    ],
    "totals": {
        "cost_subtotal": 650.0,
        "sale_subtotal": 877.50,
        "tax_amount": 61.43,
        "final_total": 938.93,
        "gross_profit": 227.50,
        "gross_profit_percent": 35.0,
    },
}


class TestSaveQuoteCase:
    def test_save_new_quote(self, session):
        case_id = save_quote_case(
            db_session=session,
            reference="PRE-2026-TEST001",
            snapshot_dict=SAMPLE_SNAPSHOT,
            calculated_dict=SAMPLE_CALCULATED,
            client_name="Cliente Test",
            status="draft",
        )
        assert case_id is not None
        assert isinstance(case_id, int)

    def test_save_and_retrieve(self, session):
        save_quote_case(
            db_session=session,
            reference="PRE-2026-TEST002",
            snapshot_dict=SAMPLE_SNAPSHOT,
            calculated_dict=SAMPLE_CALCULATED,
            client_name="Cliente Dos",
        )

        case = get_quote_case(session, "PRE-2026-TEST002")
        assert case is not None
        assert case["reference"] == "PRE-2026-TEST002"
        assert case["client_name"] == "Cliente Dos"

    def test_save_saves_totals(self, session):
        save_quote_case(
            db_session=session,
            reference="PRE-2026-TEST003",
            snapshot_dict=SAMPLE_SNAPSHOT,
            calculated_dict=SAMPLE_CALCULATED,
        )

        case = get_quote_case(session, "PRE-2026-TEST003")
        assert case["totals"] is not None
        assert case["totals"]["client_total_with_igic"] == pytest.approx(938.93)
        assert case["totals"]["benefit"] == pytest.approx(227.50)

    def test_save_saves_line_items(self, session):
        save_quote_case(
            db_session=session,
            reference="PRE-2026-TEST004",
            snapshot_dict=SAMPLE_SNAPSHOT,
            calculated_dict=SAMPLE_CALCULATED,
        )

        case = get_quote_case(session, "PRE-2026-TEST004")
        assert len(case["lines"]) == 1
        assert case["lines"][0]["description"] == "Split 1x1"

    def test_update_existing_quote(self, session):
        save_quote_case(
            db_session=session,
            reference="PRE-2026-TEST005",
            snapshot_dict=SAMPLE_SNAPSHOT,
            status="draft",
        )
        # Actualizar
        save_quote_case(
            db_session=session,
            reference="PRE-2026-TEST005",
            snapshot_dict=SAMPLE_SNAPSHOT,
            status="sent",
        )

        case = get_quote_case(session, "PRE-2026-TEST005")
        assert case["status"] == "sent"


class TestGetQuoteCase:
    def test_get_nonexistent_returns_none(self, session):
        result = get_quote_case(session, "PRE-NONEXISTENT")
        assert result is None


class TestListRecentQuoteCases:
    def test_list_returns_list(self, session):
        result = list_recent_quote_cases(session, limit=10)
        assert isinstance(result, list)

    def test_list_includes_recent_quotes(self, session):
        save_quote_case(
            db_session=session,
            reference="PRE-2026-RECENT",
            snapshot_dict=SAMPLE_SNAPSHOT,
            client_name="Cliente Reciente",
        )
        result = list_recent_quote_cases(session, limit=5)
        references = [r["reference"] for r in result]
        assert "PRE-2026-RECENT" in references

    def test_list_respects_limit(self, session):
        result = list_recent_quote_cases(session, limit=2)
        assert len(result) <= 2
