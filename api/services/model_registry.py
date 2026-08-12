"""Canonical model governance and public forecast reconciliation."""

from __future__ import annotations

from typing import Any

from api.services.data_loader import load_json


class ModelRegistryError(RuntimeError):
    """Raised when the published registry is missing or internally inconsistent."""


def get_model_registry() -> dict[str, Any]:
    registry = load_json("model_registry.json")
    if not isinstance(registry, dict) or registry.get("schema_version") != 1:
        raise ModelRegistryError("Registro canônico de modelos indisponível.")
    models = registry.get("models")
    if not isinstance(models, list) or not models:
        raise ModelRegistryError("Registro canônico de modelos vazio.")
    return registry


def models_for_task(task: str) -> list[dict[str, Any]]:
    return [
        item for item in get_model_registry().get("models", [])
        if isinstance(item, dict) and item.get("task") == task
    ]


def active_model_for_task(task: str) -> dict[str, Any] | None:
    active = [item for item in models_for_task(task) if item.get("status") == "active"]
    if len(active) > 1:
        raise ModelRegistryError(f"Mais de um modelo ativo para {task}.")
    return active[0] if active else None


def reconcile_forecast_point(
    total: float | int | None,
    p2: float | int | None,
    p3: float | int | None,
) -> dict[str, Any]:
    """Preserve the validated Total and proportionally reconcile P2/P3 to it.

    The three series are independently trained. Public executive outputs must
    nevertheless close mathematically, so the segment mix is scaled to the
    active Total using a deterministic largest-remainder equivalent for two
    segments. Raw rounded values stay available for audit.
    """
    if total is None:
        return {
            "total": None,
            "p2": None if p2 is None else round(max(float(p2), 0)),
            "p3": None if p3 is None else round(max(float(p3), 0)),
            "reconciliado": False,
            "valores_brutos": None,
        }

    total_value = round(max(float(total), 0))
    if p2 is None or p3 is None:
        return {
            "total": total_value,
            "p2": None if p2 is None else round(max(float(p2), 0)),
            "p3": None if p3 is None else round(max(float(p3), 0)),
            "reconciliado": False,
            "valores_brutos": None,
        }

    raw_p2 = round(max(float(p2), 0))
    raw_p3 = round(max(float(p3), 0))
    raw_sum = raw_p2 + raw_p3
    if raw_sum <= 0:
        reconciled_p2, reconciled_p3 = 0, total_value
    else:
        reconciled_p2 = round(total_value * raw_p2 / raw_sum)
        reconciled_p2 = min(max(reconciled_p2, 0), total_value)
        reconciled_p3 = total_value - reconciled_p2

    adjusted = raw_sum != total_value
    return {
        "total": total_value,
        "p2": reconciled_p2,
        "p3": reconciled_p3,
        "reconciliado": adjusted,
        "valores_brutos": (
            {"total": total_value, "p2": raw_p2, "p3": raw_p3}
            if adjusted else None
        ),
    }
