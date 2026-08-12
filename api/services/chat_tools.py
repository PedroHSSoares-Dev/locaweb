"""Read-only aggregate tools exposed to the analytical chat provider."""

from __future__ import annotations

import math
import re
from calendar import monthrange
from datetime import date
from typing import Any

from api.services.ollama_provider import _compact_context


def _enum_schema(name: str, description: str, values: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            name: {
                "type": "string",
                "description": description,
                "enum": values,
            },
        },
        "required": [name],
        "additionalProperties": False,
    }


CHAT_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "consultar_previsao_volume",
        "description": (
            "Consulta as previsões pontuais D+1 e D+7 de volume de incidentes do modelo ativo, "
            "com data-alvo, Total, P2, P3 e limitações de uso."
        ),
        "parameters": _enum_schema(
            "horizonte",
            "Horizonte pontual que deve ser consultado.",
            ["D1", "D7", "ambos"],
        ),
        "strict": True,
    },
    {
        "type": "function",
        "name": "consultar_kpis_ola",
        "description": (
            "Consulta metas e violações agregadas de OLA de 2025 para P2 e/ou P3. "
            "Use para status, pressão histórica, metas e priorização."
        ),
        "parameters": _enum_schema(
            "prioridade",
            "Prioridade de OLA que deve ser consultada.",
            ["P2", "P3", "ambas"],
        ),
        "strict": True,
    },
    {
        "type": "function",
        "name": "projetar_volume_longo_prazo",
        "description": (
            "Projeta volume no dia-alvo e volume acumulado para horizontes D+8 a D+365 usando os "
            "modelos Prophet v5/v6 já treinados. Fora de D+7 é cenário exploratório, não previsão validada."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "horizonte_dias": {
                    "type": "integer",
                    "description": "Quantidade de dias após 31/12/2025, entre 8 e 365.",
                    "minimum": 8,
                    "maximum": 365,
                },
            },
            "required": ["horizonte_dias"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "simular_consumo_cota_ola",
        "description": (
            "Simula se a cota anual de violações de OLA pode ser consumida em um horizonte de 1 a 365 dias. "
            "Combina volume Prophet, taxa real histórica por prioridade e metas anuais, com cenários baixo/base/alto."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "horizonte_dias": {
                    "type": "integer",
                    "description": "Janela acumulada a partir de 01/01/2026, entre 1 e 365 dias.",
                    "minimum": 1,
                    "maximum": 365,
                },
                "prioridade": {
                    "type": "string",
                    "description": "Cota de OLA que deve ser simulada.",
                    "enum": ["P2", "P3", "ambas"],
                },
            },
            "required": ["horizonte_dias", "prioridade"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "analisar_planejamento_periodico",
        "description": (
            "Gera planejamento executivo mensal ou trimestral com volume do período e acumulado, "
            "violações projetadas, consumo de cota e score auditável de preocupação de 0 a 10. "
            "Use sempre que o usuário pedir períodos, trimestres, meses, roadmap ou score de preocupação."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "periodicidade": {
                    "type": "string",
                    "description": "Granularidade da análise executiva.",
                    "enum": ["mensal", "trimestral"],
                },
                "prioridade": {
                    "type": "string",
                    "description": "Prioridade de OLA ou conjunto a analisar.",
                    "enum": ["P2", "P3", "ambas"],
                },
            },
            "required": ["periodicidade", "prioridade"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "consultar_risco_xgboost",
        "description": (
            "Consulta métricas históricas agregadas do classificador XGBoost, scores por prioridade "
            "e principais fatores SHAP. O score não é probabilidade calibrada."
        ),
        "parameters": _enum_schema(
            "prioridade",
            "Prioridade cujo risco deve ser consultado.",
            ["P2", "P3", "ambas"],
        ),
        "strict": True,
    },
    {
        "type": "function",
        "name": "consultar_clusters_operacionais",
        "description": (
            "Consulta perfis agregados dos clusters K-Means, ordenados pela taxa observada de violação. "
            "Não retorna registros, descrições causais ou identificadores sensíveis."
        ),
        "parameters": _enum_schema(
            "selecao",
            "Quantidade de clusters necessária para responder.",
            ["mais_critico", "todos"],
        ),
        "strict": True,
    },
    {
        "type": "function",
        "name": "consultar_metricas_modelos",
        "description": (
            "Consulta métricas e protocolos de validação dos modelos LSTM, Prophet, Prophet Monte Carlo "
            "ou XGBoost. Use antes de comparar modelos ou afirmar desempenho."
        ),
        "parameters": _enum_schema(
            "modelo",
            "Modelo ou família de modelos a consultar.",
            ["baseline_sazonal", "lstm", "prophet", "prophet_monte_carlo", "xgboost", "todos"],
        ),
        "strict": True,
    },
    {
        "type": "function",
        "name": "consultar_regras_operacionais",
        "description": (
            "Consulta o relógio canônico da aplicação, período observado, OLAs e regra de ground truth. "
            "Use para perguntas temporais, de escopo ou interpretação dos indicadores."
        ),
        "parameters": _enum_schema(
            "tema",
            "Conjunto de regras operacionais necessário.",
            ["data", "ola", "ground_truth", "todos"],
        ),
        "strict": True,
    },
]


TOOL_SOURCE_LABELS = {
    "consultar_previsao_volume": "previsão de volume (modelo ativo no registro canônico)",
    "projetar_volume_longo_prazo": "projeção de longo prazo (Prophet v5/v6)",
    "simular_consumo_cota_ola": "simulação de cota (Prophet + XGBoost + metas de OLA)",
    "analisar_planejamento_periodico": "planejamento periódico e score executivo auditável",
    "consultar_kpis_ola": "KPIs e metas de OLA",
    "consultar_risco_xgboost": "risco histórico (XGBoost/SHAP)",
    "consultar_clusters_operacionais": "clusters operacionais (K-Means)",
    "consultar_metricas_modelos": "métricas e validação dos modelos",
    "consultar_regras_operacionais": "regras operacionais canônicas",
}


def _require_enum(arguments: dict[str, Any], name: str, allowed: set[str]) -> str:
    if set(arguments) != {name} or arguments.get(name) not in allowed:
        raise ValueError(f"Argumento `{name}` inválido.")
    return str(arguments[name])


def _numeric_fields(source: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {
        field: value if isinstance((value := source.get(field)), (int, float)) else None
        for field in fields
    }


def _safe_identifier(value: Any, fallback: str) -> str:
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_]{1,64}", value):
        return value
    return fallback


def _require_int(arguments: dict[str, Any], name: str, minimum: int, maximum: int) -> int:
    value = arguments.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"Argumento `{name}` inválido.")
    return value


def _projection_points(context: dict[str, Any], horizon: int) -> dict[str, list[dict[str, Any]]]:
    projection = context.get("projecoes_longo_prazo", {})
    if not projection.get("disponivel") or horizon > projection.get("horizonte_max_dias", 0):
        raise ValueError("Projeção de longo prazo indisponível para o horizonte solicitado.")
    selected: dict[str, list[dict[str, Any]]] = {}
    for series in ("total", "p2", "p3"):
        points = projection.get("series", {}).get(series, [])[:horizon]
        if len(points) != horizon:
            raise ValueError("Série de projeção incompleta.")
        selected[series] = points
    return selected


def _wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    rate = successes / total
    denominator = 1 + z**2 / total
    center = (rate + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt((rate * (1 - rate) + z**2 / (4 * total)) / total) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def _concern_score(base_consumption_pct: float, high_violations: float, quota: float, pace_pct: float) -> int:
    """Return a cumulative 0-10 executive score with an explicit stable formula."""
    base_component = min(5.0, max(0.0, base_consumption_pct) * 0.05)
    high_consumption_pct = high_violations / quota * 100 if quota > 0 else 0.0
    stress_component = min(3.0, max(0.0, high_consumption_pct) * 0.03)
    pace_component = min(2.0, max(0.0, pace_pct) * 0.02)
    return max(0, min(10, round(base_component + stress_component + pace_component)))


def _concern_label(score: int) -> str:
    if score >= 9:
        return "muito_alta"
    if score >= 7:
        return "alta"
    if score >= 5:
        return "moderada"
    if score >= 3:
        return "baixa_moderada"
    return "baixa"


def execute_chat_tool(
    name: str,
    arguments: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Execute a whitelisted read-only query over the already-built aggregate context."""
    compact = _compact_context(context)

    if name == "consultar_previsao_volume":
        horizon = _require_enum(arguments, "horizonte", {"D1", "D7", "ambos"})
        forecast = compact.get("previsoes", {})
        selected = {
            key: forecast.get(key)
            for key in (("D1", "D7") if horizon == "ambos" else (horizon,))
        }
        return {
            "fonte": "artefato de previsão de volume",
            "disponivel": forecast.get("disponivel", False),
            "modelo_ativo": forecast.get("modelo_ativo"),
            "mae_holdout_92_dias": forecast.get("mae_92_dias"),
            "pontos": selected,
            "limitacoes": [
                "D+1 e D+7 são previsões pontuais, não o total acumulado da semana.",
                "As séries são treinadas independentemente; a API preserva o Total e reconcilia P2/P3 proporcionalmente.",
                "Comparar apenas D+1 e D+7 não comprova tendência.",
            ],
        }

    if name == "projetar_volume_longo_prazo":
        if set(arguments) != {"horizonte_dias"}:
            raise ValueError("Argumentos inválidos para projeção de longo prazo.")
        horizon = _require_int(arguments, "horizonte_dias", 8, 365)
        series = _projection_points(context, horizon)
        target = {
            name: series[name][-1]
            for name in ("total", "p2", "p3")
        }
        cumulative = {
            name: {
                field: round(sum(float(point.get(field) or 0) for point in series[name]), 1)
                for field in ("yhat", "lower", "upper")
            }
            for name in ("total", "p2", "p3")
        }
        return {
            "fonte": "inferência offline dos modelos Prophet v5/v6 treinados",
            "horizonte_dias": horizon,
            "data_alvo": target["total"].get("data_alvo"),
            "no_dia_alvo": target,
            "acumulado_ate_data_alvo": cumulative,
            "status_validacao": "exploratorio_fora_do_horizonte_validado_D7",
            "confianca": "baixa",
            "limitacoes": [
                "D+8 a D+365 não possui backtest documentado para esse horizonte",
                "regressores futuros usam nível recente fixo; mudanças estruturais não são capturadas",
                "Total, P2 e P3 são séries independentes",
            ],
        }

    if name == "simular_consumo_cota_ola":
        if set(arguments) != {"horizonte_dias", "prioridade"}:
            raise ValueError("Argumentos inválidos para simulação de cota.")
        horizon = _require_int(arguments, "horizonte_dias", 1, 365)
        priority_value = arguments.get("prioridade")
        if priority_value not in {"P2", "P3", "ambas"}:
            raise ValueError("Argumento `prioridade` inválido.")
        priority = str(priority_value)
        series = _projection_points(context, horizon)
        compact_risk = compact.get("risco", {}).get("por_prioridade", {})
        compact_kpi = compact.get("kpi", {})
        priorities = ("P2", "P3") if priority == "ambas" else (priority,)
        results: dict[str, Any] = {}

        for key in priorities:
            series_key = key.lower()
            volumes = {
                field: sum(float(point.get(field) or 0) for point in series[series_key])
                for field in ("yhat", "lower", "upper")
            }
            risk = compact_risk.get(key, {})
            rate_pct = risk.get("taxa_violacao_real")
            sample_size = risk.get("n_incidentes")
            quota = compact_kpi.get(key, {}).get("metaAnual")
            if not all(isinstance(value, (int, float)) for value in (rate_pct, sample_size, quota)):
                raise ValueError(f"Dados insuficientes para simular a cota {key}.")

            rate = float(rate_pct) / 100
            successes = round(float(sample_size) * rate)
            rate_low, rate_high = _wilson_interval(successes, int(sample_size))
            violations = {
                "baixo": volumes["yhat"] * rate_low,
                "base": volumes["yhat"] * rate,
                "alto": volumes["upper"] * rate_high,
            }
            proportional_quota = float(quota) * horizon / 365
            results[key] = {
                "volume_acumulado_base": round(volumes["yhat"], 1),
                "taxa_real_historica_pct": round(float(rate_pct), 3),
                "intervalo_taxa_95_pct": [round(rate_low * 100, 3), round(rate_high * 100, 3)],
                "violacoes_projetadas": {
                    scenario: round(value, 1) for scenario, value in violations.items()
                },
                "cota_anual": float(quota),
                "cota_proporcional_ao_horizonte": round(proportional_quota, 1),
                "consumo_cota_anual_pct_cenario_base": round(violations["base"] / quota * 100, 1),
                "consumo_ritmo_proporcional_pct_cenario_base": round(
                    violations["base"] / proportional_quota * 100, 1
                ),
                "estoura_cota_anual_no_cenario_base": violations["base"] > quota,
                "estoura_cota_anual_no_cenario_alto": violations["alto"] > quota,
                "acima_do_ritmo_proporcional_no_cenario_base": violations["base"] > proportional_quota,
            }

        return {
            "fonte": "simulação derivada de Prophet + taxa observada do XGBoost + metas de OLA",
            "horizonte_dias": horizon,
            "data_alvo": series["total"][-1].get("data_alvo"),
            "assuncao_cota": "metas anuais reiniciadas em 01/01/2026; P2=37,5 e P3=247",
            "prioridades": results,
            "status_validacao": (
                "validado_apenas_para_volume_D1_D7; consumo_de_cota_e_longo_prazo_sao_cenarios"
            ),
            "confianca": "baixa",
            "limitacoes": [
                "taxa histórica de violação é mantida constante",
                "score do XGBoost não é usado como probabilidade calibrada",
                "cenários alto e baixo combinam incertezas e não são intervalos preditivos calibrados",
            ],
        }

    if name == "analisar_planejamento_periodico":
        if set(arguments) != {"periodicidade", "prioridade"}:
            raise ValueError("Argumentos inválidos para planejamento periódico.")
        periodicity = arguments.get("periodicidade")
        priority = arguments.get("prioridade")
        if periodicity not in {"mensal", "trimestral"}:
            raise ValueError("Argumento `periodicidade` inválido.")
        if priority not in {"P2", "P3", "ambas"}:
            raise ValueError("Argumento `prioridade` inválido.")

        projection = context.get("projecoes_longo_prazo", {})
        try:
            base_date = date.fromisoformat(str(projection.get("data_base")))
        except ValueError as exc:
            raise ValueError("Data-base da projeção inválida.") from exc
        planning_year = base_date.year + 1
        months = range(1, 13) if periodicity == "mensal" else (3, 6, 9, 12)
        periods: list[dict[str, Any]] = []
        previous_volume = 0.0

        for index, month in enumerate(months, start=1):
            target_date = date(planning_year, month, monthrange(planning_year, month)[1])
            horizon = (target_date - base_date).days
            simulation = execute_chat_tool(
                "simular_consumo_cota_ola",
                {"horizonte_dias": horizon, "prioridade": str(priority)},
                context,
            )
            volume_projection = execute_chat_tool(
                "projetar_volume_longo_prazo",
                {"horizonte_dias": horizon},
                context,
            )
            cumulative_volume = float(
                volume_projection["acumulado_ate_data_alvo"]["total"]["yhat"]
            )
            scores: dict[str, Any] = {}
            for key, result in simulation["prioridades"].items():
                quota = float(result["cota_anual"])
                high = float(result["violacoes_projetadas"]["alto"])
                score = _concern_score(
                    float(result["consumo_cota_anual_pct_cenario_base"]),
                    high,
                    quota,
                    float(result["consumo_ritmo_proporcional_pct_cenario_base"]),
                )
                scores[key] = {
                    "score_preocupacao_0_10": score,
                    "classificacao": _concern_label(score),
                    "violacoes_base_acumuladas": result["violacoes_projetadas"]["base"],
                    "violacoes_alto_acumuladas": high,
                    "consumo_cota_anual_pct_base": result[
                        "consumo_cota_anual_pct_cenario_base"
                    ],
                    "ritmo_proporcional_pct_base": result[
                        "consumo_ritmo_proporcional_pct_cenario_base"
                    ],
                }
            dominant = max(
                scores,
                key=lambda key: scores[key]["score_preocupacao_0_10"],
            )
            label = (
                f"{index}º trimestre"
                if periodicity == "trimestral"
                else target_date.strftime("%m/%Y")
            )
            periods.append({
                "periodo": label,
                "data_final": target_date.isoformat(),
                "incidentes_no_periodo": round(cumulative_volume - previous_volume, 1),
                "incidentes_acumulados": round(cumulative_volume, 1),
                "score_preocupacao_geral_0_10": scores[dominant]["score_preocupacao_0_10"],
                "classificacao_geral": scores[dominant]["classificacao"],
                "prioridade_dominante": dominant,
                "detalhes_por_prioridade": scores,
            })
            previous_volume = cumulative_volume

        return {
            "fonte": "planejamento derivado de Prophet + taxas históricas + metas de OLA",
            "periodicidade": periodicity,
            "ano": planning_year,
            "periodos": periods,
            "formula_score": {
                "base": "até 5 pontos pelo percentual acumulado da cota no cenário-base",
                "estresse": "até 3 pontos pelo percentual acumulado da cota no cenário alto",
                "ritmo": "até 2 pontos pelo consumo frente à cota proporcional do período",
                "observacao": "score é índice executivo derivado, não probabilidade",
            },
            "confianca": "baixa",
            "status_validacao": "cenário exploratório fora de D+7",
        }
    if name == "consultar_kpis_ola":
        priority = _require_enum(arguments, "prioridade", {"P2", "P3", "ambas"})
        kpi = compact.get("kpi", {})
        priorities = ("P2", "P3") if priority == "ambas" else (priority,)
        selected: dict[str, Any] = {}
        for key in priorities:
            source = kpi.get(key, {})
            margin = source.get("margemRestante")
            selected[key] = _numeric_fields(
                source,
                ("violacoesAno", "metaAnual", "pctUtilizado", "margemRestante", "olaHoras"),
            )
            selected[key]["ultimo_status_observado_em_2025"] = (
                "atencao" if key == "P2" and isinstance(margin, (int, float)) and margin < 0
                else "dentro_da_meta"
            )
        return {
            "fonte": "agregado anual de KPI",
            "disponivel": kpi.get("disponivel", False),
            "ano_referencia": kpi.get("ano_referencia"),
            "prioridades": selected,
            "interpretacao": "status histórico observado; não é previsão de violações futuras",
        }

    if name == "consultar_risco_xgboost":
        priority = _require_enum(arguments, "prioridade", {"P2", "P3", "ambas"})
        risk = compact.get("risco", {})
        priorities = ("P2", "P3") if priority == "ambas" else (priority,)
        per_priority = risk.get("por_prioridade", {})
        metric_fields = (
            "recall_violacao", "precision_violacao", "f1_violacao", "roc_auc", "pr_auc",
            "tp", "fp", "fn", "tn", "total_teste",
        )
        safe_factors = []
        for index, factor in enumerate(risk.get("top_fatores_shap", []), start=1):
            if not isinstance(factor, dict):
                continue
            safe_factors.append({
                "rank": factor.get("rank") if isinstance(factor.get("rank"), int) else index,
                "feature": _safe_identifier(factor.get("feature"), f"feature_{index}"),
                "shap_mean_abs": (
                    factor.get("shap_mean_abs")
                    if isinstance(factor.get("shap_mean_abs"), (int, float)) else None
                ),
            })
        safe_priorities = {
            key: _numeric_fields(
                per_priority.get(key, {}),
                ("media_prob", "pct_alto_risco", "n_incidentes", "taxa_violacao_real"),
            )
            for key in priorities
        }
        return {
            "fonte": "teste temporal histórico do XGBoost",
            "disponivel": risk.get("disponivel", False),
            "periodo_avaliacao": risk.get("periodo_avaliacao"),
            "threshold_otimizado": (
                risk.get("threshold_otimizado")
                if isinstance(risk.get("threshold_otimizado"), (int, float)) else None
            ),
            "score_calibrado_como_probabilidade": False,
            "metricas": _numeric_fields(risk.get("metricas", {}), metric_fields),
            "prioridades": safe_priorities,
            "top_fatores_shap": safe_factors,
            "limitacao": "score para triagem humana; SHAP não demonstra causalidade",
        }

    if name == "consultar_clusters_operacionais":
        selection = _require_enum(arguments, "selecao", {"mais_critico", "todos"})
        clusters = compact.get("clusters", {})
        ordered = clusters.get("ordenados_por_risco", [])
        return {
            "fonte": "clusters K-Means agregados",
            "quantidade": clusters.get("quantidade"),
            "total_incidentes": clusters.get("total_incidentes"),
            "clusters": ordered[:1] if selection == "mais_critico" else ordered,
            "limitacao": "perfis e associações não demonstram causa raiz",
        }

    if name == "consultar_metricas_modelos":
        model = _require_enum(
            arguments,
            "modelo",
            {"baseline_sazonal", "lstm", "prophet", "prophet_monte_carlo", "xgboost", "todos"},
        )
        catalog = compact.get("modelos", {}).get("volume_incidentes", {})
        canonical = compact.get("modelos", {}).get("registro_canonico", {})
        lstm = catalog.get("lstm", {})
        prophet = catalog.get("prophet_original", {})
        prophet_mc = catalog.get("prophet_monte_carlo", {})
        baseline = catalog.get("baseline_sazonal", {})

        def safe_mae(source: dict[str, Any]) -> dict[str, Any]:
            return {
                series: _numeric_fields(source.get(series, {}), ("mae_d1", "mae_d7"))
                for series in ("total", "p2", "p3")
            }

        model_map = {
            "baseline_sazonal": {
                "disponivel": bool(baseline.get("disponivel")),
                "protocolo_validacao": baseline.get("protocolo_validacao"),
                "metricas_holdout_comum": baseline.get("metricas"),
                "metodologia": "mediana das três semanas anteriores no mesmo dia da semana",
            },
            "lstm": {
                "disponivel": bool(lstm.get("disponivel")),
                "protocolo_validacao": "holdout temporal real de 92 dias (01/10/2025 a 31/12/2025)",
                "mae_holdout_92_dias": _numeric_fields(
                    lstm.get("mae_holdout_92_dias", {}),
                    ("total", "p2", "p3"),
                ),
                "d7_recursivo": True,
            },
            "prophet": {
                "disponivel": bool(prophet.get("disponivel")),
                "protocolo_validacao": "rolling origin no holdout comum de 01/10/2025 a 31/12/2025",
                "metricas": safe_mae(prophet.get("metricas", {})),
            },
            "prophet_monte_carlo": {
                "disponivel": bool(prophet_mc.get("disponivel")),
                "protocolo_validacao": "rolling origin no holdout comum; base sintética limitada ao período anterior à seleção",
                "metricas": safe_mae(prophet_mc.get("metricas", {})),
            },
            "xgboost": {
                "finalidade": "classificação de risco de violação de OLA",
                "metricas": _numeric_fields(
                    compact.get("risco", {}).get("metricas", {}),
                    ("recall_violacao", "precision_violacao", "f1_violacao", "roc_auc", "pr_auc"),
                ),
                "periodo_avaliacao": "conjunto de teste temporal histórico",
            },
        }
        selected = model_map if model == "todos" else {model: model_map.get(model)}
        return {
            "fonte": "catálogo de avaliação dos modelos",
            "modelo_ativo_volume": _safe_identifier(catalog.get("modelo_ativo"), "indisponivel"),
            "registro_canonico": canonical,
            "modelos": selected,
            "regras_comparacao": [
                "comparar somente a mesma série, horizonte, métrica e período de validação",
                "o baseline, LSTM e Prophet publicados usam o mesmo rolling origin de Out–Dez/2025",
                "candidatos shadow não substituem o ativo até validação prospectiva",
                "métricas de protocolos diferentes não devem ser comparadas diretamente",
            ],
        }

    if name == "consultar_regras_operacionais":
        theme = _require_enum(arguments, "tema", {"data", "ola", "ground_truth", "todos"})
        operational = compact.get("operacional", {})
        available = {
            "data": {
                "hoje_sistema": compact.get("hoje_sistema"),
                "data_fim_observada": compact.get("data_fim_observada"),
                "periodo_observado": operational.get("periodo_observado"),
            },
            "ola": operational.get("ola_targets", {}),
            "ground_truth": {
                "campo": operational.get("ground_truth"),
                "regra": "o campo oficial incorpora pausas e exceções de negócio",
            },
        }
        return {
            "fonte": "contrato operacional canônico",
            "regras": available if theme == "todos" else {theme: available[theme]},
        }

    raise ValueError("Ferramenta não autorizada.")
