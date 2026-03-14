# Predictfy × Locaweb — Plano de Ação

> FIAP Challenge 2026 · Turma 2TSCP · Parceiro: Locaweb
> Tema: AIOps — Previsão de Incidentes e Tendências Operacionais
> Repositório: github.com/seu-usuario/predictfy-locaweb
> Board Jira: predictfy-locaweb.atlassian.net

---

## Visão geral da solução

Pipeline completo de AIOps: dados históricos de incidentes ITSM → modelos preditivos (Prophet, XGBoost, K-Means) → JSONs estáticos → Dashboard React + Power BI + Chatbot com duas LLMs + GitHub Actions com webhook de alerta.

---

## Dataset

- **Arquivo:** `LW-DATASET.xlsx` (já na pasta `data/raw/` — não commitar no git)
- **Volume:** 122.543 incidentes · 36 meses (jan/2023–dez/2025) · 19 colunas
- **Subset de trabalho:** 25.600 incidentes (apenas P2 e P3 que entraram para KPI)
- **Violações de OLA no período:** 248 → dataset desbalanceado, usar SMOTE no XGBoost
- **Atenção:** produtos (`lhco`, `lsin`...) e categorias (`cat71`...) estão anonimizados

---

## Stack tecnológica

| Camada | Tecnologia |
|---|---|
| Modelos ML | Prophet · XGBoost + SMOTE · K-Means · SHAP |
| Frontend | React + Vite · Recharts · react-router-dom · lucide-react |
| Chatbot | Gemini 2.5 Flash (LLM 1) · Gemini 2.5 Pro (LLM 2) |
| Deploy | Vercel · GitHub Actions |
| Entregável FIAP | Power BI |

---

## Cronograma

| Sprint | Prazo | Entregável |
|---|---|---|
| Sprint 1 — Ideação | **12/04/2026** | PPT: problema, proposta, público-alvo, concorrência |
| Sprint 2 — Arquitetura | **17/05/2026** | PPT: arquitetura, EDA, protótipos, gestão ágil |
| Sprint 3 — MVP | a confirmar | Modelos + Dashboard + Chatbot + GitHub Actions |
| Sprint 4 — Apresentação | NEXT 2026 | Banca Locaweb · vídeo pitch YouTube |

---

## Divisão do time

| Pessoa | Responsabilidade | Pode começar? |
|---|---|---|
| **Pessoa 1** | nb 01 EDA + nb 02 Feature Engineering | ✅ Agora — é o gargalo |
| **Pessoa 2** | nb 03 Prophet | ⏳ Após Pessoa 1 entregar o CSV |
| **Pessoa 3** | nb 04 XGBoost + nb 06 SHAP | ⏳ Após Pessoa 1 entregar o CSV |
| **Pessoa 4** | nb 05 K-Means + nb 07 Projeção KPI | ⏳ Após Pessoa 1 + após P2 e P3 |
| **Pessoa 5** | Dashboard React + GitHub Actions + Vercel | ✅ Agora |
| **Power BI** | Análise descritiva agora, preditiva depois | ✅ Agora |

> ⚠️ **A Pessoa 1 é o gargalo.** Ninguém de ML começa sem o `incidents_features.csv`.

---

## Como configurar o ambiente

```bash
# 1. Clonar o repositório
git clone https://github.com/seu-usuario/predictfy-locaweb.git
cd predictfy-locaweb

# 2. Criar o ambiente conda (Python 3.12 + todas as dependências)
conda env create -f environment.yml

# 3. Ativar
conda activate predictfy-locaweb

# 4. Registrar kernel no Jupyter
python -m ipykernel install --user \
  --name predictfy-locaweb \
  --display-name "Python 3.12 (predictfy-locaweb)"

# 5. Copiar variáveis de ambiente
cp .env.example .env
# editar .env com a GEMINI_API_KEY e WEBHOOK_URL

# 6. Abrir JupyterLab
jupyter lab
```

> Ou rode `bash setup.sh` na raiz do repositório para fazer tudo automaticamente.

---

## Ordem de desbloqueio dos notebooks

```
nb 01 EDA
    ↓
nb 02 Feature Engineering  ← gera incidents_features.csv
    ↓
    ├── nb 03 Prophet ──────────────────┐
    ├── nb 04 XGBoost → nb 06 SHAP     │
    └── nb 05 K-Means                  │
              ↓                        ↓
         nb 07 Projeção KPI ←──────────┘
              ↓
     4 JSONs em outputs/
              ↓
  Dashboard React + Power BI (dados reais)
```

---

## Fase 1 — Fundação (Pessoa 1) · KAN-4

### nb 01 — EDA · KAN-5
**Arquivo:** `notebooks/01_eda.ipynb`

- Distribuição por prioridade (P1–P5)
- Missing values: Produto (77.935 nulos), Categoria (77.721 nulos)
- Range de datas e volume mensal (36 meses)
- `Aberto por`: Monitoramento (104k) vs Manual (18k)
- `Status`: Sem Intervenção (80k) · Encerrado Automaticamente (27k) · Encerrado (15k)
- Sazonalidade: volume por dia da semana × hora
- Top produtos e grupos (Team14 domina com 92k)
- Subset KPI: 25.600 incidentes P2 e P3

**Entregável:** EDA documentada — alimenta o PPT da Sprint 2

---

### nb 02 — Feature Engineering · KAN-6
**Arquivo:** `notebooks/02_feature_engineering.ipynb`
**Depende de:** nb 01 concluído

Features a criar:
- `dia_semana`, `hora`, `mes`, `trimestre`
- `lag_1d`, `lag_7d` — volume anterior
- `rolling_7d`, `rolling_30d` — média móvel
- `target_ola` — duração > limite (P2: 14.400s · P3: 43.200s)
- Filtrar: `Entrou para KPI? == SIM`
- Remover: `Sem Intervenção` e `Incidente Pai` preenchido

**Entregável:** `data/processed/incidents_features.csv` — **desbloqueia todo o time de ML**

---

## Fase 2 — Modelos em paralelo (Pessoas 2, 3, 4) · KAN-7

### nb 03 — Prophet · KAN-8 (Pessoa 2)
**Arquivo:** `notebooks/03_prophet_volume.ipynb`
**Depende de:** nb 02

- 3 modelos: total · P2 · P3
- Previsão D+1 e D+7 com intervalo de confiança
- Feriados brasileiros como regressores (`holidays` lib)
- Avaliar com MAE e RMSE via cross-validation

**Entregável:** `models_saved/prophet_*.pkl` + `outputs/previsoes_volume.json`

---

### nb 04 — XGBoost · KAN-9 (Pessoa 3)
**Arquivo:** `notebooks/04_xgboost_ola.ipynb`
**Depende de:** nb 02

- Classificador binário: `target_ola` (SIM/NAO)
- Features: hora, produto, categoria, grupo, dia_semana, mes, prioridade
- ⚠️ Desbalanceado: 248 SIM vs 25.352 NAO → **usar SMOTE**
- Métricas: **Recall + F1 + ROC-AUC** (não usar acurácia)
- Tuning com GridSearchCV ou Optuna

**Entregável:** `models_saved/xgboost_ola.pkl` + `outputs/risco_ola.json`

---

### nb 05 — K-Means · KAN-10 (Pessoa 4)
**Arquivo:** `notebooks/05_kmeans_clusters.ipynb`
**Depende de:** nb 02

- Subset KPI (25.600 incidentes P2 e P3)
- Features: produto, categoria, grupo, hora, dia_semana, `target_ola`
- StandardScaler + Elbow + Silhouette (k=3 a k=8)
- Visualizar com PCA 2D ou t-SNE

**Entregável:** `models_saved/kmeans_clusters.pkl` + `outputs/clusters.json`

---

## Fase 3 — Explicabilidade + KPI (Pessoas 3 e 4) · KAN-11

### nb 06 — SHAP · KAN-12 (Pessoa 3)
**Arquivo:** `notebooks/06_shap_explicabilidade.ipynb`
**Depende de:** nb 04 (XGBoost treinado)

- `shap.TreeExplainer` no modelo treinado
- Summary plot: top features globalmente
- Force plot: explicar predição individual (DrillDown da dashboard)
- Top 5 features por produto e grupo

**Entregável:** SHAP values no campo `shap_values` do `outputs/risco_ola.json`

---

### nb 07 — Projeção KPI · KAN-13 (Pessoa 4)
**Arquivo:** `notebooks/07_kpi_projection.ipynb`
**Depende de:** nb 03 (Prophet) + nb 04 (XGBoost)

- Violações reais acumuladas no ano corrente
- Prophet: volume P2/P3 nos meses restantes
- XGBoost: taxa de violação esperada
- Metas: P2 = 36–39 violações/ano · P3 = 231–263 violações/ano
- Responder: "Em qual % o ano vai fechar se o padrão continuar?"

**Entregável:** `outputs/kpi_atingimento.json`

---

## Paralelo — Dashboard React · KAN-14 (Pessoa 5)

**Começa agora — independe dos modelos**

**Fase 1 (mockData):**
- `/gestao` — health banner, KPI cards, gráfico por produto, gauge, tendência
- `/monitoramento` — heatmap de risco, alertas, série temporal, drill-down
- `/tecnico` — métricas brutas, SHAP values, tabela detalhada
- `/financeiro` — KPIs financeiros, ComposedChart, tabela por produto

**Fase 2 (após modelos):** substituir mockData pelos 4 JSONs reais + integrar chatbot

---

## Paralelo — Power BI · KAN-15

**Começa agora com `LW-DATASET.xlsx`**

**Fase 1 — descritiva:**
- Página 1: Volume por prioridade, produto, grupo e período
- Página 2: Heatmap de sazonalidade (dia × hora)
- Página 3: Taxa de violação OLA histórica
- Página 4: Tendência mensal 36 meses

**Fase 2 — preditiva (após JSONs):**
- Previsão Prophet D+1 e D+7
- Gauge de atingimento KPI anual
- Risco OLA por incidente (XGBoost)

---

## Paralelo — Infra · KAN-16 (Pessoa 5)

**Começa agora**

- `src/pipeline.py` — orquestrador: load → process → treinar → exportar 4 JSONs
- `.github/workflows/run_models.yml` — roda o pipeline automaticamente (cron diário)
- `.github/workflows/alert_webhook.yml` — webhook Slack/Teams se risco OLA > threshold
- Vercel conectado ao GitHub — deploy automático a cada push

---

## 4 JSONs que conectam ML com o frontend

| Arquivo | Gerado por | Consumido por |
|---|---|---|
| `outputs/previsoes_volume.json` | nb 03 Prophet | React · Power BI · Chatbot |
| `outputs/risco_ola.json` | nb 04 XGBoost + nb 06 SHAP | React · Power BI · Chatbot |
| `outputs/clusters.json` | nb 05 K-Means | React · Power BI · Chatbot |
| `outputs/kpi_atingimento.json` | nb 07 Projeção | React · Power BI · webhook |

---

## Chatbot — definir depois

Após modelos prontos e JSONs gerados:

- **LLM 1:** Gemini 2.5 Flash — roteador de intenção (~$0 no free tier)
- **LLM 2:** Gemini 2.5 Pro — analista com contexto dos dados (~$0.47 total)
- Mesma chave de API Google para as duas
- Lógica em `chatbot/chatbot.py`
- Prompts definidos após a EDA (precisam referenciar produtos e grupos reais)

---

## Pendências

- [ ] **Definir quem é P1, P2, P3, P4, P5 e Power BI antes de começar**
- [ ] Perguntar ao mentor Douglas Gouveia: existe dicionário de mapeamento dos códigos de produto/categoria?
- [ ] Confirmar data da Sprint 3 com o SCRUM Master
- [ ] Fazer push dos commits pendentes no GitHub
- [ ] Conectar repositório ao Vercel

---

*Gerado em 14/03/2026 · Predictfy × Locaweb · FIAP Challenge 2026*
