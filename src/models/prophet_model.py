"""
Prophet — previsão de volume de incidentes (D+1 a D+7).

Consolida os notebooks 03, 03b e 03c:
  - 03b: Block Bootstrap Monte Carlo (gera dados sintéticos 2023-2024)
  - 03:  Ensemble v5+v6 treinado nos dados reais de 2025
  - 03c: Ensemble v5+v6 treinado na série Monte Carlo 2023-2025

Saídas:
  outputs/previsoes_volume.json     — modelo 2025-only (padrão do dashboard)
  outputs/previsoes_volume_mc.json  — modelo Monte Carlo (3 anos)
  models_saved/prophet_*.pkl        — modelos serializados

Feriados: apenas nacionais (Carnaval e Corpus Christi incluídos via Páscoa).
"""
from __future__ import annotations

import json
import pickle
import sys
import warnings
from datetime import date, timedelta
from pathlib import Path

import holidays as hol
import numpy as np
import pandas as pd
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).parents[2]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "LW-DATASET.xlsx"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "previsoes_volume.json"
OUTPUT_MC_PATH = PROJECT_ROOT / "outputs" / "previsoes_volume_mc.json"
MODELS_DIR = PROJECT_ROOT / "models_saved"

# Parâmetros Prophet (versão final dos notebooks)
PROPHET_PARAMS = dict(
    yearly_seasonality=True,
    weekly_seasonality=True,
    daily_seasonality=False,
    seasonality_mode="multiplicative",
    changepoint_prior_scale=0.01,
    holidays_prior_scale=8.0,
    seasonality_prior_scale=10.0,
)

# Regressores extras além dos lags
LAG_COLS = ["lag_1d", "lag_7d", "rolling_7d", "rolling_30d"]

# Floor mínimo por dia da semana (P10 histórico — impede previsões irreais)
FLOOR_P10 = {
    "total": {0: 79, 1: 70, 2: 41, 3: 64, 4: 56, 5: 29, 6: 21},
    "p2":    {0: 17, 1: 14, 2: 10, 3: 10, 4: 10, 5: 11, 6: 10},
    "p3":    {0: 55, 1: 54, 2: 30, 3: 49, 4: 46, 5: 16, 6: 10},
}


# ── Feriados ──────────────────────────────────────────────────────────────────

def _easter(year: int) -> date:
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(114 + h + l - 7 * m, 31)
    return date(year, month, day + 1)


def build_prophet_holidays(anos: range = range(2023, 2027)) -> pd.DataFrame:
    """DataFrame {ds, holiday} com feriados nacionais para o Prophet."""
    rows = []
    for year in anos:
        easter = _easter(year)
        for d, name in hol.country_holidays("BR", years=year).items():
            rows.append({"ds": pd.Timestamp(d), "holiday": name})
        rows.append({"ds": pd.Timestamp(easter - timedelta(days=48)), "holiday": "Carnaval — Segunda"})
        rows.append({"ds": pd.Timestamp(easter - timedelta(days=47)), "holiday": "Carnaval — Terça"})
        rows.append({"ds": pd.Timestamp(easter + timedelta(days=60)), "holiday": "Corpus Christi"})

    df = pd.DataFrame(rows).drop_duplicates("ds").sort_values("ds").reset_index(drop=True)
    return df


# ── Carga de dados ────────────────────────────────────────────────────────────

def load_series(path: Path = RAW_PATH) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carrega XLSX e retorna séries diárias (total, P2, P3) — 2025 real."""
    if not path.exists():
        raise FileNotFoundError(f"{path} não encontrado.")

    raw = pd.read_excel(path)
    kpi = raw[raw["Entrou para KPI?"] == "SIM"].copy()
    kpi["data"] = pd.to_datetime(kpi["Aberto"]).dt.normalize()

    def _serie(mask=None) -> pd.DataFrame:
        sub = kpi if mask is None else kpi[mask]
        return (
            sub.groupby("data")
            .size()
            .reset_index(name="y")
            .rename(columns={"data": "ds"})
            .sort_values("ds")
            .reset_index(drop=True)
        )

    serie_total = _serie()
    serie_p2 = _serie(kpi["Prioridade"] == "2 - Alta")
    serie_p3 = _serie(kpi["Prioridade"] == "3 - Média")
    return serie_total, serie_p2, serie_p3


# ── Monte Carlo (Block Bootstrap) ─────────────────────────────────────────────

def _gerar_ano_sintetico(
    ano: int, vol_base: pd.DataFrame, seed: int = 42
) -> pd.DataFrame:
    """Gera um ano sintético por Block Bootstrap semanal (reproduz nb03b)."""
    rng = np.random.default_rng(seed)
    vol_base = vol_base.copy()
    vol_base["semana"] = vol_base["ds"].dt.isocalendar().week.astype(int)
    vol_base["mes"] = vol_base["ds"].dt.month

    datas = pd.date_range(f"{ano}-01-01", f"{ano}-12-31", freq="D")
    resultado = []
    i = 0
    while i < len(datas):
        data_alvo = datas[i]
        mes_alvo = data_alvo.month

        semanas_mesmo_mes = vol_base[vol_base["mes"] == mes_alvo]["semana"].unique()
        if len(semanas_mesmo_mes) == 0:
            semanas_mesmo_mes = vol_base["semana"].unique()

        semana_escolhida = rng.choice(semanas_mesmo_mes)
        bloco = vol_base[vol_base["semana"] == semana_escolhida]["y"].values

        for j, val in enumerate(bloco):
            if i + j >= len(datas):
                break
            ruido = rng.normal(0, 3)
            resultado.append({
                "ds": datas[i + j],
                "y": max(0, round(val + ruido)),
                "dow": datas[i + j].dayofweek,
                "mes": datas[i + j].month,
                "ano": ano,
                "sintetico": True,
            })
        i += len(bloco)

    return pd.DataFrame(resultado).sort_values("ds").reset_index(drop=True)


def build_monte_carlo_series(
    serie_total: pd.DataFrame,
    serie_p2: pd.DataFrame,
    serie_p3: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Estende cada série com dados sintéticos 2023-2024 (Block Bootstrap)."""
    def _extend(serie: pd.DataFrame) -> pd.DataFrame:
        # Prepara base 2025
        base = serie.copy()
        base["dow"] = base["ds"].dt.dayofweek
        base["mes"] = base["ds"].dt.month

        sint_2023 = _gerar_ano_sintetico(2023, base, seed=42)
        sint_2024 = _gerar_ano_sintetico(2024, base, seed=123)

        real_2025 = base.assign(ano=2025, sintetico=False)

        completa = pd.concat(
            [sint_2023, sint_2024, real_2025[["ds", "y", "dow", "mes", "ano", "sintetico"]]],
            ignore_index=True,
        ).sort_values("ds").reset_index(drop=True)

        # Preencher dias ausentes com zero
        calendario = pd.DataFrame({"ds": pd.date_range("2023-01-01", "2025-12-31", freq="D")})
        completa = calendario.merge(completa[["ds", "y"]], on="ds", how="left").fillna({"y": 0.0})
        completa["y"] = completa["y"].astype(float)
        return completa.sort_values("ds").reset_index(drop=True)

    return _extend(serie_total), _extend(serie_p2), _extend(serie_p3)


# ── Preparação de regressores ─────────────────────────────────────────────────

def _add_lag_features(serie: pd.DataFrame) -> pd.DataFrame:
    s = serie.copy()
    s["lag_1d"] = s["y"].shift(1)
    s["lag_7d"] = s["y"].shift(7)
    s["rolling_7d"] = s["y"].rolling(7, min_periods=1).mean()
    s["rolling_30d"] = s["y"].rolling(30, min_periods=1).mean()
    media = s["y"].mean()
    for col in LAG_COLS:
        s[col] = s[col].fillna(media)
    return s


def _add_is_dia_util(serie: pd.DataFrame, feriados_set: set) -> pd.DataFrame:
    s = serie.copy()
    s["is_dia_util"] = s["ds"].dt.dayofweek.apply(lambda d: 0 if d >= 5 else 1).astype(int)
    s.loc[s["ds"].dt.date.isin(feriados_set), "is_dia_util"] = 0
    return s


def _build_futuro(model: Prophet, serie: pd.DataFrame, feriados_set: set, variante: str) -> pd.DataFrame:
    futuro = model.make_future_dataframe(periods=7, freq="D")
    futuro = futuro.merge(serie[["ds"] + LAG_COLS + (["is_dia_util"] if variante == "v6" else [])],
                          on="ds", how="left")
    media_recente = serie["y"].tail(7).mean()
    for col in LAG_COLS:
        futuro[col] = futuro[col].fillna(media_recente)
    if variante == "v6":
        futuro["is_dia_util"] = futuro["is_dia_util"].fillna(
            futuro["ds"].dt.dayofweek.apply(lambda d: 0 if d >= 5 else 1).astype(float)
        )
        futuro.loc[futuro["ds"].dt.date.isin(feriados_set), "is_dia_util"] = 0
    return futuro


# ── Treinamento e cross-validation ────────────────────────────────────────────

def _train_variant(
    serie: pd.DataFrame, feriados_df: pd.DataFrame, feriados_set: set, variante: str
) -> tuple[Prophet, pd.DataFrame, pd.DataFrame]:
    """Treina uma variante (v5 ou v6) e retorna (modelo, previsão, métricas_cv)."""
    m = Prophet(holidays=feriados_df, **PROPHET_PARAMS)
    for col in LAG_COLS:
        m.add_regressor(col)
    if variante == "v6":
        m.add_regressor("is_dia_util")

    m.fit(serie)

    futuro = _build_futuro(m, serie, feriados_set, variante)
    prev = m.predict(futuro)

    cv = cross_validation(m, initial="180 days", period="30 days", horizon="7 days", parallel=None)
    metricas = performance_metrics(cv)
    return m, prev, metricas


def train_series(
    serie: pd.DataFrame, feriados_df: pd.DataFrame, nome: str
) -> tuple[Prophet, Prophet, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Treina v5 e v6 para uma série; retorna ambos os modelos e métricas."""
    feriados_set = set(feriados_df["ds"].dt.date)

    serie_v5 = _add_lag_features(serie)
    serie_v6 = _add_is_dia_util(serie_v5, feriados_set)

    print(f"  [{nome}] treinando v5 (4 lags)...")
    m_v5, prev_v5, met_v5 = _train_variant(serie_v5, feriados_df, feriados_set, "v5")

    print(f"  [{nome}] treinando v6 (4 lags + is_dia_util)...")
    m_v6, prev_v6, met_v6 = _train_variant(serie_v6, feriados_df, feriados_set, "v6")

    return m_v5, m_v6, prev_v5, prev_v6, met_v5, met_v6


# ── Ensemble (melhor modelo por horizonte) ────────────────────────────────────

def build_ensemble(
    serie: pd.DataFrame,
    prev_v5: pd.DataFrame,
    prev_v6: pd.DataFrame,
    met_v5: pd.DataFrame,
    met_v6: pd.DataFrame,
    nome: str,
) -> list[dict]:
    """Para cada D+1..D+7 escolhe v5 ou v6 com menor MAE de CV."""
    ultimo_ds = serie["ds"].max()
    dias_futuros = prev_v5[prev_v5["ds"] > ultimo_ds].head(7).reset_index(drop=True)
    floor_map = FLOOR_P10.get(nome, FLOOR_P10["total"])

    previsao = []
    for i, row_v5 in dias_futuros.iterrows():
        h = i + 1
        ds = row_v5["ds"]

        mae_v5 = met_v5[met_v5["horizon"].dt.days == h]["mae"].values
        mae_v6 = met_v6[met_v6["horizon"].dt.days == h]["mae"].values
        if not len(mae_v5) or not len(mae_v6):
            continue

        row_v6 = prev_v6[prev_v6["ds"] == ds].iloc[0]
        floor = floor_map.get(ds.dayofweek, 0)

        if mae_v5[0] <= mae_v6[0]:
            vencedor, mae_usado = "v5", mae_v5[0]
            yhat = max(floor, round(float(row_v5["yhat"]), 1))
            lower = max(0.0, round(float(row_v5["yhat_lower"]), 1))
            upper = max(floor, round(float(row_v5["yhat_upper"]), 1))
        else:
            vencedor, mae_usado = "v6", mae_v6[0]
            yhat = max(floor, round(float(row_v6["yhat"]), 1))
            lower = max(0.0, round(float(row_v6["yhat_lower"]), 1))
            upper = max(floor, round(float(row_v6["yhat_upper"]), 1))

        previsao.append({
            "dia": ds.strftime("%d/%m"),
            "ds": ds.strftime("%Y-%m-%d"),
            "horizonte": f"D+{h}",
            "modelo": vencedor,
            "mae_usado": round(float(mae_usado), 2),
            "yhat": yhat,
            "yhat_lower": lower,
            "yhat_upper": upper,
        })

    return previsao


# ── Treinamento completo ───────────────────────────────────────────────────────

def train(use_monte_carlo: bool = False) -> dict:
    """Treina Prophet para total, P2 e P3. Retorna resultados e modelos."""
    print("Carregando séries...")
    serie_total, serie_p2, serie_p3 = load_series()

    if use_monte_carlo:
        print("Gerando série Monte Carlo (2023-2025)...")
        serie_total, serie_p2, serie_p3 = build_monte_carlo_series(serie_total, serie_p2, serie_p3)

    feriados_df = build_prophet_holidays()
    modelos = {}
    resultados = {}

    for nome, serie in [("total", serie_total), ("p2", serie_p2), ("p3", serie_p3)]:
        print(f"\nTreinando {nome.upper()}...")
        m_v5, m_v6, prev_v5, prev_v6, met_v5, met_v6 = train_series(serie, feriados_df, nome)

        previsao = build_ensemble(serie, prev_v5, prev_v6, met_v5, met_v6, nome)

        mae_d1 = min(
            met_v5[met_v5["horizon"].dt.days == 1]["mae"].values[0],
            met_v6[met_v6["horizon"].dt.days == 1]["mae"].values[0],
        )
        mae_d7 = min(
            met_v5[met_v5["horizon"].dt.days == 7]["mae"].values[0],
            met_v6[met_v6["horizon"].dt.days == 7]["mae"].values[0],
        )

        modelos[f"prophet_{nome}_v5"] = m_v5
        modelos[f"prophet_{nome}_v6"] = m_v6

        resultados[nome] = {
            "modelo": f"prophet_ensemble_{nome}",
            "gerado_em": date.today().strftime("%Y-%m-%d"),
            "abordagem": "ensemble v5+v6 — melhor modelo por horizonte" + (" (Monte Carlo)" if use_monte_carlo else ""),
            "D1": {
                "yhat": previsao[0]["yhat"],
                "lower": previsao[0]["yhat_lower"],
                "upper": previsao[0]["yhat_upper"],
                "modelo_usado": previsao[0]["modelo"],
            },
            "D7": {
                "yhat": previsao[6]["yhat"],
                "lower": previsao[6]["yhat_lower"],
                "upper": previsao[6]["yhat_upper"],
                "modelo_usado": previsao[6]["modelo"],
            },
            "serie_7d": previsao,
            "metricas": {
                "mae_d1": round(float(mae_d1), 2),
                "mae_d7": round(float(mae_d7), 2),
                "nota": "MAE mínimo entre v5 e v6 por horizonte — CV initial=180d",
            },
        }

        print(f"  [{nome.upper()}] MAE D+1={mae_d1:.2f} | D+7={mae_d7:.2f}")

    return {"resultados": resultados, "modelos": modelos}


# ── Export ────────────────────────────────────────────────────────────────────

def export_json(resultados: dict, path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"JSON exportado: {path}")


def save_models(modelos: dict) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for nome, modelo in modelos.items():
        path = MODELS_DIR / f"{nome}.pkl"
        with open(path, "wb") as f:
            pickle.dump(modelo, f)
    print(f"Modelos salvos em: {MODELS_DIR} ({len(modelos)} arquivos)")


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mc", action="store_true", help="Treinar apenas com Monte Carlo")
    parser.add_argument("--all", dest="all_modes", action="store_true", help="Treinar ambos (2025-only e MC)")
    args = parser.parse_args()

    run_mc_only = args.mc
    run_all = args.all_modes

    if run_all or not run_mc_only:
        print("\n=== Treinando Prophet (2025-only) ===")
        out = train(use_monte_carlo=False)
        export_json(out["resultados"], OUTPUT_PATH)
        save_models(out["modelos"])

    if run_all or run_mc_only:
        print("\n=== Treinando Prophet Monte Carlo (2023-2025) ===")
        out_mc = train(use_monte_carlo=True)
        export_json(out_mc["resultados"], OUTPUT_MC_PATH)
        save_models({f"mc_{k}": v for k, v in out_mc["modelos"].items()})

    print("\nConcluído.")
