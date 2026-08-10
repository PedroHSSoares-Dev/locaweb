# Predictfy × Locaweb — AIOps Infra Predict

> Challenge FIAP 2026 · Enterprise Challenge · Turma 2TSCPW  
> Parceiro: **Locaweb** · Tema: **AIOps — Previsão de Incidentes e Tendências Operacionais**

---

## Sobre o projeto

A **Predictfy** desenvolveu uma solução de AIOps para transformar dados históricos de incidentes operacionais da Locaweb em inteligência preditiva. O sistema antecipa falhas, identifica tendências, projeta o risco de violação de OLA e apoia a tomada de decisão — tudo em um dashboard interativo com quatro visões por perfil de usuário.

---

## Integrantes

| Nome  | RM        | GitHub |
|-------|-----------|--------|
| Pedro | RM-562283 | [@PedroHSSoares-Dev](https://github.com/PedroHSSoares-Dev) |

---

## Arquitetura da solução

```
Dataset ITSM (XLSX — 122.543 incidentes, jan/2023–dez/2025)
       ↓
src/data/preprocessor.py  →  data/processed/incidents_features.parquet
  └─ limpeza · 31 features · feriados nacionais · target OLA
       ↓
┌──────────────────────────────────────────────────────────┐
│                      src/models/                         │
│  Prophet + LSTM    XGBoost          K-Means   KPI        │
│  volume D+1/D+7    risco OLA/incid  clusters  projeção   │
└──────────────────────────────────────────────────────────┘
       ↓
outputs/  (JSONs estáticos consumidos pelo frontend)
  ├── previsoes_volume.json      Prophet ensemble 2025-only
  ├── previsoes_volume_mc.json   Prophet Monte Carlo 2023-2025
  ├── previsoes_lstm.json        LSTM v2 early stopping
  ├── previsoes_horizonte_prophet.json  Prophet D+1..D+365 para cenários
  ├── risco_ola.json             XGBoost + SHAP
  ├── clusters.json              K-Means K=5
  └── kpi_atingimento.json       Projeção orçamento mensal
       ↓
  ┌────────────────────┬──────────────┐
  │  Dashboard React   │   Power BI   │
  │  (Vercel) ✅       │  (FIAP req.) │
  └────────────────────┴──────────────┘
       ↓
  Chatbot híbrido (respostas exatas + GPT-5.6 Luna; Ollama fallback)  ✅ MVP
```

---

## Stack tecnológica

| Camada | Tecnologia |
|--------|-----------|
| Modelos ML | Prophet · XGBoost · LSTM (PyTorch) · scikit-learn · SHAP · imbalanced-learn · Optuna |
| Dados | pandas · numpy · openpyxl · pyarrow |
| Frontend | React + Vite · Recharts · react-router-dom · lucide-react |
| Chatbot | Respostas determinísticas · GPT-5.6 Luna/OpenAI · Ollama fallback · streaming NDJSON |
| Deploy | Vercel (frontend) · GitHub Actions (pipeline ML) |
| Entregável FIAP | Power BI |

---

## Estrutura do repositório

```
locaweb/
├── data/                              # dataset local — nunca commitado
│   ├── raw/LW-DATASET.xlsx            # arquivo ITSM original da Locaweb
│   └── processed/                     # parquet com 31 features geradas
├── notebooks/                         # exclusivamente exploratórios
│   ├── 01_eda.ipynb                   # EDA permanente
│   ├── 02_eda_features.ipynb          # features, imbalance, correlações
│   ├── 03_prophet_volume.ipynb        # exploratório → migrado para prophet_model.py
│   ├── 03b/03c_monte_carlo*.ipynb     # Monte Carlo → integrado em prophet_model.py
│   ├── 03d_lstm.ipynb                 # exploratório → migrado para lstm_model.py
│   ├── 04_eda_xgboost.ipynb           # PR/ROC curves, SHAP, confusion matrix
│   ├── 05_eda_kmeans.ipynb            # heatmap clusters, PCA 2D
│   └── 07_eda_kpi.ipynb               # violações × orçamento, projeção anual
├── src/
│   ├── data/
│   │   ├── loader.py                  # carga do XLSX e subset KPI
│   │   ├── preprocessor.py            # feature engineering → 31 colunas no parquet
│   │   └── feriados.py                # feriados nacionais BR (Carnaval e Corpus Christi via Páscoa)
│   ├── models/
│   │   ├── prophet_model.py           # ensemble v5+v6, Block Bootstrap Monte Carlo
│   │   ├── lstm_model.py              # LSTM 2 camadas, early stopping, Monte Carlo
│   │   ├── xgboost_model.py           # classificação risco OLA + SHAP
│   │   ├── long_horizon_projection.py # inferência Prophet D+1..D+365 para planejamento
│   │   ├── kmeans_model.py            # segmentação K-Means
│   │   └── kpi_projection.py          # projeção orçamento mensal dinâmico
│   └── pipeline.py                    # orquestrador — 8 etapas
├── api/                               # FastAPI
│   ├── main.py
│   ├── routers/                       # previsoes · risco · clusters · kpi · historico · context · chat
│   └── services/                      # contexto canônico · sessão · providers · respostas exatas
├── frontend/                          # React + Vite
│   └── src/
│       ├── pages/
│       │   ├── GestaoPage.jsx         # visão executiva
│       │   ├── MonitoramentoPage.jsx  # heatmap, alertas, sazonalidade
│       │   ├── TecnicoPage.jsx        # clusters, SHAP, drill-down
│       │   └── ModelosPage.jsx        # métricas dos modelos com contexto
│       └── components/
├── models_saved/                      # artefatos serializados — não commitados
├── outputs/                           # JSONs consumidos pelo dashboard
├── docs/                              # documentação técnica
├── CLAUDE.md                          # contexto completo do projeto para IA
├── requirements.txt
└── environment.yml
```

---

## Como rodar localmente

### Pré-requisitos

- Python 3.11+ (recomendado: micromamba env `dev`)
- Node.js 20+
- Chave da OpenAI com acesso a `gpt-5.6-luna`; Ollama com `gemma4:12b-it-qat` é fallback opcional

### 1. Clonar o repositório

```bash
git clone https://github.com/PedroHSSoares-Dev/locaweb.git
cd locaweb
```

### 2. Instalar dependências Python

```bash
micromamba env create -f environment.yml
micromamba activate dev
```

### 3. Adicionar o dataset

```
data/raw/LW-DATASET.xlsx   ← arquivo fornecido pela Locaweb
```

### 4. Executar o pipeline de ML

```bash
# Pipeline completo (~2 min)
python src/pipeline.py

# Etapas individuais
python src/pipeline.py --step fe          # feature engineering (~8s)
python src/pipeline.py --step xgb         # XGBoost risco OLA (~6s)
python src/pipeline.py --step km          # K-Means clustering (~4s)
python src/pipeline.py --step kpi         # projeção KPI (~2s)
python src/pipeline.py --step prophet     # Prophet 2025-only (~36s)
python src/pipeline.py --step prophet-mc  # Prophet Monte Carlo (~5min)
python src/pipeline.py --step lstm        # LSTM v2 (~25s)
python src/pipeline.py --step horizon     # Prophet D+1..D+365 exploratório (~2s)
```

Todos os JSONs são gerados em `outputs/` e os modelos serializados em `models_saved/`.

### 5. Iniciar a API

```bash
cp .env.example .env
# Preencha OPENAI_API_KEY no .env. Para fallback offline:
# ollama pull gemma4:12b-it-qat
uvicorn api.main:app --reload
# API em http://localhost:8000
# Docs em http://localhost:8000/docs
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

| Rota | Público-alvo | Conteúdo |
|------|-------------|---------|
| `/gestao` | Gestores | Saúde da infra · R$ em risco · tendência global · previsão LSTM |
| `/monitoramento` | Geral | Heatmap Volume/Anomalia · alertas operacionais · sazonalidade |
| `/tecnico` | DevOps / SRE | Clusters K-Means · perfis de risco · SHAP feature importance |
| `/modelos` | Todos | Métricas dos modelos com contexto e explicações |

---

## Modelos de ML

| Modelo | Objetivo | Métricas de referência |
|--------|----------|----------------------|
| **Prophet** (ensemble v5+v6) | Volume de incidentes D+1 a D+7 | MAE D+1: Total=12.4, P2=7.7, P3=10.0 |
| **LSTM v2** (early stopping) | Volume de incidentes D+1 a D+7 | MAE holdout 92 dias: Total=14.7, P2=4.2, P3=13.3 |
| **XGBoost** (Optuna 80 trials) | Risco de violação de OLA por incidente | PR-AUC=0.070, Recall=13.8%, Precision=29.6%, F1=18.8% |
| **K-Means** (K=5) | Segmentação de padrões de incidentes | Silhouette=0.199, CH=3890, DB=1.504 |

### Regras anti-leakage

As features a seguir nunca podem entrar nos modelos — são conhecidas apenas após a resolução:

`Duração` · `Resolvido` · `Encerrado` · `Código de fechamento` · `Solução`

### KPIs monitorados

| Prioridade | OLA | Meta (violações/ano) | 2025 real | Status |
|-----------|-----|---------------------|-----------|--------|
| P2 — Alta | 4h | 36–39 | 42 | ❌ Fora da meta |
| P3 — Média | 12h | 231–263 | 196 | ✅ Dentro da meta |

---

## Chatbot — arquitetura híbrida

✅ MVP funcional, cloud-agnostic e com custo concentrado apenas nas perguntas analíticas.

- **Camada determinística restrita:** somente comandos factuais explícitos e quick actions, como `Previsão amanhã`, `Status das metas` e `Cluster mais crítico`, leem os JSONs sem LLM.
- **Camada analítica:** perguntas de causa, comparação ou recomendação usam `gpt-5.6-luna` pela Responses API. `CHAT_LLM_PROVIDER=ollama` ativa o Gemma local sem alterar o frontend.
- **Roteamento agent-first:** toda pergunta natural, estratégica, futura, comparativa ou ambígua vai ao agente; palavras isoladas como “meta” ou “violação” não reduzem a resposta a um cartão factual.
- **Agente com ferramentas:** o Luna escolhe consultas read-only para LSTM, Prophet, XGBoost/SHAP, K-Means, metas e regras operacionais. Perguntas amplas podem combinar várias fontes em paralelo.
- **Cenários de longo prazo:** D+8..D+365 usa inferência offline dos Prophet já treinados. A ferramenta de cota combina volume, taxa real histórica e meta anual em cenários baixo/base/alto; o resultado é exploratório fora de D+7.
- **Planejamento periódico:** análises mensais ou trimestrais retornam volume do período e acumulado, consumo de cota e score executivo auditável de 0–10; o score combina cenário-base, estresse e ritmo proporcional e não é probabilidade.
- **Contexto canônico:** `/api/context` é a única fonte de dados injetada no modelo. O prompt proíbe inventar números e diferencia correlação, hipótese e causalidade.
- **Análise transparente:** o painel `Pensando...` mostra um resumo verificável das evidências, checagens e limitações — nunca o raciocínio interno bruto — e fecha quando a resposta começa.
- **Tempo de execução:** cada resposta registra `Worked for X min Y sec` a partir do tempo medido no backend.
- **Cache seguro:** respostas analíticas usam cache versionado por dados, prompt e modelo, single-flight e reutilização semântica local conservadora; prioridades, números e negações diferentes não compartilham resposta.
- **Conversas persistentes:** o arquivo interno gera títulos automáticos, busca título/conteúdo, permite renomear, fixar e excluir e restaura todo o histórico por identidade.
- **Resumo + memória curta:** conversas longas ganham um resumo extrativo para o contexto da LLM, mantendo as mensagens completas no arquivo; as últimas interações continuam em memória rápida.
- **Contexto do dashboard:** cada conversa registra rota e filtros selecionados. Ao reabri-la em outro contexto, a interface permite manter o original ou adotar o atual.
- **Modos de análise:** `RÁPIDO` reduz latência/custo; `PROFUNDO` amplia esforço, orçamento de saída e rodadas de ferramentas.
- **Auditabilidade:** fontes read-only, uso de tokens, origem do cache e `response_id` chegam como metadados estruturados, separados do texto da LLM.
- **Qualidade operacional:** feedback positivo/negativo e métricas agregadas não armazenam prompts na telemetria.
- **Escala:** `CHAT_REDIS_URL` habilita Redis ou Valkey para cache, memória, feedback e rate limit compartilhados; sem ele existe fallback local sem dependência de cloud.
- **Acesso:** o Microsoft Entra ID valida a identidade e o backend troca o access token por uma sessão HMAC temporária, revalidada contra a allowlist em cada requisição.
- **Custo sob controle:** somente consultas analíticas usam a OpenAI; perguntas factuais continuam locais. O modelo e o esforço são configuráveis por ambiente.
- **Fallback offline:** com Ollama ativo, a sessão inicia e pré-carrega o Gemma sob demanda; o logout descarrega o modelo e encerra somente o servidor iniciado pela API.
- **Persistência cloud-agnostic:** SQLite funciona sem configuração local; `CHAT_DATABASE_URL` troca o repositório por PostgreSQL em produção sem alterar o frontend.
- **Endpoints:** além de sessão/status/chat, há CRUD em `/api/chat/conversations`, feedback, reset de memória curta e métricas.
- **Autenticação:** Microsoft Entra ID + allowlist de e-mail, sem roles nesta fase. Consulte [`docs/autenticacao_entra.md`](docs/autenticacao_entra.md).

O frontend espera `VITE_API_URL=http://localhost:8000/api`. A chave da OpenAI permanece somente no backend. Se a API for executada no Docker com fallback Ollama no macOS, `host.docker.internal:11434` já está configurado.

Em produção, configure `CORS_ALLOWED_ORIGINS` na API com a origem exata do frontend, por exemplo `https://predictfy-locaweb.vercel.app`.
O arquivo `render.yaml` descreve a API e o workflow `.github/workflows/ci.yml` valida backend e frontend antes do auto-deploy no Render.

---

## Prazos FIAP

| Sprint | Entrega | Data |
|--------|---------|------|
| Sprint 1 | Apresentação executiva | 12/04/2026 |
| Sprint 2 | Arquitetura + EDA + protótipos | 17/05/2026 |
| Sprint 3 | MVP funcional (link da aplicação) | A definir |
| Sprint 4 | Apresentação final + pitch (NEXT 2026) | A definir |

---

## Licença

Projeto acadêmico desenvolvido para o **FIAP Enterprise Challenge 2026** em parceria com a **Locaweb**.  
Os dados utilizados são propriedade da Locaweb e não estão incluídos neste repositório.

---

<p align="center">Feito com dedicação pela equipe <strong>Predictfy</strong> · FIAP 2026</p>
