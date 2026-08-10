from typing import Optional, Union
from fastapi import APIRouter, Query
from api.schemas import KpiResponse, NaoDisponivel
from api.services.data_loader import load_json

router = APIRouter(tags=["KPI Operacional"])


@router.get(
    "/kpi",
    response_model=Union[KpiResponse, NaoDisponivel],
    summary="KPI de atingimento OLA — Metas de negócio",
)
def get_kpi(
    periodo: Optional[str] = Query("ano", description="Filtro temporal: mes | trimestre | ano"),
):
    """
    Retorna o KPI de atingimento das metas anuais de negócio de OLA.

    **Metas de negócio (2025):**
    - P2: faixa anual 36–39; referência central 37
    - P3: faixa anual 231–263; referência central 247

    **Filtro `periodo`:**
    - `ano` (padrão): KPI do ano completo
    - `trimestre`: KPI apenas do Q4 (out/nov/dez)
    - `mes`: KPI apenas de dezembro

    Retorna `disponivel: false` se `outputs/kpi_atingimento.json` não existir.
    """
    data = load_json("kpi_atingimento.json")
    if data is None:
        return {"disponivel": False, "mensagem": "KPI não disponível — execute: python src/pipeline.py --step kpi"}

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

    metas_negocio = {"P2": (36, 39), "P3": (231, 263)}

    def recalcular_periodo(prioridade):
        meses_viol = por_mes_filtrado.get(prioridade, {})
        viol = sum(meses_viol.values())
        meta_mensal = data[prioridade]["metaMensal"]
        n_meses = len(meses_idx)
        meta_periodo = round(meta_mensal * n_meses)
        meta_min_anual, meta_max_anual = metas_negocio[prioridade]
        meta_min = round(meta_min_anual * n_meses / 12)
        meta_max = round(meta_max_anual * n_meses / 12)
        pct_utilizado = round(viol / meta_periodo * 100, 1) if meta_periodo > 0 else 0.0
        margem = meta_periodo - viol
        pct_atingimento = min(100, int(meta_periodo / viol * 100)) if viol > 0 else 100
        return {
            **data[prioridade],
            "violacoesAno":   viol,
            "metaAnual":      meta_periodo,
            "metaMin":        meta_min,
            "metaMax":        meta_max,
            "pctUtilizado":   pct_utilizado,
            "margemRestante": margem,
            "pctAtingimento": pct_atingimento,
            "periodo_filtro": periodo,
        }

    return {
        "disponivel":     True,
        "metodologia":    "meta_negocio_distribuida",
        "gerado_em":      data.get("gerado_em"),
        "periodo_filtro": periodo,
        "P2":             recalcular_periodo("P2"),
        "P3":             recalcular_periodo("P3"),
        "por_mes":        por_mes_filtrado,
    }
