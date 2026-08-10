from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Must run before router imports because the local LLM provider is configured at import time.
load_dotenv()

from api.routers import previsoes, risco, clusters, kpi, historico, context
from api.routers.chat import router as chat_router
from api.schemas import HealthResponse
from api.services.data_loader import available_models
from api.services.chat_auth import SessionError, verify_session


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
| Modelo | Status | MAE holdout | Origem |
|---|---|---|---|
| **LSTM v2** (early stopping) — Volume D+1 a D+7 | ✅ Disponível | 14.67 | `src/models/lstm_model.py` |
| **Prophet MC** (ensemble adaptativo) — Volume D+1 a D+7 | ✅ Disponível | 23.80 | `src/models/prophet_model.py` |
| **Prophet original** (ensemble v5+v6) — Volume D+1 a D+7 | ✅ Disponível | 12.43 (CV D+1) | `src/models/prophet_model.py` |
| **XGBoost** — Risco de violação de OLA | ✅ Disponível | — | `src/models/xgboost_model.py` |
| **K-Means** — Segmentação de incidentes | ✅ Disponível | — | `src/models/kmeans_model.py` |
| **KPI OLA** — Meta dinâmica mensal | ✅ Disponível | — | `src/models/kpi_projection.py` |

### Fallback de disponibilidade
Os endpoints `/previsoes/*` usam o primeiro artefato disponível nesta ordem operacional:

**LSTM v2 → Prophet MC Ensemble → Prophet Original**

Essa ordem não representa um ranking direto: as métricas só podem ser comparadas quando usam o mesmo protocolo de validação.

Use `GET /api/previsoes/modelos` para verificar qual modelo está ativo e quais estão disponíveis.

### Prioridades ITSM — Locaweb
| Prioridade | OLA | Meta anual de violações (2025) |
|---|---|---|
| **P2** (Alta) | ≤ 4h | 36–39 violações |
| **P3** (Média) | ≤ 12h | 231–263 violações |

### Resultado real 2025
| Prioridade | Violações reais | Status |
|---|---|---|
| P2 | 42 | ❌ Acima da meta |
| P3 | 196 | ✅ Dentro da meta |

### Cache e atualização
Os JSONs em `outputs/` são lidos com cache em memória de **60 segundos** (TTL).
O cache é invalidado automaticamente quando o arquivo é modificado (verificação por mtime).
Para regenerar os modelos execute `python src/pipeline.py` — os endpoints atualizam em até 1 minuto sem restart da API.

### Fonte dos dados
Dataset real Locaweb — **122.543 incidentes** · jan/2023–dez/2025

### Chatbot híbrido
Perguntas factuais usam diretamente os artefatos em `outputs/`; perguntas analíticas usam o provider configurado (`gpt-5.6-luna`/OpenAI ou Gemma/Ollama) com streaming.
Consulte `GET /api/chat/status` para verificar o provider ativo.
    """,
    contact={"name": "Predictfy — Pedro Soares (RM-562283)"},
    license_info={"name": "FIAP Enterprise Challenge 2026"},
    lifespan=lifespan,
)

cors_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def protect_predictfy_api(request: Request, call_next):
    """Require a verified Predictfy session for every non-public data route."""
    path = request.url.path
    public_request = (
        request.method == "OPTIONS"
        or (path == "/api/health" and request.method == "GET")
        or (path == "/api/chat/session" and request.method == "POST")
    )
    if path.startswith("/api") and not public_request:
        authorization = request.headers.get("authorization", "")
        if not authorization.lower().startswith("bearer "):
            return JSONResponse(status_code=401, content={"detail": "Sessão de acesso ausente."})
        try:
            request.state.session = verify_session(authorization.split(" ", 1)[1].strip())
        except SessionError as exc:
            return JSONResponse(status_code=401, content={"detail": str(exc)})
    return await call_next(request)

app.include_router(previsoes.router, prefix="/api")
app.include_router(risco.router,     prefix="/api")
app.include_router(clusters.router,  prefix="/api")
app.include_router(kpi.router,       prefix="/api")
app.include_router(historico.router, prefix="/api")
app.include_router(context.router,   prefix="/api")
app.include_router(chat_router, prefix="/api")


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
    - `previsoes_volume` — Prophet ensemble (`03_prophet_volume.ipynb` — conversão Sprint 3)
    - `risco_ola` — XGBoost (`src/models/xgboost_model.py`)
    - `clusters` — K-Means (`src/models/kmeans_model.py`)
    - `kpi_atingimento` — Projeção anual (`src/models/kpi_projection.py`)

    Usar para healthcheck do Docker e monitoramento de disponibilidade.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "modelos_disponiveis": available_models(),
    }
