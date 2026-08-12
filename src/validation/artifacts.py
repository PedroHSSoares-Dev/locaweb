"""Fail-fast validation for every ML artifact consumed by the API.

This module intentionally uses only the Python standard library so it can run
as a cheap CI gate without installing the training stack or accessing raw data.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).parents[2]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
COMMON_PROTOCOL = "rolling_origin_2025Q4_D1_D7"


class ArtifactValidationError(ValueError):
    """Raised when a deployable artifact violates its public contract."""


def _load(directory: Path, filename: str) -> dict[str, Any]:
    path = directory / filename
    if not path.exists():
        raise ArtifactValidationError(f"Artefato obrigatório ausente: {filename}")
    try:
        with path.open(encoding="utf-8") as source:
            value = json.load(source)
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError(f"JSON inválido em {filename}: {exc}") from exc
    if not isinstance(value, dict):
        raise ArtifactValidationError(f"{filename} deve conter um objeto JSON")
    return value


def _finite(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ArtifactValidationError(f"{label} deve ser numérico e finito")
    return float(value)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise ArtifactValidationError(message)


def _validate_risk(data: dict[str, Any]) -> None:
    _assert(data.get("protocolo_validacao") == "treino_ate_jun_validacao_q3_teste_q4_sem_embaralhamento",
            "risco_ola.json não usa split temporal auditável")
    metrics = data.get("metricas", {})
    total = int(_finite(metrics.get("total_teste"), "risco.metricas.total_teste"))
    bands = data.get("distribuicao_risco", {})
    _assert(set(bands) == {"baixo", "medio", "alto"}, "Faixas de risco devem ser baixo/médio/alto")
    ordered = [bands[key] for key in ("baixo", "medio", "alto")]
    _assert(sum(int(item.get("count", -1)) for item in ordered) == total,
            "Contagens das faixas de risco não fecham com total_teste")
    _assert(abs(sum(_finite(item.get("pct"), "risco.faixa.pct") for item in ordered) - 100) <= 0.05,
            "Percentuais das faixas de risco não fecham 100%")
    previous = 0.0
    for index, item in enumerate(ordered):
        lower = _finite(item.get("limite_inferior"), "risco.faixa.limite_inferior")
        upper = _finite(item.get("limite_superior"), "risco.faixa.limite_superior")
        _assert(abs(lower - previous) <= 1e-6, "Faixas de risco têm lacuna ou sobreposição")
        _assert(upper >= lower, "Faixa de risco invertida")
        previous = upper
        if index == 2:
            _assert(abs(upper - 1.0) <= 1e-6, "Faixa alta deve terminar em 1")
    split = data.get("split_temporal", {})
    periods = [split.get(key, {}) for key in ("treino", "validacao", "teste")]
    dates = [
        (date.fromisoformat(item["inicio"][:10]), date.fromisoformat(item["fim"][:10]))
        for item in periods
    ]
    _assert(dates[0][1] <= dates[1][0] <= dates[1][1] <= dates[2][0],
            "Treino, validação e teste do XGBoost não estão em ordem temporal")


def _validate_forecasts(
    lstm: dict[str, Any], prophet: dict[str, Any], prophet_mc: dict[str, Any], baseline: dict[str, Any],
    comparison: dict[str, Any],
) -> None:
    _assert(lstm.get("protocolo_validacao") == COMMON_PROTOCOL, "LSTM sem protocolo comum")
    _assert(prophet.get("protocolo_validacao") == COMMON_PROTOCOL, "Prophet sem protocolo comum")
    _assert(prophet_mc.get("protocolo_validacao") == COMMON_PROTOCOL, "Prophet MC sem protocolo comum")
    _assert(baseline.get("protocolo_validacao") == COMMON_PROTOCOL, "Baseline sem protocolo comum")
    _assert(comparison.get("protocolo") == COMMON_PROTOCOL and comparison.get("comparaveis") is True,
            "Comparação LSTM × Prophet não é auditável")
    expected_dates = [(date(2026, 1, 1) + timedelta(days=index)).isoformat() for index in range(7)]
    lstm_dates = [point.get("ds") for point in lstm.get("serie", [])]
    _assert(lstm_dates == expected_dates, "LSTM deve publicar exatamente D+1…D+7 após 31/12/2025")
    _assert([point.get("ds") for point in baseline.get("serie", [])] == expected_dates,
            "Baseline deve publicar exatamente D+1…D+7 após 31/12/2025")
    for series in ("total", "p2", "p3"):
        metrics_lstm = lstm.get("metricas_holdout_comum", {}).get(series, {}).get("horizontes", {})
        metrics_prophet = prophet.get(series, {}).get("metricas", {}).get("por_horizonte", {})
        metrics_prophet_mc = prophet_mc.get(series, {}).get("metricas", {}).get("por_horizonte", {})
        metrics_baseline = baseline.get("metricas_holdout_comum", {}).get(series, {}).get("horizontes", {})
        compared = comparison.get("series", {}).get(series, {}).get("por_horizonte", {})
        _assert(set(metrics_lstm) == {f"D{i}" for i in range(1, 8)}, f"LSTM {series} sem D1…D7")
        _assert(set(metrics_prophet) == {f"D{i}" for i in range(1, 8)}, f"Prophet {series} sem D1…D7")
        _assert(set(metrics_prophet_mc) == {f"D{i}" for i in range(1, 8)}, f"Prophet MC {series} sem D1…D7")
        _assert(set(metrics_baseline) == {f"D{i}" for i in range(1, 8)}, f"Baseline {series} sem D1…D7")
        _assert(set(compared) == {f"D{i}" for i in range(1, 8)}, f"Comparação {series} sem D1…D7")
        forecast = prophet.get(series, {}).get("serie_7d", [])
        _assert([point.get("ds") for point in forecast] == expected_dates,
                f"Prophet {series} deve publicar exatamente D+1…D+7")
        for horizon in range(1, 8):
            key = f"D{horizon}"
            lm = _finite(metrics_lstm[key].get("mae"), f"LSTM {series}.{key}.mae")
            pm = _finite(metrics_prophet[key].get("mae"), f"Prophet {series}.{key}.mae")
            pmm = _finite(metrics_prophet_mc[key].get("mae"), f"Prophet MC {series}.{key}.mae")
            bm = _finite(metrics_baseline[key].get("mae"), f"Baseline {series}.{key}.mae")
            _assert(abs(lm - _finite(compared[key].get("lstm_mae"), "comparação LSTM")) <= 0.011,
                    f"Comparação diverge do LSTM em {series}/{key}")
            _assert(abs(pm - _finite(compared[key].get("prophet_mae"), "comparação Prophet")) <= 0.011,
                    f"Comparação diverge do Prophet em {series}/{key}")
            _assert(abs(pmm - _finite(compared[key].get("prophet_mc_mae"), "comparação Prophet MC")) <= 0.011,
                    f"Comparação diverge do Prophet MC em {series}/{key}")
            _assert(abs(bm - _finite(compared[key].get("baseline_sazonal_mae"), "comparação baseline")) <= 0.011,
                    f"Comparação diverge do baseline em {series}/{key}")


def _validate_kpi(data: dict[str, Any]) -> None:
    expected = {"P2": (36.0, 39.0), "P3": (231.0, 263.0)}
    for priority, (minimum, maximum) in expected.items():
        item = data.get(priority, {})
        central = (minimum + maximum) / 2
        _assert(abs(_finite(item.get("metaAnual"), f"KPI {priority}.metaAnual") - central) < 1e-9,
                f"Meta central {priority} deve preservar decimal exato")
        violations = _finite(item.get("violacoesAno"), f"KPI {priority}.violacoesAno")
        pct = _finite(item.get("pctUtilizado"), f"KPI {priority}.pctUtilizado")
        _assert(abs(pct - round(violations / central * 100, 1)) < 1e-9,
                f"pctUtilizado {priority} inconsistente")
        _assert(abs(_finite(item.get("margemRestante"), f"KPI {priority}.margemRestante") - (central - violations)) < 1e-9,
                f"margemRestante {priority} inconsistente")


def _validate_clusters(data: dict[str, Any]) -> None:
    clusters = data.get("clusters", [])
    _assert(len(clusters) == data.get("k"), "Quantidade de clusters diverge de K")
    expected_total = int(_finite(data.get("metricas", {}).get("total_incidentes"), "clusters.total_incidentes"))
    _assert(sum(int(item.get("tamanho", -1)) for item in clusters) == expected_total,
            "Tamanhos dos clusters não fecham com total_incidentes")
    _assert(abs(sum(_finite(item.get("pct_total"), "cluster.pct_total") for item in clusters) - 100) <= 0.1,
            "Percentuais dos clusters não fecham 100%")


def _validate_segments(data: dict[str, Any]) -> None:
    suppression = data.get("supressao", {})
    min_incidents = int(suppression.get("min_incidentes", 0))
    min_violations = int(suppression.get("min_violacoes", 0))
    _assert(min_incidents >= 100 and min_violations >= 10, "Supressão de segmentos está abaixo do mínimo")
    for collection in ("grupos", "produtos"):
        for item in data.get(collection, []):
            total = int(item.get("nIncidentes", 0))
            violations = int(item.get("violacoes", 0))
            _assert(total >= min_incidents and violations >= min_violations,
                    f"{collection} contém segmento abaixo do limite de privacidade")
            rate = _finite(item.get("taxaViolacaoReal"), f"{collection}.taxaViolacaoReal")
            _assert(abs(rate - round(violations / total * 100, 3)) <= 0.001,
                    f"Taxa observada inconsistente em {collection}")


def validate_artifacts(directory: Path = OUTPUTS_DIR) -> list[str]:
    risk = _load(directory, "risco_ola.json")
    clusters = _load(directory, "clusters.json")
    kpi = _load(directory, "kpi_atingimento.json")
    lstm = _load(directory, "previsoes_lstm.json")
    prophet = _load(directory, "previsoes_volume.json")
    prophet_mc = _load(directory, "previsoes_volume_mc.json")
    baseline = _load(directory, "previsoes_baseline.json")
    comparison = _load(directory, "comparacao_modelos.json")
    segments = _load(directory, "segmentos_ola.json")
    horizon = _load(directory, "previsoes_horizonte_prophet.json")
    registry = _load(directory, "model_registry.json")

    _validate_risk(risk)
    _validate_clusters(clusters)
    _validate_kpi(kpi)
    _validate_forecasts(lstm, prophet, prophet_mc, baseline, comparison)
    _validate_segments(segments)
    _assert(registry.get("schema_version") == 1, "Registro canônico de modelos inválido")
    for task in ("volume_d1_d7", "ola_risk_triage"):
        active = [
            item for item in registry.get("models", [])
            if item.get("task") == task and item.get("status") == "active"
        ]
        _assert(len(active) == 1, f"{task} deve possuir exatamente um modelo ativo")
    _assert(int(horizon.get("horizonte_validado_dias", 0)) == 7,
            "Horizonte exploratório deve declarar somente D+7 como validado")
    for series, active_key in (("total", "total"), ("p2", "P2"), ("p3", "P3")):
        long_points = horizon.get("series", {}).get(series, [])[:7]
        short_points = baseline.get("serie", [])
        _assert(len(long_points) == len(short_points) == 7, f"Horizonte curto ausente para {series}")
        for long_point, short_point in zip(long_points, short_points):
            _assert(long_point.get("ds") == short_point.get("ds"), f"Datas D1–D7 divergem em {series}")
            _assert(abs(_finite(long_point.get("yhat"), "horizonte.yhat") - float(short_point[active_key])) < 1e-9,
                    f"Horizonte longo diverge da previsão ativa em D1–D7/{series}")
    return [
        "risco_ola", "clusters", "kpi_atingimento", "previsoes_lstm",
        "previsoes_volume", "previsoes_volume_mc", "previsoes_baseline",
        "comparacao_modelos", "segmentos_ola",
        "previsoes_horizonte_prophet", "model_registry",
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", type=Path, default=OUTPUTS_DIR)
    args = parser.parse_args()
    validated = validate_artifacts(args.outputs)
    print(f"OK: {len(validated)} artefatos validados — {', '.join(validated)}")


if __name__ == "__main__":
    main()
