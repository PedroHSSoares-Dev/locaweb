"""Closed-loop raw-data research for P2 OLA-risk prioritization.

The module is deliberately isolated from production code and outputs. It reads
the local ITSM workbook, creates only aggregate/anonymized reports, constructs
point-in-time features, and evaluates paired monthly walk-forward folds from
July through December 2025.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost as xgb
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = PROJECT_ROOT / "experiments" / "raw_opportunity_loop"
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "LW-DATASET.xlsx"
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "incidents_features.parquet"
CHAMPION_REPORT = PROJECT_ROOT / "outputs" / "experiments" / "xgboost_specialists.json"
MODEL_EXPERIMENT_DIR = PROJECT_ROOT / "models_saved" / "experiments" / "raw_opportunity_loop"

TARGET = "__target"
OPEN = "Aberto"
KNOWN = "__known_time"
PRIORITY = "Prioridade"
P2 = "2 - Alta"
P3 = "3 - Média"
MISSING = "__MISSING__"
OUTER_MONTHS = [pd.Period(f"2025-{month:02d}", freq="M") for month in range(7, 13)]
SEEDS = [11, 23, 42, 67, 101]
BASE_SEED = 42

LOCKED_XGB_PARAMS: dict[str, Any] = {
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
}

# The raw snapshot cannot prove that final assignment equals initial assignment.
SAFE_BASE_CATEGORICAL = ["Produto", "Categoria", "Subcategoria", "Aberto por"]
CHAMPION_CATEGORICAL = [*SAFE_BASE_CATEGORICAL, "Grupo designado"]

COLUMN_CLASSIFICATION: dict[str, tuple[str, str]] = {
    "Número": ("unusable or sensitive", "Unique incident identifier; no stable generalizable signal."),
    "Prioridade": ("available at incident opening", "Priority is required for OLA routing at opening."),
    "Produto": ("available at incident opening", "Opening classification; missingness is retained explicitly."),
    "Categoria": ("available at incident opening", "Opening classification; missingness is retained explicitly."),
    "Subcategoria": ("available at incident opening", "Opening classification; missingness is retained explicitly."),
    "Grupo designado": ("temporally uncertain", "Single snapshot cannot verify initial versus reassigned group."),
    "Item de configuração": ("available at incident opening", "Affected configuration item is captured on creation."),
    "Aberto": ("available at incident opening", "Scoring timestamp and calendar source."),
    "Resolvido": ("known only after the outcome", "Resolution timestamp occurs after opening."),
    "Encerrado": ("known only after the outcome", "Closure timestamp occurs after opening."),
    "Duração": ("direct target leakage", "Duration is known only after resolution and proxies OLA outcome."),
    "Código de fechamento": ("known only after the outcome", "Defined during closure."),
    "Descrição resumida": ("available at incident opening", "Opening text; used only in-memory with fold-fitted vectorization."),
    "Solução": ("known only after the outcome", "Recorded during resolution."),
    "Aberto por": ("available at incident opening", "Opening source is known when the record is created."),
    "Incidente Pai": ("temporally uncertain", "Parent linkage may be assigned after opening; audit trail absent."),
    "Status": ("known only after the outcome", "Snapshot status is a post-opening mutable state."),
    "Entrou para KPI?": ("temporally uncertain", "Used only to define the historical cohort, never as a feature."),
    "KPI Violado?": ("direct target leakage", "Business ground truth and prediction target."),
}


FAMILY_METADATA: dict[str, dict[str, Any]] = {
    "arrival_burst": {
        "mechanism": "Arrival bursts may overload triage before an incident is assigned.",
        "raw_columns": ["Aberto"],
        "availability": "Prior opening timestamps only.",
        "leakage_risk": "Exclude simultaneous/current arrivals with left-open search.",
        "segment": "P2 during bursty periods.",
        "falsification": "No positive paired PR-AUC delta and no Top-5% recall gain.",
    },
    "active_workload": {
        "mechanism": "Open workload at arrival may proxy queue pressure.",
        "raw_columns": ["Aberto", "Resolvido", "Encerrado", "Prioridade", "Produto"],
        "availability": "Uses prior incidents and whether each had ended by scoring time.",
        "leakage_risk": "Outcome timestamps only determine prior incident state; never current outcome.",
        "segment": "P2 arriving under elevated backlog.",
        "falsification": "No temporal gain or instability caused by closure-coverage regime.",
    },
    "recurrence": {
        "mechanism": "Rapid recurrence can identify correlated operational episodes.",
        "raw_columns": ["Aberto", "Produto", "Categoria", "Subcategoria", "Item de configuração", "Descrição resumida"],
        "availability": "Prior openings for the same safe key only.",
        "leakage_risk": "No future/current row in cumulative support.",
        "segment": "Repeated P2 patterns.",
        "falsification": "No paired PR-AUC/Top-5% improvement.",
    },
    "novelty_support": {
        "mechanism": "Rare or first-seen classifications may be harder to resolve inside OLA.",
        "raw_columns": ["Produto", "Categoria", "Subcategoria", "Item de configuração", "Descrição resumida", "Aberto"],
        "availability": "Cumulative support from prior openings.",
        "leakage_risk": "Future category frequencies excluded.",
        "segment": "Novel and low-support P2 records.",
        "falsification": "Ablation is neutral/negative across paired folds.",
    },
    "historical_outcomes": {
        "mechanism": "Previously resolved patterns may carry persistent OLA risk.",
        "raw_columns": ["KPI Violado?", "Resolvido", "Encerrado", "Produto", "Categoria", "Subcategoria"],
        "availability": "Only outcomes known before each new opening.",
        "leakage_risk": "Strict known-time event ordering and smoothing.",
        "segment": "Recurring P2 failure modes.",
        "falsification": "No operational lift after point-in-time restriction.",
    },
    "config_identity": {
        "mechanism": "Configuration-item identity/frequency may expose fragile assets.",
        "raw_columns": ["Item de configuração"],
        "availability": "Value known at opening; mappings fitted inside each fold.",
        "leakage_risk": "High cardinality and rare-level overfit.",
        "segment": "Repeated affected assets.",
        "falsification": "Temporal PR-AUC fails to improve or fold variance increases materially.",
    },
    "description_history": {
        "mechanism": "Exact alert summaries may recur with consistent operational risk.",
        "raw_columns": ["Descrição resumida"],
        "availability": "Opening text identity; no text leaves memory.",
        "leakage_risk": "Rare exact strings and sensitive content; only encoded aggregates retained.",
        "segment": "Repeated machine-generated alerts.",
        "falsification": "No paired gain or only one-fold win.",
    },
    "interactions": {
        "mechanism": "Supported classification combinations may be more informative than marginal levels.",
        "raw_columns": ["Produto", "Categoria", "Subcategoria", "Aberto por"],
        "availability": "Opening values; encoders trained per fold.",
        "leakage_risk": "Sparse combinations; smoothing and unknown buckets required.",
        "segment": "Specific P2 operational paths.",
        "falsification": "No incremental ablation value.",
    },
    "calendar_context": {
        "mechanism": "Minute, shift boundary and holiday proximity may proxy coverage constraints.",
        "raw_columns": ["Aberto"],
        "availability": "Deterministic at opening.",
        "leakage_risk": "None beyond fixed calendar definition.",
        "segment": "Off-hours and holiday-adjacent P2.",
        "falsification": "No temporal incremental value.",
    },
    "segmented_bursts": {
        "mechanism": "Local bursts within product/priority may matter more than global volume.",
        "raw_columns": ["Aberto", "Prioridade", "Produto", "Categoria"],
        "availability": "Prior openings only.",
        "leakage_risk": "Same-timestamp events excluded.",
        "segment": "Correlated P2 alert storms.",
        "falsification": "No gain over global burst features.",
    },
    "queue_growth": {
        "mechanism": "Acceleration in arrivals and net open-queue growth may precede violations.",
        "raw_columns": ["Aberto", "Resolvido", "Encerrado"],
        "availability": "Prior arrival/end event counts only.",
        "leakage_risk": "End events included only when they occurred before scoring.",
        "segment": "Rapidly deteriorating workload.",
        "falsification": "No paired operational improvement.",
    },
    "text_tfidf": {
        "mechanism": "Fold-fitted lexical patterns may generalize beyond exact description identity.",
        "raw_columns": ["Descrição resumida"],
        "availability": "Opening text; vocabulary fitted on training rows only.",
        "leakage_risk": "Sensitive tokens never persisted; vocabulary never reported.",
        "segment": "Machine-generated and templated P2 descriptions.",
        "falsification": "Blended ranking does not improve paired PR-AUC and Top-5% recall.",
    },
}


@dataclass
class DataBundle:
    raw: pd.DataFrame
    kpi: pd.DataFrame
    processed_min: pd.Timestamp


@dataclass
class FeatureStore:
    numeric: pd.DataFrame
    categorical: dict[str, pd.Series]
    descriptions: pd.Series
    family_numeric: dict[str, list[str]]
    family_categorical: dict[str, list[str]]


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating,)): return float(value)
    if isinstance(value, (np.bool_,)): return bool(value)
    if isinstance(value, (pd.Timestamp, pd.Period)): return str(value)
    if isinstance(value, Path): return str(value)
    if isinstance(value, float) and not math.isfinite(value): return None
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(_json_safe(value), handle, ensure_ascii=False, indent=2, allow_nan=False)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_data() -> DataBundle:
    raw = pd.read_excel(RAW_PATH)
    if list(raw.columns) != list(COLUMN_CLASSIFICATION):
        missing = sorted(set(COLUMN_CLASSIFICATION) - set(raw.columns))
        extra = sorted(set(raw.columns) - set(COLUMN_CLASSIFICATION))
        raise ValueError(f"Unexpected raw schema. missing={missing}, extra={extra}")
    raw = raw.copy()
    for column in [OPEN, "Resolvido", "Encerrado"]:
        raw[column] = pd.to_datetime(raw[column], errors="coerce")
    processed_min = pd.to_datetime(pd.read_parquet(PROCESSED_PATH, columns=["data_abertura"])["data_abertura"]).min()
    kpi = raw[
        (raw["Entrou para KPI?"] == "SIM") & raw[PRIORITY].isin([P2, P3])
    ].copy()
    kpi[TARGET] = (kpi["KPI Violado?"] == "SIM").astype(np.int8)
    kpi[KNOWN] = pd.concat([kpi["Resolvido"], kpi["Encerrado"]], axis=1).min(axis=1)
    kpi = kpi[kpi[OPEN] >= processed_min].sort_values(OPEN, kind="stable").reset_index(drop=True)
    kpi["__row_id"] = np.arange(len(kpi), dtype=np.int32)
    if len(kpi) != 25_588 or int(kpi[TARGET].sum()) != 248:
        raise AssertionError(f"Unexpected modeling cohort: rows={len(kpi)}, positives={int(kpi[TARGET].sum())}")
    return DataBundle(raw=raw, kpi=kpi, processed_min=processed_min)


def _total_variation(left: pd.Series, right: pd.Series) -> float:
    left_dist = left.fillna(MISSING).astype(str).value_counts(normalize=True)
    right_dist = right.fillna(MISSING).astype(str).value_counts(normalize=True)
    levels = left_dist.index.union(right_dist.index)
    return float(0.5 * np.abs(left_dist.reindex(levels, fill_value=0) - right_dist.reindex(levels, fill_value=0)).sum())


def create_column_audit(bundle: DataBundle) -> dict[str, Any]:
    raw = bundle.raw
    opening_year = raw[OPEN].dt.year
    early = raw[opening_year < 2025]
    late = raw[opening_year == 2025]
    rows: list[dict[str, Any]] = []
    for column in raw.columns:
        series = raw[column]
        classification, rationale = COLUMN_CLASSIFICATION[column]
        non_null_open = raw.loc[series.notna(), OPEN]
        monthly_missing = series.isna().groupby(raw[OPEN].dt.to_period("M")).mean()
        if pd.api.types.is_datetime64_any_dtype(series):
            drift = float(monthly_missing.max() - monthly_missing.min())
            temporal_value_min = series.min()
            temporal_value_max = series.max()
        else:
            drift = _total_variation(early[column], late[column])
            temporal_value_min = None
            temporal_value_max = None
        p2_mask = raw[PRIORITY] == P2
        p3_mask = raw[PRIORITY] == P3
        rows.append({
            "column": column,
            "classification": classification,
            "rationale": rationale,
            "dtype": str(series.dtype),
            "missing_rate": float(series.isna().mean()),
            "cardinality_non_null": int(series.nunique(dropna=True)),
            "first_opening_with_value": None if non_null_open.empty else non_null_open.min().isoformat(),
            "last_opening_with_value": None if non_null_open.empty else non_null_open.max().isoformat(),
            "value_timestamp_min": None if temporal_value_min is None or pd.isna(temporal_value_min) else pd.Timestamp(temporal_value_min).isoformat(),
            "value_timestamp_max": None if temporal_value_max is None or pd.isna(temporal_value_max) else pd.Timestamp(temporal_value_max).isoformat(),
            "priority_levels_with_value": int(raw.loc[series.notna(), PRIORITY].nunique()),
            "p2_non_null_rate": float(series[p2_mask].notna().mean()),
            "p3_non_null_rate": float(series[p3_mask].notna().mean()),
            "monthly_missingness_range": float(monthly_missing.max() - monthly_missing.min()),
            "early_vs_2025_drift_tv_or_missing": drift,
        })
    audit_path = EXPERIMENT_DIR / "column_audit.csv"
    with audit_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

    kpi = bundle.kpi
    p2_monthly = (
        kpi[kpi[PRIORITY] == P2]
        .assign(month=lambda frame: frame[OPEN].dt.to_period("M").astype(str))
        .groupby("month").agg(incidents=(TARGET, "size"), violations=(TARGET, "sum"))
        .reset_index().to_dict("records")
    )
    quality = {
        "dataset": {
            "raw_rows": int(len(raw)), "raw_columns": int(raw.shape[1]),
            "sheet_count": 1, "duplicate_full_rows": int(raw.duplicated().sum()),
            "duplicate_incident_ids": int(raw["Número"].duplicated().sum()),
            "raw_sha256": _hash_file(RAW_PATH), "processed_sha256": _hash_file(PROCESSED_PATH),
        },
        "timestamps": {
            "open_min": raw[OPEN].min().isoformat(), "open_max": raw[OPEN].max().isoformat(),
            "resolved_before_open": int(((raw["Resolvido"] < raw[OPEN]) & raw["Resolvido"].notna()).sum()),
            "closed_before_open": int(((raw["Encerrado"] < raw[OPEN]) & raw["Encerrado"].notna()).sum()),
            "resolved_opening_coverage_by_year": {
                str(year): float(group["Resolvido"].notna().mean()) for year, group in raw.groupby(opening_year)
            },
            "closed_opening_coverage_by_year": {
                str(year): float(group["Encerrado"].notna().mean()) for year, group in raw.groupby(opening_year)
            },
        },
        "cohort": {
            "model_rows": int(len(kpi)), "violations": int(kpi[TARGET].sum()),
            "p2_first_open": kpi.loc[kpi[PRIORITY] == P2, OPEN].min().isoformat(),
            "p2_monthly": p2_monthly,
            "p2_pre_2025_rows": int(((kpi[PRIORITY] == P2) & (kpi[OPEN].dt.year < 2025)).sum()),
            "unexpected_priority_values": int((~raw[PRIORITY].isin([
                "1 - Crítica", P2, P3, "4 - Baixa", "5 - Muito Baixa",
            ])).sum()),
            "unexpected_kpi_entry_values": int((~raw["Entrou para KPI?"].isin(["SIM", "NAO"])).sum()),
            "unexpected_non_null_target_values": int((
                raw["KPI Violado?"].notna() & ~raw["KPI Violado?"].isin(["SIM", "NAO"])
            ).sum()),
            "kpi_rows_with_missing_target": int((
                (raw["Entrou para KPI?"] == "SIM") & raw["KPI Violado?"].isna()
            ).sum()),
        },
        "collection_regime_inference": {
            "observed_fact": "P2 KPI rows begin in 2025; resolution/closure timestamp coverage changes sharply by opening year.",
            "supported_inference": "A collection or scope-definition change is more plausible than a stable 2023-2025 P2 process.",
            "unsupported_conclusion": "The raw snapshot alone cannot establish the business cause of the regime change.",
        },
    }
    _write_json(EXPERIMENT_DIR / "audit_summary.json", quality)
    return quality


def create_backlog() -> list[dict[str, Any]]:
    ranking = [
        ("historical_outcomes", 9, 8, 9, 5), ("arrival_burst", 8, 8, 10, 3),
        ("recurrence", 8, 8, 9, 5), ("segmented_bursts", 8, 8, 9, 5),
        ("description_history", 8, 7, 8, 5), ("config_identity", 7, 7, 8, 4),
        ("text_tfidf", 8, 7, 7, 7), ("novelty_support", 6, 7, 9, 4),
        ("active_workload", 8, 7, 6, 6), ("queue_growth", 7, 6, 7, 5),
        ("interactions", 6, 6, 8, 5), ("calendar_context", 5, 5, 10, 2),
    ]
    backlog = []
    for rank, (family, value, plausibility, availability, cost) in enumerate(ranking, 1):
        item = dict(FAMILY_METADATA[family])
        item.update({
            "rank": rank, "id": family,
            "priority_score": float(value * plausibility * availability / cost),
            "status": "UNTESTED",
        })
        backlog.append(item)
    _write_json(EXPERIMENT_DIR / "hypothesis_backlog.json", backlog)
    return backlog


def _search_count(events: np.ndarray, queries: np.ndarray, seconds: int) -> np.ndarray:
    delta = np.timedelta64(seconds, "s")
    return (
        np.searchsorted(events, queries, side="left")
        - np.searchsorted(events, queries - delta, side="left")
    ).astype(np.float32)


def _group_event_arrays(frame: pd.DataFrame, key: str, time_col: str) -> dict[str, np.ndarray]:
    temp = frame[[key, time_col]].dropna(subset=[time_col]).copy()
    temp[key] = temp[key].fillna(MISSING).astype(str)
    return {
        str(level): np.sort(group[time_col].to_numpy(dtype="datetime64[ns]"))
        for level, group in temp.groupby(key, sort=False)
    }


def _group_prior_features(
    event_frame: pd.DataFrame,
    query_frame: pd.DataFrame,
    key: str,
    prefix: str,
    windows: Iterable[int],
) -> pd.DataFrame:
    arrays = _group_event_arrays(event_frame, key, OPEN)
    result = pd.DataFrame(index=query_frame.index)
    query_values = query_frame[key].fillna(MISSING).astype(str)
    for column in [f"{prefix}_prior_log", f"{prefix}_since_hours", *[f"{prefix}_count_{seconds}s" for seconds in windows]]:
        result[column] = np.zeros(len(query_frame), dtype=np.float32)
    for level, indices in query_values.groupby(query_values, sort=False).groups.items():
        idx = np.asarray(list(indices), dtype=int)
        events = arrays.get(str(level), np.asarray([], dtype="datetime64[ns]"))
        queries = query_frame.loc[idx, OPEN].to_numpy(dtype="datetime64[ns]")
        positions = np.searchsorted(events, queries, side="left")
        result.loc[idx, f"{prefix}_prior_log"] = np.log1p(positions).astype(np.float32)
        previous = np.full(len(idx), np.datetime64("NaT"), dtype="datetime64[ns]")
        has_previous = positions > 0
        previous[has_previous] = events[positions[has_previous] - 1]
        hours = np.full(len(idx), 24.0 * 365.0, dtype=np.float32)
        hours[has_previous] = ((queries[has_previous] - previous[has_previous]) / np.timedelta64(1, "h")).astype(np.float32)
        result.loc[idx, f"{prefix}_since_hours"] = np.clip(hours, 0, 24 * 365)
        for seconds in windows:
            result.loc[idx, f"{prefix}_count_{seconds}s"] = _search_count(events, queries, seconds)
    return result.astype(np.float32)


def _active_counts(events: pd.DataFrame, queries: pd.DataFrame, key: str | None = None) -> np.ndarray:
    if key is None:
        opens = np.sort(events[OPEN].dropna().to_numpy(dtype="datetime64[ns]"))
        ends = np.sort(events["__end"].dropna().to_numpy(dtype="datetime64[ns]"))
        q = queries[OPEN].to_numpy(dtype="datetime64[ns]")
        return (np.searchsorted(opens, q, "left") - np.searchsorted(ends, q, "right")).astype(np.float32)
    opens_by = _group_event_arrays(events, key, OPEN)
    ends_by = _group_event_arrays(events, key, "__end")
    values = queries[key].fillna(MISSING).astype(str)
    output = np.zeros(len(queries), dtype=np.float32)
    for level, indices in values.groupby(values, sort=False).groups.items():
        idx = np.asarray(list(indices), dtype=int)
        q = queries.loc[idx, OPEN].to_numpy(dtype="datetime64[ns]")
        opens = opens_by.get(str(level), np.asarray([], dtype="datetime64[ns]"))
        ends = ends_by.get(str(level), np.asarray([], dtype="datetime64[ns]"))
        output[idx] = np.searchsorted(opens, q, "left") - np.searchsorted(ends, q, "right")
    return output


def _historical_rate_features(
    kpi: pd.DataFrame, queries: pd.DataFrame, key: str, prefix: str, alpha: float = 10.0,
) -> pd.DataFrame:
    known = kpi.dropna(subset=[KNOWN]).sort_values(KNOWN, kind="stable").copy()
    known[key] = known[key].fillna(MISSING).astype(str)
    queries_key = queries[key].fillna(MISSING).astype(str)
    global_times = known[KNOWN].to_numpy(dtype="datetime64[ns]")
    global_y = known[TARGET].to_numpy(dtype=np.int64)
    global_cum = np.cumsum(global_y)
    grouped: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for level, group in known.groupby(key, sort=False):
        times = group[KNOWN].to_numpy(dtype="datetime64[ns]")
        grouped[str(level)] = (times, np.cumsum(group[TARGET].to_numpy(dtype=np.int64)))
    support = np.zeros(len(queries), dtype=np.float32)
    positives = np.zeros(len(queries), dtype=np.float32)
    global_rate = np.zeros(len(queries), dtype=np.float32)
    for level, indices in queries_key.groupby(queries_key, sort=False).groups.items():
        idx = np.asarray(list(indices), dtype=int)
        q = queries.loc[idx, OPEN].to_numpy(dtype="datetime64[ns]")
        gp = np.searchsorted(global_times, q, side="left")
        gs = np.where(gp > 0, global_cum[np.maximum(gp - 1, 0)], 0)
        global_rate[idx] = ((gs + 1.0) / (gp + 100.0)).astype(np.float32)
        times, cumulative = grouped.get(str(level), (np.asarray([], dtype="datetime64[ns]"), np.asarray([], dtype=np.int64)))
        pos = np.searchsorted(times, q, side="left")
        support[idx] = pos
        positives[idx] = np.where(pos > 0, cumulative[np.maximum(pos - 1, 0)], 0)
    rate = (positives + alpha * global_rate) / (support + alpha)
    return pd.DataFrame({
        f"{prefix}_hist_rate": rate.astype(np.float32),
        f"{prefix}_hist_support_log": np.log1p(support).astype(np.float32),
    }, index=queries.index)


def _daily_lags(kpi: pd.DataFrame) -> pd.DataFrame:
    dates = pd.date_range(kpi[OPEN].dt.normalize().min(), kpi[OPEN].dt.normalize().max(), freq="D")
    daily = pd.DataFrame(index=dates)
    daily["all"] = kpi.groupby(kpi[OPEN].dt.normalize()).size().reindex(dates, fill_value=0)
    daily["p2"] = kpi[kpi[PRIORITY] == P2].groupby(kpi.loc[kpi[PRIORITY] == P2, OPEN].dt.normalize()).size().reindex(dates, fill_value=0)
    daily["p3"] = kpi[kpi[PRIORITY] == P3].groupby(kpi.loc[kpi[PRIORITY] == P3, OPEN].dt.normalize()).size().reindex(dates, fill_value=0)
    out = pd.DataFrame(index=kpi.index)
    qdates = kpi[OPEN].dt.normalize()
    for name in ["all", "p2", "p3"]:
        out[f"lag1_{name}"] = qdates.map(daily[name].shift(1)).fillna(0).to_numpy(dtype=np.float32)
        out[f"lag7_{name}"] = qdates.map(daily[name].shift(7)).fillna(0).to_numpy(dtype=np.float32)
        out[f"roll7_{name}"] = qdates.map(daily[name].shift(1).rolling(7, min_periods=1).mean()).fillna(0).to_numpy(dtype=np.float32)
        out[f"roll30_{name}"] = qdates.map(daily[name].shift(1).rolling(30, min_periods=1).mean()).fillna(0).to_numpy(dtype=np.float32)
    return out


def build_feature_store(bundle: DataBundle) -> FeatureStore:
    raw = bundle.raw.copy()
    kpi = bundle.kpi.copy()
    for frame in [raw, kpi]:
        for column in ["Produto", "Categoria", "Subcategoria", "Grupo designado", "Item de configuração", "Descrição resumida", "Aberto por", PRIORITY]:
            frame[column] = frame[column].fillna(MISSING).astype(str)
    raw["__end"] = pd.concat([raw["Resolvido"], raw["Encerrado"]], axis=1).min(axis=1)
    q = kpi[OPEN]
    numeric = pd.DataFrame(index=kpi.index)
    numeric["priority_p2"] = (kpi[PRIORITY] == P2).astype(np.float32)
    numeric["hour"] = q.dt.hour.astype(np.float32)
    numeric["dow"] = q.dt.dayofweek.astype(np.float32)
    numeric["month"] = q.dt.month.astype(np.float32)
    numeric["day"] = q.dt.day.astype(np.float32)
    numeric["week"] = q.dt.isocalendar().week.astype(np.float32)
    numeric["is_weekend"] = (q.dt.dayofweek >= 5).astype(np.float32)
    numeric["is_business"] = ((q.dt.dayofweek < 5) & q.dt.hour.between(9, 17)).astype(np.float32)
    numeric["hour_sin"] = np.sin(2 * np.pi * q.dt.hour / 24).astype(np.float32)
    numeric["hour_cos"] = np.cos(2 * np.pi * q.dt.hour / 24).astype(np.float32)
    numeric["dow_sin"] = np.sin(2 * np.pi * q.dt.dayofweek / 7).astype(np.float32)
    numeric["dow_cos"] = np.cos(2 * np.pi * q.dt.dayofweek / 7).astype(np.float32)
    numeric["month_sin"] = np.sin(2 * np.pi * q.dt.month / 12).astype(np.float32)
    numeric["month_cos"] = np.cos(2 * np.pi * q.dt.month / 12).astype(np.float32)
    lags = _daily_lags(kpi)
    numeric = pd.concat([numeric, lags], axis=1)
    family_numeric: dict[str, list[str]] = {"base": list(numeric.columns)}
    family_categorical: dict[str, list[str]] = {"base_safe": SAFE_BASE_CATEGORICAL, "base_champion": CHAMPION_CATEGORICAL}

    # Global arrival bursts.
    raw_open = np.sort(raw[OPEN].to_numpy(dtype="datetime64[ns]"))
    q_open = kpi[OPEN].to_numpy(dtype="datetime64[ns]")
    cols = []
    for label, seconds in [("15m", 900), ("1h", 3600), ("4h", 14400), ("12h", 43200), ("24h", 86400), ("7d", 604800)]:
        column = f"arrivals_{label}"; numeric[column] = _search_count(raw_open, q_open, seconds); cols.append(column)
    family_numeric["arrival_burst"] = cols

    # Active workload; prior incident outcomes are used only to establish state at q.
    cols = []
    numeric["active_all"] = _active_counts(raw, kpi); cols.append("active_all")
    for label, subset in [("p2", raw[raw[PRIORITY] == P2]), ("p3", raw[raw[PRIORITY] == P3])]:
        column = f"active_{label}"; numeric[column] = _active_counts(subset, kpi); cols.append(column)
    for key, prefix in [("Produto", "active_product")]:
        numeric[prefix] = _active_counts(raw, kpi, key); cols.append(prefix)
    family_numeric["active_workload"] = cols

    # Recurrence and novelty/support.
    recurrence_parts = []
    recurrence_cols: list[str] = []
    novelty_cols: list[str] = []
    for key, prefix in [
        ("Produto", "product"), ("Categoria", "category"), ("Subcategoria", "subcategory"),
        ("Item de configuração", "config"), ("Descrição resumida", "description"),
    ]:
        part = _group_prior_features(raw, kpi, key, prefix, windows=[3600, 86400, 604800])
        recurrence_parts.append(part)
        recurrence_cols.extend([f"{prefix}_since_hours", f"{prefix}_count_3600s", f"{prefix}_count_86400s", f"{prefix}_count_604800s"])
        novelty_cols.append(f"{prefix}_prior_log")
    recurrence_frame = pd.concat(recurrence_parts, axis=1)
    numeric = pd.concat([numeric, recurrence_frame], axis=1)
    first_seen_cols: list[str] = []
    for column in list(novelty_cols):
        first_col = column.replace("_prior_log", "_first_seen")
        numeric[first_col] = (numeric[column] == 0).astype(np.float32)
        first_seen_cols.append(first_col)
    novelty_cols.extend(first_seen_cols)
    family_numeric["recurrence"] = recurrence_cols
    family_numeric["novelty_support"] = novelty_cols

    # Strictly prior, known historical outcomes.
    hist_cols: list[str] = []
    for key, prefix in [("Produto", "product"), ("Categoria", "category"), ("Subcategoria", "subcategory")]:
        part = _historical_rate_features(kpi, kpi, key, prefix)
        numeric = pd.concat([numeric, part], axis=1); hist_cols.extend(part.columns.tolist())
    family_numeric["historical_outcomes"] = hist_cols

    # High-cardinality safe opening fields.
    config_hist = _historical_rate_features(kpi, kpi, "Item de configuração", "config")
    numeric = pd.concat([numeric, config_hist], axis=1)
    family_numeric["config_identity"] = config_hist.columns.tolist()
    family_categorical["config_identity"] = ["Item de configuração"]
    desc_hist = _historical_rate_features(kpi, kpi, "Descrição resumida", "description")
    numeric = pd.concat([numeric, desc_hist], axis=1)
    family_numeric["description_history"] = desc_hist.columns.tolist()
    family_categorical["description_history"] = ["Descrição resumida"]

    categorical: dict[str, pd.Series] = {}
    for column in set(CHAMPION_CATEGORICAL + ["Item de configuração", "Descrição resumida"]):
        categorical[column] = kpi[column].copy()
    combos = {
        "product_category": kpi["Produto"] + "\x1f" + kpi["Categoria"],
        "product_subcategory": kpi["Produto"] + "\x1f" + kpi["Subcategoria"],
        "category_source": kpi["Categoria"] + "\x1f" + kpi["Aberto por"],
    }
    categorical.update(combos)
    family_categorical["interactions"] = list(combos)
    family_numeric["interactions"] = []

    # Calendar context beyond champion temporal features.
    calendar_cols = []
    numeric["minute"] = q.dt.minute.astype(np.float32); calendar_cols.append("minute")
    numeric["minute_sin"] = np.sin(2 * np.pi * q.dt.minute / 60).astype(np.float32); calendar_cols.append("minute_sin")
    numeric["minute_cos"] = np.cos(2 * np.pi * q.dt.minute / 60).astype(np.float32); calendar_cols.append("minute_cos")
    numeric["is_month_end"] = q.dt.is_month_end.astype(np.float32); calendar_cols.append("is_month_end")
    numeric["is_shift_boundary"] = q.dt.hour.isin([7, 8, 9, 17, 18, 19]).astype(np.float32); calendar_cols.append("is_shift_boundary")
    try:
        from src.data.feriados import build_holiday_features
        holiday = build_holiday_features(q).reset_index(drop=True).astype(np.float32)
        holiday.columns = [f"holiday_{column}" for column in holiday.columns]
        numeric = pd.concat([numeric, holiday], axis=1); calendar_cols.extend(holiday.columns.tolist())
    except Exception:
        pass
    family_numeric["calendar_context"] = calendar_cols

    # Segmented bursts for safe, opening-time keys.
    segmented_cols: list[str] = []
    for key, prefix in [(PRIORITY, "priority"), ("Produto", "product"), ("Categoria", "category")]:
        part = _group_prior_features(raw, kpi, key, f"burst_{prefix}", windows=[3600, 14400, 86400])
        selected = [column for column in part if "count_" in column]
        numeric = pd.concat([numeric, part[selected]], axis=1); segmented_cols.extend(selected)
    family_numeric["segmented_bursts"] = segmented_cols

    # Queue acceleration and net growth using only prior event timestamps.
    queue_cols = []
    for label, seconds in [("1h", 3600), ("4h", 14400)]:
        recent = _search_count(raw_open, q_open, seconds)
        previous = _search_count(raw_open, q_open - np.timedelta64(seconds, "s"), seconds)
        ratio_col = f"arrival_ratio_{label}"; diff_col = f"arrival_diff_{label}"
        numeric[ratio_col] = ((recent + 1) / (previous + 1)).astype(np.float32)
        numeric[diff_col] = (recent - previous).astype(np.float32)
        queue_cols.extend([ratio_col, diff_col])
    end_events = np.sort(raw["__end"].dropna().to_numpy(dtype="datetime64[ns]"))
    ended_1h = _search_count(end_events, q_open, 3600)
    numeric["net_queue_growth_1h"] = (numeric["arrivals_1h"].to_numpy() - ended_1h).astype(np.float32)
    queue_cols.append("net_queue_growth_1h")
    family_numeric["queue_growth"] = queue_cols

    if numeric.columns.duplicated().any():
        raise AssertionError("Duplicate engineered feature names")
    return FeatureStore(
        numeric=numeric.replace([np.inf, -np.inf], np.nan).astype(np.float32),
        categorical=categorical,
        descriptions=kpi["Descrição resumida"].copy(),
        family_numeric=family_numeric,
        family_categorical=family_categorical,
    )


def self_checks() -> dict[str, bool]:
    events = np.array(["2025-01-01T00:00:00", "2025-01-01T00:30:00", "2025-01-01T01:00:00"], dtype="datetime64[ns]")
    queries = np.array(["2025-01-01T01:00:00"], dtype="datetime64[ns]")
    assert _search_count(events, queries, 3600).tolist() == [2.0], "Current/simultaneous event leaked into recent count"
    toy = pd.DataFrame({
        OPEN: pd.to_datetime(["2025-01-01 00:00", "2025-01-01 00:30"]),
        "__end": pd.to_datetime(["2025-01-01 00:45", "2025-01-01 02:00"]),
        "key": ["a", "a"],
    })
    query = pd.DataFrame({OPEN: pd.to_datetime(["2025-01-01 01:00"]), "key": ["a"]})
    assert _active_counts(toy, query).tolist() == [1.0]
    assert _active_counts(toy, query, "key").tolist() == [1.0]
    outcomes = pd.DataFrame({
        OPEN: pd.to_datetime(["2025-01-01", "2025-01-03"]),
        KNOWN: pd.to_datetime(["2025-01-02", "2025-01-10"]),
        TARGET: [1, 1], "key": ["a", "a"],
    })
    outcome_query = pd.DataFrame({OPEN: pd.to_datetime(["2025-01-05"]), "key": ["a"]})
    rates = _historical_rate_features(outcomes, outcome_query, "key", "key")
    assert np.isclose(rates.loc[0, "key_hist_support_log"], np.log1p(1)), "Future-known outcome leaked into historical support"
    return {
        "recent_count_excludes_current": True,
        "active_count_uses_prior_end_state": True,
        "historical_rate_excludes_future_known_outcomes": True,
    }


def _fold_indices(
    kpi: pd.DataFrame, month: pd.Period, evaluation_priority: str = P2,
) -> tuple[np.ndarray, np.ndarray]:
    start = month.start_time
    end = (month + 1).start_time
    # Training labels must have been observable by the start of the outer month.
    train = np.flatnonzero(((kpi[OPEN] < start) & (kpi[KNOWN] < start)).to_numpy())
    test = np.flatnonzero(((kpi[OPEN] >= start) & (kpi[OPEN] < end) & (kpi[PRIORITY] == evaluation_priority)).to_numpy())
    if not len(train) or not len(test): raise AssertionError(f"Empty fold {month}")
    return train, test


def _encode_categories(
    store: FeatureStore, kpi: pd.DataFrame, train_idx: np.ndarray, test_idx: np.ndarray,
    columns: list[str],
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    train_parts: list[np.ndarray] = []
    test_parts: list[np.ndarray] = []
    names: list[str] = []
    y_train = kpi.iloc[train_idx][TARGET].to_numpy(dtype=np.float32)
    global_rate = float(y_train.mean())
    for column in columns:
        if column in store.categorical:
            values = store.categorical[column]
        else:
            values = kpi[column].fillna(MISSING).astype(str)
        tr = values.iloc[train_idx].astype(str)
        te = values.iloc[test_idx].astype(str)
        levels = pd.Index(tr.drop_duplicates())
        codes = pd.Series(np.arange(len(levels), dtype=np.float32), index=levels)
        tr_code = tr.map(codes).fillna(-1).to_numpy(dtype=np.float32)
        te_code = te.map(codes).fillna(-1).to_numpy(dtype=np.float32)
        counts = tr.value_counts()
        freq = counts / len(tr)
        tr_freq = tr.map(freq).to_numpy(dtype=np.float32)
        te_freq = te.map(freq).fillna(0).to_numpy(dtype=np.float32)
        grouped_sum = pd.Series(y_train, index=tr.index).groupby(tr).sum()
        grouped_count = tr.value_counts()
        alpha = 20.0
        # Leave-one-out on training rows; full training map on evaluation rows.
        tr_sum = tr.map(grouped_sum).to_numpy(dtype=np.float32) - y_train
        tr_count = tr.map(grouped_count).to_numpy(dtype=np.float32) - 1
        tr_te = (tr_sum + alpha * global_rate) / (tr_count + alpha)
        full_te = (grouped_sum + alpha * global_rate) / (grouped_count + alpha)
        te_te = te.map(full_te).fillna(global_rate).to_numpy(dtype=np.float32)
        train_parts.extend([tr_code[:, None], tr_freq[:, None], tr_te[:, None]])
        test_parts.extend([te_code[:, None], te_freq[:, None], te_te[:, None]])
        names.extend([f"{column}__code", f"{column}__freq", f"{column}__te"])
    if not train_parts:
        return np.empty((len(train_idx), 0), np.float32), np.empty((len(test_idx), 0), np.float32), []
    return np.hstack(train_parts), np.hstack(test_parts), names


def _feature_lists(store: FeatureStore, families: list[str], champion: bool) -> tuple[list[str], list[str]]:
    numeric = list(store.family_numeric["base"])
    categorical = list(CHAMPION_CATEGORICAL if champion else SAFE_BASE_CATEGORICAL)
    for family in families:
        numeric.extend(store.family_numeric.get(family, []))
        categorical.extend(store.family_categorical.get(family, []))
    return list(dict.fromkeys(numeric)), list(dict.fromkeys(categorical))


def _prepare_fold(
    store: FeatureStore, kpi: pd.DataFrame, train_idx: np.ndarray, test_idx: np.ndarray,
    families: list[str], champion: bool,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    numeric_cols, categorical_cols = _feature_lists(store, families, champion)
    tr_num = store.numeric.iloc[train_idx][numeric_cols].copy()
    te_num = store.numeric.iloc[test_idx][numeric_cols].copy()
    medians = tr_num.median().fillna(0)
    tr_num = tr_num.fillna(medians).fillna(0)
    te_num = te_num.fillna(medians).fillna(0)
    tr_cat, te_cat, cat_names = _encode_categories(store, kpi, train_idx, test_idx, categorical_cols)
    return (
        np.hstack([tr_num.to_numpy(dtype=np.float32), tr_cat]),
        np.hstack([te_num.to_numpy(dtype=np.float32), te_cat]),
        [*numeric_cols, *cat_names],
    )


def _top_metrics(y: np.ndarray, score: np.ndarray, share: float = 0.05) -> dict[str, Any]:
    k = max(1, int(round(len(y) * share)))
    selected = np.argsort(-score, kind="stable")[:k]
    hits = int(y[selected].sum())
    prevalence = float(y.mean())
    return {
        "k": k, "hits": hits, "precision": float(hits / k),
        "recall": float(hits / max(1, y.sum())),
        "lift": float((hits / k) / max(prevalence, 1e-12)),
    }


def _summarize_predictions(folds: list[dict[str, Any]]) -> dict[str, Any]:
    all_y = np.concatenate([fold.pop("_y") for fold in folds])
    all_p = np.concatenate([fold.pop("_p") for fold in folds])
    alerts = sum(fold["top_5pct"]["k"] for fold in folds)
    hits = sum(fold["top_5pct"]["hits"] for fold in folds)
    total_days = sum(pd.Period(fold["month"], freq="M").days_in_month for fold in folds)
    pr_values = np.asarray([fold["pr_auc"] for fold in folds], dtype=float)
    return {
        "aggregate": {
            "incidents": int(len(all_y)), "violations": int(all_y.sum()),
            "prevalence": float(all_y.mean()),
            "pr_auc": float(average_precision_score(all_y, all_p)),
            "monthly_pr_auc_mean": float(pr_values.mean()),
            "monthly_pr_auc_std": float(pr_values.std()),
            "precision_at_top_5pct": float(hits / alerts),
            "recall_at_top_5pct": float(hits / max(1, all_y.sum())),
            "lift_at_top_5pct": float((hits / alerts) / max(float(all_y.mean()), 1e-12)),
            "alerts": int(alerts), "hits": int(hits),
            "alerts_per_day": float(alerts / total_days),
            "incidents_reviewed_per_true_violation": None if hits == 0 else float(alerts / hits),
        },
        "monthly": folds,
        "_all_y": all_y,
        "_all_p": all_p,
    }


def evaluate_xgb(
    bundle: DataBundle, store: FeatureStore, families: list[str], seed: int = BASE_SEED,
    champion: bool = False, specialist: bool = False, evaluation_priority: str = P2,
) -> dict[str, Any]:
    kpi = bundle.kpi
    folds: list[dict[str, Any]] = []
    for month in OUTER_MONTHS:
        train_idx, test_idx = _fold_indices(kpi, month, evaluation_priority)
        if specialist:
            train_idx = train_idx[kpi.iloc[train_idx][PRIORITY].to_numpy() == P2]
        X_train, X_test, feature_names = _prepare_fold(store, kpi, train_idx, test_idx, families, champion)
        y_train = kpi.iloc[train_idx][TARGET].to_numpy(dtype=np.int8)
        y_test = kpi.iloc[test_idx][TARGET].to_numpy(dtype=np.int8)
        params = {
            **LOCKED_XGB_PARAMS, "objective": "binary:logistic", "eval_metric": "aucpr",
            "random_state": seed, "n_jobs": min(8, os.cpu_count() or 1), "tree_method": "hist",
        }
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train, verbose=False)
        probability = model.predict_proba(X_test)[:, 1].astype(float)
        top = _top_metrics(y_test, probability)
        folds.append({
            "month": str(month), "train_incidents": int(len(train_idx)),
            "train_violations": int(y_train.sum()), "test_incidents": int(len(test_idx)),
            "test_violations": int(y_test.sum()),
            "pr_auc": float(average_precision_score(y_test, probability)),
            "roc_auc_secondary": float(roc_auc_score(y_test, probability)),
            "top_5pct": top, "feature_count": len(feature_names),
            "_y": y_test, "_p": probability,
        })
    result = _summarize_predictions(folds)
    result["config"] = {
        "kind": "xgboost", "seed": seed, "families": families,
        "champion_group_included": champion, "p2_specialist": specialist,
        "evaluation_priority": evaluation_priority,
        "params": LOCKED_XGB_PARAMS,
    }
    return result


def _rank01(values: np.ndarray) -> np.ndarray:
    return pd.Series(values).rank(method="average", pct=True).to_numpy(dtype=float)


def evaluate_text_blend(
    bundle: DataBundle, store: FeatureStore, baseline: dict[str, Any], seed: int = BASE_SEED,
    p2_only: bool = False, blend_weight: float = 0.50, evaluation_priority: str = P2,
) -> dict[str, Any]:
    kpi = bundle.kpi
    # Re-evaluate baseline fold scores because report summaries intentionally strip private arrays.
    base_full = evaluate_xgb(
        bundle, store, [], seed=seed, champion=True,
        evaluation_priority=evaluation_priority,
    )
    # _summarize_predictions already moved private arrays to top level; split again by fold lengths.
    offset = 0; folds = []
    for month in OUTER_MONTHS:
        train_idx, test_idx = _fold_indices(kpi, month, evaluation_priority)
        if p2_only: train_idx = train_idx[kpi.iloc[train_idx][PRIORITY].to_numpy() == P2]
        y_train = kpi.iloc[train_idx][TARGET].to_numpy(dtype=np.int8)
        y_test = kpi.iloc[test_idx][TARGET].to_numpy(dtype=np.int8)
        vectorizer = TfidfVectorizer(
            strip_accents="unicode", lowercase=True, ngram_range=(1, 2), min_df=2,
            max_df=0.995, max_features=30_000, sublinear_tf=True, dtype=np.float32,
        )
        X_train = vectorizer.fit_transform(store.descriptions.iloc[train_idx].astype(str))
        X_test = vectorizer.transform(store.descriptions.iloc[test_idx].astype(str))
        model = LogisticRegression(
            C=1.0, class_weight="balanced", max_iter=2000, solver="liblinear", random_state=seed,
        )
        model.fit(X_train, y_train)
        text_score = model.predict_proba(X_test)[:, 1]
        n = len(test_idx)
        base_score = base_full["_all_p"][offset:offset+n]; offset += n
        blended = (1 - blend_weight) * _rank01(base_score) + blend_weight * _rank01(text_score)
        top = _top_metrics(y_test, blended)
        folds.append({
            "month": str(month), "train_incidents": int(len(train_idx)),
            "train_violations": int(y_train.sum()), "test_incidents": int(n),
            "test_violations": int(y_test.sum()),
            "pr_auc": float(average_precision_score(y_test, blended)),
            "roc_auc_secondary": float(roc_auc_score(y_test, blended)),
            "top_5pct": top, "feature_count": int(X_train.shape[1]),
            "_y": y_test, "_p": blended,
        })
    result = _summarize_predictions(folds)
    result["config"] = {
        "kind": "tfidf_logistic_rank_blend", "seed": seed,
        "p2_only": p2_only, "blend_weight": blend_weight,
        "evaluation_priority": evaluation_priority,
        "vectorizer": {
            "ngram_range": [1, 2], "min_df": 2, "max_df": 0.995,
            "max_features": 30000, "sublinear_tf": True,
        },
        "logistic": {"C": 1.0, "class_weight": "balanced", "solver": "liblinear", "max_iter": 2000},
    }
    return result


def _public_metrics(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if not key.startswith("_")}


def _paired_comparison(candidate: dict[str, Any], champion: dict[str, Any]) -> dict[str, Any]:
    c_month = {row["month"]: row for row in candidate["monthly"]}
    b_month = {row["month"]: row for row in champion["monthly"]}
    deltas = []
    for month in [str(period) for period in OUTER_MONTHS]:
        deltas.append({
            "month": month,
            "pr_auc_delta": float(c_month[month]["pr_auc"] - b_month[month]["pr_auc"]),
            "candidate_pr_auc": c_month[month]["pr_auc"],
            "champion_pr_auc": b_month[month]["pr_auc"],
            "candidate_top5_hits": c_month[month]["top_5pct"]["hits"],
            "champion_top5_hits": b_month[month]["top_5pct"]["hits"],
        })
    return {
        "aggregate_pr_auc_delta": float(candidate["aggregate"]["pr_auc"] - champion["aggregate"]["pr_auc"]),
        "top5_precision_delta": float(candidate["aggregate"]["precision_at_top_5pct"] - champion["aggregate"]["precision_at_top_5pct"]),
        "top5_recall_delta": float(candidate["aggregate"]["recall_at_top_5pct"] - champion["aggregate"]["recall_at_top_5pct"]),
        "monthly_pr_auc_wins": int(sum(row["pr_auc_delta"] > 0 for row in deltas)),
        "monthly": deltas,
    }


def _promotion_gate(candidate: dict[str, Any], champion: dict[str, Any], stability: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    comparison = _paired_comparison(candidate, champion)
    required_pr = max(0.05, 1.25 * champion["aggregate"]["pr_auc"])
    checks = {
        "aggregate_pr_auc": candidate["aggregate"]["pr_auc"] >= required_pr,
        "precision_at_top_5pct": candidate["aggregate"]["precision_at_top_5pct"] >= 0.05,
        "recall_at_top_5pct": candidate["aggregate"]["recall_at_top_5pct"] >= 0.30,
        "monthly_pr_auc_wins": comparison["monthly_pr_auc_wins"] >= 4,
        "point_in_time_safe": not candidate["config"].get("champion_group_included", False),
    }
    stability_result = None
    if stability:
        recalls = np.asarray([row["recall_at_top_5pct"] for row in stability], dtype=float)
        median = float(np.median(recalls)); minimum = float(recalls.min())
        stability_result = {
            "principal_metric": "recall_at_top_5pct", "seeds": stability,
            "median": median, "minimum": minimum,
            "max_regression_from_median": float((median - minimum) / max(median, 1e-12)),
            "passes": minimum >= 0.95 * median,
        }
        checks["five_seed_stability"] = stability_result["passes"]
    return {"passes": all(checks.values()), "required_pr_auc": required_pr, "checks": checks, "comparison": comparison, "stability": stability_result}


def run_loop() -> dict[str, Any]:
    started = time.perf_counter()
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    checks = self_checks()
    bundle = load_data()
    audit = create_column_audit(bundle)
    backlog = create_backlog()
    store = build_feature_store(bundle)

    champion = evaluate_xgb(bundle, store, [], seed=BASE_SEED, champion=True)
    safe_base = evaluate_xgb(bundle, store, [], seed=BASE_SEED, champion=False)
    champion_p3 = evaluate_xgb(
        bundle, store, [], seed=BASE_SEED, champion=True,
        evaluation_priority=P3,
    )
    safe_base_p3 = evaluate_xgb(
        bundle, store, [], seed=BASE_SEED, champion=False,
        evaluation_priority=P3,
    )
    candidates: dict[str, dict[str, Any]] = {"safe_base": safe_base}
    log_path = EXPERIMENT_DIR / "experiment_log.jsonl"
    with log_path.open("w", encoding="utf-8") as log:
        for cycle, item in enumerate(backlog, 1):
            family = item["id"]
            cycle_started = time.perf_counter()
            if family == "text_tfidf":
                result = evaluate_text_blend(bundle, store, champion, seed=BASE_SEED, p2_only=False, blend_weight=0.5)
                p3_result = evaluate_text_blend(
                    bundle, store, champion_p3, seed=BASE_SEED,
                    p2_only=False, blend_weight=0.5, evaluation_priority=P3,
                )
            else:
                result = evaluate_xgb(bundle, store, [family], seed=BASE_SEED, champion=False)
                p3_result = evaluate_xgb(
                    bundle, store, [family], seed=BASE_SEED,
                    champion=False, evaluation_priority=P3,
                )
            comparison_to_safe = _paired_comparison(result, safe_base)
            comparison_to_champion = _paired_comparison(result, champion)
            retain = (
                comparison_to_safe["aggregate_pr_auc_delta"] > 0
                and result["aggregate"]["recall_at_top_5pct"] >= safe_base["aggregate"]["recall_at_top_5pct"]
                and comparison_to_safe["monthly_pr_auc_wins"] >= 3
            )
            status = "RETAIN" if retain else "REJECT"
            candidates[family] = result
            record = {
                "cycle": cycle, "hypothesis": family, **FAMILY_METADATA[family],
                "status": status, "duration_seconds": time.perf_counter() - cycle_started,
                "metrics": _public_metrics(result),
                "p3_diagnostic_metrics": _public_metrics(p3_result),
                "paired_vs_safe_base": comparison_to_safe,
                "paired_vs_champion": comparison_to_champion,
                "p3_paired_vs_safe_base": _paired_comparison(p3_result, safe_base_p3),
                "p3_paired_vs_champion": _paired_comparison(p3_result, champion_p3),
            }
            log.write(json.dumps(_json_safe(record), ensure_ascii=False, allow_nan=False) + "\n"); log.flush()
            for backlog_item in backlog:
                if backlog_item["id"] == family:
                    backlog_item["status"] = status
                    backlog_item["result_summary"] = {
                        "pr_auc": result["aggregate"]["pr_auc"],
                        "recall_at_top_5pct": result["aggregate"]["recall_at_top_5pct"],
                        "paired_pr_auc_delta_vs_champion": comparison_to_champion["aggregate_pr_auc_delta"],
                    }
            _write_json(EXPERIMENT_DIR / "hypothesis_backlog.json", backlog)
            print(f"[{cycle:02d}/12] {family}: PR-AUC={result['aggregate']['pr_auc']:.5f}, "
                  f"P@5={result['aggregate']['precision_at_top_5pct']:.3f}, "
                  f"R@5={result['aggregate']['recall_at_top_5pct']:.3f}, {status}", flush=True)

    # Pre-specified full-safe numeric/categorical candidate and evidence-driven retained union.
    non_text_families = [item["id"] for item in backlog if item["id"] != "text_tfidf"]
    full_safe = evaluate_xgb(bundle, store, non_text_families, seed=BASE_SEED, champion=False)
    retained = [item["id"] for item in backlog if item["status"] == "RETAIN" and item["id"] != "text_tfidf"]
    retained_union = evaluate_xgb(bundle, store, retained, seed=BASE_SEED, champion=False) if retained else safe_base
    candidates["full_safe"] = full_safe; candidates["retained_union"] = retained_union

    # Strongest candidate is selected by the predefined operational lexicographic objective.
    eligible = {
        name: result for name, result in candidates.items()
        if not result["config"].get("champion_group_included", False)
    }
    best_name, best = max(
        eligible.items(),
        key=lambda item: (
            item[1]["aggregate"]["recall_at_top_5pct"] >= 0.30,
            item[1]["aggregate"]["precision_at_top_5pct"] >= 0.05,
            item[1]["aggregate"]["pr_auc"],
        ),
    )

    # Drop-one ablations for every retained family in a multi-family final candidate.
    final_families = list(best["config"].get("families", []))
    ablations: list[dict[str, Any]] = []
    if len(final_families) > 1:
        for family in final_families:
            without = [value for value in final_families if value != family]
            ablated = evaluate_xgb(bundle, store, without, seed=BASE_SEED, champion=False)
            ablations.append({
                "removed_family": family,
                "full_pr_auc": best["aggregate"]["pr_auc"],
                "without_pr_auc": ablated["aggregate"]["pr_auc"],
                "incremental_pr_auc": best["aggregate"]["pr_auc"] - ablated["aggregate"]["pr_auc"],
                "full_top5_recall": best["aggregate"]["recall_at_top_5pct"],
                "without_top5_recall": ablated["aggregate"]["recall_at_top_5pct"],
            })
        demonstrably_incremental = [row["removed_family"] for row in ablations if row["incremental_pr_auc"] > 0 and row["full_top5_recall"] >= row["without_top5_recall"]]
        if set(demonstrably_incremental) != set(final_families):
            final_families = demonstrably_incremental
            if final_families:
                best_name = "pruned_incremental_union"
                best = evaluate_xgb(bundle, store, final_families, seed=BASE_SEED, champion=False)

    preliminary_gate = _promotion_gate(best, champion)
    stability_rows: list[dict[str, Any]] = []
    for seed in SEEDS:
        if best["config"]["kind"] == "xgboost":
            seeded = evaluate_xgb(bundle, store, list(best["config"].get("families", [])), seed=seed, champion=False, specialist=best["config"].get("p2_specialist", False))
        else:
            seeded = evaluate_text_blend(bundle, store, champion, seed=seed)
        stability_rows.append({
            "seed": seed, "pr_auc": seeded["aggregate"]["pr_auc"],
            "precision_at_top_5pct": seeded["aggregate"]["precision_at_top_5pct"],
            "recall_at_top_5pct": seeded["aggregate"]["recall_at_top_5pct"],
        })
    gate = _promotion_gate(best, champion, stability_rows)

    if best["config"]["kind"] == "xgboost":
        best_p3 = evaluate_xgb(
            bundle, store, list(best["config"].get("families", [])),
            seed=BASE_SEED, champion=False,
            specialist=best["config"].get("p2_specialist", False),
            evaluation_priority=P3,
        )
    else:
        best_p3 = evaluate_text_blend(
            bundle, store, champion_p3, seed=BASE_SEED,
            p2_only=best["config"].get("p2_only", False),
            blend_weight=best["config"].get("blend_weight", 0.5),
            evaluation_priority=P3,
        )

    status = "SUCCESS: TARGET X ACHIEVED" if gate["passes"] else "NO-GO: RAW-ONLY CEILING"
    prior_report = json.loads(CHAMPION_REPORT.read_text(encoding="utf-8"))
    prior_p2 = prior_report["especialistas"]["P2"]["baseline_generalista_no_segmento"]["avaliacao"]["test_q4"]["ranking"]
    prior_p3 = prior_report["especialistas"]["P3"]["baseline_generalista_no_segmento"]["avaliacao"]["test_q4"]["ranking"]
    prior_global = prior_report["generalista"]["avaliacao_global"]["test_q4"]["ranking"]
    final_metrics = {
        "status": status,
        "generated_at": pd.Timestamp.now(tz="America/Sao_Paulo").isoformat(),
        "protocol": {
            "outer_months": [str(month) for month in OUTER_MONTHS],
            "training_rule": "opened before month AND target known before month",
            "evaluation_segment": "P2 only", "top_k_share": 0.05,
            "q4_fresh_holdout": False, "selection_note": "All 2025 outer folds are already inspected; evidence is paired temporal, not independent confirmation.",
        },
        "champion": _public_metrics(champion),
        "previous_opened_q4_artifact_context": {
            "source": str(CHAMPION_REPORT.relative_to(PROJECT_ROOT)),
            "global_pr_auc": prior_global["pr_auc"],
            "p2_pr_auc": prior_p2["pr_auc"],
            "p3_pr_auc": prior_p3["pr_auc"],
            "comparability_note": "Previously opened fixed train-through-June Q4 result; not directly comparable with monthly label-available walk-forward folds.",
        },
        "champion_p3_diagnostic": _public_metrics(champion_p3),
        "safe_base": _public_metrics(safe_base),
        "safe_base_p3_diagnostic": _public_metrics(safe_base_p3),
        "final_candidate_name": best_name,
        "final_candidate": _public_metrics(best),
        "final_candidate_p3_diagnostic": _public_metrics(best_p3),
        "promotion_gate": gate,
        "ablations": ablations,
        "stability": stability_rows,
        "cycles_completed": len(backlog),
        "feature_families_evaluated": [item["id"] for item in backlog],
        "self_checks": checks,
        "data_hashes": {"raw": _hash_file(RAW_PATH), "processed": _hash_file(PROCESSED_PATH)},
        "environment": {
            "python": platform.python_version(), "platform": platform.platform(),
            "pandas": pd.__version__, "numpy": np.__version__, "scikit_learn": sklearn.__version__,
            "xgboost": xgb.__version__, "joblib": joblib.__version__,
        },
        "runtime_seconds": time.perf_counter() - started,
    }
    _write_json(EXPERIMENT_DIR / "final_metrics.json", final_metrics)
    _write_json(EXPERIMENT_DIR / "feature_catalog.json", {
        "safe_base_numeric": store.family_numeric["base"],
        "safe_base_categorical": SAFE_BASE_CATEGORICAL,
        "champion_additional_uncertain": ["Grupo designado"],
        "families": {
            family: {
                "numeric_features": store.family_numeric.get(family, []),
                "categorical_sources": store.family_categorical.get(family, []),
                **FAMILY_METADATA[family],
            } for family in FAMILY_METADATA
        },
        "final_candidate_families": best["config"].get("families", []),
        "forbidden_fields_confirmed_absent": ["Duração", "Resolvido", "Encerrado", "Código de fechamento", "Solução", "KPI Violado?", "Status", "Incidente Pai", "Entrou para KPI?"],
    })
    _write_json(MODEL_EXPERIMENT_DIR / "final_candidate_config.json", {
        "status": status, "candidate_name": best_name, "config": best["config"],
        "locked_xgb_params": LOCKED_XGB_PARAMS, "seeds": SEEDS,
        "data_hashes": final_metrics["data_hashes"],
    })
    write_final_report(final_metrics, backlog, audit)
    update_state(final_metrics)
    return final_metrics


def write_final_report(metrics: dict[str, Any], backlog: list[dict[str, Any]], audit: dict[str, Any]) -> None:
    champion = metrics["champion"]["aggregate"]
    candidate = metrics["final_candidate"]["aggregate"]
    gate = metrics["promotion_gate"]
    retained = [item for item in backlog if item["status"] == "RETAIN"]
    rejected = [item for item in backlog if item["status"] == "REJECT"]
    cycle_logs = [
        json.loads(line) for line in (EXPERIMENT_DIR / "experiment_log.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    family_rows = []
    for row in cycle_logs:
        aggregate = row["metrics"]["aggregate"]
        p3_aggregate = row["p3_diagnostic_metrics"]["aggregate"]
        family_rows.append(
            f"| {row['hypothesis']} | {aggregate['pr_auc']:.5f} | "
            f"{row['paired_vs_safe_base']['aggregate_pr_auc_delta']:+.5f} | "
            f"{aggregate['recall_at_top_5pct']:.1%} | {p3_aggregate['pr_auc']:.5f} | {row['status']} |"
        )
    p3_champion = metrics["champion_p3_diagnostic"]["aggregate"]
    p3_candidate = metrics["final_candidate_p3_diagnostic"]["aggregate"]
    monthly_rows = []
    champ_month = {row["month"]: row for row in metrics["champion"]["monthly"]}
    for row in metrics["final_candidate"]["monthly"]:
        baseline = champ_month[row["month"]]
        monthly_rows.append(
            f"| {row['month']} | {baseline['pr_auc']:.4f} | {row['pr_auc']:.4f} | "
            f"{row['pr_auc']-baseline['pr_auc']:+.4f} | {row['top_5pct']['hits']}/{row['top_5pct']['k']} |"
        )
    conclusion = (
        "A point-in-time-safe raw-data candidate passed every promotion gate."
        if gate["passes"] else
        "Twelve materially different, point-in-time-safe raw-data families were tested; none produced a candidate that passed all P2 promotion gates."
    )
    stopping = (
        "All five promotion conditions, including five-seed stability, were satisfied."
        if gate["passes"] else
        "NO-GO condition: 12 materially different cycles completed, safe raw columns exhausted, strongest candidate rechecked, and failure established on paired monthly folds."
    )
    report = f"""# Raw Opportunity Loop — Final Report

## Status

{metrics['status']}

## Executive conclusion

{conclusion} Q4 and all 2025 outer months were already inspected; this is not described as a fresh holdout.

## Exact stopping criterion

{stopping}

## Champion versus final candidate

| Metric | Locked generalist, fold-safe reimplementation | Final candidate |
|---|---:|---:|
| Aggregate P2 PR-AUC | {champion['pr_auc']:.5f} | {candidate['pr_auc']:.5f} |
| Precision@Top-5% | {champion['precision_at_top_5pct']:.2%} | {candidate['precision_at_top_5pct']:.2%} |
| Recall@Top-5% | {champion['recall_at_top_5pct']:.2%} | {candidate['recall_at_top_5pct']:.2%} |
| Lift@Top-5% | {champion['lift_at_top_5pct']:.2f} | {candidate['lift_at_top_5pct']:.2f} |
| Alerts/day | {champion['alerts_per_day']:.3f} | {candidate['alerts_per_day']:.3f} |
| Reviewed per true violation | {champion['incidents_reviewed_per_true_violation']} | {candidate['incidents_reviewed_per_true_violation']} |

Required candidate PR-AUC: `{gate['required_pr_auc']:.5f}`. Monthly PR-AUC wins: `{gate['comparison']['monthly_pr_auc_wins']}/6`.

The previously opened `xgboost_specialists.json` reports P2 Q4 PR-AUC {metrics['previous_opened_q4_artifact_context']['p2_pr_auc']:.5f} (global {metrics['previous_opened_q4_artifact_context']['global_pr_auc']:.5f}; P3 {metrics['previous_opened_q4_artifact_context']['p3_pr_auc']:.5f}). That artifact fits once through June and evaluates a fixed Q4 block, whereas this research retrains monthly and excludes labels not known at each month start; the numbers are therefore context, not interchangeable baselines.

## Monthly P2 results

| Month | Champion PR-AUC | Candidate PR-AUC | Delta | Candidate Top-5% hits/alerts |
|---|---:|---:|---:|---:|
{chr(10).join(monthly_rows)}

## Feature-family evidence

Retained single-family hypotheses: {', '.join(item['id'] for item in retained) or 'none'}.

Rejected single-family hypotheses: {', '.join(item['id'] for item in rejected) or 'none'}.

| Family | P2 PR-AUC | Delta vs safe base | P2 Recall@Top-5% | P3 PR-AUC diagnostic | Decision |
|---|---:|---:|---:|---:|---|
{chr(10).join(family_rows)}

The final text family is an explicit single-family ablation against the safe base: PR-AUC rose from {metrics['safe_base']['aggregate']['pr_auc']:.5f} to {candidate['pr_auc']:.5f}, while Top-5% recall rose from {metrics['safe_base']['aggregate']['recall_at_top_5pct']:.1%} to {candidate['recall_at_top_5pct']:.1%}. It still failed the absolute promotion thresholds. The exact per-cycle paired deltas are in `experiment_log.jsonl`; multi-family drop-one evidence, when applicable, is in `final_metrics.json`.

## Why the strongest candidate improved

Observed: the fold-fitted TF-IDF/logistic rank blend beat the champion PR-AUC in five of six months. The gain was highly concentrated in November, where it found three violations in 22 reviews; it found no Top-5% violations in four months. Supported inference: lexical structure in templated opening summaries adds a limited recurrence signal beyond exact category encodings. Hypothesis, not established fact: repeated machine-generated alert wording identifies operational episodes. Unsupported conclusion: the experiment does not show that any word or incident cause is causal, and no vocabulary or raw text was persisted.

## P3 diagnostic (not used to select P2)

Across the same July-December walk-forward protocol, champion P3 PR-AUC was {p3_champion['pr_auc']:.5f} and the strongest P2 candidate's P3 PR-AUC was {p3_candidate['pr_auc']:.5f}. P3 metrics were logged in every experiment cycle but did not influence the P2 promotion decision.

## Leakage and point-in-time audit

- All 19 raw columns were classified in `column_audit.csv`.
- Forbidden post-outcome/direct-target fields were excluded from predictive matrices.
- `Grupo designado` remains temporally uncertain because the local snapshot has no assignment history and the referenced data dictionary was absent. It is included only in the champion reimplementation, not in the safe challenger.
- Training rows require both opening before the fold and outcome known before the fold.
- Arrival/recurrence features use left-open searches, so the current and simultaneous incidents are excluded.
- Historical outcome rates use only prior known resolution/closure events.
- All category maps, target encodings, imputers and text vocabularies are fitted inside each outer training fold.

## Facts, inferences, hypotheses, unsupported conclusions

- Observed fact: P2 KPI coverage begins in 2025; there are only 42 P2 violations total and 20 in July-December.
- Observed fact: closure/resolution coverage changes sharply by opening year.
- Supported inference: P2 evidence is dominated by a single collection regime and has high monthly variance.
- Tested hypothesis: workload, recurrence, novelty, prior outcomes, configuration identity, description history, interactions, calendar, segmented bursts, queue growth and text can improve ranking.
- Unsupported conclusion: the raw snapshot cannot establish the organizational cause of P2 violations or prove causal effects.

## Operational interpretation

Scores are ranking signals, not calibrated probabilities. A model passing the gate may prioritize only the top 5% of monthly P2 arrivals for human review; it must not auto-close, auto-escalate, deny service, or replace OLA rules. A NO-GO result means the raw snapshot should not be promoted for P2 prioritization.

## Limitations and confidence

Only 20 P2 violations occur across the six evaluation folds. All months have already been inspected, so confidence is exploratory and low for promotion even with paired folds and seed checks. The single-snapshot dataset cannot verify reassignment history or the cause of the 2025 regime change.

## Minimum additional data if NO-GO

Live queue depth and concurrent open P2/P3 at scoring time; group workload and staffing/on-call coverage; time to acknowledgement; product health telemetry; deployment/change events; alert correlation/recurrence identifiers; and escalation/assignment history. These distinguish “not predictive” from “not measured.”

## Reproduction

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/predictfy-locaweb/bin/python experiments/raw_opportunity_loop/reproduce.py
```
"""
    (EXPERIMENT_DIR / "final_report.md").write_text(report, encoding="utf-8")


def update_state(metrics: dict[str, Any]) -> None:
    state = f"""# Raw Opportunity Loop — State

- Status: {metrics['status']}
- Completed: {date.today().isoformat()}
- Cycles completed: {metrics['cycles_completed']}
- Final candidate: {metrics['final_candidate_name']}
- Final P2 PR-AUC: {metrics['final_candidate']['aggregate']['pr_auc']:.8f}
- Final Precision@Top-5%: {metrics['final_candidate']['aggregate']['precision_at_top_5pct']:.8f}
- Final Recall@Top-5%: {metrics['final_candidate']['aggregate']['recall_at_top_5pct']:.8f}
- Promotion gate passed: {metrics['promotion_gate']['passes']}
- Raw SHA-256: `{metrics['data_hashes']['raw']}`
- Processed SHA-256: `{metrics['data_hashes']['processed']}`
- Production artifacts were not modified.
"""
    (EXPERIMENT_DIR / "STATE.md").write_text(state, encoding="utf-8")


def reproduce() -> dict[str, Any]:
    expected_path = EXPERIMENT_DIR / "final_metrics.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    if _hash_file(RAW_PATH) != expected["data_hashes"]["raw"] or _hash_file(PROCESSED_PATH) != expected["data_hashes"]["processed"]:
        raise AssertionError("Input hashes differ from the original research run")
    bundle = load_data(); self_checks(); store = build_feature_store(bundle)
    champion = evaluate_xgb(bundle, store, [], seed=BASE_SEED, champion=True)
    config = expected["final_candidate"]["config"]
    if config["kind"] == "xgboost":
        candidate = evaluate_xgb(bundle, store, config.get("families", []), seed=config.get("seed", BASE_SEED), champion=False, specialist=config.get("p2_specialist", False))
    else:
        candidate = evaluate_text_blend(bundle, store, champion, seed=config.get("seed", BASE_SEED), p2_only=config.get("p2_only", False), blend_weight=config.get("blend_weight", 0.5))
    keys = ["pr_auc", "precision_at_top_5pct", "recall_at_top_5pct"]
    differences = {key: abs(candidate["aggregate"][key] - expected["final_candidate"]["aggregate"][key]) for key in keys}
    tolerance = 1e-12
    result = {
        "passed": all(value <= tolerance for value in differences.values()),
        "tolerance": tolerance, "absolute_differences": differences,
        "data_hashes_verified": True, "clean_process_pid": os.getpid(),
        "reproduced_metrics": _public_metrics(candidate),
    }
    _write_json(EXPERIMENT_DIR / "reproduction_check.json", result)
    if not result["passed"]: raise AssertionError(f"Reproduction mismatch: {differences}")
    print(json.dumps({"passed": True, "absolute_differences": differences}, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reproduce", action="store_true")
    args = parser.parse_args()
    if args.reproduce: reproduce()
    else: run_loop()


if __name__ == "__main__":
    main()
