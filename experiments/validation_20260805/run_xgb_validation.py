"""Experimento isolado e temporalmente válido do XGBoost de risco OLA.

Nenhum artefato de produção é lido como dataset nem sobrescrito. Categorias e
frequências são ajustadas apenas no treino; hiperparâmetros e thresholds são
escolhidos na validação; o teste Nov-Dez/2025 fica intocado até a avaliação.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
import xgboost as xgb
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import OneHotEncoder


ROOT = Path(__file__).parents[2]
RAW_PATH = ROOT / "data" / "raw" / "LW-DATASET.xlsx"
RESULT_PATH = Path(__file__).with_name("xgb_results.json")
TARGET = "target_ola"
RECALL_TARGET = 0.70

sys.path.insert(0, str(ROOT / "src" / "data"))
from feriados import build_holiday_features  # noqa: E402


CATEGORICAL = [
    "Produto",
    "Categoria",
    "Subcategoria",
    "Grupo designado",
    "Aberto por",
]

NUMERIC = [
    "hora",
    "dia_semana",
    "mes",
    "trimestre",
    "dia_mes",
    "semana_ano",
    "is_horario_comercial",
    "is_fim_de_semana",
    "is_segunda_terca",
    "periodo_dia",
    "lag_1d",
    "lag_7d",
    "rolling_7d",
    "rolling_30d",
    "lag_1d_p2",
    "lag_1d_p3",
    "prioridade_bin",
    "produto_freq",
    "grupo_freq",
    "mes_sin",
    "mes_cos",
    "is_feriado",
    "tipo_feriado",
    "dias_ate_feriado",
    "dias_desde_feriado",
]


def periodo_dia(hour: int) -> int:
    if hour < 6:
        return 0
    if hour < 12:
        return 1
    if hour < 18:
        return 2
    return 3


def load_and_build_features() -> pd.DataFrame:
    columns = [
        "Aberto",
        "Entrou para KPI?",
        "KPI Violado?",
        "Prioridade",
        *CATEGORICAL,
    ]
    raw = pd.read_excel(RAW_PATH, usecols=columns)
    df = raw[raw["Entrou para KPI?"].eq("SIM")].copy()
    df["Aberto"] = pd.to_datetime(df["Aberto"])
    df = df[df["Aberto"].dt.year.eq(2025)].copy()
    df = df.sort_values("Aberto").reset_index(drop=True)
    df[TARGET] = df["KPI Violado?"].eq("SIM").astype(np.int8)

    df["data"] = df["Aberto"].dt.normalize()
    df["hora"] = df["Aberto"].dt.hour
    df["dia_semana"] = df["Aberto"].dt.dayofweek
    df["mes"] = df["Aberto"].dt.month
    df["trimestre"] = df["Aberto"].dt.quarter
    df["dia_mes"] = df["Aberto"].dt.day
    df["semana_ano"] = df["Aberto"].dt.isocalendar().week.astype(int)
    df["is_horario_comercial"] = df["hora"].between(9, 17).astype(np.int8)
    df["is_fim_de_semana"] = df["dia_semana"].ge(5).astype(np.int8)
    df["is_segunda_terca"] = df["dia_semana"].le(1).astype(np.int8)
    df["periodo_dia"] = df["hora"].map(periodo_dia)
    df["prioridade_bin"] = df["Prioridade"].eq("2 - Alta").astype(np.int8)
    df["mes_sin"] = np.sin(2 * np.pi * df["mes"] / 12)
    df["mes_cos"] = np.cos(2 * np.pi * df["mes"] / 12)

    holiday = build_holiday_features(df["Aberto"])
    for column in holiday.columns:
        df[column] = holiday[column].to_numpy()

    calendar = pd.date_range("2025-01-01", "2025-12-31", freq="D")
    daily = df.groupby("data").size().reindex(calendar, fill_value=0).rename("volume")
    daily_p2 = (
        df[df["Prioridade"].eq("2 - Alta")]
        .groupby("data")
        .size()
        .reindex(calendar, fill_value=0)
        .rename("p2")
    )
    daily_p3 = (
        df[df["Prioridade"].eq("3 - Média")]
        .groupby("data")
        .size()
        .reindex(calendar, fill_value=0)
        .rename("p3")
    )
    lag_frame = pd.DataFrame(index=calendar)
    lag_frame["lag_1d"] = daily.shift(1)
    lag_frame["lag_7d"] = daily.shift(7)
    # A média precisa terminar em D-1: o volume do próprio dia ainda não é conhecido.
    lag_frame["rolling_7d"] = daily.shift(1).rolling(7, min_periods=1).mean()
    lag_frame["rolling_30d"] = daily.shift(1).rolling(30, min_periods=1).mean()
    lag_frame["lag_1d_p2"] = daily_p2.shift(1)
    lag_frame["lag_1d_p3"] = daily_p3.shift(1)
    df = df.merge(lag_frame, left_on="data", right_index=True, how="left")
    lag_columns = [
        "lag_1d",
        "lag_7d",
        "rolling_7d",
        "rolling_30d",
        "lag_1d_p2",
        "lag_1d_p3",
    ]
    df[lag_columns] = df[lag_columns].fillna(0.0)

    for column in CATEGORICAL:
        df[column] = df[column].fillna("DESCONHECIDO").astype(str)
    return df


def split_temporally(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = df[df["Aberto"] < pd.Timestamp("2025-09-01")].copy()
    validation = df[
        (df["Aberto"] >= pd.Timestamp("2025-09-01"))
        & (df["Aberto"] < pd.Timestamp("2025-11-01"))
    ].copy()
    test = df[df["Aberto"] >= pd.Timestamp("2025-11-01")].copy()
    return train, validation, test


def add_train_only_frequencies(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> None:
    for source, output in [("Produto", "produto_freq"), ("Grupo designado", "grupo_freq")]:
        mapping = train[source].value_counts(normalize=True).to_dict()
        for frame in (train, validation, test):
            frame[output] = frame[source].map(mapping).fillna(0.0)


def matrices(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> tuple[sp.csr_matrix, sp.csr_matrix, sp.csr_matrix, OneHotEncoder]:
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=True, dtype=np.float32)
    train_cat = encoder.fit_transform(train[CATEGORICAL])
    val_cat = encoder.transform(validation[CATEGORICAL])
    test_cat = encoder.transform(test[CATEGORICAL])

    def combine(frame: pd.DataFrame, encoded: sp.csr_matrix) -> sp.csr_matrix:
        numeric = sp.csr_matrix(frame[NUMERIC].to_numpy(dtype=np.float32))
        return sp.hstack([numeric, encoded], format="csr")

    return (
        combine(train, train_cat),
        combine(validation, val_cat),
        combine(test, test_cat),
        encoder,
    )


def choose_threshold(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    mode: str,
) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, probabilities)
    precision = precision[:-1]
    recall = recall[:-1]
    if mode == "recall70":
        valid = np.flatnonzero(recall >= RECALL_TARGET)
        if len(valid) == 0:
            return float(thresholds[int(np.argmax(recall))])
        best_precision = float(np.max(precision[valid]))
        candidates = valid[np.isclose(precision[valid], best_precision)]
        return float(thresholds[candidates[-1]])
    if mode == "f1":
        f1 = 2 * precision * recall / (precision + recall + 1e-12)
        return float(thresholds[int(np.argmax(f1))])
    raise ValueError(mode)


def classification_at_threshold(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, float | int]:
    prediction = probabilities >= threshold
    tn, fp, fn, tp = confusion_matrix(y_true, prediction, labels=[0, 1]).ravel()
    return {
        "threshold": round(float(threshold), 6),
        "recall": round(float(recall_score(y_true, prediction, zero_division=0)), 4),
        "precision": round(float(precision_score(y_true, prediction, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, prediction, zero_division=0)), 4),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
        "alerts": int(prediction.sum()),
    }


def ranking_metrics(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    prevalence = float(np.mean(y_true))
    pr_auc = float(average_precision_score(y_true, probabilities))
    cutoff = float(np.quantile(probabilities, 0.90))
    top = probabilities >= cutoff
    return {
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(float(roc_auc_score(y_true, probabilities)), 4),
        "prevalence": round(prevalence, 6),
        "pr_auc_lift_over_random": round(pr_auc / prevalence, 2),
        "top_10pct_recall": round(float(recall_score(y_true, top)), 4),
        "top_10pct_precision": round(float(precision_score(y_true, top)), 4),
    }


def bootstrap_intervals(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    iterations: int = 500,
) -> dict[str, list[float]]:
    rng = np.random.default_rng(42)
    pr_scores: list[float] = []
    roc_scores: list[float] = []
    for _ in range(iterations):
        indices = rng.integers(0, len(y_true), len(y_true))
        y_sample = y_true[indices]
        if len(np.unique(y_sample)) < 2:
            continue
        p_sample = probabilities[indices]
        pr_scores.append(float(average_precision_score(y_sample, p_sample)))
        roc_scores.append(float(roc_auc_score(y_sample, p_sample)))
    return {
        "pr_auc_95pct": [round(float(v), 4) for v in np.percentile(pr_scores, [2.5, 97.5])],
        "roc_auc_95pct": [round(float(v), 4) for v in np.percentile(roc_scores, [2.5, 97.5])],
    }


def model_candidates() -> list[dict[str, float | int | str]]:
    common: dict[str, float | int | str] = {
        "objective": "binary:logistic",
        "eval_metric": "aucpr",
        "subsample": 0.85,
        "colsample_bytree": 0.83,
        "gamma": 0.65,
        "max_delta_step": 8,
        "reg_alpha": 1.74,
        "reg_lambda": 3.65,
        "random_state": 42,
        "n_jobs": -1,
        "tree_method": "hist",
    }
    candidates = []
    specs = [
        ("current_like", 8, 5, 0.0108, 454, 48),
        ("shallow_spw20", 3, 10, 0.03, 350, 20),
        ("shallow_spw48", 3, 10, 0.03, 350, 48),
        ("shallow_spw100", 3, 10, 0.03, 350, 100),
        ("medium_spw48", 5, 10, 0.025, 400, 48),
        ("medium_spw100", 5, 10, 0.025, 400, 100),
    ]
    for name, depth, child, rate, trees, weight in specs:
        candidates.append(
            {
                **common,
                "name": name,
                "max_depth": depth,
                "min_child_weight": child,
                "learning_rate": rate,
                "n_estimators": trees,
                "scale_pos_weight": weight,
            }
        )
    return candidates


def split_summary(frame: pd.DataFrame) -> dict[str, object]:
    return {
        "start": frame["Aberto"].min().strftime("%Y-%m-%d"),
        "end": frame["Aberto"].max().strftime("%Y-%m-%d"),
        "n": int(len(frame)),
        "positives": int(frame[TARGET].sum()),
        "prevalence": round(float(frame[TARGET].mean()), 6),
    }


def main() -> None:
    print("Construindo features cronológicas diretamente do XLSX...")
    df = load_and_build_features()
    train, validation, test = split_temporally(df)
    add_train_only_frequencies(train, validation, test)
    x_train, x_val, x_test, encoder = matrices(train, validation, test)
    y_train = train[TARGET].to_numpy()
    y_val = validation[TARGET].to_numpy()
    y_test = test[TARGET].to_numpy()
    print(
        f"Treino {len(train)} ({y_train.sum()} pos) | validação {len(validation)} "
        f"({y_val.sum()} pos) | teste {len(test)} ({y_test.sum()} pos)"
    )

    validation_runs: list[dict[str, object]] = []
    fitted: dict[str, xgb.XGBClassifier] = {}
    for raw_params in model_candidates():
        params = dict(raw_params)
        name = str(params.pop("name"))
        print(f"Treinando candidato {name}...")
        model = xgb.XGBClassifier(**params)
        model.fit(x_train, y_train, verbose=False)
        probabilities = model.predict_proba(x_val)[:, 1]
        metrics = ranking_metrics(y_val, probabilities)
        validation_runs.append({"name": name, **metrics})
        fitted[name] = model
        print(f"  validação PR-AUC={metrics['pr_auc']:.4f} ROC-AUC={metrics['roc_auc']:.4f}")

    # A escolha acontece exclusivamente na validação.
    selected_run = max(validation_runs, key=lambda item: float(item["pr_auc"]))
    selected_name = str(selected_run["name"])
    selected_model = fitted[selected_name]
    val_prob = selected_model.predict_proba(x_val)[:, 1]
    threshold_recall = choose_threshold(y_val, val_prob, "recall70")
    threshold_f1 = choose_threshold(y_val, val_prob, "f1")

    # Só agora o teste é consultado.
    test_prob = selected_model.predict_proba(x_test)[:, 1]
    test_ranking = ranking_metrics(y_test, test_prob)
    test_by_priority: dict[str, object] = {}
    for label, raw_label in [("p2", "2 - Alta"), ("p3", "3 - Média")]:
        mask = test["Prioridade"].eq(raw_label).to_numpy()
        test_by_priority[label] = {
            "n": int(mask.sum()),
            "positives": int(y_test[mask].sum()),
            "ranking": ranking_metrics(y_test[mask], test_prob[mask]),
            "recall70_threshold": classification_at_threshold(
                y_test[mask], test_prob[mask], threshold_recall
            ),
            "f1_threshold": classification_at_threshold(
                y_test[mask], test_prob[mask], threshold_f1
            ),
        }

    feature_names = NUMERIC + encoder.get_feature_names_out(CATEGORICAL).tolist()
    importance = sorted(
        zip(feature_names, selected_model.feature_importances_),
        key=lambda item: -float(item[1]),
    )[:20]
    result = {
        "protocol": {
            "split": "chronological",
            "train": split_summary(train),
            "validation": split_summary(validation),
            "test": split_summary(test),
            "feature_encoding": "OneHotEncoder fit only on train; unseen categories ignored",
            "rolling_features": "all shifted by one day; current-day volume excluded",
            "threshold_selection": "validation only",
            "test_access": "once, after model and thresholds were fixed",
            "n_features_after_one_hot": int(x_train.shape[1]),
            "n_one_hot_features": int(len(encoder.get_feature_names_out())),
        },
        "production_published_reference": {
            "pr_auc": 0.0694,
            "roc_auc": 0.7767,
            "recall70_threshold_metrics": {"recall": 0.7069, "precision": 0.031, "f1": 0.0594},
            "f1_threshold_metrics": {"recall": 0.1379, "precision": 0.2759, "f1": 0.1839},
            "warning": "referência usa split posicional em dataset reverso e seleciona modelo/threshold no teste",
        },
        "validation_candidates": validation_runs,
        "selected_model": selected_name,
        "selected_feature_importance": [
            {"feature": feature, "importance": round(float(value), 6)}
            for feature, value in importance
        ],
        "validation_selected": {
            "ranking": ranking_metrics(y_val, val_prob),
            "recall70": classification_at_threshold(y_val, val_prob, threshold_recall),
            "f1": classification_at_threshold(y_val, val_prob, threshold_f1),
        },
        "untouched_test": {
            "ranking": test_ranking,
            "bootstrap_intervals": bootstrap_intervals(y_test, test_prob),
            "threshold_from_validation_recall70": classification_at_threshold(
                y_test, test_prob, threshold_recall
            ),
            "threshold_from_validation_f1": classification_at_threshold(
                y_test, test_prob, threshold_f1
            ),
            "by_priority": test_by_priority,
        },
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Selecionado: {selected_name}")
    print(
        f"Teste intocado: PR-AUC={test_ranking['pr_auc']:.4f} | "
        f"ROC-AUC={test_ranking['roc_auc']:.4f} | lift={test_ranking['pr_auc_lift_over_random']:.2f}x"
    )
    print(f"Resultado gravado somente no experimento: {RESULT_PATH}")


if __name__ == "__main__":
    main()
