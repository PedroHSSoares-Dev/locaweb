from typing import Union
from fastapi import APIRouter
from api.schemas import (
    PrevisaoCompletaResponse, PrevisaoD1Response, PrevisaoD7Response,
    PrevisaoSerieResponse, NaoDisponivel,
)
from api.services.data_loader import load_json

router = APIRouter(tags=["Previsões Prophet"])

_NOT_TRAINED = {"disponivel": False, "mensagem": "Modelo Prophet ainda não treinado"}


def _round_pos(v: float) -> int:
    return round(max(v, 0))


@router.get(
    "/previsoes",
    response_model=Union[PrevisaoCompletaResponse, NaoDisponivel],
    summary="JSON completo do modelo Prophet",
)
def get_previsoes():
    """
    Retorna toda a estrutura do JSON do modelo Prophet ensemble, incluindo:

    - Série D+1 a D+7 com intervalo de confiança por horizonte
    - MAE de cross-validation (janela inicial de 180 dias)
    - Metadados do modelo (versão, data de geração, abordagem)
    - Três séries independentes: **total**, **P2** e **P3**

    O modelo usa ensemble v5+v6 — o melhor modelo é selecionado
    por horizonte com base no MAE da cross-validation.

    Retorna `disponivel: false` se `outputs/previsoes_volume.json` não existir.
    """
    data = load_json("previsoes_volume.json")
    if data is None:
        return _NOT_TRAINED
    return {"disponivel": True, **data}


@router.get(
    "/previsoes/d1",
    response_model=Union[PrevisaoD1Response, NaoDisponivel],
    summary="Previsão D+1 — resumo para KPI cards",
)
def get_d1():
    """
    Retorna o volume previsto de incidentes para **D+1** (amanhã) em formato
    resumido — ideal para os KPI cards do dashboard.

    - **total**: soma de P2 + P3 previstos
    - **p2**: incidentes de prioridade Alta (OLA ≤ 4h)
    - **p3**: incidentes de prioridade Média (OLA ≤ 12h)

    Os valores são arredondados para inteiro e floored em 0 (nunca negativo).

    Retorna `disponivel: false` se o modelo Prophet ainda não foi treinado
    (`outputs/previsoes_volume.json` não encontrado).
    """
    data = load_json("previsoes_volume.json")
    if data is None:
        return _NOT_TRAINED
    return {
        "disponivel": True,
        "total": _round_pos(data["total"]["D1"]["yhat"]),
        "p2":    _round_pos(data["p2"]["D1"]["yhat"]),
        "p3":    _round_pos(data["p3"]["D1"]["yhat"]),
    }


@router.get(
    "/previsoes/d7",
    response_model=Union[PrevisaoD7Response, NaoDisponivel],
    summary="Previsão D+7 — resumo para KPI cards",
)
def get_d7():
    """
    Retorna o volume previsto de incidentes para **D+7** (7 dias à frente)
    em formato resumido — ideal para os KPI cards do dashboard.

    - **total**: soma de P2 + P3 previstos
    - **p2**: incidentes de prioridade Alta (OLA ≤ 4h)
    - **p3**: incidentes de prioridade Média (OLA ≤ 12h)

    Os valores são arredondados para inteiro e floored em 0 (nunca negativo).

    Retorna `disponivel: false` se o modelo Prophet ainda não foi treinado.
    """
    data = load_json("previsoes_volume.json")
    if data is None:
        return _NOT_TRAINED
    return {
        "disponivel": True,
        "total": _round_pos(data["total"]["D7"]["yhat"]),
        "p2":    _round_pos(data["p2"]["D7"]["yhat"]),
        "p3":    _round_pos(data["p3"]["D7"]["yhat"]),
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

    Cada ponto contém:
    - **dia**: label do eixo X no formato `DD/MM` (ex.: `01/01`)
    - **ds**: data ISO 8601 para cálculos no frontend
    - **total**, **P2**, **P3**: volumes inteiros arredondados

    A coluna `dia` usa o mesmo formato do histórico diário (`DD/MM`), permitindo
    que o Recharts distribua os pontos uniformemente no eixo X sem gap.

    **Nota sobre sábados e domingos:** o modelo aplica *floor* no percentil 10
    histórico de janeiro para evitar previsões negativas em fins de semana.

    Retorna `disponivel: false` se o modelo Prophet ainda não foi treinado.
    """
    data = load_json("previsoes_volume.json")
    if data is None:
        return _NOT_TRAINED
    serie = []
    for t, p2, p3 in zip(
        data["total"]["serie_7d"],
        data["p2"]["serie_7d"],
        data["p3"]["serie_7d"],
    ):
        serie.append({
            "dia": t["horizonte"],
            "ds":  t["ds"],
            "total": _round_pos(t["yhat"]),
            "P2":    _round_pos(p2["yhat"]),
            "P3":    _round_pos(p3["yhat"]),
        })
    return {"disponivel": True, "serie": serie}
