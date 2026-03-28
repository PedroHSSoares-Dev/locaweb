"""
previsoes.py — Endpoints de previsão de volume de incidentes.

Hierarquia de modelos (melhor → fallback):
  1. LSTM v2 early stopping  (MAE holdout = 13.15)
  2. Prophet MC ensemble     (MAE holdout = 23.80)
  3. Prophet original v5+v6  (MAE CV     = 17.06)

Todos os endpoints tentam na ordem acima e usam o primeiro disponível.
"""
from typing import Union
from fastapi import APIRouter
from api.schemas import (
    ModelosDisponiveisResponse,
    PrevisaoD1Response, PrevisaoD7Response,
    PrevisaoSerieResponse, NaoDisponivel,
)
from api.services.data_loader import load_json

router = APIRouter(tags=["Previsões"])

_NOT_TRAINED = {"disponivel": False, "mensagem": "Nenhum modelo de previsão disponível"}


def _round_pos(v: float) -> int:
    return round(max(v, 0))


def _carregar_melhor_modelo() -> tuple[str | None, dict | None]:
    """
    Carrega o melhor modelo disponível em ordem de hierarquia.
    Retorna (nome_modelo, dados) ou (None, None) se nenhum disponível.
    """
    lstm = load_json("previsoes_lstm.json")
    if lstm:
        return "lstm_v2", lstm
    mc = load_json("previsoes_volume_mc.json")
    if mc:
        return "prophet_mc_ensemble", mc
    orig = load_json("previsoes_volume.json")
    if orig:
        return "prophet_original", orig
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

    **Hierarquia:** LSTM v2 (MAE=13.15) > Prophet MC (MAE=23.80) > Prophet Original (MAE=17.06 CV)
    """
    modelo_ativo, data = _carregar_melhor_modelo()
    mae_raw = data.get("mae_holdout_92_dias") if modelo_ativo == "lstm_v2" and data else None
    mae = mae_raw["total"] if isinstance(mae_raw, dict) else mae_raw
    return {
        "lstm":             load_json("previsoes_lstm.json")      is not None,
        "prophet_mc":       load_json("previsoes_volume_mc.json") is not None,
        "prophet_original": load_json("previsoes_volume.json")    is not None,
        "modelo_ativo":     modelo_ativo or "nenhum",
        "mae_modelo_ativo": mae,
    }


@router.get(
    "/previsoes",
    summary="JSON completo do melhor modelo disponível",
)
def get_previsoes():
    """
    Retorna o JSON completo do melhor modelo disponível com campo `modelo_usado`.

    **Hierarquia:** LSTM v2 > Prophet MC > Prophet Original.

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

    - **LSTM v2** (ativo se disponível): prevê apenas `total`. `p2` e `p3` retornam `null`.
    - **Prophet MC**: prevê `total`, `p2` e `p3`.
    - **Prophet original**: prevê `total`, `p2` e `p3`.

    O campo `modelo_usado` indica qual modelo gerou a previsão.
    O campo `mae` contém o MAE holdout (apenas LSTM tem este valor).

    Retorna `disponivel: false` se nenhum modelo estiver disponível.
    """
    lstm = load_json("previsoes_lstm.json")
    if lstm:
        mae_raw = lstm["mae_holdout_92_dias"]
        mae_val = mae_raw["total"] if isinstance(mae_raw, dict) else float(mae_raw)
        return {
            "disponivel":   True,
            "total":        _round_pos(lstm["serie"][0]["total"]),
            "p2":           _round_pos(lstm["serie"][0]["P2"]),
            "p3":           _round_pos(lstm["serie"][0]["P3"]),
            "modelo_usado": "lstm_v2",
            "mae":          mae_val,
        }
    mc = load_json("previsoes_volume_mc.json")
    if mc:
        return {
            "disponivel":   True,
            "total":        mc["d1"]["total"],
            "p2":           mc["d1"]["p2"],
            "p3":           mc["d1"]["p3"],
            "modelo_usado": "prophet_mc_ensemble",
            "mae":          None,
        }
    orig = load_json("previsoes_volume.json")
    if orig:
        return {
            "disponivel":   True,
            "total":        _round_pos(orig["total"]["D1"]["yhat"]),
            "p2":           _round_pos(orig["p2"]["D1"]["yhat"]),
            "p3":           _round_pos(orig["p3"]["D1"]["yhat"]),
            "modelo_usado": "prophet_original",
            "mae":          None,
        }
    return _NOT_TRAINED


@router.get(
    "/previsoes/d7",
    response_model=Union[PrevisaoD7Response, NaoDisponivel],
    summary="Previsão D+7 — resumo para KPI cards",
)
def get_d7():
    """
    Retorna o volume previsto de incidentes para **D+7** (7 dias à frente).

    Mesma lógica de fallback do `/previsoes/d1` — LSTM > MC > Original.

    Retorna `disponivel: false` se nenhum modelo estiver disponível.
    """
    lstm = load_json("previsoes_lstm.json")
    if lstm:
        mae_raw = lstm["mae_holdout_92_dias"]
        mae_val = mae_raw["total"] if isinstance(mae_raw, dict) else float(mae_raw)
        return {
            "disponivel":   True,
            "total":        _round_pos(lstm["serie"][6]["total"]),
            "p2":           _round_pos(lstm["serie"][6]["P2"]),
            "p3":           _round_pos(lstm["serie"][6]["P3"]),
            "modelo_usado": "lstm_v2",
            "mae":          mae_val,
        }
    mc = load_json("previsoes_volume_mc.json")
    if mc:
        return {
            "disponivel":   True,
            "total":        mc["d7"]["total"],
            "p2":           mc["d7"]["p2"],
            "p3":           mc["d7"]["p3"],
            "modelo_usado": "prophet_mc_ensemble",
            "mae":          None,
        }
    orig = load_json("previsoes_volume.json")
    if orig:
        return {
            "disponivel":   True,
            "total":        _round_pos(orig["total"]["D7"]["yhat"]),
            "p2":           _round_pos(orig["p2"]["D7"]["yhat"]),
            "p3":           _round_pos(orig["p3"]["D7"]["yhat"]),
            "modelo_usado": "prophet_original",
            "mae":          None,
        }
    return _NOT_TRAINED


@router.get(
    "/previsoes/serie",
    response_model=Union[PrevisaoSerieResponse, NaoDisponivel],
    summary="Série D+1 a D+7 — formatada para o gráfico de área",
)
def get_serie():
    """
    Retorna a série completa **D+1 a D+7** formatada para o gráfico de área
    do MonitoramentoPage.

    - **LSTM v2**: `P2` e `P3` retornam `null` (modelo prevê apenas total).
    - **Prophet MC / Original**: `P2` e `P3` preenchidos.

    O campo `modelo_usado` indica a fonte dos dados.

    Retorna `disponivel: false` se nenhum modelo estiver disponível.
    """
    lstm = load_json("previsoes_lstm.json")
    if lstm:
        serie = [
            {
                "dia":   p["horizonte"],
                "ds":    p["ds"],
                "total": _round_pos(p["total"]),
                "P2":    _round_pos(p["P2"]) if p.get("P2") is not None else None,
                "P3":    _round_pos(p["P3"]) if p.get("P3") is not None else None,
            }
            for p in lstm["serie"]
        ]
        return {"disponivel": True, "modelo_usado": "lstm_v2", "serie": serie}

    mc = load_json("previsoes_volume_mc.json")
    if mc:
        serie = [
            {
                "dia":   p["horizonte"],
                "ds":    p["ds"],
                "total": _round_pos(p["total"]),
                "P2":    _round_pos(p["P2"]),
                "P3":    _round_pos(p["P3"]),
            }
            for p in mc["serie"]
        ]
        return {"disponivel": True, "modelo_usado": "prophet_mc_ensemble", "serie": serie}

    orig = load_json("previsoes_volume.json")
    if orig:
        serie = []
        for t, p2, p3 in zip(
            orig["total"]["serie_7d"],
            orig["p2"]["serie_7d"],
            orig["p3"]["serie_7d"],
        ):
            serie.append({
                "dia":   t["horizonte"],
                "ds":    t["ds"],
                "total": _round_pos(t["yhat"]),
                "P2":    _round_pos(p2["yhat"]),
                "P3":    _round_pos(p3["yhat"]),
            })
        return {"disponivel": True, "modelo_usado": "prophet_original", "serie": serie}

    return _NOT_TRAINED
