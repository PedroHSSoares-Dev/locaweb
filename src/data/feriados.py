"""
Calendário de feriados brasileiro — nacional + SP estado + SP município.
Cobre 2023–2026 (intervalo do dataset + previsões futuras).

Features geradas:
  is_feriado       (0/1)  — dia é feriado?
  tipo_feriado     (0–3)  — 0=normal, 1=nacional, 2=estadual SP, 3=municipal SP
  dias_ate_feriado (0–7)  — dias até o próximo feriado (clipado em 7)
  dias_desde_feriado (0–7) — dias desde o último feriado (clipado em 7)
"""
from __future__ import annotations

from datetime import date, timedelta

import holidays as hol
import numpy as np
import pandas as pd

ANOS = range(2023, 2027)

# ── Tipos de feriado (ordinal) ────────────────────────────────────────────────
TIPO_NORMAL     = 0
TIPO_NACIONAL   = 1
TIPO_ESTADUAL   = 2
TIPO_MUNICIPAL  = 3


def _easter(year: int) -> date:
    """Algoritmo de Butcher para calcular a Páscoa."""
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


def _build_holiday_map(anos: range = ANOS) -> dict[date, int]:
    """Retorna {data: tipo_feriado} para todos os anos solicitados."""
    cal: dict[date, int] = {}

    for year in anos:
        easter = _easter(year)

        # ── Nacionais via biblioteca ──────────────────────────────────────
        for d in hol.country_holidays("BR", years=year):
            if d not in cal:
                cal[d] = TIPO_NACIONAL

        # ── Nacionais sem cobertura na lib ────────────────────────────────
        # Carnaval: segunda e terça antes da Quarta-feira de Cinzas
        cal[easter - timedelta(days=48)] = TIPO_NACIONAL  # segunda
        cal[easter - timedelta(days=47)] = TIPO_NACIONAL  # terça
        # Corpus Christi: 60 dias após a Páscoa
        cal[easter + timedelta(days=60)] = TIPO_NACIONAL

        # ── SP estado ─────────────────────────────────────────────────────
        # 09/07 — Revolução Constitucionalista
        for d in hol.country_holidays("BR", subdiv="SP", years=year):
            cal.setdefault(d, TIPO_ESTADUAL)

        # ── SP município ──────────────────────────────────────────────────
        # 25/01 — Aniversário de São Paulo
        d_aniv = date(year, 1, 25)
        cal.setdefault(d_aniv, TIPO_MUNICIPAL)

    return cal


def build_holiday_features(datas: pd.Series) -> pd.DataFrame:
    """
    Recebe uma Series de timestamps ou datas e retorna DataFrame com 4 colunas:
      is_feriado, tipo_feriado, dias_ate_feriado, dias_desde_feriado
    """
    holiday_map = _build_holiday_map()

    # Trabalhar com datas (sem hora)
    datas_date = pd.to_datetime(datas).dt.date

    # Índice completo de datas únicas no dataset
    dmin = datas_date.min()
    dmax = datas_date.max()
    all_dates = pd.date_range(dmin, dmax, freq="D").date

    # Para cada data no range, marcar tipo
    tipo_series = pd.Series(
        [holiday_map.get(d, TIPO_NORMAL) for d in all_dates],
        index=all_dates,
        dtype=np.int8,
    )
    is_feriado = (tipo_series > 0).astype(np.int8)

    # Dias até próximo feriado (forward-looking)
    feriados_idx = np.where(is_feriado.values)[0]

    dias_ate = np.full(len(all_dates), 7, dtype=np.int8)
    dias_desde = np.full(len(all_dates), 7, dtype=np.int8)

    for i in range(len(all_dates)):
        futuros = feriados_idx[feriados_idx > i]
        passados = feriados_idx[feriados_idx < i]
        if len(futuros):
            dias_ate[i] = min(7, futuros[0] - i)
        if len(passados):
            dias_desde[i] = min(7, i - passados[-1])
        # Se o próprio dia é feriado, ambos = 0
        if is_feriado.values[i]:
            dias_ate[i] = 0
            dias_desde[i] = 0

    df_cal = pd.DataFrame({
        "data_key":           pd.to_datetime(all_dates),
        "is_feriado":         is_feriado.values,
        "tipo_feriado":       tipo_series.values,
        "dias_ate_feriado":   dias_ate,
        "dias_desde_feriado": dias_desde,
    })

    # Mapear para o dataset original por data
    datas_dt = pd.to_datetime(datas).dt.normalize()
    result = datas_dt.rename("data_key").to_frame().merge(df_cal, on="data_key", how="left")

    return result[["is_feriado", "tipo_feriado", "dias_ate_feriado", "dias_desde_feriado"]].reset_index(drop=True)


if __name__ == "__main__":
    # Sanidade: imprimir feriados 2025
    hmap = _build_holiday_map(range(2025, 2026))
    nomes_tipo = {0: "normal", 1: "nacional", 2: "estadual-SP", 3: "municipal-SP"}
    print("Feriados 2025:")
    for d, t in sorted(hmap.items()):
        print(f"  {d.strftime('%d/%m/%Y')}  [{nomes_tipo[t]}]")
