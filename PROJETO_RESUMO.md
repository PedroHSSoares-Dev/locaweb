# Predictfy × Locaweb — AIOps Infra Predict
### FIAP Enterprise Challenge 2026 · Turma 2TSCPW

---

## Visão Geral

Solução de **AIOps (Artificial Intelligence for IT Operations)** desenvolvida em parceria com a Locaweb para o FIAP Enterprise Challenge 2026. Transforma 122.543 incidentes históricos do sistema ITSM (jan/2023–dez/2025) em inteligência preditiva para antecipar falhas, prever volume de incidentes, classificar risco de violação de SLA e apoiar decisões operacionais via dashboard interativa.

| Campo | Valor |
|---|---|
| Integrante principal | Pedro (RM-562283) · @PedroHSSoares-Dev |
| Período do dataset | Jan/2023 – Dez/2025 |
| Volume de dados | 122.543 incidentes |
| Subset KPI | ~25.600 incidentes (P2 + P3) |
| Deploy | Vercel (frontend) · GitHub Actions (pipeline ML) |

---

## Stack Tecnológica

| Camada | Tecnologias |
|---|---|
| Modelos ML | Prophet · XGBoost · scikit-learn · LSTM (PyTorch) · SHAP · imbalanced-learn |
| Dados | pandas · numpy · openpyxl · pyarrow |
| Frontend | React + Vite · Recharts · react-router-dom · lucide-react |
| Chatbot | Gemini 2.5 Flash (roteador) · Gemini 2.5 Pro (analista sênior) |
| Deploy | Vercel · GitHub Actions |
| Entregável FIAP | Power BI |

---

## Arquitetura da Solução

```
Dataset ITSM (XLSX · 122.543 incidentes)
              ↓
   Preparação & Validação (nb01 + nb02)
       limpeza · feature engineering
              ↓
 ┌────────────────────────────────────────┐
 │           Pipeline de ML               │
 │  Prophet      XGBoost      K-Means     │
 │  D+1/D+7      risco OLA    clusters    │
 │   (nb03)       (nb04)       (nb05)     │
 │                                        │
 │  LSTM              SHAP                │
 │  séries temporais  explicabilidade     │
 │   (nb03d)           (nb06)             │
 └────────────────────────────────────────┘
              ↓
     JSONs estáticos (outputs/)
              ↓
  ┌──────────────────┬──────────────────┐
  │  Dashboard React │    Power BI      │
  │  /gestao         │  (entregável     │
  │  /monitoramento  │   FIAP)          │
  │  /tecnico        │                  │
  │  /financeiro     │                  │
  └──────────────────┴──────────────────┘
              ↓
    Chatbot Gemini (roteador + analista)
```

---

## Contexto de Negócio

### OLAs (Prazos de Resolução por Prioridade)
| Prioridade | Label | OLA | Meses anômalos em 2025 |
|---|---|---|---|
| P2 | Alta | 4 horas | Maio, Julho, Novembro |
| P3 | Média | 12 horas | Junho, Julho |

### Metas e Atingimento 2025 (via SPC)
| Prioridade | Violações Reais | Meta Anual (SPC) | % Utilizado | Margem |
|---|---|---|---|---|
| P2 | 42 | 63 | 66.7% | +21 |
| P3 | 206 | 280 | 73.6% | +74 |

> **Método:** As metas foram derivadas estatisticamente via SPC (Statistical Process Control): `Meta = Média mensal histórica + 1 desvio padrão (σ)`. Essa é a abordagem padrão para distinguir variação normal de anomalia operacional na ausência de SLA formal documentado.

### Desbalanceamento do Dataset
- Taxa de violação: **0.97%** — 248 SIM vs 24.997 NÃO
- Razão: ~102:1 (não-violação : violação)
- Tratamento: SMOTE aplicado exclusivamente no conjunto de treino

---

## Análises Realizadas

### Notebook 01 — EDA (Análise Exploratória)

**Objetivo:** Explorar os 122.543 incidentes e gerar entendimento profundo para embasar o feature engineering.

**Principais descobertas:**

- **Qualidade de dados:** Produto (63.7%) e Categoria (63.5%) apresentam nulos MNAR — concentrados em incidentes "Sem Intervenção" que não entram para KPI. Decisão: preencher com `"DESCONHECIDO"` (ausência é sinal preditivo).
- **Distribuição temporal:** A grande maioria das violações está em 2025 (248 de 258 totais), tornando os anos anteriores pouco representativos para treino de classificação.
- **Validação do ground truth:** O campo `KPI Violado?` é 100% auditado pela Locaweb e **não** é derivado mecanicamente de `Duração > OLA`. Há 3.399 registros divergentes — o campo do sistema é o target confiável.
- **Padrão semanal:** Maior concentração de incidentes em terças e quartas-feiras.
- **Padrão horário:** Picos às 08h–09h (abertura pós-madrugada) e 17h–18h (fechamento de expediente).
- **Sazonalidade anual:** Junho–Julho registram picos ~31% acima da média anual.
- **Incidentes recorrentes:** Top 10 descrições cobrem 28% do volume. Incidentes recorrentes têm taxa de violação 4.7% vs 0.6% de incidentes únicos.
- **Subcategorias:** Cramér's V = 0.32 (maior associação com o target entre as variáveis categóricas). Categorias de infraestrutura apresentam 3.2× maior taxa de violação.

---

### Notebook 02 — Feature Engineering

**Objetivo:** Transformar o dataset bruto em dataset modelável com zero data leakage.

**Dataset final:** 25.245 linhas × 25 colunas (24 features + 1 target)

**Features criadas:**

| Grupo | Features | Tipo |
|---|---|---|
| Temporais | `hora`, `dia_semana`, `mes`, `trimestre`, `dia_mes`, `semana_ano` | Numéricas |
| Indicadores | `is_horario_comercial`, `is_fim_de_semana`, `is_segunda_terca`, `periodo_dia` | Binárias/Ordinal |
| Lags de volume | `lag_1d`, `lag_7d`, `rolling_7d`, `rolling_30d` | Numéricas |
| Categóricas | `produto_enc`, `categoria_enc`, `subcategoria_enc`, `grupo_enc`, `aberto_por_enc` | Label Encoded |
| Frequency | `produto_freq`, `grupo_freq` | Float |
| Prioridade | `prioridade_bin` (P2=1, P3=0) | Binária |
| **Target** | **`target_ola`** (KPI Violado?) | **Binária** |

**Colunas bloqueadas por leakage:** `Duração`, `Resolvido`, `Encerrado`, `Código de fechamento`, `Solução`, `KPI Violado?`

**Exportado em:** `data/processed/incidents_features.parquet`

---

### Notebook 03 — Prophet: Previsão de Volume

**Objetivo:** Prever volume de incidentes KPI nos horizontes D+1 a D+7 por prioridade (Total, P2, P3).

**Evolução de modelos testados:**

| Versão | Configuração | Destaque |
|---|---|---|
| v1 | Baseline Prophet padrão | MAE médio ~19.4 |
| v2 | + lag_1d como regressor | Melhora 2–8% em MAE |
| v3 | + Termos de Fourier | Pior (overfitting em série curta) |
| v4 | Modelos separados por tipo de dia | Inconsistente |
| v5 | Todos os lags (lag_1d, lag_7d, rolling_7d, rolling_30d) | Melhor em D+2 a D+5 |
| v6 | v5 + indicador is_dia_util | Melhor em D+1, D+4, D+6, D+7 |
| **Ensemble** | **v5+v6 adaptativo por horizonte** | **Melhor global** |

**Estratégia ensemble:** selecionar v5 ou v6 por horizonte com base no menor MAE de validação cruzada.

| Horizonte | Modelo | MAE |
|---|---|---|
| D+1 | v6 | 17.06 |
| D+2 | v5 | 10.93 |
| D+3 | v5 | 7.36 |
| D+4 | v6 | 11.46 |
| D+5 | v5 | 9.06 |
| D+6 | v6 | 20.02 |
| D+7 | v6 | 14.14 |

**Previsões finais (ensemble) — Próximos 7 dias:**
| Série | D+1 (forecast) | D+7 (forecast) |
|---|---|---|
| Total | 32.4 inc. [17.8–47.7] | 53.4 inc. [38.0–68.6] |
| P2 | 15.4 inc. [9.2–20.7] | 18.5 inc. [13.0–24.1] |
| P3 | 28.4 inc. [13.6–43.6] | 45.6 inc. [31.8–60.5] |

**Feriados brasileiros incluídos:** 16 datas (nacionais + vésperas customizadas)

**Output:** `outputs/previsoes_volume.json`

---

### Notebook 03d — LSTM: Deep Learning para Séries Temporais

**Objetivo:** Superar o Prophet com modelo de deep learning capaz de capturar padrões não-lineares.

**Arquitetura:**
```
Input (lookback = 30 dias)
  → LSTM Layer 1 (hidden=128, return_sequences=True)
  → Dropout (0.3)
  → LSTM Layer 2 (hidden=128)
  → Dense (64, ReLU)
  → Dense (3, Linear) → [Total, P2, P3]
```

**Dados:**
- Treino: Jan/2023 – Set/2025 (998 dias, incluindo Monte Carlo)
- Holdout: Out–Dez/2025 (92 dias, 100% dados reais)

**Resultados em holdout (92 dias reais):**
| Série | MAE | vs Prophet |
|---|---|---|
| **Total** | **13.15** | **-44.8%** |
| P2 | 4.38 | - |
| P3 | 11.63 | - |

**Previsões D+1 a D+7:**
| D+1 | D+2 | D+3 | D+4 | D+5 | D+6 | D+7 |
|---|---|---|---|---|---|---|
| 69.1 | 61.1 | 56.5 | 26.0 | 19.0 | 67.2 | 65.0 |

**Output:** `outputs/previsoes_lstm.json`

---

### Notebook 03c — Monte Carlo Adaptativo

**Objetivo:** Combinar múltiplas versões do Prophet com pesos adaptativos baseados no erro de validação.

**Método:** Pesos inversamente proporcionais ao MAE de validação cruzada por horizonte.

| Horizonte | Peso Monte Carlo | Peso Original |
|---|---|---|
| D+1 | 53.9% | 46.1% |
| D+3 | 39.8% | 60.2% |
| D+5 | 33.8% | 66.2% |
| D+7 | 48.1% | 51.9% |

**Output:** `outputs/previsoes_volume_mc.json`

---

### Notebook 07 — KPI de Atingimento OLA

**Objetivo:** Calcular e reportar o atingimento das metas de OLA para uso no dashboard.

**Resultado anual 2025:**

| Prioridade | Jan | Fev | Mar | Abr | Mai | Jun | Jul | Ago | Set | Out | Nov | Dez | **Total** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P2 | 4 | 4 | 3 | 2 | **6*** | 3 | **6*** | 3 | 2 | 2 | **6*** | 1 | **42** |
| P3 | 19 | 23 | 18 | 11 | 15 | **29*** | **24*** | 14 | 9 | 9 | 15 | 20 | **206** |

> `*` = mês acima do limiar SPC (anomalia operacional)

**Outputs:** `outputs/kpi_atingimento.json` · `outputs/kpi_violacoes_mensal.png`

---

## Insights e Recomendações

### Insights Operacionais

1. **Sazonalidade crítica em Julho**
   - Único mês com pico simultâneo em P2 **e** P3
   - Sugestão: investigar causa (manutenções planejadas, aumento de tráfego)
   - Ação preventiva: elevar staffing e capacidade em junho/julho

2. **Operação dentro da meta com folga razoável**
   - P2: 66.7% da cota utilizada (margem de +21 violações)
   - P3: 73.6% da cota utilizada (margem de +74 violações)
   - Sinal positivo, mas proximidade ao limiar em alguns meses exige monitoramento

3. **Incidentes recorrentes são um problema desproporcional**
   - Taxa de violação 4.7% vs 0.6% em incidentes únicos (7.8× maior)
   - Top 10 descrições cobrem 28% do volume total
   - Oportunidade: automação de resolução para os padrões mais frequentes

4. **Lags de volume são features preditivas relevantes**
   - lag_1d melhora o Prophet em até 8% no MAE de D+6
   - Indica que o volume do dia anterior é sinal do volume do próximo dia

5. **LSTM supera Prophet em 44.8%**
   - MAE holdout 92 dias: 13.15 vs 23.8 (Prophet)
   - Recomendado para previsões de médio-longo prazo quando histórico disponível

6. **Subcategorias têm a maior correlação com violação**
   - Cramér's V = 0.32 — maior que qualquer outra variável categórica
   - Categorias de infraestrutura apresentam 3.2× mais violações

### Recomendações Técnicas

- Usar **ensemble Prophet v5+v6** para previsões D+1–D+7 (produção atual)
- Usar **LSTM** como validação paralela e para análise de tendência de médio prazo
- Aplicar **SMOTE** apenas no treino ao implementar XGBoost (nb04)
- **Nunca usar acurácia** como métrica principal (classificador "tudo NÃO" teria 99%)
- Métricas corretas: Recall, F1-Score, ROC-AUC, Precision-Recall AUC

---

## Status dos Notebooks

| Notebook | Descrição | Status |
|---|---|---|
| `01_eda.ipynb` | Análise Exploratória de Dados | ✅ Completo |
| `02_feature_engineering.ipynb` | Feature Engineering + Export Parquet | ✅ Completo |
| `03_prophet_volume.ipynb` | Prophet D+1/D+7 ensemble v5+v6 | ✅ Completo |
| `03b_monte_carlo_seed.ipynb` | Monte Carlo com seed fixo | ✅ Completo |
| `03c_prophet_monte_carlo.ipynb` | Ensemble Monte Carlo adaptativo | ✅ Completo |
| `03d_lstm.ipynb` | LSTM 2-layer (hidden=128) | ✅ Completo |
| `04_xgboost_ola_risk.ipynb` | XGBoost — classificação risco OLA | ⚙️ Em desenvolvimento |
| `05_kmeans_clusters.ipynb` | K-Means — padrões recorrentes | ⚙️ Em desenvolvimento |
| `06_shap_interpretability.ipynb` | SHAP — feature importance | ⚙️ Em desenvolvimento |
| `07_kpi_projection.ipynb` | Projeção anual KPI + metas SPC | ✅ Completo |

## Status dos Outputs

| Arquivo | Conteúdo | Status |
|---|---|---|
| `outputs/previsoes_volume.json` | Previsões Prophet ensemble D+1–D+7 | ✅ Gerado |
| `outputs/previsoes_volume_mc.json` | Previsões Monte Carlo adaptativo | ✅ Gerado |
| `outputs/previsoes_lstm.json` | Previsões LSTM D+1–D+7 | ✅ Gerado |
| `outputs/kpi_atingimento.json` | Metas SPC e atingimento real 2025 | ✅ Gerado |
| `outputs/risco_ola.json` | Score de risco por incidente (XGBoost) | ⚙️ Pendente |
| `outputs/clusters.json` | Segmentação K-Means | ⚙️ Pendente |

---

## Dashboard — Rotas

| Rota | Público | Conteúdo |
|---|---|---|
| `/gestao` | Gestores | Saúde geral · R$ em risco · tendência global |
| `/monitoramento` | Geral | Heatmap de risco · alertas · série temporal |
| `/tecnico` | DevOps / SRE | Métricas brutas · drill-down · SHAP values |
| `/financeiro` | Gestores | Exposição financeira · projeção KPI anual |

---

## Prazos FIAP

| Sprint | Entrega | Data |
|---|---|---|
| Sprint 1 | Apresentação executiva (PowerPoint) | 12/04/2026 |
| Sprint 2 | Arquitetura + EDA + protótipos (PowerPoint) | 17/05/2026 |
| Sprint 3 | MVP funcional (link da aplicação) | A definir |
| Sprint 4 | Apresentação final + pitch (Banca + YouTube) | NEXT 2026 |

---

*Documento gerado automaticamente em 2026-04-01 — Predictfy × Locaweb*
