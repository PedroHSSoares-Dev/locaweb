"""Experimento isolado de validação do LSTM de volume.

Este arquivo não importa nem grava artefatos de produção. Ele compara:
1. LSTM univariado com a arquitetura atual, mas protocolo limpo;
2. a mesma base com covariáveis de calendário conhecidas no futuro;
3. baselines ingênuos válidos.

O holdout permanece 2025-10-01..2025-12-31. O scaler e a geração
sintética usam exclusivamente dados anteriores ao holdout.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import MinMaxScaler
from torch.utils.data import DataLoader, TensorDataset


ROOT = Path(__file__).parents[2]
RAW_PATH = ROOT / "data" / "raw" / "LW-DATASET.xlsx"
RESULT_PATH = Path(__file__).with_name("lstm_results.json")

HOLDOUT_START = pd.Timestamp("2025-10-01")
LOOKBACK = 30
HIDDEN_SIZE = 128
NUM_LAYERS = 2
DROPOUT = 0.3
BATCH_SIZE = 32
MAX_EPOCHS = 100
PATIENCE = 10
LR = 0.001
SEED = 42
MODEL_SEEDS = (42, 123, 2026)
DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_real_series() -> dict[str, pd.Series]:
    raw = pd.read_excel(
        RAW_PATH,
        usecols=["Aberto", "Entrou para KPI?", "Prioridade"],
    )
    kpi = raw[raw["Entrou para KPI?"].eq("SIM")].copy()
    kpi["data"] = pd.to_datetime(kpi["Aberto"]).dt.normalize()
    kpi = kpi[kpi["data"].dt.year.eq(2025)]
    calendar = pd.date_range("2025-01-01", "2025-12-31", freq="D")

    def daily(mask: pd.Series | None = None) -> pd.Series:
        subset = kpi if mask is None else kpi[mask]
        return subset.groupby("data").size().reindex(calendar, fill_value=0).astype(float)

    return {
        "total": daily(),
        "p2": daily(kpi["Prioridade"].eq("2 - Alta")),
        "p3": daily(kpi["Prioridade"].eq("3 - Média")),
    }


def make_clean_synthetic_year(
    year: int,
    source: pd.Series,
    seed: int,
) -> pd.Series:
    """Bootstrap de semanas alinhado por dia da semana, sem consultar holdout."""
    rng = np.random.default_rng(seed)
    source_df = source.rename("y").to_frame()
    source_df["week_start"] = source_df.index - pd.to_timedelta(source_df.index.dayofweek, unit="D")
    source_df["month"] = source_df.index.month

    source_weeks: list[dict[str, object]] = []
    for week_start, block in source_df.groupby("week_start"):
        by_dow = block.assign(dow=block.index.dayofweek).set_index("dow")["y"].to_dict()
        if len(by_dow) == 7:
            source_weeks.append(
                {
                    "week_start": week_start,
                    "month": int((week_start + pd.Timedelta(days=3)).month),
                    "values": by_dow,
                }
            )

    target_dates = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    target_df = pd.DataFrame(index=target_dates)
    target_df["week_start"] = target_df.index - pd.to_timedelta(target_df.index.dayofweek, unit="D")
    result = pd.Series(index=target_dates, dtype=float)

    for week_start, target_block in target_df.groupby("week_start"):
        target_month = int((week_start + pd.Timedelta(days=3)).month)
        candidates = [w for w in source_weeks if w["month"] == target_month]
        if not candidates:
            candidates = source_weeks
        sampled = candidates[int(rng.integers(0, len(candidates)))]
        values = sampled["values"]
        for target_date in target_block.index:
            base = float(values[int(target_date.dayofweek)])
            result.loc[target_date] = max(0.0, base + float(rng.normal(0, 3)))

    return result


def build_clean_training(real: pd.Series) -> tuple[pd.Series, pd.Series]:
    real_train = real[real.index < HOLDOUT_START]
    holdout = real[real.index >= HOLDOUT_START]
    synth_2023 = make_clean_synthetic_year(2023, real_train, seed=42)
    synth_2024 = make_clean_synthetic_year(2024, real_train, seed=123)
    train = pd.concat([synth_2023, synth_2024, real_train]).sort_index()
    return train, holdout


def calendar_covariates(dates: pd.DatetimeIndex) -> np.ndarray:
    """Variáveis conhecidas antes da abertura dos incidentes."""
    dow = dates.dayofweek.to_numpy()
    month = dates.month.to_numpy()
    dow_one_hot = np.eye(7, dtype=np.float32)[dow]
    cyclical = np.column_stack(
        [
            np.sin(2 * np.pi * month / 12),
            np.cos(2 * np.pi * month / 12),
            (dow >= 5).astype(float),
        ]
    ).astype(np.float32)
    return np.column_stack([dow_one_hot, cyclical]).astype(np.float32)


class UnivariateLSTM(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=1,
            hidden_size=HIDDEN_SIZE,
            num_layers=NUM_LAYERS,
            dropout=DROPOUT,
            batch_first=True,
        )
        self.fc = nn.Linear(HIDDEN_SIZE, 1)

    def forward(self, history: torch.Tensor, future_cov: torch.Tensor) -> torch.Tensor:
        del future_cov
        out, _ = self.lstm(history)
        return self.fc(out[:, -1, :])


class CalendarLSTM(nn.Module):
    def __init__(self, covariate_size: int = 10) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=1,
            hidden_size=HIDDEN_SIZE,
            num_layers=NUM_LAYERS,
            dropout=DROPOUT,
            batch_first=True,
        )
        self.head = nn.Sequential(
            nn.Linear(HIDDEN_SIZE + covariate_size, 64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 1),
        )

    def forward(self, history: torch.Tensor, future_cov: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(history)
        return self.head(torch.cat([out[:, -1, :], future_cov], dim=1))


def make_sequences(
    scaled: np.ndarray,
    dates: pd.DatetimeIndex,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    histories, covariates, targets = [], [], []
    all_covariates = calendar_covariates(dates)
    for i in range(LOOKBACK, len(scaled)):
        histories.append(scaled[i - LOOKBACK : i])
        covariates.append(all_covariates[i])
        targets.append(scaled[i])
    return (
        np.asarray(histories, dtype=np.float32),
        np.asarray(covariates, dtype=np.float32),
        np.asarray(targets, dtype=np.float32),
    )


@dataclass
class TrainedModel:
    model: nn.Module
    scaler: MinMaxScaler
    epochs: int
    best_val_loss: float


def train_model(train: pd.Series, use_calendar: bool, seed: int) -> TrainedModel:
    set_seed(seed)
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(train.to_numpy().reshape(-1, 1)).ravel()
    histories, covariates, targets = make_sequences(scaled, train.index)
    val_size = max(1, int(len(histories) * 0.1))

    x_train = torch.tensor(histories[:-val_size]).unsqueeze(-1).to(DEVICE)
    c_train = torch.tensor(covariates[:-val_size]).to(DEVICE)
    y_train = torch.tensor(targets[:-val_size]).unsqueeze(-1).to(DEVICE)
    x_val = torch.tensor(histories[-val_size:]).unsqueeze(-1).to(DEVICE)
    c_val = torch.tensor(covariates[-val_size:]).to(DEVICE)
    y_val = torch.tensor(targets[-val_size:]).unsqueeze(-1).to(DEVICE)

    loader = DataLoader(
        TensorDataset(x_train, c_train, y_train),
        batch_size=BATCH_SIZE,
        shuffle=False,
    )
    model: nn.Module = CalendarLSTM() if use_calendar else UnivariateLSTM()
    model = model.to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.MSELoss()
    best_loss = math.inf
    best_state: dict[str, torch.Tensor] | None = None
    wait = 0
    epochs_run = 0

    for epoch in range(MAX_EPOCHS):
        epochs_run = epoch + 1
        model.train()
        for xb, cb, yb in loader:
            optimizer.zero_grad()
            loss = criterion(model(xb, cb), yb)
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            val_loss = float(criterion(model(x_val, c_val), y_val).item())
        if val_loss < best_loss:
            best_loss = val_loss
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= PATIENCE:
                break

    if best_state is None:
        raise RuntimeError("O treinamento não produziu pesos válidos")
    model.load_state_dict(best_state)
    return TrainedModel(model=model, scaler=scaler, epochs=epochs_run, best_val_loss=best_loss)


def predict_one(
    trained: TrainedModel,
    raw_history: list[float],
    target_date: pd.Timestamp,
) -> float:
    scaled_history = trained.scaler.transform(
        np.asarray(raw_history[-LOOKBACK:]).reshape(-1, 1)
    ).ravel()
    history_tensor = (
        torch.tensor(scaled_history, dtype=torch.float32)
        .view(1, LOOKBACK, 1)
        .to(DEVICE)
    )
    cov_tensor = torch.tensor(
        calendar_covariates(pd.DatetimeIndex([target_date])), dtype=torch.float32
    ).to(DEVICE)
    trained.model.eval()
    with torch.no_grad():
        pred_scaled = float(trained.model(history_tensor, cov_tensor).item())
    pred = float(trained.scaler.inverse_transform([[pred_scaled]])[0, 0])
    return max(0.0, pred)


def evaluate_model(
    trained: TrainedModel,
    train: pd.Series,
    holdout: pd.Series,
) -> dict[str, object]:
    history = train.to_list()
    one_step_predictions = []
    for target_date, actual in holdout.items():
        one_step_predictions.append(predict_one(trained, history, target_date))
        history.append(float(actual))

    horizon_actuals: dict[int, list[float]] = {h: [] for h in range(1, 8)}
    horizon_predictions: dict[int, list[float]] = {h: [] for h in range(1, 8)}
    for origin in range(0, len(holdout) - 6):
        recursive_history = train.to_list() + holdout.iloc[:origin].to_list()
        future_dates = holdout.index[origin : origin + 7]
        future_actuals = holdout.iloc[origin : origin + 7].to_numpy()
        for offset, target_date in enumerate(future_dates):
            prediction = predict_one(trained, recursive_history, target_date)
            recursive_history.append(prediction)
            horizon = offset + 1
            horizon_predictions[horizon].append(prediction)
            horizon_actuals[horizon].append(float(future_actuals[offset]))

    by_horizon = {
        f"d{h}": round(
            float(mean_absolute_error(horizon_actuals[h], horizon_predictions[h])), 4
        )
        for h in range(1, 8)
    }
    return {
        "one_step_mae_92d": round(
            float(mean_absolute_error(holdout.to_numpy(), one_step_predictions)), 4
        ),
        "rolling_origin_mae_by_horizon": by_horizon,
        "rolling_origin_mae_mean_d1_d7": round(float(np.mean(list(by_horizon.values()))), 4),
        "epochs": trained.epochs,
        "best_internal_val_loss": round(trained.best_val_loss, 7),
    }


def evaluate_baselines(train: pd.Series, holdout: pd.Series) -> dict[str, object]:
    all_actual = pd.concat([train, holdout])
    train_dow_median = train.groupby(train.index.dayofweek).median().to_dict()
    methods = ["seasonal_naive_lag7", "last_value", "train_dow_median"]
    errors: dict[str, dict[int, list[float]]] = {
        method: {h: [] for h in range(1, 8)} for method in methods
    }
    one_step_actual: list[float] = []
    one_step_preds: dict[str, list[float]] = {method: [] for method in methods}

    full_one_step_actual = holdout.to_numpy(dtype=float)
    full_one_step_preds = {
        "seasonal_naive_lag7": np.asarray(
            [all_actual.loc[d - pd.Timedelta(days=7)] for d in holdout.index],
            dtype=float,
        ),
        "last_value": np.asarray(
            [all_actual.loc[d - pd.Timedelta(days=1)] for d in holdout.index],
            dtype=float,
        ),
        "train_dow_median": np.asarray(
            [train_dow_median[d.dayofweek] for d in holdout.index],
            dtype=float,
        ),
    }

    for origin in range(0, len(holdout) - 6):
        target_dates = holdout.index[origin : origin + 7]
        last_known_date = holdout.index[origin] - pd.Timedelta(days=1)
        last_known = float(all_actual.loc[last_known_date])
        for offset, target_date in enumerate(target_dates):
            actual = float(holdout.loc[target_date])
            horizon = offset + 1
            predictions = {
                "seasonal_naive_lag7": float(all_actual.loc[target_date - pd.Timedelta(days=7)]),
                "last_value": last_known,
                "train_dow_median": float(train_dow_median[target_date.dayofweek]),
            }
            for method, prediction in predictions.items():
                errors[method][horizon].append(abs(actual - prediction))
                if horizon == 1:
                    one_step_preds[method].append(prediction)
            if horizon == 1:
                one_step_actual.append(actual)

    output: dict[str, object] = {}
    for method in methods:
        by_horizon = {
            f"d{h}": round(float(np.mean(errors[method][h])), 4) for h in range(1, 8)
        }
        output[method] = {
            "one_step_mae_92d": round(
                float(mean_absolute_error(full_one_step_actual, full_one_step_preds[method])),
                4,
            ),
            "one_step_mae_comparable_86_origins": round(
                float(mean_absolute_error(one_step_actual, one_step_preds[method])), 4
            ),
            "rolling_origin_mae_by_horizon": by_horizon,
            "rolling_origin_mae_mean_d1_d7": round(
                float(np.mean(list(by_horizon.values()))), 4
            ),
        }
    return output


def main() -> None:
    print(f"Device: {DEVICE}")
    real_series = load_real_series()
    production_published = {
        "total": 14.67,
        "p2": 4.15,
        "p3": 13.32,
        "note": (
            "MAE one-step publicado; scaler ajustado na série completa e anos sintéticos "
            "gerados com todo 2025, inclusive o holdout. Não é comparação limpa."
        ),
    }
    result: dict[str, object] = {
        "protocol": {
            "holdout": "2025-10-01..2025-12-31",
            "training_real_cutoff": "2025-09-30",
            "lookback": LOOKBACK,
            "rolling_origins": 86,
            "device": str(DEVICE),
            "synthetic_rule": "weekly block bootstrap aligned by weekday; source only Jan-Sep/2025",
        },
        "production_published_one_step_mae": production_published,
        "series": {},
    }

    for name, real in real_series.items():
        print(f"\n[{name}] preparando treino limpo...")
        train, holdout = build_clean_training(real)
        series_result: dict[str, object] = {
            "n_train": int(len(train)),
            "n_holdout": int(len(holdout)),
            "holdout_mean": round(float(holdout.mean()), 4),
            "baselines": evaluate_baselines(train, holdout),
            "models": {},
        }
        for variant, use_calendar in [
            ("univariate_clean_mc", False),
            ("calendar_clean_mc", True),
        ]:
            seed_runs: dict[str, object] = {}
            for model_seed in MODEL_SEEDS:
                print(f"[{name}] treinando {variant} (seed={model_seed})...")
                trained = train_model(train, use_calendar=use_calendar, seed=model_seed)
                metrics = evaluate_model(trained, train, holdout)
                seed_runs[str(model_seed)] = metrics
                print(
                    f"[{name}] {variant} seed={model_seed}: "
                    f"one-step={metrics['one_step_mae_92d']:.3f} | "
                    f"D1-D7={metrics['rolling_origin_mae_mean_d1_d7']:.3f}"
                )
                del trained
                if DEVICE.type == "mps":
                    torch.mps.empty_cache()

            one_step_values = np.asarray(
                [run["one_step_mae_92d"] for run in seed_runs.values()], dtype=float
            )
            multihorizon_values = np.asarray(
                [run["rolling_origin_mae_mean_d1_d7"] for run in seed_runs.values()],
                dtype=float,
            )
            series_result["models"][variant] = {
                "primary_seed_42": seed_runs["42"],
                "seed_stability": {
                    "seeds": list(MODEL_SEEDS),
                    "one_step_mae_mean": round(float(one_step_values.mean()), 4),
                    "one_step_mae_std": round(float(one_step_values.std()), 4),
                    "multihorizon_mae_mean": round(float(multihorizon_values.mean()), 4),
                    "multihorizon_mae_std": round(float(multihorizon_values.std()), 4),
                },
                "runs": seed_runs,
            }
        result["series"][name] = series_result

    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResultado gravado somente no experimento: {RESULT_PATH}")


if __name__ == "__main__":
    main()
