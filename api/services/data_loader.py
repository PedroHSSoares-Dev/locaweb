"""
data_loader.py — Carrega JSONs de outputs/ com cache em memória (TTL 60s).
Invalida o cache quando o arquivo é modificado (mtime). Nunca lança exceção.
"""
import json
import os
import time
from pathlib import Path
from typing import Any, Optional

BASE = Path(__file__).parent.parent.parent / "outputs"

_cache: dict[str, dict] = {}
TTL = 60  # segundos


def load_json(filename: str) -> Optional[Any]:
    """
    Carrega um arquivo JSON de outputs/. Retorna None se o arquivo não existir
    ou se ocorrer qualquer erro. Cache de 60s invalidado por mtime.
    """
    filepath = BASE / filename
    if not filepath.exists():
        return None

    try:
        mtime = os.path.getmtime(filepath)
        cached = _cache.get(filename)
        now = time.time()

        if cached and cached["mtime"] == mtime and (now - cached["loaded_at"]) < TTL:
            return cached["data"]

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        _cache[filename] = {"data": data, "mtime": mtime, "loaded_at": now}
        return data
    except Exception:
        return None


_MODEL_FILES = [
    "previsoes_volume.json",         # Prophet original — baseline
    "previsoes_volume_mc.json",      # Prophet Monte Carlo ensemble adaptativo
    "previsoes_lstm.json",           # LSTM v2 — modelo principal
    "risco_ola.json",
    "clusters.json",
    "kpi_atingimento.json",
]


def available_models() -> list[str]:
    """Retorna lista de modelos (sem .json) cujos arquivos existem em outputs/."""
    return [f.replace(".json", "") for f in _MODEL_FILES if (BASE / f).exists()]
