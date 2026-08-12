"""Offline, dependency-free release contract used by CI before deployment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).parents[2]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


class ReleasePreflightError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleasePreflightError(f"Não foi possível ler {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleasePreflightError(f"{path.name} deve conter um objeto JSON")
    return value


def validate_release(outputs: Path = OUTPUTS_DIR) -> list[str]:
    registry = _load(outputs / "model_registry.json")
    if registry.get("schema_version") != 1:
        raise ReleasePreflightError("Versão do registro de modelos inválida")
    models = registry.get("models", [])
    if not isinstance(models, list):
        raise ReleasePreflightError("Registro de modelos inválido")
    for task in ("volume_d1_d7", "ola_risk_triage"):
        active = [item for item in models if item.get("task") == task and item.get("status") == "active"]
        if len(active) != 1:
            raise ReleasePreflightError(f"{task} deve ter exatamente um modelo ativo")
    shadows = [item for item in models if item.get("status") == "shadow"]
    if len(shadows) < 2:
        raise ReleasePreflightError("Candidatos de volume e risco devem permanecer registrados em shadow")

    baseline = _load(outputs / "previsoes_baseline.json")
    series = baseline.get("serie", [])
    if len(series) != 7:
        raise ReleasePreflightError("Previsão ativa deve conter D+1…D+7")
    required = ["model_registry.json", "risco_ola.json", "clusters.json", "kpi_atingimento.json"]
    missing = [name for name in required if not (outputs / name).exists()]
    if missing:
        raise ReleasePreflightError(f"Artefatos ausentes: {', '.join(missing)}")
    return ["model_registry", "active_models", "shadow_candidates", "forecast_horizon"]


def main() -> None:
    validated = validate_release()
    print(f"OK: release preflight — {', '.join(validated)}")


if __name__ == "__main__":
    main()
