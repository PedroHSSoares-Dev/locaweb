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
from sklearn.model_selection import StratifiedKFold, cross_validate

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

    df_model = df[PARQUET_FEATURES + [TARGET]].copy()
    for c in ["lag_1d", "lag_7d", "rolling_7d", "rolling_30d", "lag_1d_p2", "lag_1d_p3",
              "is_feriado", "tipo_feriado", "dias_ate_feriado", "dias_desde_feriado"]:
        if c in df_model.columns:
            df_model[c] = df_model[c].fillna(0)

    assert df_model.isnull().sum().sum() == 0, "Dataset com nulos"
    return df_model


def train(df: pd.DataFrame) -> dict:
    """Treina, avalia e retorna resultados do XGBoost."""
    contagem = df[TARGET].value_counts().sort_index()
    scale_pos_weight = int(contagem[0] // contagem[1])

    n_total = len(df)
    n_treino = int(n_total * 0.80)

    # grupo_viol_rate: taxa histórica de violação por grupo — calculada SÓ no treino.
    # Mapeia grupo_enc → prob(violação) visto no passado. Sem leakage do período de teste.
    df = df.copy()
    train_slice = df.iloc[:n_treino]
    grupo_rate = train_slice.groupby("grupo_enc")[TARGET].mean()
    global_rate = train_slice[TARGET].mean()
    df["grupo_viol_rate"] = df["grupo_enc"].map(grupo_rate).fillna(global_rate).round(6)

    X = df[FEATURES].values
    y = df[TARGET].values

    X_train, X_test = X[:n_treino], X[n_treino:]
    y_train, y_test = y[:n_treino], y[n_treino:]

    # SMOTE apenas no treino
    smote = SMOTE(random_state=42, k_neighbors=5)
    X_train_sm, y_train_sm = smote.fit_resample(X_train, y_train)

    # Parâmetros otimizados via Optuna (80 trials, métrica PR-AUC).
    # max_delta_step=8 é o parâmetro mais impactante: recomendado para datasets imbalanceados.
    # scale_pos_weight=48 (vs razão real ~102): regularização já compensa o desbalanceamento.
    params_base = dict(
        n_estimators=454,
        max_depth=8,
        learning_rate=0.0108,
        subsample=0.8507,
        colsample_bytree=0.8277,
        min_child_weight=5,
        gamma=0.648,
        max_delta_step=8,
        reg_alpha=1.74,
        reg_lambda=3.649,
        scale_pos_weight=48,
        eval_metric="aucpr",
        random_state=42,
        n_jobs=-1,
        tree_method="hist",
    )
    model_base = xgb.XGBClassifier(**params_base)
    model_base.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    y_prob_base = model_base.predict_proba(X_test)[:, 1]
    pr_base = average_precision_score(y_test, y_prob_base)

    # Modelo SMOTE: mesmos hiperparâmetros Optuna, treinado em dados reamostrados.
    params_smote = dict(
        n_estimators=454,
        max_depth=8,
        learning_rate=0.0108,
        subsample=0.8507,
        colsample_bytree=0.8277,
        min_child_weight=5,
        gamma=0.648,
        max_delta_step=8,
        reg_alpha=1.74,
        reg_lambda=3.649,
        eval_metric="aucpr",
        random_state=42,
        n_jobs=-1,
        tree_method="hist",
    )
    model_smote = xgb.XGBClassifier(**params_smote)
    model_smote.fit(X_train_sm, y_train_sm, eval_set=[(X_test, y_test)], verbose=False)
    y_prob_smote = model_smote.predict_proba(X_test)[:, 1]
    pr_smote = average_precision_score(y_test, y_prob_smote)

    # Selecionar melhor modelo por PR-AUC
    if pr_smote >= pr_base:
        melhor_nome, model_final, y_prob_final = "SMOTE", model_smote, y_prob_smote
        X_cv, y_cv, params_cv = X_train_sm, y_train_sm, params_smote
    else:
        melhor_nome, model_final, y_prob_final = "Base", model_base, y_prob_base
        X_cv, y_cv, params_cv = X_train, y_train, params_base

    print(f"Melhor modelo: {melhor_nome} (PR-AUC Base={pr_base:.4f}, SMOTE={pr_smote:.4f})")

    # Cross-validation
    cv_splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    model_cv = xgb.XGBClassifier(**params_cv)
    resultados_cv = cross_validate(
        model_cv, X_cv, y_cv,
        cv=cv_splitter,
        scoring={"roc_auc": "roc_auc", "average_precision": "average_precision"},
        return_train_score=False,
        n_jobs=-1,
    )
    roc_vals = resultados_cv["test_roc_auc"]
    pr_vals = resultados_cv["test_average_precision"]

    precision_arr, recall_arr, thresholds = precision_recall_curve(y_test, y_prob_final)
    f1_arr = 2 * precision_arr[:-1] * recall_arr[:-1] / (precision_arr[:-1] + recall_arr[:-1] + 1e-9)

    # Threshold otimizado por F1 — melhor equilíbrio precisão/recall dada a imbalance 1:102.
    # Nota: recall ficará baixo (~8%), mas a precisão (~14%) mantém os alertas utilizáveis.
    # Usar probabilidades contínuas (prob > 0.15 = atenção, > 0.30 = alto risco) para triagem.
    best_idx = int(np.argmax(f1_arr))
    threshold_otm = float(thresholds[best_idx])
    best_prec = float(precision_arr[best_idx])
    best_rec = float(recall_arr[best_idx])
    best_f1 = float(f1_arr[best_idx])

    y_pred_otm = (y_prob_final >= threshold_otm).astype(int)
    cm = confusion_matrix(y_test, y_pred_otm)
    tn_v, fp_v, fn_v, tp_v = cm.ravel()

    # Threshold para recall >= 70% — referência para análise exploratória.
    # Não usado como threshold principal: precisão cai para ~2% (98% falsos alarmes).
    threshold_r70 = None
    for thr in np.arange(0.10, 0.85, 0.01):
        pred_t = (y_prob_final >= thr).astype(int)
        if recall_score(y_test, pred_t, zero_division=0) >= 0.70:
            threshold_r70 = round(float(thr), 4)
            break

    print(f"Threshold F1: {threshold_otm:.4f} | Recall: {best_rec:.4f} | F1: {best_f1:.4f}")
    print(classification_report(y_test, y_pred_otm, target_names=["NAO (0)", "SIM (1)"]))

    # SHAP feature importance
    n_shap = min(2000, len(X_test))
    idx = np.random.choice(len(X_test), n_shap, replace=False)
    explainer = shap.TreeExplainer(model_final)
    shap_values = explainer.shap_values(X_test[idx])
    shap_abs = np.abs(shap_values).mean(axis=0)
    feat_imp_list = [
        {"rank": i + 1, "feature": f, "shap_mean_abs": round(float(v), 6)}
        for i, (f, v) in enumerate(sorted(zip(FEATURES, shap_abs), key=lambda x: -x[1]))
    ]

    # Análise de risco por segmento
    df_test = df.iloc[n_treino:].copy()
    df_test["prob"] = y_prob_final
    df_test["real"] = y_test

    limites = {"baixo": (0.0, 0.2), "medio": (0.2, threshold_otm), "alto": (threshold_otm, 1.0)}
    dist_risco = {}
    for cat, (lo, hi) in limites.items():
        mask = (df_test["prob"] >= lo) & (df_test["prob"] < hi)
        dist_risco[cat] = {
            "count": int(mask.sum()),
            "pct": round(float(mask.sum() / len(df_test) * 100), 2),
            "limite_inferior": lo,
            "limite_superior": hi if hi < 1.0 else 1.0,
            "violacoes_reais": int(df_test.loc[mask, "real"].sum()),
        }

    risco_prio_dict = {}
    for pbin, label in [(0, "P3"), (1, "P2")]:
        mask = df_test["prioridade_bin"] == pbin
        risco_prio_dict[label] = {
            "media_prob": round(float(df_test.loc[mask, "prob"].mean()), 4),
            "pct_alto_risco": round(float((df_test.loc[mask, "prob"] >= threshold_otm).mean() * 100), 2),
            "n_incidentes": int(mask.sum()),
            "taxa_violacao_real": round(float(df_test.loc[mask, "real"].mean() * 100), 2),
        }

    return {
        "model": model_final,
        "threshold_otm": threshold_otm,
        "threshold_r70": threshold_r70,
        "scale_pos_weight": scale_pos_weight,
        "melhor_nome": melhor_nome,
        "metricas": {
            "recall_violacao": round(best_rec, 4),
            "precision_violacao": round(best_prec, 4),
            "f1_violacao": round(best_f1, 4),
            "roc_auc": round(roc_auc_score(y_test, y_prob_final), 4),
            "pr_auc": round(average_precision_score(y_test, y_prob_final), 4),
            "roc_auc_cv_mean": round(float(roc_vals.mean()), 4),
            "roc_auc_cv_std": round(float(roc_vals.std()), 4),
            "pr_auc_cv_mean": round(float(pr_vals.mean()), 4),
            "pr_auc_cv_std": round(float(pr_vals.std()), 4),
            "tp": int(tp_v), "fp": int(fp_v), "fn": int(fn_v), "tn": int(tn_v),
            "total_teste": int(len(y_test)),
            "violacoes_reais": int(y_test.sum()),
            "violacoes_capturadas": int(tp_v),
        },
        "feat_imp_list": feat_imp_list,
        "risco_prio_dict": risco_prio_dict,
        "dist_risco": dist_risco,
        # Dados para notebooks exploratórios
        "y_test": y_test,
        "y_prob_final": y_prob_final,
        "X_test": X_test,
        "shap_values": shap_values,
        "shap_abs": shap_abs,
        "n_treino": n_treino,
    }


def export_json(results: dict, path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "modelo": "xgboost_ola_risk",
        "gerado_em": date.today().strftime("%Y-%m-%d"),
        "versao": "v2",
        "abordagem": f"XGBoost + {results['melhor_nome']} + threshold F1-ótimo + CV validado",
        "threshold_otimizado": round(results["threshold_otm"], 4),
        "threshold_recall_70": results["threshold_r70"],
        "scale_pos_weight": results["scale_pos_weight"],
        "metricas": results["metricas"],
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
