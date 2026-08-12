"""Add raw Total/P2/P3 reconciliation and segment diagnostics to artifacts."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

import run_research as research


def load_raw_series() -> dict[str, pd.Series]:
    raw = pd.read_excel(
        research.RAW_PATH,
        usecols=["Aberto", "Entrou para KPI?", "Prioridade"],
    )
    raw["Aberto"] = pd.to_datetime(raw["Aberto"], errors="coerce")
    kpi = raw[raw["Entrou para KPI?"].eq("SIM") & raw["Aberto"].dt.year.eq(2025)].copy()
    kpi["data"] = kpi["Aberto"].dt.normalize()
    calendar = pd.date_range("2025-01-01", "2025-12-31", freq="D")

    def daily(mask: pd.Series | None = None) -> pd.Series:
        part = kpi if mask is None else kpi[mask]
        return part.groupby("data").size().reindex(calendar, fill_value=0).astype(float)

    return {
        "total": daily(),
        "p2": daily(kpi["Prioridade"].eq("2 - Alta")),
        "p3": daily(kpi["Prioridade"].eq("3 - Média")),
    }


def baseline_frame(series: pd.Series) -> pd.DataFrame:
    return research.predict_frame(
        series,
        research.TEST_START,
        research.TEST_END,
        lambda s, target, origin, horizon: research.seasonal_median(s, target, origin),
    )


def candidate_frame(series: pd.Series) -> pd.DataFrame:
    def predictor(s: pd.Series, target: pd.Timestamp, origin: pd.Timestamp, horizon: int) -> float:
        del horizon
        value = research.seasonal_median(s, target, origin)
        if ((target in research.HOLIDAYS_2025 and target.dayofweek < 5)
                or research.is_year_end_reduced_window(target)):
            value *= research.learned_weekday_holiday_factor(s, origin)
        return value

    return research.predict_frame(series, research.TEST_START, research.TEST_END, predictor)


def build_evidence(series: dict[str, pd.Series]) -> tuple[dict, dict]:
    gap = series["total"] - (series["p2"] + series["p3"])
    reconciliation = {
        "period": "2025-01-01/2025-12-31",
        "raw_priority_labels": {"p2": "2 - Alta", "p3": "3 - Média"},
        "daily_rows": int(len(gap)),
        "total_incidents": int(series["total"].sum()),
        "p2_incidents": int(series["p2"].sum()),
        "p3_incidents": int(series["p3"].sum()),
        "p2_plus_p3": int(series["p2"].sum() + series["p3"].sum()),
        "identity_holds_annual": bool(series["total"].sum() == series["p2"].sum() + series["p3"].sum()),
        "identity_holds_every_day": bool((gap == 0).all()),
        "mismatched_days": int((gap != 0).sum()),
        "maximum_absolute_daily_gap": float(gap.abs().max()),
    }
    expected = (25156, 5159, 19997)
    observed = (reconciliation["total_incidents"], reconciliation["p2_incidents"], reconciliation["p3_incidents"])
    if observed != expected or not reconciliation["identity_holds_every_day"]:
        raise AssertionError(f"Unexpected Total/P2/P3 reconciliation: {reconciliation}")

    metrics = {}
    for name, values in series.items():
        baseline = research.prediction_metrics(baseline_frame(values))
        candidate = research.prediction_metrics(candidate_frame(values))
        metrics[name] = {
            "baseline": baseline,
            "calendar_candidate": candidate,
            "paired_comparison": research.compare_to_baseline(candidate, baseline, eligible=True),
            "promotion_scope": name == "total",
            "note": (
                "Promotion gate is claimed on Total only. P2/P3 are diagnostic and were not used "
                "to select, weight, or sum the Total forecast."
            ),
        }
    return reconciliation, metrics


def seed_aggregated_synthetic_contribution(metrics: dict) -> dict:
    by_id = {cycle["cycle_id"]: cycle for cycle in metrics["cycles"]}

    def summary(cycle_id: str) -> dict:
        cycle = by_id[cycle_id]
        values = [float(item["test"]["aggregate_mae_mean_horizons"]) for item in cycle["per_seed"]]
        return {
            "cycle_id": cycle_id,
            "seed_values": {str(item["seed"]): float(item["test"]["aggregate_mae_mean_horizons"])
                            for item in cycle["per_seed"]},
            "seed_mean_mae": float(sum(values) / len(values)),
            "seed_std_mae": float(pd.Series(values).std(ddof=0)),
            "n_seeds": len(values),
            "promotion_eligible": bool(cycle["promotion_eligible"]),
        }

    real = summary("F03")
    mapping = {
        "equal_weight": "F06",
        "reduced_weight_0.25": "F07",
        "pretrain_real_finetune": "F08",
        "lag_initialization_only": "F09",
        "provided_file_equal_diagnostic": "F10",
    }
    strategies = {}
    for label, cycle_id in mapping.items():
        item = summary(cycle_id)
        item["incremental_mae_vs_real_only_seed_mean"] = item["seed_mean_mae"] - real["seed_mean_mae"]
        strategies[label] = item
    return {
        "attribution_metric": "mean D1-D7 MAE averaged across all deterministic seeds",
        "real_only_reference": real,
        "strategies": strategies,
        "note": (
            "Synthetic contribution is the strategy seed-mean minus the real-only seed-mean. "
            "Individual seed values are retained, but no first-seed value is used for attribution."
        ),
    }


def main() -> None:
    series = load_raw_series()
    reconciliation, segment_metrics = build_evidence(series)

    audit_path = research.WORK_DIR / "audit.json"
    metrics_path = research.WORK_DIR / "metrics.json"
    report_path = research.WORK_DIR / "report.md"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    audit["total_p2_p3_reconciliation"] = reconciliation
    metrics["series_scope"] = {
        "promoted_series": "total",
        "segment_metrics_are_diagnostic": True,
        "total_is_modeled_directly_not_summed": True,
    }
    metrics["segment_metrics"] = segment_metrics
    metrics["synthetic_contribution"] = seed_aggregated_synthetic_contribution(metrics)
    for cycle in metrics["cycles"]:
        if cycle["cycle_id"] == "F01":
            cycle["decision"] = "RETAIN"
        elif cycle["cycle_id"] == "F10":
            cycle["decision"] = "INELIGIBLE DIAGNOSTIC"
    research.write_json(audit_path, audit)
    research.write_json(metrics_path, metrics)
    with (research.WORK_DIR / "experiment_registry.jsonl").open("w", encoding="utf-8") as registry:
        for cycle in metrics["cycles"]:
            registry.write(json.dumps(research.json_safe(cycle), ensure_ascii=False) + "\n")

    report = report_path.read_text(encoding="utf-8")
    synthetic = metrics["synthetic_contribution"]
    real_mean = synthetic["real_only_reference"]["seed_mean_mae"]
    equal = synthetic["strategies"]["equal_weight"]
    reduced = synthetic["strategies"]["reduced_weight_0.25"]
    pretrain = synthetic["strategies"]["pretrain_real_finetune"]
    lag_init = synthetic["strategies"]["lag_initialization_only"]
    supplied = synthetic["strategies"]["provided_file_equal_diagnostic"]
    authoritative_synthetic_paragraph = (
        f"Fold-safe comparisons use seed means, with individual seeds retained in `metrics.json`. "
        f"Versus real-only Ridge MAE {real_mean:.4f}: equal augmentation was "
        f"{equal['seed_mean_mae']:.4f} (std {equal['seed_std_mae']:.4f}; delta "
        f"{equal['incremental_mae_vs_real_only_seed_mean']:+.4f}), 0.25-weight augmentation "
        f"{reduced['seed_mean_mae']:.4f} (std {reduced['seed_std_mae']:.4f}; delta "
        f"{reduced['incremental_mae_vs_real_only_seed_mean']:+.4f}), pretrain/fine-tune "
        f"{pretrain['seed_mean_mae']:.4f} (std {pretrain['seed_std_mae']:.4f}; delta "
        f"{pretrain['incremental_mae_vs_real_only_seed_mean']:+.4f}), and lag-only initialization "
        f"{lag_init['seed_mean_mae']:.4f} (std {lag_init['seed_std_mae']:.4f}; delta "
        f"{lag_init['incremental_mae_vs_real_only_seed_mean']:+.4f}). The supplied-file equal-weight "
        f"diagnostic scored {supplied['seed_mean_mae']:.4f}, but F10 is explicitly ineligible because "
        f"the generator used Q4 actuals. None displaced the real-only calendar challenger."
    )
    report, replacements = re.subn(
        r"Fold-safe comparisons regenerated blocks from each training prefix\..*?None displaced the real-only calendar challenger\.",
        authoritative_synthetic_paragraph,
        report,
        flags=re.DOTALL,
    )
    if replacements != 1:
        # On subsequent runs the paragraph is already authoritative.
        report = re.sub(
            r"Fold-safe comparisons use seed means, with individual seeds retained in `metrics\.json`\..*?None displaced the real-only calendar challenger\.",
            authoritative_synthetic_paragraph,
            report,
            flags=re.DOTALL,
        )
    report = report.replace(
        "| ID | Experiment | Family | Q4 MAE | Q4 WAPE | Decision |",
        "| ID | Experiment | Family | Q4 MAE (seed mean) | Q4 WAPE (seed mean) | Decision |",
    )
    for cycle in metrics["cycles"]:
        mean_wape = sum(float(item["test"]["aggregate_wape"]) for item in cycle["per_seed"]) / len(cycle["per_seed"])
        replacement = (
            f"| {cycle['cycle_id']} | {cycle['name']} | {cycle['family']} | "
            f"{cycle['seed_mae_mean']:.4f} | {mean_wape:.4f} | {cycle['decision']} |"
        )
        report = re.sub(rf"^\| {cycle['cycle_id']} \|.*$", replacement, report, flags=re.MULTILINE)
    by_id = {cycle["cycle_id"]: cycle for cycle in metrics["cycles"]}
    full_ridge = by_id["F03"]["seed_mae_mean"]
    ablation_text = (
        "Four explicit drop-family Ridge ablations were paired on the same Q4 rows. "
        f"Full Ridge MAE was {full_ridge:.4f}; dropping calendar/Fourier (F11) yielded "
        f"{by_id['F11']['seed_mae_mean']:.4f} ({by_id['F11']['seed_mae_mean']-full_ridge:+.4f}), "
        f"dropping rolling distribution (F12) {by_id['F12']['seed_mae_mean']:.4f} "
        f"({by_id['F12']['seed_mae_mean']-full_ridge:+.4f}), dropping trend/residual (F13) "
        f"{by_id['F13']['seed_mae_mean']:.4f} ({by_id['F13']['seed_mae_mean']-full_ridge:+.4f}), "
        f"and dropping aligned/state lags (F14) {by_id['F14']['seed_mae_mean']:.4f} "
        f"({by_id['F14']['seed_mae_mean']-full_ridge:+.4f}). The broad linear model was rejected: "
        "several families reduced its extrapolation error when removed, yet every ablation still lost "
        "to the active seasonal baseline. The promoted hybrid retains only same-weekday median lags, "
        "calendar-known event windows, and a causally estimated prior-holiday factor."
    )
    report = re.sub(
        r"Four explicit drop-family Ridge ablations.*?factor estimated from outcomes already observed by each origin\.",
        ablation_text,
        report,
        flags=re.DOTALL,
    )
    baseline_months = metrics["baseline"]["months"]
    candidate_months = metrics["final_candidate"]["months"]
    month_rows = "\n".join(
        f"| {month} | {baseline_months[month]['mae']:.4f} | {candidate_months[month]['mae']:.4f} | "
        f"{(baseline_months[month]['mae']-candidate_months[month]['mae'])/baseline_months[month]['mae']*100:.2f}% | "
        f"{baseline_months[month]['wape']:.4f} | {candidate_months[month]['wape']:.4f} |"
        for month in ("2025-10", "2025-11", "2025-12")
    )
    temporal_text = f"""The rule is neutral outside its declared event window, so October is exactly unchanged. It improves both affected months: November through its known weekday holiday and December through Christmas/year-end activity.

| Target month | Baseline MAE | Candidate MAE | MAE reduction | Baseline WAPE | Candidate WAPE |
|---|---:|---:|---:|---:|---:|
{month_rows}

The effect is stable by mechanism (neutral when inactive; lower error in both active months), but only one real Christmas/year-end period exists. A future-year canary is therefore required before unconditional rollout. Aggregate bias changed from {metrics['baseline']['aggregate_bias']:.3f} to {metrics['final_candidate']['aggregate_bias']:.3f} incidents per forecast."""
    report = re.sub(
        r"The rule is neutral on dates outside its declared event window\..*?incidents per forecast\.",
        temporal_text,
        report,
        flags=re.DOTALL,
    )
    marker = "## Total/P2/P3 reconciliation"
    if marker in report:
        report = report.split(marker)[0].rstrip() + "\n"
    rows = []
    for name in ("total", "p2", "p3"):
        item = segment_metrics[name]
        bm = item["baseline"]["aggregate_mae_mean_horizons"]
        cm = item["calendar_candidate"]["aggregate_mae_mean_horizons"]
        rows.append(
            f"| {name.upper()} | {bm:.4f} | {cm:.4f} | {(bm-cm)/bm*100:.2f}% | "
            f"{item['paired_comparison']['horizon_wins']}/7 |"
        )
    report += f"""

## Total/P2/P3 reconciliation

Raw 2025 KPI totals reconcile exactly on every calendar day: **{reconciliation['total_incidents']:,} Total = {reconciliation['p2_incidents']:,} P2 + {reconciliation['p3_incidents']:,} P3**, with {reconciliation['mismatched_days']} mismatched days and maximum absolute daily gap {reconciliation['maximum_absolute_daily_gap']:.0f}. The exact raw labels are `2 - Alta` and `3 - Média`.

| Series | Active baseline MAE | Calendar candidate MAE | Reduction | Horizon wins |
|---|---:|---:|---:|---:|
{chr(10).join(rows)}

The promotion claim applies to **Total only**. Total is forecast directly; P2/P3 diagnostics are neither summed into the candidate nor used to select its adjustment. This avoids concealing segment-specific error behind reconciliation.
"""
    report_path.write_text(report, encoding="utf-8")
    print(json.dumps({"reconciliation": reconciliation, "segments": {
        k: {"baseline_mae": v["baseline"]["aggregate_mae_mean_horizons"],
            "candidate_mae": v["calendar_candidate"]["aggregate_mae_mean_horizons"]}
        for k, v in segment_metrics.items()
    }}, indent=2))


if __name__ == "__main__":
    main()
