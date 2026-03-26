from typing import Union
from fastapi import APIRouter
from api.schemas import RiscoProdutosResponse, RiscoGruposResponse, NaoDisponivel
from api.services.data_loader import load_json

router = APIRouter(tags=["Risco OLA (XGBoost)"])

_NOT_TRAINED = {"disponivel": False, "mensagem": "Modelo XGBoost ainda não treinado"}


@router.get(
    "/risco",
    response_model=Union[dict, NaoDisponivel],
    summary="JSON completo do modelo XGBoost de risco OLA",
)
def get_risco():
    """
    Retorna o JSON completo do modelo XGBoost de risco de violação de OLA.

    **Disponível apenas após execução do notebook 04** (`04_xgboost_ola.ipynb`).
    O JSON gerado em `outputs/risco_ola.json` deve conter:

    - `produtos`: lista de produtos com probabilidade de violação
    - `grupos`: lista de grupos com taxa histórica de violação
    - `shap_features`: feature importance do modelo XGBoost (para o gráfico SHAP)

    **Contexto do modelo:**
    - Target: `KPI Violado?` — 1 se duração > OLA, 0 caso contrário
    - Desbalanceamento: ~1:102 (248 violações vs 25.352 não-violações)
    - Tratamento: `scale_pos_weight` ou SMOTE (apenas no treino)
    - Métricas: Recall, F1-Score, ROC-AUC (acurácia descartada pelo desbalanceamento)

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
    produtos = sorted(
        data.get("produtos", []),
        key=lambda x: x.get("probViolacao", 0),
        reverse=True,
    )
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
    return {"disponivel": True, "grupos": grupos}
