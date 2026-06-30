"""Initial schema — todas las tablas EON

Revision ID: 0001
Revises:
Create Date: 2026-06-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── suppliers ────────────────────────────────────────────────────────────
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("normalized_name", sa.String(200), nullable=False),
        sa.Column("contact_name", sa.String(200), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_suppliers_normalized_name", "suppliers", ["normalized_name"])

    # ── products ─────────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("internal_code", sa.String(100), nullable=True),
        sa.Column("supplier_reference", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("normalized_description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("subcategory", sa.String(100), nullable=True),
        sa.Column("unit_purchase", sa.String(50), nullable=True),
        sa.Column("unit_calc", sa.String(50), nullable=True),
        sa.Column("conversion_factor", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_internal_code", "products", ["internal_code"])
    op.create_index("ix_products_supplier_reference", "products", ["supplier_reference"])
    op.create_index("ix_products_normalized_description", "products", ["normalized_description"])
    op.create_index("ix_products_category", "products", ["category"])

    # ── supplier_prices ───────────────────────────────────────────────────────
    op.create_table(
        "supplier_prices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=True),
        sa.Column("source_file", sa.String(500), nullable=True),
        sa.Column("source_sheet", sa.String(200), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("document_number", sa.String(100), nullable=True),
        sa.Column("document_date", sa.DateTime(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("gross_unit_price", sa.Float(), nullable=True),
        sa.Column("discount_percent", sa.Float(), nullable=True),
        sa.Column("net_unit_price", sa.Float(), nullable=False),
        sa.Column("line_total", sa.Float(), nullable=True),
        sa.Column("igic_rate", sa.Float(), nullable=True),
        sa.Column("igic_included", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="EUR"),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="media"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supplier_prices_product_id", "supplier_prices", ["product_id"])
    op.create_index("ix_supplier_prices_supplier_id", "supplier_prices", ["supplier_id"])
    op.create_index("ix_supplier_prices_is_current", "supplier_prices", ["is_current"])

    # ── price_import_batches ──────────────────────────────────────────────────
    op.create_table(
        "price_import_batches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_file", sa.String(500), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("status", sa.String(50), nullable=False, server_default="completed"),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_products", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_products", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_prices", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warnings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("report_path", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_price_import_batches_source_hash", "price_import_batches", ["source_hash"])

    # ── quote_cases ───────────────────────────────────────────────────────────
    op.create_table(
        "quote_cases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reference", sa.String(50), nullable=False),
        sa.Column("client_name", sa.String(200), nullable=True),
        sa.Column("client_location", sa.String(200), nullable=True),
        sa.Column("quote_type", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("input_original", sa.Text(), nullable=True),
        sa.Column("extracted_data_json", sa.Text(), nullable=True),
        sa.Column("pending_data_json", sa.Text(), nullable=True),
        sa.Column("warnings_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index("ix_quote_cases_reference", "quote_cases", ["reference"])
    op.create_index("ix_quote_cases_client_name", "quote_cases", ["client_name"])
    op.create_index("ix_quote_cases_status", "quote_cases", ["status"])

    # ── quote_line_items ──────────────────────────────────────────────────────
    op.create_table(
        "quote_line_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("quote_case_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("supplier_price_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("internal_unit_cost", sa.Float(), nullable=True),
        sa.Column("client_unit_price", sa.Float(), nullable=True),
        sa.Column("internal_total_cost", sa.Float(), nullable=True),
        sa.Column("client_total_price", sa.Float(), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=True),
        sa.Column("source_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["quote_case_id"], ["quote_cases.id"]),
        sa.ForeignKeyConstraint(["supplier_price_id"], ["supplier_prices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quote_line_items_quote_case_id", "quote_line_items", ["quote_case_id"])

    # ── quote_totals ──────────────────────────────────────────────────────────
    op.create_table(
        "quote_totals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("quote_case_id", sa.Integer(), nullable=False),
        sa.Column("internal_total_cost", sa.Float(), nullable=True),
        sa.Column("client_total_without_igic", sa.Float(), nullable=True),
        sa.Column("igic_rate", sa.Float(), nullable=True),
        sa.Column("igic_amount", sa.Float(), nullable=True),
        sa.Column("client_total_with_igic", sa.Float(), nullable=True),
        sa.Column("benefit", sa.Float(), nullable=True),
        sa.Column("margin_percent", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["quote_case_id"], ["quote_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quote_case_id"),
    )
    op.create_index("ix_quote_totals_quote_case_id", "quote_totals", ["quote_case_id"])

    # ── quote_corrections ─────────────────────────────────────────────────────
    op.create_table(
        "quote_corrections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("quote_case_id", sa.Integer(), nullable=False),
        sa.Column("field_path", sa.String(300), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("correction_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["quote_case_id"], ["quote_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quote_corrections_quote_case_id", "quote_corrections", ["quote_case_id"])

    # ── learning_items ────────────────────────────────────────────────────────
    op.create_table(
        "learning_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_quote_case_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("proposed_rule", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("approved_by", sa.String(100), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["source_quote_case_id"], ["quote_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_items_type", "learning_items", ["type"])
    op.create_index("ix_learning_items_status", "learning_items", ["status"])

    # ── error_cases ───────────────────────────────────────────────────────────
    op.create_table(
        "error_cases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cause", sa.Text(), nullable=True),
        sa.Column("solution", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("related_quote_case_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["related_quote_case_id"], ["quote_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_error_cases_status", "error_cases", ["status"])


def downgrade() -> None:
    op.drop_table("error_cases")
    op.drop_table("learning_items")
    op.drop_table("quote_corrections")
    op.drop_table("quote_totals")
    op.drop_table("quote_line_items")
    op.drop_table("quote_cases")
    op.drop_table("price_import_batches")
    op.drop_table("supplier_prices")
    op.drop_table("products")
    op.drop_table("suppliers")
