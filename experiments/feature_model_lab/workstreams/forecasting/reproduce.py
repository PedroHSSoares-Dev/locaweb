"""Clean-process reproduction for the retained forecasting candidate."""
from __future__ import annotations

import json
import math
from pathlib import Path

import run_research as research
from add_segment_evidence import build_evidence, load_raw_series


TOLERANCE = 1e-12


def compare_numeric(path: str, observed, expected, differences: dict[str, float]) -> None:
    if isinstance(expected, dict):
        if not isinstance(observed, dict):
            raise AssertionError(f"{path}: observed value is not an object")
        for key, value in expected.items():
            if key in {"months"}:
                # Monthly values are still checked recursively; this branch is
                # retained to make the intended scope explicit.
                pass
            if key not in observed:
                raise AssertionError(f"{path}.{key}: missing")
            compare_numeric(f"{path}.{key}", observed[key], value, differences)
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        delta = abs(float(observed) - float(expected))
        differences[path] = delta
        if not math.isfinite(delta) or delta > TOLERANCE:
            raise AssertionError(f"{path}: delta {delta} > {TOLERANCE}")
    elif observed != expected:
        raise AssertionError(f"{path}: {observed!r} != {expected!r}")


def candidate_frame(series):
    def predictor(s, target, origin, horizon):
        del horizon
        value = research.seasonal_median(s, target, origin)
        if ((target in research.HOLIDAYS_2025 and target.dayofweek < 5)
                or research.is_year_end_reduced_window(target)):
            value *= research.learned_weekday_holiday_factor(s, origin)
        return value
    return research.predict_frame(series, research.TEST_START, research.TEST_END, predictor)


def main() -> None:
    expected = json.loads((research.WORK_DIR / "metrics.json").read_text(encoding="utf-8"))
    audit = json.loads((research.WORK_DIR / "audit.json").read_text(encoding="utf-8"))
    config = json.loads((research.MODEL_DIR / "calendar_adjusted_seasonal_config.json").read_text(encoding="utf-8"))
    frame = research.load_source_frame()
    csv_real = research.load_real_series(frame)
    raw_series = load_raw_series()
    if not csv_real.equals(raw_series["total"]):
        raise AssertionError("CSV real Total differs from raw Total")

    baseline_frame = research.predict_frame(
        csv_real, research.TEST_START, research.TEST_END,
        lambda s, target, origin, horizon: research.seasonal_median(s, target, origin),
    )
    observed_baseline = research.prediction_metrics(baseline_frame)
    observed_candidate = research.prediction_metrics(candidate_frame(csv_real))
    differences: dict[str, float] = {}
    compare_numeric("baseline", observed_baseline, expected["baseline"], differences)
    compare_numeric("candidate", observed_candidate, expected["final_candidate"], differences)

    reconciliation, segments = build_evidence(raw_series)
    compare_numeric("reconciliation", reconciliation, audit["total_p2_p3_reconciliation"], differences)
    for name in ("total", "p2", "p3"):
        compare_numeric(
            f"segments.{name}.baseline", segments[name]["baseline"],
            expected["segment_metrics"][name]["baseline"], differences,
        )
        compare_numeric(
            f"segments.{name}.candidate", segments[name]["calendar_candidate"],
            expected["segment_metrics"][name]["calendar_candidate"], differences,
        )

    gate = research.compare_to_baseline(observed_candidate, observed_baseline, eligible=True)
    compare_numeric("gate", gate, expected["promotion_gate"], differences)
    repeated_maes = []
    for ignored_seed in research.SEEDS:
        del ignored_seed
        repeated_maes.append(research.prediction_metrics(candidate_frame(csv_real))["aggregate_mae_mean_horizons"])
    max_seed_difference = max(repeated_maes) - min(repeated_maes)
    if max_seed_difference != 0.0:
        raise AssertionError("Deterministic candidate changed across seed labels")

    source_hashes = {
        "csv": research.sha256(research.CSV_PATH),
        "generator": research.sha256(research.GENERATOR_PATH),
    }
    if source_hashes != expected["source_hashes"]:
        raise AssertionError("Source hashes changed")
    if config["source_csv_sha256"] != source_hashes["csv"]:
        raise AssertionError("Saved candidate config source hash changed")

    result = {
        "status": "PASS",
        "process": "fresh Python interpreter",
        "tolerance": TOLERANCE,
        "source_hashes": source_hashes,
        "candidate": config["name"],
        "baseline_mae": observed_baseline["aggregate_mae_mean_horizons"],
        "candidate_mae": observed_candidate["aggregate_mae_mean_horizons"],
        "promotion_gate_passed": gate["passed"],
        "seed_labels": list(research.SEEDS),
        "seed_maes": repeated_maes,
        "max_seed_difference": max_seed_difference,
        "reconciliation": reconciliation,
        "segment_mae": {
            name: {
                "baseline": segments[name]["baseline"]["aggregate_mae_mean_horizons"],
                "candidate": segments[name]["calendar_candidate"]["aggregate_mae_mean_horizons"],
            }
            for name in ("total", "p2", "p3")
        },
        "numeric_values_checked": len(differences),
        "maximum_absolute_numeric_difference": max(differences.values(), default=0.0),
    }
    research.write_json(research.WORK_DIR / "reproduction_check.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
