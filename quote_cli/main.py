"""CLI del motor de presupuestos Index Clima."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from quote_engine import storage as _storage
from quote_engine.calculator import calculate_quote
from quote_engine.exporters.holded import export_holded_payload
from quote_engine.exporters.internal_report import (
    build_internal_report,
    build_internal_report_html,
    save_internal_report_html,
)
from quote_engine.models import QuoteSnapshot


def _load_snapshot_from_file(path: Path) -> QuoteSnapshot:
    """Carga QuoteSnapshot desde un archivo JSON.

    Acepta tanto el formato completo {metadata, snapshot} como un snapshot puro.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    if "snapshot" in raw and isinstance(raw["snapshot"], dict):
        return QuoteSnapshot.model_validate(raw["snapshot"])
    return QuoteSnapshot.model_validate(raw)


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def cmd_list(args: argparse.Namespace) -> int:
    quotes = _storage.list_quotes(
        status=args.status,
        client_name=args.client,
        project_type=args.project_type,
        tag=args.tag,
        limit=args.limit,
    )
    if not quotes:
        print("No hay presupuestos guardados.")
        return 0

    for q in quotes:
        qid = q["quote_id"] or "?"
        status = q["status"] or "?"
        client = q["client_name"] or "(sin cliente)"
        updated = q["updated_at"] or "?"

        total_str = ""
        try:
            doc = _storage.load_quote(qid)
            snap = QuoteSnapshot.model_validate(doc["snapshot"])
            calc = calculate_quote(snap)
            total_str = f" | {calc.totals.final_total:.2f} €"
        except Exception:
            pass

        print(f"{qid} | {status} | {client}{total_str} | updated: {updated}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    try:
        doc = _storage.load_quote(args.quote_id)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.output_json:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0

    meta = doc.get("metadata", {})
    snap_data = doc.get("snapshot", {})
    header = snap_data.get("header", {})
    lines = snap_data.get("lines", [])

    print(f"ID:            {meta.get('id', '?')}")
    print(f"Cliente:       {header.get('client_name') or '(sin cliente)'}")
    print(f"Estado:        {meta.get('status', '?')}")
    print(f"Creado:        {meta.get('created_at', '?')}")
    print(f"Actualizado:   {meta.get('updated_at', '?')}")
    print(f"Tipo proyecto: {meta.get('project_type') or '(sin tipo)'}")
    tags = meta.get("tags", [])
    print(f"Tags:          {', '.join(tags) if tags else '(sin tags)'}")
    print(f"Líneas:        {len(lines)}")

    try:
        snap = QuoteSnapshot.model_validate(snap_data)
        calc = calculate_quote(snap)
        print(f"Total cliente: {calc.totals.final_total:.2f} €")
        pct = calc.totals.gross_profit_percent
        pct_str = f"{pct:.1f}%" if pct is not None else "N/A"
        print(f"Beneficio:     {calc.totals.gross_profit:.2f} € ({pct_str})")
    except Exception:
        pass

    return 0


def cmd_calculate(args: argparse.Namespace) -> int:
    try:
        doc = _storage.load_quote(args.quote_id)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        snap = QuoteSnapshot.model_validate(doc["snapshot"])
        calc = calculate_quote(snap)
    except Exception as exc:
        print(f"Error al calcular: {exc}", file=sys.stderr)
        return 1

    if args.output_json:
        print(json.dumps(calc.model_dump(), ensure_ascii=False, indent=2))
        return 0

    meta = doc.get("metadata", {})
    header = doc.get("snapshot", {}).get("header", {})
    t = calc.totals
    pct = t.gross_profit_percent
    pct_str = f"{pct:.1f}%" if pct is not None else "N/A"

    print(f"Presupuesto:    {meta.get('id', args.quote_id)}")
    print(f"Cliente:        {header.get('client_name') or '(sin cliente)'}")
    print(f"Coste total:    {t.cost_subtotal:.2f} €")
    print(f"Venta sin IGIC: {t.sale_subtotal:.2f} €")
    print(f"IGIC:           {t.tax_amount:.2f} €")
    print(f"Total cliente:  {t.final_total:.2f} €")
    print(f"Beneficio:      {t.gross_profit:.2f} €")
    print(f"Beneficio %:    {pct_str}")
    print(f"Líneas:         {len(calc.lines)}")
    if calc.warnings:
        print(f"Warnings:       {len(calc.warnings)}")
        for w in calc.warnings:
            print(f"  - {w}")
    else:
        print("Warnings:       0")
    return 0


def cmd_save(args: argparse.Namespace) -> int:
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: archivo no encontrado: {file_path}", file=sys.stderr)
        return 1

    try:
        snap = _load_snapshot_from_file(file_path)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Error al leer JSON: {exc}", file=sys.stderr)
        return 1

    try:
        quote_id = _storage.save_quote(
            snap,
            quote_id=args.id,
            created_by=args.created_by,
            source=args.source,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    updates: dict[str, Any] = {}
    if args.project_type:
        updates["project_type"] = args.project_type
    if args.tag:
        updates["tags"] = args.tag
    if args.status:
        updates["status"] = args.status
    if updates:
        _storage.update_quote_metadata(quote_id, updates)

    print(f"Guardado: {quote_id}")
    return 0


def cmd_duplicate(args: argparse.Namespace) -> int:
    try:
        new_id = _storage.duplicate_quote(args.quote_id, new_quote_id=args.new_id)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Duplicado {args.quote_id} -> {new_id}")
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    try:
        _storage.archive_quote(args.quote_id)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Archivado {args.quote_id}")
    return 0


def cmd_export_holded(args: argparse.Namespace) -> int:
    try:
        doc = _storage.load_quote(args.quote_id)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        snap = QuoteSnapshot.model_validate(doc["snapshot"])
        calc = calculate_quote(snap)
        payload = export_holded_payload(snap, calc)
    except Exception as exc:
        print(f"Error al exportar: {exc}", file=sys.stderr)
        return 1

    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload_json, encoding="utf-8")
        print(f"Exportado a: {args.output}")
        return 0

    if args.output_json:
        print(payload_json)
        return 0

    t = payload.get("totals", {})
    print(f"Cliente:     {payload.get('contactName') or '(sin cliente)'}")
    print(f"Presupuesto: {payload.get('quoteNumber') or '?'}")
    print(f"Líneas:      {len(payload.get('items', []))}")
    print(f"Subtotal:    {t.get('subtotal', 0):.2f} €")
    print(f"IGIC:        {t.get('tax', 0):.2f} €")
    print(f"Total:       {t.get('total', 0):.2f} €")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    try:
        doc = _storage.load_quote(args.quote_id)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    snap = QuoteSnapshot.model_validate(doc["snapshot"])
    meta = doc.get("metadata", {})

    if args.output:
        try:
            path = save_internal_report_html(snap, args.output, metadata=meta)
        except Exception as exc:
            print(f"Error al guardar informe: {exc}", file=sys.stderr)
            return 1
        print(f"Informe interno generado: {path}")
        if args.open:
            import webbrowser
            webbrowser.open(Path(path).resolve().as_uri())
        return 0

    # Sin --output: resumen en texto
    report = build_internal_report(snap, metadata=meta)
    t = report["totals"]
    pct = t["gross_profit_percent"]
    pct_str = f"{pct:.1f}%" if pct is not None else "N/A"

    print(f"Presupuesto:    {meta.get('id', args.quote_id)}")
    print(f"Cliente:        {report['header'].get('client_name') or '(sin cliente)'}")
    print(f"Estado:         {meta.get('status', '?')}")
    print(f"Coste total:    {t['cost_subtotal']:.2f} €")
    print(f"Venta sin IGIC: {t['sale_subtotal']:.2f} €")
    print(f"Total cliente:  {t['final_total']:.2f} €")
    print(f"Beneficio:      {t['gross_profit']:.2f} € ({pct_str})")
    print(f"Proveedores:    {len(report['supplier_summary'])}")
    print(f"Líneas:         {len(report['lines'])}")
    if report["problems"]:
        print(f"Problemas:      {len(report['problems'])}")
        for p in report["problems"]:
            print(f"  ⚠ {p['line']} — {p['issue']}")
    print("(Usa --output <archivo.html> para generar el informe HTML completo)")
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="index-quote",
        description="Motor de presupuestos Index Clima — CLI",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMANDO")
    sub.required = True

    # list
    p_list = sub.add_parser("list", help="Listar presupuestos guardados")
    p_list.add_argument("--status", help="Filtrar por estado")
    p_list.add_argument("--client", help="Filtrar por nombre de cliente (parcial)")
    p_list.add_argument("--project-type", dest="project_type", help="Filtrar por tipo de proyecto")
    p_list.add_argument("--tag", help="Filtrar por tag")
    p_list.add_argument("--limit", type=int, help="Limitar número de resultados")
    p_list.set_defaults(func=cmd_list)

    # show
    p_show = sub.add_parser("show", help="Mostrar detalle de un presupuesto")
    p_show.add_argument("quote_id", help="ID del presupuesto (ej. PRE-2026-0001)")
    p_show.add_argument("--json", dest="output_json", action="store_true", help="Salida JSON completa")
    p_show.set_defaults(func=cmd_show)

    # calculate
    p_calc = sub.add_parser("calculate", help="Calcular totales de un presupuesto")
    p_calc.add_argument("quote_id", help="ID del presupuesto")
    p_calc.add_argument("--json", dest="output_json", action="store_true", help="Salida JSON completa")
    p_calc.set_defaults(func=cmd_calculate)

    # save
    p_save = sub.add_parser("save", help="Guardar presupuesto desde archivo JSON")
    p_save.add_argument("file", help="Ruta al archivo JSON del presupuesto")
    p_save.add_argument("--id", help="ID explícito (opcional)")
    p_save.add_argument("--created-by", dest="created_by", help="Autor del presupuesto")
    p_save.add_argument("--source", default="cli", help="Fuente (default: cli)")
    p_save.add_argument("--status", default=None, help="Estado inicial")
    p_save.add_argument("--project-type", dest="project_type", help="Tipo de proyecto")
    p_save.add_argument("--tag", action="append", dest="tag", help="Tag (puede repetirse)")
    p_save.set_defaults(func=cmd_save)

    # duplicate
    p_dup = sub.add_parser("duplicate", help="Duplicar un presupuesto")
    p_dup.add_argument("quote_id", help="ID del presupuesto a duplicar")
    p_dup.add_argument("--new-id", dest="new_id", help="ID para el duplicado (opcional)")
    p_dup.set_defaults(func=cmd_duplicate)

    # archive
    p_arch = sub.add_parser("archive", help="Archivar un presupuesto")
    p_arch.add_argument("quote_id", help="ID del presupuesto a archivar")
    p_arch.set_defaults(func=cmd_archive)

    # export-holded
    p_exp = sub.add_parser("export-holded", help="Exportar payload Holded (sin enviar)")
    p_exp.add_argument("quote_id", help="ID del presupuesto")
    p_exp.add_argument("--output", help="Ruta del archivo de salida (opcional)")
    p_exp.add_argument("--json", dest="output_json", action="store_true", help="Salida JSON en pantalla")
    p_exp.set_defaults(func=cmd_export_holded)

    # report
    p_rep = sub.add_parser("report", help="Generar informe interno HTML")
    p_rep.add_argument("quote_id", help="ID del presupuesto")
    p_rep.add_argument("--output", help="Ruta del archivo HTML de salida")
    p_rep.add_argument("--open", dest="open", action="store_true", help="Abrir en navegador tras generar")
    p_rep.set_defaults(func=cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
