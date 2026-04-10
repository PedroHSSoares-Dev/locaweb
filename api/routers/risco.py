from typing import Union
from fastapi import APIRouter
from api.schemas import RiscoResponse, RiscoProdutosResponse, RiscoGruposResponse, NaoDisponivel
from api.services.data_loader import load_json

router = APIRouter(tags=["Risco OLA (XGBoost)"])

_NOT_TRAINED = {"disponivel": False, "mensagem": "Modelo XGBoost ainda não treinado"}


@router.get(
    "/risco",
    response_model=Union[RiscoResponse, NaoDisponivel],
    summary="JSON completo do modelo XGBoost de risco OLA",
)
def get_risco():
    """
    Retorna o JSON completo do modelo XGBoost de risco de violação de OLA.

    **Disponível apenas após execução do notebook 04** (`04_xgboost_ola.ipynb`).

    **Contexto do modelo:**
    - Target: `KPI Violado?` — 1 se duração > OLA, 0 caso contrário
    - Desbalanceamento: ~1:102 — tratado com `scale_pos_weight`
    - Métricas: Recall, F1-Score, ROC-AUC, PR-AUC (acurácia descartada)

    Retorna `disponivel: false` enquanto o notebook não for executado.
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
    Retorna a lista de produtos com incidentes em aberto, ordenada por
    **probabilidade de violação de OLA decrescente**.

    Campos por produto:
    - **produto**: código interno do produto Locaweb (ex.: `lhco`, `lhdns`)
    - **probViolacao**: probabilidade XGBoost de violar OLA (0–100%)
    - **incidentesPendentes**: incidentes em aberto no produto
    - **criticos**: incidentes com probabilidade > 50%

    Usado na tabela de alertas do MonitoramentoPage com semáforo:
    - > 30%: 🔴 ALTO RISCO
    - > 15%: 🟡 ATENÇÃO
    - ≤ 15%: 🟢 NORMAL

    Retorna `disponivel: false` enquanto o notebook 04 não for executado.
    """
    data = load_json("risco_ola.json")
    if data is None:
        return _NOT_TRAINED
    risco_prio = data.get("risco_por_prioridade", {})
    produtos = [
        {
            "produto":          prio,
            "probViolacao":     round(v["media_prob"] * 100, 1),
            "pctAltoRisco":     v["pct_alto_risco"],
            "nIncidentes":      v["n_incidentes"],
            "taxaViolacaoReal": v["taxa_violacao_real"],
        }
        for prio, v in risco_prio.items()
    ]
    produtos.sort(key=lambda x: x["probViolacao"], reverse=True)
    return {"disponivel": True, "produtos": produtos}


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

    **Grupo mais crítico:** Team07 — 8.94% de taxa de violação
    (16 violações em 179 incidentes).

    Usado no ranking de grupos do TecnicoPage.

    Retorna `disponivel: false` enquanto o notebook 04 não for executado.
    """
    data = load_json("risco_ola.json")
    if data is None:
        return _NOT_TRAINED
    grupos = sorted(
        data.get("grupos", []),
        key=lambda x: x.get("taxaViolacao", 0),
        reverse=True,
    )
    return {"disponivel": True, "grupos": grupos}  # lista vazia se notebook não gerou grupos
