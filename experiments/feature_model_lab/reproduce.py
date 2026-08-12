"""Reproduce all retained feature-model-lab candidates in clean processes."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


LAB_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = LAB_DIR.parents[1]
WORKSTREAM_DIR = LAB_DIR / "workstreams"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _passed(payload: dict) -> bool:
    return bool(
        payload.get("passed", payload.get("success", False))
        or str(payload.get("status", "")).upper() == "PASS"
    )


def main() -> None:
    commands = {
        "risk": WORKSTREAM_DIR / "risk" / "reproduce.py",
        "forecasting": WORKSTREAM_DIR / "forecasting" / "reproduce.py",
        "operational": WORKSTREAM_DIR / "operational" / "reproduce.py",
    }
    for track, script in commands.items():
        if not script.exists():
            raise FileNotFoundError(f"Missing {track} reproduction script: {script}")
        subprocess.run([sys.executable, str(script)], cwd=PROJECT_ROOT, check=True)

    checks = {
        track: _read_json(WORKSTREAM_DIR / track / "reproduction_check.json")
        for track in commands
    }
    passed = all(_passed(check) for check in checks.values())
    result = {
        "passed": passed,
        "clean_child_processes": True,
        "generated_at": datetime.now().astimezone().isoformat(),
        "tracks": {
            track: {
                "passed": _passed(check),
                "check_file": str(
                    (WORKSTREAM_DIR / track / "reproduction_check.json").relative_to(PROJECT_ROOT)
                ),
            }
            for track, check in checks.items()
        },
    }
    (LAB_DIR / "reproduction_check.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not passed:
        raise AssertionError(f"At least one workstream failed reproduction: {result}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
