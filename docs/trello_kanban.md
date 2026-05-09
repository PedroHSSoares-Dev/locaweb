# Predictfy × Locaweb — Cards do Trello (Simulação)

> **Como usar:** Cada seção é um Sprint (Epic). Cada card vai para a lista correspondente ao seu estado atual.
> Listas sugeridas: **Backlog → A Fazer → Em Progresso → Em Revisão → Concluído**
> Labels sugeridas: `ML` `Frontend` `Backend` `Dados` `Docs` `Apresentação` `DevOps`

---

## Sprint 1 — Ideação ✅ (entrega: 12/04/2026)

---

### [S1-01] Kick-off e formação do time
**Lista:** Concluído  
**Label:** `Docs`  
**Estimativa:** 3h  
**Descrição:** Reunião de kick-off, definição de papéis e responsabilidades, setup de ferramentas de comunicação e repositório GitHub.

**Checklist:**
- [x] Criar repositório no GitHub
- [x] Definir stack tecnológica
- [x] Configurar ambiente Python (micromamba)
- [x] Criar estrutura de pastas inicial
- [x] Definir papéis do time

---

### [S1-02] Análise do problema e escopo
**Lista:** Concluído  
**Label:** `Docs`  
**Estimativa:** 4h  
**Descrição:** Entendimento profundo do desafio Locaweb, regras de negócio dos OLAs, metas anuais de violações e critérios do FIAP Enterprise Challenge.

**Checklist:**
- [x] Ler Dicionário de Dados (LW-DATASET)
- [x] Entender OLAs (P2=4h, P3=12h)
- [x] Mapear metas anuais (P2: 36-39, P3: 231-263 violações/ano)
- [x] Identificar regras anti-leakage
- [x] Definir variável target (`KPI Violado?`)

---

### [S1-03] EDA preliminar do dataset
**Lista:** Concluído  
**Label:** `Dados` `ML`  
**Estimativa:** 6h  
**Descrição:** Exploração inicial do LW-DATASET.xlsx: volume, distribuição de prioridades, sazonalidade, desbalanceamento de classes e achados críticos.

**Checklist:**
- [x] Carregar e inspecionar LW-DATASET.xlsx (122.543 incidentes)
- [x] Identificar subset KPI (~25.600 incidentes P2+P3)
- [x] Analisar desbalanceamento (1:102 SIM/NÃO)
- [x] Mapear nulos MNAR (Produto, Categoria, Subcategoria)
- [x] Identificar P2 só a partir de 2025

---

### [S1-04] Definição da arquitetura inicial
**Lista:** Concluído  
**Label:** `Docs` `Backend`  
**Estimativa:** 4h  
**Descrição:** Esboço da arquitetura da solução: pipeline de dados, modelos de ML, API, dashboard e chatbot. Decisões de stack.

**Checklist:**
- [x] Definir fluxo: XLSX → preprocessor → modelos → JSONs → API → React
- [x] Escolher modelos (Prophet, XGBoost, K-Means)
- [x] Definir stack frontend (React + Vite + Recharts)
- [x] Definir stack API (FastAPI)
- [x] Mapear perfis de usuário (Gestão, Monitoramento, Técnico, Financeiro)

---

### [S1-05] Elaboração do PowerPoint — Sprint 1
**Lista:** Concluído  
**Label:** `Apresentação`  
**Estimativa:** 8h  
**Descrição:** Criação do deck de ideação conforme template FIAP: problema, solução proposta, arquitetura inicial, stack e roadmap.

**Checklist:**
- [x] Slide de capa e time
- [x] Slide de contexto e problema
- [x] Slide de solução proposta
- [x] Slide de arquitetura
- [x] Slide de stack tecnológica
- [x] Slide de roadmap (sprints)
- [x] Revisão e ensaio

---

### [S1-06] Apresentação Sprint 1 — FIAP
**Lista:** Concluído  
**Label:** `Apresentação`  
**Estimativa:** 2h  
**Descrição:** Apresentação presencial na FIAP em 12/04/2026.

---

## Sprint 2 — Arquitetura + EDA + Protótipos (entrega: 17/05/2026)

---

### [S2-01] Feature Engineering — preprocessor.py
**Lista:** Concluído  
**Label:** `Dados` `ML`  
**Estimativa:** 1 dia  
**Descrição:** Implementar `src/data/preprocessor.py` com todas as 27 features canônicas (convenção NB04): temporais, binárias, lags, encoded, frequência e cíclicas.

**Checklist:**
- [x] Features temporais (hora, dia_semana, mes, trimestre, dia_mes, semana_ano)
- [x] Features binárias (is_horario_comercial, is_fim_de_semana, is_segunda_terca)
- [x] Lags e rolling (lag_1d, lag_7d, rolling_7d, rolling_30d, lag_1d_p2, lag_1d_p3)
- [x] Label encoding (produto, categoria, subcategoria, grupo, aberto_por)
- [x] Frequency encoding (produto_freq, grupo_freq)
- [x] Features cíclicas (mes_sin, mes_cos)
- [x] Target (target_ola = KPI Violado? == SIM)
- [x] Exportar parquet (25.588 linhas × 27 colunas)
- [x] Validação: sem nulos, sem data leakage

---

### [S2-02] EDA completa — Notebooks exploratórios
**Lista:** Concluído  
**Label:** `Dados` `ML`  
**Estimativa:** 1,5 dias  
**Descrição:** Criar notebooks 100% exploratórios (sem geração de arquivos de produção) para análise de features, distribuições, correlações e resultados dos modelos.

**Checklist:**
- [x] 01_eda.ipynb — EDA completa do dataset
- [x] 02_eda_features.ipynb — Distribuição de features, imbalance, Pearson com target
- [x] 04_eda_xgboost.ipynb — PR/ROC curves, confusion matrix, SHAP bar
- [x] 05_eda_kmeans.ipynb — Heatmap de clusters, PCA 2D, taxa de violação por cluster
- [x] 07_eda_kpi.ipynb — Violações vs orçamento mensal, projeção anual

---

### [S2-03] Modelo XGBoost — Classificação de risco OLA
**Lista:** Concluído  
**Label:** `ML`  
**Estimativa:** 2 dias  
**Descrição:** Implementar `src/models/xgboost_model.py`: split temporal, SMOTE no treino, comparação Base vs SMOTE por PR-AUC, threshold por F1, SHAP, exportar `outputs/risco_ola.json`.

**Checklist:**
- [x] Split temporal (80% treino / 20% teste, ordenado por data)
- [x] SMOTE aplicado SOMENTE no treino
- [x] Modelo Base (scale_pos_weight) vs Modelo SMOTE
- [x] Seleção por PR-AUC (Base venceu: 0.048 vs 0.032)
- [x] Cross-validation 5-fold estratificado
- [x] Threshold otimizado por F1 (0.3072)
- [x] SHAP feature importance
- [x] Exportar risco_ola.json com formato compatível com a API

---

### [S2-04] Modelo K-Means — Clustering de padrões
**Lista:** Concluído  
**Label:** `ML`  
**Estimativa:** 1 dia  
**Descrição:** Implementar `src/models/kmeans_model.py`: avaliação K=2-10, candidatos K ímpar ≥ 5, seleção por voto majoritário (Silhouette, CH, DB), exportar `outputs/clusters.json`.

**Checklist:**
- [x] Seleção de features de clustering (11 features)
- [x] StandardScaler antes do clustering
- [x] Avaliação K=2-10 com 3 métricas
- [x] Seleção por voto majoritário (K=5 selecionado)
- [x] PCA 2D para visualização
- [x] Nomeação automática de clusters por perfil
- [x] Exportar clusters.json com formato compatível com a API

---

### [S2-05] Projeção KPI — Meta dinâmica mensal
**Lista:** Concluído  
**Label:** `ML` `Backend`  
**Estimativa:** 0,5 dia  
**Descrição:** Implementar `src/models/kpi_projection.py` com redistribuição de orçamento mensal dinâmica: se um mês estoura, os meses seguintes têm orçamento menor.

**Checklist:**
- [x] Lógica `calcular_meta_ajustada()` com redistribuição progressiva
- [x] Status por mês (ok / atencao / critico)
- [x] Identificação de meses anômalos
- [x] Exportar kpi_atingimento.json com formato compatível com a API

---

### [S2-06] Pipeline orquestrador — src/pipeline.py
**Lista:** Concluído  
**Label:** `Backend` `DevOps`  
**Estimativa:** 0,5 dia  
**Descrição:** Criar `src/pipeline.py` como ponto único de execução do pipeline de ML, com suporte a steps individuais via `--step`.

**Checklist:**
- [x] Step `fe` — Feature Engineering
- [x] Step `xgb` — XGBoost
- [x] Step `km` — K-Means
- [x] Step `kpi` — Projeção KPI
- [x] Modo completo (sem --step roda tudo)
- [x] Validação: pipeline completo em < 30s

---

### [S2-07] API FastAPI — Endpoints
**Lista:** Concluído  
**Label:** `Backend`  
**Estimativa:** 1,5 dias  
**Descrição:** Implementar e validar todos os endpoints da API FastAPI: previsões, risco, clusters, kpi, histórico e context para chatbot.

**Checklist:**
- [x] `/api/previsoes` — hierarquia LSTM > Prophet MC > Prophet original
- [x] `/api/previsoes/d1`, `/api/previsoes/d7`, `/api/previsoes/serie`
- [x] `/api/risco`, `/api/risco/produtos`, `/api/risco/grupos`
- [x] `/api/clusters`
- [x] `/api/kpi?periodo=ano|trimestre|mes`
- [x] `/api/historico/mensal`, `/api/historico/diario`, `/api/historico/sazonalidade`
- [x] `/api/context` — snapshot para chatbot
- [x] Todos os endpoints retornando 200

---

### [S2-08] Dashboard React — 4 páginas
**Lista:** Concluído  
**Label:** `Frontend`  
**Estimativa:** 3 dias  
**Descrição:** Implementar as 4 rotas do dashboard React com gráficos Recharts consumindo a API FastAPI.

**Checklist:**
- [x] `/gestao` — KPI cards, tendência mensal, R$ em risco
- [x] `/monitoramento` — Heatmap sazonalidade, série temporal + previsão, alertas de risco
- [x] `/tecnico` — Risco OLA por grupo, clusters K-Means, SHAP values
- [x] `/financeiro` — Projeção KPI anual, violações vs orçamento mensal
- [x] Filtro de período (mês / trimestre / ano) funcional
- [x] Responsividade básica

---

### [S2-09] Documentação técnica — docs/
**Lista:** Concluído  
**Label:** `Docs`  
**Estimativa:** 1 dia  
**Descrição:** Criar documentação técnica completa em `docs/`: arquitetura, dataset, modelos e API.

**Checklist:**
- [x] docs/arquitetura.md — diagrama de camadas + decisões arquiteturais
- [x] docs/arquitetura.drawio — diagrama visual (draw.io XML)
- [x] docs/dataset.md — dicionário de dados, OLAs, metas, leakage
- [x] docs/modelos.md — pipeline chain, hiperparâmetros, JSONs
- [x] docs/api.md — endpoints com exemplos de request/response
- [x] README.md atualizado
- [x] CLAUDE.md atualizado

---

### [S2-10] Elaboração da apresentação — Sprint 2
**Lista:** A Fazer  
**Label:** `Apresentação`  
**Estimativa:** 1 dia  
**Descrição:** Criar deck Sprint 2 conforme template FIAP: arquitetura implementada, EDA, modelos, dashboard e próximos passos.

**Checklist:**
- [ ] Slide de capa e time
- [ ] Slide de arquitetura implementada (draw.io)
- [ ] Slide de resultados EDA (gráficos)
- [ ] Slide de modelos (XGBoost, K-Means, KPI — métricas)
- [ ] Slide de demo do dashboard
- [ ] Slide de próximos passos (Sprint 3)
- [ ] Revisão e ensaio

---

### [S2-11] Apresentação Sprint 2 — FIAP
**Lista:** A Fazer  
**Label:** `Apresentação`  
**Estimativa:** 2h  
**Data:** 17/05/2026

---

## Sprint 3 — MVP Funcional (data a definir)

---

### [S3-01] Conversão Prophet → src/models/prophet_model.py
**Lista:** Backlog  
**Label:** `ML` `Backend`  
**Estimativa:** 2 dias  
**Descrição:** Extrair a lógica de treino e exportação dos notebooks 03_prophet_volume.ipynb, 03b_monte_carlo_seed.ipynb e 03c_prophet_monte_carlo.ipynb para `src/models/prophet_model.py`. O pipeline automatizado não pode depender de notebooks.

**Checklist:**
- [ ] Extrair lógica Prophet v5 + v6 (ensemble)
- [ ] Incorporar Monte Carlo seed (03b)
- [ ] Incorporar Prophet MC ensemble (03c)
- [ ] Exportar `previsoes_volume.json` e `previsoes_volume_mc.json`
- [ ] Adicionar step `prophet` em `src/pipeline.py`
- [ ] Validar MAE holdout

---

### [S3-02] Conversão LSTM → src/models/lstm_model.py
**Lista:** Backlog  
**Label:** `ML` `Backend`  
**Estimativa:** 2 dias  
**Descrição:** Extrair a lógica de treino e exportação do notebook 03d_lstm.ipynb para `src/models/lstm_model.py`. LSTM v2 com early stopping, MAE=13.15.

**Checklist:**
- [ ] Extrair LSTMForecaster (PyTorch)
- [ ] Preservar early stopping e arquitetura v2
- [ ] Exportar `previsoes_lstm.json`
- [ ] Adicionar step `lstm` em `src/pipeline.py`
- [ ] Validar MAE holdout (< 15 incidentes/dia)

---

### [S3-03] Pipeline completo automatizado
**Lista:** Backlog  
**Label:** `DevOps` `Backend`  
**Estimativa:** 0,5 dia  
**Descrição:** Garantir que `python src/pipeline.py` (sem flags) execute todos os steps incluindo Prophet e LSTM, gerando todos os 6 JSONs em `outputs/`.

**Checklist:**
- [ ] Step `prophet` integrado ao pipeline
- [ ] Step `lstm` integrado ao pipeline
- [ ] Todos os 6 JSONs gerados em uma execução
- [ ] Tempo total < 5 minutos
- [ ] Sem dependência de notebooks

---

### [S3-04] GitHub Actions — CI/CD do pipeline ML
**Lista:** Backlog  
**Label:** `DevOps`  
**Estimativa:** 1 dia  
**Descrição:** Criar workflow GitHub Actions para executar `src/pipeline.py` automaticamente (semanal ou on-push), atualizar os JSONs em `outputs/` e acionar deploy no Vercel.

**Checklist:**
- [ ] Workflow YAML (.github/workflows/pipeline.yml)
- [ ] Setup micromamba no runner
- [ ] Cache de dependências
- [ ] Execução de `python src/pipeline.py`
- [ ] Commit automático dos JSONs atualizados
- [ ] Trigger: schedule semanal + push em main

---

### [S3-05] Chatbot Gemini — Roteador (Flash)
**Lista:** Backlog  
**Label:** `Backend` `ML`  
**Estimativa:** 1,5 dias  
**Descrição:** Implementar LLM 1 com Gemini 2.5 Flash como roteador: responde perguntas simples usando o snapshot de `/api/context` e escala para o Pro quando necessário.

**Checklist:**
- [ ] Integração com Gemini 2.5 Flash API
- [ ] System prompt com contexto operacional (via /api/context)
- [ ] Lógica de roteamento: resposta simples vs escala para Pro
- [ ] Tempo de resposta alvo: < 2s para perguntas simples
- [ ] Tratamento de erros e fallback

---

### [S3-06] Chatbot Gemini — Analista (Pro)
**Lista:** Backlog  
**Label:** `Backend` `ML`  
**Estimativa:** 1,5 dias  
**Descrição:** Implementar LLM 2 com Gemini 2.5 Pro como analista sênior: recebe contexto expandido e retorna análise formatada para o Flash repassar ao usuário.

**Checklist:**
- [ ] Integração com Gemini 2.5 Pro API
- [ ] System prompt expandido com histórico e outputs dos modelos
- [ ] Contexto: risco_ola + clusters + kpi + previsoes
- [ ] Resposta formatada para o dashboard
- [ ] Testes com perguntas reais de operação

---

### [S3-07] Integração do chatbot no dashboard
**Lista:** Backlog  
**Label:** `Frontend` `Backend`  
**Estimativa:** 1 dia  
**Descrição:** Criar componente de chat no dashboard React integrado à API do chatbot. Disponível em todas as páginas como drawer lateral.

**Checklist:**
- [ ] Componente ChatDrawer (React)
- [ ] Endpoint `/api/chat` (FastAPI → Gemini)
- [ ] Histórico de mensagens na sessão
- [ ] Indicador de "digitando..."
- [ ] Exemplos de perguntas sugeridas

---

### [S3-08] Power BI — Dashboard entregável FIAP
**Lista:** Backlog  
**Label:** `Frontend` `Apresentação`  
**Estimativa:** 2 dias  
**Descrição:** Criar dashboard Power BI como entregável oficial do FIAP Enterprise Challenge, conectando aos JSONs exportados pelo pipeline.

**Checklist:**
- [ ] Importar JSONs de outputs/ no Power BI
- [ ] Página: Visão Geral (KPI cards + tendência)
- [ ] Página: Risco OLA (XGBoost + grupos)
- [ ] Página: Clusters (K-Means + perfis)
- [ ] Página: Projeção KPI (meta mensal dinâmica)
- [ ] Publicar no Power BI Service

---

### [S3-09] Testes E2E e QA
**Lista:** Backlog  
**Label:** `Backend` `Frontend`  
**Estimativa:** 1 dia  
**Descrição:** Validação end-to-end do sistema completo: pipeline → API → dashboard → chatbot.

**Checklist:**
- [ ] Pipeline completo sem erros
- [ ] Todos os endpoints API retornam 200
- [ ] Dashboard carrega em < 3s
- [ ] Chatbot responde em < 5s
- [ ] Sem erros de console no frontend
- [ ] Validação anti-leakage nos modelos

---

### [S3-10] Deploy em produção — Vercel + API
**Lista:** Backlog  
**Label:** `DevOps`  
**Estimativa:** 0,5 dia  
**Descrição:** Deploy do frontend no Vercel e configuração do servidor da API (backend).

**Checklist:**
- [ ] Frontend deployado no Vercel
- [ ] Variáveis de ambiente configuradas
- [ ] API acessível publicamente
- [ ] URL de produção testada e funcional

---

### [S3-11] Apresentação Sprint 3 — FIAP
**Lista:** Backlog  
**Label:** `Apresentação`  
**Estimativa:** 1 dia  
**Descrição:** Deck e apresentação do MVP funcional conforme template FIAP.

**Checklist:**
- [ ] Demo ao vivo do dashboard
- [ ] Demo do chatbot
- [ ] Métricas dos modelos
- [ ] Slide de próximos passos (Sprint 4)

---

## Sprint 4 — Apresentação Final / NEXT 2026

---

### [S4-01] Refinamentos baseados no feedback Sprint 3
**Lista:** Backlog  
**Label:** `ML` `Frontend`  
**Estimativa:** 2 dias  
**Descrição:** Incorporar feedbacks da banca e do time após a apresentação da Sprint 3.

**Checklist:**
- [ ] Listar feedbacks recebidos
- [ ] Priorizar ajustes por impacto
- [ ] Implementar refinamentos selecionados
- [ ] Validação final do sistema

---

### [S4-02] Pitch deck final
**Lista:** Backlog  
**Label:** `Apresentação`  
**Estimativa:** 1,5 dias  
**Descrição:** Deck executivo para o NEXT 2026: storytelling, impacto de negócio, demo, diferenciais competitivos e pitch de produto.

**Checklist:**
- [ ] Slide de hook (problema impactante)
- [ ] Slide de solução (demo screenshot)
- [ ] Slide de impacto (R$ economizados, violações evitadas)
- [ ] Slide de tecnologia (arquitetura resumida)
- [ ] Slide de diferenciais vs concorrentes
- [ ] Slide de próximos passos (roadmap de produto)
- [ ] Ensaio com timer (< 10 min)

---

### [S4-03] Vídeo demonstração — YouTube
**Lista:** Backlog  
**Label:** `Apresentação`  
**Estimativa:** 1 dia  
**Descrição:** Gravar e editar vídeo de demonstração do MVP para submissão no YouTube conforme requisito FIAP.

**Checklist:**
- [ ] Script do vídeo (3-5 min)
- [ ] Gravação do dashboard em uso
- [ ] Gravação do chatbot em ação
- [ ] Gravação da arquitetura (draw.io)
- [ ] Edição e legenda
- [ ] Upload no YouTube (unlisted ou público)

---

### [S4-04] Documentação final do projeto
**Lista:** Backlog  
**Label:** `Docs`  
**Estimativa:** 0,5 dia  
**Descrição:** Garantir que README, CLAUDE.md e docs/ estejam completos, atualizados e prontos para entrega.

**Checklist:**
- [ ] README com link do Vercel e YouTube
- [ ] docs/ completo e revisado
- [ ] CLAUDE.md com status final
- [ ] Tag v1.0 no GitHub

---

### [S4-05] Ensaios e dry-run para o NEXT
**Lista:** Backlog  
**Label:** `Apresentação`  
**Estimativa:** 3h  
**Descrição:** Ensaio completo da apresentação final com cronometragem, simulação de perguntas da banca e ajustes finais.

**Checklist:**
- [ ] Dry-run completo (pitch + demo)
- [ ] Simulação de perguntas difíceis
- [ ] Ajuste de timing
- [ ] Verificar demo ao vivo (internet, laptop backup)

---

### [S4-06] Apresentação Final — NEXT 2026 (Banca + YouTube)
**Lista:** Backlog  
**Label:** `Apresentação`  
**Estimativa:** —  
**Descrição:** Apresentação presencial para a banca do FIAP Enterprise Challenge no evento NEXT 2026.

---

## Resumo por Sprint

| Sprint | Cards | Estimativa total |
|---|---|---|
| Sprint 1 ✅ | 6 cards | ~27h |
| Sprint 2 | 11 cards | ~14 dias |
| Sprint 3 | 11 cards | ~15 dias |
| Sprint 4 | 6 cards | ~6 dias |
| **Total** | **34 cards** | **~35 dias de trabalho** |

## Labels Sugeridas no Trello

| Label | Cor | Uso |
|---|---|---|
| `ML` | Verde | Modelos, dados, feature engineering |
| `Frontend` | Laranja | React, UI, visualizações |
| `Backend` | Roxo | API, FastAPI, integração |
| `Dados` | Azul | Dataset, ETL, parquet |
| `Docs` | Cinza | Documentação, CLAUDE.md, README |
| `Apresentação` | Vermelho | Decks, vídeo, pitch |
| `DevOps` | Preto | CI/CD, GitHub Actions, deploy |
