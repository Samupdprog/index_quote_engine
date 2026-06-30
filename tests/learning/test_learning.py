"""Tests del sistema de correcciones y aprendizajes."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from quote_engine.db.base import Base
from quote_engine.db.models import QuoteCase, LearningItem
from quote_engine.learning.corrections import register_correction, list_corrections
from quote_engine.learning.proposer import (
    propose_learning_from_correction,
    list_pending_learnings,
    _infer_type,
)
from quote_engine.learning.approval import approve_learning, reject_learning


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
def quote_case(session):
    """Crea un caso de presupuesto con referencia única por test.

    register_correction hace commit(), así que el QuoteCase queda persistido en
    el engine de módulo. Para evitar UNIQUE constraint en ejecuciones sucesivas
    del mismo test o entre tests, se usa un sufijo UUID por invocación.
    """
    ref = f"PRE-2026-LEARN-{uuid.uuid4().hex[:8].upper()}"
    case = QuoteCase(reference=ref, client_name="Test Client")
    session.add(case)
    session.flush()
    return case


class TestCorrections:
    def test_register_correction(self, session, quote_case):
        corr_id = register_correction(
            db_session=session,
            quote_reference=quote_case.reference,
            field_path="lines[0].transport",
            old_value="30.0",
            new_value="15.0",
            correction_reason="Obra cercana",
            created_by="Samuel",
        )
        assert corr_id is not None
        assert isinstance(corr_id, int)

    def test_correction_on_nonexistent_quote(self, session):
        result = register_correction(
            db_session=session,
            quote_reference="PRE-NO-EXISTE",
            field_path="field",
            old_value="old",
            new_value="new",
        )
        assert result is None

    def test_list_corrections(self, session, quote_case):
        register_correction(
            db_session=session,
            quote_reference=quote_case.reference,
            field_path="header.global_margin",
            old_value="35.0",
            new_value="40.0",
        )
        corrections = list_corrections(session, quote_case.reference)
        assert len(corrections) >= 1
        assert all("field_path" in c for c in corrections)


class TestProposer:
    def test_infer_transport_type(self):
        t = _infer_type("lines[0].transport", "30", "15")
        assert t == "transport_rule"

    def test_infer_labor_type(self):
        t = _infer_type("labor_hours", "8", "6")
        assert t == "labor_rule"

    def test_infer_pricing_default(self):
        t = _infer_type("some_random_field", "a", "b")
        assert t == "pricing_rule"

    def test_propose_learning_from_correction(self, session, quote_case):
        # Crear corrección primero
        corr_id = register_correction(
            db_session=session,
            quote_reference=quote_case.reference,
            field_path="transport",
            old_value="30",
            new_value="15",
            correction_reason="Test",
        )
        assert corr_id is not None

        learning_id = propose_learning_from_correction(session, corr_id)
        assert learning_id is not None

    def test_proposed_learning_is_pending(self, session, quote_case):
        corr_id = register_correction(
            db_session=session,
            quote_reference=quote_case.reference,
            field_path="margin",
            old_value="35",
            new_value="40",
        )
        learning_id = propose_learning_from_correction(session, corr_id)

        # Verificar que está pending
        item = session.query(LearningItem).filter_by(id=learning_id).first()
        assert item is not None
        assert item.status == "pending"
        assert item.approved_by is None
        assert item.approved_at is None

    def test_list_pending_learnings(self, session):
        items = list_pending_learnings(session)
        assert isinstance(items, list)
        for item in items:
            assert item["status"] == "pending"


class TestApproval:
    def test_approve_learning(self, session, quote_case):
        # Crear corrección + proponer aprendizaje
        corr_id = register_correction(
            db_session=session,
            quote_reference=quote_case.reference,
            field_path="supplier",
            old_value="Frigicoll",
            new_value="Airwell",
        )
        learning_id = propose_learning_from_correction(session, corr_id)
        assert learning_id is not None

        result = approve_learning(session, learning_id, approved_by="Samuel")
        assert result is not None
        assert result["status"] == "approved"
        assert result["approved_by"] == "Samuel"

    def test_cannot_auto_approve_with_eon(self, session, quote_case):
        """EON no puede aprobar aprendizajes."""
        corr_id = register_correction(
            db_session=session,
            quote_reference=quote_case.reference,
            field_path="auto_test",
            old_value="a",
            new_value="b",
        )
        learning_id = propose_learning_from_correction(session, corr_id)

        result = approve_learning(session, learning_id, approved_by="EON")
        assert result is None  # Bloqueado

    def test_cannot_auto_approve_with_auto(self, session, quote_case):
        """'auto' como aprobador es rechazado."""
        corr_id = register_correction(
            db_session=session,
            quote_reference=quote_case.reference,
            field_path="auto_test2",
            old_value="x",
            new_value="y",
        )
        learning_id = propose_learning_from_correction(session, corr_id)

        result = approve_learning(session, learning_id, approved_by="auto")
        assert result is None

    def test_reject_learning(self, session, quote_case):
        corr_id = register_correction(
            db_session=session,
            quote_reference=quote_case.reference,
            field_path="reject_test",
            old_value="a",
            new_value="b",
        )
        learning_id = propose_learning_from_correction(session, corr_id)

        result = reject_learning(session, learning_id, rejected_by="Samuel")
        assert result is not None
        assert result["status"] == "rejected"

    def test_approved_learning_has_timestamp(self, session, quote_case):
        corr_id = register_correction(
            db_session=session,
            quote_reference=quote_case.reference,
            field_path="timestamp_test",
            old_value="a",
            new_value="b",
        )
        learning_id = propose_learning_from_correction(session, corr_id)

        result = approve_learning(session, learning_id, approved_by="Samuel",
                                   generate_obsidian_note=False)
        assert result["approved_at"] is not None
