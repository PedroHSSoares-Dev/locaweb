"""
Feature engineering pipeline — gera incidents_features.parquet a partir do dataset bruto.

Convenção de nomes alinhada com NB04/NB05:
  produto_enc, categoria_enc, subcategoria_enc, grupo_enc, aberto_por_enc
  produto_freq, grupo_freq, mes_sin, mes_cos
"""
from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

sys.path.insert(0, str(Path(__file__).parent))
from feriados import build_holiday_features
sys.path.pop(0)

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).parents[2]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "LW-DATASET.xlsx"
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "incidents_features.parquet"

# Features geradas por este módulo (todas disponíveis no parquet)
FEATURES = [
    # Temporais
    "hora", "dia_semana", "mes", "trimestre", "dia_mes", "semana_ano",
    # Binárias / ordinais
    "is_horario_comercial", "is_fim_de_semana", "is_segunda_terca", "periodo_dia",
    # Lags de volume geral
    "lag_1d", "lag_7d", "rolling_7d", "rolling_30d",
    # Lags por prioridade (P2/P3)
    "lag_1d_p2", "lag_1d_p3",
    # Prioridade
    "prioridade_bin",
    # Categóricas — label encoded
    "produto_enc", "categoria_enc", "subcategoria_enc", "grupo_enc", "aberto_por_enc",
    # Categóricas — frequency encoded
    "produto_freq", "grupo_freq",
    # Cíclicas
    "mes_sin", "mes_cos",
    # Feriados (nacionais + SP estado + SP município)
    "is_feriado", "tipo_feriado", "dias_ate_feriado", "dias_desde_feriado",
]
TARGET = "target_ola"


def _periodo_dia(h: int) -> int:
    if 0 <= h < 6:
        return 0
    elif 6 <= h < 12:
        return 1
    elif 12 <= h < 18:
        return 2
    return 3


def build_features(raw_path: Path = RAW_PATH) -> pd.DataFrame:
    """Carrega o dataset bruto e retorna o DataFrame com todas as features."""
    df = pd.read_excel(raw_path)

    kpi = df[df["Entrou para KPI?"] == "SIM"].copy()

    prioridades = set(kpi["Prioridade"].unique())
    assert prioridades <= {"2 - Alta", "3 - Média"}, f"Prioridades inesperadas: {prioridades}"
    assert "Sem Intervenção" not in kpi["Status"].values, "Status inválido no subset KPI"

    # Target
    kpi["target_ola"] = (kpi["KPI Violado?"] == "SIM").astype(int)

    # Features temporais
    kpi["hora"] = kpi["Aberto"].dt.hour
    kpi["dia_semana"] = kpi["Aberto"].dt.dayofweek
    kpi["mes"] = kpi["Aberto"].dt.month
    kpi["trimestre"] = kpi["Aberto"].dt.quarter
    kpi["dia_mes"] = kpi["Aberto"].dt.day
    kpi["semana_ano"] = kpi["Aberto"].dt.isocalendar().week.astype(int)

    kpi["is_horario_comercial"] = kpi["hora"].between(9, 17).astype(int)
    kpi["is_fim_de_semana"] = (kpi["dia_semana"] >= 5).astype(int)
    kpi["is_segunda_terca"] = (kpi["dia_semana"] <= 1).astype(int)
    kpi["periodo_dia"] = kpi["hora"].apply(_periodo_dia)

    # Features cíclicas
    kpi["mes_sin"] = np.sin(2 * np.pi * kpi["mes"] / 12)
    kpi["mes_cos"] = np.cos(2 * np.pi * kpi["mes"] / 12)

    # Feriados — nacionais + SP estado + SP município
    feriados_df = build_holiday_features(kpi["Aberto"])
    feriados_df.index = kpi.index
    kpi = pd.concat([kpi, feriados_df], axis=1)

    # Lags e médias móveis (volume diário geral)
    kpi["data"] = kpi["Aberto"].dt.date
    vol = kpi.groupby("data").size().reset_index(name="vol_dia")
    vol["data"] = pd.to_datetime(vol["data"])
    vol = vol.sort_values("data")

    vol["lag_1d"] = vol["vol_dia"].shift(1)
    vol["lag_7d"] = vol["vol_dia"].shift(7)
    vol["rolling_7d"] = vol["vol_dia"].rolling(7, min_periods=1).mean().round(2)
    vol["rolling_30d"] = vol["vol_dia"].rolling(30, min_periods=1).mean().round(2)

    # Lags por prioridade
    for prio_label, prio_name in [("2 - Alta", "p2"), ("3 - Média", "p3")]:
        vol_prio = (
            kpi[kpi["Prioridade"] == prio_label]
            .groupby("data")
            .size()
            .reset_index(name=f"vol_{prio_name}")
        )
        vol_prio["data"] = pd.to_datetime(vol_prio["data"])
        vol = vol.merge(vol_prio, on="data", how="left")
        vol[f"vol_{prio_name}"] = vol[f"vol_{prio_name}"].fillna(0)
        vol[f"lag_1d_{prio_name}"] = vol[f"vol_{prio_name}"].shift(1)

    merge_cols = ["data", "lag_1d", "lag_7d", "rolling_7d", "rolling_30d", "lag_1d_p2", "lag_1d_p3"]
    kpi["data_dt"] = pd.to_datetime(kpi["data"])
    kpi = kpi.merge(vol[merge_cols], left_on="data_dt", right_on="data", how="left", suffixes=("", "_vol"))
    kpi = kpi.dropna(subset=["lag_1d", "lag_7d"])

    # Prioridade binária
    kpi["prioridade_bin"] = (kpi["Prioridade"] == "2 - Alta").astype(int)

    # Nulos categóricos — MNAR, ausência é sinal preditivo
    for col in ["Produto", "Categoria", "Subcategoria"]:
        kpi[col] = kpi[col].fillna("DESCONHECIDO")

    # Label encoding
    le = LabelEncoder()
    enc_map = {
        "Produto": "produto_enc",
        "Categoria": "categoria_enc",
        "Subcategoria": "subcategoria_enc",
        "Grupo designado": "grupo_enc",
        "Aberto por": "aberto_por_enc",
    }
    for col, enc_col in enc_map.items():
        kpi[enc_col] = le.fit_transform(kpi[col].astype(str))

    # Frequency encoding
    for col, freq_col in [("Produto", "produto_freq"), ("Grupo designado", "grupo_freq")]:
        freq_map = kpi[col].value_counts(normalize=True).to_dict()
        kpi[freq_col] = kpi[col].map(freq_map).round(6)

    df_model = kpi[FEATURES + [TARGET]].copy()
    for c in ["lag_1d_p2", "lag_1d_p3"]:
        df_model[c] = df_model[c].fillna(0)

    assert df_model.isnull().sum().sum() == 0, "Dataset com nulos após feature engineering"

    return df_model


def save_features(df: pd.DataFrame, path: Path = PROCESSED_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    df.to_csv(path.with_suffix(".csv"), index=False)


if __name__ == "__main__":
    print("Gerando features...")
    df = build_features()
    save_features(df)
    n_viol = int(df[TARGET].sum())
    print(f"OK — {df.shape[0]} incidentes, {df.shape[1]} colunas")
    print(f"Target: {n_viol} violações ({df[TARGET].mean()*100:.2f}%)")
    print(f"Parquet: {PROCESSED_PATH}")
