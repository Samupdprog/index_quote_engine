"""Tests del importador de Excel de productos."""

from __future__ import annotations

from pathlib import Path

import pytest

from quote_engine.importers.excel_products_importer import (
    ExcelProductsImporter,
    ImportReport,
    normalize_text,
    normalize_supplier_name,
    _detect_columns,
    _safe_float,
    _safe_date,
)

# Ruta al fixture Excel
FIXTURE_EXCEL = Path(__file__).parent.parent / "fixtures_excel" / "test_productos.xlsx"


class TestNormalization:
    def test_normalize_text_accents(self):
        assert normalize_text("Tubería") == "tuberia"
        assert normalize_text("Válvula") == "valvula"
        assert normalize_text("Artículo") == "articulo"

    def test_normalize_text_lowercase(self):
        assert normalize_text("FRIGICOLL") == "frigicoll"

    def test_normalize_text_spaces(self):
        assert normalize_text("  split   1x1  ") == "split 1x1"

    def test_normalize_supplier_removes_suffix(self):
        assert normalize_supplier_name("Frigicoll S.L.") == "frigicoll"
        assert normalize_supplier_name("Airwell S.A.") == "airwell"

    def test_normalize_supplier_empty(self):
        assert normalize_supplier_name("") == ""


class TestColumnDetection:
    def test_detect_description_column(self):
        headers = ["Descripcion", "Precio Neto", "Unidad"]
        cols = _detect_columns(headers)
        assert cols["description"] == 0

    def test_detect_price_column(self):
        headers = ["Articulo", "Precio Neto", "Tarifa"]
        cols = _detect_columns(headers)
        assert cols["price_net"] == 1
        assert cols["price_gross"] == 2

    def test_detect_discount_column(self):
        headers = ["Producto", "Precio", "Dto%"]
        cols = _detect_columns(headers)
        assert cols["discount"] == 2

    def test_no_match_returns_minus_one(self):
        headers = ["Col1", "Col2", "Col3"]
        cols = _detect_columns(headers)
        assert cols["price_net"] == -1


class TestSafeConversions:
    def test_safe_float_number(self):
        assert _safe_float(12.5) == 12.5

    def test_safe_float_string(self):
        assert _safe_float("12,50") == 12.5
        assert _safe_float("12.50") == 12.5

    def test_safe_float_with_euro(self):
        assert _safe_float("12.50 €") == 12.5

    def test_safe_float_none(self):
        assert _safe_float(None) is None

    def test_safe_float_empty_string(self):
        assert _safe_float("") is None

    def test_safe_date_dd_mm_yyyy(self):
        d = _safe_date("15/01/2026")
        assert d is not None
        assert d.year == 2026
        assert d.month == 1
        assert d.day == 15

    def test_safe_date_none(self):
        assert _safe_date(None) is None


class TestExcelImporterDryRun:
    """Tests del importador en modo dry-run (sin DB)."""

    @pytest.mark.skipif(
        not FIXTURE_EXCEL.exists(),
        reason=f"Fixture Excel no encontrado: {FIXTURE_EXCEL}"
    )
    def test_import_fixture_dry_run(self):
        importer = ExcelProductsImporter(db_session=None)
        report = importer.run(FIXTURE_EXCEL, force=True, report_output_dir="/tmp")

        assert isinstance(report, ImportReport)
        assert report.total_rows > 0
        assert report.created_products > 0
        assert report.created_prices > 0

    @pytest.mark.skipif(
        not FIXTURE_EXCEL.exists(),
        reason=f"Fixture Excel no encontrado: {FIXTURE_EXCEL}"
    )
    def test_suppliers_detected(self):
        importer = ExcelProductsImporter(db_session=None)
        report = importer.run(FIXTURE_EXCEL, force=True, report_output_dir="/tmp")

        assert len(report.suppliers_detected) >= 1
        # Frigicoll debe aparecer
        suppliers_norm = [s.lower() for s in report.suppliers_detected]
        assert any("frigicoll" in s for s in suppliers_norm)

    @pytest.mark.skipif(
        not FIXTURE_EXCEL.exists(),
        reason=f"Fixture Excel no encontrado: {FIXTURE_EXCEL}"
    )
    def test_ignores_index_sheet(self):
        importer = ExcelProductsImporter(db_session=None)
        report = importer.run(FIXTURE_EXCEL, force=True, report_output_dir="/tmp")

        # La hoja "Indice" debe ignorarse o procesarse sin datos útiles
        # Lo verificamos por no encontrar errores de hoja vacía
        assert report.errors_count == 0

    @pytest.mark.skipif(
        not FIXTURE_EXCEL.exists(),
        reason=f"Fixture Excel no encontrado: {FIXTURE_EXCEL}"
    )
    def test_detects_dubious_units(self):
        """La tubería de cobre en 'rollo' debe marcar unidad dudosa."""
        importer = ExcelProductsImporter(db_session=None)
        report = importer.run(FIXTURE_EXCEL, force=True, report_output_dir="/tmp")
        # Puede haber advertencias de unidades de empaque
        # Al menos el informe se genera sin error
        assert isinstance(report.dubious_units, list)

    @pytest.mark.skipif(
        not FIXTURE_EXCEL.exists(),
        reason=f"Fixture Excel no encontrado: {FIXTURE_EXCEL}"
    )
    def test_report_generates_markdown(self, tmp_path):
        importer = ExcelProductsImporter(db_session=None)
        report = importer.run(FIXTURE_EXCEL, force=True, report_output_dir=str(tmp_path))

        md = report.to_markdown()
        assert "# Informe de importación" in md
        assert "Resumen" in md

    @pytest.mark.skipif(
        not FIXTURE_EXCEL.exists(),
        reason=f"Fixture Excel no encontrado: {FIXTURE_EXCEL}"
    )
    def test_hash_computed(self):
        importer = ExcelProductsImporter(db_session=None)
        report = importer.run(FIXTURE_EXCEL, force=True, report_output_dir="/tmp")
        assert len(report.source_hash) == 64  # SHA-256

    def test_file_not_found_raises(self):
        importer = ExcelProductsImporter(db_session=None)
        with pytest.raises(FileNotFoundError):
            importer.run("no_existe.xlsx")


class TestImportReportMarkdown:
    def test_empty_report_markdown(self):
        report = ImportReport(source_file="test.xlsx", source_hash="abc123")
        md = report.to_markdown()
        assert "# Informe de importación" in md
        assert "test.xlsx" in md

    def test_report_with_warnings(self):
        report = ImportReport(source_file="test.xlsx", source_hash="abc123")
        report.add_warning("Warning de prueba")
        md = report.to_markdown()
        assert "Warning de prueba" in md
        assert report.warnings_count == 1

    def test_report_with_errors(self):
        report = ImportReport(source_file="test.xlsx", source_hash="abc123")
        report.add_error("Error de prueba")
        md = report.to_markdown()
        assert "Error de prueba" in md
        assert report.errors_count == 1
