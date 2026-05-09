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
    """
    if ano_referencia is None:
        ano_referencia = int(kpi["ano"].max())

    kpi_ano = kpi[kpi["ano"] == ano_referencia].copy()

    resultado = {"ano": ano_referencia, "por_prioridade": {}}

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
        orcamento_mensal_base = meta_centro / 12

        # Status anual
        if total_violacoes <= meta_max:
            status_anual = "dentro_meta"
        elif total_violacoes <= meta_max * 1.2:
            status_anual = "atencao"
        else:
            status_anual = "fora_meta"

        # Análise mensal com ajuste dinâmico
        meses_info = []
        for mes in range(1, 13):
            viol_mes = violacoes_lista[mes - 1]
            meta_ajustada = calcular_meta_ajustada(violacoes_lista, int(meta_centro), mes)
            orcamento = orcamento_mensal_base

            if viol_mes > orcamento * 1.5:
                status_mes = "critico"
            elif viol_mes > orcamento:
                status_mes = "atencao"
            else:
                status_mes = "ok"

            meses_info.append({
                "mes": mes,
                "violacoes": viol_mes,
                "orcamento_base": round(orcamento_mensal_base, 2),
                "meta_ajustada_proximo": round(meta_ajustada, 2),
                "status": status_mes,
            })

        # Projeção fim de ano (tendência dos últimos 3 meses com dados)
        meses_com_dados = [m for m in meses_info if m["violacoes"] > 0]
        if len(meses_com_dados) >= 3:
            media_recente = sum(m["violacoes"] for m in meses_com_dados[-3:]) / 3
            meses_decorridos = len(meses_com_dados)
            meses_restantes = 12 - meses_decorridos
            projecao_fim_ano = total_violacoes + media_recente * meses_restantes
        else:
            projecao_fim_ano = total_violacoes * (12 / max(1, len(meses_com_dados)))

        resultado["por_prioridade"][prio_key] = {
            "meta_anual": {"min": meta_min, "max": meta_max, "centro": meta_centro},
            "total_violacoes_ano": total_violacoes,
            "status_anual": status_anual,
            "projecao_fim_ano": round(projecao_fim_ano, 1),
            "pct_meta_utilizado": round(total_violacoes / meta_centro * 100, 1),
            "meses": meses_info,
        }

    return resultado


def export_json(resultado: dict, path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "modelo": "kpi_projection",
        "gerado_em": date.today().strftime("%Y-%m-%d"),
        "versao": "v2",
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

    for prio, dados in resultado["por_prioridade"].items():
        print(
            f"  {prio}: {dados['total_violacoes_ano']} violações | "
            f"Meta {dados['meta_anual']['min']}-{dados['meta_anual']['max']} | "
            f"Status: {dados['status_anual']}"
        )

    print("\nExportando JSON...")
    export_json(resultado)
    print("Concluído.")
