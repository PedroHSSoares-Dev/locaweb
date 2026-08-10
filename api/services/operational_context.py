"""Build the canonical, compact operational context used by API and chatbot."""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any

from api.services.data_loader import load_json


OLA_TARGETS = {"P2": "4h", "P3": "12h"}
METAS_ANUAIS = {"P2": "36-39", "P3": "231-263"}
VIOLACOES_2025 = {"P2": 42, "P3": 196}
DATA_FIM_OBSERVADA = "2025-12-31"


def _application_current_date() -> date:
    """Return the canonical current date inside the application's data universe."""
    configured = os.getenv(
        "CHAT_CURRENT_DATE",
        os.getenv("CHAT_REFERENCE_DATE", DATA_FIM_OBSERVADA),
    ).strip()
    try:
        return date.fromisoformat(configured)
    except ValueError:
        return date.fromisoformat(DATA_FIM_OBSERVADA)


def _round_positive(value: float | int | None) -> int | None:
    if value is None:
        return None
    return round(max(float(value), 0))


def _forecast_point(source: dict[str, Any], index: int, values: dict[str, Any]) -> dict[str, Any]:
    """Attach the forecast target date so an archived horizon is never called current."""
    series = source.get("serie", [])
    try:
        point = series[index]
    except (IndexError, TypeError):
        point = {}
    target = point.get("ds")
    stale = False
    if target:
        try:
            stale = date.fromisoformat(target) < _application_current_date()
        except ValueError:
            target = None
    return {**values, "data_alvo": target, "status_stale": stale}


def _build_forecasts() -> dict[str, Any]:
    lstm = load_json("previsoes_lstm.json")
    monte_carlo = load_json("previsoes_volume_mc.json")
    prophet = load_json("previsoes_volume.json")

    if lstm:
        mae_raw = lstm.get("mae_holdout_92_dias")
        mae = mae_raw.get("total") if isinstance(mae_raw, dict) else mae_raw
        return {
            "disponivel": True,
            "modelo_ativo": "lstm_v2",
            "mae_92_dias": mae,
            "gerado_em": lstm.get("gerado_em"),
            "D1": _forecast_point(
                lstm,
                0,
                {key: _round_positive(lstm.get("d1", {}).get(key)) for key in ("total", "p2", "p3")},
            ),
            "D7": _forecast_point(
                lstm,
                -1,
                {key: _round_positive(lstm.get("d7", {}).get(key)) for key in ("total", "p2", "p3")},
            ),
        }

    if monte_carlo:
        metadata = {"serie": monte_carlo.get("total", {}).get("serie_7d", [])}
        return {
            "disponivel": True,
            "modelo_ativo": "prophet_mc_ensemble",
            "mae_92_dias": None,
            "gerado_em": monte_carlo.get("total", {}).get("gerado_em"),
            "D1": _forecast_point(metadata, 0, {
                key: _round_positive(monte_carlo.get(key, {}).get("D1", {}).get("yhat"))
                for key in ("total", "p2", "p3")
            }),
            "D7": _forecast_point(metadata, -1, {
                key: _round_positive(monte_carlo.get(key, {}).get("D7", {}).get("yhat"))
                for key in ("total", "p2", "p3")
            }),
        }

    if prophet:
        metadata = {"serie": prophet.get("total", {}).get("serie_7d", [])}
        return {
            "disponivel": True,
            "modelo_ativo": "prophet_original",
            "mae_92_dias": None,
            "gerado_em": prophet.get("total", {}).get("gerado_em"),
            "D1": _forecast_point(metadata, 0, {
                key: _round_positive(prophet.get(key, {}).get("D1", {}).get("yhat"))
                for key in ("total", "p2", "p3")
            }),
            "D7": _forecast_point(metadata, -1, {
                key: _round_positive(prophet.get(key, {}).get("D7", {}).get("yhat"))
                for key in ("total", "p2", "p3")
            }),
        }

    return {"disponivel": False}


def _build_risk() -> dict[str, Any]:
    data = load_json("risco_ola.json")
    if not data:
        return {"disponivel": False}

    metrics = data.get("metricas", {})
    return {
        "disponivel": True,
        "gerado_em": data.get("gerado_em"),
        "periodo_avaliacao": "conjunto de teste temporal histórico; não representa estado atual",
        "threshold_otimizado": data.get("threshold_otimizado"),
        "score_calibrado_como_probabilidade": False,
        "metricas": {
            key: metrics.get(key)
            for key in (
                "recall_violacao",
                "precision_violacao",
                "f1_violacao",
                "roc_auc",
                "pr_auc",
                "tp",
                "fp",
                "fn",
                "tn",
                "total_teste",
            )
        },
        "por_prioridade": data.get("risco_por_prioridade", {}),
        "top_fatores": data.get("feature_importance_shap", [])[:5],
    }


def _build_clusters() -> dict[str, Any]:
    data = load_json("clusters.json")
    if not data:
        return {"disponivel": False}

    clusters = data.get("clusters", [])
    ordered = sorted(clusters, key=lambda item: item.get("taxaViolacao", 0), reverse=True)
    compact = [
        {
            "id": item.get("id"),
            "label": item.get("label"),
            "descricao": item.get("descricao"),
            "tamanho": item.get("tamanho"),
            "taxa_violacao_pct": item.get("taxaViolacao"),
            "perfil": item.get("perfil", {}),
        }
        for item in ordered
    ]
    metrics = data.get("metricas", {})
    return {
        "disponivel": True,
        "resumo": {
            "n_clusters": data.get("k", len(clusters)),
            "total_incidentes": metrics.get("total_incidentes"),
            "silhouette": data.get("silhouette", metrics.get("silhouette_score")),
            "mais_critico": compact[0] if compact else None,
            "clusters_por_risco": compact,
        },
    }


def _build_kpi() -> dict[str, Any]:
    data = load_json("kpi_atingimento.json")
    if not data:
        return {"disponivel": False}

    def compact_priority(priority: str) -> dict[str, Any]:
        source = data.get(priority, {})
        compact = {
            key: source.get(key)
            for key in (
                "violacoesAno",
                "metaAnual",
                "pctUtilizado",
                "margemRestante",
                "olaHoras",
            )
        }
        compact["tendencia_em_2025"] = source.get("tendencia")
        compact["meses_anomalos_em_2025"] = source.get("mesesAnomalos")
        return compact

    return {
        "disponivel": True,
        "ano_referencia": data.get("ano", 2025),
        "gerado_em": data.get("gerado_em"),
        "metodologia": data.get("metodologia"),
        "P2": compact_priority("P2"),
        "P3": compact_priority("P3"),
    }


def _metricas_prophet(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not data:
        return None
    return {
        serie: {
            "mae_d1": data.get(serie, {}).get("metricas", {}).get("mae_d1"),
            "mae_d7": data.get(serie, {}).get("metricas", {}).get("mae_d7"),
        }
        for serie in ("total", "p2", "p3")
    }


def _build_model_catalog() -> dict[str, Any]:
    """Expose evaluation protocols so the assistant can compare models safely."""
    lstm = load_json("previsoes_lstm.json")
    prophet = load_json("previsoes_volume.json")
    prophet_mc = load_json("previsoes_volume_mc.json")

    lstm_context: dict[str, Any] = {"disponivel": False}
    if lstm:
        lstm_context = {
            "disponivel": True,
            "nome": lstm.get("modelo"),
            "arquitetura": lstm.get("arquitetura"),
            "treino": lstm.get("treino"),
            "protocolo_validacao": lstm.get("holdout"),
            "mae_holdout_92_dias": lstm.get("mae_holdout_92_dias"),
            "comparacao_prophet_no_holdout_validada": False,
        }

    return {
        "volume_incidentes": {
            "modelo_ativo": "lstm_v2" if lstm else "fallback_por_disponibilidade",
            "lstm": lstm_context,
            "prophet_original": {
                "disponivel": bool(prophet),
                "protocolo_validacao": "cross-validation temporal, janela inicial de 180 dias",
                "metricas": _metricas_prophet(prophet),
            },
            "prophet_monte_carlo": {
                "disponivel": bool(prophet_mc),
                "protocolo_validacao": "cross-validation temporal, janela inicial de 180 dias",
                "metricas": _metricas_prophet(prophet_mc),
            },
            "regras_comparacao": [
                "MAE só pode ser comparado no mesmo horizonte, série e conjunto de validação.",
                "O holdout de 92 dias do LSTM não é diretamente comparável à CV do Prophet original.",
                "Modelo ativo é uma decisão operacional de fallback, não prova de superioridade geral.",
                "D+7 do LSTM é recursivo e exige validação específica para esse horizonte.",
            ],
        },
    }


def _build_long_horizon_projection() -> dict[str, Any]:
    """Expose only numeric long-horizon planning points from the offline artifact."""
    data = load_json("previsoes_horizonte_prophet.json")
    if not data:
        return {"disponivel": False}

    validated_days = data.get("horizonte_validado_dias", 7)
    max_days = data.get("horizonte_max_dias", 0)
    if not isinstance(validated_days, int) or not isinstance(max_days, int):
        return {"disponivel": False}

    safe_series: dict[str, list[dict[str, Any]]] = {}
    for series in ("total", "p2", "p3"):
        points = []
        for point in data.get("series", {}).get(series, [])[:max_days]:
            horizon = point.get("horizonte_dias")
            target = point.get("ds")
            if not isinstance(horizon, int) or not isinstance(target, str):
                continue
            values = {
                key: point.get(key) if isinstance(point.get(key), (int, float)) else None
                for key in ("yhat", "lower", "upper")
            }
            points.append({
                "data_alvo": target,
                "horizonte_dias": horizon,
                **values,
                "validado": horizon <= validated_days,
            })
        safe_series[series] = points

    return {
        "disponivel": all(safe_series.values()),
        "modelo": "prophet_v5_v6",
        "data_base": data.get("data_base"),
        "horizonte_max_dias": max_days,
        "horizonte_validado_dias": validated_days,
        "series": safe_series,
        "regra_uso": (
            "D+1..D+7 é previsão validada; D+8 em diante é projeção exploratória para cenários"
        ),
    }


def build_operational_context() -> dict[str, Any]:
    """Return one source of truth for deterministic and LLM chatbot answers."""
    current_date = _application_current_date().isoformat()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "previsoes": _build_forecasts(),
        "risco": _build_risk(),
        "clusters": _build_clusters(),
        "kpi": _build_kpi(),
        "modelos": _build_model_catalog(),
        "projecoes_longo_prazo": _build_long_horizon_projection(),
        "operacional": {
            "ola_targets": OLA_TARGETS,
            "metas_anuais": METAS_ANUAIS,
            "violacoes_2025": VIOLACOES_2025,
            "dataset": {
                "total_incidentes": 122_543,
                "periodo": "jan/2023-dez/2025",
                "data_fim_observada": DATA_FIM_OBSERVADA,
                "data_atual_aplicacao": current_date,
                "relogio_canonico_aplicacao": True,
                "subset_kpi_aproximado": 25_600,
            },
            "modelagem": {
                "target": "KPI Violado? == SIM",
                "desbalanceamento_aproximado": "1:102",
                "features_proibidas_por_leakage": [
                    "Duração",
                    "Resolvido",
                    "Encerrado",
                    "Código de fechamento",
                    "Solução",
                    "KPI Violado?",
                ],
            },
        },
        "observacoes": [
            "KPI Violado? é o ground truth; duração não substitui as regras de negócio.",
            "Métricas de modelos só devem ser comparadas quando usam o mesmo protocolo de validação.",
            "D+7 do LSTM é recursivo e não deve ser apresentado como causal ou garantido.",
            "As séries total, P2 e P3 são modeladas independentemente e podem não fechar por soma.",
            "Score do XGBoost não é probabilidade calibrada nem chance real de violação.",
            "O threshold do XGBoost serve para priorização humana; a baixa precisão impede automação de ações.",
            "Previsões vencidas devem ser chamadas de snapshots históricos e sempre exibir a data-alvo.",
        ],
    }
