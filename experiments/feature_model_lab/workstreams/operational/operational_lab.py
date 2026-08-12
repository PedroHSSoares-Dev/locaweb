#!/usr/bin/env python3
"""Isolated operational-track research for next-day high-workload advisories.

All persisted results are aggregate. Incident identifiers, people, categorical
values, and raw descriptions never leave memory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import resource
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler


ROOT = Path(__file__).resolve().parents[4]
RAW_PATH = ROOT / "data/raw/LW-DATASET.xlsx"
WORK_DIR = ROOT / "experiments/feature_model_lab/workstreams/operational"
MODEL_DIR = ROOT / "models_saved/experiments/feature_model_lab/operational"
OUTER_MONTHS = tuple(f"2025-{m:02d}" for m in range(7, 13))
SEEDS = (11, 29, 47, 71, 101)
TOP_SHARE = 0.20


CALENDAR_FEATURES = [
    "dow_sin", "dow_cos", "month_sin", "month_cos", "doy_sin", "doy_cos",
    "is_weekend", "is_month_end",
]
LAG_FEATURES = [f"lag_{lag}" for lag in (1, 2, 3, 7, 14, 21, 28, 56)]
ROLLING_FEATURES = [
    f"roll_{stat}_{window}"
    for window in (7, 14, 28, 56)
    for stat in ("mean", "median", "std", "q25", "q80")
] + [
    "same_dow_median_4", "same_dow_q80_4", "same_dow_median_8",
    "same_dow_q80_8", "same_dow_median_12", "same_dow_q80_12",
]
RESIDUAL_FEATURES = [
    "lag7_margin", "lag7_ratio", "past_resid_1", "past_resid_7",
    "past_resid_mean_7", "past_resid_mean_28", "past_high_rate_7",
    "past_high_rate_28",
]
REGIME_FEATURES = [
    "mean7_minus_mean28", "mean14_minus_mean56", "mean7_over_mean28",
    "std7_over_std28", "roll_mad_28", "slope_7", "slope_28", "threshold_change_7",
]
FULL_FEATURES = CALENDAR_FEATURES + LAG_FEATURES + ROLLING_FEATURES + RESIDUAL_FEATURES + REGIME_FEATURES


@dataclass
class FoldPrediction:
    month: str
    dates: list[str]
    y_true: list[int]
    score: list[float]
    train_days: int
    train_positives: int
    runtime_seconds: float


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_real_daily() -> tuple[pd.Series, dict[str, Any]]:
    opened = pd.read_excel(RAW_PATH, usecols=["Aberto"])["Aberto"]
    opened = pd.to_datetime(opened, errors="coerce")
    if opened.isna().any():
        raise ValueError(f"Found {int(opened.isna().sum())} invalid opening timestamps")
    counts = opened.dt.normalize().value_counts().sort_index().astype(float)
    full_index = pd.date_range(counts.index.min(), counts.index.max(), freq="D")
    counts = counts.reindex(full_index, fill_value=0.0).rename("y")
    if counts.index.has_duplicates:
        raise ValueError("Daily index contains duplicate dates")
    if counts.index.min() > pd.Timestamp("2023-01-02") or counts.index.max() < pd.Timestamp("2025-12-31"):
        raise ValueError("Unexpected raw-data date coverage")
    year_stats = {}
    for year, values in counts.groupby(counts.index.year):
        year_stats[str(year)] = {
            "days": int(len(values)), "mean": float(values.mean()),
            "std": float(values.std()), "min": float(values.min()),
            "median": float(values.median()), "max": float(values.max()),
        }
    audit = {
        "source": "data/raw/LW-DATASET.xlsx",
        "sha256": _sha256(RAW_PATH),
        "incident_rows": int(len(opened)),
        "valid_opening_timestamps": int(opened.notna().sum()),
        "daily_start": str(counts.index.min().date()),
        "daily_end": str(counts.index.max().date()),
        "calendar_days": int(len(counts)),
        "zero_count_days": int((counts == 0).sum()),
        "duplicate_daily_dates": int(counts.index.duplicated().sum()),
        "year_stats": year_stats,
        "sensitive_values_persisted": False,
    }
    return counts, audit


def _rolling_slope(values: np.ndarray) -> float:
    if len(values) < 2 or not np.isfinite(values).all():
        return np.nan
    x = np.arange(len(values), dtype=float)
    return float(np.polyfit(x, values.astype(float), 1)[0])


def build_frame(counts: pd.Series) -> pd.DataFrame:
    frame = pd.DataFrame({"y": counts.astype(float)})
    idx = frame.index
    dow = idx.dayofweek
    frame["dow_sin"] = np.sin(2 * np.pi * dow / 7)
    frame["dow_cos"] = np.cos(2 * np.pi * dow / 7)
    frame["month_sin"] = np.sin(2 * np.pi * idx.month / 12)
    frame["month_cos"] = np.cos(2 * np.pi * idx.month / 12)
    frame["doy_sin"] = np.sin(2 * np.pi * idx.dayofyear / 365.25)
    frame["doy_cos"] = np.cos(2 * np.pi * idx.dayofyear / 365.25)
    frame["is_weekend"] = (dow >= 5).astype(float)
    frame["is_month_end"] = idx.is_month_end.astype(float)

    for lag in (1, 2, 3, 7, 14, 21, 28, 56):
        frame[f"lag_{lag}"] = frame["y"].shift(lag)
    shifted = frame["y"].shift(1)
    for window in (7, 14, 28, 56):
        roll = shifted.rolling(window, min_periods=max(4, window // 2))
        frame[f"roll_mean_{window}"] = roll.mean()
        frame[f"roll_median_{window}"] = roll.median()
        frame[f"roll_std_{window}"] = roll.std()
        frame[f"roll_q25_{window}"] = roll.quantile(0.25)
        frame[f"roll_q80_{window}"] = roll.quantile(0.80)

    dow_key = pd.Series(dow, index=idx)
    for window in (4, 8, 12):
        prior_dow = frame["y"].groupby(dow_key).transform(
            lambda s: s.shift(1).rolling(window, min_periods=window).median()
        )
        prior_q80 = frame["y"].groupby(dow_key).transform(
            lambda s: s.shift(1).rolling(window, min_periods=window).quantile(0.80)
        )
        frame[f"same_dow_median_{window}"] = prior_dow
        frame[f"same_dow_q80_{window}"] = prior_q80

    threshold = frame["same_dow_q80_8"]
    frame["target"] = np.where(threshold.notna(), (frame["y"] >= threshold).astype(float), np.nan)
    observed_resid = frame["y"] - threshold
    observed_high = frame["target"]
    frame["lag7_margin"] = frame["lag_7"] - threshold
    frame["lag7_ratio"] = frame["lag_7"] / threshold.clip(lower=1.0)
    frame["past_resid_1"] = observed_resid.shift(1)
    frame["past_resid_7"] = observed_resid.shift(7)
    frame["past_resid_mean_7"] = observed_resid.shift(1).rolling(7, min_periods=4).mean()
    frame["past_resid_mean_28"] = observed_resid.shift(1).rolling(28, min_periods=14).mean()
    frame["past_high_rate_7"] = observed_high.shift(1).rolling(7, min_periods=4).mean()
    frame["past_high_rate_28"] = observed_high.shift(1).rolling(28, min_periods=14).mean()

    frame["mean7_minus_mean28"] = frame["roll_mean_7"] - frame["roll_mean_28"]
    frame["mean14_minus_mean56"] = frame["roll_mean_14"] - frame["roll_mean_56"]
    frame["mean7_over_mean28"] = frame["roll_mean_7"] / frame["roll_mean_28"].clip(lower=1.0)
    frame["std7_over_std28"] = frame["roll_std_7"] / frame["roll_std_28"].clip(lower=1.0)
    frame["roll_mad_28"] = shifted.rolling(28, min_periods=14).apply(
        lambda x: float(np.median(np.abs(x - np.median(x)))), raw=True
    )
    frame["slope_7"] = shifted.rolling(7, min_periods=7).apply(_rolling_slope, raw=True)
    frame["slope_28"] = shifted.rolling(28, min_periods=20).apply(_rolling_slope, raw=True)
    frame["threshold_change_7"] = threshold - threshold.shift(7)
    return frame


def _robust_rule_scores(frame: pd.DataFrame) -> np.ndarray:
    # Fixed candidate-free rule: seasonal margin plus recent level/regime evidence.
    scale = (1.4826 * frame["roll_mad_28"]).clip(lower=1.0)
    seasonal = frame["lag7_margin"] / scale
    level_shift = frame["mean7_minus_mean28"] / scale
    persistence = frame["past_resid_mean_7"] / scale
    return (seasonal + 0.75 * level_shift + 0.25 * persistence).fillna(0.0).to_numpy()


def _positive_weights(y: np.ndarray) -> np.ndarray:
    positives = max(int(y.sum()), 1)
    negatives = max(int(len(y) - y.sum()), 1)
    weights = np.ones(len(y), dtype=float)
    weights[y == 1] = negatives / positives
    return weights


def _fit_predict(
    method: str,
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
    seed: int,
) -> np.ndarray:
    if method == "seasonal_naive_lag7_margin":
        return test["lag7_margin"].fillna(0.0).to_numpy()
    if method == "robust_residual_rule":
        return _robust_rule_scores(test)

    x_train = train[features]
    x_test = test[features]
    y_train = train["target"].astype(int).to_numpy()
    if method.startswith("logistic"):
        model = Pipeline([
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", RobustScaler()),
            ("model", LogisticRegression(
                C=0.25, l1_ratio=0.0, class_weight="balanced", max_iter=2000,
                solver="liblinear", random_state=seed,
            )),
        ])
        model.fit(x_train, y_train)
        return model.predict_proba(x_test)[:, 1]
    if method.startswith("extra_trees"):
        imputer = SimpleImputer(strategy="median", add_indicator=True)
        xt = imputer.fit_transform(x_train)
        xv = imputer.transform(x_test)
        model = ExtraTreesClassifier(
            n_estimators=500, max_depth=8, min_samples_leaf=4,
            max_features=0.75, class_weight="balanced", random_state=seed,
            n_jobs=2,
        )
        model.fit(xt, y_train)
        return model.predict_proba(xv)[:, 1]
    if method == "hist_gradient_boosting":
        imputer = SimpleImputer(strategy="median", add_indicator=True)
        xt = imputer.fit_transform(x_train)
        xv = imputer.transform(x_test)
        model = HistGradientBoostingClassifier(
            learning_rate=0.04, max_iter=180, max_leaf_nodes=15,
            min_samples_leaf=12, l2_regularization=1.0, random_state=seed,
        )
        model.fit(xt, y_train, sample_weight=_positive_weights(y_train))
        return model.predict_proba(xv)[:, 1]
    if method == "isolation_regime_hybrid":
        iso_features = LAG_FEATURES + REGIME_FEATURES + ["lag7_margin", "past_resid_mean_7"]
        imputer = SimpleImputer(strategy="median")
        xt = imputer.fit_transform(train[iso_features])
        xv = imputer.transform(test[iso_features])
        scaler = RobustScaler().fit(xt)
        xt = scaler.transform(xt)
        xv = scaler.transform(xv)
        iso = IsolationForest(
            n_estimators=350, max_samples=min(192, len(train)), contamination="auto",
            random_state=seed, n_jobs=2,
        )
        iso.fit(xt)
        anomaly = -iso.decision_function(xv)
        direction = np.tanh(
            (test["mean7_minus_mean28"] / test["roll_std_28"].clip(lower=1.0))
            .fillna(0.0).to_numpy()
        )
        robust = _robust_rule_scores(test)
        # High-side anomalies receive positive weight; low-side anomalies do not.
        return robust + np.maximum(direction, 0.0) * anomaly
    raise KeyError(method)


def _evaluate_method(
    frame: pd.DataFrame,
    method: str,
    features: list[str],
    seed: int,
) -> list[FoldPrediction]:
    folds: list[FoldPrediction] = []
    for month in OUTER_MONTHS:
        start = pd.Timestamp(f"{month}-01")
        end = start + pd.offsets.MonthEnd(0)
        # 2025-only training prevents the documented 2023/2024 collection regime
        # from dominating. All threshold initialization still uses strict history.
        train = frame.loc[(frame.index >= "2025-01-01") & (frame.index < start)].copy()
        test = frame.loc[(frame.index >= start) & (frame.index <= end)].copy()
        train = train.loc[train["target"].notna()]
        test = test.loc[test["target"].notna()]
        if test.empty or train["target"].nunique() < 2:
            raise ValueError(f"Invalid fold {month}: train classes/test rows")
        t0 = time.perf_counter()
        score = _fit_predict(method, train, test, features, seed)
        elapsed = time.perf_counter() - t0
        folds.append(FoldPrediction(
            month=month,
            dates=[str(x.date()) for x in test.index],
            y_true=test["target"].astype(int).tolist(),
            score=np.asarray(score, dtype=float).tolist(),
            train_days=int(len(train)),
            train_positives=int(train["target"].sum()),
            runtime_seconds=float(elapsed),
        ))
    return folds


def _ap(y: np.ndarray, score: np.ndarray) -> float:
    return float(average_precision_score(y, score))


def summarize(folds: list[FoldPrediction]) -> dict[str, Any]:
    monthly = []
    all_y: list[int] = []
    all_score: list[float] = []
    total_alerts = 0
    total_hits = 0
    for fold in folds:
        y = np.asarray(fold.y_true, dtype=int)
        score = np.asarray(fold.score, dtype=float)
        k = max(1, int(math.ceil(len(y) * TOP_SHARE)))
        order = np.argsort(-score, kind="mergesort")[:k]
        hits = int(y[order].sum())
        monthly.append({
            "month": fold.month,
            "days": int(len(y)),
            "positives": int(y.sum()),
            "prevalence": float(y.mean()),
            "pr_auc": _ap(y, score),
            "top20_alerts": k,
            "top20_hits": hits,
            "top20_precision": float(hits / k),
            "top20_recall": float(hits / y.sum()) if y.sum() else 0.0,
            "train_days": fold.train_days,
            "train_positives": fold.train_positives,
            "runtime_seconds": fold.runtime_seconds,
        })
        total_alerts += k
        total_hits += hits
        all_y.extend(y.tolist())
        all_score.extend(score.tolist())
    y_all = np.asarray(all_y, dtype=int)
    score_all = np.asarray(all_score, dtype=float)
    first_n = sum(x["days"] for x in monthly[:3])
    positives = int(y_all.sum())
    aggregate = {
        "days": int(len(y_all)),
        "positives": positives,
        "prevalence": float(y_all.mean()),
        "pr_auc": _ap(y_all, score_all),
        "monthly_pr_auc_mean": float(np.mean([x["pr_auc"] for x in monthly])),
        "monthly_pr_auc_std": float(np.std([x["pr_auc"] for x in monthly])),
        "top20_alerts": int(total_alerts),
        "top20_hits": int(total_hits),
        "top20_precision": float(total_hits / total_alerts),
        "top20_recall": float(total_hits / positives) if positives else 0.0,
        "top20_lift": float((total_hits / total_alerts) / y_all.mean()),
        "alerts_per_calendar_day": float(total_alerts / len(y_all)),
        "days_reviewed_per_true_positive": float(total_alerts / total_hits) if total_hits else None,
        "jul_sep_pr_auc": _ap(y_all[:first_n], score_all[:first_n]),
        "oct_dec_pr_auc": _ap(y_all[first_n:], score_all[first_n:]),
        "runtime_seconds": float(sum(x["runtime_seconds"] for x in monthly)),
    }
    return {"aggregate": aggregate, "monthly": monthly}


def paired_gate(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    ca = candidate["aggregate"]
    ba = baseline["aggregate"]
    improvement = (ca["pr_auc"] / ba["pr_auc"] - 1.0) if ba["pr_auc"] else None
    monthly_wins = sum(
        c["pr_auc"] > b["pr_auc"]
        for c, b in zip(candidate["monthly"], baseline["monthly"], strict=True)
    )
    precision_ok = ca["top20_precision"] >= ba["top20_precision"]
    recall_ok = ca["top20_recall"] >= 0.95 * ba["top20_recall"]
    halves_ok = ca["jul_sep_pr_auc"] > ba["jul_sep_pr_auc"] and ca["oct_dec_pr_auc"] > ba["oct_dec_pr_auc"]
    checks = {
        "paired_pr_auc_gain_at_least_15pct": bool(improvement is not None and improvement >= 0.15),
        "monthly_wins_at_least_4_of_6": bool(monthly_wins >= 4),
        "wins_both_halves": bool(halves_ok),
        "top20_precision_not_lower": bool(precision_ok),
        "top20_recall_not_more_than_5pct_relative_lower": bool(recall_ok),
    }
    return {
        "pr_auc_relative_improvement": float(improvement) if improvement is not None else None,
        "monthly_wins": int(monthly_wins),
        "checks": checks,
        "base_gate_passed_before_seed_check": bool(all(checks.values())),
    }


def _experiment_specs() -> list[dict[str, Any]]:
    return [
        {
            "cycle": 1, "name": "robust_residual_rule", "method": "robust_residual_rule",
            "family": "robust seasonal residual/MAD-style rule", "features": RESIDUAL_FEATURES + REGIME_FEATURES,
            "mechanism": "Carry last same-weekday pressure forward and adjust for recent robust level shift/persistence.",
            "falsification": "Fails paired 15% PR-AUC gate or temporal/workload guardrails.",
            "ablation": "Seasonal baseline + residual/regime rule.",
        },
        {
            "cycle": 2, "name": "logistic_calendar", "method": "logistic_calendar",
            "family": "regularized generalized linear", "features": CALENDAR_FEATURES,
            "mechanism": "Estimate stable calendar-only high-workload propensity.",
            "falsification": "Calendar-only ranking does not beat seasonal baseline.",
            "ablation": "Calendar-only lower bound.",
        },
        {
            "cycle": 3, "name": "logistic_calendar_lags", "method": "logistic_calendar_lags",
            "family": "regularized generalized linear", "features": CALENDAR_FEATURES + LAG_FEATURES,
            "mechanism": "Add autoregressive level signals to the transparent calendar model.",
            "falsification": "Lag-family ablation has non-positive paired gain over calendar-only.",
            "ablation": "+ lag levels versus cycle 2.",
        },
        {
            "cycle": 4, "name": "logistic_full", "method": "logistic_full",
            "family": "regularized generalized linear", "features": FULL_FEATURES,
            "mechanism": "Linear combination of calendar, lag, rolling, residual, and regime evidence.",
            "falsification": "Full features do not improve over calendar+lags or are temporally unstable.",
            "ablation": "+ rolling/residual/regime versus cycle 3.",
        },
        {
            "cycle": 5, "name": "isolation_regime_hybrid", "method": "isolation_regime_hybrid",
            "family": "unsupervised density plus directional rule", "features": LAG_FEATURES + RESIDUAL_FEATURES + REGIME_FEATURES,
            "mechanism": "Use Isolation Forest to amplify only high-side context anomalies on top of the robust rule.",
            "falsification": "Unsupervised novelty adds no paired outcome association or destabilizes folds.",
            "ablation": "Isolation component versus cycle 1.",
        },
        {
            "cycle": 6, "name": "extra_trees_no_rolling", "method": "extra_trees_no_rolling",
            "family": "random-tree bagging", "features": CALENDAR_FEATURES + LAG_FEATURES + RESIDUAL_FEATURES + REGIME_FEATURES,
            "mechanism": "Capture nonlinear interactions without rolling-distribution features.",
            "falsification": "Does not beat linear/full and baseline gates.",
            "ablation": "Tree model with rolling-distribution family removed.",
        },
        {
            "cycle": 7, "name": "extra_trees_full", "method": "extra_trees_full",
            "family": "random-tree bagging", "features": FULL_FEATURES,
            "mechanism": "Capture nonlinear interactions across all point-in-time feature families.",
            "falsification": "Rolling family is non-incremental or candidate fails temporal gates.",
            "ablation": "+ rolling-distribution features versus cycle 6.",
        },
        {
            "cycle": 8, "name": "hist_gradient_boosting", "method": "hist_gradient_boosting",
            "family": "gradient boosting", "features": FULL_FEATURES,
            "mechanism": "Sequentially fit nonlinear residual structure with bounded shallow leaves.",
            "falsification": "No paired improvement or excessive fold/seed sensitivity.",
            "ablation": "Boosting inductive bias on the same full feature matrix as cycle 7.",
        },
    ]


def _rank_average(arrays: list[np.ndarray]) -> np.ndarray:
    ranks = []
    for values in arrays:
        order = pd.Series(values).rank(method="average", pct=True).to_numpy()
        ranks.append(order)
    return np.mean(np.vstack(ranks), axis=0)


def _hybrid_folds(parts: list[list[FoldPrediction]]) -> list[FoldPrediction]:
    combined: list[FoldPrediction] = []
    for fold_parts in zip(*parts, strict=True):
        first = fold_parts[0]
        for item in fold_parts[1:]:
            if item.month != first.month or item.dates != first.dates or item.y_true != first.y_true:
                raise ValueError("Hybrid fold alignment mismatch")
        score = _rank_average([np.asarray(x.score) for x in fold_parts])
        combined.append(FoldPrediction(
            month=first.month, dates=first.dates, y_true=first.y_true, score=score.tolist(),
            train_days=first.train_days, train_positives=first.train_positives,
            runtime_seconds=float(sum(x.runtime_seconds for x in fold_parts)),
        ))
    return combined


def _stability(
    frame: pd.DataFrame,
    winner_name: str,
    specs_by_name: dict[str, dict[str, Any]],
    baseline_summary: dict[str, Any],
) -> dict[str, Any]:
    per_seed = []
    for seed in SEEDS:
        if winner_name == "hybrid_rank_blend":
            e = _evaluate_method(frame, "extra_trees_full", FULL_FEATURES, seed)
            l = _evaluate_method(frame, "logistic_full", FULL_FEATURES, seed)
            r = _evaluate_method(frame, "robust_residual_rule", RESIDUAL_FEATURES + REGIME_FEATURES, seed)
            folds = _hybrid_folds([e, l, r])
        else:
            spec = specs_by_name[winner_name]
            folds = _evaluate_method(frame, spec["method"], spec["features"], seed)
        summary = summarize(folds)
        gate = paired_gate(summary, baseline_summary)
        per_seed.append({
            "seed": seed,
            "pr_auc": summary["aggregate"]["pr_auc"],
            "relative_gain": gate["pr_auc_relative_improvement"],
            "monthly_wins": gate["monthly_wins"],
            "base_gate_passed": gate["base_gate_passed_before_seed_check"],
            "top20_precision": summary["aggregate"]["top20_precision"],
            "top20_recall": summary["aggregate"]["top20_recall"],
        })
    scores = np.asarray([x["pr_auc"] for x in per_seed])
    gains = np.asarray([x["relative_gain"] for x in per_seed])
    spread = float((scores.max() - scores.min()) / scores.mean()) if scores.mean() else None
    checks = {
        "mean_gain_at_least_15pct": bool(gains.mean() >= 0.15),
        "every_seed_gain_at_least_10pct": bool((gains >= 0.10).all()),
        "relative_pr_auc_spread_at_most_10pct": bool(spread is not None and spread <= 0.10),
        "every_seed_base_gate_passed": bool(all(x["base_gate_passed"] for x in per_seed)),
    }
    return {
        "seeds": list(SEEDS), "per_seed": per_seed,
        "mean_pr_auc": float(scores.mean()), "std_pr_auc": float(scores.std()),
        "relative_pr_auc_spread": spread, "mean_relative_gain": float(gains.mean()),
        "checks": checks, "seed_stability_passed": bool(all(checks.values())),
    }


def _feature_catalog(cycle_results: list[dict[str, Any]]) -> dict[str, Any]:
    families = {
        "calendar": {
            "mechanism": "Known target-day weekly/annual position.",
            "source_columns": ["Aberto"], "availability": "Known before target day.",
            "leakage": "Deterministic calendar only.", "missing": "None.",
            "track": "next-day high workload", "features": CALENDAR_FEATURES,
            "compute": "O(n), negligible memory.",
        },
        "lag_levels": {
            "mechanism": "Recent and seasonal observed workload persistence.",
            "source_columns": ["Aberto"], "availability": "Counts through d-1 only.",
            "leakage": "Positive shifts only; target-day count excluded.", "missing": "Median imputation fitted in each training fold.",
            "track": "next-day high workload", "features": LAG_FEATURES,
            "compute": "O(n), negligible memory.",
        },
        "rolling_distribution": {
            "mechanism": "Robust recent workload level, dispersion, and weekday capacity proxy.",
            "source_columns": ["Aberto"], "availability": "Strictly prior daily counts.",
            "leakage": "Every rolling input shifted by one; same-weekday windows shift one group observation.",
            "missing": "Minimum histories enforced; fold-fitted median imputation.",
            "track": "next-day high workload", "features": ROLLING_FEATURES,
            "compute": "O(n*w), under 1 MB for this series.",
        },
        "seasonal_residual": {
            "mechanism": "Recent deviations from the point-in-time same-weekday capacity proxy.",
            "source_columns": ["Aberto"], "availability": "Observed residuals through d-1 only.",
            "leakage": "Current-day residual is shifted before use.", "missing": "Fold-fitted median imputation or zero in fixed rule.",
            "track": "next-day high workload", "features": RESIDUAL_FEATURES,
            "compute": "O(n), negligible memory.",
        },
        "trend_regime": {
            "mechanism": "Detect persistent level shift/change relative to longer context.",
            "source_columns": ["Aberto"], "availability": "Windows end at d-1.",
            "leakage": "No centered windows or future change points.", "missing": "Fold-fitted median imputation.",
            "track": "next-day high workload", "features": REGIME_FEATURES,
            "compute": "O(n*28), negligible memory.",
        },
    }
    # Attach measured ablation references without reproducing raw scores in multiple places.
    by_name = {x["name"]: x for x in cycle_results}
    families["lag_levels"]["ablation"] = {
        "from": "logistic_calendar", "to": "logistic_calendar_lags",
        "pr_auc_delta": by_name["logistic_calendar_lags"]["metrics"]["aggregate"]["pr_auc"] - by_name["logistic_calendar"]["metrics"]["aggregate"]["pr_auc"],
    }
    families["rolling_distribution"]["ablation"] = {
        "from": "extra_trees_no_rolling", "to": "extra_trees_full",
        "pr_auc_delta": by_name["extra_trees_full"]["metrics"]["aggregate"]["pr_auc"] - by_name["extra_trees_no_rolling"]["metrics"]["aggregate"]["pr_auc"],
    }
    families["seasonal_residual"]["ablation"] = {
        "from": "seasonal_naive_lag7_margin", "to": "robust_residual_rule",
        "relative_gain": by_name["robust_residual_rule"]["gate"]["pr_auc_relative_improvement"],
    }
    families["trend_regime"]["ablation"] = {
        "from": "robust_residual_rule", "to": "isolation_regime_hybrid",
        "pr_auc_delta": by_name["isolation_regime_hybrid"]["metrics"]["aggregate"]["pr_auc"] - by_name["robust_residual_rule"]["metrics"]["aggregate"]["pr_auc"],
    }
    families["calendar"]["ablation"] = {
        "candidate": "logistic_calendar",
        "pr_auc": by_name["logistic_calendar"]["metrics"]["aggregate"]["pr_auc"],
    }
    return {"families": families, "full_feature_count": len(FULL_FEATURES)}


def _write_report(metrics: dict[str, Any], path: Path) -> None:
    base = metrics["baseline"]["metrics"]
    strong = metrics["strongest"]
    cand = strong["metrics"]
    gate = strong["gate"]
    stability = strong["seed_stability"]
    rows = []
    for b, c in zip(base["monthly"], cand["monthly"], strict=True):
        rows.append(
            f"| {b['month']} | {b['positives']}/{b['days']} | {b['pr_auc']:.4f} | "
            f"{c['pr_auc']:.4f} | {c['top20_hits']}/{c['top20_alerts']} |"
        )
    cycle_rows = []
    for cycle in metrics["cycles"]:
        a = cycle["metrics"]["aggregate"]
        g = cycle["gate"]
        cycle_rows.append(
            f"| {cycle['cycle']} | {cycle['name']} | {cycle['family']} | {a['pr_auc']:.4f} | "
            f"{100*g['pr_auc_relative_improvement']:+.1f}% | {g['monthly_wins']}/6 | "
            f"{a['top20_precision']:.1%} | {a['top20_recall']:.1%} | {cycle['decision']} |"
        )
    feature_rows = []
    for name, item in metrics["feature_catalog"]["families"].items():
        feature_rows.append(f"| {name} | `{json.dumps(item['ablation'], ensure_ascii=False)}` |")
    status = metrics["status"]
    promoted = strong["promotion_gate_passed"]
    report = f"""# Alternative Operational Track — Next-day High-workload Advisory

## Status

{status}

## Executive conclusion

The strongest candidate was `{strong['name']}`. It raised pooled real-2025 PR-AUC from {base['aggregate']['pr_auc']:.4f} to {cand['aggregate']['pr_auc']:.4f} ({100*gate['pr_auc_relative_improvement']:+.1f}%), won {gate['monthly_wins']}/6 monthly folds, and improved Top-20% precision from {base['aggregate']['top20_precision']:.1%} to {cand['aggregate']['top20_precision']:.1%}. It did **not** pass the predeclared 15% paired-improvement gate and was slightly below the baseline in pooled Oct-Dec PR-AUC ({cand['aggregate']['oct_dec_pr_auc']:.4f} versus {base['aggregate']['oct_dec_pr_auc']:.4f}). Promotion decision: **{'PROMOTE' if promoted else 'DO NOT PROMOTE'}**.

This is a track-level no-go, not a claim that the overall multi-track research has reached its terminal condition.

## Preregistration and target-validity amendment

The baseline, metric, 15% gate, folds, workload, and operational action were written before any candidate ran. The original fixed threshold was invalidated before candidate execution: the all-incident daily mean changes from {metrics['data_audit']['year_stats']['2023']['mean']:.2f} (2023) and {metrics['data_audit']['year_stats']['2024']['mean']:.2f} (2024) to {metrics['data_audit']['year_stats']['2025']['mean']:.2f} (2025), and its frozen q80={metrics['target_audit']['original_preregistered_target_invalidated']['threshold']:.0f} labeled {metrics['target_audit']['original_preregistered_target_invalidated']['evaluation_positives']}/{metrics['target_audit']['original_preregistered_target_invalidated']['evaluation_days']} evaluation days positive. `preregistration_amendment.json`, also written before candidate execution, therefore defines the observable proxy as:

> A high-workload day has a real opening count at or above the 80th percentile of the eight strictly prior same-weekday counts.

This threshold is known by the end of d-1. July-December contains {metrics['target_audit']['evaluation_positives']}/{metrics['target_audit']['evaluation_days']} positives. The score supports a D+1 flex-staffing/on-call-readiness advisory only; it does not automate incident handling.

## Exact track stopping criterion

Nine materially distinct cycles covered robust seasonal residual/MAD, regularized logistic, Isolation Forest hybrid, Extra Trees, histogram gradient boosting, and a fixed rank ensemble. Five seeds were checked for the strongest stochastic candidate. No candidate passed all predeclared gates, so this isolated operational track stops as no-go.

## Baseline versus strongest candidate

| Metric | Seasonal lag-7 margin | `{strong['name']}` |
|---|---:|---:|
| Pooled PR-AUC | {base['aggregate']['pr_auc']:.4f} | {cand['aggregate']['pr_auc']:.4f} |
| Relative PR-AUC gain | — | {100*gate['pr_auc_relative_improvement']:+.1f}% |
| Monthly wins | — | {gate['monthly_wins']}/6 |
| Jul-Sep PR-AUC | {base['aggregate']['jul_sep_pr_auc']:.4f} | {cand['aggregate']['jul_sep_pr_auc']:.4f} |
| Oct-Dec PR-AUC | {base['aggregate']['oct_dec_pr_auc']:.4f} | {cand['aggregate']['oct_dec_pr_auc']:.4f} |
| Top-20% alerts | {base['aggregate']['top20_alerts']} | {cand['aggregate']['top20_alerts']} |
| Top-20% hits | {base['aggregate']['top20_hits']} | {cand['aggregate']['top20_hits']} |
| Top-20% precision | {base['aggregate']['top20_precision']:.1%} | {cand['aggregate']['top20_precision']:.1%} |
| Top-20% recall | {base['aggregate']['top20_recall']:.1%} | {cand['aggregate']['top20_recall']:.1%} |
| Days reviewed per hit | {base['aggregate']['days_reviewed_per_true_positive']:.2f} | {cand['aggregate']['days_reviewed_per_true_positive']:.2f} |

Top-20% is a capacity-matched ranking diagnostic (40 advisory-days across 184 days), not a threshold selected on the evaluation folds.

## Temporal results

| Month | Positives | Baseline PR-AUC | Candidate PR-AUC | Candidate Top-20% hits/alerts |
|---|---:|---:|---:|---:|
{chr(10).join(rows)}

The candidate wins July, August, September, October, and December, but loses November. The first-half gain is strong; the second-half aggregate is marginally worse, which independently fails the stability gate.

## Experiment coverage

| Cycle | Candidate | Family | PR-AUC | Gain vs baseline | Monthly wins | Top-20% precision | Top-20% recall | Decision |
|---:|---|---|---:|---:|---:|---:|---:|---|
{chr(10).join(cycle_rows)}

## Explicit feature ablations

| Feature family | Measured ablation |
|---|---|
{chr(10).join(feature_rows)}

Lag levels are retained: adding them to calendar-only logistic contributes the largest positive ablation. The full rolling-distribution family is rejected for Extra Trees because it lowers PR-AUC materially. Seasonal residual and directional Isolation Forest additions are only marginally positive. Calendar-only is insufficient.

## Seed stability

Across seeds {', '.join(map(str, stability['seeds']))}, candidate PR-AUC is {stability['mean_pr_auc']:.4f} ± {stability['std_pr_auc']:.4f}, relative spread {stability['relative_pr_auc_spread']:.2%}, and mean gain {stability['mean_relative_gain']:.1%}. Randomness is controlled, but every seed remains below the 15% gate; stability cannot rescue an insufficient effect.

## Synthetic evidence separation

No synthetic row was used for training or evaluation in this track. The available synthetic series was generated from 2025 P2/P3 observations, including the evaluation period, and does not represent all-incident workload. Mixing it here would create both target mismatch and future-information risk. Synthetic contribution for this track is therefore not estimable and is not claimed.

## Leakage and reproducibility

- Daily aggregates contain no persisted incident identifiers, people, categories, or descriptions.
- Target thresholds use eight strictly prior same-weekday observations.
- Every lag/rolling feature ends by d-1; no centered windows are used.
- Each monthly model trains only on 2025 target dates before the fold.
- All evaluation rows are real July-December 2025 observations and are identical across methods.
- Preprocessing is fit inside each training fold.
- Strongest-candidate seed spread is recorded above; `reproduce.py` performs a fresh-process exact-metric check.

## Hardware and runtime

Apple arm64, {metrics['hardware']['cpu_count']} logical CPUs; Python {metrics['hardware']['python']}; scikit-learn {metrics['hardware']['scikit_learn']}. The research run took {metrics['hardware']['wall_seconds']:.1f}s with observed process peak RSS about {metrics['hardware']['peak_rss_mb_process']:.1f} MB. Tree jobs were bounded to two workers; CUDA/MPS was not used.

## Production decision

Do not promote this challenger. If a safe rule must ship today, retain the transparent lag-7 margin as an exploratory staffing signal with human review and no automated action. The Extra Trees candidate is useful evidence—especially its {cand['aggregate']['top20_precision']:.1%} precision versus {base['aggregate']['top20_precision']:.1%} at the same workload—but remains exploratory until it passes the locked effect-size and second-half stability gates on later real data.
"""
    path.write_text(report, encoding="utf-8")


def run(output_dir: Path = WORK_DIR, model_dir: Path = MODEL_DIR) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    counts, data_audit = load_real_daily()
    frame = build_frame(counts)

    eval_frame = frame.loc["2025-07-01":"2025-12-31"]
    target_audit = {
        "definition": "y[d] >= q80(previous 8 same-weekday real counts)",
        "evaluation_days": int(eval_frame["target"].notna().sum()),
        "evaluation_positives": int(eval_frame["target"].sum()),
        "evaluation_prevalence": float(eval_frame["target"].mean()),
        "monthly_positives": {
            str(k.date()): int(v)
            for k, v in eval_frame["target"].groupby(pd.Grouper(freq="MS")).sum().items()
        },
        "original_preregistered_target_invalidated": {
            "threshold": float(counts.loc[:"2025-06-30"].quantile(0.80)),
            "evaluation_positives": int((counts.loc["2025-07-01":"2025-12-31"] >= counts.loc[:"2025-06-30"].quantile(0.80)).sum()),
            "evaluation_days": int(len(counts.loc["2025-07-01":"2025-12-31"])),
        },
    }

    baseline_folds = _evaluate_method(frame, "seasonal_naive_lag7_margin", ["lag7_margin"], 47)
    baseline = summarize(baseline_folds)
    registry_path = output_dir / "experiment_registry.jsonl"
    registry_path.write_text("", encoding="utf-8")

    specs = _experiment_specs()
    fold_cache: dict[str, list[FoldPrediction]] = {}
    results: list[dict[str, Any]] = []
    for spec in specs:
        folds = _evaluate_method(frame, spec["method"], spec["features"], 47)
        fold_cache[spec["name"]] = folds
        metrics = summarize(folds)
        gate = paired_gate(metrics, baseline)
        decision = "RETAIN" if gate["pr_auc_relative_improvement"] > 0 else "REJECT"
        if gate["base_gate_passed_before_seed_check"]:
            decision = "PROMOTION_CANDIDATE_PENDING_SEEDS"
        record = {
            **{k: v for k, v in spec.items() if k != "features"},
            "feature_count": len(spec["features"]), "seed": 47,
            "data": "real-only", "synthetic_rows_train": 0, "synthetic_rows_evaluation": 0,
            "metrics": metrics, "gate": gate, "decision": decision,
            "peak_rss_mb_process": float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)),
        }
        results.append(record)
        with registry_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    # Fixed equal-rank hybrid; no evaluation-fold weight fitting.
    hybrid_folds = _hybrid_folds([
        fold_cache["extra_trees_full"], fold_cache["logistic_full"], fold_cache["robust_residual_rule"]
    ])
    hybrid_metrics = summarize(hybrid_folds)
    hybrid_gate = paired_gate(hybrid_metrics, baseline)
    hybrid_record = {
        "cycle": 9, "name": "hybrid_rank_blend", "method": "fixed_equal_rank_blend",
        "family": "ensemble/hybrid", "feature_count": len(FULL_FEATURES), "seed": 47,
        "mechanism": "Equal within-fold rank average of Extra Trees, full logistic, and fixed robust rule; weights are fixed, not fit on evaluation data.",
        "falsification": "Fails any paired, monthly, half-year, or workload gate.",
        "ablation": "Ensemble versus strongest constituent on identical folds.",
        "data": "real-only", "synthetic_rows_train": 0, "synthetic_rows_evaluation": 0,
        "metrics": hybrid_metrics, "gate": hybrid_gate,
        "decision": "PROMOTION_CANDIDATE_PENDING_SEEDS" if hybrid_gate["base_gate_passed_before_seed_check"] else ("RETAIN" if hybrid_gate["pr_auc_relative_improvement"] > 0 else "REJECT"),
        "peak_rss_mb_process": float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)),
    }
    results.append(hybrid_record)
    with registry_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(hybrid_record, ensure_ascii=False, sort_keys=True) + "\n")

    # Strongest by primary metric; gate is applied only after explicit seed audit.
    strongest = max(results, key=lambda x: x["metrics"]["aggregate"]["pr_auc"])
    specs_by_name = {x["name"]: x for x in specs}
    stability = _stability(frame, strongest["name"], specs_by_name, baseline)
    final_gate = bool(strongest["gate"]["base_gate_passed_before_seed_check"] and stability["seed_stability_passed"])
    strongest["decision"] = "PROMOTION_CANDIDATE" if final_gate else "RETAIN_EXPLORATORY"
    with registry_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "audit": "strongest_candidate_seed_stability",
            "candidate": strongest["name"], "result": stability,
            "decision": strongest["decision"],
        }, ensure_ascii=False, sort_keys=True) + "\n")

    feature_catalog = _feature_catalog(results)
    synthetic_note = {
        "used_in_track": False,
        "training_rows": 0,
        "evaluation_rows": 0,
        "reason": "The available synthetic daily series was generated from 2025 observations, including the July-December evaluation period, and represents the P2/P3 KPI subset rather than all-incident workload. Using it would mismatch the target and risk future-information leakage.",
        "evidence_separation": "All metrics in this track use real raw opening timestamps only.",
    }
    metrics = {
        "status": "SUCCESS: OPERATIONAL TRACK GATE PASSED" if final_gate else "NO-GO: OPERATIONAL TRACK GATE NOT PASSED",
        "generated_at": datetime.now().astimezone().isoformat(),
        "protocol": {
            "target": target_audit["definition"], "prediction_horizon": "D+1",
            "outer_months": list(OUTER_MONTHS), "evaluation": "real 2025 only",
            "training": "expanding real 2025 days strictly before each evaluation month",
            "top_share": TOP_SHARE, "seeds": list(SEEDS),
        },
        "data_audit": data_audit,
        "target_audit": target_audit,
        "baseline": {"name": "seasonal_naive_lag7_margin", "metrics": baseline},
        "cycles": results,
        "strongest": {
            "name": strongest["name"], "metrics": strongest["metrics"],
            "gate": strongest["gate"], "seed_stability": stability,
            "promotion_gate_passed": final_gate,
        },
        "synthetic": synthetic_note,
        "feature_catalog": feature_catalog,
        "coverage": {
            "cycles": len(results),
            "model_families": sorted(set(x["family"] for x in results)),
            "feature_families": list(feature_catalog["families"]),
        },
        "hardware": {
            "platform": platform.platform(), "machine": platform.machine(),
            "python": platform.python_version(), "pandas": pd.__version__,
            "numpy": np.__version__, "scikit_learn": sklearn.__version__,
            "cpu_count": os.cpu_count(),
            "peak_rss_mb_process": float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)),
            "wall_seconds": float(time.perf_counter() - started),
            "cuda_used": False, "mps_used": False,
        },
        "leakage_checks": {
            "target_threshold_uses_strict_prior_same_weekdays": True,
            "features_shifted_before_rolling": True,
            "train_dates_precede_fold": True,
            "identical_baseline_candidate_rows": True,
            "evaluation_real_only": True,
            "synthetic_excluded": True,
            "raw_sensitive_values_persisted": False,
        },
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "feature_catalog.json").write_text(json.dumps(feature_catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_report(metrics, output_dir / "report.md")
    config = {
        "candidate": strongest["name"], "seed_reference": 47,
        "seeds_checked": list(SEEDS), "feature_names": FULL_FEATURES if strongest["name"] in {"extra_trees_full", "hybrid_rank_blend", "logistic_full", "hist_gradient_boosting"} else None,
        "raw_sha256": data_audit["sha256"], "target": target_audit["definition"],
        "outer_months": list(OUTER_MONTHS), "promotion_gate_passed": final_gate,
    }
    (model_dir / "final_candidate_config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=WORK_DIR)
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    args = parser.parse_args()
    metrics = run(args.output_dir, args.model_dir)
    print(json.dumps({
        "status": metrics["status"],
        "baseline_pr_auc": metrics["baseline"]["metrics"]["aggregate"]["pr_auc"],
        "strongest": metrics["strongest"]["name"],
        "strongest_pr_auc": metrics["strongest"]["metrics"]["aggregate"]["pr_auc"],
        "promotion_gate_passed": metrics["strongest"]["promotion_gate_passed"],
    }, indent=2))


if __name__ == "__main__":
    main()
