"""Modelos SQLAlchemy para EON Index Quote Engine.

IMPORTANTE: Este archivo define los modelos ORM (base de datos).
No confundir con quote_engine/models.py que define los modelos Pydantic del motor.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


# ---------------------------------------------------------------------------
# Proveedores
# ---------------------------------------------------------------------------

class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    prices: Mapped[list["SupplierPrice"]] = relationship("SupplierPrice", back_populates="supplier")

    def __repr__(self) -> str:
        return f"<Supplier id={self.id} name={self.name!r}>"


# ---------------------------------------------------------------------------
# Productos
# ---------------------------------------------------------------------------

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    internal_code: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    supplier_reference: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_description: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(100))
    unit_purchase: Mapped[Optional[str]] = mapped_column(String(50))
    unit_calc: Mapped[Optional[str]] = mapped_column(String(50))
    conversion_factor: Mapped[Optional[float]] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    prices: Mapped[list["SupplierPrice"]] = relationship("SupplierPrice", back_populates="product")

    def __repr__(self) -> str:
        return f"<Product id={self.id} description={self.description[:40]!r}>"


# ---------------------------------------------------------------------------
# Precios de proveedor (historial)
# ---------------------------------------------------------------------------

class SupplierPrice(Base):
    __tablename__ = "supplier_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False, index=True)

    # Fuente de datos
    source_type: Mapped[Optional[str]] = mapped_column(String(50))   # excel, manual, holded
    source_file: Mapped[Optional[str]] = mapped_column(String(500))
    source_sheet: Mapped[Optional[str]] = mapped_column(String(200))
    source_row: Mapped[Optional[int]] = mapped_column(Integer)
    document_number: Mapped[Optional[str]] = mapped_column(String(100))
    document_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Precios
    quantity: Mapped[Optional[float]] = mapped_column(Float)
    gross_unit_price: Mapped[Optional[float]] = mapped_column(Float)
    discount_percent: Mapped[Optional[float]] = mapped_column(Float)
    net_unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    line_total: Mapped[Optional[float]] = mapped_column(Float)
    igic_rate: Mapped[Optional[float]] = mapped_column(Float)
    igic_included: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="EUR", nullable=False)

    # Calidad del dato
    confidence: Mapped[str] = mapped_column(String(20), default="media", nullable=False)
    # alta / media / baja
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    product: Mapped["Product"] = relationship("Product", back_populates="prices")
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="prices")

    def __repr__(self) -> str:
        return f"<SupplierPrice id={self.id} product={self.product_id} net={self.net_unit_price}>"


# ---------------------------------------------------------------------------
# Lotes de importación
# ---------------------------------------------------------------------------

class PriceImportBatch(Base):
    __tablename__ = "price_import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_file: Mapped[str] = mapped_column(String(500), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_products: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_products: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_prices: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warnings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    report_path: Mapped[Optional[str]] = mapped_column(String(500))

    def __repr__(self) -> str:
        return f"<PriceImportBatch id={self.id} file={self.source_file!r} status={self.status!r}>"


# ---------------------------------------------------------------------------
# Casos de presupuesto (histórico)
# ---------------------------------------------------------------------------

class QuoteCase(Base):
    __tablename__ = "quote_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    client_name: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    client_location: Mapped[Optional[str]] = mapped_column(String(200))
    quote_type: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False, index=True)

    # JSON almacenado como texto
    input_original: Mapped[Optional[str]] = mapped_column(Text)
    extracted_data_json: Mapped[Optional[str]] = mapped_column(Text)
    pending_data_json: Mapped[Optional[str]] = mapped_column(Text)
    warnings_json: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relaciones
    line_items: Mapped[list["QuoteLineItem"]] = relationship("QuoteLineItem", back_populates="quote_case", cascade="all, delete-orphan")
    totals: Mapped[Optional["QuoteTotalRecord"]] = relationship("QuoteTotalRecord", back_populates="quote_case", uselist=False, cascade="all, delete-orphan")
    corrections: Mapped[list["QuoteCorrection"]] = relationship("QuoteCorrection", back_populates="quote_case", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<QuoteCase id={self.id} ref={self.reference!r} client={self.client_name!r}>"


# ---------------------------------------------------------------------------
# Partidas de presupuesto
# ---------------------------------------------------------------------------

class QuoteLineItem(Base):
    __tablename__ = "quote_line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quote_case_id: Mapped[int] = mapped_column(ForeignKey("quote_cases.id"), nullable=False, index=True)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"))
    supplier_price_id: Mapped[Optional[int]] = mapped_column(ForeignKey("supplier_prices.id"))

    category: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(50))

    internal_unit_cost: Mapped[Optional[float]] = mapped_column(Float)
    client_unit_price: Mapped[Optional[float]] = mapped_column(Float)
    internal_total_cost: Mapped[Optional[float]] = mapped_column(Float)
    client_total_price: Mapped[Optional[float]] = mapped_column(Float)

    confidence: Mapped[Optional[str]] = mapped_column(String(20))
    source_reason: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    quote_case: Mapped["QuoteCase"] = relationship("QuoteCase", back_populates="line_items")

    def __repr__(self) -> str:
        return f"<QuoteLineItem id={self.id} desc={self.description[:30]!r}>"


# ---------------------------------------------------------------------------
# Totales de presupuesto
# ---------------------------------------------------------------------------

class QuoteTotalRecord(Base):
    __tablename__ = "quote_totals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quote_case_id: Mapped[int] = mapped_column(ForeignKey("quote_cases.id"), nullable=False, unique=True, index=True)

    internal_total_cost: Mapped[Optional[float]] = mapped_column(Float)
    client_total_without_igic: Mapped[Optional[float]] = mapped_column(Float)
    igic_rate: Mapped[Optional[float]] = mapped_column(Float)
    igic_amount: Mapped[Optional[float]] = mapped_column(Float)
    client_total_with_igic: Mapped[Optional[float]] = mapped_column(Float)
    benefit: Mapped[Optional[float]] = mapped_column(Float)
    margin_percent: Mapped[Optional[float]] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    quote_case: Mapped["QuoteCase"] = relationship("QuoteCase", back_populates="totals")

    def __repr__(self) -> str:
        return f"<QuoteTotalRecord id={self.id} total={self.client_total_with_igic}>"


# ---------------------------------------------------------------------------
# Correcciones
# ---------------------------------------------------------------------------

class QuoteCorrection(Base):
    __tablename__ = "quote_corrections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quote_case_id: Mapped[int] = mapped_column(ForeignKey("quote_cases.id"), nullable=False, index=True)
    field_path: Mapped[str] = mapped_column(String(300), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    correction_reason: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relaciones
    quote_case: Mapped["QuoteCase"] = relationship("QuoteCase", back_populates="corrections")

    def __repr__(self) -> str:
        return f"<QuoteCorrection id={self.id} field={self.field_path!r}>"


# ---------------------------------------------------------------------------
# Aprendizajes
# ---------------------------------------------------------------------------

class LearningItem(Base):
    __tablename__ = "learning_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_quote_case_id: Mapped[Optional[int]] = mapped_column(ForeignKey("quote_cases.id"))
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # pricing_rule, exclusion_rule, transport_rule, labor_rule, material_rule,
    # supplier_preference, template_text, error_pattern, client_exception
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    proposed_rule: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    # pending / approved / rejected
    approved_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<LearningItem id={self.id} type={self.type!r} status={self.status!r}>"


# ---------------------------------------------------------------------------
# Casos de error
# ---------------------------------------------------------------------------

class ErrorCase(Base):
    __tablename__ = "error_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    cause: Mapped[Optional[str]] = mapped_column(Text)
    solution: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False, index=True)
    related_quote_case_id: Mapped[Optional[int]] = mapped_column(ForeignKey("quote_cases.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<ErrorCase id={self.id} title={self.title[:40]!r} status={self.status!r}>"
