"""Sistema de comandos para editar el QuoteSnapshot."""

from __future__ import annotations

import uuid
from typing import Any

from .models import QuoteLine, QuoteSnapshot
from .validators import (
    CommandError,
    require_line,
    require_supplier,
    validate_margin,
    validate_patch_fields,
    validate_quantity,
    validate_tax,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _replace_line(snapshot: QuoteSnapshot, updated: QuoteLine) -> QuoteSnapshot:
    new_lines = [updated if line.id == updated.id else line for line in snapshot.lines]
    return snapshot.model_copy(update={"lines": new_lines})


def _lines_for_supplier(snapshot: QuoteSnapshot, supplier: str) -> list[QuoteLine]:
    return [line for line in snapshot.lines if line.supplier == supplier]


# ---------------------------------------------------------------------------
# Handlers de comandos
# ---------------------------------------------------------------------------

def _cmd_add_line(snapshot: QuoteSnapshot, cmd: dict) -> QuoteSnapshot:
    line_data = cmd.get("line", {})
    if "id" not in line_data:
        line_data = {**line_data, "id": str(uuid.uuid4())}
    line = QuoteLine(**line_data)
    return snapshot.model_copy(update={"lines": [*snapshot.lines, line]})


def _cmd_update_line(snapshot: QuoteSnapshot, cmd: dict) -> QuoteSnapshot:
    line_id = cmd["line_id"]
    require_line(snapshot, line_id)
    patch: dict = cmd.get("patch", {})
    validate_patch_fields(patch)

    new_lines = []
    for line in snapshot.lines:
        if line.id == line_id:
            updated_data = line.model_dump()
            updated_data.update(patch)
            line = QuoteLine(**updated_data)
        new_lines.append(line)
    return snapshot.model_copy(update={"lines": new_lines})


def _cmd_delete_line(snapshot: QuoteSnapshot, cmd: dict) -> QuoteSnapshot:
    line_id = cmd["line_id"]
    require_line(snapshot, line_id)
    new_lines = [line for line in snapshot.lines if line.id != line_id]
    return snapshot.model_copy(update={"lines": new_lines})


def _cmd_set_global_margin(snapshot: QuoteSnapshot, cmd: dict) -> QuoteSnapshot:
    margin = float(cmd["margin"])
    validate_margin(margin)
    new_header = snapshot.header.model_copy(update={"global_margin": margin})
    return snapshot.model_copy(update={"header": new_header})


def _cmd_set_global_tax(snapshot: QuoteSnapshot, cmd: dict) -> QuoteSnapshot:
    tax = float(cmd["tax"])
    validate_tax(tax)
    new_header = snapshot.header.model_copy(update={"tax": tax})
    return snapshot.model_copy(update={"header": new_header})


def _cmd_set_include_tax(snapshot: QuoteSnapshot, cmd: dict) -> QuoteSnapshot:
    include_tax = bool(cmd["include_tax"])
    new_header = snapshot.header.model_copy(update={"include_tax": include_tax})
    return snapshot.model_copy(update={"header": new_header})


def _cmd_set_line_margin(snapshot: QuoteSnapshot, cmd: dict) -> QuoteSnapshot:
    line_id = cmd["line_id"]
    margin = float(cmd["margin"])
    require_line(snapshot, line_id)
    validate_margin(margin)
    return _cmd_update_line(snapshot, {"line_id": line_id, "patch": {"margin": margin}})


def _cmd_set_line_quantity(snapshot: QuoteSnapshot, cmd: dict) -> QuoteSnapshot:
    line_id = cmd["line_id"]
    quantity = float(cmd["quantity"])
    require_line(snapshot, line_id)
    validate_quantity(quantity)
    return _cmd_update_line(snapshot, {"line_id": line_id, "patch": {"quantity": quantity}})


def _cmd_set_line_sale_mode(snapshot: QuoteSnapshot, cmd: dict) -> QuoteSnapshot:
    line_id = cmd["line_id"]
    require_line(snapshot, line_id)
    patch: dict[str, Any] = {"sale_mode": cmd["sale_mode"]}
    if "sale_value" in cmd:
        patch["sale_value"] = cmd["sale_value"]
    return _cmd_update_line(snapshot, {"line_id": line_id, "patch": patch})


def _cmd_set_line_supplier_discounts(snapshot: QuoteSnapshot, cmd: dict) -> QuoteSnapshot:
    line_id = cmd["line_id"]
    require_line(snapshot, line_id)
    discounts = [float(d) for d in cmd["discounts"]]
    return _cmd_update_line(
        snapshot, {"line_id": line_id, "patch": {"supplier_discounts": discounts}}
    )


def _cmd_set_line_supplier_net_unit_cost(snapshot: QuoteSnapshot, cmd: dict) -> QuoteSnapshot:
    line_id = cmd["line_id"]
    require_line(snapshot, line_id)
    cost = float(cmd["cost"])
    return _cmd_update_line(
        snapshot, {"line_id": line_id, "patch": {"supplier_net_unit_cost": cost}}
    )


def _cmd_apply_margin_to_all(snapshot: QuoteSnapshot, cmd: dict) -> QuoteSnapshot:
    margin = float(cmd["margin"])
    validate_margin(margin)
    new_lines = [
        line.model_copy(update={"margin": margin, "sale_mode": "margin"})
        for line in snapshot.lines
    ]
    return snapshot.model_copy(update={"lines": new_lines})


def _cmd_apply_margin_to_supplier(snapshot: QuoteSnapshot, cmd: dict) -> QuoteSnapshot:
    supplier = cmd["supplier"]
    margin = float(cmd["margin"])
    require_supplier(snapshot, supplier)
    validate_margin(margin)
    new_lines = [
        line.model_copy(update={"margin": margin, "sale_mode": "margin"})
        if line.supplier == supplier
        else line
        for line in snapshot.lines
    ]
    return snapshot.model_copy(update={"lines": new_lines})


def _cmd_apply_tax_to_all(snapshot: QuoteSnapshot, cmd: dict) -> QuoteSnapshot:
    tax = float(cmd["tax"])
    validate_tax(tax)
    new_lines = [line.model_copy(update={"tax": tax}) for line in snapshot.lines]
    return snapshot.model_copy(update={"lines": new_lines})


def _cmd_apply_tax_to_supplier(snapshot: QuoteSnapshot, cmd: dict) -> QuoteSnapshot:
    supplier = cmd["supplier"]
    tax = float(cmd["tax"])
    require_supplier(snapshot, supplier)
    validate_tax(tax)
    new_lines = [
        line.model_copy(update={"tax": tax}) if line.supplier == supplier else line
        for line in snapshot.lines
    ]
    return snapshot.model_copy(update={"lines": new_lines})


def _cmd_apply_pass_supplier_discount_to_supplier(
    snapshot: QuoteSnapshot, cmd: dict
) -> QuoteSnapshot:
    supplier = cmd["supplier"]
    enabled = bool(cmd.get("enabled", True))
    require_supplier(snapshot, supplier)
    new_lines = [
        line.model_copy(update={"pass_supplier_discount_to_client": enabled})
        if line.supplier == supplier
        else line
        for line in snapshot.lines
    ]
    return snapshot.model_copy(update={"lines": new_lines})


def _cmd_apply_patch_to_supplier(snapshot: QuoteSnapshot, cmd: dict) -> QuoteSnapshot:
    supplier = cmd["supplier"]
    patch: dict = cmd.get("patch", {})
    require_supplier(snapshot, supplier)
    validate_patch_fields(patch)
    new_lines = [
        QuoteLine(**{**line.model_dump(), **patch}) if line.supplier == supplier else line
        for line in snapshot.lines
    ]
    return snapshot.model_copy(update={"lines": new_lines})


# ---------------------------------------------------------------------------
# Registro de comandos
# ---------------------------------------------------------------------------

_COMMAND_HANDLERS: dict[str, Any] = {
    "add_line": _cmd_add_line,
    "update_line": _cmd_update_line,
    "delete_line": _cmd_delete_line,
    "set_global_margin": _cmd_set_global_margin,
    "set_global_tax": _cmd_set_global_tax,
    "set_include_tax": _cmd_set_include_tax,
    "set_line_margin": _cmd_set_line_margin,
    "set_line_quantity": _cmd_set_line_quantity,
    "set_line_sale_mode": _cmd_set_line_sale_mode,
    "set_line_supplier_discounts": _cmd_set_line_supplier_discounts,
    "set_line_supplier_net_unit_cost": _cmd_set_line_supplier_net_unit_cost,
    "apply_margin_to_all": _cmd_apply_margin_to_all,
    "apply_margin_to_supplier": _cmd_apply_margin_to_supplier,
    "apply_tax_to_all": _cmd_apply_tax_to_all,
    "apply_tax_to_supplier": _cmd_apply_tax_to_supplier,
    "apply_pass_supplier_discount_to_supplier": _cmd_apply_pass_supplier_discount_to_supplier,
    "apply_patch_to_supplier": _cmd_apply_patch_to_supplier,
}


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def apply_command(snapshot: QuoteSnapshot, command: dict) -> QuoteSnapshot:
    """Aplica un único comando al snapshot y devuelve el nuevo snapshot."""
    cmd_type = command.get("type")
    if not cmd_type:
        raise CommandError("El comando debe tener un campo 'type'.")
    handler = _COMMAND_HANDLERS.get(cmd_type)
    if handler is None:
        raise CommandError(f"Comando desconocido: '{cmd_type}'.")
    return handler(snapshot, command)


def apply_commands(snapshot: QuoteSnapshot, commands: list[dict]) -> QuoteSnapshot:
    """Aplica una lista de comandos en orden."""
    for cmd in commands:
        snapshot = apply_command(snapshot, cmd)
    return snapshot
