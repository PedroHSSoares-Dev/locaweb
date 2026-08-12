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

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).parents[2]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "LW-DATASET.xlsx"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "previsoes_volume.json"
OUTPUT_MC_PATH = PROJECT_ROOT / "outputs" / "previsoes_volume_mc.json"
MODELS_DIR = PROJECT_ROOT / "models_saved"
VALIDATION_START = pd.Timestamp("2025-07-01")
HOLDOUT_START = pd.Timestamp("2025-10-01")
HOLDOUT_END = pd.Timestamp("2025-12-31")
COMMON_HOLDOUT_PROTOCOL = "rolling_origin_2025Q4_D1_D7"

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
        grouped = (
            sub.groupby("data")
            .size()
            .reset_index(name="y")
            .rename(columns={"data": "ds"})
            .sort_values("ds")
            .reset_index(drop=True)
        )
        calendar = pd.DataFrame({"ds": pd.date_range("2025-01-01", "2025-12-31", freq="D")})
        grouped = calendar.merge(grouped, on="ds", how="left").fillna({"y": 0})
        grouped["y"] = grouped["y"].astype(float)
        return grouped

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
        # A base sintética termina antes da janela de seleção (jul–set) e do
        # holdout final (out–dez). Assim nenhum padrão futuro é copiado para
        # os anos sintéticos usados no treino.
        bootstrap_base = serie[serie["ds"] < VALIDATION_START].copy()
        bootstrap_base["dow"] = bootstrap_base["ds"].dt.dayofweek
        bootstrap_base["mes"] = bootstrap_base["ds"].dt.month

        sint_2023 = _gerar_ano_sintetico(2023, bootstrap_base, seed=42)
        sint_2024 = _gerar_ano_sintetico(2024, bootstrap_base, seed=123)

        real_2025 = serie.copy()
        real_2025["dow"] = real_2025["ds"].dt.dayofweek
        real_2025["mes"] = real_2025["ds"].dt.month
        real_2025 = real_2025.assign(ano=2025, sintetico=False)

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
    past = s["y"].shift(1)
    s["rolling_7d"] = past.rolling(7, min_periods=1).mean()
    s["rolling_30d"] = past.rolling(30, min_periods=1).mean()
    media = s["y"].mean()
    for col in LAG_COLS:
        s[col] = s[col].fillna(media)
    return s


def _add_is_dia_util(serie: pd.DataFrame, feriados_set: set) -> pd.DataFrame:
    s = serie.copy()
    s["is_dia_util"] = s["ds"].dt.dayofweek.apply(lambda d: 0 if d >= 5 else 1).astype(int)
    s.loc[s["ds"].dt.date.isin(feriados_set), "is_dia_util"] = 0
    return s


def _fit_variant(
    serie: pd.DataFrame,
    feriados_df: pd.DataFrame,
    feriados_set: set,
    variant: str,
) -> Prophet:
    prepared = _add_lag_features(serie)
    if variant == "v6":
        prepared = _add_is_dia_util(prepared, feriados_set)
    model = Prophet(holidays=feriados_df, **PROPHET_PARAMS)
    for column in LAG_COLS:
        model.add_regressor(column)
    if variant == "v6":
        model.add_regressor("is_dia_util")
    model.fit(prepared)
    return model


def _recursive_forecast(
    model: Prophet,
    history: pd.Series,
    target_dates: pd.DatetimeIndex,
    variant: str,
    feriados_set: set,
) -> list[dict]:
    """Forecast sequentially so future regressors never use future actuals."""
    values = history.astype(float).copy().sort_index()
    points: list[dict] = []
    for target_date in target_dates:
        recent_mean = float(values.tail(7).mean()) if len(values) else 0.0
        row = {
            "ds": target_date,
            "lag_1d": float(values.iloc[-1]) if len(values) else recent_mean,
            "lag_7d": float(values.iloc[-7]) if len(values) >= 7 else recent_mean,
            "rolling_7d": recent_mean,
            "rolling_30d": float(values.tail(30).mean()) if len(values) else recent_mean,
        }
        if variant == "v6":
            row["is_dia_util"] = float(
                target_date.dayofweek < 5 and target_date.date() not in feriados_set
            )
        prediction = model.predict(pd.DataFrame([row])).iloc[0]
        central = max(0.0, float(prediction["yhat"]))
        points.append({
            "ds": target_date,
            "yhat": central,
            "yhat_lower": max(0.0, float(prediction["yhat_lower"])),
            "yhat_upper": max(0.0, float(prediction["yhat_upper"])),
        })
        values.loc[target_date] = central
    return points


def _rolling_origin_errors(
    model: Prophet,
    serie: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    variant: str,
    feriados_set: set,
) -> dict[int, list[float]]:
    actual = serie.set_index("ds")["y"].astype(float).sort_index()
    errors: dict[int, list[float]] = {horizon: [] for horizon in range(1, 8)}
    origins = pd.date_range(start - pd.Timedelta(days=1), end - pd.Timedelta(days=1), freq="D")
    for origin in origins:
        horizon = min(7, (end - origin).days)
        dates = pd.date_range(origin + pd.Timedelta(days=1), periods=horizon, freq="D")
        predictions = _recursive_forecast(
            model, actual.loc[:origin], dates, variant, feriados_set,
        )
        for offset, point in enumerate(predictions, start=1):
            errors[offset].append(abs(float(actual.loc[point["ds"]]) - point["yhat"]))
    return errors


def _mean_errors(errors: dict[int, list[float]]) -> dict[int, float]:
    return {horizon: float(np.mean(values)) for horizon, values in errors.items()}


def train_series(
    serie: pd.DataFrame,
    feriados_df: pd.DataFrame,
    nome: str,
) -> tuple[Prophet, Prophet, list[dict], dict]:
    """Select before Q4, evaluate once on Q4, then fit full deployable models."""
    feriados_set = set(feriados_df["ds"].dt.date)
    selection_train = serie[serie["ds"] < VALIDATION_START].copy()
    evaluation_train = serie[serie["ds"] < HOLDOUT_START].copy()
    validation_errors = {}
    holdout_errors = {}

    for variant in ("v5", "v6"):
        print(f"  [{nome}] seleção {variant} — treino até 30/06...")
        selection_model = _fit_variant(selection_train, feriados_df, feriados_set, variant)
        validation_errors[variant] = _rolling_origin_errors(
            selection_model,
            serie,
            VALIDATION_START,
            HOLDOUT_START - pd.Timedelta(days=1),
            variant,
            feriados_set,
        )
        print(f"  [{nome}] holdout {variant} — treino até 30/09...")
        evaluation_model = _fit_variant(evaluation_train, feriados_df, feriados_set, variant)
        holdout_errors[variant] = _rolling_origin_errors(
            evaluation_model,
            serie,
            HOLDOUT_START,
            HOLDOUT_END,
            variant,
            feriados_set,
        )

    validation_mae = {
        variant: _mean_errors(errors) for variant, errors in validation_errors.items()
    }
    selected = {
        horizon: min(("v5", "v6"), key=lambda variant: validation_mae[variant][horizon])
        for horizon in range(1, 8)
    }
    holdout_mae = {
        horizon: float(np.mean(holdout_errors[selected[horizon]][horizon]))
        for horizon in range(1, 8)
    }

    print(f"  [{nome}] treino final v5/v6 até 31/12...")
    final_models = {
        variant: _fit_variant(serie, feriados_df, feriados_set, variant)
        for variant in ("v5", "v6")
    }
    history = serie.set_index("ds")["y"].astype(float).sort_index()
    future_dates = pd.date_range(serie["ds"].max() + pd.Timedelta(days=1), periods=7, freq="D")
    forecasts = {
        variant: _recursive_forecast(
            final_models[variant], history, future_dates, variant, feriados_set,
        )
        for variant in ("v5", "v6")
    }
    forecast = []
    for index, target_date in enumerate(future_dates):
        horizon = index + 1
        variant = selected[horizon]
        point = forecasts[variant][index]
        forecast.append({
            "dia": target_date.strftime("%d/%m"),
            "ds": target_date.strftime("%Y-%m-%d"),
            "horizonte": f"D+{horizon}",
            "modelo": variant,
            "mae_usado": round(holdout_mae[horizon], 2),
            "yhat": round(point["yhat"], 1),
            "yhat_lower": round(point["yhat_lower"], 1),
            "yhat_upper": round(point["yhat_upper"], 1),
        })

    metrics = {
        "protocolo": COMMON_HOLDOUT_PROTOCOL,
        "inicio": HOLDOUT_START.strftime("%Y-%m-%d"),
        "fim": HOLDOUT_END.strftime("%Y-%m-%d"),
        "mae_d1": round(holdout_mae[1], 2),
        "mae_d7": round(holdout_mae[7], 2),
        "mae_medio_d1_d7": round(float(np.mean(list(holdout_mae.values()))), 2),
        "por_horizonte": {
            f"D{horizon}": {
                "mae": round(holdout_mae[horizon], 2),
                "n_previsoes": len(holdout_errors[selected[horizon]][horizon]),
                "modelo_selecionado": selected[horizon],
                "selecao_mae_validacao": round(validation_mae[selected[horizon]][horizon], 2),
            }
            for horizon in range(1, 8)
        },
        "nota": "Variante escolhida em Jul–Set; métricas reportadas no holdout posterior Out–Dez.",
    }
    print(f"  [{nome}] MAE comum D+1={metrics['mae_d1']:.2f} | D+7={metrics['mae_d7']:.2f}")
    return final_models["v5"], final_models["v6"], forecast, metrics


# ── Treinamento completo ───────────────────────────────────────────────────────

def train(use_monte_carlo: bool = False) -> dict:
    """Train Prophet with selection before, and evaluation on, the common Q4 holdout."""
    print("Carregando séries...")
    serie_total, serie_p2, serie_p3 = load_series()

    if use_monte_carlo:
        print("Gerando série Monte Carlo (2023-2025)...")
        serie_total, serie_p2, serie_p3 = build_monte_carlo_series(serie_total, serie_p2, serie_p3)

    feriados_df = build_prophet_holidays()
    modelos = {}
    resultados = {"protocolo_validacao": COMMON_HOLDOUT_PROTOCOL}

    for nome, serie in (("total", serie_total), ("p2", serie_p2), ("p3", serie_p3)):
        print(f"\nTreinando {nome.upper()}...")
        model_v5, model_v6, forecast, metrics = train_series(serie, feriados_df, nome)
        modelos[f"prophet_{nome}_v5"] = model_v5
        modelos[f"prophet_{nome}_v6"] = model_v6
        resultados[nome] = {
            "modelo": f"prophet_ensemble_{nome}",
            "gerado_em": date.today().strftime("%Y-%m-%d"),
            "abordagem": (
                "v5/v6 selecionado por horizonte antes do holdout comum"
                + (" (treino Monte Carlo)" if use_monte_carlo else "")
            ),
            "D1": {
                "yhat": forecast[0]["yhat"],
                "lower": forecast[0]["yhat_lower"],
                "upper": forecast[0]["yhat_upper"],
                "modelo_usado": forecast[0]["modelo"],
            },
            "D7": {
                "yhat": forecast[6]["yhat"],
                "lower": forecast[6]["yhat_lower"],
                "upper": forecast[6]["yhat_upper"],
                "modelo_usado": forecast[6]["modelo"],
            },
            "serie_7d": forecast,
            "metricas": metrics,
        }

    return {"resultados": resultados, "modelos": modelos}


# ── Export ────────────────────────────────────────────────────────────────────

def export_json(resultados: dict, path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"JSON exportado: {path}")


def save_models(modelos: dict, prefix: str = "") -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for nome, modelo in modelos.items():
        path = MODELS_DIR / f"{prefix}{nome}.pkl"
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
        save_models(out_mc["modelos"], prefix="mc_")

    print("\nConcluído.")
