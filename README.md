# Predictfy × Locaweb — AIOps Infra Predict

> Challenge FIAP 2026 · Enterprise Challenge · Turma 2TSCPW  
> Parceiro: **Locaweb** · Tema: **AIOps — Previsão de Incidentes e Tendências Operacionais**

---

## Sobre o projeto

A **Predictfy** idealizou e desenvolveu uma solução de AIOps para transformar dados históricos de incidentes operacionais da Locaweb em inteligência preditiva. O sistema antecipa falhas, identifica tendências, projeta o risco de violação de OLA e apoia a tomada de decisão operacional — tudo em uma dashboard interativa com três visões distintas por perfil de usuário.

---

## Integrantes

| Nome | RM | GitHub |
|---|---|---|
| Pedro | RM-562283 | [@usuario](https://github.com/usuario) |
| — | RM-XXXXX | — |
| — | RM-XXXXX | — |
| — | RM-XXXXX | — |
| — | RM-XXXXX | — |

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

| Camada | Tecnologia |
|---|---|
| Modelos ML | Prophet · XGBoost · scikit-learn · SHAP |
| Dados | pandas · numpy · openpyxl |
| Frontend | React + Vite · Recharts · react-router-dom · lucide-react |
| Chatbot | Gemini 2.5 Flash (LLM 1) · Gemini 2.5 Pro (LLM 2) |
| Deploy | Vercel (frontend) · GitHub Actions (pipeline ML) |
| Entregável FIAP | Power BI |

---

## Estrutura do repositório

```
predictfy-locaweb/
├── data/                   # dataset local — nunca commitado
│   ├── raw/                # CSV original da Locaweb
│   └── processed/          # dados após limpeza e feature engineering
├── notebooks/              # análises KDD — exploração e prova de conceito
│   ├── 01_eda.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_prophet_volume.ipynb
│   ├── 04_xgboost_ola.ipynb
│   ├── 05_kmeans_clusters.ipynb
│   ├── 06_shap_explicabilidade.ipynb
│   └── 07_kpi_projection.ipynb
├── src/                    # código de produção
│   ├── data/               # loader.py · preprocessor.py
│   ├── models/             # prophet_model.py · xgboost_model.py · kmeans_model.py
│   ├── outputs/            # json_generator.py
│   └── pipeline.py         # orquestrador: load → process → train → export
├── models_saved/           # artefatos .pkl — não commitados (regeneráveis)
├── outputs/                # JSONs consumidos pelo frontend — commitados
│   ├── previsoes_volume.json
│   ├── risco_ola.json
│   ├── clusters.json
│   └── kpi_atingimento.json
├── frontend/               # React + Vite
│   └── src/
│       ├── pages/          # GestaoPage · MonitoramentoPage · TecnicoPage · FinancialPage
│       ├── components/     # KpiCards · RiskHeatmap · AlertsList · TimeSeriesChart · DrillDownPanel · FinancialImpact
│       ├── context/        # DashboardContext (horizon global)
│       └── data/           # mockData.js → substituído pelos JSONs reais
├── chatbot/                # lógica de roteamento Gemini Flash → Pro
├── avaliacoes/             # relatórios de avaliação da dashboard
├── docs/                   # documentos do challenge FIAP
├── .github/workflows/      # GitHub Actions: pipeline ML + webhook de alerta
├── .env.example            # variáveis de ambiente necessárias
├── requirements.txt        # dependências Python
└── README.md
```


---

## Como rodar localmente

### Pré-requisitos

- Python 3.11+
- Node.js 20+
- Git

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/predictfy-locaweb.git
cd predictfy-locaweb
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
# editar .env com suas chaves
```

### 3. Instalar dependências Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Adicionar o dataset

Colocar o arquivo CSV fornecido pela Locaweb em:
```
data/raw/incidents.csv
```

### 5. Rodar o pipeline de ML

```bash
python3 src/pipeline.py
# gera os JSONs em outputs/
```

### 6. Rodar o frontend

```bash
cd frontend
npm install
npm run dev
# acesse http://localhost:5173
```

---

## Dashboard — visões disponíveis

| Rota | Público-alvo | Conteúdo |
|---|---|---|
| `/gestao` | Gestores | Saúde geral da infra · R$ em risco · tendência global |
| `/monitoramento` | Geral | Heatmap de risco · alertas · série temporal |
| `/tecnico` | DevOps / SRE | Métricas brutas · drill-down · SHAP values |
| `/financeiro` | Gestores | Exposição financeira · projeção de KPI anual |


---

## Modelos de ML

| Modelo | Objetivo | Output |
|---|---|---|
| **Prophet** | Prever volume de incidentes D+1 e D+7 | Volume por prioridade (P2 e P3) com intervalo de confiança |
| **XGBoost** | Classificar risco de violação de OLA por incidente | Probabilidade 0–100% + SHAP feature importance |
| **K-Means** | Identificar clusters de padrões recorrentes | Perfis de incidentes por produto · hora · grupo |

### KPIs monitorados

| Prioridade | Prazo de resolução (OLA) | Meta 100% (violações/ano) |
|---|---|---|
| P2 — Alta | até 4h | 36 a 39 violações |
| P3 — Média | até 12h | 231 a 263 violações |

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

## Entregáveis FIAP

| Item | Formato | Status |
|---|---|---|
| Apresentação executiva | PowerPoint | Sprint 1 · 12/04/2026 |
| Arquitetura + EDA + protótipos | PowerPoint | Sprint 2 · 17/05/2026 |
| MVP funcional | Link da aplicação | Sprint 3 |
| Apresentação final + pitch | Banca Locaweb + YouTube | Sprint 4 · NEXT 2026 |

---

## Licença

Projeto acadêmico desenvolvido para o **FIAP Enterprise Challenge 2026** em parceria com a **Locaweb**.  
Os dados utilizados são propriedade da Locaweb e não estão incluídos neste repositório.

---

<p align="center">
  Feito com muito amor e carinho pela equipe <strong>Predictfy</strong> · FIAP 2026
</p>
