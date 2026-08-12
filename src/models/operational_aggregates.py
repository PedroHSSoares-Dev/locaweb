"""Privacy-preserving historical aggregates for group and product endpoints."""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).parents[2]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "LW-DATASET.xlsx"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "segmentos_ola.json"
MIN_INCIDENTS = 100
MIN_VIOLATIONS = 10


def _wilson(successes: int, total: int, z: float = 1.96) -> list[float]:
    rate = successes / total
    denominator = 1 + z**2 / total
    center = (rate + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt((rate * (1 - rate) + z**2 / (4 * total)) / total) / denominator
    return [round(max(0.0, center - margin) * 100, 3), round(min(1.0, center + margin) * 100, 3)]


def _aggregate(data: pd.DataFrame, column: str, label: str) -> list[dict[str, Any]]:
    rows = []
    for value, group in data.groupby(column, dropna=False):
        total = int(len(group))
        violations = int(group["violou"].sum())
        if total < MIN_INCIDENTS or violations < MIN_VIOLATIONS:
            continue
        rows.append({
            label: str(value) if pd.notna(value) else "DESCONHECIDO",
            "nIncidentes": total,
            "violacoes": violations,
            "taxaViolacaoReal": round(violations / total * 100, 3),
            "intervaloConfianca95": _wilson(violations, total),
            "pctP2": round(float(group["Prioridade"].eq("2 - Alta").mean() * 100), 1),
        })
    return sorted(rows, key=lambda item: (-item["taxaViolacaoReal"], -item["nIncidentes"]))


def build_aggregates(raw_path: Path = RAW_PATH) -> dict[str, Any]:
    raw = pd.read_excel(raw_path)
    kpi = raw[
        raw["Entrou para KPI?"].eq("SIM")
        & raw["Prioridade"].isin(["2 - Alta", "3 - Média"])
        & raw["Aberto"].dt.year.eq(2025)
    ].copy()
    kpi["violou"] = kpi["KPI Violado?"].eq("SIM").astype(int)
    kpi["Produto"] = kpi["Produto"].fillna("DESCONHECIDO")
    kpi["Grupo designado"] = kpi["Grupo designado"].fillna("DESCONHECIDO")
    return {
        "modelo": "agregados_operacionais_ola",
        "gerado_em": date.today().isoformat(),
        "ano_referencia": 2025,
        "ground_truth": "KPI Violado?",
        "supressao": {
            "min_incidentes": MIN_INCIDENTS,
            "min_violacoes": MIN_VIOLATIONS,
        },
        "grupos": _aggregate(kpi, "Grupo designado", "grupo"),
        "produtos": _aggregate(kpi, "Produto", "produto"),
    }


def export_aggregates(result: dict[str, Any], path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as destination:
        json.dump(result, destination, ensure_ascii=False, indent=2)


def main() -> None:
    result = build_aggregates()
    export_aggregates(result)
    print(f"OK: {len(result['grupos'])} grupos e {len(result['produtos'])} produtos publicados")


if __name__ == "__main__":
    main()
