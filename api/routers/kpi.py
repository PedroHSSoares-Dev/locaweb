from typing import Optional, Union
from fastapi import APIRouter, Query
from api.schemas import KpiResponse, NaoDisponivel
from api.services.data_loader import load_json

router = APIRouter(tags=["KPI Operacional"])


@router.get(
    "/kpi",
    response_model=Union[KpiResponse, NaoDisponivel],
    summary="KPI de atingimento OLA — Metodologia SPC",
)
def get_kpi(
    periodo: Optional[str] = Query("ano", description="Filtro temporal: mes | trimestre | ano"),
):
    """
    Retorna o KPI de atingimento das metas de OLA derivadas via SPC.

    **Metodologia:** Meta = média mensal histórica + 1 desvio padrão (Statistical Process Control).
    Meses acima do limiar representam anomalias operacionais.

    **Metas derivadas (2025):**
    - P2: meta anual = 63 violações (média 3.5/mês + σ 1.7)
    - P3: meta anual = 280 violações (média 17.2/mês + σ 6.2)

    **Filtro `periodo`:**
    - `ano` (padrão): KPI do ano completo
    - `trimestre`: KPI apenas do Q4 (out/nov/dez)
    - `mes`: KPI apenas de dezembro

    Retorna `disponivel: false` enquanto o notebook 07 não for executado.
    """
    data = load_json("kpi_atingimento.json")
    if data is None:
        return {"disponivel": False, "mensagem": "KPI ainda não calculado — execute o notebook 07"}

    if periodo == "mes":
        meses_idx = ["12"]
    elif periodo == "trimestre":
        meses_idx = ["10", "11", "12"]
    else:
        meses_idx = [str(m) for m in range(1, 13)]

    por_mes_completo = data.get("por_mes", {})
    por_mes_filtrado = {
        p: {k: v for k, v in meses.items() if k in meses_idx}
        for p, meses in por_mes_completo.items()
    }

    def recalcular_periodo(prioridade):
        meses_viol = por_mes_filtrado.get(prioridade, {})
        viol = sum(meses_viol.values())
        meta_mensal = data[prioridade]["metaMensal"]
        n_meses = len(meses_idx)
        meta_periodo = round(meta_mensal * n_meses)
        pct_utilizado = round(viol / meta_periodo * 100, 1) if meta_periodo > 0 else 0.0
        margem = meta_periodo - viol
        pct_atingimento = min(100, int(meta_periodo / viol * 100)) if viol > 0 else 100
        return {
            **data[prioridade],
            "violacoesAno":   viol,
            "metaAnual":      meta_periodo,
            "pctUtilizado":   pct_utilizado,
            "margemRestante": margem,
            "pctAtingimento": pct_atingimento,
            "periodo_filtro": periodo,
        }

    return {
        "disponivel":     True,
        "metodologia":    data.get("metodologia"),
        "gerado_em":      data.get("gerado_em"),
        "periodo_filtro": periodo,
        "P2":             recalcular_periodo("P2"),
        "P3":             recalcular_periodo("P3"),
        "por_mes":        por_mes_filtrado,
    }
