"""
XGBoost — classificação de risco de violação de OLA.

Treina dois modelos (Base com scale_pos_weight e SMOTE), seleciona o melhor
por PR-AUC, otimiza threshold por F1, calcula SHAP e exporta outputs/risco_ola.json.

Regras anti-leakage (CLAUDE.md):
  - Nunca usar: Duração, Resolvido, Encerrado, Código de fechamento, Solução
  - SMOTE somente no treino, jamais no teste
  - Métricas: Recall, F1, ROC-AUC, PR-AUC (nunca acurácia)
"""
from __future__ import annotations

import json
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from imblearn.over_sampling import SMOTE
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).parents[2]
PARQUET_PATH = PROJECT_ROOT / "data" / "processed" / "incidents_features.parquet"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "risco_ola.json"

# Features carregadas do parquet
PARQUET_FEATURES = [
    "hora", "dia_semana", "mes", "trimestre", "dia_mes", "semana_ano",
    "is_horario_comercial", "is_fim_de_semana", "is_segunda_terca", "periodo_dia",
    "lag_1d", "lag_7d", "rolling_7d", "rolling_30d",
    "lag_1d_p2", "lag_1d_p3",
    "prioridade_bin",
    "produto_enc", "categoria_enc", "subcategoria_enc", "grupo_enc", "aberto_por_enc",
    "produto_freq", "grupo_freq",
    "mes_sin", "mes_cos",
    # Feriados
    "is_feriado", "tipo_feriado", "dias_ate_feriado", "dias_desde_feriado",
]

# Features do modelo (inclui derivadas calculadas dentro do split de treino)
FEATURES = PARQUET_FEATURES + ["grupo_viol_rate"]

TARGET = "target_ola"


def load_data(path: Path = PARQUET_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} não encontrado.\n"
            "Execute: python src/data/preprocessor.py"
        )
    df = pd.read_parquet(path)

    missing = [f for f in PARQUET_FEATURES if f not in df.columns]
    if missing:
        raise ValueError(
            f"Features faltando no parquet: {missing}\n"
            "Execute: python src/data/preprocessor.py"
        )

    if "data_abertura" not in df.columns:
        raise ValueError("Parquet sem data_abertura — execute novamente o feature engineering.")
    df_model = df[["data_abertura", *PARQUET_FEATURES, TARGET]].copy()
    df_model["data_abertura"] = pd.to_datetime(df_model["data_abertura"])
    df_model = df_model.sort_values("data_abertura", kind="stable").reset_index(drop=True)
    for c in ["lag_1d", "lag_7d", "rolling_7d", "rolling_30d", "lag_1d_p2", "lag_1d_p3",
              "is_feriado", "tipo_feriado", "dias_ate_feriado", "dias_desde_feriado"]:
        if c in df_model.columns:
            df_model[c] = df_model[c].fillna(0)

    assert df_model.isnull().sum().sum() == 0, "Dataset com nulos"
    return df_model


def _apply_training_statistics(df: pd.DataFrame, cutoff: int) -> pd.DataFrame:
    """Derive frequency/target encodings using only rows before ``cutoff``."""
    transformed = df.copy()
    reference = transformed.iloc[:cutoff]
    for source, target in (("produto_enc", "produto_freq"), ("grupo_enc", "grupo_freq")):
        frequencies = reference[source].value_counts(normalize=True)
        transformed[target] = transformed[source].map(frequencies).fillna(0.0).astype(float)
    group_rate = reference.groupby("grupo_enc")[TARGET].mean()
    global_rate = float(reference[TARGET].mean())
    transformed["grupo_viol_rate"] = transformed["grupo_enc"].map(group_rate).fillna(global_rate)
    return transformed


def _fit_candidate(X: np.ndarray, y: np.ndarray, params: dict, use_smote: bool):
    if use_smote:
        positives = int(y.sum())
        neighbors = max(1, min(5, positives - 1))
        X, y = SMOTE(random_state=42, k_neighbors=neighbors).fit_resample(X, y)
    model = xgb.XGBClassifier(**params)
    model.fit(X, y, verbose=False)
    return model


def _thresholds_from_validation(y_true: np.ndarray, probabilities: np.ndarray, recall_target: float):
    precision_arr, recall_arr, thresholds = precision_recall_curve(y_true, probabilities)
    f1_arr = 2 * precision_arr[:-1] * recall_arr[:-1] / (precision_arr[:-1] + recall_arr[:-1] + 1e-9)
    f1_idx = int(np.argmax(f1_arr))
    valid_recall = np.where(recall_arr[:-1] >= recall_target)[0]
    recall_idx = int(valid_recall[-1]) if len(valid_recall) else int(np.argmax(recall_arr[:-1]))
    return float(thresholds[recall_idx]), float(thresholds[f1_idx])


def _temporal_cv(df: pd.DataFrame, end: int, params: dict, use_smote: bool) -> tuple[np.ndarray, np.ndarray]:
    """Expanding-window CV; every fold derives encodings and SMOTE from its own past."""
    roc_values: list[float] = []
    pr_values: list[float] = []
    region = df.iloc[:end].reset_index(drop=True)
    normalized_dates = region["data_abertura"].dt.normalize()
    unique_dates = np.asarray(sorted(normalized_dates.unique()))
    for train_days, validation_days in TimeSeriesSplit(n_splits=5).split(unique_dates):
        train_date_set = set(unique_dates[train_days])
        validation_date_set = set(unique_dates[validation_days])
        train_idx = np.flatnonzero(normalized_dates.isin(train_date_set).to_numpy())
        validation_idx = np.flatnonzero(normalized_dates.isin(validation_date_set).to_numpy())
        cutoff = int(train_idx[-1]) + 1
        prepared = _apply_training_statistics(region, cutoff)
        y_train = prepared.iloc[train_idx][TARGET].to_numpy()
        y_validation = prepared.iloc[validation_idx][TARGET].to_numpy()
        if len(np.unique(y_train)) < 2 or len(np.unique(y_validation)) < 2:
            continue
        model = _fit_candidate(
            prepared.iloc[train_idx][FEATURES].to_numpy(), y_train, params, use_smote,
        )
        probabilities = model.predict_proba(prepared.iloc[validation_idx][FEATURES].to_numpy())[:, 1]
        roc_values.append(float(roc_auc_score(y_validation, probabilities)))
        pr_values.append(float(average_precision_score(y_validation, probabilities)))
    if not roc_values:
        raise ValueError("Validação temporal sem folds contendo ambas as classes.")
    return np.asarray(roc_values), np.asarray(pr_values)


def train(df: pd.DataFrame, recall_target: float = 0.70) -> dict:
    """Select on validation and report once on a later, untouched temporal test."""
    if not df["data_abertura"].is_monotonic_increasing:
        raise ValueError("Dataset deve estar em ordem temporal crescente.")

    n_total = len(df)
    normalized_dates = df["data_abertura"].dt.normalize()
    reference_year = int(normalized_dates.max().year)
    validation_start_date = np.datetime64(f"{reference_year}-07-01")
    test_start_date = np.datetime64(f"{reference_year}-10-01")
    n_train = int(np.searchsorted(normalized_dates.to_numpy(), validation_start_date, side="left"))
    n_validation_end = int(np.searchsorted(normalized_dates.to_numpy(), test_start_date, side="left"))
    prepared = _apply_training_statistics(df, n_train)
    y = prepared[TARGET].to_numpy()
    X = prepared[FEATURES].to_numpy()
    X_train, y_train = X[:n_train], y[:n_train]
    X_validation, y_validation = X[n_train:n_validation_end], y[n_train:n_validation_end]
    X_test, y_test = X[n_validation_end:], y[n_validation_end:]

    negatives, positives = np.bincount(y_train.astype(int), minlength=2)
    scale_pos_weight = max(1, int(round(negatives / max(1, positives))))
    common_params = dict(
        n_estimators=454, max_depth=8, learning_rate=0.0108,
        subsample=0.8507, colsample_bytree=0.8277, min_child_weight=5,
        gamma=0.648, max_delta_step=8, reg_alpha=1.74, reg_lambda=3.649,
        eval_metric="aucpr", random_state=42, n_jobs=-1, tree_method="hist",
    )
    params_base = {**common_params, "scale_pos_weight": scale_pos_weight}
    params_smote = dict(common_params)

    candidates = {}
    for name, params, use_smote in (
        ("Base", params_base, False),
        ("SMOTE", params_smote, True),
    ):
        model = _fit_candidate(X_train, y_train, params, use_smote)
        validation_probabilities = model.predict_proba(X_validation)[:, 1]
        candidates[name] = {
            "model": model,
            "params": params,
            "use_smote": use_smote,
            "probabilities": validation_probabilities,
            "pr_auc": float(average_precision_score(y_validation, validation_probabilities)),
        }

    winner_name = max(candidates, key=lambda name: candidates[name]["pr_auc"])
    winner = candidates[winner_name]
    threshold_recall, threshold_f1 = _thresholds_from_validation(
        y_validation, winner["probabilities"], recall_target,
    )
    model_final = winner["model"]
    y_prob_test = model_final.predict_proba(X_test)[:, 1]
    y_pred_recall = (y_prob_test >= threshold_recall).astype(int)
    y_pred_f1 = (y_prob_test >= threshold_f1).astype(int)

    tn_v, fp_v, fn_v, tp_v = confusion_matrix(y_test, y_pred_recall, labels=[0, 1]).ravel()
    tn_f1, fp_f1, fn_f1, tp_f1 = confusion_matrix(y_test, y_pred_f1, labels=[0, 1]).ravel()
    test_precision = float(precision_score(y_test, y_pred_recall, zero_division=0))
    test_recall = float(recall_score(y_test, y_pred_recall, zero_division=0))
    test_f1 = float(f1_score(y_test, y_pred_recall, zero_division=0))
    f1_precision = float(precision_score(y_test, y_pred_f1, zero_division=0))
    f1_recall = float(recall_score(y_test, y_pred_f1, zero_division=0))
    f1_value = float(f1_score(y_test, y_pred_f1, zero_division=0))

    roc_values, pr_values = _temporal_cv(
        df, n_validation_end, winner["params"], winner["use_smote"],
    )
    print(
        f"Seleção temporal: {winner_name} | PR-AUC validação "
        f"Base={candidates['Base']['pr_auc']:.4f} SMOTE={candidates['SMOTE']['pr_auc']:.4f}"
    )
    print(
        f"Teste intocado: PR-AUC={average_precision_score(y_test, y_prob_test):.4f} "
        f"Recall={test_recall:.4f} Precision={test_precision:.4f}"
    )
    print(classification_report(y_test, y_pred_recall, target_names=["NAO (0)", "SIM (1)"], zero_division=0))

    rng = np.random.default_rng(42)
    n_shap = min(2000, len(X_test))
    shap_idx = rng.choice(len(X_test), n_shap, replace=False)
    explainer = shap.TreeExplainer(model_final)
    shap_values = explainer.shap_values(X_test[shap_idx])
    shap_abs = np.abs(shap_values).mean(axis=0)
    feature_importance = [
        {"rank": index + 1, "feature": feature, "shap_mean_abs": round(float(value), 6)}
        for index, (feature, value) in enumerate(
            sorted(zip(FEATURES, shap_abs), key=lambda item: -item[1])
        )
    ]

    df_test = prepared.iloc[n_validation_end:].copy()
    df_test["prob"] = y_prob_test
    df_test["real"] = y_test
    low_limit, high_limit = sorted((threshold_recall, threshold_f1))
    limits = {
        "baixo": (0.0, low_limit),
        "medio": (low_limit, high_limit),
        "alto": (high_limit, 1.0),
    }
    risk_distribution = {}
    for category, (lower, upper) in limits.items():
        mask = (df_test["prob"] >= lower) & (
            df_test["prob"] <= upper if upper == 1.0 else df_test["prob"] < upper
        )
        risk_distribution[category] = {
            "count": int(mask.sum()),
            "pct": round(float(mask.mean() * 100), 2),
            "limite_inferior": round(float(lower), 6),
            "limite_superior": round(float(upper), 6),
            "violacoes_reais": int(df_test.loc[mask, "real"].sum()),
        }

    risk_by_priority = {}
    for binary_value, label in ((0, "P3"), (1, "P2")):
        mask = df_test["prioridade_bin"] == binary_value
        risk_by_priority[label] = {
            "media_prob": round(float(df_test.loc[mask, "prob"].mean()), 4),
            "pct_alto_risco": round(float((df_test.loc[mask, "prob"] >= high_limit).mean() * 100), 2),
            "n_incidentes": int(mask.sum()),
            "taxa_violacao_real": round(float(df_test.loc[mask, "real"].mean() * 100), 2),
        }

    def _period(start: int, end: int) -> dict:
        subset = df.iloc[start:end]
        return {
            "inicio": subset["data_abertura"].min().isoformat(),
            "fim": subset["data_abertura"].max().isoformat(),
            "incidentes": int(len(subset)),
            "violacoes": int(subset[TARGET].sum()),
        }

    return {
        "model": model_final,
        "threshold_otm": threshold_recall,
        "threshold_f1": threshold_f1,
        "recall_target": recall_target,
        "scale_pos_weight": scale_pos_weight,
        "melhor_nome": winner_name,
        "split_temporal": {
            "treino": _period(0, n_train),
            "validacao": _period(n_train, n_validation_end),
            "teste": _period(n_validation_end, n_total),
        },
        "selecao_validacao": {
            "pr_auc_base": round(candidates["Base"]["pr_auc"], 4),
            "pr_auc_smote": round(candidates["SMOTE"]["pr_auc"], 4),
        },
        "metricas": {
            "recall_violacao": round(test_recall, 4),
            "precision_violacao": round(test_precision, 4),
            "f1_violacao": round(test_f1, 4),
            "roc_auc": round(float(roc_auc_score(y_test, y_prob_test)), 4),
            "pr_auc": round(float(average_precision_score(y_test, y_prob_test)), 4),
            "roc_auc_cv_mean": round(float(roc_values.mean()), 4),
            "roc_auc_cv_std": round(float(roc_values.std()), 4),
            "pr_auc_cv_mean": round(float(pr_values.mean()), 4),
            "pr_auc_cv_std": round(float(pr_values.std()), 4),
            "cv_folds_temporais": int(len(roc_values)),
            "tp": int(tp_v), "fp": int(fp_v), "fn": int(fn_v), "tn": int(tn_v),
            "total_teste": int(len(y_test)),
            "violacoes_reais": int(y_test.sum()),
            "violacoes_capturadas": int(tp_v),
        },
        "metricas_f1_ref": {
            "threshold": round(threshold_f1, 4),
            "recall_violacao": round(f1_recall, 4),
            "precision_violacao": round(f1_precision, 4),
            "f1_violacao": round(f1_value, 4),
            "tp": int(tp_f1), "fp": int(fp_f1), "fn": int(fn_f1), "tn": int(tn_f1),
            "violacoes_capturadas": int(tp_f1),
        },
        "feat_imp_list": feature_importance,
        "risco_prio_dict": risk_by_priority,
        "dist_risco": risk_distribution,
        "y_test": y_test,
        "y_prob_final": y_prob_test,
        "X_test": X_test,
        "shap_values": shap_values,
        "shap_abs": shap_abs,
        "n_treino": n_train,
    }


def export_json(results: dict, path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "modelo": "xgboost_ola_risk",
        "gerado_em": date.today().strftime("%Y-%m-%d"),
        "versao": "v4",
        "abordagem": (
            f"XGBoost + {results['melhor_nome']} selecionado em validação temporal; "
            f"threshold recall≥{results['recall_target']:.0%}; teste posterior intocado"
        ),
        "protocolo_validacao": "treino_ate_jun_validacao_q3_teste_q4_sem_embaralhamento",
        "split_temporal": results["split_temporal"],
        "selecao_validacao": results["selecao_validacao"],
        "threshold_otimizado": round(results["threshold_otm"], 4),
        "threshold_f1_referencia": round(results["threshold_f1"], 4),
        "recall_target": results["recall_target"],
        "scale_pos_weight": results["scale_pos_weight"],
        "metricas": results["metricas"],
        "metricas_f1_referencia": results["metricas_f1_ref"],
        "feature_importance_shap": results["feat_imp_list"][:15],
        "risco_por_prioridade": results["risco_prio_dict"],
        "distribuicao_risco": results["dist_risco"],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"JSON exportado: {path}")


if __name__ == "__main__":
    print("Carregando features...")
    df = load_data()
    print(f"Dataset: {df.shape} | Violações: {df[TARGET].sum()}")

    print("\nTreinando XGBoost...")
    results = train(df)

    print("\nExportando JSON...")
    export_json(results)
    print("Concluído.")
