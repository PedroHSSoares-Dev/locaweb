# Dataset — Predictfy × Locaweb

## Fonte e Volume

| Campo | Valor |
|---|---|
| Sistema | ITSM da Locaweb |
| Período | jan/2023 – dez/2025 |
| Volume total | 122.543 incidentes |
| Arquivo | `data/raw/LW-DATASET.xlsx` (gitignored) |

## Subset KPI

Filtro: `Entrou para KPI? == SIM` → somente P2 e P3.

| Prioridade | Label | Volume KPI | OLA | Segundos |
|---|---|---|---|---|
| P1 | Crítica | 1 (irrelevante) | — | — |
| P2 | Alta | ~300 | 4 horas | 14.400 |
| P3 | Média | ~25.300 | 12 horas | 43.200 |
| P5 | Baixa | 333 | não entra KPI | — |

**Total subset KPI:** ~25.600 incidentes (P2 + P3)

## Colunas Principais

| Coluna | Tipo | Notas |
|---|---|---|
| `Número` | String | ID único do incidente |
| `Aberto` | Datetime | Abertura — base para features temporais |
| `Resolvido` | Datetime | **Leakage** — nunca usar como feature |
| `Encerrado` | Datetime | **Leakage** — nunca usar como feature |
| `Duração` | Int (segundos) | **Leakage** — só conhecida após resolução |
| `Prioridade` | Categórica | `2 - Alta`, `3 - Média` no subset KPI |
| `Status` | Categórica | `Sem Intervenção` = automático, não entra KPI |
| `Entrou para KPI?` | SIM/NÃO | Filtro para subset |
| `KPI Violado?` | SIM/NÃO | **Target** — ground truth de negócio |
| `Produto` | Categórica | ~64% nulos no total (MNAR) |
| `Categoria` | Categórica | ~63% nulos no total (MNAR) |
| `Subcategoria` | Categórica | maior Cramér's V (0.32) com target |
| `Grupo designado` | Categórica | Team responsável |
| `Aberto por` | Categórica | Monitoramento vs manual |
| `Código de fechamento` | Categórica | **Leakage** — só definido ao fechar |

## Metas Anuais de Violações

| Prioridade | Meta mín | Meta máx | 2025 real | Status |
|---|---|---|---|---|
| P2 | 36 | 39 | 42 | ❌ Fora da meta |
| P3 | 231 | 263 | 196 | ✅ Dentro da meta |

## Target

```python
target_ola = (kpi["KPI Violado?"] == "SIM").astype(int)
# 1 = violou OLA, 0 = não violou
```

> O campo `KPI Violado?` reflete regras de negócio adicionais (pausas de SLA, exceções
> aprovadas). Não é equivalente a `Duração > OLA` — há ~3.399 divergências. Use sempre
> `KPI Violado?` como ground truth.

**Desbalanceamento:** ~248 SIM vs ~25.340 NÃO → razão 1:102

## Regras Anti-Leakage

Colunas que **nunca** podem ser usadas como features (só disponíveis pós-resolução):

```
Duração, Resolvido, Encerrado, Código de fechamento, Solução, KPI Violado?
```

## Tratamento de Nulos

| Coluna | % nulos no KPI | Estratégia |
|---|---|---|
| `Produto` | ~0.1% | `fillna("DESCONHECIDO")` |
| `Categoria` | ~0.1% | `fillna("DESCONHECIDO")` |
| `Subcategoria` | ~63% | `fillna("DESCONHECIDO")` — ausência é sinal MNAR |

> **MNAR** (Missing Not at Random): ausência de Subcategoria concentra-se em incidentes
> "Sem Intervenção". Tratar como categoria própria, nunca imputar por moda/KNN.

## Achados Críticos da EDA

1. P2 só aparece no subset KPI a partir de 2025 → dados limitados para treino XGBoost
2. Subcategoria tem maior Cramér's V com target (0.32) — feature mais preditiva
3. Hora do dia NÃO prediz violação (Cramér's V ≈ 0), mas prediz volume (Prophet)
4. Monitoramento automático abre a maioria dos incidentes
5. Outliers de Duração P3: ~13% acima de 1.5×IQR (pausas de SLA aprovadas)
