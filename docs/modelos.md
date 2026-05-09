# Modelos de ML — Predictfy × Locaweb

## Visão Geral da Cadeia

```
data/raw/LW-DATASET.xlsx
        │
        ▼
src/data/preprocessor.py
  → data/processed/incidents_features.parquet
        │
        ├──► src/models/xgboost_model.py  → outputs/risco_ola.json
        ├──► src/models/kmeans_model.py   → outputs/clusters.json
        ├──► src/models/kpi_projection.py → outputs/kpi_atingimento.json
        │
        │    (notebooks — geram seus próprios JSONs)
        ├──► notebooks/03_prophet_volume.ipynb → outputs/previsoes_volume.json
        └──► notebooks/03d_lstm.ipynb          → outputs/previsoes_lstm.json
```

Orquestrador completo: `python src/pipeline.py`

---

## 1. Feature Engineering (`src/data/preprocessor.py`)

**Input:** `data/raw/LW-DATASET.xlsx`  
**Output:** `data/processed/incidents_features.parquet` (27 colunas)

### Features geradas

| Grupo | Features |
|---|---|
| Temporais | `hora`, `dia_semana`, `mes`, `trimestre`, `dia_mes`, `semana_ano` |
| Binárias | `is_horario_comercial`, `is_fim_de_semana`, `is_segunda_terca` |
| Ordinal | `periodo_dia` (0=madrugada, 1=manhã, 2=tarde, 3=noite) |
| Lags gerais | `lag_1d`, `lag_7d`, `rolling_7d`, `rolling_30d` |
| Lags por prioridade | `lag_1d_p2`, `lag_1d_p3` |
| Prioridade | `prioridade_bin` (P2=1, P3=0) |
| Label encoded | `produto_enc`, `categoria_enc`, `subcategoria_enc`, `grupo_enc`, `aberto_por_enc` |
| Frequency encoded | `produto_freq`, `grupo_freq` |
| Cíclicas | `mes_sin`, `mes_cos` |
| Target | `target_ola` (1=violou OLA, 0=não violou) |

### Invariantes críticos
- Nulos de Produto/Categoria/Subcategoria → `"DESCONHECIDO"` (MNAR)
- Primeiros 7 dias removidos (lags indisponíveis)
- Assertivas validam ausência de nulos e prioridades inesperadas

---

## 2. XGBoost — Risco OLA (`src/models/xgboost_model.py`)

**Input:** `data/processed/incidents_features.parquet`  
**Output:** `outputs/risco_ola.json`  
**Notebook exploratório:** `notebooks/04_eda_xgboost.ipynb`

### Abordagem
- Dois modelos comparados: **Base** (scale_pos_weight) e **SMOTE** (oversampling)
- Vencedor selecionado por PR-AUC (mais adequado para dados desbalanceados)
- Cross-validation 5-fold estratificado
- Threshold otimizado por F1 (não 0.5)
- SHAP para feature importance

### Hiperparâmetros
```python
n_estimators=300, max_depth=6, learning_rate=0.05
subsample=0.8, colsample_bytree=0.8
tree_method="hist"
```

### Regras anti-leakage
- SMOTE aplicado **somente** no treino, jamais no teste
- Split temporal: 80% treino (cronológico) / 20% teste (mais recentes)
- Features: apenas colunas disponíveis **no momento da abertura** do incidente

### Métricas (2025, test set)
| Métrica | Valor |
|---|---|
| PR-AUC | ≈ 0.048 |
| ROC-AUC | ≈ 0.7+ |
| Recall | configurável via threshold |

> **Nota:** Recall baixo esperado — P2 só aparece em 2025 (dados limitados).
> O modelo é útil para triagem de risco, não para alerta 100% preciso.

### Formato do JSON exportado
```json
{
  "modelo": "xgboost_ola_risk",
  "threshold_otimizado": 0.3072,
  "metricas": { "recall_violacao": ..., "f1_violacao": ..., "roc_auc": ... },
  "feature_importance_shap": [{ "rank": 1, "feature": "...", "shap_mean_abs": ... }],
  "risco_por_prioridade": { "P2": {...}, "P3": {...} },
  "distribuicao_risco": { "baixo": {...}, "medio": {...}, "alto": {...} }
}
```

---

## 3. K-Means — Clustering (`src/models/kmeans_model.py`)

**Input:** `data/processed/incidents_features.parquet`  
**Output:** `outputs/clusters.json`  
**Notebook exploratório:** `notebooks/05_eda_kmeans.ipynb`

### Abordagem
- K avaliado de 2 a 10 com 3 métricas: Silhouette, Calinski-Harabasz, Davies-Bouldin
- Candidatos: apenas K **ímpar** e K ≥ `K_MIN=5` (evita partições simétricas artificiais)
- Seleção por voto majoritário; desempate pelo Silhouette
- Normalização com `StandardScaler` antes do clustering
- PCA 2D para visualização

### Features de clustering
```
hora, dia_semana, mes, periodo_dia,
is_horario_comercial, is_fim_de_semana, prioridade_bin,
lag_1d, rolling_7d, produto_freq, grupo_freq
```

### Resultado típico
- K=5 clusters com Silhouette ≈ 0.18
- Nomes automáticos por perfil: "Alta Prioridade P2-dominante", "Fim de Semana / Noturno", etc.

---

## 4. KPI Projection (`src/models/kpi_projection.py`)

**Input:** `data/raw/LW-DATASET.xlsx`  
**Output:** `outputs/kpi_atingimento.json`  
**Notebook exploratório:** `notebooks/07_eda_kpi.ipynb`

### Lógica de Meta Mensal Dinâmica

Meta anual distribuída igualmente (meta_anual/12). Se um mês estoura seu orçamento,
os meses seguintes têm orçamento menor para compensar:

```python
def calcular_meta_ajustada(violacoes_por_mes, meta_anual, mes_atual):
    violacoes_ate_agora = sum(violacoes_por_mes[:mes_atual])
    meses_restantes = 12 - mes_atual
    meta_restante = meta_anual - violacoes_ate_agora
    return max(0.0, meta_restante / meses_restantes)
```

**Exemplo:** setembro estoura → outubro/novembro/dezembro têm orçamento menor.

### Status possíveis por mês/ano
| Status | Condição |
|---|---|
| `ok` | violações ≤ orçamento |
| `atencao` | orçamento < violações ≤ 1.5× orçamento |
| `critico` | violações > 1.5× orçamento |
| `fora_meta` (anual) | total > meta_max × 1.2 |

---

## 5. Prophet — Volume D+1/D+7 (pendente conversão para .py)

**Notebook:** `notebooks/03_prophet_volume.ipynb`  
**Output:** `outputs/previsoes_volume.json`

> Ainda como notebook. Conversão para `src/models/prophet_model.py` é pendente (Sprint 3).

---

## 6. LSTM (pendente conversão para .py)

**Notebook:** `notebooks/03d_lstm.ipynb`  
**Output:** `outputs/previsoes_lstm.json`

> Ainda como notebook. Conversão para `src/models/lstm_model.py` é pendente (Sprint 3).
