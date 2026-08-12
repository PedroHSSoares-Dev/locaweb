"""Point-in-time incident-level OLA risk model laboratory.

This workstream deliberately reuses the audited cohort and feature construction
from ``experiments/raw_opportunity_loop`` without modifying that prior research.
It evaluates materially different model families on the same July--December
2025 monthly walk-forward rows. No incident identifiers, category values, or
raw text/vocabulary are written to disk.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import platform
import resource
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import psutil
import scipy
from scipy import sparse
import sklearn
import xgboost as xgb
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import SGDClassifier
from sklearn.svm import LinearSVC


PROJECT_ROOT = Path(__file__).resolve().parents[4]
WORK_DIR = PROJECT_ROOT / "experiments" / "feature_model_lab" / "workstreams" / "risk"
MODEL_DIR = PROJECT_ROOT / "models_saved" / "experiments" / "feature_model_lab" / "risk"
RAW_LOOP_DIR = PROJECT_ROOT / "experiments" / "raw_opportunity_loop"
if str(RAW_LOOP_DIR) not in sys.path:
    sys.path.insert(0, str(RAW_LOOP_DIR))
import research_loop as raw  # noqa: E402


SEED = 42
STABILITY_SEEDS = [11, 42, 101]
SEGMENTS = {
    "global": None,
    "P2": raw.P2,
    "P3": raw.P3,
}
TOP_SHARE = 0.05


@dataclass(frozen=True)
class ModelSpec:
    name: str
    family: str
    kind: str
    feature_families: tuple[str, ...]
    mechanism: str
    falsification: str
    config: dict[str, Any]


SPECS: list[ModelSpec] = [
    ModelSpec(
        "elastic_structured_full", "regularized_linear", "elastic_structured",
        ("calendar_volume", "sparse_categories", "historical_backoff", "novelty_missingness"),
        "Elastic-net shrinkage can share weak additive evidence across safe calendar, categorical, historical-support, and novelty signals.",
        "Reject if it fails to beat the reconstructed champion robust PR-AUC or loses more than 5% Recall@Top-5%.",
        {"alpha": 2e-5, "l1_ratio": 0.10, "solver": "sgd_log_loss", "max_iter": 1200},
    ),
    ModelSpec(
        "elastic_no_categories", "regularized_linear", "elastic_structured",
        ("calendar_volume", "historical_backoff", "novelty_missingness"),
        "Explicit ablation of opening-time sparse categorical identity from the elastic model.",
        "Falsify categorical value if removal does not reduce robust PR-AUC or operational recall.",
        {"alpha": 2e-5, "l1_ratio": 0.10, "solver": "sgd_log_loss", "max_iter": 1200, "no_categories": True},
    ),
    ModelSpec(
        "elastic_no_history_novelty", "regularized_linear", "elastic_structured",
        ("calendar_volume", "sparse_categories"),
        "Explicit ablation of point-in-time outcome backoff and novelty/support features.",
        "Falsify historical/novelty value if removal does not reduce robust PR-AUC or operational recall.",
        {"alpha": 2e-5, "l1_ratio": 0.10, "solver": "sgd_log_loss", "max_iter": 1200, "no_history_novelty": True},
    ),
    ModelSpec(
        "elastic_no_volume_context", "regularized_linear", "elastic_structured",
        ("calendar", "sparse_categories", "historical_backoff", "novelty_missingness"),
        "Explicit ablation of prior-day and rolling-volume context while preserving deterministic calendar features.",
        "Falsify volume-context value if removal does not reduce robust PR-AUC or operational recall.",
        {"alpha": 2e-5, "l1_ratio": 0.10, "solver": "sgd_log_loss", "max_iter": 1200, "no_volume": True},
    ),
    ModelSpec(
        "linear_svm_structured", "linear_margin", "linear_svm_structured",
        ("calendar_volume", "sparse_categories", "historical_backoff", "novelty_missingness"),
        "A maximum-margin sparse ranker may outperform likelihood optimization under extreme imbalance.",
        "Reject if monthly paired wins or operational recall do not improve.",
        {"C": 0.08, "class_weight": "balanced", "max_iter": 5000},
    ),
    ModelSpec(
        "extra_trees_structured", "bagging_random_trees", "extra_trees",
        ("calendar_volume", "fold_safe_encoded_categories"),
        "Randomized bagged trees may capture discontinuous interactions without boosting's sequential focus on rare positives.",
        "Reject if gains are unstable or Recall@Top-5% degrades by more than 5%.",
        {"n_estimators": 320, "max_depth": 14, "min_samples_leaf": 3, "max_features": 0.75},
    ),
    ModelSpec(
        "hist_gradient_boosting_structured", "gradient_boosting", "hist_gradient_boosting",
        ("calendar_volume", "fold_safe_encoded_categories"),
        "Regularized histogram boosting may generalize differently from the deep locked XGBoost champion.",
        "Reject if it cannot improve paired robust PR-AUC with stable workload.",
        {"learning_rate": 0.055, "max_iter": 220, "max_leaf_nodes": 15, "min_samples_leaf": 30, "l2_regularization": 1.0},
    ),
    ModelSpec(
        "xgboost_safe_reconstruction", "gradient_boosting", "xgboost_safe",
        ("calendar_volume", "fold_safe_encoded_categories"),
        "Reconstruct the locked XGBoost without the temporally uncertain assignment group to isolate model-family versus feature effects.",
        "Use as a safe boosting reference; reject as a promotion if it fails the complete gate.",
        dict(raw.LOCKED_XGB_PARAMS),
    ),
    ModelSpec(
        "word_tfidf_logistic", "sparse_text_linear", "word_tfidf_logistic",
        ("word_tfidf",),
        "Reconstruct the retained lexical mechanism without champion blending to isolate its contribution.",
        "Reject standalone text if it loses operational recall or paired temporal stability.",
        {"ngram_range": [1, 2], "min_df": 2, "max_features": 30000, "C": 1.0},
    ),
    ModelSpec(
        "word_char_tfidf_svm", "sparse_text_margin", "word_char_tfidf_svm",
        ("word_tfidf", "char_tfidf"),
        "Character shapes should generalize templated alert variants and identifiers that word tokenization fragments.",
        "Reject if character augmentation fails to improve robust PR-AUC over word-only text with non-degraded recall.",
        {"word_features": 22000, "char_features": 32000, "char_ngram_range": [3, 5], "C": 0.08},
    ),
    ModelSpec(
        "nbsvm_word_char", "nbsvm_sparse_text", "nbsvm_word_char",
        ("word_binary_counts", "char_binary_counts", "naive_bayes_log_count_ratio"),
        "Class-conditional log-count ratios can amplify rare violation-associated lexical patterns before a regularized linear fit.",
        "Reject if the NB transform fails to improve over the plain word/character margin model or destabilizes Top-5% recall.",
        {"word_features": 22000, "char_features": 32000, "char_ngram_range": [3, 5], "C": 0.50},
    ),
]


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, pd.Period, Path)):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(value), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _rss_mb() -> float:
    return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)


def _max_rss_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return float(value / (1024 * 1024)) if sys.platform == "darwin" else float(value / 1024)


def _month_indices(kpi: pd.DataFrame, month: pd.Period) -> tuple[np.ndarray, np.ndarray]:
    start = month.start_time
    end = (month + 1).start_time
    train = np.flatnonzero(((kpi[raw.OPEN] < start) & (kpi[raw.KNOWN] < start)).to_numpy())
    test = np.flatnonzero(((kpi[raw.OPEN] >= start) & (kpi[raw.OPEN] < end)).to_numpy())
    if not len(train) or not len(test):
        raise AssertionError(f"Empty fold: {month}")
    if not (kpi.iloc[train][raw.KNOWN] < start).all():
        raise AssertionError(f"Unknown training labels leaked into {month}")
    if not (kpi.iloc[train][raw.OPEN] < start).all():
        raise AssertionError(f"Future openings leaked into {month}")
    return train, test


def _top_metrics(y: np.ndarray, score: np.ndarray, share: float = TOP_SHARE) -> dict[str, Any]:
    k = max(1, int(round(len(y) * share)))
    chosen = np.argsort(-score, kind="stable")[:k]
    hits = int(y[chosen].sum())
    prevalence = float(y.mean())
    return {
        "k": int(k),
        "hits": hits,
        "precision": float(hits / k),
        "recall": float(hits / max(1, y.sum())),
        "lift": float((hits / k) / max(prevalence, 1e-12)),
    }


def _summarize_segment(fold_rows: list[dict[str, Any]]) -> dict[str, Any]:
    ys = np.concatenate([row["_y"] for row in fold_rows])
    scores = np.concatenate([row["_score"] for row in fold_rows])
    alerts = int(sum(row["top_5pct"]["k"] for row in fold_rows))
    hits = int(sum(row["top_5pct"]["hits"] for row in fold_rows))
    aps = np.asarray([row["pr_auc"] for row in fold_rows], dtype=float)
    days = int(sum(pd.Period(row["month"], freq="M").days_in_month for row in fold_rows))
    public_monthly = [{k: v for k, v in row.items() if not k.startswith("_")} for row in fold_rows]
    return {
        "aggregate": {
            "incidents": int(len(ys)),
            "violations": int(ys.sum()),
            "prevalence": float(ys.mean()),
            "pr_auc": float(average_precision_score(ys, scores)),
            "robust_pr_auc": float(np.median(aps)),
            "monthly_pr_auc_mean": float(aps.mean()),
            "monthly_pr_auc_std": float(aps.std()),
            "precision_at_top_5pct": float(hits / alerts),
            "recall_at_top_5pct": float(hits / max(1, ys.sum())),
            "lift_at_top_5pct": float((hits / alerts) / max(float(ys.mean()), 1e-12)),
            "alerts": alerts,
            "hits": hits,
            "alerts_per_day": float(alerts / days),
            "incidents_reviewed_per_true_violation": None if hits == 0 else float(alerts / hits),
        },
        "monthly": public_monthly,
    }


def _make_result(name: str, family: str, config: dict[str, Any], folds: list[dict[str, Any]], runtime: dict[str, float]) -> dict[str, Any]:
    segments: dict[str, Any] = {}
    for segment, priority in SEGMENTS.items():
        rows: list[dict[str, Any]] = []
        for fold in folds:
            mask = np.ones(len(fold["y"]), dtype=bool) if priority is None else fold["priority"] == priority
            y = fold["y"][mask]
            score = fold["score"][mask]
            top = _top_metrics(y, score)
            rows.append({
                "month": fold["month"],
                "train_incidents": fold["train_incidents"],
                "train_violations": fold["train_violations"],
                "test_incidents": int(len(y)),
                "test_violations": int(y.sum()),
                "pr_auc": float(average_precision_score(y, score)),
                "roc_auc_secondary": float(roc_auc_score(y, score)),
                "top_5pct": top,
                "feature_count": fold["feature_count"],
                "_y": y,
                "_score": score,
            })
        segments[segment] = _summarize_segment(rows)
    return {
        "name": name,
        "family": family,
        "config": config,
        "segments": segments,
        "runtime": runtime,
        "_folds": folds,
    }


def _numeric_columns(store: raw.FeatureStore, spec: ModelSpec) -> list[str]:
    columns = list(store.family_numeric["base"])
    if not spec.config.get("no_history_novelty"):
        columns += store.family_numeric["historical_outcomes"]
        columns += store.family_numeric["novelty_support"]
    columns = list(dict.fromkeys(columns))
    if spec.config.get("no_volume"):
        columns = [c for c in columns if not (c.startswith("lag") or c.startswith("roll"))]
    return columns


def _structured_sparse_matrices(
    bundle: raw.DataBundle,
    store: raw.FeatureStore,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    spec: ModelSpec,
) -> tuple[sparse.csr_matrix, sparse.csr_matrix, int]:
    num_cols = _numeric_columns(store, spec)
    tr_num = store.numeric.iloc[train_idx][num_cols].to_numpy(dtype=np.float32)
    te_num = store.numeric.iloc[test_idx][num_cols].to_numpy(dtype=np.float32)
    num_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler(with_mean=False)),
    ])
    tr_num_sparse = sparse.csr_matrix(num_pipe.fit_transform(tr_num), dtype=np.float32)
    te_num_sparse = sparse.csr_matrix(num_pipe.transform(te_num), dtype=np.float32)
    if spec.config.get("no_categories"):
        return tr_num_sparse, te_num_sparse, int(tr_num_sparse.shape[1])
    cat_cols = raw.SAFE_BASE_CATEGORICAL
    tr_cat = pd.DataFrame({c: store.categorical[c].iloc[train_idx].astype(str).to_numpy() for c in cat_cols})
    te_cat = pd.DataFrame({c: store.categorical[c].iloc[test_idx].astype(str).to_numpy() for c in cat_cols})
    onehot = OneHotEncoder(handle_unknown="ignore", min_frequency=3, dtype=np.float32)
    tr_ohe = onehot.fit_transform(tr_cat)
    te_ohe = onehot.transform(te_cat)
    xtr = sparse.hstack([tr_num_sparse, tr_ohe], format="csr", dtype=np.float32)
    xte = sparse.hstack([te_num_sparse, te_ohe], format="csr", dtype=np.float32)
    return xtr, xte, int(xtr.shape[1])


def _dense_matrices(
    bundle: raw.DataBundle,
    store: raw.FeatureStore,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    champion: bool,
) -> tuple[np.ndarray, np.ndarray, int]:
    xtr, xte, names = raw._prepare_fold(store, bundle.kpi, train_idx, test_idx, [], champion)
    return xtr, xte, len(names)


def _word_tfidf(text_train: pd.Series, text_test: pd.Series, max_features: int = 30000) -> tuple[sparse.csr_matrix, sparse.csr_matrix, int]:
    vec = TfidfVectorizer(
        strip_accents="unicode", lowercase=True, ngram_range=(1, 2), min_df=2,
        max_df=0.995, max_features=max_features, sublinear_tf=True, dtype=np.float32,
    )
    xtr = vec.fit_transform(text_train.astype(str))
    xte = vec.transform(text_test.astype(str))
    return xtr, xte, int(xtr.shape[1])


def _word_char_tfidf(text_train: pd.Series, text_test: pd.Series, spec: ModelSpec) -> tuple[sparse.csr_matrix, sparse.csr_matrix, int]:
    word = TfidfVectorizer(
        strip_accents="unicode", lowercase=True, analyzer="word", ngram_range=(1, 2),
        min_df=2, max_df=0.995, max_features=spec.config["word_features"], sublinear_tf=True, dtype=np.float32,
    )
    char = TfidfVectorizer(
        strip_accents="unicode", lowercase=True, analyzer="char_wb",
        ngram_range=tuple(spec.config["char_ngram_range"]), min_df=3,
        max_features=spec.config["char_features"], sublinear_tf=True, dtype=np.float32,
    )
    xtr_word = word.fit_transform(text_train.astype(str))
    xte_word = word.transform(text_test.astype(str))
    xtr_char = char.fit_transform(text_train.astype(str))
    xte_char = char.transform(text_test.astype(str))
    xtr = sparse.hstack([xtr_word, xtr_char], format="csr", dtype=np.float32)
    xte = sparse.hstack([xte_word, xte_char], format="csr", dtype=np.float32)
    return xtr, xte, int(xtr.shape[1])


def _nbsvm_matrices(text_train: pd.Series, text_test: pd.Series, y_train: np.ndarray, spec: ModelSpec) -> tuple[sparse.csr_matrix, sparse.csr_matrix, int]:
    word = CountVectorizer(
        strip_accents="unicode", lowercase=True, analyzer="word", ngram_range=(1, 2),
        min_df=2, max_features=spec.config["word_features"], binary=True, dtype=np.float32,
    )
    char = CountVectorizer(
        strip_accents="unicode", lowercase=True, analyzer="char_wb",
        ngram_range=tuple(spec.config["char_ngram_range"]), min_df=3,
        max_features=spec.config["char_features"], binary=True, dtype=np.float32,
    )
    xtr = sparse.hstack([
        word.fit_transform(text_train.astype(str)),
        char.fit_transform(text_train.astype(str)),
    ], format="csr", dtype=np.float32)
    xte = sparse.hstack([
        word.transform(text_test.astype(str)),
        char.transform(text_test.astype(str)),
    ], format="csr", dtype=np.float32)
    pos = np.asarray(xtr[y_train == 1].sum(axis=0)).ravel() + 1.0
    neg = np.asarray(xtr[y_train == 0].sum(axis=0)).ravel() + 1.0
    ratio = np.log(pos / pos.sum()) - np.log(neg / neg.sum())
    ratio = ratio.astype(np.float32)
    return xtr.multiply(ratio).tocsr(), xte.multiply(ratio).tocsr(), int(xtr.shape[1])


def _fit_score_fold(
    spec: ModelSpec,
    bundle: raw.DataBundle,
    store: raw.FeatureStore,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, int]:
    y_train = bundle.kpi.iloc[train_idx][raw.TARGET].to_numpy(dtype=np.int8)
    if spec.kind in {"elastic_structured", "linear_svm_structured"}:
        xtr, xte, count = _structured_sparse_matrices(bundle, store, train_idx, test_idx, spec)
        if spec.kind == "elastic_structured":
            model = SGDClassifier(
                loss="log_loss", penalty="elasticnet", alpha=spec.config["alpha"],
                l1_ratio=spec.config["l1_ratio"], class_weight="balanced",
                max_iter=spec.config["max_iter"], tol=1e-3, average=True,
                random_state=seed,
            )
            model.fit(xtr, y_train)
            score = model.predict_proba(xte)[:, 1]
        else:
            model = LinearSVC(
                C=spec.config["C"], class_weight="balanced", max_iter=spec.config["max_iter"],
                dual="auto", random_state=seed,
            )
            model.fit(xtr, y_train)
            score = model.decision_function(xte)
    elif spec.kind in {"extra_trees", "hist_gradient_boosting", "xgboost_safe", "champion"}:
        xtr, xte, count = _dense_matrices(bundle, store, train_idx, test_idx, champion=spec.kind == "champion")
        if spec.kind == "extra_trees":
            model = ExtraTreesClassifier(
                n_estimators=spec.config["n_estimators"], max_depth=spec.config["max_depth"],
                min_samples_leaf=spec.config["min_samples_leaf"], max_features=spec.config["max_features"],
                class_weight="balanced", bootstrap=False, random_state=seed, n_jobs=min(6, os.cpu_count() or 1),
            )
            model.fit(xtr, y_train)
            score = model.predict_proba(xte)[:, 1]
        elif spec.kind == "hist_gradient_boosting":
            model = HistGradientBoostingClassifier(
                learning_rate=spec.config["learning_rate"], max_iter=spec.config["max_iter"],
                max_leaf_nodes=spec.config["max_leaf_nodes"], min_samples_leaf=spec.config["min_samples_leaf"],
                l2_regularization=spec.config["l2_regularization"], class_weight="balanced",
                early_stopping=False, random_state=seed,
            )
            model.fit(xtr, y_train)
            score = model.predict_proba(xte)[:, 1]
        else:
            model = xgb.XGBClassifier(
                **raw.LOCKED_XGB_PARAMS, objective="binary:logistic", eval_metric="aucpr",
                random_state=seed, n_jobs=min(6, os.cpu_count() or 1), tree_method="hist",
            )
            model.fit(xtr, y_train, verbose=False)
            score = model.predict_proba(xte)[:, 1]
    elif spec.kind == "word_tfidf_logistic":
        xtr, xte, count = _word_tfidf(store.descriptions.iloc[train_idx], store.descriptions.iloc[test_idx], spec.config["max_features"])
        model = LogisticRegression(C=spec.config["C"], class_weight="balanced", max_iter=2000, solver="liblinear", random_state=seed)
        model.fit(xtr, y_train)
        score = model.predict_proba(xte)[:, 1]
    elif spec.kind == "word_char_tfidf_svm":
        xtr, xte, count = _word_char_tfidf(store.descriptions.iloc[train_idx], store.descriptions.iloc[test_idx], spec)
        model = LinearSVC(C=spec.config["C"], class_weight="balanced", max_iter=5000, dual="auto", random_state=seed)
        model.fit(xtr, y_train)
        score = model.decision_function(xte)
    elif spec.kind == "nbsvm_word_char":
        xtr, xte, count = _nbsvm_matrices(store.descriptions.iloc[train_idx], store.descriptions.iloc[test_idx], y_train, spec)
        model = LogisticRegression(C=spec.config["C"], class_weight="balanced", max_iter=2000, solver="liblinear", random_state=seed)
        model.fit(xtr, y_train)
        score = model.predict_proba(xte)[:, 1]
    else:
        raise ValueError(f"Unknown kind: {spec.kind}")
    del model, xtr, xte
    gc.collect()
    return np.asarray(score, dtype=float), count


def evaluate_spec(spec: ModelSpec, bundle: raw.DataBundle, store: raw.FeatureStore, seed: int = SEED) -> dict[str, Any]:
    started = time.perf_counter()
    rss_start = _rss_mb()
    folds: list[dict[str, Any]] = []
    for month in raw.OUTER_MONTHS:
        train_idx, test_idx = _month_indices(bundle.kpi, month)
        score, feature_count = _fit_score_fold(spec, bundle, store, train_idx, test_idx, seed)
        folds.append({
            "month": str(month),
            "train_incidents": int(len(train_idx)),
            "train_violations": int(bundle.kpi.iloc[train_idx][raw.TARGET].sum()),
            "y": bundle.kpi.iloc[test_idx][raw.TARGET].to_numpy(dtype=np.int8),
            "priority": bundle.kpi.iloc[test_idx][raw.PRIORITY].to_numpy(),
            "score": score,
            "feature_count": int(feature_count),
        })
    runtime = {
        "seconds": float(time.perf_counter() - started),
        "rss_start_mb": rss_start,
        "rss_end_mb": _rss_mb(),
        "process_peak_rss_mb": _max_rss_mb(),
    }
    config = {"kind": spec.kind, "seed": seed, **spec.config}
    return _make_result(spec.name, spec.family, config, folds, runtime)


def _rank01(values: np.ndarray) -> np.ndarray:
    return pd.Series(values).rank(method="average", pct=True).to_numpy(dtype=float)


def evaluate_hybrid(name: str, components: list[dict[str, Any]], weights: list[float]) -> dict[str, Any]:
    started = time.perf_counter()
    if not np.isclose(sum(weights), 1.0):
        raise AssertionError("Hybrid weights must sum to one")
    folds: list[dict[str, Any]] = []
    for fold_number, month in enumerate(raw.OUTER_MONTHS):
        source = components[0]["_folds"][fold_number]
        scores = sum(weight * _rank01(component["_folds"][fold_number]["score"]) for component, weight in zip(components, weights))
        folds.append({
            **{k: source[k] for k in ["month", "train_incidents", "train_violations", "y", "priority"]},
            "score": np.asarray(scores, dtype=float),
            "feature_count": int(sum(component["_folds"][fold_number]["feature_count"] for component in components)),
        })
    return _make_result(
        name, "leakage_safe_fixed_rank_hybrid",
        {"kind": "fixed_rank_hybrid", "components": [c["name"] for c in components], "weights": weights, "seed": SEED},
        folds,
        {"seconds": float(time.perf_counter() - started), "rss_start_mb": _rss_mb(), "rss_end_mb": _rss_mb(), "process_peak_rss_mb": _max_rss_mb()},
    )


def _public_result(result: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in result.items() if not k.startswith("_")}


def compare_to_champion(candidate: dict[str, Any], champion: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for segment in SEGMENTS:
        cand = candidate["segments"][segment]
        base = champion["segments"][segment]
        monthly = []
        for c_row, b_row in zip(cand["monthly"], base["monthly"]):
            if c_row["month"] != b_row["month"]:
                raise AssertionError("Unpaired monthly rows")
            monthly.append({
                "month": c_row["month"],
                "candidate_pr_auc": c_row["pr_auc"],
                "champion_pr_auc": b_row["pr_auc"],
                "delta": float(c_row["pr_auc"] - b_row["pr_auc"]),
                "candidate_hits": c_row["top_5pct"]["hits"],
                "champion_hits": b_row["top_5pct"]["hits"],
            })
        ca = cand["aggregate"]
        ba = base["aggregate"]
        robust_relative = float(ca["robust_pr_auc"] / max(ba["robust_pr_auc"], 1e-12) - 1.0)
        recall_floor = 0.95 * ba["recall_at_top_5pct"]
        checks = {
            "robust_pr_auc_improvement_at_least_15pct": robust_relative >= 0.15,
            "monthly_pr_auc_wins_at_least_4": sum(row["delta"] > 0 for row in monthly) >= 4,
            "recall_at_top_5pct_no_more_than_5pct_relative_degradation": ca["recall_at_top_5pct"] + 1e-12 >= recall_floor,
            "point_in_time_safe": candidate["config"]["kind"] != "champion",
        }
        output[segment] = {
            "pooled_pr_auc_delta": float(ca["pr_auc"] - ba["pr_auc"]),
            "pooled_pr_auc_relative": float(ca["pr_auc"] / max(ba["pr_auc"], 1e-12) - 1.0),
            "robust_pr_auc_delta": float(ca["robust_pr_auc"] - ba["robust_pr_auc"]),
            "robust_pr_auc_relative": robust_relative,
            "monthly_pr_auc_wins": int(sum(row["delta"] > 0 for row in monthly)),
            "precision_at_top_5pct_delta": float(ca["precision_at_top_5pct"] - ba["precision_at_top_5pct"]),
            "recall_at_top_5pct_delta": float(ca["recall_at_top_5pct"] - ba["recall_at_top_5pct"]),
            "monthly": monthly,
            "gate_checks": checks,
            "passes": bool(all(checks.values())),
        }
    return output


def _candidate_key(result: dict[str, Any], comparison: dict[str, Any]) -> tuple[Any, ...]:
    passing_segments = [s for s in SEGMENTS if comparison[s]["passes"]]
    best_improvement = max((comparison[s]["robust_pr_auc_relative"] for s in SEGMENTS), default=-np.inf)
    best_wins = max(comparison[s]["monthly_pr_auc_wins"] for s in SEGMENTS)
    pooled = max(result["segments"][s]["aggregate"]["pr_auc"] for s in SEGMENTS)
    return (bool(passing_segments), len(passing_segments), best_wins, best_improvement, pooled)


def _feature_catalog(ablations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    common = {
        "availability": "Computed at incident opening from the current opening record or strictly prior events/outcomes.",
        "missing_behavior": "Categorical absence is an explicit level; numeric absence is fold-fitted median imputation.",
        "affected_track": "incident-level OLA risk",
    }
    catalog = {
        "families": {
            "calendar_volume": {
                **common,
                "mechanism": "Opening calendar plus D-1/D-7 and left-shifted rolling incident volumes proxy operating regime.",
                "source_columns": ["Aberto", "Prioridade"],
                "leakage_analysis": "All lags and rolling windows end before the opening date; current-day total is excluded.",
                "compute_memory_cost": "low; dense float32",
            },
            "sparse_categories": {
                **common,
                "mechanism": "Fold-fitted one-hot identity represents additive opening classification effects without ordinal assumptions.",
                "source_columns": raw.SAFE_BASE_CATEGORICAL,
                "leakage_analysis": "Vocabulary is fitted only on pre-month training rows; unknown levels are ignored.",
                "compute_memory_cost": "low; CSR sparse matrix",
            },
            "historical_backoff": {
                **common,
                "mechanism": "Smoothed violation history and support for product/category/subcategory using outcomes known before each opening.",
                "source_columns": ["Produto", "Categoria", "Subcategoria", "KPI Violado?", "Resolvido", "Encerrado"],
                "leakage_analysis": "Target appears only in strictly prior known outcomes; current/future outcomes are excluded by event-time search.",
                "compute_memory_cost": "low; six dense float32 features",
            },
            "novelty_missingness": {
                **common,
                "mechanism": "Prior support and first-seen indicators expose unfamiliar classifications while preserving informative missingness.",
                "source_columns": ["Produto", "Categoria", "Subcategoria", "Item de configuração", "Descrição resumida", "Aberto"],
                "leakage_analysis": "Support uses only prior openings; simultaneous/current rows are left-open excluded.",
                "compute_memory_cost": "low; ten dense float32 features",
            },
            "fold_safe_encoded_categories": {
                **common,
                "mechanism": "Code, frequency, and smoothed target encodings make categories usable by tree models.",
                "source_columns": raw.SAFE_BASE_CATEGORICAL,
                "leakage_analysis": "Maps are fitted inside each outer fold; training target encodings are leave-one-out.",
                "compute_memory_cost": "low; twelve dense float32 features",
            },
            "word_tfidf": {
                **common,
                "mechanism": "Word unigrams/bigrams capture recurring alert and incident-summary templates.",
                "source_columns": ["Descrição resumida"],
                "leakage_analysis": "Vocabulary/IDF are fitted only on training rows; no vocabulary or raw text is persisted.",
                "compute_memory_cost": "moderate; up to 30k sparse features",
            },
            "char_tfidf": {
                **common,
                "mechanism": "Character 3-5 grams capture morphological variants and fragmented machine identifiers.",
                "source_columns": ["Descrição resumida"],
                "leakage_analysis": "Fold-local vocabulary; no raw token output.",
                "compute_memory_cost": "moderate; up to 32k sparse features",
            },
            "naive_bayes_log_count_ratio": {
                **common,
                "mechanism": "Training-only class-conditional ratios reweight binary word/character counts before logistic fitting.",
                "source_columns": ["Descrição resumida", "KPI Violado?"],
                "leakage_analysis": "Ratios use training labels only and are recomputed for every outer fold.",
                "compute_memory_cost": "moderate; sparse elementwise scaling",
            },
            "fixed_rank_hybrid": {
                **common,
                "mechanism": "Predeclared equal-weight fold-local ranks combine independent text and safe structured error patterns.",
                "source_columns": ["safe structured features", "Descrição resumida"],
                "leakage_analysis": "Weights are fixed before evaluation; no outer-fold labels tune blending.",
                "compute_memory_cost": "low after component inference",
            },
        },
        "forbidden_predictor_fields": ["Duração", "Resolvido", "Encerrado", "Código de fechamento", "Solução", "KPI Violado?", "Status", "Incidente Pai", "Entrou para KPI?"],
        "temporally_uncertain_group_policy": "Grupo designado is used only by the reconstructed champion, never by challengers.",
    }
    if ablations is not None:
        by_family = {row["feature_or_mechanism"]: row for row in ablations}
        mapping = {
            "sparse_categories": "sparse_categories",
            "historical_backoff": "historical_backoff_plus_novelty",
            "novelty_missingness": "historical_backoff_plus_novelty",
            "calendar_volume": "volume_context",
            "char_tfidf": "character_tfidf_and_margin",
            "naive_bayes_log_count_ratio": "naive_bayes_log_count_ratio",
            "fixed_rank_hybrid": "fixed_rank_hybrid",
        }
        for family, ablation_key in mapping.items():
            catalog["families"][family]["ablation_result"] = by_family.get(ablation_key, "No isolated ablation available")
        for family in catalog["families"]:
            catalog["families"][family].setdefault("ablation_result", "Evaluated as part of a model-family cycle; no clean one-factor isolation")
    return catalog


def _model_registry(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_name = {result["name"]: result for result in results}
    entries = []
    for spec in SPECS:
        result = by_name[spec.name]
        entries.append({
            "name": spec.name,
            "family": spec.family,
            "mechanism": spec.mechanism,
            "falsification": spec.falsification,
            "feature_families": list(spec.feature_families),
            "config": result["config"],
            "runtime": result["runtime"],
        })
    entries.append({
        "name": "hybrid_nbsvm_xgboost", "family": "leakage_safe_fixed_rank_hybrid",
        "mechanism": "Equal-weight rank blend of NB-SVM lexical and safe XGBoost structured signals.",
        "falsification": "Reject if it fails the full promotion gate or adds no robust value over both components.",
        "feature_families": ["word_binary_counts", "char_binary_counts", "naive_bayes_log_count_ratio", "calendar_volume", "fold_safe_encoded_categories"],
        "config": by_name["hybrid_nbsvm_xgboost"]["config"],
        "runtime": by_name["hybrid_nbsvm_xgboost"]["runtime"],
    })
    return {"models": entries}


def _log_record(cycle: int, result: dict[str, Any], comparison: dict[str, Any], spec: ModelSpec | None) -> dict[str, Any]:
    return {
        "cycle": cycle,
        "name": result["name"],
        "family": result["family"],
        "mechanism": spec.mechanism if spec else "Fixed equal-rank fusion of safe structured boosting and NB-SVM text.",
        "falsification": spec.falsification if spec else "Reject if the fusion cannot pass the predeclared complete gate.",
        "status": "PROMOTION CANDIDATE" if any(comparison[s]["passes"] for s in SEGMENTS) else "RETAIN" if max(comparison[s]["monthly_pr_auc_wins"] for s in SEGMENTS) >= 4 else "REJECT",
        "metrics": {s: result["segments"][s]["aggregate"] for s in SEGMENTS},
        "paired_vs_champion": comparison,
        "runtime": result["runtime"],
    }


def _ablation_rows(results_by_name: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    pairs = [
        ("sparse_categories", "elastic_structured_full", "elastic_no_categories"),
        ("historical_backoff_plus_novelty", "elastic_structured_full", "elastic_no_history_novelty"),
        ("volume_context", "elastic_structured_full", "elastic_no_volume_context"),
        ("character_tfidf_and_margin", "word_char_tfidf_svm", "word_tfidf_logistic"),
        ("naive_bayes_log_count_ratio", "nbsvm_word_char", "word_char_tfidf_svm"),
        ("fixed_rank_hybrid", "hybrid_nbsvm_xgboost", "nbsvm_word_char"),
    ]
    rows: list[dict[str, Any]] = []
    for family, full_name, ablated_name in pairs:
        full = results_by_name[full_name]
        ablated = results_by_name[ablated_name]
        row = {"feature_or_mechanism": family, "full": full_name, "ablated_or_reference": ablated_name, "segments": {}}
        for segment in SEGMENTS:
            fa = full["segments"][segment]["aggregate"]
            aa = ablated["segments"][segment]["aggregate"]
            row["segments"][segment] = {
                "pooled_pr_auc_delta": float(fa["pr_auc"] - aa["pr_auc"]),
                "robust_pr_auc_delta": float(fa["robust_pr_auc"] - aa["robust_pr_auc"]),
                "recall_at_top_5pct_delta": float(fa["recall_at_top_5pct"] - aa["recall_at_top_5pct"]),
            }
        rows.append(row)
    return rows


def run(seed: int = SEED, write_artifacts: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    checks = raw.self_checks()
    bundle = raw.load_data()
    store = raw.build_feature_store(bundle)

    champion_spec = ModelSpec(
        "reconstructed_champion", "locked_xgboost_champion", "champion",
        ("calendar_volume", "fold_safe_encoded_categories", "temporally_uncertain_group"),
        "Reproduce the prior locked generalist under the exact monthly protocol.",
        "Comparator only; not promotion eligible because assignment timing is uncertain.",
        dict(raw.LOCKED_XGB_PARAMS),
    )
    champion = evaluate_spec(champion_spec, bundle, store, seed=seed)
    results: list[dict[str, Any]] = []
    comparisons: dict[str, Any] = {}
    registry_rows: list[dict[str, Any]] = []
    for cycle, spec in enumerate(SPECS, 1):
        result = evaluate_spec(spec, bundle, store, seed=seed)
        comparison = compare_to_champion(result, champion)
        results.append(result)
        comparisons[result["name"]] = comparison
        registry_rows.append(_log_record(cycle, result, comparison, spec))
        print(
            f"[{cycle:02d}/{len(SPECS)+1}] {result['name']}: "
            f"global AP={result['segments']['global']['aggregate']['pr_auc']:.5f}, "
            f"P2={result['segments']['P2']['aggregate']['pr_auc']:.5f}, "
            f"P3={result['segments']['P3']['aggregate']['pr_auc']:.5f}",
            flush=True,
        )

    by_name = {result["name"]: result for result in results}
    hybrid = evaluate_hybrid("hybrid_nbsvm_xgboost", [by_name["nbsvm_word_char"], by_name["xgboost_safe_reconstruction"]], [0.5, 0.5])
    hybrid_comparison = compare_to_champion(hybrid, champion)
    results.append(hybrid)
    comparisons[hybrid["name"]] = hybrid_comparison
    registry_rows.append(_log_record(len(SPECS) + 1, hybrid, hybrid_comparison, None))
    print(
        f"[{len(SPECS)+1:02d}/{len(SPECS)+1}] {hybrid['name']}: "
        f"global AP={hybrid['segments']['global']['aggregate']['pr_auc']:.5f}, "
        f"P2={hybrid['segments']['P2']['aggregate']['pr_auc']:.5f}, "
        f"P3={hybrid['segments']['P3']['aggregate']['pr_auc']:.5f}",
        flush=True,
    )

    strongest = max(results, key=lambda r: _candidate_key(r, comparisons[r["name"]]))
    strongest_comparison = comparisons[strongest["name"]]
    passing_segments = [s for s in SEGMENTS if strongest_comparison[s]["passes"]]
    status = "PROMOTION CANDIDATE" if passing_segments else "NO PROMOTION CANDIDATE"
    results_by_name = {r["name"]: r for r in results}
    ablations = _ablation_rows(results_by_name)
    # Seed sensitivity is measured only after model/candidate selection. This is
    # a stability check, never a second opportunity to tune the outer folds.
    stability_runs: list[dict[str, Any]] = []
    spec_by_name = {spec.name: spec for spec in SPECS}
    for stability_seed in STABILITY_SEEDS:
        if stability_seed == seed:
            seeded = strongest
        elif strongest["name"] == "hybrid_nbsvm_xgboost":
            nb_seeded = evaluate_spec(spec_by_name["nbsvm_word_char"], bundle, store, seed=stability_seed)
            xgb_seeded = evaluate_spec(spec_by_name["xgboost_safe_reconstruction"], bundle, store, seed=stability_seed)
            seeded = evaluate_hybrid("hybrid_nbsvm_xgboost", [nb_seeded, xgb_seeded], [0.5, 0.5])
            seeded["config"]["seed"] = stability_seed
        else:
            seeded = evaluate_spec(spec_by_name[strongest["name"]], bundle, store, seed=stability_seed)
        stability_runs.append({
            "seed": stability_seed,
            "segments": {segment: seeded["segments"][segment]["aggregate"] for segment in SEGMENTS},
        })
    stability_summary = {}
    for segment in SEGMENTS:
        robust = np.asarray([row["segments"][segment]["robust_pr_auc"] for row in stability_runs])
        recall = np.asarray([row["segments"][segment]["recall_at_top_5pct"] for row in stability_runs])
        stability_summary[segment] = {
            "robust_pr_auc_min": float(robust.min()),
            "robust_pr_auc_max": float(robust.max()),
            "robust_pr_auc_relative_range": float((robust.max() - robust.min()) / max(float(np.median(robust)), 1e-12)),
            "recall_at_top_5pct_min": float(recall.min()),
            "recall_at_top_5pct_max": float(recall.max()),
            "recall_at_top_5pct_relative_range": float((recall.max() - recall.min()) / max(float(np.median(recall)), 1e-12)),
        }
    metrics = {
        "workstream_status": status,
        "generated_at": pd.Timestamp.now(tz="America/Sao_Paulo").isoformat(),
        "protocol": {
            "outer_months": [str(m) for m in raw.OUTER_MONTHS],
            "training_rule": "opened before fold start AND resolution/closure label known before fold start",
            "evaluation_rows": "all P2/P3 KPI incidents opened in each outer month; identical rows for every model",
            "segments": list(SEGMENTS),
            "top_k_share": TOP_SHARE,
            "primary_robust_metric": "median of six monthly PR-AUC values",
            "operational_guardrail": "Recall@Top-5% must be at least 95% of champion (relative)",
            "promotion_gate": ">=15% robust PR-AUC improvement; >=4/6 monthly wins; <=5% relative Recall@Top-5% degradation; point-in-time safe",
            "threshold_selection": "none; Top-5% workload is predeclared",
            "q4_is_fresh": False,
        },
        "champion": _public_result(champion),
        "experiments": [_public_result(r) for r in results],
        "comparisons_to_champion": comparisons,
        "strongest_candidate_name": strongest["name"],
        "strongest_candidate": _public_result(strongest),
        "strongest_comparison": strongest_comparison,
        "passing_segments": passing_segments,
        "ablations": ablations,
        "seed_stability": {"seeds": STABILITY_SEEDS, "runs": stability_runs, "summary": stability_summary},
        "coverage": {
            "cycles": len(results),
            "model_families": sorted(set(r["family"] for r in results)),
            "feature_families": sorted({f for spec in SPECS for f in spec.feature_families} | {"fixed_rank_hybrid"}),
            "explicit_ablations": len(ablations),
        },
        "leakage_checks": {
            **checks,
            "same_outer_rows_for_all_models": True,
            "training_openings_strictly_before_month": True,
            "training_labels_known_strictly_before_month": True,
            "text_vocabulary_fit_per_fold": True,
            "category_vocabulary_fit_per_fold": True,
            "ensemble_weights_fixed_without_outer_labels": True,
            "uncertain_group_absent_from_challengers": True,
            "no_sensitive_values_persisted": True,
        },
        "data_hashes": {"raw": _hash_file(raw.RAW_PATH), "processed": _hash_file(raw.PROCESSED_PATH)},
        "environment": {
            "python": platform.python_version(), "platform": platform.platform(),
            "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__, "xgboost": xgb.__version__, "joblib": joblib.__version__,
            "psutil": psutil.__version__, "cpu_count": os.cpu_count(),
        },
        "runtime": {
            "total_seconds": float(time.perf_counter() - started),
            "process_peak_rss_mb": _max_rss_mb(),
            "declared_memory_ceiling_mb": 18432,
            "within_declared_ceiling": _max_rss_mb() < 18432,
        },
    }
    if write_artifacts:
        with (WORK_DIR / "experiment_registry.jsonl").open("w", encoding="utf-8") as handle:
            for row in registry_rows:
                handle.write(json.dumps(_json_safe(row), ensure_ascii=False, allow_nan=False) + "\n")
        _write_json(WORK_DIR / "feature_catalog.json", _feature_catalog(ablations))
        _write_json(WORK_DIR / "model_registry.json", _model_registry(results))
        _write_json(WORK_DIR / "metrics.json", metrics)
        strongest_spec = spec_by_name.get(strongest["name"])
        _write_json(MODEL_DIR / "final_candidate_config.json", {
            "candidate_name": strongest["name"], "config": strongest["config"],
            "model_family": strongest["family"],
            "feature_families": [] if strongest_spec is None else list(strongest_spec.feature_families),
            "component_configs": {
                name: results_by_name[name]["config"] for name in strongest["config"].get("components", [])
            },
            "data_hashes": metrics["data_hashes"], "seed": seed,
            "note": "Configuration only; no raw text vocabulary or sensitive values persisted.",
        })
        write_report(metrics)
    return metrics


def _metric_row(result: dict[str, Any], segment: str) -> str:
    a = result["segments"][segment]["aggregate"]
    reviewed = "n/a" if a["incidents_reviewed_per_true_violation"] is None else f"{a['incidents_reviewed_per_true_violation']:.1f}"
    return f"| {segment} | {a['pr_auc']:.5f} | {a['robust_pr_auc']:.5f} | {a['precision_at_top_5pct']:.2%} | {a['recall_at_top_5pct']:.2%} | {a['lift_at_top_5pct']:.2f} | {a['alerts']} | {reviewed} |"


def write_report(metrics: dict[str, Any]) -> None:
    champion = metrics["champion"]
    candidate = metrics["strongest_candidate"]
    comparison = metrics["strongest_comparison"]
    experiment_rows = []
    for result in metrics["experiments"]:
        parts = [result["name"]]
        for segment in SEGMENTS:
            a = result["segments"][segment]["aggregate"]
            parts += [f"{a['pr_auc']:.5f}", f"{a['robust_pr_auc']:.5f}", f"{a['recall_at_top_5pct']:.1%}"]
        experiment_rows.append("| " + " | ".join(parts) + " |")
    monthly_rows = []
    for segment in SEGMENTS:
        for row in comparison[segment]["monthly"]:
            monthly_rows.append(f"| {segment} | {row['month']} | {row['champion_pr_auc']:.5f} | {row['candidate_pr_auc']:.5f} | {row['delta']:+.5f} | {row['champion_hits']} | {row['candidate_hits']} |")
    ablation_rows = []
    for row in metrics["ablations"]:
        for segment in SEGMENTS:
            value = row["segments"][segment]
            ablation_rows.append(f"| {row['feature_or_mechanism']} | {segment} | {value['pooled_pr_auc_delta']:+.5f} | {value['robust_pr_auc_delta']:+.5f} | {value['recall_at_top_5pct_delta']:+.1%} |")
    gate_rows = []
    for segment in SEGMENTS:
        c = comparison[segment]
        gate_rows.append(f"| {segment} | {c['robust_pr_auc_relative']:+.1%} | {c['monthly_pr_auc_wins']}/6 | {c['recall_at_top_5pct_delta']:+.1%} | {'PASS' if c['passes'] else 'FAIL'} |")
    stability_rows = []
    for segment in SEGMENTS:
        summary = metrics["seed_stability"]["summary"][segment]
        stability_rows.append(
            f"| {segment} | {summary['robust_pr_auc_min']:.5f} | {summary['robust_pr_auc_max']:.5f} | "
            f"{summary['robust_pr_auc_relative_range']:.2%} | {summary['recall_at_top_5pct_min']:.2%} | "
            f"{summary['recall_at_top_5pct_max']:.2%} |"
        )
    report = f"""# Incident-level OLA Risk Workstream

## Workstream result

{metrics['workstream_status']}

The strongest point-in-time-safe candidate is `{metrics['strongest_candidate_name']}`. This workstream does not make the overall multi-track stopping decision; it supplies paired evidence to the parent feature-model laboratory.

## Protocol and predeclared gate

- Monthly outer folds: July through December 2025.
- Training rows opened strictly earlier and had a resolution/closure label known strictly before each fold start.
- Every model scores the same monthly P2/P3 rows; global, P2, and P3 metrics are derived from one fold fit.
- Robust PR-AUC is the median of the six monthly PR-AUC values.
- Operational workload is fixed at the top 5% within each segment/month.
- Model specifications are bounded and fixed; no outer-fold labels tune hyperparameters or ensemble weights.
- Promotion requires at least 15% robust PR-AUC improvement, at least four monthly wins, no more than 5% relative Recall@Top-5% degradation, and point-in-time-safe features.

## Champion versus strongest candidate

Champion:

| Segment | Pooled PR-AUC | Robust PR-AUC | Precision@5% | Recall@5% | Lift@5% | Alerts | Reviews/hit |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(_metric_row(champion, s) for s in SEGMENTS)}

Strongest candidate:

| Segment | Pooled PR-AUC | Robust PR-AUC | Precision@5% | Recall@5% | Lift@5% | Alerts | Reviews/hit |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(_metric_row(candidate, s) for s in SEGMENTS)}

| Segment | Robust improvement | Monthly wins | Recall@5% delta | Gate |
|---|---:|---:|---:|---:|
{chr(10).join(gate_rows)}

## Model-family coverage

| Model | Global pooled / robust / R@5 | P2 pooled / robust / R@5 | P3 pooled / robust / R@5 |
|---|---:|---:|---:|
{chr(10).join(experiment_rows)}

The {metrics['coverage']['cycles']} cycles cover {len(metrics['coverage']['model_families'])} named model families: {', '.join(metrics['coverage']['model_families'])}.

## Explicit feature/model ablations

Positive deltas mean the named full mechanism outperformed its ablated/reference model.

| Mechanism | Segment | Pooled PR-AUC delta | Robust PR-AUC delta | Recall@5% delta |
|---|---|---:|---:|---:|
{chr(10).join(ablation_rows)}

## Temporal stability of strongest candidate

| Segment | Month | Champion PR-AUC | Candidate PR-AUC | Delta | Champion hits | Candidate hits |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(monthly_rows)}

Three-seed sensitivity check (`{', '.join(str(s) for s in metrics['seed_stability']['seeds'])}`):

| Segment | Min robust PR-AUC | Max robust PR-AUC | Relative range | Min Recall@5% | Max Recall@5% |
|---|---:|---:|---:|---:|---:|
{chr(10).join(stability_rows)}

## Leakage and interpretation

The assignment group remains temporally uncertain and appears only in the reconstructed champion. Challengers use opening-time fields, strictly left-shifted volume/support features, and historical targets only after their outcome time. Category/text vocabularies are fold-local. Hybrid weights are fixed in advance. Scores are ranking signals, not calibrated probabilities.

No incident number, category value, source value, raw summary, token, or vocabulary is persisted. Post-outcome fields are never predictors; resolution and closure timestamps only establish when a prior label became observable.

## Runtime and memory

Total workstream runtime: {metrics['runtime']['total_seconds']:.1f} seconds. Observed process peak RSS: {metrics['runtime']['process_peak_rss_mb']:.1f} MB, below the declared 18 GB ceiling. Per-cycle measurements are in `experiment_registry.jsonl` and `model_registry.json`.

## Reproduction

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/predictfy-locaweb/bin/python experiments/feature_model_lab/workstreams/risk/reproduce.py
```
"""
    (WORK_DIR / "report.md").write_text(report, encoding="utf-8")


def reproduce() -> dict[str, Any]:
    expected = json.loads((WORK_DIR / "metrics.json").read_text(encoding="utf-8"))
    if _hash_file(raw.RAW_PATH) != expected["data_hashes"]["raw"] or _hash_file(raw.PROCESSED_PATH) != expected["data_hashes"]["processed"]:
        raise AssertionError("Input data hashes changed")
    candidate_name = expected["strongest_candidate_name"]
    needed = [candidate_name]
    if candidate_name == "hybrid_nbsvm_xgboost":
        needed = ["nbsvm_word_char", "xgboost_safe_reconstruction"]
    bundle = raw.load_data()
    store = raw.build_feature_store(bundle)
    champion_spec = ModelSpec("reconstructed_champion", "locked_xgboost_champion", "champion", (), "", "", dict(raw.LOCKED_XGB_PARAMS))
    champion = evaluate_spec(champion_spec, bundle, store, seed=expected["strongest_candidate"]["config"].get("seed", SEED))
    result_map = {}
    for spec in SPECS:
        if spec.name in needed:
            result_map[spec.name] = evaluate_spec(spec, bundle, store, seed=expected["strongest_candidate"]["config"].get("seed", SEED))
    if candidate_name == "hybrid_nbsvm_xgboost":
        candidate = evaluate_hybrid(candidate_name, [result_map["nbsvm_word_char"], result_map["xgboost_safe_reconstruction"]], [0.5, 0.5])
    else:
        candidate = result_map[candidate_name]
    candidate_comparison = compare_to_champion(candidate, champion)
    diffs: dict[str, float] = {}
    for segment in SEGMENTS:
        for key in ["pr_auc", "robust_pr_auc", "precision_at_top_5pct", "recall_at_top_5pct"]:
            diffs[f"{segment}.{key}"] = abs(candidate["segments"][segment]["aggregate"][key] - expected["strongest_candidate"]["segments"][segment]["aggregate"][key])
    tolerance = 1e-10
    check = {
        "passed": all(value <= tolerance for value in diffs.values()),
        "tolerance": tolerance,
        "absolute_differences": diffs,
        "data_hashes_verified": True,
        "clean_process_pid": os.getpid(),
        "candidate_name": candidate_name,
        "reproduced_candidate": _public_result(candidate),
        "reproduced_comparison": candidate_comparison,
    }
    _write_json(WORK_DIR / "reproduction_check.json", check)
    if not check["passed"]:
        raise AssertionError(f"Reproduction mismatch: {diffs}")
    print(json.dumps({"passed": True, "candidate_name": candidate_name, "max_absolute_difference": max(diffs.values())}, indent=2))
    return check


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reproduce", action="store_true")
    args = parser.parse_args()
    if args.reproduce:
        reproduce()
    else:
        run()


if __name__ == "__main__":
    main()
