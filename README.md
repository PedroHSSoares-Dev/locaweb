# Predictfy × Locaweb — AIOps Infra Predict

> Challenge FIAP 2026 · Enterprise Challenge · Turma 2TSCPW  
> Parceiro: **Locaweb** · Tema: **AIOps — Previsão de Incidentes e Tendências Operacionais**

---

## Sobre o projeto

A **Predictfy** idealizou e desenvolveu uma solução de AIOps para transformar dados históricos de incidentes operacionais da Locaweb em inteligência preditiva. O sistema antecipa falhas, identifica tendências, projeta o risco de violação de OLA e apoia a tomada de decisão operacional — tudo em uma dashboard interativa com três visões distintas por perfil de usuário.

---

## Integrantes

| Nome  | RM        | GitHub                                                     |
| ----- | --------- | ---------------------------------------------------------- |
| Pedro | RM-562283 | [@PedroHSSoares-Dev](https://github.com/PedroHSSoares-Dev) |
| —     | RM-XXXXX  | —                                                          |
| —     | RM-XXXXX  | —                                                          |
| —     | RM-XXXXX  | —                                                          |
| —     | RM-XXXXX  | —                                                          |

---

## Arquitetura da solução

```
Dataset ITSM (CSV)
       ↓
Preparação (Python / pandas)
  └─ limpeza · feature engineering · targets OLA
       ↓
┌─────────────────────────────────────┐
│           Modelos de ML             │
│  Prophet   XGBoost     K-Means      │
│  D+1/D+7   risco OLA   clusters     │
└─────────────────────────────────────┘
       ↓
JSONs estáticos (outputs/)
       ↓
  ┌────────────┬──────────────┐
  │ Dashboard  │   Power BI   │
  │   React    │  (FIAP req.) │
  └────────────┴──────────────┘
       ↓
  Chatbot (Gemini Flash + Pro)
  GitHub Actions + Webhook de alerta
```


---

## Stack tecnológica

| Camada          | Tecnologia                                                |
| --------------- | --------------------------------------------------------- |
| Modelos ML      | Prophet · XGBoost · scikit-learn · SHAP                   |
| Dados           | pandas · numpy · openpyxl                                 |
| Frontend        | React + Vite · Recharts · react-router-dom · lucide-react |
| Chatbot         | Gemini 2.5 Flash (LLM 1) · Gemini 2.5 Pro (LLM 2)         |
| Deploy          | Vercel (frontend) · GitHub Actions (pipeline ML)          |
| Entregável FIAP | Power BI                                                  |

---

## Estrutura do repositório

```
locaweb/
├── data/                        # dataset local — nunca commitado
│   ├── raw/LW-DATASET.xlsx      # arquivo ITSM original da Locaweb
│   └── processed/               # parquet com features geradas
├── notebooks/                   # APENAS exploratórios — sem código de produção
│   ├── 01_eda.ipynb             # EDA permanente
│   ├── 02_eda_features.ipynb    # distribuição de features, imbalance, correlações
│   ├── 03_prophet_volume.ipynb  # Prophet séries temporais (pendente .py)
│   ├── 03b/03c_monte_carlo      # variantes Monte Carlo (pendente .py)
│   ├── 03d_lstm.ipynb           # LSTM v2 early stopping (pendente .py)
│   ├── 04_eda_xgboost.ipynb     # PR/ROC curves, SHAP, confusion matrix
│   ├── 05_eda_kmeans.ipynb      # heatmap clusters, PCA 2D
│   └── 07_eda_kpi.ipynb         # violações × orçamento, projeção anual
├── src/                         # código de produção Python
│   ├── data/
│   │   ├── loader.py            # carga do XLSX e subset KPI
│   │   └── preprocessor.py     # feature engineering → parquet (27 colunas)
│   ├── models/
│   │   ├── xgboost_model.py    # classificação risco OLA ✅
│   │   ├── kmeans_model.py     # segmentação K-Means ✅
│   │   ├── kpi_projection.py   # projeção atingimento anual ✅
│   │   ├── prophet_model.py    # séries temporais ⏳ Sprint 3
│   │   └── lstm_model.py       # LSTM ⏳ Sprint 3
│   └── pipeline.py             # orquestrador principal
├── api/                         # FastAPI
│   ├── main.py
│   ├── routers/                 # previsoes · risco · clusters · kpi · historico · context
│   ├── schemas.py
│   └── services/data_loader.py
├── frontend/                    # React + Vite + Recharts
│   └── src/
│       ├── pages/               # GestaoPage · MonitoramentoPage · TecnicoPage · FinancialPage
│       └── components/
├── models_saved/                # artefatos .pkl — não commitados (regeneráveis)
├── outputs/                     # JSONs consumidos pelo frontend
│   ├── risco_ola.json
│   ├── clusters.json
│   ├── kpi_atingimento.json
│   ├── previsoes_volume.json
│   ├── previsoes_volume_mc.json
│   └── previsoes_lstm.json
├── docs/                        # documentação técnica
│   ├── arquitetura.md
│   ├── dataset.md
│   ├── modelos.md
│   └── api.md
├── chatbot/                     # Gemini Flash + Pro ⏳ Sprint 3
├── requirements.txt
├── environment.yml
├── CLAUDE.md
└── README.md
```


---

## Como rodar localmente

### Pré-requisitos

- Python 3.11+ (recomendado: micromamba env `dev`)
- Node.js 20+
- Git

### 1. Clonar o repositório

```bash
git clone https://github.com/PedroHSSoares-Dev/locaweb.git
cd locaweb
```

### 2. Instalar dependências Python

```bash
micromamba install -c conda-forge --file requirements.txt
# ou com pip:
pip install -r requirements.txt
```

### 3. Adicionar o dataset

Colocar o arquivo fornecido pela Locaweb em:
```
data/raw/LW-DATASET.xlsx
```

### 4. Executar o pipeline de ML

```bash
# Pipeline completo (feature engineering + todos os modelos)
python src/pipeline.py

# Passos individuais
python src/pipeline.py --step fe    # só feature engineering
python src/pipeline.py --step xgb   # só XGBoost
python src/pipeline.py --step km    # só K-Means
python src/pipeline.py --step kpi   # só projeção KPI

# Gera em outputs/:
#   risco_ola.json · clusters.json · kpi_atingimento.json
```

### 5. Iniciar a API

```bash
uvicorn api.main:app --reload
# API disponível em http://localhost:8000
# Docs interativos em http://localhost:8000/docs
```

### 6. Iniciar o frontend

```bash
cd frontend
npm install
npm run dev
# Dashboard em http://localhost:5173
```

---

## Dashboard — visões disponíveis

| Rota             | Público-alvo | Conteúdo                                              |
| ---------------- | ------------ | ----------------------------------------------------- |
| `/gestao`        | Gestores     | Saúde geral da infra · R$ em risco · tendência global |
| `/monitoramento` | Geral        | Heatmap de risco · alertas · série temporal           |
| `/tecnico`       | DevOps / SRE | Métricas brutas · drill-down · SHAP values            |
| `/financeiro`    | Gestores     | Exposição financeira · projeção de KPI anual          |


---

## Modelos de ML

| Modelo      | Objetivo                                           | Output                                                     |
| ----------- | -------------------------------------------------- | ---------------------------------------------------------- |
| **Prophet** | Prever volume de incidentes D+1 e D+7              | Volume por prioridade (P2 e P3) com intervalo de confiança |
| **XGBoost** | Classificar risco de violação de OLA por incidente | Probabilidade 0–100% + SHAP feature importance             |
| **K-Means** | Identificar clusters de padrões recorrentes        | Perfis de incidentes por produto · hora · grupo            |

### KPIs monitorados

| Prioridade | Prazo de resolução (OLA) | Meta 100% (violações/ano) |
| ---------- | ------------------------ | ------------------------- |
| P2 — Alta  | até 4h                   | 36 a 39 violações         |
| P3 — Média | até 12h                  | 231 a 263 violações       |

---

## Chatbot — arquitetura de roteamento

O chatbot integrado à dashboard usa duas LLMs em cascata:

- **LLM 1 — Gemini 2.5 Flash**: roteador de intenção. Responde perguntas simples diretamente (~1s). Escala para a LLM 2 quando a consulta exige análise profunda.
- **LLM 2 — Gemini 2.5 Pro**: analista sênior. Recebe contexto expandido com dados históricos e outputs dos modelos. Retorna análise para a LLM 1 formatar e entregar ao usuário.

> Prompts de sistema serão definidos após a EDA e o treinamento dos modelos.

---

## Automação

- **GitHub Actions** executa `pipeline.py` periodicamente, atualiza os JSONs e faz deploy automático via Vercel
- **Webhook de alerta** dispara notificação quando o risco de OLA ultrapassa o threshold configurado em `.env`

---

## Licença

Projeto acadêmico desenvolvido para o **FIAP Enterprise Challenge 2026** em parceria com a **Locaweb**.  
Os dados utilizados são propriedade da Locaweb e não estão incluídos neste repositório.

---

<p align="center">
  Feito com muito amor e carinho pela equipe <strong>Predictfy</strong> · FIAP 2026
</p>
