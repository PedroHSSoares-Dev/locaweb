# Predictfy × Locaweb — AIOps Infra Predict

> Challenge FIAP 2026 · Enterprise Challenge · Turma 2TSCPW  
> Parceiro: **Locaweb** · Tema: **AIOps — Previsão de Incidentes e Tendências Operacionais**

---

## Sobre o projeto

A **Predictfy** é uma plataforma de AIOps que transforma o histórico de incidentes da Locaweb em apoio operacional e executivo. A solução prevê volume, prioriza risco de violação de OLA, identifica perfis operacionais, acompanha metas, organiza uma fila de investigação com feedback humano e disponibiliza um agente de IA capaz de consultar os artefatos dos modelos. A aplicação possui cinco áreas operacionais, administração de acessos e uma arquitetura preparada para substituir provedores de infraestrutura sem reescrever o produto.

### Aplicação publicada

- **Dashboard:** [predictfy.vercel.app](https://predictfy.vercel.app/gestao)
- **API:** [predictfy-api.onrender.com](https://predictfy-api.onrender.com/api/health)
- **Documentação OpenAPI:** [predictfy-api.onrender.com/docs](https://predictfy-api.onrender.com/docs)

### Estado atual

- MVP full stack publicado com frontend na Vercel, API no Render e PostgreSQL no Supabase.
- Microsoft Entra ID para identidade e diretório próprio com papéis `member` e `admin`.
- Model registry com um modelo ativo e um candidato shadow para volume e risco OLA.
- Fila operacional com revisão humana, feedback observado e trilha de auditoria.
- Chatbot com ferramentas read-only, persistência de conversas, cache, guardrails e medição de tokens por usuário.
- CI/CD com contratos de artefatos ML, testes de API/segurança, lint, build e teste responsivo.
- Data de referência operacional: **31/12/2025**, último dia observado no dataset.

---

## Integrantes

| Nome | RM | GitHub |
|------|----|--------|
| Elton Vinicios Almeida de Oliveira | RM-562187 | — |
| Emerson dos Santos Silva | RM-562033 | — |
| Kelvin Douglas Ribeiro Rabelo | RM-561538 | — |
| Pedro Henrique Simão Soares | RM-562283 | [@PedroHSSoares-Dev](https://github.com/PedroHSSoares-Dev) |
| Vitor Lucas Mattos de Brito Mariano | RM-562116 | — |

---

## Arquitetura da solução

```
Dataset ITSM (XLSX — 122.543 incidentes, jan/2023–dez/2025)
       ↓
src/data/preprocessor.py  →  data/processed/incidents_features.parquet
  └─ limpeza · 30 features · data de auditoria · target OLA
       ↓
┌──────────────────────────────────────────────────────────────────┐
│                      Modelos e governança                        │
│  Baseline/LSTM/Prophet   XGBoost/SVM   K-Means   KPI             │
│  volume e cenários       risco OLA     perfis    metas anuais    │
│  modelo ativo + candidatos shadow + protocolos de promoção       │
└──────────────────────────────────────────────────────────────────┘
       ↓
outputs/  (artefatos JSON versionados e validados pelo CI)
  ├── previsoes_volume.json      Prophet ensemble 2025-only
  ├── previsoes_volume_mc.json   Prophet Monte Carlo 2023-2025
  ├── previsoes_lstm.json        LSTM v2 early stopping
  ├── previsoes_baseline.json    baseline sazonal semanal ativo
  ├── previsoes_horizonte_prophet.json  Prophet D+1..D+365 para cenários
  ├── risco_ola.json             XGBoost + SHAP
  ├── clusters.json              K-Means K=5
  ├── kpi_atingimento.json       Projeção orçamento mensal
  ├── comparacao_modelos.json    Holdout comum LSTM × Prophet
  ├── segmentos_ola.json         Agregados de grupo/produto com supressão
  └── model_registry.json        Fonte canônica de status e governança
       ↓
FastAPI / Render
  ├── endpoints de dados, modelos, contexto, operações e administração
  ├── respostas determinísticas + agente GPT-5.6 Luna com ferramentas
  ├── autenticação Microsoft Entra ID e autorização por papel
  ├── PostgreSQL/Supabase: usuários, conversas, tokens, fila e auditoria
  └── cache, rate limit, guardrails e provedores OpenAI/Ollama
       ↓
React + Vite / Vercel
  └── Gestão · Monitoramento · Fila Operacional · Técnico · Modelos · Admin
```

---

## Stack tecnológica

| Camada | Tecnologia |
|--------|-----------|
| Modelos ML | Prophet · XGBoost · LSTM (PyTorch) · scikit-learn · SHAP · imbalanced-learn · Optuna |
| Dados | pandas · numpy · openpyxl · pyarrow |
| Frontend | React + Vite · Recharts · react-router-dom · lucide-react |
| API | FastAPI · Uvicorn · SQLAlchemy · Pydantic |
| Persistência | PostgreSQL/Supabase em produção · SQLite local · Redis/Valkey opcional |
| Identidade e acesso | Microsoft Entra ID · diretório RBAC próprio (`member`/`admin`) · sessões HMAC |
| Chatbot | Respostas determinísticas · GPT-5.6 Luna/OpenAI · Ollama fallback · streaming NDJSON |
| Deploy | Vercel (frontend) · Render (API) · GitHub Actions (CI/CD e contratos ML) |
| Entregável acadêmico | Dashboard web funcional · Power BI planejado conforme requisito FIAP |

---

## Estrutura do repositório

```
locaweb/
├── data/                              # dataset local — nunca commitado
│   ├── raw/LW-DATASET.xlsx            # arquivo ITSM original da Locaweb
│   └── processed/                     # parquet com features, data de auditoria e target
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
│   │   ├── preprocessor.py            # 30 features → 32 colunas com data e target
│   │   └── feriados.py                # feriados nacionais BR (Carnaval e Corpus Christi via Páscoa)
│   ├── models/
│   │   ├── seasonal_baseline.py       # baseline ativo de volume D+1..D+7
│   │   ├── prophet_model.py           # ensemble v5+v6, Block Bootstrap Monte Carlo
│   │   ├── lstm_model.py              # LSTM 2 camadas, early stopping, série real
│   │   ├── xgboost_model.py           # classificação risco OLA + SHAP
│   │   ├── xgboost_specialists.py      # experimento isolado generalista/P2/P3
│   │   ├── long_horizon_projection.py # inferência Prophet D+1..D+365 para planejamento
│   │   ├── kmeans_model.py            # segmentação K-Means
│   │   ├── kpi_projection.py          # projeção orçamento mensal dinâmico
│   │   ├── model_comparison.py        # comparação temporal no mesmo holdout
│   │   └── operational_aggregates.py  # grupos/produtos com limiar de privacidade
│   ├── validation/
│   │   ├── artifacts.py               # contratos dos artefatos JSON
│   │   └── release_preflight.py       # gate offline antes do deploy
│   └── pipeline.py                    # orquestrador — 11 etapas + trilho experimental
├── api/                               # FastAPI
│   ├── main.py
│   ├── routers/                       # dados · modelos · operações · chat · administração
│   └── services/                      # Entra/RBAC · stores · cache · guardrails · ferramentas · providers
├── frontend/                          # React + Vite
│   └── src/
│       ├── pages/
│       │   ├── GestaoPage.jsx         # visão executiva
│       │   ├── MonitoramentoPage.jsx  # heatmap, alertas, sazonalidade
│       │   ├── OperationsPage.jsx     # fila shadow e feedback operacional
│       │   ├── TecnicoPage.jsx        # clusters, SHAP, drill-down
│       │   ├── ModelosPage.jsx        # métricas e governança dos modelos
│       │   └── AdminPage.jsx          # usuários, permissões, consumo e preflight
│       └── components/
├── models_saved/                      # artefatos serializados — não commitados
├── outputs/                           # JSONs servidos pela API ao dashboard
├── docs/                              # documentação técnica
├── tests/                             # testes de API, segurança, stores e governança
├── .github/workflows/ci.yml           # gates de artefatos, API e frontend
├── render.yaml                        # infraestrutura declarativa da API
├── CLAUDE.md                          # contexto completo do projeto para IA
├── requirements.txt
└── environment.yml
```

---

## Como rodar localmente

### Pré-requisitos

- Python 3.11
- Node.js 22.x
- Conda/Micromamba ou outro gerenciador de ambiente Python
- Chave da OpenAI com acesso a `gpt-5.6-luna`; Ollama com `gemma4:12b-it-qat` é fallback opcional

### 1. Clonar o repositório

```bash
git clone https://github.com/PedroHSSoares-Dev/locaweb.git
cd locaweb
```

### 2. Instalar dependências Python

```bash
conda env create -f environment.yml
conda activate predictfy-locaweb
python -m pip install -r api/requirements.txt
```

O último comando instala as dependências do serviço web, incluindo FastAPI, Uvicorn, autenticação Microsoft e o driver PostgreSQL.

### 3. Adicionar o dataset

```
data/raw/LW-DATASET.xlsx   ← arquivo fornecido pela Locaweb
```

### 4. Executar o pipeline de ML

```bash
# Pipeline completo (inclui os treinos Prophet; vários minutos)
python src/pipeline.py

# Etapas individuais
python src/pipeline.py --step fe          # feature engineering (~8s)
python src/pipeline.py --step xgb         # XGBoost risco OLA (~6s)
python src/pipeline.py --step km          # K-Means clustering (~4s)
python src/pipeline.py --step kpi         # projeção KPI (~2s)
python src/pipeline.py --step prophet     # Prophet 2025-only (~36s)
python src/pipeline.py --step prophet-mc  # Prophet Monte Carlo (~5min)
python src/pipeline.py --step lstm        # LSTM v2 (~25s)
python src/pipeline.py --step baseline    # baseline sazonal semanal
python src/pipeline.py --step horizon     # Prophet D+1..D+365 exploratório (~2s)
python src/pipeline.py --step compare     # comparação no holdout temporal comum
python src/pipeline.py --step segments    # agregados operacionais anonimizados
python src/pipeline.py --step xgb-specialists # experimento isolado P2/P3; não promove produção
python -m src.validation.artifacts        # valida contratos antes do deploy
python -m src.validation.release_preflight # valida ativos, shadows e horizonte público
```

Todos os JSONs são gerados em `outputs/` e os modelos serializados em `models_saved/`.

### 5. Iniciar a API

```bash
cp .env.example .env
# Configure Entra ID, CHAT_SESSION_SECRET e, para o modo OpenAI, OPENAI_API_KEY.
# Para fallback offline:
# ollama pull gemma4:12b-it-qat
uvicorn api.main:app --reload
# API em http://localhost:8000
# Docs em http://localhost:8000/docs
```

As variáveis e os registros necessários do Microsoft Entra ID estão documentados em [`docs/autenticacao_entra.md`](docs/autenticacao_entra.md).

### 6. Iniciar o frontend

```bash
cd frontend
npm ci
npm run dev
# Dashboard em http://localhost:5173
```

Copie `frontend/.env.example` para `frontend/.env.local` e informe a URL da API, o Client ID da SPA, o redirect URI e o scope exposto pela API.

### 7. Executar os gates locais

```bash
# Na raiz
python -m src.validation.artifacts
python -m src.validation.release_preflight
python -m unittest discover -s tests -v

# Em frontend/
npm run lint
npm run build
npm run test:e2e
```

---

## Dashboard — visões disponíveis

| Rota | Público-alvo | Conteúdo |
|------|-------------|---------|
| `/gestao` | Gestão e diretoria | Saúde operacional · metas OLA · impacto estimado · previsão ativa |
| `/monitoramento` | Geral | Heatmap Volume/Anomalia · alertas operacionais · sazonalidade |
| `/operacoes` | Analistas / SRE | Fila shadow · priorização Top-5% · investigação · feedback observado |
| `/tecnico` | DevOps / SRE | Clusters K-Means · perfis de risco · SHAP feature importance |
| `/modelos` | Todos | Registro de modelos · métricas · protocolos · ativos, shadows e limitações |
| `/admin` | Administradores | Convites · RBAC · revogação de acesso · uso de tokens · preflight |

---

## Modelos de ML

`outputs/model_registry.json` é a fonte canônica para saber o que está ativo, em shadow ou disponível apenas para cenário.

| Modelo | Papel | Status atual | Evidência de referência |
|--------|-------|--------------|-------------------------|
| **Baseline sazonal de 3 semanas** | Volume D+1 a D+7 | **Ativo / serving** | MAE médio Total=12,4605; venceu 7/7 horizontes no rolling origin de 2025-Q4 |
| **Calendar Adjusted Seasonal** | Candidato de volume Total | **Shadow offline** | MAE=10,1848; melhora de 18,264%; sem validação prospectiva em 2026 |
| **LSTM v2** | Benchmark de volume D+1 a D+7 | Disponível | MAE médio D1–D7=21,19 no holdout comum |
| **Prophet / Prophet MC** | Benchmarks de volume | Disponíveis | MAE médio D1–D7=47,66 / 25,61 no protocolo registrado |
| **XGBoost OLA Risk** | Triagem P2/P3 | **Ativo / triagem humana** | PR-AUC=0,1290; Recall=82,0%; Precision=2,86%; F1=5,53% em 2025-Q4 |
| **Linear SVM Structured** | Ranking OLA Top-5% | **Shadow offline** | Recall@5%=27,1%; 3,24 alertas/dia; 20,59 revisões por acerto; sem validação prospectiva |
| **K-Means** (K=5) | Segmentação operacional | Exploratório | Silhouette=0,2001; descreve perfis, não causalidade |
| **Prophet de longo prazo** | Cenários D+8 a D+365 | Somente cenário | Após D+7 é projeção exploratória, não previsão validada |

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
- **Acesso:** o Microsoft Entra ID valida a identidade; o backend vincula o primeiro login ao par imutável `tenant + object ID` e emite uma sessão HMAC temporária, revalidada no PostgreSQL em cada requisição.
- **Administração:** `/admin` permite ao proprietário e aos administradores convidar e-mails, definir `member/admin`, desativar, reativar ou remover acessos. As mudanças revogam sessões existentes e geram auditoria append-only.
- **Custo sob controle:** somente consultas analíticas usam a OpenAI; perguntas factuais continuam locais. O modelo e o esforço são configuráveis por ambiente.
- **Fallback offline:** com Ollama ativo, a sessão inicia e pré-carrega o Gemma sob demanda; o logout descarrega o modelo e encerra somente o servidor iniciado pela API.
- **Persistência cloud-agnostic:** SQLite funciona sem configuração local; `CHAT_DATABASE_URL` troca o repositório por PostgreSQL em produção sem alterar o frontend.
- **Endpoints:** além de sessão/status/chat, há CRUD em `/api/chat/conversations`, feedback, reset de memória curta e métricas.
- **Autenticação e autorização:** Microsoft Entra ID + diretório dinâmico no PostgreSQL/Supabase, com papéis `member/admin`. `ALLOWED_EMAILS` serve somente para o bootstrap do proprietário inicial. Consulte [`docs/autenticacao_entra.md`](docs/autenticacao_entra.md).

O frontend espera `VITE_API_URL=http://localhost:8000/api`. A chave da OpenAI permanece somente no backend. Se a API for executada no Docker com fallback Ollama no macOS, `host.docker.internal:11434` já está configurado.

Em produção, configure `CORS_ALLOWED_ORIGINS` na API com a origem exata do frontend, atualmente `https://predictfy.vercel.app`.
O arquivo `render.yaml` descreve a API. O workflow `.github/workflows/ci.yml` executa testes de API/segurança, lint/build do frontend, teste responsivo e valida os 11 contratos de artefatos ML atuais; com o deploy automático configurado para aguardar os checks, o Render só publica um commit aprovado e o build da Vercel continua protegido pelo gate do frontend.

---

## Prazos FIAP

| Sprint | Entrega | Data |
|--------|---------|------|
| Sprint 1 | Apresentação executiva | 12/04/2026 |
| Sprint 2 | Arquitetura + EDA + protótipos | 17/05/2026 |
| Sprint 3 | MVP funcional (link da aplicação) | 23/05/2026 |
| Sprint 4 | Apresentação final + pitch (NEXT 2026) | 14/09/2026 |

---

## Licença

Projeto acadêmico desenvolvido para o **FIAP Enterprise Challenge 2026** em parceria com a **Locaweb**.  
Os dados utilizados são propriedade da Locaweb e não estão incluídos neste repositório.

---

<p align="center">Feito com dedicação pela equipe <strong>Predictfy</strong> · FIAP 2026</p>
