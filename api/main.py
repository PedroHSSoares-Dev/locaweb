from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Union

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import previsoes, risco, clusters, kpi, historico, context
from api.schemas import HealthResponse, NaoDisponivel
from api.services.data_loader import available_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    models = available_models()
    print(f"[startup] Modelos disponíveis em outputs/: {models or ['nenhum']}")
    yield


app = FastAPI(
    title="Predictfy API — Locaweb AIOps",
    version="1.0.0",
    description="""
## Predictfy × Locaweb — FIAP Challenge 2026

API AIOps para previsão de incidentes e monitoramento de OLA em operações ITSM.

### Modelos disponíveis
| Modelo | Status | MAE holdout | Notebook |
|---|---|---|---|
| **LSTM v2** (early stopping) — Volume D+1 a D+7 | ✅ Disponível | 13.15 | `03d_lstm` |
| **Prophet MC** (ensemble adaptativo) — Volume D+1 a D+7 | ✅ Disponível | 23.80 | `03c_prophet_monte_carlo` |
| **Prophet original** (ensemble v5+v6) — Volume D+1 a D+7 | ✅ Disponível | 17.06 (CV) | `03_prophet_volume` |
| **XGBoost** — Risco de violação de OLA | ⏳ Pendente | — | `04_xgboost_ola` |
| **K-Means** — Segmentação de incidentes | ⏳ Pendente | — | `05_kmeans_clusters` |
| **KPI OLA** (SPC — média + 1σ) | ✅ Disponível | — | `07_kpi_projection` |

### Hierarquia de modelos ativos
Os endpoints `/previsoes/*` usam automaticamente o melhor modelo disponível:

**LSTM v2 (MAE=13.15) > Prophet MC Ensemble (MAE=23.80) > Prophet Original (MAE=17.06 CV)**

Use `GET /api/previsoes/modelos` para verificar qual modelo está ativo e quais estão disponíveis.

### Prioridades ITSM — Locaweb
| Prioridade | OLA | Meta anual de violações (2025) |
|---|---|---|
| **P2** (Alta) | ≤ 4h | 63 violações (SPC) |
| **P3** (Média) | ≤ 12h | 280 violações (SPC) |

### Resultado real 2025
| Prioridade | Violações reais | Status |
|---|---|---|
| P2 | 42 | ❌ Acima da meta |
| P3 | 196 | ✅ Dentro da meta |

### Cache e atualização
Os JSONs em `outputs/` são lidos com cache em memória de **60 segundos** (TTL).
O cache é invalidado automaticamente quando o arquivo é modificado (verificação por mtime).
Ao executar um notebook e gerar um novo JSON, o endpoint correspondente começa a retornar
dados reais em até 1 minuto — sem restart da API.

### Fonte dos dados
Dataset real Locaweb — **122.543 incidentes** · jan/2023–dez/2025
    """,
    contact={"name": "Predictfy — Pedro Soares (RM-562283)"},
    license_info={"name": "FIAP Enterprise Challenge 2026"},
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(previsoes.router, prefix="/api")
app.include_router(risco.router,     prefix="/api")
app.include_router(clusters.router,  prefix="/api")
app.include_router(kpi.router,       prefix="/api")
app.include_router(historico.router, prefix="/api")
app.include_router(context.router,   prefix="/api")


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["Infra"],
    summary="Status da API",
)
def health():
    """
    Verifica se a API está no ar e lista os modelos ML disponíveis em `outputs/`.

    **Modelos possíveis:**
    - `previsoes_volume` — Prophet ensemble (notebook 03)
    - `risco_ola` — XGBoost (notebook 04)
    - `clusters` — K-Means (notebook 05)
    - `kpi_atingimento` — Projeção anual (notebook 07)

    Usar para healthcheck do Docker e monitoramento de disponibilidade.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "modelos_disponiveis": available_models(),
    }
