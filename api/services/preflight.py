"""Safe release and live-demo readiness checks."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from api.services.data_loader import load_json
from api.services.model_registry import (
    ModelRegistryError,
    active_model_for_task,
    get_model_registry,
    reconcile_forecast_point,
)


def _check(name: str, ok: bool, detail: str, *, critical: bool = True) -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "detail": detail[:240], "critical": critical}


def _sync_checks(user_store, queue_store) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    required = (
        "model_registry.json", "comparacao_modelos.json", "previsoes_baseline.json",
        "risco_ola.json", "clusters.json", "kpi_atingimento.json",
    )
    missing = [filename for filename in required if load_json(filename) is None]
    checks.append(_check(
        "artefatos",
        not missing,
        "Artefatos canônicos carregados." if not missing else f"Ausentes: {', '.join(missing)}",
    ))

    try:
        registry = get_model_registry()
        active_volume = active_model_for_task("volume_d1_d7")
        active_risk = active_model_for_task("ola_risk_triage")
        shadows = [item for item in registry.get("models", []) if item.get("status") == "shadow"]
        registry_ok = bool(active_volume and active_risk and shadows)
        detail = (
            f"Ativos: {active_volume.get('display_name')} e {active_risk.get('display_name')}; "
            f"{len(shadows)} candidato(s) shadow."
            if registry_ok else "Ativos ou candidatos shadow não estão definidos de forma única."
        )
        checks.append(_check("registro_modelos", registry_ok, detail))
    except ModelRegistryError as exc:
        checks.append(_check("registro_modelos", False, str(exc)))

    baseline = load_json("previsoes_baseline.json") or {}
    series = baseline.get("serie", [])
    reconciled = [
        reconcile_forecast_point(item.get("total"), item.get("P2"), item.get("P3"))
        for item in series
    ]
    closes = len(reconciled) == 7 and all(
        point.get("total") == point.get("p2") + point.get("p3")
        for point in reconciled
        if point.get("p2") is not None and point.get("p3") is not None
    )
    checks.append(_check(
        "reconciliacao_previsao", closes,
        "Total = P2 + P3 em D+1…D+7." if closes else "A previsão pública não fecha matematicamente.",
    ))

    for name, store in (("banco_autorizacao", user_store), ("fila_operacional", queue_store)):
        try:
            with store.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            checks.append(_check(name, True, "Conexão e esquema disponíveis."))
        except Exception as exc:  # no secret-bearing exception is returned
            checks.append(_check(name, False, f"Indisponível: {type(exc).__name__}"))
    return checks


async def run_preflight(provider, user_store, queue_store) -> dict[str, Any]:
    checks = await asyncio.to_thread(_sync_checks, user_store, queue_store)
    try:
        llm = await provider.health()
        llm_ok = bool(llm.get("available"))
        detail = (
            f"{llm.get('provider', 'provider')} / {llm.get('model', 'modelo')} disponível."
            if llm_ok else "Provider analítico indisponível; consultas determinísticas continuam operando."
        )
        checks.append(_check("assistente_analitico", llm_ok, detail))
    except Exception as exc:
        checks.append(_check(
            "assistente_analitico", False,
            f"Falha controlada no provider: {type(exc).__name__}",
        ))

    critical_failures = [item for item in checks if item["critical"] and not item["ok"]]
    return {
        "status": "ready" if not critical_failures else "blocked",
        "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "checks": checks,
        "passed": sum(1 for item in checks if item["ok"]),
        "total": len(checks),
    }
