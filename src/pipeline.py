"""
Pipeline orquestrador — executa toda a cadeia de ML em sequência.

Uso:
    python src/pipeline.py              # pipeline completo
    python src/pipeline.py --step fe    # só feature engineering
    python src/pipeline.py --step xgb   # só XGBoost
    python src/pipeline.py --step km    # só K-Means
    python src/pipeline.py --step kpi   # só KPI projection
    python src/pipeline.py --step prophet     # Prophet 2025-only
    python src/pipeline.py --step prophet-mc  # Prophet Monte Carlo (3 anos)
    python src/pipeline.py --step lstm        # LSTM v2 (Monte Carlo 2023-2025)
    python src/pipeline.py --step horizon     # Prophet D+1..D+365 exploratório
    python src/pipeline.py --step compare     # comparação LSTM × Prophet no holdout comum
    python src/pipeline.py --step baseline    # baseline sazonal semanal
    python src/pipeline.py --step segments    # agregados operacionais anonimizados
    python src/pipeline.py --step xgb-specialists  # experimento champion/challenger P2/P3
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def step_feature_engineering() -> None:
    print("=" * 50)
    print("ETAPA 1 — Feature Engineering")
    print("=" * 50)
    from src.data.preprocessor import build_features, save_features

    df = build_features()
    save_features(df)
    print(f"OK: {df.shape[0]} incidentes, {df.shape[1]} features\n")


def step_xgboost() -> None:
    print("=" * 50)
    print("ETAPA 2 — XGBoost (Risco OLA)")
    print("=" * 50)
    from src.models.xgboost_model import export_json, load_data, train

    df = load_data()
    results = train(df)
    export_json(results)
    print("OK: outputs/risco_ola.json gerado\n")


def step_kmeans() -> None:
    print("=" * 50)
    print("ETAPA 3 — K-Means (Clustering)")
    print("=" * 50)
    from src.models.kmeans_model import export_json, load_data, train

    df = load_data()
    results = train(df)
    export_json(results)
    print("OK: outputs/clusters.json gerado\n")


def step_lstm() -> None:
    print("=" * 50)
    print("ETAPA — LSTM (Previsão de Volume)")
    print("=" * 50)
    from src.models.lstm_model import export_json, save_models, train

    out = train()
    export_json(out["resultados"])
    save_models(out["modelos"], out["scalers"])
    mae = out["resultados"]["mae_holdout_92_dias"]
    print(f"OK: previsoes_lstm.json gerado | MAE D+1 Total={mae['total']} P2={mae['p2']} P3={mae['p3']}\n")


def step_prophet(use_monte_carlo: bool = False) -> None:
    label = "Prophet Monte Carlo (2023-2025)" if use_monte_carlo else "Prophet (2025-only)"
    print("=" * 50)
    print(f"ETAPA — {label}")
    print("=" * 50)
    from src.models.prophet_model import (
        OUTPUT_MC_PATH,
        OUTPUT_PATH,
        export_json,
        save_models,
        train,
    )

    out = train(use_monte_carlo=use_monte_carlo)
    path = OUTPUT_MC_PATH if use_monte_carlo else OUTPUT_PATH
    export_json(out["resultados"], path)
    save_models(out["modelos"], prefix="mc_" if use_monte_carlo else "")
    print(f"OK: {path.name} gerado\n")


def step_kpi() -> None:
    print("=" * 50)
    print("ETAPA 4 — KPI Projection")
    print("=" * 50)
    from src.models.kpi_projection import calcular_projecao, export_json, load_data

    kpi = load_data()
    resultado = calcular_projecao(kpi)
    export_json(resultado)
    print("OK: outputs/kpi_atingimento.json gerado\n")


def step_long_horizon() -> None:
    print("=" * 50)
    print("ETAPA — Prophet Long Horizon (Planejamento D+1..D+365)")
    print("=" * 50)
    from src.models.long_horizon_projection import build_projection, export_projection

    result = build_projection()
    export_projection(result)
    print("OK: outputs/previsoes_horizonte_prophet.json gerado\n")


def step_compare() -> None:
    print("=" * 50)
    print("ETAPA — Comparação temporal LSTM × Prophet")
    print("=" * 50)
    from src.models.model_comparison import build_comparison, export_comparison

    result = build_comparison()
    export_comparison(result)
    print(f"OK: outputs/comparacao_modelos.json | vencedor Total={result['series']['total']['vencedor_geral']}\n")


def step_baseline() -> None:
    print("=" * 50)
    print("ETAPA — Baseline sazonal semanal")
    print("=" * 50)
    from src.models.seasonal_baseline import build_baseline, export_baseline

    result = build_baseline()
    export_baseline(result)
    print(f"OK: outputs/previsoes_baseline.json | MAE médio Total={result['metricas_holdout_comum']['total']['mae_medio_d1_d7']}\n")


def step_segments() -> None:
    print("=" * 50)
    print("ETAPA — Agregados de grupos e produtos")
    print("=" * 50)
    from src.models.operational_aggregates import build_aggregates, export_aggregates

    result = build_aggregates()
    export_aggregates(result)
    print(f"OK: {len(result['grupos'])} grupos e {len(result['produtos'])} produtos publicados\n")


def step_xgboost_specialists() -> None:
    """Run the isolated specialist experiment; never replaces production risk output."""
    print("=" * 50)
    print("EXPERIMENTO — XGBoost Generalista × P2 × P3")
    print("=" * 50)
    from src.models.xgboost_specialists import export_report, train_all

    result = train_all(n_trials=30, n_splits=4)
    export_report(result)
    routes = result["roteador_recomendado"]
    print(
        "OK: outputs/experiments/xgboost_specialists.json | "
        f"P2={routes['P2']['modelo_ativo']} P3={routes['P3']['modelo_ativo']}\n"
    )


STEPS = {
    "fe": step_feature_engineering,
    "xgb": step_xgboost,
    "km": step_kmeans,
    "kpi": step_kpi,
    "prophet": lambda: step_prophet(use_monte_carlo=False),
    # O horizonte usa os modelos reais; os modelos Monte Carlo são salvos
    # com prefixo próprio para nunca sobrescrevê-los.
    "horizon": step_long_horizon,
    "prophet-mc": lambda: step_prophet(use_monte_carlo=True),
    "lstm": step_lstm,
    "baseline": step_baseline,
    "compare": step_compare,
    "segments": step_segments,
}

# Experimental steps must be explicitly requested and are intentionally not
# executed by the default production pipeline.
EXPERIMENTAL_STEPS = {
    "xgb-specialists": step_xgboost_specialists,
}
ALL_STEPS = {**STEPS, **EXPERIMENTAL_STEPS}


def main(step: str | None = None) -> None:
    t0 = time.time()

    if step:
        if step not in ALL_STEPS:
            print(f"Step inválido: {step}. Opções: {list(ALL_STEPS)}")
            sys.exit(1)
        ALL_STEPS[step]()
    else:
        for fn in STEPS.values():
            fn()

    print(f"Pipeline concluído em {time.time() - t0:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", choices=list(ALL_STEPS), default=None,
                        metavar="{" + ",".join(ALL_STEPS) + "}")
    args = parser.parse_args()
    main(args.step)
