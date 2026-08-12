from typing import Union
from fastapi import APIRouter
from api.schemas import RiscoResponse, RiscoProdutosResponse, RiscoGruposResponse, NaoDisponivel
from api.services.data_loader import load_json

router = APIRouter(tags=["Risco OLA (XGBoost)"])

_NOT_TRAINED = {"disponivel": False, "mensagem": "Modelo XGBoost não disponível — execute: python src/pipeline.py --step xgb"}


@router.get(
    "/risco",
    response_model=Union[RiscoResponse, NaoDisponivel],
    summary="JSON completo do modelo XGBoost de risco OLA",
)
def get_risco():
    """
    Retorna o JSON completo do modelo XGBoost de risco de violação de OLA.

    **Gerado por** `src/models/xgboost_model.py` via `python src/pipeline.py --step xgb`.

    **Contexto do modelo:**
    - Target: `KPI Violado?` — ground truth oficial já considera pausas e exceções aprovadas
    - Desbalanceamento: ~1:102 — tratado com `scale_pos_weight`
    - Métricas: Recall, F1-Score, ROC-AUC, PR-AUC (acurácia descartada)

    Retorna `disponivel: false` se `outputs/risco_ola.json` não existir.
    """
    data = load_json("risco_ola.json")
    if data is None:
        return _NOT_TRAINED
    return {"disponivel": True, **data}


@router.get(
    "/risco/produtos",
    response_model=Union[RiscoProdutosResponse, NaoDisponivel],
    summary="Produtos ordenados por risco de violação de OLA",
)
def get_risco_produtos():
    """
    Retorna produtos ordenados pela **taxa histórica observada de violação**.

    Para preservar o menor privilégio, segmentos com menos de 100 incidentes
    ou 10 violações são suprimidos. Nenhum registro individual é exposto.
    """
    data = load_json("segmentos_ola.json")
    if data is None:
        return {"disponivel": False, "mensagem": "Agregados por produto indisponíveis — execute: python src/pipeline.py --step segments"}
    return {"disponivel": True, "produtos": data.get("produtos", [])}


@router.get(
    "/risco/grupos",
    response_model=Union[RiscoGruposResponse, NaoDisponivel],
    summary="Grupos de atendimento ordenados por taxa de violação",
)
def get_risco_grupos():
    """
    Retorna a lista de grupos de atendimento ITSM ordenada por
    **taxa histórica de violação de OLA decrescente**.

    Campos por grupo:
    - **grupo**: identificador do grupo (ex.: `Team07`, `Team03`)
    - **taxaViolacao**: percentual de incidentes que violaram OLA no histórico 2025

    Usado no ranking de grupos do TecnicoPage.

    Segmentos pequenos são suprimidos para reduzir risco de reidentificação.
    """
    data = load_json("segmentos_ola.json")
    if data is None:
        return {"disponivel": False, "mensagem": "Agregados por grupo indisponíveis — execute: python src/pipeline.py --step segments"}
    grupos = [
        {**item, "taxaViolacao": item["taxaViolacaoReal"]}
        for item in data.get("grupos", [])
    ]
    return {"disponivel": True, "grupos": grupos}
