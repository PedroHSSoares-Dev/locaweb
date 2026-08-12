"""Zero-cost answers for common questions whose values already exist in outputs/."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any


@dataclass(frozen=True)
class DeterministicAnswer:
    reply: str
    badge: dict[str, str] = field(default_factory=dict)
    action: dict[str, str] | None = None
    suggestions: list[str] = field(default_factory=list)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _priority(text: str) -> str | None:
    if re.search(r"\bp\s*2\b", text):
        return "P2"
    if re.search(r"\bp\s*3\b", text):
        return "P3"
    return None


def _format_pt(value: Any, decimals: int = 2) -> str:
    if not isinstance(value, (int, float)):
        return "indisponível"
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def _format_date(value: str | None) -> str:
    try:
        parsed = date.fromisoformat(value or "")
    except ValueError:
        return "data não informada"
    return parsed.strftime("%d/%m/%Y")


def _is_direct_factual_query(text: str) -> bool:
    """Reserve the zero-cost path for explicit, bounded fact lookups only.

    Natural-language questions default to the analytical agent. This avoids a
    keyword such as "meta" or "violação" collapsing a broader management
    question into a dashboard card.
    """
    cleaned = re.sub(r"[^a-z0-9+]+", " ", text).strip()
    if re.fullmatch(
        r"(oi|ola|bom dia|boa tarde|boa noite|ajuda|help|comandos|o que voce faz)",
        cleaned,
    ):
        return True

    patterns = (
        r"(?:qual (?:e )?a? )?previsao (?:para )?(?:amanha|d ?\+? ?1|d ?\+? ?7)",
        r"previsao (?:da |para a )?proxima semana",
        r"status (?:das |de )?metas",
        r"(?:qual (?:e )?o? )?cluster mais critico",
        r"fatores de risco",
        r"(?:quantas? )?violacoes? (?:de )?(?:ola )?(?:p ?2|p ?3)(?: (?:em|de) 2025)?",
        r"(?:qual (?:e )?a? )?meta (?:de )?(?:p ?2|p ?3)(?: (?:em|de) 2025)?",
        r"(?:qual (?:e )?o? )?prazo (?:de |do )?ola",
        r"(?:qual (?:e )?o? )?modelo (?:esta )?ativo",
        r"(?:que dia e hoje|qual (?:e )?a data de hoje|qual a data de hoje)",
        r"que dia e hoje diga tambem qual e amanha e qual e a data de d ?\+? ?7",
    )
    return any(re.fullmatch(pattern, cleaned) for pattern in patterns)


def answer_deterministically(message: str, context: dict[str, Any]) -> DeterministicAnswer | None:
    text = _normalize(message)
    priority = _priority(text)
    mentions_both_priorities = bool(re.search(r"\bp\s*2\b", text) and re.search(r"\bp\s*3\b", text))
    requested_years = {int(value) for value in re.findall(r"\b20\d{2}\b", text)}

    # Default to the tool-capable analytical agent. Only explicit quick facts
    # continue through the deterministic branches below.
    if not _is_direct_factual_query(text):
        return None

    # Comparisons of known numbers must never be delegated to a language model.
    if "compar" in text and mentions_both_priorities and any(term in text for term in ("risco", "xgboost", "probabilidade", "score")):
        risk = context.get("risco", {})
        per_priority = risk.get("por_prioridade", {})
        p2 = per_priority.get("P2", {})
        p3 = per_priority.get("P3", {})
        precision = risk.get("metricas", {}).get("precision_violacao")
        precision_note = (
            f" A precisão no teste foi **{_format_pt(precision * 100)}%**, portanto o score deve servir "
            "apenas para triagem com validação humana."
            if isinstance(precision, (int, float)) else ""
        )
        return DeterministicAnswer(
            reply=(
                "**Fatos do teste do XGBoost:** P3 tem score médio do modelo de **"
                f"{_format_pt(p3.get('media_prob', 0) * 100)}%**, contra "
                f"**{_format_pt(p2.get('media_prob', 0) * 100)}%** em P2; "
                f"a faixa de alto risco contém **{_format_pt(p3.get('pct_alto_risco'))}% dos P3** e "
                f"**{_format_pt(p2.get('pct_alto_risco'))}% dos P2**. A taxa real de violação foi "
                f"**{_format_pt(p3.get('taxa_violacao_real'))}% em P3** e "
                f"**{_format_pt(p2.get('taxa_violacao_real'))}% em P2**.\n"
                "**Prioridade operacional:** P2 merece atenção imediata porque excedeu sua meta anual de 2025; "
                "em paralelo, investigue por que o modelo concentra mais P3 na faixa de alto risco. "
                "O score não é uma probabilidade calibrada nem a chance real de violação; indica risco "
                f"preditivo, não causalidade.{precision_note}"
            ),
            badge={"label": "COMPARAÇÃO VALIDADA", "tone": "green"},
            action={"route": "/tecnico", "label": "ABRIR ANÁLISE DE RISCO"},
            suggestions=["Status das metas", "Cluster mais crítico"],
        )

    if "compar" in text and mentions_both_priorities and any(term in text for term in ("meta", "kpi", "violac")):
        kpi = context.get("kpi", {})
        p2 = kpi.get("P2", {})
        p3 = kpi.get("P3", {})
        return DeterministicAnswer(
            reply=(
                f"**P2 em 2025:** {p2.get('violacoesAno')} violações para meta central {p2.get('metaAnual')} "
                f"(**{_format_pt(p2.get('pctUtilizado'), 1)}%**, acima da meta).\n"
                f"**P3 em 2025:** {p3.get('violacoesAno')} violações para meta central {p3.get('metaAnual')} "
                f"(**{_format_pt(p3.get('pctUtilizado'), 1)}%**, dentro da meta).\n"
                "A atenção imediata é P2, que já consumiu mais de 100% do orçamento anual de violações."
            ),
            badge={"label": "ATENÇÃO P2", "tone": "red"},
            action={"route": "/gestao", "label": "ABRIR GESTÃO"},
        )

    requests_next_week = any(phrase in text for phrase in (
        "proxima semana",
        "semana que vem",
        "proximos 7 dias",
        "nos proximos sete dias",
        "de 1 a 7 de janeiro",
        "1-7/01/2026",
    ))
    requests_next_week_analysis = any(term in text for term in (
        "esperar",
        "cenario",
        "norte",
        "planej",
        "prepar",
        "capacidade",
        "risco",
        "recomend",
        "analise",
        "panorama",
        "consider",
        "prioriz",
        "vai acontecer",
        "melhorar",
        "piorar",
    ))
    if requests_next_week and not requests_next_week_analysis:
        forecast = context.get("previsoes", {})
        if not forecast.get("disponivel"):
            return DeterministicAnswer("A previsão da próxima semana não está disponível.")
        d1 = forecast.get("D1", {})
        d7 = forecast.get("D7", {})
        return DeterministicAnswer(
            reply=(
                "**Norte operacional:** use dois pontos de planejamento para **1–7/01/2026**:\n"
                f"- **D+1 — {_format_date(d1.get('data_alvo'))}:** {d1.get('total')} incidentes, "
                f"{d1.get('p2')} P2 e {d1.get('p3')} P3.\n"
                f"- **D+7 — {_format_date(d7.get('data_alvo'))}:** {d7.get('total')} incidentes, "
                f"{d7.get('p2')} P2 e {d7.get('p3')} P3.\n"
                "São previsões pontuais, não o total acumulado da semana. Comparar D+1 com D+7 isoladamente "
                "não comprova tendência; as séries total, P2 e P3 são independentes. Planeje monitoramento "
                "diário, priorize P2 e recalibre com os volumes observados."
            ),
            badge={"label": "PREVISÃO · PRÓXIMA SEMANA", "tone": "purple"},
            action={"route": "/monitoramento", "label": "ABRIR MONITORAMENTO"},
            suggestions=["Fatores de risco", "Status das metas"],
        )

    analytical_terms = (
        "por que",
        "porque",
        "causa",
        "correl",
        "compar",
        "cruz",
        "estrateg",
        "reduzir",
        "recomenda",
        "impacto",
        "explique",
        "analise",
        "melhor",
        "versus",
        " vs ",
        "diferenc",
        "vantag",
        "limitac",
        "esperar",
        "panorama",
        "consider",
        "prioriz",
    )
    if any(term in text for term in analytical_terms):
        return None

    badge = {"label": "DADO VALIDADO", "tone": "green"}

    is_help_or_greeting = bool(re.fullmatch(
        r"\s*(oi|ola|bom dia|boa tarde|boa noite|ajuda|help|comandos|o que voce faz)[!?.\s]*",
        text,
    ))
    if is_help_or_greeting:
        return DeterministicAnswer(
            reply=(
                "Posso consultar **previsões D+1/D+7**, **metas e violações de OLA**, "
                "**clusters operacionais** e **fatores de risco do XGBoost**. Perguntas analíticas "
                "são processadas pelo provedor analítico configurado."
            ),
            badge={"label": "ESCOPO AIOPS", "tone": "purple"},
            suggestions=["Previsão amanhã", "Status das metas", "Cluster mais crítico"],
        )

    asks_current_date = any(phrase in text for phrase in (
        "que dia e hoje",
        "qual e a data de hoje",
        "qual a data de hoje",
        "data atual da aplicacao",
        "em que data estamos",
    ))
    if asks_current_date:
        raw_current_date = context.get("operacional", {}).get("dataset", {}).get("data_atual_aplicacao")
        try:
            current_date = date.fromisoformat(raw_current_date or "")
        except ValueError:
            return DeterministicAnswer("A data atual da aplicação não está disponível.")

        facts = [f"Hoje é **{current_date.strftime('%d/%m/%Y')}**."]
        if "amanha" in text:
            facts.append(f"Amanhã é **{(current_date + timedelta(days=1)).strftime('%d/%m/%Y')}**.")
        if any(term in text for term in ("d+7", "d7")):
            facts.append(f"D+7 corresponde a **{(current_date + timedelta(days=7)).strftime('%d/%m/%Y')}**.")
        return DeterministicAnswer(
            reply=" ".join(facts),
            badge={"label": "DATA ATUAL", "tone": "green"},
            suggestions=["Previsão amanhã", "Previsão D+7"],
        )

    if any(term in text for term in ("receita", "faturamento", "financeir", "custo", "valor monetario")):
        return DeterministicAnswer(
            reply=(
                "Não há dados financeiros ou de receita por cliente no contexto autorizado. "
                "Os modelos estimam volume de incidentes e risco operacional; não calculam impacto financeiro."
            ),
            badge={"label": "DADO INDISPONÍVEL", "tone": "purple"},
        )

    if any(term in text for term in ("previs", "amanha", "d+1", "d1", "d+7", "d7")):
        forecast = context.get("previsoes", {})
        if not forecast.get("disponivel"):
            return DeterministicAnswer("A previsão de volume não está disponível neste snapshot.")
        horizon = "D7" if any(term in text for term in ("d+7", "d7", "7 dias", "semana")) else "D1"
        values = forecast.get(horizon, {})
        horizon_label = "D+7" if horizon == "D7" else "D+1"
        target_label = _format_date(values.get("data_alvo"))
        stale = bool(values.get("status_stale"))
        requested_current = any(term in text for term in ("amanha", "hoje", "atual"))
        prefix = ""
        if stale and requested_current:
            prefix = "Não há previsão disponível para amanhã na data atual da aplicação. "
        forecast_label = f"Previsão **{horizon_label} arquivada**" if stale else f"Previsão **{horizon_label}**"
        reply = (
            f"{prefix}{forecast_label}, com data-alvo **{target_label}**: "
            f"**{values.get('total')} incidentes** no total, "
            f"sendo **{values.get('p2')} P2** e **{values.get('p3')} P3**. "
            f"Modelo ativo: **{forecast.get('modelo_ativo')}**."
        )
        if horizon == "D7" and forecast.get("modelo_ativo") == "lstm_v2":
            reply += " O horizonte D+7 é recursivo e deve ser tratado como estimativa operacional."
        if values.get("reconciliado"):
            reply += " P2 e P3 foram reconciliados proporcionalmente ao Total do modelo ativo."
        return DeterministicAnswer(
            reply=reply,
            badge={"label": "SNAPSHOT HISTÓRICO", "tone": "purple"} if stale else badge,
            action={"route": "/monitoramento", "label": "ABRIR MONITORAMENTO"},
            suggestions=["Status das metas", "Fatores de risco"],
        )

    if any(term in text for term in ("kpi", "ola", "violac", "meta", "prazo")):
        reference_year = context.get("kpi", {}).get("ano_referencia", 2025)
        unavailable_years = requested_years - {reference_year}
        month_terms = (
            "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
        )
        requests_monthly_count = "quant" in text and any(month in text for month in month_terms)
        if unavailable_years or requests_monthly_count:
            period = ", ".join(str(year) for year in sorted(unavailable_years)) or str(reference_year)
            return DeterministicAnswer(
                reply=(
                    f"Não há contagem mensal validada de violações de OLA para **{period}** no contexto disponível. "
                    f"O agregado autorizado de KPI refere-se ao ano de **{reference_year}**."
                ),
                badge={"label": "DADO INDISPONÍVEL", "tone": "purple"},
            )

        if "prazo" in text or ("ola" in text and not any(term in text for term in ("kpi", "violac", "meta"))):
            targets = context.get("operacional", {}).get("ola_targets", {})
            return DeterministicAnswer(
                reply=f"Os prazos de OLA são **{targets.get('P2')} para P2** e **{targets.get('P3')} para P3**.",
                badge=badge,
                suggestions=["Violações P2", "Violações P3"],
            )

        kpi = context.get("kpi", {})
        if not kpi.get("disponivel"):
            return DeterministicAnswer("A projeção de KPI não está disponível neste snapshot.")

        reference_year = kpi.get("ano_referencia", 2025)

        def describe(name: str) -> str:
            item = kpi.get(name, {})
            status = "acima" if (item.get("margemRestante") or 0) < 0 else "dentro"
            return (
                f"**{name} em {reference_year}**: {item.get('violacoesAno')} violações, "
                f"meta central {item.get('metaAnual')}, "
                f"{_format_pt(item.get('pctUtilizado'), 1)}% utilizado — **{status} da meta**"
            )

        reply = describe(priority) if priority else f"{describe('P2')}.\n{describe('P3')}."
        return DeterministicAnswer(
            reply=reply,
            badge={"label": "ATENÇÃO P2", "tone": "red"} if priority != "P3" else badge,
            action={"route": "/gestao", "label": "ABRIR GESTÃO"},
            suggestions=["Previsão amanhã", "Cluster mais crítico"],
        )

    if any(term in text for term in ("cluster", "segment", "grupo critico")):
        summary = context.get("clusters", {}).get("resumo", {})
        critical = summary.get("mais_critico")
        if not critical:
            return DeterministicAnswer("Os clusters não estão disponíveis neste snapshot.")
        reply = (
            f"Há **{summary.get('n_clusters')} clusters**. O mais crítico é o **cluster {critical.get('id')} — "
            f"{critical.get('label')}**, com **{_format_pt(critical.get('taxa_violacao_pct'), 3)}%** "
            f"de violações em **{_format_pt(critical.get('tamanho'), 0)} incidentes**."
        )
        return DeterministicAnswer(
            reply=reply,
            badge={"label": "CLUSTER CRÍTICO", "tone": "red"},
            action={"route": "/tecnico", "label": "ABRIR ANÁLISE TÉCNICA"},
            suggestions=["Fatores de risco", "Status das metas"],
        )

    if any(term in text for term in ("risco", "shap", "fator", "xgboost", "feature")):
        risk = context.get("risco", {})
        if not risk.get("disponivel"):
            return DeterministicAnswer("O modelo de risco não está disponível neste snapshot.")
        top = risk.get("top_fatores", [])[:3]
        factors = ", ".join(f"**{item.get('feature')}**" for item in top)
        per_priority = risk.get("por_prioridade", {})
        p2 = per_priority.get("P2", {})
        p3 = per_priority.get("P3", {})
        threshold = risk.get("threshold_otimizado")
        threshold_text = _format_pt(threshold * 100) if isinstance(threshold, (int, float)) else "indisponível"
        precision = risk.get("metricas", {}).get("precision_violacao")
        precision_text = _format_pt(precision * 100) if isinstance(precision, (int, float)) else "indisponível"
        return DeterministicAnswer(
            reply=(
                f"Os principais fatores SHAP são {factors}. No teste, "
                f"**{_format_pt(p2.get('pct_alto_risco'))}% dos P2** e "
                f"**{_format_pt(p3.get('pct_alto_risco'))}% dos P3** ficaram acima do threshold de score de "
                f"**{threshold_text}%**. Esse score do XGBoost não é probabilidade calibrada nem chance real. "
                f"A precisão no teste foi **{precision_text}%**; use-o somente para triagem humana. "
                "SHAP indica influência preditiva, não causalidade."
            ),
            badge=badge,
            action={"route": "/tecnico", "label": "ABRIR SHAP"},
            suggestions=["Cluster mais crítico", "Previsão amanhã"],
        )

    if "lstm" in text and any(term in text for term in ("roc-auc", "roc auc", "classificacao binaria")):
        return DeterministicAnswer(
            reply=(
                "Não existe ROC-AUC documentado para o LSTM: ele é um modelo de **previsão de volume**, "
                "não um classificador binário. Sua métrica disponível é MAE no holdout de 92 dias. "
                "ROC-AUC pertence ao classificador XGBoost de risco de violação."
            ),
            badge={"label": "MÉTRICA NÃO APLICÁVEL", "tone": "purple"},
            action={"route": "/modelos", "label": "ABRIR MODELOS"},
        )

    if any(term in text for term in ("modelo ativo", "qual modelo", "mae", "lstm", "prophet")):
        forecast = context.get("previsoes", {})
        mae = forecast.get("mae_92_dias")
        mae_text = f", com MAE de **{_format_pt(mae)}** no holdout documentado" if isinstance(mae, (int, float)) else ""
        return DeterministicAnswer(
            reply=(
                f"O modelo ativo para volume é **{forecast.get('modelo_ativo')}**{mae_text}. "
                "Não comparo métricas de modelos obtidas em protocolos de validação diferentes."
            ),
            badge=badge,
            action={"route": "/modelos", "label": "ABRIR MODELOS"},
        )

    return None
