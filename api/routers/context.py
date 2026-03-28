"""
context.py — Snapshot operacional agregado para o chatbot Gemini.
Consolida todos os modelos disponíveis em uma única chamada.
"""
from datetime import datetime, timezone
from fastapi import APIRouter
from api.schemas import ContextResponse
from api.services.data_loader import load_json

router = APIRouter(tags=["Contexto Chatbot"])

_OLA_TARGETS    = {"P2": "4h", "P3": "12h"}
_METAS_ANUAIS   = {"P2": "36-39", "P3": "231-263"}
_VIOLACOES_2025 = {"P2": 42, "P3": 196}


def _round_pos(v: float) -> int:
    return round(max(v, 0))


@router.get(
    "/context",
    response_model=ContextResponse,
    summary="Snapshot operacional completo para o chatbot Gemini",
)
def get_context():
    """
    Retorna um **snapshot operacional completo** do estado atual do sistema AIOps,
    projetado para uso como contexto do chatbot Gemini (system prompt context).

    Agrega em uma única chamada:
    - **previsoes**: D+1 e D+7 para total, P2 e P3 (se Prophet disponível)
    - **risco**: top 3 produtos e grupos com maior risco/violação (se XGBoost disponível)
    - **clusters**: número de clusters identificados (se K-Means disponível)
    - **kpi**: atingimento de meta P2 e P3 (se projeção disponível)
    - **operacional**: metadados fixos — OLA targets, metas anuais, violações reais 2025

    ### Uso recomendado no chatbot Gemini
    ```
    GET /api/context
    → serializar resposta como JSON
    → injetar no system prompt do Gemini Flash (roteador)
    → Gemini Flash usa para responder perguntas simples (~1s)
    → escalar para Gemini Pro (analista) com contexto expandido quando necessário
    ```

    ### Campos sempre presentes (independente de modelos disponíveis)
    - `operacional.ola_targets`: P2 = 4h, P3 = 12h
    - `operacional.metas_anuais`: P2 = 36-39, P3 = 231-263 violações/ano
    - `operacional.violacoes_2025`: valores reais do ano (P2=42, P3=196)

    Nunca retorna erro — campos indisponíveis ficam com `disponivel: false`.
    """
    risco_data    = load_json("risco_ola.json")
    clusters_data = load_json("clusters.json")
    kpi_data      = load_json("kpi_atingimento.json")

    # ── Previsões — LSTM v2 > Prophet MC > Prophet Original ────────────────────
    lstm_data = load_json("previsoes_lstm.json")
    mc_data   = load_json("previsoes_volume_mc.json")
    orig_data = load_json("previsoes_volume.json")

    if lstm_data:
        previsoes_ctx = {
            "disponivel":   True,
            "modelo_ativo": "lstm_v2",
            "mae_92_dias":  lstm_data["mae_holdout_92_dias"],
            "D1": {"total": _round_pos(lstm_data["serie"][0]["total"]), "p2": None, "p3": None},
            "D7": {"total": _round_pos(lstm_data["serie"][6]["total"]), "p2": None, "p3": None},
        }
    elif mc_data:
        previsoes_ctx = {
            "disponivel":   True,
            "modelo_ativo": "prophet_mc_ensemble",
            "mae_92_dias":  None,
            "D1": {"total": mc_data["d1"]["total"], "p2": mc_data["d1"]["p2"], "p3": mc_data["d1"]["p3"]},
            "D7": {"total": mc_data["d7"]["total"], "p2": mc_data["d7"]["p2"], "p3": mc_data["d7"]["p3"]},
        }
    elif orig_data:
        previsoes_ctx = {
            "disponivel":   True,
            "modelo_ativo": "prophet_original",
            "mae_92_dias":  None,
            "D1": {
                "total": _round_pos(orig_data["total"]["D1"]["yhat"]),
                "p2":    _round_pos(orig_data["p2"]["D1"]["yhat"]),
                "p3":    _round_pos(orig_data["p3"]["D1"]["yhat"]),
            },
            "D7": {
                "total": _round_pos(orig_data["total"]["D7"]["yhat"]),
                "p2":    _round_pos(orig_data["p2"]["D7"]["yhat"]),
                "p3":    _round_pos(orig_data["p3"]["D7"]["yhat"]),
            },
        }
    else:
        previsoes_ctx = {"disponivel": False}

    # ── Risco OLA ──────────────────────────────────────────────────────────────
    if risco_data:
        top_produtos = sorted(
            risco_data.get("produtos", []),
            key=lambda x: x.get("probViolacao", 0),
            reverse=True,
        )[:3]
        top_grupos = sorted(
            risco_data.get("grupos", []),
            key=lambda x: x.get("taxaViolacao", 0),
            reverse=True,
        )[:3]
        risco_ctx = {"disponivel": True, "top_produtos": top_produtos, "top_grupos": top_grupos}
    else:
        risco_ctx = {"disponivel": False}

    # ── Clusters ───────────────────────────────────────────────────────────────
    if clusters_data:
        clusters_ctx = {
            "disponivel": True,
            "resumo": {"n_clusters": clusters_data.get("n_clusters", 0)},
        }
    else:
        clusters_ctx = {"disponivel": False}

    # ── KPI ────────────────────────────────────────────────────────────────────
    if kpi_data:
        kpi_ctx = {
            "disponivel":  True,
            "metodologia": kpi_data.get("metodologia"),
            "P2": {
                "violacoesAno":   kpi_data["P2"]["violacoesAno"],
                "metaAnual":      kpi_data["P2"]["metaAnual"],
                "pctUtilizado":   kpi_data["P2"]["pctUtilizado"],
                "margemRestante": kpi_data["P2"]["margemRestante"],
                "tendencia":      kpi_data["P2"]["tendencia"],
                "mesesAnomalos":  kpi_data["P2"].get("mesesAnomalos", []),
            },
            "P3": {
                "violacoesAno":   kpi_data["P3"]["violacoesAno"],
                "metaAnual":      kpi_data["P3"]["metaAnual"],
                "pctUtilizado":   kpi_data["P3"]["pctUtilizado"],
                "margemRestante": kpi_data["P3"]["margemRestante"],
                "tendencia":      kpi_data["P3"]["tendencia"],
                "mesesAnomalos":  kpi_data["P3"].get("mesesAnomalos", []),
            },
        }
    else:
        kpi_ctx = {"disponivel": False}

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "previsoes": previsoes_ctx,
        "risco":     risco_ctx,
        "clusters":  clusters_ctx,
        "kpi":       kpi_ctx,
        "operacional": {
            "ola_targets":    _OLA_TARGETS,
            "metas_anuais":   _METAS_ANUAIS,
            "violacoes_2025": _VIOLACOES_2025,
        },
    }
