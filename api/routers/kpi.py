from typing import Union
from fastapi import APIRouter
from api.schemas import KpiResponse, NaoDisponivel
from api.services.data_loader import load_json

router = APIRouter(tags=["KPI Operacional"])


@router.get(
    "/kpi",
    response_model=Union[KpiResponse, NaoDisponivel],
    summary="Projeção de atingimento das metas anuais de OLA",
)
def get_kpi():
    """
    Retorna a projeção de atingimento das metas anuais de violação de OLA
    para **P2** e **P3**, calculada com base na série histórica e na previsão Prophet.

    **Disponível apenas após execução do notebook 07** (`07_kpi_projection.ipynb`).

    ### Metas anuais (contrato Locaweb 2025)
    | Prioridade | OLA | Meta de violações/ano |
    |---|---|---|
    | P2 (Alta) | ≤ 4h | 36–39 |
    | P3 (Média) | ≤ 12h | 231–263 |

    ### Resultado real 2025
    | Prioridade | Violações | Status |
    |---|---|---|
    | P2 | 42 | ❌ Acima da meta |
    | P3 | 196 | ✅ Dentro da meta |

    Campos por prioridade:
    - **pctAtingimento**: percentual de atingimento (100% = dentro da meta superior)
    - **previsaoFechamento**: violações projetadas ao final do ano

    Retorna `disponivel: false` enquanto o notebook 07 não for executado.
    """
    data = load_json("kpi_atingimento.json")
    if data is None:
        return {"disponivel": False, "mensagem": "Projeção de KPI ainda não calculada"}
    return {"disponivel": True, **data}
