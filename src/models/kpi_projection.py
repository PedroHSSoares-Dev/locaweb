"""
Projeção anual de KPI com ajuste mensal dinâmico.

Calcula violações reais por mês, distribui a meta anual mensalmente,
detecta quando um mês estoura o orçamento e redistribui o restante.
Exporta outputs/kpi_atingimento.json.

Metas (CLAUDE.md):
  P2 (Alta): 36–39 violações/ano | P3 (Média): 231–263 violações/ano
"""
from __future__ import annotations

import json
import warnings
from datetime import date
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).parents[2]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "LW-DATASET.xlsx"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "kpi_atingimento.json"

OLA_MAP = {"2 - Alta": 14_400, "3 - Média": 43_200}

META_ANUAL = {
    "P2": {"min": 36, "max": 39},
    "P3": {"min": 231, "max": 263},
}

OLA_HORAS = {"P2": 4, "P3": 12}

NOMES_MESES = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
    5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}


def calcular_meta_ajustada(
    violacoes_por_mes: list[int],
    meta_anual: int,
    mes_atual: int,
) -> float:
    """
    Redistribui a meta restante pelos meses futuros.
    Se setembro (mes_atual=9) já usou mais que o orçamento acumulado,
    outubro em diante terá orçamento menor para compensar.
    """
    violacoes_ate_agora = sum(violacoes_por_mes[:mes_atual])
    meses_restantes = 12 - mes_atual
    if meses_restantes <= 0:
        return 0.0
    meta_restante = meta_anual - violacoes_ate_agora
    return max(0.0, meta_restante / meses_restantes)


def load_data(raw_path: Path = RAW_PATH) -> pd.DataFrame:
    df = pd.read_excel(raw_path)
    kpi = df[df["Entrou para KPI?"] == "SIM"].copy()
    kpi = kpi[kpi["Prioridade"].isin(["2 - Alta", "3 - Média"])].copy()
    kpi["ano"] = kpi["Aberto"].dt.year
    kpi["mes"] = kpi["Aberto"].dt.month
    kpi["violou"] = (kpi["KPI Violado?"] == "SIM").astype(int)
    return kpi


def calcular_projecao(kpi: pd.DataFrame, ano_referencia: int | None = None) -> dict:
    """
    Calcula KPI atingimento para o ano de referência (último ano do dataset se None).
    Formato de saída compatível com o schema KpiResponse da API FastAPI.
    """
    if ano_referencia is None:
        ano_referencia = int(kpi["ano"].max())

    kpi_ano = kpi[kpi["ano"] == ano_referencia].copy()

    resultado: dict = {"ano": ano_referencia}
    por_mes: dict = {}

    for prio_label, prio_key in [("2 - Alta", "P2"), ("3 - Média", "P3")]:
        sub = kpi_ano[kpi_ano["Prioridade"] == prio_label]

        # Violações por mês
        mensal = (
            sub.groupby("mes")["violou"].sum()
            .reindex(range(1, 13), fill_value=0)
            .astype(int)
        )
        violacoes_lista = mensal.tolist()
        total_violacoes = int(sum(violacoes_lista))

        meta_min = META_ANUAL[prio_key]["min"]
        meta_max = META_ANUAL[prio_key]["max"]
        meta_centro = (meta_min + meta_max) / 2
        meta_mensal = meta_centro / 12

        # Status / tendência anual
        if total_violacoes <= meta_max:
            tendencia = "dentro_da_meta"
        elif total_violacoes <= meta_max * 1.2:
            tendencia = "atencao"
        else:
            tendencia = "fora_da_meta"

        # Meses anômalos (status critico ou atencao)
        meses_anomalos = []
        for mes in range(1, 13):
            viol = violacoes_lista[mes - 1]
            if viol > meta_mensal * 1.5:
                meses_anomalos.append(NOMES_MESES[mes])
            elif viol > meta_mensal:
                meses_anomalos.append(NOMES_MESES[mes])

        # pct e margem
        pct_utilizado = round(total_violacoes / meta_centro * 100, 1) if meta_centro > 0 else 0.0
        margem_restante = int(meta_centro - total_violacoes)
        pct_atingimento = min(100, int(meta_centro / total_violacoes * 100)) if total_violacoes > 0 else 100

        resultado[prio_key] = {
            "violacoesAno":   total_violacoes,
            "metaAnual":      int(meta_centro),
            "metaMensal":     round(meta_mensal, 2),
            "pctUtilizado":   pct_utilizado,
            "margemRestante": margem_restante,
            "tendencia":      tendencia,
            "olaHoras":       OLA_HORAS[prio_key],
            "pctAtingimento": pct_atingimento,
            "mesesAnomalos":  meses_anomalos,
        }

        # por_mes: chave = número do mês como string (ex.: "1", "2", ...)
        por_mes[prio_key] = {str(m): int(violacoes_lista[m - 1]) for m in range(1, 13)}

    resultado["por_mes"] = por_mes
    return resultado


def export_json(resultado: dict, path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "modelo": "kpi_projection",
        "metodologia": "meta_anual_distribuida",
        "gerado_em": date.today().strftime("%Y-%m-%d"),
        **resultado,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"JSON exportado: {path}")


if __name__ == "__main__":
    print("Carregando dataset...")
    kpi = load_data()
    print(f"Dataset: {len(kpi)} incidentes KPI")

    print("\nCalculando projeção...")
    resultado = calcular_projecao(kpi)

    for prio in ["P2", "P3"]:
        dados = resultado[prio]
        print(
            f"  {prio}: {dados['violacoesAno']} violações | "
            f"Meta ±{dados['metaAnual']} | "
            f"Status: {dados['tendencia']}"
        )

    print("\nExportando JSON...")
    export_json(resultado)
    print("Concluído.")
