# Arquitetura — Predictfy × Locaweb

## Visão Geral

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FONTE DE DADOS                                │
│                 data/raw/LW-DATASET.xlsx (gitignored)                   │
│           122.543 incidentes ITSM — jan/2023–dez/2025                   │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         CAMADA DE DADOS                                 │
│                                                                         │
│  src/data/loader.py          src/data/preprocessor.py                  │
│  ─────────────────           ───────────────────────                   │
│  load_raw()                  build_features()                           │
│  load_kpi_subset()           → 30 colunas (29 features + target)        │
│                              → data/processed/incidents_features.parquet│
│                                                                         │
│  src/data/feriados.py                                                   │
│  ──────────────────                                                     │
│  feriados_nacionais_br()     → datas via algoritmo de Páscoa de Butcher │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        CAMADA DE MODELOS                                │
│                                                                         │
│  src/models/                                                            │
│  ├── xgboost_model.py   → outputs/risco_ola.json              ✅        │
│  ├── kmeans_model.py    → outputs/clusters.json               ✅        │
│  ├── kpi_projection.py  → outputs/kpi_atingimento.json        ✅        │
│  ├── prophet_model.py   → outputs/previsoes_volume.json       ✅        │
│  │                        outputs/previsoes_volume_mc.json    ✅        │
│  └── lstm_model.py      → outputs/previsoes_lstm.json         ✅        │
│                                                                         │
│  Orquestrador: src/pipeline.py                                          │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        CAMADA DE OUTPUTS                                │
│                                                                         │
│  outputs/                                                               │
│  ├── risco_ola.json            XGBoost: probabilidade de violação OLA   │
│  ├── clusters.json             K-Means: segmentação de padrões          │
│  ├── kpi_atingimento.json      Projeção: atingimento anual/mensal       │
│  ├── previsoes_volume.json     Prophet: D+1 a D+7 (ensemble v5+v6)      │
│  ├── previsoes_volume_mc.json  Prophet: Monte Carlo ensemble adaptativo  │
│  └── previsoes_lstm.json       LSTM v2 (PyTorch): séries temporais      │
└──────────────────┬────────────────────────────────────┬─────────────────┘
                   │                                    │
                   ▼                                    ▼
┌──────────────────────────────┐   ┌────────────────────────────────────┐
│         API (FastAPI)        │   │          EXPLORAÇÃO / EDA           │
│                              │   │                                    │
│  api/                        │   │  notebooks/                        │
│  ├── main.py                 │   │  ├── 01_eda.ipynb    (permanente)  │
│  ├── Dockerfile              │   │  ├── 02_eda_features.ipynb         │
│  ├── routers/                │   │  ├── 03_prophet_volume.ipynb       │
│  │   ├── previsoes.py        │   │  ├── 03b_monte_carlo_seed.ipynb    │
│  │   ├── risco.py            │   │  ├── 03c_prophet_monte_carlo.ipynb │
│  │   ├── clusters.py         │   │  ├── 03d_lstm.ipynb               │
│  │   ├── kpi.py              │   │  ├── 04_eda_xgboost.ipynb         │
│  │   ├── historico.py        │   │  ├── 05_eda_kmeans.ipynb          │
│  │   └── context.py          │   │  └── 07_eda_kpi.ipynb             │
│  ├── schemas.py              │   └────────────────────────────────────┘
│  └── services/               │
│      └── data_loader.py      │
└──────────────┬───────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        CAMADA DE APRESENTAÇÃO                           │
│                                                                         │
│  frontend/ (React + Vite + Recharts)                                    │
│  ├── /gestao        → Saúde geral · tendência · R$ em risco             │
│  ├── /monitoramento → Heatmap · alertas · série temporal + previsão     │
│  ├── /tecnico       → Clusters K-Means · SHAP values · risco por grupo  │
│  ├── /financeiro    → Exposição financeira · projeção KPI anual         │
│  └── /modelos       → Métricas dos modelos com contexto e explicações   │
│                                                                         │
│  chatbot/ (Gemini Flash + Pro)               ⏳ Sprint 3               │
│  ├── Gemini 2.5 Flash — roteador (~1s)                                  │
│  └── Gemini 2.5 Pro  — analista sênior                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Camadas em Detalhe

### 1. Fonte de Dados

| Campo | Valor |
|---|---|
| Arquivo | `data/raw/LW-DATASET.xlsx` |
| Sistema | ITSM da Locaweb |
| Volume | 122.543 incidentes |
| Período | jan/2023–dez/2025 |
| Status git | Gitignored — nunca commitar |

O subset KPI (`Entrou para KPI? == SIM`) resulta em ~25.600 incidentes (P2 e P3).

### 2. Camada de Dados (`src/data/`)

**`loader.py`** — interface única de carga:
- `load_raw()` — carrega o XLSX completo
- `load_kpi_subset()` — aplica filtro KPI + ordenação temporal

**`preprocessor.py`** — feature engineering canônico:
- Entrada: `LW-DATASET.xlsx`
- Saída: `data/processed/incidents_features.parquet` (25.588 linhas × 30 colunas)
- Remove os primeiros 7 dias (lags indisponíveis)
- Convenção de nomes: lowercase sem espaços (`produto_enc`, `grupo_enc`)

**`feriados.py`** — geração de datas de feriados nacionais BR:
- Calcula feriados fixos e móveis via algoritmo de Páscoa de Butcher
- Gera features `is_feriado`, `tipo_feriado`, `dias_ate_feriado`, `dias_desde_feriado`
- Usado pelo `preprocessor.py` como dependência

### 3. Camada de Modelos (`src/models/`)

| Modelo | Arquivo | Técnica | Problema | Status |
|---|---|---|---|---|
| XGBoost | `xgboost_model.py` | Gradient Boosting | Classificação (violação OLA) | ✅ |
| K-Means | `kmeans_model.py` | Clustering | Segmentação de padrões | ✅ |
| KPI | `kpi_projection.py` | Estatística | Projeção de atingimento anual | ✅ |
| Prophet | `prophet_model.py` | Séries temporais | Previsão D+1/D+7 | ✅ |
| LSTM | `lstm_model.py` | Deep Learning (PyTorch) | Previsão D+1/D+7 (MAE=13.15) | ✅ |

**Orquestrador** (`src/pipeline.py`):
```bash
python src/pipeline.py                   # todos os passos
python src/pipeline.py --step fe         # só feature engineering
python src/pipeline.py --step xgb        # só XGBoost
python src/pipeline.py --step km         # só K-Means
python src/pipeline.py --step kpi        # só projeção KPI
python src/pipeline.py --step prophet    # Prophet ensemble v5+v6 (2025-only)
python src/pipeline.py --step prophet-mc # Prophet Monte Carlo (série 2023-2025)
python src/pipeline.py --step lstm       # LSTM v2 com early stopping
```

### 4. Camada de Outputs (`outputs/`)

JSONs estáticos consumidos pela API e pelo frontend. Gerados pelo pipeline e
commitados no repositório (exceto dados brutos/processados). Todos os 6 arquivos
já estão gerados.

### 5. API (`api/`)

FastAPI servindo os JSONs de outputs com:
- Normalização de formatos (diferentes modelos → resposta uniforme)
- Hierarquia de fallback para previsões: LSTM v2 > Prophet MC > Prophet Original
- Snapshot operacional para o chatbot (`/api/context`)
- `Dockerfile` disponível para containerização

### 6. Frontend (`frontend/`)

React + Vite + Recharts. Consume a API via `http://localhost:8000/api`.
Cinco rotas com perfis de usuário dedicados:

| Rota | Público-alvo | Conteúdo |
|---|---|---|
| `/gestao` | Gestores | KPI cards · tendência mensal · R$ em risco |
| `/monitoramento` | Geral | Heatmap sazonalidade · alertas · série temporal + previsão |
| `/tecnico` | DevOps / SRE | Clusters K-Means · SHAP values · risco por grupo |
| `/financeiro` | Gestores | Exposição financeira · projeção KPI anual |
| `/modelos` | Todos | Métricas dos modelos com contexto e explicações |

### 7. Notebooks (`notebooks/`)

Apenas exploratórios — código de produção vive em `src/`. Todos os notebooks
Prophet e LSTM já foram convertidos para `.py`:

| Notebook | Descrição | Código de produção |
|---|---|---|
| `01_eda.ipynb` | EDA permanente do dataset | — |
| `02_eda_features.ipynb` | Distribuição de features, correlações | — |
| `03_prophet_volume.ipynb` | Exploratório Prophet | `src/models/prophet_model.py` |
| `03b_monte_carlo_seed.ipynb` | Exploratório Monte Carlo seed | `src/models/prophet_model.py` |
| `03c_prophet_monte_carlo.ipynb` | Exploratório Prophet MC ensemble | `src/models/prophet_model.py` |
| `03d_lstm.ipynb` | Exploratório LSTM v2 | `src/models/lstm_model.py` |
| `04_eda_xgboost.ipynb` | PR/ROC curves, SHAP, confusion matrix | — |
| `05_eda_kmeans.ipynb` | Heatmap de clusters, PCA 2D | — |
| `07_eda_kpi.ipynb` | Violações × orçamento mensal | — |

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Python | 3.14.3 (micromamba env `dev`) |
| ML | XGBoost 2.x · scikit-learn · imbalanced-learn · SHAP · Optuna |
| Séries temporais | Prophet 1.3.0 · PyTorch (LSTM v2) |
| Dados | pandas · numpy · pyarrow · openpyxl |
| API | FastAPI · Uvicorn · Pydantic · Docker |
| Frontend | React 18 · Vite · Recharts · react-router-dom · lucide-react |
| Chatbot | Gemini 2.5 Flash (roteador) · Gemini 2.5 Pro (analista) ⏳ Sprint 3 |

---

## Fluxo de Dados em Produção

```
1. python src/pipeline.py          # gera todos os outputs/
2. uvicorn api.main:app            # serve API em :8000
3. npm run dev (frontend/)         # serve dashboard em :5173
```

### Atualização de modelos

1. Atualizar `data/raw/LW-DATASET.xlsx` com novos dados ITSM
2. Executar `python src/pipeline.py` para regenerar todos os JSONs
3. A API carrega os JSONs na primeira requisição (sem restart necessário)

---

## Decisões Arquiteturais

| Decisão | Motivo |
|---|---|
| JSONs estáticos em vez de DB | Pipeline batch, não tempo-real; simplifica deploy |
| Hierarquia de modelos na API | LSTM tem menor MAE, mas pode estar indisponível |
| Notebooks só para EDA | Reprodutibilidade: código de produção deve ser testável em `.py` |
| Odd K only (K-Means) | Evita partições simétricas artificiais em clusters |
| PR-AUC como métrica principal | Dados muito desbalanceados (1:102); acurácia é enganosa |
| Temporal split (não random) | Evita data leakage temporal — modelo não "vê o futuro" |
| Feriados via algoritmo (não CSV) | Reprodutível para qualquer ano sem dependência externa |
| PyTorch em vez de TensorFlow | Controle granular do loop de treino; `.pt` portátil |
