#!/usr/bin/env python3
"""Reproduce the operational research in a clean child process and compare metrics."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


WORK_DIR = Path(__file__).resolve().parent
LAB = WORK_DIR / "operational_lab.py"
CANONICAL = WORK_DIR / "metrics.json"
CHECK = WORK_DIR / "reproduction_check.json"
TOL = 1e-12


def _collect(metrics: dict[str, Any]) -> dict[str, Any]:
    cycles = {
        x["name"]: {
            "pr_auc": x["metrics"]["aggregate"]["pr_auc"],
            "top20_precision": x["metrics"]["aggregate"]["top20_precision"],
            "top20_recall": x["metrics"]["aggregate"]["top20_recall"],
            "relative_gain": x["gate"]["pr_auc_relative_improvement"],
            "monthly_wins": x["gate"]["monthly_wins"],
        }
        for x in metrics["cycles"]
    }
    return {
        "raw_sha256": metrics["data_audit"]["sha256"],
        "target_evaluation_days": metrics["target_audit"]["evaluation_days"],
        "target_evaluation_positives": metrics["target_audit"]["evaluation_positives"],
        "baseline_pr_auc": metrics["baseline"]["metrics"]["aggregate"]["pr_auc"],
        "baseline_top20_precision": metrics["baseline"]["metrics"]["aggregate"]["top20_precision"],
        "baseline_top20_recall": metrics["baseline"]["metrics"]["aggregate"]["top20_recall"],
        "strongest_name": metrics["strongest"]["name"],
        "strongest_pr_auc": metrics["strongest"]["metrics"]["aggregate"]["pr_auc"],
        "strongest_relative_gain": metrics["strongest"]["gate"]["pr_auc_relative_improvement"],
        "strongest_monthly_wins": metrics["strongest"]["gate"]["monthly_wins"],
        "strongest_seed_pr_auc": [x["pr_auc"] for x in metrics["strongest"]["seed_stability"]["per_seed"]],
        "promotion_gate_passed": metrics["strongest"]["promotion_gate_passed"],
        "cycles": cycles,
    }


def _compare(expected: Any, actual: Any, path: str = "root") -> tuple[list[str], float]:
    mismatches: list[str] = []
    max_delta = 0.0
    if isinstance(expected, dict) and isinstance(actual, dict):
        if set(expected) != set(actual):
            mismatches.append(f"{path}: keys differ")
        for key in sorted(set(expected) & set(actual)):
            child, delta = _compare(expected[key], actual[key], f"{path}.{key}")
            mismatches.extend(child)
            max_delta = max(max_delta, delta)
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            mismatches.append(f"{path}: lengths differ")
        for idx, (left, right) in enumerate(zip(expected, actual)):
            child, delta = _compare(left, right, f"{path}[{idx}]")
            mismatches.extend(child)
            max_delta = max(max_delta, delta)
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        delta = abs(float(expected) - float(actual))
        max_delta = max(max_delta, delta)
        if delta > TOL:
            mismatches.append(f"{path}: |expected-actual|={delta}")
    elif expected != actual:
        mismatches.append(f"{path}: expected {expected!r}, actual {actual!r}")
    return mismatches, max_delta


def main() -> None:
    canonical = json.loads(CANONICAL.read_text(encoding="utf-8"))
    expected = _collect(canonical)
    with tempfile.TemporaryDirectory(prefix="locaweb-operational-reproduce-") as tmp:
        temp_root = Path(tmp)
        output_dir = temp_root / "output"
        model_dir = temp_root / "models"
        env = os.environ.copy()
        env.update({
            "PYTHONHASHSEED": "0", "OMP_NUM_THREADS": "2",
            "OPENBLAS_NUM_THREADS": "2", "MKL_NUM_THREADS": "2",
            "VECLIB_MAXIMUM_THREADS": "2",
        })
        completed = subprocess.run(
            [sys.executable, str(LAB), "--output-dir", str(output_dir), "--model-dir", str(model_dir)],
            cwd=str(WORK_DIR.parents[3]), env=env, text=True, capture_output=True,
            check=False, timeout=600,
        )
        if completed.returncode != 0:
            result = {
                "success": False, "reason": "child process failed",
                "returncode": completed.returncode,
                "stderr_tail": completed.stderr[-2000:],
                "generated_at": datetime.now().astimezone().isoformat(),
            }
            CHECK.write_text(json.dumps(result, indent=2), encoding="utf-8")
            raise SystemExit(json.dumps(result, indent=2))
        actual_metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
        actual = _collect(actual_metrics)
    mismatches, max_delta = _compare(expected, actual)
    result = {
        "success": not mismatches,
        "clean_child_process": True,
        "tolerance": TOL,
        "max_absolute_numeric_difference": max_delta,
        "mismatches": mismatches,
        "canonical_raw_sha256": expected["raw_sha256"],
        "candidate": expected["strongest_name"],
        "generated_at": datetime.now().astimezone().isoformat(),
    }
    CHECK.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
