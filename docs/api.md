# API — Predictfy × Locaweb

**Base URL:** `http://localhost:8000/api`  
**Framework:** FastAPI + Uvicorn  
**Início:** `uvicorn api.main:app --reload`

Todos os endpoints retornam JSON. Quando um modelo ainda não foi treinado / seu JSON
não existe em `outputs/`, a resposta segue o padrão:

```json
{ "disponivel": false, "mensagem": "..." }
```

---

## Módulo: Previsões de Volume

Hierarquia de modelos (melhor → fallback):
1. **LSTM v2** — MAE holdout = 13.15 incidentes/dia
2. **Prophet MC ensemble** — MAE holdout = 23.80
3. **Prophet original** — MAE CV = 17.06

### `GET /api/previsoes/modelos`

Status de disponibilidade de cada modelo e qual está sendo usado.

**Response:**
```json
{
  "lstm":             true,
  "prophet_mc":       true,
  "prophet_original": true,
  "modelo_ativo":     "lstm_v2",
  "mae_modelo_ativo": 13.15
}
```

---

### `GET /api/previsoes`

JSON completo do melhor modelo disponível (estrutura varia por modelo).
Use os endpoints normalizados (`/d1`, `/d7`, `/serie`) para formato consistente.

---

### `GET /api/previsoes/d1`

Previsão de volume para **D+1** (amanhã).

**Response:**
```json
{
  "disponivel":   true,
  "total":        87,
  "p2":           14,
  "p3":           73,
  "modelo_usado": "lstm_v2",
  "mae":          13.15
}
```

> `p2` e `p3` retornam `null` se o modelo ativo for LSTM v2 (prevê apenas `total`).

---

### `GET /api/previsoes/d7`

Previsão de volume para **D+7** (7 dias à frente). Mesma estrutura do `/d1`.

---

### `GET /api/previsoes/serie`

Série completa **D+1 a D+7** formatada para gráfico de área.

**Response:**
```json
{
  "disponivel":   true,
  "modelo_usado": "lstm_v2",
  "serie": [
    { "dia": "D+1", "ds": "2026-01-02", "total": 87, "P2": null, "P3": null },
    { "dia": "D+2", "ds": "2026-01-03", "total": 91, "P2": null, "P3": null }
  ]
}
```

---

## Módulo: Risco OLA (XGBoost)

### `GET /api/risco`

JSON completo do modelo XGBoost de risco de violação de OLA.

**Response:**
```json
{
  "disponivel": true,
  "modelo": "xgboost_ola_risk",
  "threshold_otimizado": 0.3072,
  "metricas": {
    "recall_violacao": 0.086,
    "f1_violacao":     0.124,
    "roc_auc":         0.71
  },
  "feature_importance_shap": [
    { "rank": 1, "feature": "subcategoria_enc", "shap_mean_abs": 0.043 }
  ],
  "risco_por_prioridade": {
    "P2": { "n_incidentes": 58,  "taxa_violacao_real": 0.103, "media_prob": 0.21, "pct_alto_risco": 12.1 },
    "P3": { "n_incidentes": 5060,"taxa_violacao_real": 0.008, "media_prob": 0.06, "pct_alto_risco":  0.3 }
  },
  "distribuicao_risco": {
    "baixo":  { "n": 4800, "pct": 93.8 },
    "medio":  { "n":  250, "pct":  4.9 },
    "alto":   { "n":   68, "pct":  1.3 }
  }
}
```

---

### `GET /api/risco/produtos`

Prioridades ordenadas por probabilidade de violação (decrescente).

**Response:**
```json
{
  "disponivel": true,
  "produtos": [
    {
      "produto":          "P2",
      "probViolacao":     21.0,
      "pctAltoRisco":     12.1,
      "nIncidentes":      58,
      "taxaViolacaoReal": 0.103
    }
  ]
}
```

Semáforo do dashboard:
- `probViolacao > 30%` → 🔴 ALTO RISCO
- `probViolacao > 15%` → 🟡 ATENÇÃO
- `probViolacao ≤ 15%` → 🟢 NORMAL

---

### `GET /api/risco/grupos`

Grupos de atendimento ordenados por taxa histórica de violação (decrescente).

**Response:**
```json
{
  "disponivel": true,
  "grupos": [
    { "grupo": "Team07", "taxaViolacao": 8.94 }
  ]
}
```

---

## Módulo: Clusters K-Means

### `GET /api/clusters`

Segmentação K-Means dos padrões de incidentes KPI.

**Response:**
```json
{
  "disponivel": true,
  "k": 5,
  "metricas": {
    "silhouette": 0.1838,
    "calinski_harabasz": 4083.4,
    "davies_bouldin": 1.7138
  },
  "clusters": [
    {
      "id":           0,
      "label":        "Alta Prioridade P2-dominante",
      "tamanho":      1200,
      "taxaViolacao": 8.2,
      "perfil": {
        "hora_media":   10.5,
        "periodo_dia":  "manhã",
        "prioridade":   "P2"
      }
    }
  ]
}
```

---

## Módulo: KPI Operacional

### `GET /api/kpi?periodo={mes|trimestre|ano}`

KPI de atingimento das metas de OLA.

**Parâmetro `periodo`:**
| Valor | Meses incluídos |
|---|---|
| `ano` (padrão) | Jan–Dez |
| `trimestre` | Out, Nov, Dez (Q4) |
| `mes` | Dez apenas |

**Response:**
```json
{
  "disponivel":     true,
  "metodologia":    "meta_anual_distribuida",
  "gerado_em":      "2026-05-09T12:00:00",
  "periodo_filtro": "ano",
  "P2": {
    "violacoesAno":   42,
    "metaAnual":      39,
    "metaMensal":     3.25,
    "pctUtilizado":   107.7,
    "margemRestante": -3,
    "pctAtingimento": 92,
    "status":         "atencao"
  },
  "P3": {
    "violacoesAno":   196,
    "metaAnual":      263,
    "metaMensal":     21.9,
    "pctUtilizado":   74.5,
    "margemRestante": 67,
    "pctAtingimento": 100,
    "status":         "dentro_meta"
  },
  "por_mes": {
    "P2": { "1": 4, "2": 4, "3": 3, ... },
    "P3": { "1": 19, "2": 21, "3": 16, ... }
  }
}
```

**Status possíveis:**
| Status | Condição |
|---|---|
| `dentro_meta` | violações ≤ orçamento |
| `atencao` | orçamento < violações ≤ 1.5× orçamento |
| `critico` | violações > 1.5× orçamento |

---

## Módulo: Histórico ITSM

Dados históricos estáticos extraídos diretamente do `LW-DATASET.xlsx`.
Não dependem de modelos — sempre disponíveis.

### `GET /api/historico/mensal?periodo={mes|trimestre|ano}`

Série mensal de 2025 com volume e violações por prioridade.

**Response:**
```json
[
  { "mes": "Jan", "P2": 552, "P3": 1805, "total": 2357, "violP2": 4, "violP3": 19 },
  { "mes": "Fev", "P2": 470, "P3": 1812, "total": 2282, "violP2": 4, "violP3": 21 }
]
```

---

### `GET /api/historico/diario?periodo={mes|trimestre|ano}`

Volume diário de incidentes KPI — dezembro/2025 (02/12–31/12).
Conecta o histórico à janela de previsão no gráfico de área.

**Response:**
```json
[
  { "dia": "02/12", "P2": 17, "P3": 62 },
  { "dia": "03/12", "P2":  9, "P3": 59 }
]
```

---

### `GET /api/historico/sazonalidade`

Heatmap de concentração de incidentes por hora × dia da semana (2023–2025).

**Response:**
```json
[
  {
    "dia": "Seg",
    "horas": [85, 56, 28, 56, 37, 54, 35, 47, 177, 316, 355, 384,
              334, 268, 275, 367, 317, 267, 171, 129, 125, 172, 135, 75]
  }
]
```

`horas[i]` = volume acumulado na hora `i` (0–23).  
Pico: quinta-feira às 15h (420 incidentes acumulados).

---

## Módulo: Contexto Chatbot

### `GET /api/context`

Snapshot operacional completo para uso como contexto do chatbot Gemini.

**Response:**
```json
{
  "gerado_em": "2026-05-09T12:00:00Z",
  "previsoes": {
    "disponivel": true,
    "modelo_usado": "lstm_v2",
    "d1": { "total": 87, "p2": null, "p3": null },
    "d7": { "total": 91, "p2": null, "p3": null }
  },
  "risco": {
    "disponivel": true,
    "top_produtos": [...],
    "top_grupos": [...]
  },
  "clusters": {
    "disponivel": true,
    "k": 5
  },
  "kpi": {
    "disponivel": true,
    "P2": { "status": "atencao", "pctUtilizado": 107.7 },
    "P3": { "status": "dentro_meta", "pctUtilizado": 74.5 }
  },
  "operacional": {
    "ola_targets":    { "P2": "4h", "P3": "12h" },
    "metas_anuais":   { "P2": "36-39", "P3": "231-263" },
    "violacoes_2025": { "P2": 42, "P3": 196 }
  }
}
```

Campos com modelos indisponíveis retornam `"disponivel": false`.

---

## Rotas do Dashboard

| Rota | Público-alvo | Endpoints consumidos |
|---|---|---|
| `/gestao` | Gestores | `/historico/mensal`, `/kpi`, `/previsoes/d1` |
| `/monitoramento` | Geral | `/historico/diario`, `/previsoes/serie`, `/historico/sazonalidade`, `/risco/produtos` |
| `/tecnico` | DevOps/SRE | `/risco`, `/risco/grupos`, `/clusters` |
| `/financeiro` | Gestores | `/kpi`, `/historico/mensal` |
| Chatbot | — | `/context` |
