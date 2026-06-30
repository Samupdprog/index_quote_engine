"""CLI de EON — punto de entrada para pruebas desde terminal."""

import argparse
import json
import sys

from .orchestrator import handle_user_request


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="eon",
        description="EON — Orquestador de presupuestos Index Clima",
    )
    parser.add_argument("text", help="Petición en lenguaje natural")
    parser.add_argument(
        "--file",
        dest="files",
        action="append",
        default=[],
        metavar="PATH",
        help="Archivo adjunto (se puede repetir)",
    )
    parser.add_argument(
        "--json",
        dest="output_json",
        action="store_true",
        help="Salida en formato JSON",
    )

    args = parser.parse_args()

    try:
        result = handle_user_request(args.text, files=args.files)
    except Exception as exc:
        print(f"\n[EON] Error inesperado: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.output_json:
        print(json.dumps(result.__dict__, ensure_ascii=False, default=str, indent=2))
        sys.exit(0 if result.success else 1)

    # Salida legible
    status = "OK" if result.success else "PENDIENTE"
    print(f"\n[EON] Acción: {result.action}  |  Estado: {status}")
    if result.summary:
        print(f"      {result.summary}")
    if result.questions:
        print("\n  Preguntas pendientes:")
        for q in result.questions:
            print(f"    · [{q.field}] {q.question}")
    if result.error:
        print(f"\n  Error: {result.error}", file=sys.stderr)
        if result.details:
            print(
                f"  Detalles: {json.dumps(result.details, ensure_ascii=False, default=str, indent=4)}",
                file=sys.stderr,
            )
    if result.data and not result.questions:
        print(f"\n  Datos:\n{json.dumps(result.data, ensure_ascii=False, default=str, indent=4)}")

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
