#!/usr/bin/env python3
"""Crea un presupuesto de validacion en PostgreSQL usando el motor real.

Uso:
    cd C:\\Users\\Samuel\\index_quote_engine
    python scripts/create_validation_quote.py

Requiere DATABASE_URL en el entorno (o en .env).
No toca Holded. No toca facturas. No borra datos.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from typing import Optional

# Asegurar que el raiz del proyecto estÃ¡ en sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Cargar .env si existe
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://eon:eon_dev_password@localhost:5435/eon_index_clima",
)

REFERENCE   = "PRE-EON-VALIDACION-001"
CLIENT_NAME = "PRUEBA EON VALIDACION"
QUOTE_TYPE  = "instalacion_split"
GLOBAL_MARGIN = 35.0   # %
TAX_RATE      = 7.0    # IGIC Canarias

# Partidas que queremos presupuestar (query, cantidad, unidad, tipo)
MATERIAL_ITEMS: list[tuple[str, float, str]] = [
    ("tuberÃ­a cobre",           20.0, "ml"),
    ("canaleta",                10.0, "ml"),
    ("cable",                   15.0, "ml"),
    ("split",                    1.0, "ud"),
]

# Mano de obra fija (sin catÃ¡logo â€” precio acordado)
LABOR_ITEMS: list[tuple[str, float, str, float]] = [
    # descripcion, cantidad, unidad, coste_unitario
    ("InstalaciÃ³n y puesta en marcha",  8.0, "h",   20.0),
    ("Desplazamiento",                  1.0, "ud",  25.0),
]


# ============================================================
# HELPERS
# ============================================================

def sep(char="â”€", n=70):
    print(char * n)

def section(title: str):
    print()
    sep("â•")
    print(f"  {title}")
    sep("â•")

def ok(msg):  print(f"  âœ“  {msg}")
def warn(msg):print(f"  âš   {msg}")
def err(msg): print(f"  âœ—  {msg}", file=sys.stderr)


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    section("Presupuesto de validaciÃ³n â€” Index Quote Engine")
    print(f"  Reference : {REFERENCE}")
    print(f"  Cliente   : {CLIENT_NAME}")
    print(f"  Tipo      : {QUOTE_TYPE}")
    print(f"  Margen    : {GLOBAL_MARGIN}%  |  IGIC: {TAX_RATE}%")

    # ----------------------------------------------------------
    # 1. ConexiÃ³n DB
    # ----------------------------------------------------------
    section("1. ConexiÃ³n a base de datos")
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        # version() en PostgreSQL, sqlite_version() en SQLite
        if "sqlite" in DATABASE_URL:
            ver = session.execute(text("SELECT sqlite_version()")).scalar()
            ok(f"Conectado (SQLite {ver})")
        else:
            ver = session.execute(text("SELECT version()")).scalar()
            ok(f"Conectado: {ver[:55]}")
    except Exception as exc:
        err(f"No se pudo conectar: {exc}")
        return 1

    # Conteos antes
    section("2. Conteos DB antes")
    from quote_engine.db.models import QuoteCase, QuoteLineItem, QuoteTotalRecord
    n_cases_before  = session.query(QuoteCase).count()
    n_lines_before  = session.query(QuoteLineItem).count()
    n_totals_before = session.query(QuoteTotalRecord).count()
    print(f"  quote_cases       : {n_cases_before}")
    print(f"  quote_line_items  : {n_lines_before}")
    print(f"  quote_totals      : {n_totals_before}")

    # ----------------------------------------------------------
    # 3. CatÃ¡logo + PriceSelector
    # ----------------------------------------------------------
    section("3. BÃºsqueda en catÃ¡logo")
    from quote_engine.catalog.service import CatalogService
    from quote_engine.pricing.selector import PriceSelector
    from quote_engine.models import QuoteHeader, QuoteLine, QuoteSnapshot

    catalog = CatalogService(db_session=session)
    selector = PriceSelector()

    snapshot_lines: list[QuoteLine] = []
    line_summaries: list[dict] = []  # para el informe final

    for query, qty, unit in MATERIAL_ITEMS:
        print()
        print(f"  Buscando: {query!r}  qty={qty} {unit}")
        result = selector.select_from_catalog(query, catalog)

        if not result.selected:
            warn(f"Sin precio para {query!r}: {result.reason}")
            # AÃ±adir lÃ­nea sin precio (quedarÃ¡ a 0 con warning)
            line = QuoteLine(
                type="material",
                description=f"[SIN PRECIO] {query}",
                quantity=qty,
                unit=unit,
                sale_mode="margin",
                notes=f"No encontrado en catÃ¡logo: {result.reason}",
            )
            snapshot_lines.append(line)
            line_summaries.append({
                "description": f"[SIN PRECIO] {query}",
                "qty": qty, "unit": unit,
                "supplier": None, "price": None,
                "confidence": None, "reason": result.reason,
                "warnings": result.warnings,
                "source": {},
            })
            continue

        ok(f"  {result.supplier[:30]:30} | {result.price:>8.2f} EUR/{unit} | {result.confidence} | {result.reason[:40]}")
        if result.warnings:
            for w in result.warnings:
                warn(f"    {w[:70]}")

        # Nombre de descripciÃ³n real del catÃ¡logo (de la fuente)
        search_resp = catalog.search_products(query, limit=1)
        desc = search_resp.results[0].description if search_resp.results else query

        line = QuoteLine(
            type="material",
            description=desc,
            quantity=qty,
            unit=unit,
            supplier=result.supplier,
            supplier_net_unit_cost=result.price,
            sale_mode="margin",
        )
        snapshot_lines.append(line)
        line_summaries.append({
            "description": desc,
            "qty": qty, "unit": unit,
            "supplier": result.supplier,
            "price": result.price,
            "confidence": result.confidence,
            "reason": result.reason,
            "warnings": result.warnings,
            "source": result.source,
        })

    # Mano de obra
    print()
    print("  AÃ±adiendo partidas de mano de obra...")
    for desc, qty, unit, cost in LABOR_ITEMS:
        line = QuoteLine(
            type="labor",
            description=desc,
            quantity=qty,
            unit=unit,
            supplier_net_unit_cost=cost,
            sale_mode="margin",
        )
        snapshot_lines.append(line)
        line_summaries.append({
            "description": desc,
            "qty": qty, "unit": unit,
            "supplier": "Mano de obra propia",
            "price": cost,
            "confidence": "alta",
            "reason": "precio fijo mano de obra",
            "warnings": [],
            "source": {},
        })
        ok(f"  {desc:40} | {cost:>8.2f} EUR/{unit} | alta (fijo)")

    # ----------------------------------------------------------
    # 4. Calcular presupuesto
    # ----------------------------------------------------------
    section("4. CÃ¡lculo con motor quote_engine")
    from quote_engine.calculator import calculate_quote

    header = QuoteHeader(
        quote_number=REFERENCE,
        client_name=CLIENT_NAME,
        date=str(date.today()),
        global_margin=GLOBAL_MARGIN,
        tax=TAX_RATE,
        include_tax=False,
        title="InstalaciÃ³n de sistema split â€” ValidaciÃ³n EON",
        validity="30 dÃ­as",
        payment="50% a la firma y 50% al finalizar",
    )
    snapshot = QuoteSnapshot(header=header, lines=snapshot_lines)
    calculated = calculate_quote(snapshot)

    print()
    print(f"  {'DescripciÃ³n':45} {'Qty':>5} {'U':4} {'Coste':>8} {'PVP':>9} {'Margen':>7}")
    sep()
    for cl in calculated.lines:
        margin_pct = f"{cl.gross_profit_percent:.1f}%" if cl.gross_profit_percent else "  n/a"
        print(f"  {cl.description[:45]:45} {cl.quantity:>5.1f} {cl.unit:4} "
              f"{cl.cost_unit:>8.2f} {cl.sale_unit_without_tax:>9.2f} {margin_pct:>7}")

    sep()
    t = calculated.totals
    print(f"  {'Subtotal coste':52} {t.cost_subtotal:>8.2f} EUR")
    print(f"  {'Subtotal venta (sin IGIC)':52} {t.sale_subtotal:>8.2f} EUR")
    print(f"  {'IGIC {:.0f}%'.format(TAX_RATE):52} {t.tax_amount:>8.2f} EUR")
    print(f"  {'TOTAL CLIENTE (con IGIC)':52} {t.final_total:>8.2f} EUR")
    print(f"  {'Beneficio bruto':52} {t.gross_profit:>8.2f} EUR  ({t.gross_profit_percent:.1f}%)")

    if calculated.warnings:
        print()
        for w in calculated.warnings:
            warn(w[:70])

    # ----------------------------------------------------------
    # 5. Serializar y guardar en PostgreSQL
    # ----------------------------------------------------------
    section("5. Guardar en PostgreSQL")
    from quote_engine.db.repositories.quotes import save_quote_case, get_quote_case

    snapshot_dict = snapshot.model_dump(mode="json")

    # calculated_dict con formato esperado por save_quote_case
    calculated_dict = {
        "lines": [
            {
                "description":          cl.description,
                "type":                 cl.type,
                "quantity":             cl.quantity,
                "unit":                 cl.unit,
                "cost_unit":            cl.cost_unit,
                "cost_total":           cl.cost_total,
                "sale_unit_without_tax": cl.sale_unit_without_tax,
                "sale_total_without_tax": cl.sale_total_without_tax,
                "sale_mode":            cl.sale_mode,
            }
            for cl in calculated.lines
        ],
        "totals": {
            "cost_subtotal":        t.cost_subtotal,
            "sale_subtotal":        t.sale_subtotal,
            "tax_amount":           t.tax_amount,
            "final_total":          t.final_total,
            "gross_profit":         t.gross_profit,
            "gross_profit_percent": t.gross_profit_percent,
        },
    }

    # Warnings globales (catÃ¡logo + calculadora)
    all_warnings = calculated.warnings[:]
    for ls in line_summaries:
        all_warnings.extend(ls.get("warnings", []))

    case_id = save_quote_case(
        db_session=session,
        reference=REFERENCE,
        snapshot_dict=snapshot_dict,
        calculated_dict=calculated_dict,
        client_name=CLIENT_NAME,
        quote_type=QUOTE_TYPE,
        status="draft",
        warnings=all_warnings,
    )

    if case_id is None:
        err("save_quote_case devolviÃ³ None â€” revisar logs")
        session.close()
        return 1

    ok(f"Guardado â€” case_id={case_id}, reference={REFERENCE}")

    # ----------------------------------------------------------
    # 6. Conteos despuÃ©s y verificaciÃ³n
    # ----------------------------------------------------------
    section("6. Conteos DB despuÃ©s")
    n_cases_after  = session.query(QuoteCase).count()
    n_lines_after  = session.query(QuoteLineItem).count()
    n_totals_after = session.query(QuoteTotalRecord).count()

    def delta(before, after):
        d = after - before
        return f"{after}  (+{d})" if d else str(after)

    print(f"  quote_cases       : {delta(n_cases_before,  n_cases_after)}")
    print(f"  quote_line_items  : {delta(n_lines_before,  n_lines_after)}")
    print(f"  quote_totals      : {delta(n_totals_before, n_totals_after)}")

    ok_count = 0
    if n_cases_after  >= 1: ok_count += 1
    else: err("quote_cases < 1 tras guardar")
    if n_lines_after  >= 1: ok_count += 1
    else: err("quote_line_items < 1 tras guardar")
    if n_totals_after >= 1: ok_count += 1
    else: err("quote_totals < 1 tras guardar")

    # ----------------------------------------------------------
    # 7. Recuperar y mostrar presupuesto completo
    # ----------------------------------------------------------
    section("7. RecuperaciÃ³n y verificaciÃ³n del presupuesto")
    saved = get_quote_case(session, REFERENCE)
    if saved is None:
        err(f"No se pudo recuperar {REFERENCE} de la DB")
        session.close()
        return 1

    print(f"  Reference    : {saved['reference']}")
    print(f"  Cliente      : {saved['client_name']}")
    print(f"  Estado       : {saved['status']}")
    print(f"  Creado       : {saved['created_at']}")
    print(f"  LÃ­neas en DB : {saved['line_count']}")

    if saved["totals"]:
        tot = saved["totals"]
        print(f"  Total cliente: {tot['client_total_with_igic']:.2f} EUR (con IGIC)")
        print(f"  Beneficio    : {tot['benefit']:.2f} EUR  ({tot['margin_percent']:.1f}%)" if tot.get('benefit') else "")
    print()

    print(f"  {'#':>2}  {'DescripciÃ³n':45} {'Coste':>8}  {'PVP':>9}")
    sep()
    for i, li in enumerate(saved["lines"], 1):
        print(f"  {i:>2}  {li['description'][:45]:45} {li['internal_unit_cost'] or 0:>8.2f}  {li['client_unit_price'] or 0:>9.2f}")
    sep()

    # Fuentes por partida
    print()
    print("  Detalle por partida (catÃ¡logo):")
    sep("â”€", 70)
    for ls in line_summaries:
        confidence = ls.get("confidence") or "n/a"
        supplier   = ls.get("supplier")   or "â€”"
        price      = ls.get("price")
        price_str  = f"{price:.2f} EUR" if price is not None else "sin precio"
        print(f"  Â· {ls['description'][:43]}")
        print(f"    Proveedor : {supplier}")
        print(f"    Precio    : {price_str}  |  Confianza: {confidence}")
        print(f"    Fuente    : {ls['reason']}")
        if ls.get("source", {}).get("source_file"):
            s = ls["source"]
            print(f"    Archivo   : {s.get('source_file','?')} / hoja: {s.get('source_sheet','?')} / fila: {s.get('source_row','?')}")
        if ls.get("warnings"):
            for w in ls["warnings"]:
                warn(f"  {w[:65]}")
        sep("Â·", 70)

    # ----------------------------------------------------------
    # Resumen final
    # ----------------------------------------------------------
    section("RESULTADO FINAL")
    if ok_count == 3 and case_id:
        print(f"  âœ“  Presupuesto PRE-EON-VALIDACION-001 creado y verificado en PostgreSQL")
        print(f"  âœ“  quote_cases={n_cases_after}  quote_line_items={n_lines_after}  quote_totals={n_totals_after}")
        print(f"  âœ“  Total cliente: {t.final_total:.2f} EUR (sin IGIC: {t.sale_subtotal:.2f} EUR)")
        print(f"  âœ“  Beneficio: {t.gross_profit:.2f} EUR ({t.gross_profit_percent:.1f}%)")
    else:
        err("VerificaciÃ³n incompleta â€” revisar conteos DB")

    session.close()
    return 0 if ok_count == 3 else 1


if __name__ == "__main__":
    sys.exit(main())

