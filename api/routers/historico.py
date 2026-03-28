"""
historico.py — Serve dados históricos estáticos derivados do dataset real.
Imutáveis — não vêm de JSON de modelo.
Volume diário: dezembro/2025 (02/12–31/12) extraído do LW-DATASET.xlsx.
"""
from typing import Optional, Union
from fastapi import APIRouter, Query
from api.schemas import HistoricoMensalItem, HistoricoDiarioItem, HeatmapItem

router = APIRouter(tags=["Histórico ITSM"])

# ─── Volume mensal 2025 ───────────────────────────────────────────────────────
_VOLUME_MENSAL_2025 = [
    {"mes": "Jan", "P2": 552, "P3": 1805, "total": 2357, "violP2": 4,  "violP3": 19},
    {"mes": "Fev", "P2": 470, "P3": 1812, "total": 2282, "violP2": 4,  "violP3": 21},
    {"mes": "Mar", "P2": 470, "P3": 1660, "total": 2130, "violP2": 3,  "violP3": 16},
    {"mes": "Abr", "P2": 393, "P3": 1679, "total": 2072, "violP2": 2,  "violP3": 10},
    {"mes": "Mai", "P2": 375, "P3": 1872, "total": 2247, "violP2": 6,  "violP3": 15},
    {"mes": "Jun", "P2": 409, "P3": 1696, "total": 2105, "violP2": 3,  "violP3": 28},
    {"mes": "Jul", "P2": 386, "P3": 1740, "total": 2126, "violP2": 6,  "violP3": 23},
    {"mes": "Ago", "P2": 414, "P3": 1916, "total": 2330, "violP2": 3,  "violP3": 14},
    {"mes": "Set", "P2": 442, "P3": 1882, "total": 2324, "violP2": 2,  "violP3":  9},
    {"mes": "Out", "P2": 436, "P3": 1690, "total": 2126, "violP2": 2,  "violP3":  9},
    {"mes": "Nov", "P2": 448, "P3": 1186, "total": 1634, "violP2": 6,  "violP3": 15},
    {"mes": "Dez", "P2": 364, "P3": 1059, "total": 1423, "violP2": 1,  "violP3": 17},
]

# ─── Volume diário — dezembro/2025 (02/12–31/12) extraído do dataset real ────
_VOLUME_DIARIO_30D = [
    {"dia": "02/12", "P2": 17, "P3": 62},
    {"dia": "03/12", "P2":  9, "P3": 59},
    {"dia": "04/12", "P2": 16, "P3": 44},
    {"dia": "05/12", "P2":  7, "P3": 40},
    {"dia": "06/12", "P2":  7, "P3": 26},
    {"dia": "07/12", "P2": 12, "P3": 21},
    {"dia": "08/12", "P2": 12, "P3": 57},
    {"dia": "09/12", "P2": 21, "P3": 53},
    {"dia": "10/12", "P2": 12, "P3": 50},
    {"dia": "11/12", "P2":  8, "P3": 36},
    {"dia": "12/12", "P2":  8, "P3": 42},
    {"dia": "13/12", "P2":  8, "P3": 22},
    {"dia": "14/12", "P2": 10, "P3": 15},
    {"dia": "15/12", "P2": 19, "P3": 71},
    {"dia": "16/12", "P2": 19, "P3": 42},
    {"dia": "17/12", "P2": 10, "P3": 46},
    {"dia": "18/12", "P2": 18, "P3": 47},
    {"dia": "19/12", "P2": 13, "P3": 57},
    {"dia": "20/12", "P2": 11, "P3": 27},
    {"dia": "21/12", "P2": 13, "P3": 20},
    {"dia": "22/12", "P2": 16, "P3": 34},
    {"dia": "23/12", "P2": 13, "P3": 40},
    {"dia": "24/12", "P2":  8, "P3": 32},
    {"dia": "25/12", "P2":  6, "P3": 16},
    {"dia": "26/12", "P2":  9, "P3": 22},
    {"dia": "27/12", "P2": 10, "P3":  8},
    {"dia": "28/12", "P2":  7, "P3":  5},
    {"dia": "29/12", "P2": 19, "P3":  7},
    {"dia": "30/12", "P2":  5, "P3":  5},
    {"dia": "31/12", "P2":  9, "P3":  1},
]

# ─── Heatmap sazonalidade (incidentes por hora × dia da semana) ───────────────
_HEATMAP_DATA = [
    {"dia": "Seg", "horas": [85,56,28,56,37,54,35,47,177,316,355,384,334,268,275,367,317,267,171,129,125,172,135,75]},
    {"dia": "Ter", "horas": [90,88,85,79,60,83,62,67,217,315,357,374,336,247,312,368,334,293,154,165,157,162,149,72]},
    {"dia": "Qua", "horas": [94,86,66,81,55,53,40,59,198,311,373,377,316,286,309,388,335,241,165,169,130,181,112,76]},
    {"dia": "Qui", "horas": [88,72,58,74,51,60,45,55,192,308,365,352,328,279,301,420,329,258,161,162,128,178,119,79]},
    {"dia": "Sex", "horas": [75,65,52,67,46,54,40,50,175,285,342,369,305,261,285,369,308,241,148,150,119,165,108,71]},
    {"dia": "Sáb", "horas": [42,38,31,39,27,32,24,29,98,161,193,208,172,147,161,208,174,136,84,85,67,93,61,40]},
    {"dia": "Dom", "horas": [27,24,20,25,17,20,15,18,62,102,122,132,109,93,102,132,110,86,53,54,42,59,39,25]},
]


@router.get(
    "/historico/mensal",
    response_model=list[HistoricoMensalItem],
    summary="Série mensal de incidentes e violações — 2025",
)
def get_historico_mensal(
    periodo: Optional[str] = Query("ano", description="Filtro temporal: mes | trimestre | ano"),
):
    """
    Retorna a série mensal real de **2025** com volume de incidentes KPI (P2 e P3)
    e contagem de violações de OLA por mês.

    **Filtro `periodo`:**
    - `ano` (padrão): todos os 12 meses (Jan–Dez)
    - `trimestre`: últimos 3 meses (Out, Nov, Dez — Q4 2025)
    - `mes`: apenas o último mês disponível (Dez)

    **Dados extraídos diretamente do LW-DATASET.xlsx** — 122.543 incidentes reais.

    Campos por mês:
    - **P2** / **P3**: total de incidentes abertos no mês
    - **total**: P2 + P3
    - **violP2**: incidentes P2 que ultrapassaram 4h (OLA violado)
    - **violP3**: incidentes P3 que ultrapassaram 12h (OLA violado)

    Usado nos gráficos de tendência mensal e barras de violação do GestaoPage.
    """
    if periodo == "mes":
        return _VOLUME_MENSAL_2025[-1:]
    if periodo == "trimestre":
        return _VOLUME_MENSAL_2025[-3:]
    return _VOLUME_MENSAL_2025


@router.get(
    "/historico/diario",
    response_model=list[HistoricoDiarioItem],
    summary="Volume diário — dezembro/2025 (02/12–31/12)",
)
def get_historico_diario(
    periodo: Optional[str] = Query("ano", description="Filtro temporal: mes | trimestre | ano"),
):
    """
    Retorna o volume diário real de incidentes KPI de **02/12 a 31/12/2025**
    (30 dias imediatamente anteriores à janela de previsão do Prophet).

    **Filtro `periodo`:**
    - `mes` ou `ano` (padrão): todos os 30 dias disponíveis (dados só cobrem Dez)
    - `trimestre`: todos os 30 dias disponíveis (idem — dados cobrem apenas Dez)

    **Por que dezembro?**
    A previsão Prophet começa em **01/01/2026**. Para que o gráfico de área
    do MonitoramentoPage mostre o histórico conectado à previsão sem gap,
    o histórico precisa terminar em 31/12/2025.

    O formato `DD/MM` do campo `dia` é idêntico ao formato retornado pelo
    endpoint `/previsoes/serie`, garantindo continuidade no eixo X do Recharts.

    Dados extraídos do LW-DATASET.xlsx — incidentes com `Entrou para KPI? = SIM`.
    """
    return _VOLUME_DIARIO_30D


@router.get(
    "/historico/sazonalidade",
    response_model=list[HeatmapItem],
    summary="Heatmap hora × dia da semana — período 2023–2025",
)
def get_historico_sazonalidade():
    """
    Retorna o heatmap de concentração de incidentes por **hora × dia da semana**,
    acumulado em todo o período do dataset (jan/2023–dez/2025).

    Cada entrada representa um dia da semana (Seg a Dom) com **24 valores**
    — um por hora do dia (índice 0 = hora 00h, índice 23 = hora 23h).

    **Este é um dado descritivo — não é previsão.** Representa o padrão
    histórico de abertura de incidentes KPI.

    **Pico identificado:** Quinta-feira às 15h (420 incidentes acumulados).

    Usado no heatmap de sazonalidade do MonitoramentoPage.
    """
    return _HEATMAP_DATA
