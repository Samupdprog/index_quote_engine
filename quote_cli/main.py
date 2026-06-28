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
from quote_engine.eon_tools import eon_summarize_quote, list_eon_tools
from quote_engine.workflow import run_quote_workflow
from quote_engine.search import find_recent_quotes, search_quotes, summarize_search_results


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


def cmd_workflow(args: argparse.Namespace) -> int:
    result = run_quote_workflow(
        input_path=args.input_file,
        quote_id=args.id,
        created_by=args.created_by,
        source=args.source,
        status=args.status,
        project_type=args.project_type,
        tags=args.tag or [],
        generate_report=not args.no_report,
        export_holded=not args.no_holded,
        report_output_path=args.report_output,
        holded_output_path=args.holded_output,
    )

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1

    if not result["ok"]:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    qid = result["quote_id"]
    s = result["summary"]
    pct = s.get("gross_profit_percent")
    pct_str = f"{pct:.1f}%" if pct is not None else "N/A"

    print(f"Workflow completado: {qid}")
    print()
    print(f"Estado:         [{s.get('report_label', '?')}]")
    print(f"Cliente:        {s.get('client_name') or '(sin cliente)'}")
    print(f"Total cliente:  {s.get('final_total', 0):.2f} €")
    print(f"Beneficio:      {s.get('gross_profit', 0):.2f} € ({pct_str})")
    print(f"Problemas:      {s.get('problems_count', 0)}")
    print(f"Warnings:       {s.get('warnings_count', 0)}")

    if result.get("report_path"):
        print(f"\nInforme HTML:   {result['report_path']}")
    if result.get("holded_path"):
        print(f"Payload Holded: {result['holded_path']}")

    recs = result.get("review_recommendations", [])
    if recs:
        print("\nQué revisar:")
        for r in recs:
            print(f"  ! {r}")

    return 0


def cmd_eon_tools(args: argparse.Namespace) -> int:
    tools = list_eon_tools()
    print(f"Herramientas EON disponibles ({len(tools)}):\n")
    for t in tools:
        params = ", ".join(t["params"])
        print(f"  {t['name']}({params})")
        print(f"    {t['description']}")
        print()
    return 0


def cmd_eon_summary(args: argparse.Namespace) -> int:
    result = eon_summarize_quote(args.quote_id)
    if not result["ok"]:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    d = result["data"]
    print(f"ID:             {d.get('id', '?')}")
    print(f"Cliente:        {d.get('client_name') or '(sin cliente)'}")
    print(f"Estado:         {d.get('status', '?')}")
    print(f"Semáforo:       [{d.get('report_label', '?')}]")
    print(f"Total cliente:  {d.get('final_total', 0):.2f} €")
    pct = d.get("gross_profit_percent")
    pct_str = f"{pct:.1f}%" if pct is not None else "N/A"
    print(f"Beneficio:      {d.get('gross_profit', 0):.2f} € ({pct_str})")
    print(f"Proveedores:    {', '.join(d.get('suppliers', [])) or '(sin proveedor)'}")
    print(f"Líneas:         {d.get('line_count', 0)}")
    print(f"Problemas:      {d.get('problems_count', 0)}")
    print(f"Warnings:       {d.get('warnings_count', 0)}")
    if d.get("human_summary"):
        print()
        print("Resumen rápido:")
        for s in d["human_summary"]:
            print(f"  · {s}")
    if d.get("review_recommendations"):
        print()
        print("Qué revisar:")
        for r in d["review_recommendations"]:
            print(f"  ! {r}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    has_warnings: bool | None = None
    if args.has_warnings:
        has_warnings = True

    has_problems: bool | None = None
    if args.has_problems:
        has_problems = True

    descending = not args.asc

    results = search_quotes(
        query=args.query,
        client_name=args.client,
        supplier=args.supplier,
        status=args.status,
        project_type=args.project_type,
        tag=args.tag,
        min_profit=args.min_profit,
        max_profit=args.max_profit,
        min_total=args.min_total,
        max_total=args.max_total,
        has_warnings=has_warnings,
        has_problems=has_problems,
        sort_by=args.sort_by,
        descending=descending,
        limit=args.limit,
    )

    if args.output_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    print(summarize_search_results(results))
    if not results:
        return 0
    print()
    for r in results:
        qid = r["id"] or "?"
        status = r["status"] or "?"
        client = r["client_name"] or "(sin cliente)"
        total = r["final_total"]
        profit = r["gross_profit"]
        label = r["report_status"]
        print(f"{qid} | {status} | {client} | Total: {total:.2f} € | Beneficio: {profit:.2f} € | Estado: {label}")

    return 0


def cmd_recent(args: argparse.Namespace) -> int:
    results = find_recent_quotes(limit=args.limit)

    if args.output_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    print(summarize_search_results(results))
    if not results:
        return 0
    print()
    for r in results:
        qid = r["id"] or "?"
        status = r["status"] or "?"
        client = r["client_name"] or "(sin cliente)"
        updated = r["updated_at"] or "?"
        total = r["final_total"]
        print(f"{qid} | {status} | {client} | Total: {total:.2f} € | Actualizado: {updated}")

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
    rs = report["report_status"]

    print(f"Presupuesto:    {meta.get('id', args.quote_id)}")
    print(f"Cliente:        {report['header'].get('client_name') or '(sin cliente)'}")
    print(f"Estado:         {meta.get('status', '?')}")
    print(f"Semáforo:       [{rs['label']}] {rs['reason']}")
    print()
    print(f"Total cliente:  {t['final_total']:.2f} €")
    print(f"Coste total:    {t['cost_subtotal']:.2f} €")
    print(f"Beneficio:      {t['gross_profit']:.2f} € ({pct_str})")
    print(f"Proveedores:    {len(report['supplier_summary'])}")
    print(f"Líneas:         {len(report['lines'])}")
    print()

    if report["human_summary"]:
        print("Resumen rápido:")
        for s in report["human_summary"]:
            print(f"  · {s}")
        print()

    if report["review_recommendations"]:
        print("Qué revisar:")
        for r in report["review_recommendations"]:
            print(f"  ! {r}")
        print()
    elif not report["problems"] and not report["warnings"]:
        print("Qué revisar: ninguna revisión pendiente.")
        print()

    if report["problems"]:
        print(f"Problemas ({len(report['problems'])}):")
        for p in report["problems"]:
            print(f"  ⚠ {p['line']} — {p['issue']}")
        print()

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

    # workflow
    p_wf = sub.add_parser("workflow", help="Flujo completo: importar, guardar, calcular, informar")
    p_wf.add_argument("input_file", help="Ruta al JSON de entrada (snapshot o doc completo)")
    p_wf.add_argument("--id", help="ID explícito del presupuesto (opcional)")
    p_wf.add_argument("--created-by", dest="created_by", default="EON", help="Autor")
    p_wf.add_argument("--source", default="workflow", help="Fuente (default: workflow)")
    p_wf.add_argument("--status", default="draft", help="Estado inicial (default: draft)")
    p_wf.add_argument("--project-type", dest="project_type", help="Tipo de proyecto")
    p_wf.add_argument("--tag", action="append", dest="tag", help="Tag (puede repetirse)")
    p_wf.add_argument("--no-report", dest="no_report", action="store_true", help="No generar informe HTML")
    p_wf.add_argument("--no-holded", dest="no_holded", action="store_true", help="No exportar payload Holded")
    p_wf.add_argument("--report-output", dest="report_output", help="Ruta del informe HTML")
    p_wf.add_argument("--holded-output", dest="holded_output", help="Ruta del payload Holded")
    p_wf.add_argument("--json", dest="output_json", action="store_true", help="Salida JSON")
    p_wf.set_defaults(func=cmd_workflow)

    # eon-tools
    p_eon = sub.add_parser("eon-tools", help="Listar herramientas disponibles para EON")
    p_eon.set_defaults(func=cmd_eon_tools)

    # eon-summary
    p_eon_sum = sub.add_parser("eon-summary", help="Resumen EON de un presupuesto")
    p_eon_sum.add_argument("quote_id", help="ID del presupuesto")
    p_eon_sum.add_argument("--json", dest="output_json", action="store_true", help="Salida JSON")
    p_eon_sum.set_defaults(func=cmd_eon_summary)

    # search
    p_search = sub.add_parser("search", help="Buscar presupuestos guardados")
    p_search.add_argument("query", nargs="?", default=None, help="Texto libre (busca en cliente, proveedor, líneas, tags...)")
    p_search.add_argument("--client", help="Filtrar por nombre de cliente (parcial)")
    p_search.add_argument("--supplier", help="Filtrar por proveedor (parcial)")
    p_search.add_argument("--status", help="Filtrar por estado")
    p_search.add_argument("--project-type", dest="project_type", help="Filtrar por tipo de proyecto")
    p_search.add_argument("--tag", help="Filtrar por tag")
    p_search.add_argument("--min-profit", dest="min_profit", type=float, help="Beneficio mínimo")
    p_search.add_argument("--max-profit", dest="max_profit", type=float, help="Beneficio máximo")
    p_search.add_argument("--min-total", dest="min_total", type=float, help="Total cliente mínimo")
    p_search.add_argument("--max-total", dest="max_total", type=float, help="Total cliente máximo")
    p_search.add_argument("--has-warnings", dest="has_warnings", action="store_true", default=False, help="Solo con warnings")
    p_search.add_argument("--has-problems", dest="has_problems", action="store_true", default=False, help="Solo con problemas")
    p_search.add_argument("--sort-by", dest="sort_by", default="updated_at", help="Campo de ordenación (default: updated_at)")
    p_search.add_argument("--asc", action="store_true", default=False, help="Orden ascendente (default: descendente)")
    p_search.add_argument("--limit", type=int, help="Límite de resultados")
    p_search.add_argument("--json", dest="output_json", action="store_true", help="Salida JSON")
    p_search.set_defaults(func=cmd_search)

    # recent
    p_recent = sub.add_parser("recent", help="Últimos presupuestos por fecha de actualización")
    p_recent.add_argument("--limit", type=int, default=10, help="Número de resultados (default: 10)")
    p_recent.add_argument("--json", dest="output_json", action="store_true", help="Salida JSON")
    p_recent.set_defaults(func=cmd_recent)

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
