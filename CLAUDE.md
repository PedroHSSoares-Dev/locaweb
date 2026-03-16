# CLAUDE.md — Predictfy × Locaweb

> Contexto completo do projeto para consulta em qualquer conversa futura.

---

## 1. Identidade do Projeto

| Campo | Valor |
|---|---|
| **Nome** | Predictfy × Locaweb — AIOps Infra Predict |
| **Competição** | FIAP Enterprise Challenge 2026 |
| **Turma** | 2TSCPW |
| **Parceiro** | Locaweb |
| **Tema** | AIOps — Previsão de Incidentes e Tendências Operacionais |
| **Integrante principal** | Pedro (RM-562283) — GitHub: @PedroHSSoares-Dev |

---

## 2. Contexto de Negócio (CRÍTICO)

### Dataset
- **Fonte:** Sistema ITSM da Locaweb
- **Volume:** 122.543 incidentes (jan/2023–dez/2025)
- **Arquivo local:** `data/raw/LW-DATASET.xlsx`
- **Colunas-chave:** `Número`, `Aberto`, `Resolvido`, `Encerrado`, `Duração` (segundos), `Prioridade`, `Status`, `Entrou para KPI?`, `KPI Violado?`, `Produto`, `Categoria`, `Subcategoria`, `Grupo designado`, `Aberto por`, `Incidente Pai`, `Código de fechamento`

### Subset KPI
- Filtro: `Entrou para KPI? == SIM`
- **~25.600 incidentes** (P2 e P3 apenas)
- P1 tem 1 caso (irrelevante), P5 tem 333 (não entram para KPI)

### OLAs (Prazos de Resolução)
| Prioridade | Label | OLA | Segundos |
|---|---|---|---|
| P2 | Alta | 4 horas | 14.400s |
| P3 | Média | 12 horas | 43.200s |

### Metas Anuais de Violações
| Prioridade | Meta (violações/ano) | 2025 Real | Status |
|---|---|---|---|
| P2 | 36 a 39 | 42 | ❌ Fora da meta |
| P3 | 231 a 263 | 196 | ✅ Dentro da meta |

### Target (variável alvo dos modelos)
```python
target_ola = (Duração > OLA_por_prioridade).astype(int)
# 1 = KPI violado, 0 = KPI não violado
```
- `KPI Violado?` no dataset é 100% consistente com `Duração > OLA` (verificado na EDA)
- **Desbalanceamento:** ~248 violações SIM vs ~25.352 NAO → razão 1:102

---

## 3. Regras Críticas de Modelagem

### Data Leakage — NÃO usar como features:
| Coluna | Motivo |
|---|---|
| `Duração` | Só conhecida após resolução |
| `Resolvido` | Só preenchida após resolução |
| `Encerrado` | Só preenchida após encerramento |
| `Código de fechamento` | Só definido ao fechar |
| `Solução` | Só registrada ao resolver |
| `KPI Violado?` | É o próprio target |

### Desbalanceamento
- **Nunca usar acurácia** como métrica (classificador "tudo NAO" teria 99%)
- **Métricas corretas:** Recall (capturar violações), F1-Score, ROC-AUC, Precision-Recall AUC
- **SMOTE:** aplicar SOMENTE no conjunto de treino, JAMAIS no teste/validação
- Alternativa: `scale_pos_weight` do XGBoost

### Nulos de Produto/Categoria
- ~64% do dataset total tem `Produto` nulo, mas concentrado em incidentes "Sem Intervenção" (não entram para KPI)
- Estratégia: preencher com `"DESCONHECIDO"` — ausência é sinal preditivo (MNAR)
- Não usar imputação por moda ou KNN

---

## 4. Features do Modelo (Notebook 02)

O arquivo `data/processed/incidents_features.parquet` contém:

| Feature | Tipo | Origem |
|---|---|---|
| `hora` | Numérica | `Aberto.dt.hour` |
| `dia_semana` | Numérica (0=Seg) | `Aberto.dt.dayofweek` |
| `mes` | Numérica | `Aberto.dt.month` |
| `trimestre` | Numérica | `Aberto.dt.quarter` |
| `dia_mes` | Numérica | `Aberto.dt.day` |
| `semana_ano` | Numérica | `Aberto.dt.isocalendar().week` |
| `is_horario_comercial` | Binária | hora entre 8-18 e não fim de semana |
| `is_fim_de_semana` | Binária | dia_semana >= 5 |
| `is_segunda_terca` | Binária | dia_semana in [0,1] |
| `periodo_dia` | Ordinal | 0=madrugada, 1=manhã, 2=tarde, 3=noite |
| `lag_1d` | Numérica | volume de incidentes no dia anterior |
| `lag_7d` | Numérica | volume de incidentes 7 dias antes |
| `rolling_7d` | Numérica | média móvel 7 dias |
| `rolling_30d` | Numérica | média móvel 30 dias |
| `prioridade_bin` | Binária | P2=1, P3=0 |
| `produto_enc` | Label Encoded | Produto (nulos → "DESCONHECIDO") |
| `categoria_enc` | Label Encoded | Categoria |
| `subcategoria_enc` | Label Encoded | Subcategoria |
| `grupo_enc` | Label Encoded | Grupo designado |
| `aberto_por_enc` | Label Encoded | Aberto por |
| `produto_freq` | Frequency Encoded | Produto |
| `grupo_freq` | Frequency Encoded | Grupo designado |
| `mes_sin`, `mes_cos` | Cíclicas | Encoding senoidal do mês |
| `target_ola` | Binária (TARGET) | Duração > OLA |

---

## 5. Arquitetura da Solução

```
Dataset ITSM (XLSX)
       ↓
Preparação (Python / pandas)
  └─ limpeza · feature engineering · targets OLA
       ↓
┌─────────────────────────────────────────────┐
│              Modelos de ML                   │
│  Prophet        XGBoost          K-Means     │
│  D+1/D+7        risco OLA        clusters    │
│  (nb03) ✅      (nb04) ❌        (nb05) ❌   │
└─────────────────────────────────────────────┘
       ↓
JSONs estáticos (outputs/)
  ├── previsoes_volume.json ✅
  ├── risco_ola.json ❌
  ├── clusters.json ❌
  └── kpi_atingimento.json ❌
       ↓
  ┌────────────────┬──────────────┐
  │ Dashboard React│   Power BI   │
  │ (frontend/) ✅ │  (pendente)  │
  └────────────────┴──────────────┘
       ↓
  Chatbot (Gemini Flash + Pro) ❌ pendente
```

---

## 6. Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Modelos ML | Prophet · XGBoost · scikit-learn · SHAP · imbalanced-learn |
| Dados | pandas · numpy · openpyxl · pyarrow |
| Frontend | React + Vite · Recharts · react-router-dom · lucide-react |
| Chatbot | Gemini 2.5 Flash (roteador) · Gemini 2.5 Pro (analista) |
| Deploy | Vercel (frontend) · GitHub Actions (pipeline ML) |
| Entregável FIAP | Power BI |

---

## 7. Status dos Notebooks

| Notebook | Descrição | Status |
|---|---|---|
| `01_eda.ipynb` | Análise Exploratória de Dados | ✅ Criado |
| `02_feature_engineering.ipynb` | Feature Engineering + Export Parquet | ✅ Criado |
| `03_prophet_volume.ipynb` | Prophet D+1/D+7 com ensemble v5/v6 | ✅ Criado |
| `04_xgboost_ola.ipynb` | XGBoost — classificação risco OLA | ❌ Pendente |
| `05_kmeans_clusters.ipynb` | K-Means — padrões recorrentes | ❌ Pendente |
| `06_shap_explicabilidade.ipynb` | SHAP — feature importance | ❌ Pendente |
| `07_kpi_projection.ipynb` | Projeção anual de KPI atingimento | ❌ Pendente |

---

## 8. Status do Código Python (`src/`)

Todos os scripts de produção estão **pendentes**:
- `src/data/loader.py` · `preprocessor.py`
- `src/models/prophet_model.py` · `xgboost_model.py` · `kmeans_model.py`
- `src/outputs/json_generator.py`
- `src/pipeline.py` (orquestrador)

---

## 9. Dashboard — Rotas e Perfis

| Rota | Público-alvo | Conteúdo |
|---|---|---|
| `/gestao` | Gestores | Saúde geral · R$ em risco · tendência global |
| `/monitoramento` | Geral | Heatmap de risco · alertas · série temporal |
| `/tecnico` | DevOps/SRE | Métricas brutas · drill-down · SHAP values |
| `/financeiro` | Gestores | Exposição financeira · projeção KPI anual |

---

## 10. Chatbot — Arquitetura

- **LLM 1 — Gemini 2.5 Flash:** roteador. Responde perguntas simples (~1s). Escala para LLM 2 quando necessário.
- **LLM 2 — Gemini 2.5 Pro:** analista sênior. Recebe contexto expandido com dados históricos e outputs dos modelos.

---

## 11. Prazos dos Sprints (FIAP)

| Sprint | Entrega | Data |
|---|---|---|
| Sprint 1 | Apresentação executiva (PowerPoint) | 12/04/2026 |
| Sprint 2 | Arquitetura + EDA + protótipos (PowerPoint) | 17/05/2026 |
| Sprint 3 | MVP funcional (link da aplicação) | A definir |
| Sprint 4 | Apresentação final + pitch (Banca + YouTube) | NEXT 2026 |

---

## 12. Arquivos Importantes do Projeto

| Arquivo | Localização | Descrição |
|---|---|---|
| Dataset bruto | `data/raw/LW-DATASET.xlsx` | Nunca commitar |
| Dataset processado | `data/processed/incidents_features.parquet` | Gerado pelo nb02 |
| Previsões volume | `outputs/previsoes_volume.json` | Gerado pelo nb03 |
| Regras do challenge | `../projeto-locaweb/Regras_Gerais_Challenge_Locaweb_...pdf` | Referência FIAP |
| Dicionário de dados | `../projeto-locaweb/lw-dataset/Dicionário de Dados - v2.docx` | Referência colunas |
| Template Sprint 1 | `../projeto-locaweb/01Template_IDEACAO_...pptx` | Entrega 12/04 |
| Template Sprint 2 | `../projeto-locaweb/02Template_Arquitetura_...pptx` | Entrega 17/05 |

---

## 13. Achados Críticos da EDA

1. P2 só aparece no subset KPI a partir de 2025 → dados limitados para treino
2. P2 violou a meta em 2025 (42 violações vs meta 36-39) → problema real e relevante
3. Monitoramento automático abre a maioria dos incidentes
4. Nulos de Produto/Categoria são MNAR — concentrados em "Sem Intervenção"
5. `KPI Violado?` é 100% consistente com `Duração > OLA` → target confiável
6. Sazonalidade intra-dia evidente: horário comercial concentra incidentes
7. Desbalanceamento 1:102 → SMOTE obrigatório + métricas corretas
