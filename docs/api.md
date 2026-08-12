# API — Predictfy × Locaweb

**Base URL:** `http://localhost:8000/api`  
**Framework:** FastAPI + Uvicorn  
**Início:** `uvicorn api.main:app --reload`

Todos os endpoints retornam JSON. Quando um modelo ainda não foi treinado / seu JSON
não existe em `outputs/`, a resposta segue o padrão:

```json
{ "disponivel": false, "mensagem": "..." }
```

## Chatbot operacional

As rotas abaixo exigem `Authorization: Bearer <sessão Predictfy>`.

- `POST /api/chat/stream`: NDJSON com `conversation_id` e `analysis_mode` (`fast` ou `deep`).
- `POST /api/chat`: versão não streaming com fontes, uso, cache e `response_id` estruturados.
- `POST /api/chat/feedback`: registra `up`/`down` somente para uma resposta recente do mesmo usuário.
- `DELETE /api/chat/conversation`: apaga a memória curta de uma conversa.
- `GET/POST /api/chat/conversations`: pesquisa/lista ou cria uma conversa persistente.
- `GET/PATCH/DELETE /api/chat/conversations/{id}`: restaura, renomeia, fixa, troca contexto ou exclui uma conversa.
- `GET /api/chat/metrics`: telemetria agregada sem prompts ou respostas.

O cache inclui a versão do contexto, prompt, provider e modelo. Redis/Valkey é opcional
via `CHAT_REDIS_URL`; sem ele, cache, memória e rate limit continuam locais ao processo.
O arquivo completo usa SQLite por padrão e aceita PostgreSQL por `CHAT_DATABASE_URL`.

---

## Módulo: Previsões de Volume

Seleção validada no mesmo rolling origin de Out–Dez/2025:
1. **Baseline sazonal** — MAE médio D1–D7 Total = 12,46
2. **LSTM v2** — MAE médio D1–D7 Total = 21,19
3. **Prophet MC** — MAE médio D1–D7 Total = 25,61
4. **Prophet original** — MAE médio D1–D7 Total = 47,66

O modelo ativo vem de `comparacao_modelos.json`; a disponibilidade isolada não
é tratada como prova de superioridade.

### `GET /api/previsoes/modelos`

Status de disponibilidade de cada modelo e qual está sendo usado.

**Response:**
```json
{
  "lstm":             true,
  "baseline_sazonal": true,
  "prophet_mc":       true,
  "prophet_original": true,
  "modelo_ativo":     "baseline_sazonal_7d",
  "mae_modelo_ativo": 12.46,
  "comparacao": { "comparaveis": true, "protocolo": "rolling_origin_2025Q4_D1_D7" }
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
  "total":        44,
  "p2":           8,
  "p3":           36,
  "modelo_usado": "baseline_sazonal_7d",
  "mae":          12.70,
  "reconciliado": false,
  "valores_brutos": null
}
```

> As séries são treinadas independentemente. A API preserva o Total validado e
> reconcilia P2/P3 proporcionalmente para que a saída pública feche por soma.

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
    { "dia": "D+1", "ds": "2026-01-01", "total": 44, "P2": 10, "P3": 34, "reconciliado": true },
    { "dia": "D+2", "ds": "2026-01-02", "total": 44, "P2": 10, "P3": 34, "reconciliado": true }
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

Produtos ordenados pela taxa histórica observada de violação. Segmentos com
menos de 100 incidentes ou 10 violações são suprimidos.

**Response:**
```json
{
  "disponivel": true,
  "produtos": [
    {
      "produto": "produto-agregado",
      "nIncidentes": 1200,
      "violacoes": 18,
      "taxaViolacaoReal": 1.5,
      "intervaloConfianca95": [0.95, 2.36],
      "pctP2": 22.1
    }
  ]
}
```

Nenhum score individual, identificador de incidente ou conteúdo livre é exposto.

---

### `GET /api/risco/grupos`

Grupos de atendimento ordenados por taxa histórica de violação (decrescente).

**Response:**
```json
{
  "disponivel": true,
  "grupos": [
    { "grupo": "grupo-agregado", "taxaViolacao": 2.1, "nIncidentes": 800,
      "violacoes": 17, "intervaloConfianca95": [1.31, 3.39], "pctP2": 20.0 }
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
    "metaAnual":      37.5,
    "metaMensal":     3.12,
    "pctUtilizado":   112.0,
    "margemRestante": -4.5,
    "pctAtingimento": 89,
    "tendencia":      "atencao"
  },
  "P3": {
    "violacoesAno":   196,
    "metaAnual":      247.0,
    "metaMensal":     20.58,
    "pctUtilizado":   79.4,
    "margemRestante": 51.0,
    "pctAtingimento": 100,
    "tendencia":      "dentro_da_meta"
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

Snapshot operacional canônico para o chatbot local e outras integrações.

**Response:**
```json
{
  "timestamp": "2026-08-06T12:00:00Z",
  "previsoes": {
    "disponivel": true,
    "modelo_ativo": "baseline_sazonal_7d",
    "D1": { "total": 44, "p2": 8, "p3": 36, "reconciliado": false },
    "D7": { "total": 40, "p2": 9, "p3": 31, "reconciliado": true }
  },
  "risco": {
    "disponivel": true,
    "por_prioridade": { "P2": {}, "P3": {} },
    "top_fatores": []
  },
  "clusters": {
    "disponivel": true,
    "resumo": { "n_clusters": 5, "mais_critico": { "id": 4 } }
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

## Módulo: Chatbot híbrido

| Método | Endpoint | Função |
|---|---|---|
| `POST` | `/api/chat/session` | Valida o access token Microsoft Entra, vincula/consulta o diretório autorizado e emite a sessão Predictfy |
| `GET` | `/api/chat/session` | Valida a sessão atual e retorna identidade, papel e capacidades públicas |
| `DELETE` | `/api/chat/session` | Revoga a versão atual da sessão e libera recursos locais quando o provider usa Ollama |
| `GET` | `/api/chat/status` | Verifica o provider e o modelo configurados |
| `POST` | `/api/chat` | Resposta completa, útil para integrações e testes |
| `POST` | `/api/chat/stream` | Eventos NDJSON `meta`, `status`, `reasoning`, `token`, `done` ou `error` |
| `GET` | `/api/chat/conversations` | Lista e pesquisa conversas do usuário atual |
| `POST` | `/api/chat/conversations` | Cria uma conversa com o contexto atual do dashboard |
| `GET` | `/api/chat/conversations/{id}` | Restaura metadados e mensagens completas |
| `PATCH` | `/api/chat/conversations/{id}` | Renomeia, fixa ou atualiza o contexto anexado |
| `DELETE` | `/api/chat/conversations/{id}` | Exclui permanentemente a conversa do usuário |

## Módulo: Administração de acessos

Todos os endpoints abaixo exigem uma sessão Predictfy ativa com papel `admin`.
O frontend nunca recebe as chaves imutáveis `oid`/`tid` e nunca acessa o
Supabase diretamente.

| Método | Endpoint | Função |
|---|---|---|
| `GET` | `/api/admin/users` | Lista o diretório autorizado; aceita busca e filtros de papel/status |
| `POST` | `/api/admin/users` | Cria um convite por e-mail com papel `member` ou `admin` |
| `PATCH` | `/api/admin/users/{id}` | Altera papel ou status com controle otimista por `version` |
| `DELETE` | `/api/admin/users/{id}` | Remove o acesso de forma lógica, revoga sessões e preserva a auditoria |
| `GET` | `/api/admin/audit` | Lista eventos append-only de administração e vinculação |
| `GET` | `/api/admin/preflight` | Verifica artefatos, registro de modelos, reconciliação, bancos e provider antes de uma demonstração/deploy |

## Módulo: Governança de modelos

### `GET /api/models/registry`

Retorna o registro canônico versionado. Há exatamente um modelo `active` por
tarefa servida; modelos `shadow` ficam visíveis para comparação, mas não alteram
previsões, decisões ou filas automaticamente.

O registro também documenta protocolo, janela de validação, métricas,
capacidades e limitações. A política de promoção exige validação temporal
comparável e evidência prospectiva.

## Módulo: Fila operacional

Todos os endpoints exigem uma sessão Predictfy ativa. A fila fecha o ciclo entre
um sinal do modelo, a investigação humana e o resultado observado.

| Método | Endpoint | Função |
|---|---|---|
| `GET` | `/api/operations/alerts` | Lista alertas com filtros de status/prioridade e resumo agregado |
| `POST` | `/api/operations/alerts` | Abre investigação manual ou vinculada a um modelo autorizado pelo registro |
| `PATCH` | `/api/operations/alerts/{id}` | Atualiza responsável, ação, resultado e status com controle otimista por `version` |
| `GET` | `/api/operations/alerts/{id}/audit` | Lista o histórico append-only do alerta |

Um alerta só pode ir para `resolved` após registrar ação tomada e resultado
observado. `false_positive` exige justificativa. O score de origem continua sendo
um sinal de ranking, nunca uma probabilidade calibrada.

Os endpoints de consulta exigem `Authorization: Bearer <token>`. Somente quick actions factuais explicitamente reconhecidas são respondidas a partir de `outputs/`, sem custo de LLM. Toda pergunta natural, estratégica, futura, comparativa ou ambígua prefere o agente `gpt-5.6-luna` quando `CHAT_LLM_PROVIDER=openai`, ou `OLLAMA_MODEL` quando o fallback local está ativo.

O provider OpenAI usa a Responses API com function calling, `reasoning.effort=low` e chave mantida somente no backend. O agente possui ferramentas read-only para previsões LSTM, projeções Prophet D+1..D+365, simulação de cota, planejamento mensal/trimestral com score auditável, KPIs, XGBoost/SHAP, K-Means e regras operacionais. Chamadas têm schemas estritos, limite de rodadas e retornam somente agregados sanitizados. O ciclo do fallback local é controlado por `OLLAMA_AUTOSTART`, `OLLAMA_PRELOAD_ON_SESSION` e `OLLAMA_STOP_MANAGED_SERVER_ON_LOGOUT`.

O evento `reasoning` contém somente um resumo auditável das evidências e limitações, não a cadeia de pensamento interna do modelo. O evento `done` inclui `elapsed_ms`, usado pela interface para exibir `Worked for X min Y sec`.

---

## Rotas do Dashboard

| Rota | Público-alvo | Endpoints consumidos |
|---|---|---|
| `/gestao` | Gestores | `/historico/mensal`, `/kpi`, `/previsoes/d1` |
| `/monitoramento` | Geral | `/historico/diario`, `/previsoes/serie`, `/historico/sazonalidade`, `/risco/produtos` |
| `/tecnico` | DevOps/SRE | `/risco`, `/risco/grupos`, `/clusters` |
| `/financeiro` | Gestores | `/kpi`, `/historico/mensal` |
| `/modelos` | Geral | `/models/registry`, `/previsoes/modelos`, `/risco`, `/clusters` |
| `/operacoes` | Geral autenticado | `/operations/alerts`, `/models/registry` |
| `/admin` | Administradores | `/admin/users`, `/admin/audit`, `/admin/preflight` |
| Chatbot | — | `/context`, `/chat/session` (`POST`/`DELETE`), `/chat/status`, `/chat`, `/chat/stream` |
