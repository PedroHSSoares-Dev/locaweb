"""Champion/challenger training for general, P2 and P3 OLA-risk models.

This module is deliberately isolated from ``outputs/risco_ola.json``.  It
performs recent rolling-origin selection through June, chooses thresholds on
Q3, reports once on Q4 and writes only experimental artifacts.

The generalist parameters are locked from the pre-Q4 temporal Optuna study.
Specialists are tuned without consulting Q3 or Q4.  P2 remains experimental
while the training sample contains fewer than 50 positive examples.
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import optuna
import pandas as pd
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.models.specialist_policy import promotion_decision
from src.models.xgboost_model import (
    FEATURES,
    TARGET,
    _apply_training_statistics,
    load_data,
)

PROJECT_ROOT = Path(__file__).parents[2]
REPORT_PATH = PROJECT_ROOT / "outputs" / "experiments" / "xgboost_specialists.json"
MODEL_DIR = PROJECT_ROOT / "models_saved" / "xgboost_specialists"

RANDOM_STATE = 42
PRIORITY_LABELS = {1: "P2", 0: "P3"}
SPECIALIST_FEATURES = [feature for feature in FEATURES if feature != "prioridade_bin"]

# Locked before the specialist comparison.  These parameters were selected on
# inner temporal folds and only then evaluated on Q3/Q4 in notebook 04b.
GENERALIST_SPEC = {
    "kind": "xgboost",
    "balance": "none",
    "params": {
        "n_estimators": 500,
        "max_depth": 7,
        "learning_rate": 0.03607939886307854,
        "subsample": 0.7454404070203796,
        "colsample_bytree": 0.9630659181130072,
        "min_child_weight": 2,
        "gamma": 2.9282357199398956,
        "max_delta_step": 4,
        "reg_alpha": 0.4520071476614973,
        "reg_lambda": 0.11537349692556405,
    },
}

COMMON_XGB_PARAMS = {
    "objective": "binary:logistic",
    "eval_metric": "aucpr",
    "random_state": RANDOM_STATE,
    "n_jobs": -1,
    "tree_method": "hist",
}


@dataclass(frozen=True)
class TemporalBounds:
    train_end: pd.Timestamp
    validation_end: pd.Timestamp


def temporal_bounds(df: pd.DataFrame) -> TemporalBounds:
    """Return July/October boundaries for the latest year in the dataset."""
    year = int(df["data_abertura"].dt.year.max())
    return TemporalBounds(
        train_end=pd.Timestamp(year=year, month=7, day=1),
        validation_end=pd.Timestamp(year=year, month=10, day=1),
    )


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, Path):
        return str(value)
    return value


def _concrete_xgb_params(spec: dict[str, Any], y: np.ndarray) -> dict[str, Any]:
    params = {**COMMON_XGB_PARAMS, **spec["params"]}
    if spec.get("balance") == "weighted":
        negatives, positives = np.bincount(np.asarray(y, dtype=int), minlength=2)
        params["scale_pos_weight"] = float(negatives / max(1, positives))
    else:
        params.pop("scale_pos_weight", None)
    return params


def fit_spec(
    X: np.ndarray, y: np.ndarray, spec: dict[str, Any],
) -> xgb.XGBClassifier | Pipeline:
    """Fit an XGBoost or regularized logistic candidate."""
    if len(np.unique(y)) < 2:
        raise ValueError("O período de treino precisa conter as duas classes.")
    if spec["kind"] == "logistic":
        model = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(
                C=float(spec["params"]["C"]),
                class_weight=spec["params"].get("class_weight"),
                max_iter=5000,
                solver="liblinear",
                random_state=RANDOM_STATE,
            )),
        ])
        model.fit(X, y)
        return model
    model = xgb.XGBClassifier(**_concrete_xgb_params(spec, y))
    model.fit(X, y, verbose=False)
    return model


def _predict(model: xgb.XGBClassifier | Pipeline, X: np.ndarray) -> np.ndarray:
    return np.asarray(model.predict_proba(X)[:, 1], dtype=float)


def _recent_months_before(df: pd.DataFrame, end: pd.Timestamp, n_splits: int) -> list[pd.Period]:
    months = sorted(df.loc[df["data_abertura"] < end, "data_abertura"].dt.to_period("M").unique())
    if len(months) < n_splits + 2:
        raise ValueError(f"São necessários ao menos {n_splits + 2} meses antes de {end.date()}.")
    return months[-n_splits:]


def rolling_cv(
    raw_df: pd.DataFrame,
    spec: dict[str, Any],
    features: list[str],
    end: pd.Timestamp,
    *,
    n_splits: int = 4,
    evaluation_priority: int | None = None,
) -> dict[str, Any]:
    """Run recent expanding monthly folds and return OOF ranking metrics.

    When ``evaluation_priority`` is set the model is still trained on all rows,
    but the validation metric is calculated only for that priority.  This is
    the fair segment baseline for a specialist trained solely on that segment.
    """
    region = raw_df.loc[raw_df["data_abertura"] < end].copy().reset_index(drop=True)
    validation_months = _recent_months_before(region, end, n_splits)
    fold_rows: list[dict[str, Any]] = []
    all_y: list[np.ndarray] = []
    all_probabilities: list[np.ndarray] = []

    for fold_number, validation_month in enumerate(validation_months, start=1):
        validation_start = validation_month.start_time
        validation_end = (validation_month + 1).start_time
        train_end = int(np.searchsorted(
            region["data_abertura"].to_numpy(), np.datetime64(validation_start), side="left",
        ))
        validation_end_idx = int(np.searchsorted(
            region["data_abertura"].to_numpy(), np.datetime64(validation_end), side="left",
        ))
        if train_end <= 0 or validation_end_idx <= train_end:
            continue
        prepared = _apply_training_statistics(region, train_end)
        train_frame = prepared.iloc[:train_end]
        validation_frame = prepared.iloc[train_end:validation_end_idx]
        if evaluation_priority is not None:
            validation_frame = validation_frame[
                validation_frame["prioridade_bin"] == evaluation_priority
            ]
        y_train = train_frame[TARGET].to_numpy(dtype=int)
        y_validation = validation_frame[TARGET].to_numpy(dtype=int)
        if len(np.unique(y_train)) < 2 or len(np.unique(y_validation)) < 2:
            continue
        model = fit_spec(train_frame[features].to_numpy(), y_train, spec)
        probabilities = _predict(model, validation_frame[features].to_numpy())
        pr_auc = float(average_precision_score(y_validation, probabilities))
        roc_auc = float(roc_auc_score(y_validation, probabilities))
        fold_rows.append({
            "fold": fold_number,
            "mes_validacao": str(validation_month),
            "incidentes": int(len(validation_frame)),
            "violacoes": int(y_validation.sum()),
            "prevalencia": float(y_validation.mean()),
            "pr_auc": pr_auc,
            "roc_auc": roc_auc,
        })
        all_y.append(y_validation)
        all_probabilities.append(probabilities)

    if not fold_rows:
        raise ValueError("Nenhum fold temporal válido foi produzido.")
    y_oof = np.concatenate(all_y)
    p_oof = np.concatenate(all_probabilities)
    pr_values = np.asarray([row["pr_auc"] for row in fold_rows])
    roc_values = np.asarray([row["roc_auc"] for row in fold_rows])
    pr_mean = float(pr_values.mean())
    pr_std = float(pr_values.std())
    return {
        "folds": fold_rows,
        "incidentes_oof": int(len(y_oof)),
        "violacoes_oof": int(y_oof.sum()),
        "pr_auc_oof": float(average_precision_score(y_oof, p_oof)),
        "roc_auc_oof": float(roc_auc_score(y_oof, p_oof)),
        "pr_auc_media_folds": pr_mean,
        "pr_auc_std_folds": pr_std,
        "roc_auc_media_folds": float(roc_values.mean()),
        "score_robusto": pr_mean - 0.25 * pr_std,
    }


def _suggest_xgb_spec(trial: optuna.Trial, priority: int) -> dict[str, Any]:
    """Constrain P2 more heavily because it has only 22 train positives."""
    p2 = priority == 1
    return {
        "kind": "xgboost",
        "balance": trial.suggest_categorical("balance", ["weighted", "none"]),
        "params": {
            "n_estimators": trial.suggest_int(
                "n_estimators", 80 if p2 else 200, 400 if p2 else 750, step=40 if p2 else 50,
            ),
            "max_depth": trial.suggest_int("max_depth", 1 if p2 else 2, 3 if p2 else 7),
            "learning_rate": trial.suggest_float("learning_rate", 0.008, 0.10, log=True),
            "subsample": trial.suggest_float("subsample", 0.65, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.55, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 3 if p2 else 2, 35),
            "gamma": trial.suggest_float("gamma", 0.0, 4.0),
            "max_delta_step": trial.suggest_int("max_delta_step", 0, 10),
            "reg_alpha": trial.suggest_float("reg_alpha", 0.01, 15.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 25.0, log=True),
        },
    }


def tune_specialist(
    specialist_df: pd.DataFrame,
    priority: int,
    end: pd.Timestamp,
    *,
    n_trials: int,
    n_splits: int = 4,
) -> dict[str, Any]:
    """Tune XGBoost and compare it with regularized logistic candidates."""
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial: optuna.Trial) -> float:
        spec = _suggest_xgb_spec(trial, priority)
        metrics = rolling_cv(
            specialist_df, spec, SPECIALIST_FEATURES, end, n_splits=n_splits,
        )
        trial.set_user_attr("pr_auc_oof", metrics["pr_auc_oof"])
        trial.set_user_attr("pr_auc_mean", metrics["pr_auc_media_folds"])
        trial.set_user_attr("pr_auc_std", metrics["pr_auc_std_folds"])
        return float(metrics["score_robusto"])

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE),
    )
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    best_params = dict(study.best_trial.params)
    best_xgb_spec = {
        "kind": "xgboost",
        "balance": best_params.pop("balance"),
        "params": best_params,
    }

    candidates: list[tuple[str, dict[str, Any]]] = [("xgboost_optuna", best_xgb_spec)]
    for class_weight in ("balanced", None):
        for c_value in (0.01, 0.1, 1.0, 10.0):
            weight_name = "balanced" if class_weight else "unweighted"
            candidates.append((
                f"logistic_{weight_name}_c{c_value:g}",
                {
                    "kind": "logistic",
                    "balance": weight_name,
                    "params": {"C": c_value, "class_weight": class_weight},
                },
            ))

    rows: list[dict[str, Any]] = []
    candidate_metrics: dict[str, dict[str, Any]] = {}
    candidate_specs: dict[str, dict[str, Any]] = {}
    for name, spec in candidates:
        metrics = rolling_cv(
            specialist_df, spec, SPECIALIST_FEATURES, end, n_splits=n_splits,
        )
        candidate_metrics[name] = metrics
        candidate_specs[name] = spec
        rows.append({
            "nome": name,
            "kind": spec["kind"],
            "balance": spec["balance"],
            "pr_auc_oof": metrics["pr_auc_oof"],
            "pr_auc_media_folds": metrics["pr_auc_media_folds"],
            "pr_auc_std_folds": metrics["pr_auc_std_folds"],
            "score_robusto": metrics["score_robusto"],
        })
    rows.sort(key=lambda row: row["score_robusto"], reverse=True)
    winner_name = str(rows[0]["nome"])
    return {
        "winner_name": winner_name,
        "winner_spec": candidate_specs[winner_name],
        "winner_cv": candidate_metrics[winner_name],
        "candidates": rows,
        "optuna": {
            "n_trials": n_trials,
            "best_value": float(study.best_value),
            "best_xgb_spec": best_xgb_spec,
        },
    }


def ranking_metrics(y: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    prevalence = float(y.mean())
    result: dict[str, Any] = {
        "incidentes": int(len(y)),
        "violacoes": int(y.sum()),
        "prevalencia": prevalence,
        "pr_auc": float(average_precision_score(y, probabilities)),
        "roc_auc": float(roc_auc_score(y, probabilities)),
    }
    result["lift_pr_auc"] = result["pr_auc"] / max(prevalence, 1e-12)
    top_k = []
    for share in (0.01, 0.05, 0.10):
        k = min(len(y), max(1, int(round(len(y) * share))))
        indices = np.argsort(-probabilities, kind="stable")[:k]
        hits = int(y[indices].sum())
        top_k.append({
            "share": share,
            "k": k,
            "violacoes_encontradas": hits,
            "precision_at_k": float(hits / k),
            "recall_at_k": float(hits / max(1, y.sum())),
            "lift_at_k": float((hits / k) / max(prevalence, 1e-12)),
        })
    result["top_k"] = top_k
    return result


def best_f1_threshold(y: np.ndarray, probabilities: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(y, probabilities)
    f1_values = 2 * precision[:-1] * recall[:-1] / (precision[:-1] + recall[:-1] + 1e-12)
    return float(thresholds[int(np.argmax(f1_values))])


def threshold_metrics(
    y: np.ndarray, probabilities: np.ndarray, threshold: float,
) -> dict[str, Any]:
    predicted = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    alerts = int(predicted.sum())
    return {
        "threshold": float(threshold),
        "alertas": alerts,
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "incidentes_por_acerto": None if tp == 0 else float(alerts / tp),
    }


def _period(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "inicio": df["data_abertura"].min().isoformat(),
        "fim": df["data_abertura"].max().isoformat(),
        "incidentes": int(len(df)),
        "violacoes": int(df[TARGET].sum()),
        "prevalencia": float(df[TARGET].mean()),
    }


def evaluate_model(
    raw_df: pd.DataFrame,
    spec: dict[str, Any],
    features: list[str],
    bounds: TemporalBounds,
    *,
    evaluation_priority: int | None = None,
) -> dict[str, Any]:
    """Fit through June, select a threshold on Q3, report once on Q4."""
    train_end = int(np.searchsorted(
        raw_df["data_abertura"].to_numpy(), np.datetime64(bounds.train_end), side="left",
    ))
    validation_end = int(np.searchsorted(
        raw_df["data_abertura"].to_numpy(), np.datetime64(bounds.validation_end), side="left",
    ))
    prepared = _apply_training_statistics(raw_df, train_end)
    train_frame = prepared.iloc[:train_end]
    validation_frame = prepared.iloc[train_end:validation_end]
    test_frame = prepared.iloc[validation_end:]
    if evaluation_priority is not None:
        validation_frame = validation_frame[
            validation_frame["prioridade_bin"] == evaluation_priority
        ]
        test_frame = test_frame[test_frame["prioridade_bin"] == evaluation_priority]
    y_train = train_frame[TARGET].to_numpy(dtype=int)
    model = fit_spec(train_frame[features].to_numpy(), y_train, spec)
    y_validation = validation_frame[TARGET].to_numpy(dtype=int)
    p_validation = _predict(model, validation_frame[features].to_numpy())
    threshold = best_f1_threshold(y_validation, p_validation)
    y_test = test_frame[TARGET].to_numpy(dtype=int)
    p_test = _predict(model, test_frame[features].to_numpy())
    return {
        "model": model,
        "threshold_selected_q3": threshold,
        "train": _period(train_frame),
        "validation_q3": {
            "ranking": ranking_metrics(y_validation, p_validation),
            "threshold": threshold_metrics(y_validation, p_validation, threshold),
        },
        "test_q4": {
            "ranking": ranking_metrics(y_test, p_test),
            "threshold": threshold_metrics(y_test, p_test, threshold),
        },
    }


def _save_model(model: xgb.XGBClassifier | Pipeline, name: str) -> Path:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if isinstance(model, xgb.XGBClassifier):
        path = MODEL_DIR / f"{name}.json"
        # Persist the native booster. XGBoost 2.1's sklearn wrapper cannot be
        # serialized with sklearn 1.8 because of the newer estimator tags.
        # The booster JSON is portable and avoids pickle execution entirely.
        model.get_booster().save_model(path)
        stale_path = MODEL_DIR / f"{name}.joblib"
    else:
        path = MODEL_DIR / f"{name}.joblib"
        joblib.dump(model, path)
        stale_path = MODEL_DIR / f"{name}.json"
    # A different algorithm may win a later reproducible run. Remove only the
    # alternate artifact for this exact candidate name to avoid stale routing.
    if stale_path.exists():
        stale_path.unlink()
    return path


def _without_model(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "model"}


def train_all(*, n_trials: int = 30, n_splits: int = 4) -> dict[str, Any]:
    """Train and compare all three models without modifying production output."""
    started = time.perf_counter()
    df = load_data().sort_values("data_abertura", kind="stable").reset_index(drop=True)
    bounds = temporal_bounds(df)
    general_eval = evaluate_model(df, GENERALIST_SPEC, FEATURES, bounds)
    general_model_path = _save_model(general_eval["model"], "generalist_evaluation_through_june")

    report: dict[str, Any] = {
        "relatorio": "xgboost_champion_challenger_por_prioridade",
        "gerado_em": date.today().isoformat(),
        "versao": "experimental_v1",
        "protocolo": "rolling_cv_mar_jun_threshold_q3_teste_q4",
        "producao_alterada": False,
        "artefato_producao_preservado": "outputs/risco_ola.json",
        "configuracao": {
            "n_trials_por_especialista": n_trials,
            "n_splits": n_splits,
            "random_state": RANDOM_STATE,
        },
        "generalista": {
            "spec": GENERALIST_SPEC,
            "avaliacao_global": _without_model(general_eval),
            "artefato_avaliacao": str(general_model_path.relative_to(PROJECT_ROOT)),
        },
        "especialistas": {},
    }

    for priority_value, priority_label in ((1, "P2"), (0, "P3")):
        print(f"\n[{priority_label}] tuning de {n_trials} trials + regressões logísticas...")
        specialist_df = df[df["prioridade_bin"] == priority_value].copy().reset_index(drop=True)
        tuning = tune_specialist(
            specialist_df,
            priority_value,
            bounds.train_end,
            n_trials=n_trials,
            n_splits=n_splits,
        )
        specialist_eval = evaluate_model(
            specialist_df, tuning["winner_spec"], SPECIALIST_FEATURES, bounds,
        )
        general_segment_eval = evaluate_model(
            df, GENERALIST_SPEC, FEATURES, bounds, evaluation_priority=priority_value,
        )
        general_segment_cv = rolling_cv(
            df,
            GENERALIST_SPEC,
            FEATURES,
            bounds.train_end,
            n_splits=n_splits,
            evaluation_priority=priority_value,
        )
        train_positives = int(
            specialist_df.loc[
                specialist_df["data_abertura"] < bounds.train_end, TARGET
            ].sum()
        )
        decision = promotion_decision(
            priority_label,
            train_positives,
            tuning["winner_cv"],
            general_segment_cv,
            specialist_eval,
            general_segment_eval,
        )
        artifact_path = _save_model(
            specialist_eval["model"], f"{priority_label.lower()}_evaluation_through_june",
        )
        report["especialistas"][priority_label] = {
            "amostra": {
                "total_incidentes": int(len(specialist_df)),
                "total_violacoes": int(specialist_df[TARGET].sum()),
                "violacoes_treino": train_positives,
            },
            "tuning": tuning,
            "avaliacao_especialista": _without_model(specialist_eval),
            "baseline_generalista_no_segmento": {
                "cv": general_segment_cv,
                "avaliacao": _without_model(general_segment_eval),
            },
            "decisao": decision,
            "artefato_avaliacao": str(artifact_path.relative_to(PROJECT_ROOT)),
        }
        print(
            f"[{priority_label}] vencedor={tuning['winner_name']} | "
            f"PR-AUC Q4 especialista={specialist_eval['test_q4']['ranking']['pr_auc']:.4f} "
            f"vs geral={general_segment_eval['test_q4']['ranking']['pr_auc']:.4f} | "
            f"decisão={decision['status']}"
        )

    report["roteador_recomendado"] = {}
    for priority, data in report["especialistas"].items():
        status = data["decisao"]["status"]
        promoted = status == "promover_especialista"
        if priority == "P2" and not promoted:
            report["roteador_recomendado"][priority] = {
                "modelo_ativo": "nenhum_modelo_preditivo_promovido",
                "modo_operacional": "regra_ola_e_triagem_humana",
                "modelo_shadow": "especialista_p2",
                "status_especialista": status,
                "fallback_analitico": "generalista_apenas_como_ranking_experimental",
            }
        else:
            report["roteador_recomendado"][priority] = {
                "modelo_ativo": f"especialista_{priority.lower()}" if promoted else "generalista",
                "modo_operacional": "triagem_humana_por_score",
                "status_especialista": status,
                "fallback": "generalista",
            }
    report["duracao_segundos"] = float(time.perf_counter() - started)
    return _json_safe(report)


def export_report(report: dict[str, Any], path: Path = REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as report_file:
        json.dump(report, report_file, ensure_ascii=False, indent=2, allow_nan=False)
    print(f"\nRelatório experimental: {path}")
    print("Produção preservada: outputs/risco_ola.json não foi alterado.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=30)
    parser.add_argument("--splits", type=int, default=4)
    args = parser.parse_args()
    if args.trials < 1:
        parser.error("--trials deve ser positivo")
    report = train_all(n_trials=args.trials, n_splits=args.splits)
    export_report(report)


if __name__ == "__main__":
    main()
