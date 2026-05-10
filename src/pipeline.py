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
    save_models(out["modelos"])
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


STEPS = {
    "fe": step_feature_engineering,
    "xgb": step_xgboost,
    "km": step_kmeans,
    "kpi": step_kpi,
    "prophet": lambda: step_prophet(use_monte_carlo=False),
    "prophet-mc": lambda: step_prophet(use_monte_carlo=True),
}


def main(step: str | None = None) -> None:
    t0 = time.time()

    if step:
        if step not in STEPS:
            print(f"Step inválido: {step}. Opções: {list(STEPS)}")
            sys.exit(1)
        STEPS[step]()
    else:
        for fn in STEPS.values():
            fn()

    print(f"Pipeline concluído em {time.time() - t0:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", choices=list(STEPS), default=None,
                        metavar="{" + ",".join(STEPS) + "}")
    args = parser.parse_args()
    main(args.step)
