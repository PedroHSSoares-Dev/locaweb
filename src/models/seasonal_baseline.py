"""Auditable weekly seasonal-naive baseline for volume forecasts."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.models.lstm_model import HOLDOUT_END, HOLDOUT_START, load_real_series


PROJECT_ROOT = Path(__file__).parents[2]
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "previsoes_baseline.json"
COMMON_PROTOCOL = "rolling_origin_2025Q4_D1_D7"


def _evaluate(series: pd.DataFrame) -> dict[str, Any]:
    actual = series.set_index("ds")["y"].astype(float).sort_index()
    errors: dict[int, list[float]] = {horizon: [] for horizon in range(1, 8)}
    origins = pd.date_range(HOLDOUT_START - pd.Timedelta(days=1), HOLDOUT_END - pd.Timedelta(days=1))
    for origin in origins:
        max_horizon = min(7, (HOLDOUT_END - origin).days)
        for horizon in range(1, max_horizon + 1):
            target = origin + pd.Timedelta(days=horizon)
            prediction = float(np.median([
                actual.loc[target - pd.Timedelta(days=7 * week)]
                for week in range(1, 4)
            ]))
            errors[horizon].append(abs(float(actual.loc[target]) - prediction))
    horizons = {
        f"D{horizon}": {
            "mae": round(float(np.mean(values)), 2),
            "n_previsoes": len(values),
        }
        for horizon, values in errors.items()
    }
    return {
        "protocolo": COMMON_PROTOCOL,
        "inicio": HOLDOUT_START.strftime("%Y-%m-%d"),
        "fim": HOLDOUT_END.strftime("%Y-%m-%d"),
        "horizontes": horizons,
        "mae_medio_d1_d7": round(float(np.mean([item["mae"] for item in horizons.values()])), 2),
    }


def build_baseline() -> dict[str, Any]:
    loaded = dict(zip(("total", "p2", "p3"), load_real_series()))
    metrics = {name: _evaluate(series) for name, series in loaded.items()}
    indexes = {name: series.set_index("ds")["y"].astype(float) for name, series in loaded.items()}
    last_date = max(index.index.max() for index in indexes.values())
    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=7)
    forecast = []
    for position, target in enumerate(future_dates, start=1):
        forecast.append({
            "ds": target.strftime("%Y-%m-%d"),
            "horizonte": f"D+{position}",
            "total": round(float(np.median([indexes["total"].loc[target - pd.Timedelta(days=7 * week)] for week in range(1, 4)])), 1),
            "P2": round(float(np.median([indexes["p2"].loc[target - pd.Timedelta(days=7 * week)] for week in range(1, 4)])), 1),
            "P3": round(float(np.median([indexes["p3"].loc[target - pd.Timedelta(days=7 * week)] for week in range(1, 4)])), 1),
        })
    return {
        "modelo": "baseline_sazonal_7d",
        "gerado_em": date.today().isoformat(),
        "protocolo_validacao": COMMON_PROTOCOL,
        "metodologia": "mediana das três semanas anteriores para o mesmo dia da semana",
        "holdout": "2025-10-01 a 2025-12-31 (rolling origin 100% real)",
        "metricas_holdout_comum": metrics,
        "mae_holdout_92_dias": {
            name: value["horizontes"]["D1"]["mae"] for name, value in metrics.items()
        },
        "d1": {"total": forecast[0]["total"], "p2": forecast[0]["P2"], "p3": forecast[0]["P3"]},
        "d7": {"total": forecast[6]["total"], "p2": forecast[6]["P2"], "p3": forecast[6]["P3"]},
        "serie": forecast,
    }


def export_baseline(result: dict[str, Any], path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as destination:
        json.dump(result, destination, ensure_ascii=False, indent=2)


def main() -> None:
    result = build_baseline()
    export_baseline(result)
    print(f"OK: {OUTPUT_PATH.name} — MAE médio Total={result['metricas_holdout_comum']['total']['mae_medio_d1_d7']}")


if __name__ == "__main__":
    main()
