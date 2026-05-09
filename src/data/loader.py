"""Utilitário de carregamento do dataset bruto."""
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parents[2]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "LW-DATASET.xlsx"


def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    """Carrega o dataset XLSX bruto com tipos corretos."""
    if not path.exists():
        raise FileNotFoundError(f"Dataset não encontrado: {path}")
    df = pd.read_excel(path)
    return df


def load_kpi_subset(path: Path = RAW_PATH) -> pd.DataFrame:
    """Retorna apenas os incidentes P2/P3 que entraram para KPI."""
    df = load_raw(path)
    kpi = df[df["Entrou para KPI?"] == "SIM"].copy()
    kpi = kpi[kpi["Prioridade"].isin(["2 - Alta", "3 - Média"])].copy()
    return kpi.sort_values("Aberto").reset_index(drop=True)
