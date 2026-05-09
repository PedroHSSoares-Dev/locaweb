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
│  load_kpi_subset()           → 27 colunas (24 features + target)        │
│                              → data/processed/incidents_features.parquet│
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        CAMADA DE MODELOS                                │
│                                                                         │
│  src/models/                                                            │
│  ├── xgboost_model.py   → outputs/risco_ola.json         ✅             │
│  ├── kmeans_model.py    → outputs/clusters.json           ✅             │
│  ├── kpi_projection.py  → outputs/kpi_atingimento.json   ✅             │
│  ├── prophet_model.py   → outputs/previsoes_volume.json  ⏳ Sprint 3   │
│  └── lstm_model.py      → outputs/previsoes_lstm.json    ⏳ Sprint 3   │
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
│  ├── previsoes_volume.json     Prophet: D+1 a D+7 (original)            │
│  ├── previsoes_volume_mc.json  Prophet: Monte Carlo ensemble            │
│  └── previsoes_lstm.json       LSTM v2: séries temporais                │
└──────────────────┬────────────────────────────────────┬─────────────────┘
                   │                                    │
                   ▼                                    ▼
┌──────────────────────────────┐   ┌────────────────────────────────────┐
│         API (FastAPI)        │   │          EXPLORAÇÃO / EDA           │
│                              │   │                                    │
│  api/                        │   │  notebooks/                        │
│  ├── main.py                 │   │  ├── 01_eda.ipynb    (permanente)  │
│  ├── routers/                │   │  ├── 02_eda_features.ipynb         │
│  │   ├── previsoes.py        │   │  ├── 03_prophet_volume.ipynb       │
│  │   ├── risco.py            │   │  ├── 03b/03c montecarlo            │
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
│  ├── /tecnico       → Métricas brutas · drill-down · SHAP values        │
│  └── /financeiro    → Exposição financeira · projeção KPI anual         │
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
- Saída: `data/processed/incidents_features.parquet` (25.588 linhas × 27 colunas)
- Remove os primeiros 7 dias (lags indisponíveis)
- Convenção de nomes: lowercase sem espaços (`produto_enc`, `grupo_enc`)

### 3. Camada de Modelos (`src/models/`)

| Modelo | Arquivo | Técnica | Problema |
|---|---|---|---|
| XGBoost | `xgboost_model.py` | Gradient Boosting | Classificação (violação OLA) |
| K-Means | `kmeans_model.py` | Clustering | Segmentação de padrões |
| KPI | `kpi_projection.py` | Estatística | Projeção de atingimento anual |
| Prophet | `prophet_model.py` ⏳ | Séries temporais | Previsão D+1/D+7 |
| LSTM | `lstm_model.py` ⏳ | Deep Learning | Previsão D+1/D+7 (MAE=13.15) |

**Orquestrador** (`src/pipeline.py`):
```bash
python src/pipeline.py              # todos os passos
python src/pipeline.py --step fe    # só feature engineering
python src/pipeline.py --step xgb   # só XGBoost
python src/pipeline.py --step km    # só K-Means
python src/pipeline.py --step kpi   # só projeção KPI
```

### 4. Camada de Outputs (`outputs/`)

JSONs estáticos consumidos pela API e pelo frontend. Gerados pelo pipeline e
commitados no repositório (exceto dados brutos/processados).

### 5. API (`api/`)

FastAPI servindo os JSONs de outputs com:
- Normalização de formatos (diferentes modelos → resposta uniforme)
- Hierarquia de fallback para previsões: LSTM v2 > Prophet MC > Prophet Original
- Snapshot operacional para o chatbot (`/api/context`)

### 6. Frontend (`frontend/`)

React + Vite + Recharts. Consume a API via `http://localhost:8000/api`.
Quatro perfis de usuário com rotas dedicadas.

### 7. Notebooks (`notebooks/`)

Apenas exploratórios — nunca contêm código de produção:
- `01_eda.ipynb` — EDA permanente
- `02_eda_features.ipynb` — visualizações de features
- `04_eda_xgboost.ipynb` — PR/ROC curves, SHAP, confusion matrix
- `05_eda_kmeans.ipynb` — heatmap de clusters, PCA 2D
- `07_eda_kpi.ipynb` — violações × orçamento mensal, projeção anual
- `03_*` / `03d_*` — Prophet e LSTM (pendentes conversão para `.py`)

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Python | 3.14 (micromamba env `dev`) |
| ML | XGBoost 2.x · scikit-learn · imbalanced-learn · SHAP |
| Séries temporais | Prophet 1.3.0 · TensorFlow/Keras (LSTM) |
| Dados | pandas · numpy · pyarrow · openpyxl |
| API | FastAPI · Uvicorn · Pydantic |
| Frontend | React 18 · Vite · Recharts · react-router-dom · lucide-react |
| Chatbot | Gemini 2.5 Flash (roteador) · Gemini 2.5 Pro (analista) |

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
