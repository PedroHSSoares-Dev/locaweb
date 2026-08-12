"""Generate an exploratory D+1..D+365 Prophet projection for chat planning tools.

The dashboard's validated forecast remains D+1..D+7. Beyond D+7 this module
uses the already-trained Prophet v5/v6 models and fixed recent-volume
regressors. It is a planning scenario, not a validated long-range forecast.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import pandas as pd

from src.models.prophet_model import FLOOR_P10, LAG_COLS


PROJECT_ROOT = Path(__file__).parents[2]
MODELS_DIR = PROJECT_ROOT / "models_saved"
BASELINE_PATH = PROJECT_ROOT / "outputs" / "previsoes_volume.json"
ACTIVE_SHORT_PATH = PROJECT_ROOT / "outputs" / "previsoes_baseline.json"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "previsoes_horizonte_prophet.json"
MAX_HORIZON = 365
SERIES = ("total", "p2", "p3")


def _load_model(series: str, variant: str):
    path = MODELS_DIR / f"prophet_{series}_{variant}.pkl"
    if not path.exists():
        raise FileNotFoundError(f"Modelo ausente: {path}")
    # Loading pickle is restricted to explicit pipeline-generated local paths.
    with path.open("rb") as model_file:
        return pickle.load(model_file)  # noqa: S301 - trusted offline ML artifact


def _future_frame(model: Any, horizon: int, variant: str) -> pd.DataFrame:
    last_date = pd.Timestamp(model.history["ds"].max())
    future = pd.DataFrame({
        "ds": pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon, freq="D")
    })
    recent_mean = float(model.history["y"].tail(7).mean())
    for column in LAG_COLS:
        future[column] = recent_mean
    if variant == "v6":
        future["is_dia_util"] = (future["ds"].dt.dayofweek < 5).astype(int)
        if model.holidays is not None:
            holiday_dates = set(pd.to_datetime(model.holidays["ds"]).dt.date)
            future.loc[future["ds"].dt.date.isin(holiday_dates), "is_dia_util"] = 0
    return future


def _project_series(
    series: str, baseline: dict[str, Any], active_short: dict[str, Any],
) -> list[dict[str, Any]]:
    predictions: dict[str, pd.DataFrame] = {}
    for variant in ("v5", "v6"):
        model = _load_model(series, variant)
        future = _future_frame(model, MAX_HORIZON, variant)
        predictions[variant] = model.predict(future)[
            ["ds", "yhat", "yhat_lower", "yhat_upper"]
        ].reset_index(drop=True)

    existing = {
        point["ds"]: point
        for point in baseline.get(series, {}).get("serie_7d", [])
        if isinstance(point, dict) and point.get("ds")
    }
    active_key = {"total": "total", "p2": "P2", "p3": "P3"}[series]
    active_points = {
        point["ds"]: point.get(active_key)
        for point in active_short.get("serie", [])
        if isinstance(point, dict) and point.get("ds")
    }
    floors = FLOOR_P10[series]
    result: list[dict[str, Any]] = []

    for index in range(MAX_HORIZON):
        v5 = predictions["v5"].iloc[index]
        v6 = predictions["v6"].iloc[index]
        target_date = pd.Timestamp(v5["ds"])
        date_key = target_date.strftime("%Y-%m-%d")
        floor = float(floors.get(target_date.dayofweek, 0))

        if date_key in existing and date_key in active_points:
            point = existing[date_key]
            central = float(active_points[date_key])
            lower = min(central, float(point.get("yhat_lower", 0)))
            upper = max(central, float(point.get("yhat_upper", central)))
            method = "baseline_sazonal_validado_com_intervalo_prophet_referencia"
        else:
            central = (float(v5["yhat"]) + float(v6["yhat"])) / 2
            lower = min(float(v5["yhat_lower"]), float(v6["yhat_lower"]))
            upper = max(float(v5["yhat_upper"]), float(v6["yhat_upper"]))
            method = "media_v5_v6_exploratoria"

        # D+1…D+7 must remain byte-for-byte equivalent in value to the
        # validated baseline. Historical floors are only a planning heuristic
        # for the explicitly exploratory D+8…D+365 region.
        apply_floor = date_key not in existing
        result.append({
            "ds": date_key,
            "horizonte_dias": index + 1,
            "yhat": round(max(floor, central) if apply_floor else central, 1),
            "lower": round(max(0.0, lower), 1),
            "upper": round(max(floor, upper) if apply_floor else upper, 1),
            "metodo": method,
        })
    return result


def build_projection() -> dict[str, Any]:
    if not BASELINE_PATH.exists():
        raise FileNotFoundError(f"Baseline ausente: {BASELINE_PATH}")
    if not ACTIVE_SHORT_PATH.exists():
        raise FileNotFoundError(f"Previsão curta ativa ausente: {ACTIVE_SHORT_PATH}")
    with BASELINE_PATH.open(encoding="utf-8") as baseline_file:
        baseline = json.load(baseline_file)
    with ACTIVE_SHORT_PATH.open(encoding="utf-8") as active_file:
        active_short = json.load(active_file)

    projected = {
        series: _project_series(series, baseline, active_short) for series in SERIES
    }
    return {
        "modelo": "prophet_v5_v6_long_horizon_planning",
        "data_base": "2025-12-31",
        "horizonte_max_dias": MAX_HORIZON,
        "horizonte_validado_dias": 7,
        "metodologia": {
            "D1_D7": "baseline sazonal ativo, avaliado por rolling origin no holdout Out–Dez/2025",
            "D8_D365": (
                "média dos modelos Prophet v5/v6 já treinados, regressores de volume fixados "
                "na média recente e piso histórico por dia da semana"
            ),
        },
        "uso_autorizado": "planejamento exploratório e cenários; não tratar D+8..D+365 como previsão validada",
        "series": projected,
    }


def export_projection(result: dict[str, Any], path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output_file:
        json.dump(result, output_file, ensure_ascii=False, indent=2)


def main() -> None:
    result = build_projection()
    export_projection(result)
    print(f"OK: {OUTPUT_PATH.name} gerado com D+1..D+{MAX_HORIZON}")


if __name__ == "__main__":
    main()
