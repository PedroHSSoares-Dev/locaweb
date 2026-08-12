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

    **Gerado por** `src/models/kmeans_model.py` via `python src/pipeline.py --step km`.
    O JSON gerado em `outputs/clusters.json` deve conter uma lista de clusters,
    cada um com:

    - `id`: índice técnico do cluster (não é estável entre retreinos)
    - `label`: nome descritivo (ex.: "Cluster Noturno", "Picos P2")
    - `tamanho`: número de incidentes no cluster
    - `taxaViolacao`: percentual de violações de OLA no cluster
    - `perfil`: hora média, concentração P2, fim de semana e dias críticos
    - `descricao`: interpretação do padrão identificado

    Os IDs podem mudar após o retreino; consumidores devem ordenar por métricas
    e usar `label`, nunca assumir que um perfil continuará sendo “cluster 4”.

    Retorna `disponivel: false` se `outputs/clusters.json` não existir.
    """
    data = load_json("clusters.json")
    if data is None:
        return {"disponivel": False, "mensagem": "Modelo K-Means não disponível — execute: python src/pipeline.py --step km"}
    return {"disponivel": True, **data}
