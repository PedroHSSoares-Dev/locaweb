"""
previsoes.py — Endpoints de previsão de volume de incidentes.

O modelo ativo (incluindo o baseline sazonal) é o vencedor para a série Total no holdout temporal comum.
Disponibilidade é usada apenas como fallback quando a comparação não existe.
"""
from typing import Union
from fastapi import APIRouter
from api.schemas import (
    ModelosDisponiveisResponse, MetricasLSTM, MetricasProphet,
    PrevisaoD1Response, PrevisaoD7Response,
    PrevisaoSerieResponse, NaoDisponivel,
)
from api.services.data_loader import load_json
from api.services.model_registry import reconcile_forecast_point

router = APIRouter(tags=["Previsões"])

_NOT_TRAINED = {"disponivel": False, "mensagem": "Nenhum modelo de previsão disponível"}


def _round_pos(v: float) -> int:
    return round(max(v, 0))


def _public_forecast(total, p2, p3) -> dict:
    return reconcile_forecast_point(total, p2, p3)


def _carregar_melhor_modelo() -> tuple[str | None, dict | None]:
    """
    Carrega o melhor modelo disponível em ordem de hierarquia.
    Retorna (nome_modelo, dados) ou (None, None) se nenhum disponível.
    """
    comparison = load_json("comparacao_modelos.json")
    winner = comparison.get("series", {}).get("total", {}).get("vencedor_geral") if comparison else None
    baseline = load_json("previsoes_baseline.json")
    lstm = load_json("previsoes_lstm.json")
    orig = load_json("previsoes_volume.json")
    if winner == "lstm" and lstm:
        return "lstm_v2", lstm
    if winner == "baseline_sazonal" and baseline:
        return "baseline_sazonal_7d", baseline
    if winner == "prophet" and orig:
        return "prophet_original", orig
    mc = load_json("previsoes_volume_mc.json")
    if winner == "prophet_mc" and mc:
        return "prophet_mc_ensemble", mc
    if baseline:
        return "baseline_sazonal_7d", baseline
    if lstm:
        return "lstm_v2", lstm
    if orig:
        return "prophet_original", orig
    if mc:
        return "prophet_mc_ensemble", mc
    return None, None


@router.get(
    "/previsoes/modelos",
    response_model=ModelosDisponiveisResponse,
    summary="Status de disponibilidade dos modelos de previsão",
)
def get_modelos():
    """
    Retorna quais modelos de previsão estão disponíveis e qual está sendo usado
    ativamente pelos endpoints `/previsoes/d1`, `/previsoes/d7` e `/previsoes/serie`.

    **Seleção:** vencedor no holdout temporal comum; fallback por disponibilidade.
    """
    modelo_ativo, data = _carregar_melhor_modelo()
    comparison = load_json("comparacao_modelos.json")
    total_comparison = comparison.get("series", {}).get("total", {}) if comparison else {}
    active_key = {
        "lstm_v2": "lstm",
        "baseline_sazonal_7d": "baseline_sazonal",
        "prophet_original": "prophet",
        "prophet_mc_ensemble": "prophet_mc",
    }.get(modelo_ativo)
    mae = total_comparison.get("mae_medio_d1_d7", {}).get(active_key)

    lstm_data = load_json("previsoes_lstm.json")
    prophet_data = load_json("previsoes_volume.json")

    metricas_lstm = None
    if lstm_data:
        mae_h = lstm_data.get("mae_holdout_92_dias", {})
        metricas_lstm = MetricasLSTM(
            mae_total=mae_h.get("total", 0),
            mae_p2=mae_h.get("p2", 0),
            mae_p3=mae_h.get("p3", 0),
            mae_prophet_holdout_comum=lstm_data.get("mae_prophet_holdout_comum"),
            melhora_pct_vs_prophet=lstm_data.get("melhora_pct_vs_prophet", 0),
            protocolo_validacao=lstm_data.get("protocolo_validacao", "indisponivel"),
            arquitetura=lstm_data.get("arquitetura", ""),
            treino=lstm_data.get("treino", ""),
            holdout=lstm_data.get("holdout", ""),
        )

    metricas_prophet = None
    if prophet_data:
        total_m = prophet_data.get("total", {}).get("metricas", {})
        p2_m = prophet_data.get("p2", {}).get("metricas", {})
        p3_m = prophet_data.get("p3", {}).get("metricas", {})
        metricas_prophet = MetricasProphet(
            mae_d1_total=total_m.get("mae_d1", 0),
            mae_d7_total=total_m.get("mae_d7", 0),
            mae_d1_p2=p2_m.get("mae_d1", 0),
            mae_d1_p3=p3_m.get("mae_d1", 0),
            protocolo_validacao=prophet_data.get("protocolo_validacao", "indisponivel"),
        )

    return {
        "lstm":             lstm_data is not None,
        "baseline_sazonal": load_json("previsoes_baseline.json") is not None,
        "prophet_mc":       load_json("previsoes_volume_mc.json") is not None,
        "prophet_original": prophet_data is not None,
        "modelo_ativo":     modelo_ativo or "nenhum",
        "mae_modelo_ativo": mae,
        "metricas_lstm":    metricas_lstm,
        "metricas_prophet": metricas_prophet,
        "comparacao":       comparison,
    }


@router.get(
    "/previsoes",
    summary="JSON completo do melhor modelo disponível",
)
def get_previsoes():
    """
    Retorna o JSON completo do melhor modelo disponível com campo `modelo_usado`.

    **Seleção:** vencedor no holdout temporal comum; fallback por disponibilidade.

    A estrutura do JSON varia por modelo — use `/previsoes/d1`, `/previsoes/d7`
    e `/previsoes/serie` para respostas normalizadas e compatíveis com o dashboard.

    Retorna `disponivel: false` se nenhum modelo estiver disponível.
    """
    modelo_ativo, data = _carregar_melhor_modelo()
    if data is None:
        return _NOT_TRAINED
    return {"disponivel": True, "modelo_usado": modelo_ativo, **data}


@router.get(
    "/previsoes/d1",
    response_model=Union[PrevisaoD1Response, NaoDisponivel],
    summary="Previsão D+1 — resumo para KPI cards",
)
def get_d1():
    """
    Retorna o volume previsto de incidentes para **D+1** (amanhã).

    - **Baseline sazonal / LSTM v2**: preveem `total`, `p2` e `p3`.
    - **Prophet MC**: prevê `total`, `p2` e `p3`.
    - **Prophet original**: prevê `total`, `p2` e `p3`.

    O campo `modelo_usado` indica qual modelo gerou a previsão.
    O campo `mae` contém o MAE D+1 no holdout comum quando disponível.

    Retorna `disponivel: false` se nenhum modelo estiver disponível.
    """
    modelo_ativo, data = _carregar_melhor_modelo()
    if data is None:
        return _NOT_TRAINED
    if modelo_ativo in {"lstm_v2", "baseline_sazonal_7d"}:
        mae_raw = data["mae_holdout_92_dias"]
        mae_val = mae_raw["total"] if isinstance(mae_raw, dict) else float(mae_raw)
        point = _public_forecast(
            data["serie"][0]["total"], data["serie"][0]["P2"], data["serie"][0]["P3"]
        )
        return {
            "disponivel":   True,
            **point,
            "modelo_usado": modelo_ativo,
            "mae":          mae_val,
        }
    if modelo_ativo == "prophet_mc_ensemble":
        point = _public_forecast(data["d1"]["total"], data["d1"]["p2"], data["d1"]["p3"])
        return {
            "disponivel":   True,
            **point,
            "modelo_usado": "prophet_mc_ensemble",
            "mae":          None,
        }
    point = _public_forecast(
        data["total"]["D1"]["yhat"], data["p2"]["D1"]["yhat"], data["p3"]["D1"]["yhat"]
    )
    return {
        "disponivel":   True,
        **point,
        "modelo_usado": "prophet_original",
        "mae":          None,
    }


@router.get(
    "/previsoes/d7",
    response_model=Union[PrevisaoD7Response, NaoDisponivel],
    summary="Previsão D+7 — resumo para KPI cards",
)
def get_d7():
    """
    Retorna o volume previsto de incidentes para **D+7** (7 dias à frente).

    Mesma seleção validada do `/previsoes/d1`.

    Retorna `disponivel: false` se nenhum modelo estiver disponível.
    """
    modelo_ativo, data = _carregar_melhor_modelo()
    if data is None:
        return _NOT_TRAINED
    if modelo_ativo in {"lstm_v2", "baseline_sazonal_7d"}:
        mae_raw = data["mae_holdout_92_dias"]
        mae_val = mae_raw["total"] if isinstance(mae_raw, dict) else float(mae_raw)
        point = _public_forecast(
            data["serie"][6]["total"], data["serie"][6]["P2"], data["serie"][6]["P3"]
        )
        return {
            "disponivel":   True,
            **point,
            "modelo_usado": modelo_ativo,
            "mae":          mae_val,
        }
    if modelo_ativo == "prophet_mc_ensemble":
        point = _public_forecast(data["d7"]["total"], data["d7"]["p2"], data["d7"]["p3"])
        return {
            "disponivel":   True,
            **point,
            "modelo_usado": "prophet_mc_ensemble",
            "mae":          None,
        }
    point = _public_forecast(
        data["total"]["D7"]["yhat"], data["p2"]["D7"]["yhat"], data["p3"]["D7"]["yhat"]
    )
    return {
        "disponivel":   True,
        **point,
        "modelo_usado": "prophet_original",
        "mae":          None,
    }


@router.get(
    "/previsoes/serie",
    response_model=Union[PrevisaoSerieResponse, NaoDisponivel],
    summary="Série D+1 a D+7 — formatada para o gráfico de área",
)
def get_serie():
    """
    Retorna a série completa **D+1 a D+7** formatada para o gráfico de área
    do MonitoramentoPage.

    - **Baseline sazonal / LSTM v2**: `P2` e `P3` também são previstos.
    - **Prophet MC / Original**: `P2` e `P3` preenchidos.

    O campo `modelo_usado` indica a fonte dos dados.

    Retorna `disponivel: false` se nenhum modelo estiver disponível.
    """
    modelo_ativo, data = _carregar_melhor_modelo()
    if data is None:
        return _NOT_TRAINED
    if modelo_ativo in {"lstm_v2", "baseline_sazonal_7d"}:
        serie = []
        for p in data["serie"]:
            point = _public_forecast(p["total"], p.get("P2"), p.get("P3"))
            serie.append({
                "dia":   p["horizonte"],
                "ds":    p["ds"],
                "total": point["total"],
                "P2": point["p2"],
                "P3": point["p3"],
                "reconciliado": point["reconciliado"],
            })
        return {"disponivel": True, "modelo_usado": modelo_ativo, "serie": serie}
    if modelo_ativo == "prophet_mc_ensemble":
        serie = []
        for p in data["serie"]:
            point = _public_forecast(p["total"], p.get("P2"), p.get("P3"))
            serie.append({
                "dia":   p["horizonte"],
                "ds":    p["ds"],
                "total": point["total"],
                "P2": point["p2"],
                "P3": point["p3"],
                "reconciliado": point["reconciliado"],
            })
        return {"disponivel": True, "modelo_usado": "prophet_mc_ensemble", "serie": serie}
    serie = []
    for t, p2, p3 in zip(
        data["total"]["serie_7d"],
        data["p2"]["serie_7d"],
        data["p3"]["serie_7d"],
    ):
        point = _public_forecast(t["yhat"], p2["yhat"], p3["yhat"])
        serie.append({
            "dia":   t["horizonte"],
            "ds":    t["ds"],
            "total": point["total"],
            "P2": point["p2"],
            "P3": point["p3"],
            "reconciliado": point["reconciliado"],
        })
    return {"disponivel": True, "modelo_usado": "prophet_original", "serie": serie}
