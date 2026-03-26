from typing import Union
from fastapi import APIRouter
from api.schemas import ClustersResponse, NaoDisponivel
from api.services.data_loader import load_json

router = APIRouter(tags=["Clusters K-Means"])


@router.get(
    "/clusters",
    response_model=Union[ClustersResponse, NaoDisponivel],
    summary="Segmentação K-Means de padrões de incidentes",
)
def get_clusters():
    """
    Retorna os clusters K-Means de padrões de incidentes KPI.

    **Disponível apenas após execução do notebook 05** (`05_kmeans_clusters.ipynb`).
    O JSON gerado em `outputs/clusters.json` deve conter uma lista de clusters,
    cada um com:

    - `id`: índice do cluster (0–3)
    - `label`: nome descritivo (ex.: "Cluster Noturno", "Picos P2")
    - `tamanho`: número de incidentes no cluster
    - `taxaViolacao`: percentual de violações de OLA no cluster
    - `perfil`: hora média, grupo dominante, dias críticos, produtos frequentes
    - `descricao`: interpretação do padrão identificado

    **Clusters esperados (baseado na EDA):**
    - Cluster 0: Incidentes noturnos — baixo volume, horário comercial ausente
    - Cluster 1: Picos P2 — alta concentração em horas pico, Alta prioridade
    - Cluster 2: Volume alto P3 — maior cluster, horário comercial, Média prioridade
    - Cluster 3: Team07 anomalias — grupo específico com taxa de violação extrema

    Retorna `disponivel: false` enquanto o notebook 05 não for executado.
    """
    data = load_json("clusters.json")
    if data is None:
        return {"disponivel": False, "mensagem": "Modelo K-Means ainda não treinado"}
    return {"disponivel": True, **data}
