"""
LSTM v2 — previsão de volume de incidentes (D+1 a D+7).

Arquitetura: 2 camadas LSTM, hidden=128, dropout=0.3, lookback=30 dias.
Treino: série real de 2025 com early stopping (patience=10).
Holdout: 2025-10-01 a 2025-12-31 (92 dias 100% real).

Saídas:
  outputs/previsoes_lstm.json    — previsão D+1..D+7 (total, P2, P3) + MAE holdout
  models_saved/lstm_total.pt     — pesos do modelo total
  models_saved/lstm_p2.pt        — pesos do modelo P2
  models_saved/lstm_p3.pt        — pesos do modelo P3
  models_saved/lstm_*_scaler.pkl — scalers MinMaxScaler
"""
from __future__ import annotations

import json
import pickle
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler
from torch.utils.data import DataLoader, TensorDataset

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).parents[2]
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "previsoes_lstm.json"
MODELS_DIR = PROJECT_ROOT / "models_saved"

LOOKBACK = 30
HIDDEN_SIZE = 128
NUM_LAYERS = 2
DROPOUT = 0.3
BATCH_SIZE = 32
MAX_EPOCHS = 100
PATIENCE = 10
LR = 0.001
HOLDOUT_START = pd.Timestamp("2025-10-01")
HOLDOUT_END = pd.Timestamp("2025-12-31")
COMMON_HOLDOUT_PROTOCOL = "rolling_origin_2025Q4_D1_D7"

device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")


# ── Arquitetura ───────────────────────────────────────────────────────────────

class LSTMForecaster(nn.Module):
    def __init__(self, hidden_size=HIDDEN_SIZE, num_layers=NUM_LAYERS, dropout=DROPOUT):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=1,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True,
        )
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


# ── Utilitários ───────────────────────────────────────────────────────────────

def _criar_sequencias(serie: np.ndarray, lookback: int) -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for i in range(lookback, len(serie)):
        X.append(serie[i - lookback:i])
        y.append(serie[i])
    return np.array(X), np.array(y)


def _to_tensor(arr: np.ndarray) -> torch.Tensor:
    return torch.FloatTensor(arr).unsqueeze(-1).to(device)


# ── Treino com early stopping ─────────────────────────────────────────────────

def _treinar(serie_scaled: np.ndarray, seed: int = 42) -> LSTMForecaster:
    torch.manual_seed(seed)
    np.random.seed(seed)

    X, y = _criar_sequencias(serie_scaled, LOOKBACK)
    val_size = max(1, int(len(X) * 0.1))

    X_tr = _to_tensor(X[:-val_size])
    y_tr = _to_tensor(y[:-val_size])
    X_vl = _to_tensor(X[-val_size:])
    y_vl = _to_tensor(y[-val_size:])

    loader_tr = DataLoader(TensorDataset(X_tr, y_tr), batch_size=BATCH_SIZE, shuffle=False)
    criterion = nn.MSELoss()

    model = LSTMForecaster().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    best_val = float("inf")
    best_weights = None
    wait = 0

    for epoch in range(MAX_EPOCHS):
        model.train()
        for Xb, yb in loader_tr:
            optimizer.zero_grad()
            loss = criterion(model(Xb), yb)
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            val_loss = criterion(model(X_vl), y_vl).item()

        if val_loss < best_val:
            best_val = val_loss
            best_weights = {k: v.clone() for k, v in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= PATIENCE:
                print(f"    early stopping época {epoch + 1} | best val loss: {best_val:.5f}")
                break

    model.load_state_dict(best_weights)
    return model


# ── Inferência ────────────────────────────────────────────────────────────────

def _predict_rollout(
    model: LSTMForecaster,
    seed_history: list[float],
    n_steps: int,
    real_values: np.ndarray | None = None,
) -> np.ndarray:
    """
    Previsão recursiva. Se real_values fornecido (holdout), usa os valores reais
    como seed do próximo passo (one-step-ahead). Caso contrário, usa predições
    próprias (autoregressive para D+1..D+7).
    """
    model.eval()
    historico = list(seed_history[-LOOKBACK:])
    preds = []

    with torch.no_grad():
        for i in range(n_steps):
            seq = torch.FloatTensor(historico[-LOOKBACK:]).unsqueeze(0).unsqueeze(-1).to(device)
            pred = model(seq).item()
            preds.append(pred)
            next_val = real_values[i] if real_values is not None else pred
            historico.append(next_val)

    return np.array(preds)


# ── Pipeline por série ────────────────────────────────────────────────────────

def _run_serie(
    serie_mc: pd.DataFrame, nome: str, seed: int = 42
) -> tuple[LSTMForecaster, MinMaxScaler, dict, np.ndarray]:
    """Evaluate on Q4 without leakage, then train the deployable full-series model."""
    vals = serie_mc.sort_values("ds")["y"].values.astype(float)
    datas = pd.to_datetime(serie_mc.sort_values("ds")["ds"].values)
    split_idx = int(np.where(datas >= HOLDOUT_START)[0][0])
    holdout_end_idx = int(np.searchsorted(datas, np.datetime64(HOLDOUT_END), side="right"))
    train_values = vals[:split_idx]

    evaluation_scaler = MinMaxScaler(feature_range=(0, 1))
    train_scaled = evaluation_scaler.fit_transform(train_values.reshape(-1, 1)).flatten()
    print(
        f"  [{nome}] avaliação — {len(train_values)} dias treino | "
        f"{holdout_end_idx - split_idx} dias holdout..."
    )
    evaluation_model = _treinar(train_scaled, seed=seed)

    absolute_errors: dict[int, list[float]] = {horizon: [] for horizon in range(1, 8)}
    for origin_idx in range(split_idx - 1, holdout_end_idx - 1):
        horizon = min(7, holdout_end_idx - origin_idx - 1)
        history = vals[:origin_idx + 1]
        history_scaled = evaluation_scaler.transform(history.reshape(-1, 1)).flatten()
        predicted_scaled = _predict_rollout(evaluation_model, list(history_scaled), horizon)
        predicted = np.maximum(
            0,
            evaluation_scaler.inverse_transform(predicted_scaled.reshape(-1, 1)).flatten(),
        )
        actual = vals[origin_idx + 1:origin_idx + 1 + horizon]
        for offset in range(horizon):
            absolute_errors[offset + 1].append(abs(float(actual[offset] - predicted[offset])))

    horizon_metrics = {
        f"D{horizon}": {
            "mae": round(float(np.mean(errors)), 2),
            "n_previsoes": len(errors),
        }
        for horizon, errors in absolute_errors.items()
    }
    metrics = {
        "protocolo": COMMON_HOLDOUT_PROTOCOL,
        "inicio": HOLDOUT_START.strftime("%Y-%m-%d"),
        "fim": HOLDOUT_END.strftime("%Y-%m-%d"),
        "horizontes": horizon_metrics,
        "mae_medio_d1_d7": round(
            float(np.mean([item["mae"] for item in horizon_metrics.values()])), 2,
        ),
    }
    print(
        f"  [{nome}] MAE comum: D+1={horizon_metrics['D1']['mae']:.2f} | "
        f"D+7={horizon_metrics['D7']['mae']:.2f}"
    )

    # O modelo publicado é treinado novamente com toda a série e recebe o
    # histórico real até 31/12 como seed da previsão de janeiro.
    final_scaler = MinMaxScaler(feature_range=(0, 1))
    all_scaled = final_scaler.fit_transform(vals.reshape(-1, 1)).flatten()
    final_model = _treinar(all_scaled, seed=seed)
    predicted_7d_scaled = _predict_rollout(final_model, list(all_scaled), 7)
    predicted_7d = np.maximum(
        0,
        final_scaler.inverse_transform(predicted_7d_scaled.reshape(-1, 1)).flatten(),
    )
    return final_model, final_scaler, metrics, predicted_7d


# ── Carga de dados (Monte Carlo) ──────────────────────────────────────────────
# O LSTM usa MC construído a partir de 2025 APENAS (igual ao nb03b).
# A série completa real é substituída por [sintético 2023 + sintético 2024 + real 2025].

RAW_PATH = PROJECT_ROOT / "data" / "raw" / "LW-DATASET.xlsx"


def _gerar_ano_sintetico_lstm(
    ano: int, vol_2025: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    """Block Bootstrap semanal: amostra semanas de 2025 por mês."""
    vol = vol_2025.copy()
    vol["semana"] = vol["ds"].dt.isocalendar().week.astype(int)
    vol["mes"] = vol["ds"].dt.month

    datas = pd.date_range(f"{ano}-01-01", f"{ano}-12-31", freq="D")
    resultado = []
    i = 0
    while i < len(datas):
        data_alvo = datas[i]
        mes_alvo = data_alvo.month

        semanas_mes = vol[vol["mes"] == mes_alvo]["semana"].unique()
        if len(semanas_mes) == 0:
            semanas_mes = vol["semana"].unique()

        semana_esc = rng.choice(semanas_mes)
        bloco = vol[vol["semana"] == semana_esc]["y"].values

        for j, val in enumerate(bloco):
            if i + j >= len(datas):
                break
            resultado.append({"ds": datas[i + j], "y": max(0.0, float(val) + rng.normal(0, 3))})
        i += len(bloco)

    return pd.DataFrame(resultado).sort_values("ds").reset_index(drop=True)


def load_real_series() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load complete real 2025 daily series; no synthetic holdout information."""
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"{RAW_PATH} não encontrado.")

    raw = pd.read_excel(RAW_PATH)
    kpi = raw[raw["Entrou para KPI?"] == "SIM"].copy()
    kpi["data"] = pd.to_datetime(kpi["Aberto"]).dt.normalize()
    kpi = kpi[kpi["data"].dt.year == 2025]
    calendar = pd.DataFrame({"ds": pd.date_range("2025-01-01", "2025-12-31", freq="D")})

    def _series(mask: pd.Series | None = None) -> pd.DataFrame:
        subset = kpi if mask is None else kpi[mask]
        grouped = subset.groupby("data").size().rename("y").rename_axis("ds").reset_index()
        result = calendar.merge(grouped, on="ds", how="left").fillna({"y": 0.0})
        result["y"] = result["y"].astype(float)
        return result

    return (
        _series(),
        _series(kpi["Prioridade"].eq("2 - Alta")),
        _series(kpi["Prioridade"].eq("3 - Média")),
    )


# ── Entrypoint público ────────────────────────────────────────────────────────

def train() -> dict:
    """Treina LSTM para total, P2 e P3. Retorna resultados e modelos."""
    print("Carregando séries reais de 2025...")
    mc_total, mc_p2, mc_p3 = load_real_series()

    ultima_data = pd.to_datetime(mc_total.sort_values("ds")["ds"].values[-1])
    datas_futuro = pd.date_range(ultima_data + pd.Timedelta(days=1), periods=7, freq="D")

    modelos: dict[str, LSTMForecaster] = {}
    scalers: dict[str, MinMaxScaler] = {}
    holdout_metrics: dict[str, dict] = {}
    previsoes_7d: dict[str, np.ndarray] = {}

    for nome, mc in [("total", mc_total), ("p2", mc_p2), ("p3", mc_p3)]:
        model, scaler, metrics, preds = _run_serie(mc, nome, seed=42)
        modelos[nome] = model
        scalers[nome] = scaler
        holdout_metrics[nome] = metrics
        previsoes_7d[nome] = preds

    prophet_d1 = None
    prophet_path = PROJECT_ROOT / "outputs" / "previsoes_volume.json"
    if prophet_path.exists():
        prophet_data = json.loads(prophet_path.read_text(encoding="utf-8"))
        if prophet_data.get("protocolo_validacao") == COMMON_HOLDOUT_PROTOCOL:
            prophet_d1 = prophet_data.get("total", {}).get("metricas", {}).get("mae_d1")
    lstm_d1 = holdout_metrics["total"]["horizontes"]["D1"]["mae"]
    improvement = (
        round((float(prophet_d1) - lstm_d1) / float(prophet_d1) * 100, 1)
        if isinstance(prophet_d1, (int, float)) and prophet_d1 > 0
        else None
    )

    resultados = {
        "modelo": "lstm_v2_early_stopping",
        "gerado_em": date.today().strftime("%Y-%m-%d"),
        "arquitetura": f"LSTM {NUM_LAYERS} camadas hidden={HIDDEN_SIZE} dropout={DROPOUT} lookback={LOOKBACK}",
        "treino": "2025-01-01 a 2025-09-30 (100% real; avaliação) / até 31-12 no modelo publicado",
        "holdout": "2025-10-01 a 2025-12-31 (92 dias 100% real)",
        "protocolo_validacao": COMMON_HOLDOUT_PROTOCOL,
        "metricas_holdout_comum": holdout_metrics,
        # Compatibilidade: este campo agora representa MAE D+1 no mesmo
        # holdout temporal para todas as séries.
        "mae_holdout_92_dias": {
            key: value["horizontes"]["D1"]["mae"]
            for key, value in holdout_metrics.items()
        },
        "mae_prophet_holdout_comum": prophet_d1,
        "melhora_pct_vs_prophet": improvement,
        "d1": {
            "total": round(float(previsoes_7d["total"][0]), 1),
            "p2": round(float(previsoes_7d["p2"][0]), 1),
            "p3": round(float(previsoes_7d["p3"][0]), 1),
        },
        "d7": {
            "total": round(float(previsoes_7d["total"][6]), 1),
            "p2": round(float(previsoes_7d["p2"][6]), 1),
            "p3": round(float(previsoes_7d["p3"][6]), 1),
        },
        "serie": [
            {
                "ds": d.strftime("%Y-%m-%d"),
                "horizonte": f"D+{i + 1}",
                "total": round(float(previsoes_7d["total"][i]), 1),
                "P2": round(float(previsoes_7d["p2"][i]), 1),
                "P3": round(float(previsoes_7d["p3"][i]), 1),
            }
            for i, d in enumerate(datas_futuro)
        ],
    }

    return {"resultados": resultados, "modelos": modelos, "scalers": scalers}


def export_json(resultados: dict, path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"JSON exportado: {path}")


def save_models(modelos: dict, scalers: dict) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for nome, model in modelos.items():
        torch.save(model.state_dict(), MODELS_DIR / f"lstm_{nome}.pt")
    for nome, scaler in scalers.items():
        with open(MODELS_DIR / f"lstm_{nome}_scaler.pkl", "wb") as f:
            pickle.dump(scaler, f)
    print(f"Modelos salvos em: {MODELS_DIR} ({len(modelos)} LSTM + {len(scalers)} scalers)")


if __name__ == "__main__":
    print(f"Device: {device}")
    print("\n=== Treinando LSTM ===")
    out = train()
    export_json(out["resultados"])
    save_models(out["modelos"], out["scalers"])

    mae = out["resultados"]["mae_holdout_92_dias"]
    print(f"\nMAE D+1 no holdout comum — Total: {mae['total']} | P2: {mae['p2']} | P3: {mae['p3']}")
    print("Concluído.")
