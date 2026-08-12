"""Build an auditable LSTM × Prophet comparison on the shared temporal holdout."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).parents[2]
LSTM_PATH = PROJECT_ROOT / "outputs" / "previsoes_lstm.json"
PROPHET_PATH = PROJECT_ROOT / "outputs" / "previsoes_volume.json"
PROPHET_MC_PATH = PROJECT_ROOT / "outputs" / "previsoes_volume_mc.json"
BASELINE_PATH = PROJECT_ROOT / "outputs" / "previsoes_baseline.json"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "comparacao_modelos.json"
EXPECTED_PROTOCOL = "rolling_origin_2025Q4_D1_D7"


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Artefato ausente: {path}")
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def build_comparison() -> dict[str, Any]:
    lstm = _read(LSTM_PATH)
    prophet = _read(PROPHET_PATH)
    prophet_mc = _read(PROPHET_MC_PATH)
    baseline = _read(BASELINE_PATH)
    protocols = {
        lstm.get("protocolo_validacao"),
        prophet.get("protocolo_validacao"),
        prophet_mc.get("protocolo_validacao"),
        baseline.get("protocolo_validacao"),
    }
    if protocols != {EXPECTED_PROTOCOL}:
        raise ValueError(f"Protocolos incompatíveis: {sorted(str(value) for value in protocols)}")

    by_series: dict[str, Any] = {}
    for series in ("total", "p2", "p3"):
        lstm_metrics = lstm["metricas_holdout_comum"][series]["horizontes"]
        prophet_metrics = prophet[series]["metricas"]["por_horizonte"]
        prophet_mc_metrics = prophet_mc[series]["metricas"]["por_horizonte"]
        baseline_metrics = baseline["metricas_holdout_comum"][series]["horizontes"]
        horizons = {}
        for horizon in range(1, 8):
            key = f"D{horizon}"
            values = {
                "lstm": float(lstm_metrics[key]["mae"]),
                "prophet": float(prophet_metrics[key]["mae"]),
                "prophet_mc": float(prophet_mc_metrics[key]["mae"]),
                "baseline_sazonal": float(baseline_metrics[key]["mae"]),
            }
            ordered = sorted(values.items(), key=lambda item: item[1])
            winner = ordered[0][0] if ordered[0][1] < ordered[1][1] else "empate"
            horizons[key] = {
                **{f"{name}_mae": round(value, 2) for name, value in values.items()},
                "vencedor": winner,
                "reducao_erro_pct_vs_segundo": (
                    round((ordered[1][1] - ordered[0][1]) / ordered[1][1] * 100, 1)
                    if ordered[1][1] else 0.0
                ),
                "n_previsoes": min(
                    int(lstm_metrics[key]["n_previsoes"]),
                    int(prophet_metrics[key]["n_previsoes"]),
                    int(prophet_mc_metrics[key]["n_previsoes"]),
                ),
            }
        means = {
            name: sum(item[f"{name}_mae"] for item in horizons.values()) / 7
            for name in ("lstm", "prophet", "prophet_mc", "baseline_sazonal")
        }
        ordered_means = sorted(means.items(), key=lambda item: item[1])
        by_series[series] = {
            "mae_medio_d1_d7": {name: round(value, 2) for name, value in means.items()},
            "vencedor_geral": ordered_means[0][0] if ordered_means[0][1] < ordered_means[1][1] else "empate",
            "por_horizonte": horizons,
        }

    return {
        "modelo": "comparacao_previsao_volume",
        "gerado_em": date.today().isoformat(),
        "protocolo": EXPECTED_PROTOCOL,
        "holdout": {"inicio": "2025-10-01", "fim": "2025-12-31"},
        "comparaveis": True,
        "nota": (
            "Baseline sazonal, LSTM, Prophet real e Prophet Monte Carlo foram avaliados por rolling "
            "origin no mesmo período. Seleção de variante e base sintética terminam antes do holdout."
        ),
        "series": by_series,
    }


def export_comparison(result: dict[str, Any], path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as destination:
        json.dump(result, destination, ensure_ascii=False, indent=2)


def main() -> None:
    result = build_comparison()
    export_comparison(result)
    print(f"OK: {OUTPUT_PATH.name} — vencedor Total: {result['series']['total']['vencedor_geral']}")


if __name__ == "__main__":
    main()
