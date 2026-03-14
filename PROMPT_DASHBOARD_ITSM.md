# Prompt — Predictfy × Locaweb: Reconstrução completa da Dashboard ITSM

## Contexto

Você está reconstruindo do zero o frontend de uma dashboard AIOps chamada
**Predictfy × Locaweb** para o FIAP Challenge 2026.

O projeto original foi construído com dados de infraestrutura de servidores
(CPU, RAM, falhas de hardware) — isso estava **errado**. O desafio real da
Locaweb é sobre **ITSM (IT Service Management)**: gestão de tickets de
incidentes, cumprimento de OLA (Operational Level Agreement) e antecipação
de volumes de chamados.

O frontend deve ser **completamente reconstruído** para refletir o contexto
correto, mantendo o mesmo stack técnico e o mesmo dark theme.

---

## Stack (não alterar)

- React + Vite
- Recharts (gráficos)
- react-router-dom (roteamento)
- lucide-react (ícones)
- Fonte: IBM Plex Mono + IBM Plex Sans (Google Fonts, já no index.html)

---

## Design tokens (index.css — não alterar)

```css
:root {
  --bg: #0a0a0a;
  --surface1: #111111;
  --surface2: #181818;
  --surface3: #1f1f1f;
  --border: rgba(255,255,255,0.07);
  --border-md: rgba(255,255,255,0.13);
  --red: #E8002D;
  --red-hover: #ff1744;
  --red-dim: rgba(232,0,45,0.10);
  --orange: #ff6d00;
  --yellow: #ffea00;
  --green: #00e676;
  --text-pri: #f0f0f0;
  --text-sec: #888888;
  --text-muted: #444444;
  --font-mono: 'IBM Plex Mono', monospace;
  --font-sans: 'IBM Plex Sans', sans-serif;
}
```

---

## Contexto do negócio (ESSENCIAL para construir os componentes certos)

A Locaweb opera uma infraestrutura de TI 24x7 gerenciada via ITSM.
Incidentes são registrados como tickets com prioridade P1–P5.
Apenas **P2 (Alta)** e **P3 (Média)** entram nos indicadores de KPI.

**OLA (prazo de resolução):**
- P2: resolução em até **4 horas**
- P3: resolução em até **12 horas**

**Meta anual de violações (100% de atingimento):**
- P2: entre 36 e 39 violações no ano
- P3: entre 231 e 263 violações no ano

**Dado real 2025:**
- P2: 42 violações → acima da meta → KPI P2 não atingido (~79%)
- P3: 196 violações → abaixo do limite → KPI P3 atingido com folga (112%)

**Volume diário médio (2025):**
- P2: ~14 incidentes/dia
- P3: ~42 incidentes/dia

**Grupo mais crítico:** Team07 com 8.94% de taxa de violação
**Produto mais crítico:** lsin com 1.93% de taxa de violação

---

## Arquivos que NÃO mudam

- `src/main.jsx` — entry point, não tocar
- `src/index.css` — tokens CSS, não tocar
- `src/App.jsx` — roteamento, não tocar (mantém 4 rotas)
- `src/context/DashboardContext.jsx` — manter, mas trocar `horizon`
  por `filtroAtivo` (string: null | produto | grupo | categoria)
- `src/data/mockData.js` — já foi reescrito com dados ITSM reais,
  não alterar

---

## Arquivos a criar/reescrever completamente

### 1. `src/components/Topbar.jsx`

Header fixo com:
- Logo: `locaweb` em `--font-mono` vermelho + badge `INFRA PREDICT`
- 4 abas de navegação com NavLink + classe CSS `tab`/`tab-active`:
  - Gestão (`/gestao`) com ícone `BarChart2`
  - Monitoramento (`/monitoramento`) com ícone `Activity`
  - Técnico (`/tecnico`) com ícone `Terminal`
  - Financeiro (`/financeiro`) com ícone `TrendingUp`
- Badge de status global no centro:
  - Vermelho `KPI P2 CRÍTICO` se violacoesReais2025.P2 > olaTargets.P2.metaViolacoesAno.max
  - Verde `KPI DENTRO DA META` se ambos ok
- Timestamp atualizado a cada segundo (setInterval) à direita
- Importa: `violacoesReais2025`, `olaTargets` do mockData

---

### 2. `src/pages/GestaoPage.jsx`

Visão executiva. Público: gestores que querem o estado do KPI em segundos.

**Seção 1 — Banner de status KPI**
- Dois cards lado a lado (P2 e P3):
  - P2: vermelho (meta não atingida — 42 violações vs meta 36-39)
    - Título: "KPI P2 — Alta Prioridade"
    - Valor grande: "42 violações"
    - Subtítulo: "Meta: até 39 · ano 2025"
    - Badge: "ACIMA DA META"
  - P3: verde (meta atingida — 196 violações vs meta até 263)
    - Título: "KPI P3 — Média Prioridade"
    - Valor grande: "196 violações"
    - Subtítulo: "Meta: até 263 · ano 2025"
    - Badge: "DENTRO DA META"

**Seção 2 — 4 KPI Cards**
- "Previsão D+1" → valor: `previsaoVolume.D1.total` incidentes
  com sub "P2: 14 · P3: 38" | cor: laranja
- "Previsão D+7" → valor: `previsaoVolume.D7.total` incidentes
  com sub "próxima semana" | cor: amarelo
- "Atingimento P2" → valor: `79%` com sub "abaixo da meta" | cor: vermelho
- "Atingimento P3" → valor: `112%` com sub "meta atingida" | cor: verde

**Seção 3 — Violações mensais 2025**
- BarChart lado a lado (P2=vermelho, P3=laranja)
- Dados: `volumeMensal2025` (12 meses, campos violP2 e violP3)
- ReferenceLine horizontal em y=3 (média mensal P2 da meta) com label
- Título: "Violações de OLA por mês — 2025"

**Seção 4 — Volume total por produto (horizontal)**
- BarChart horizontal com `produtos` (top 8)
- Barra principal: total (azul claro)
- Segunda barra: violacoes (vermelho)
- Clicável: ao clicar no produto navega para `/monitoramento`
- Título: "Volume e Violações por Produto"

**Seção 5 — Tendência de volume mensal**
- LineChart com `volumeMensal2025`
- 2 linhas: P2 (vermelho) e P3 (laranja)
- Título: "Evolução mensal de incidentes KPI — 2025"

**Seção 6 — Projeção de fechamento do ano**
- Dois gauges (PieChart donut) lado a lado: P2 e P3
- P2: 79% de atingimento (vermelho)
- P3: 112% de atingimento (verde, capped visualmente em 100%)
- Abaixo: texto "Projeção de fechamento: P2=47 violações · P3=210 violações"

---

### 3. `src/pages/MonitoramentoPage.jsx`

Visão operacional. Público: analistas e supervisores de operações.

**Seção 1 — 4 KPI Cards operacionais**
- "Incidentes hoje (D+1)" → `previsaoVolume.D1.total` | cor laranja
- "P2 em aberto estimado" → `previsaoVolume.D1.P2` | cor vermelho
- "P3 em aberto estimado" → `previsaoVolume.D1.P3` | cor amarelo
- "Grupo mais crítico" → `Team07 · 8.94%` taxa violação | cor vermelho

**Seção 2 — Volume diário (últimos 30 dias + D+7)**
- AreaChart com `volumeDiario30d` (30 dias reais)
- Adicionar após o último dia os 7 dias de previsão Prophet com estilo
  tracejado e preenchimento mais transparente
- 2 séries: P2 (vermelho) e P3 (laranja)
- Linha divisória vertical separando "histórico" de "previsão"
- Label "← Histórico · Previsão →" na linha divisória
- Título: "Volume de incidentes — 30 dias + previsão D+7"

**Seção 3 — Heatmap sazonalidade**
- Grid 7 linhas (dias) × 24 colunas (horas)
- Cor de cada célula baseada no valor do `heatmapData`
  (escala: transparente → laranja → vermelho)
- Pico real: Qui 15h (391 incidentes) deve ser a célula mais vermelha
- Eixo X: 0h a 23h (mostrar apenas 0, 6, 12, 18, 23)
- Eixo Y: Seg a Dom
- Legenda: "Concentração de incidentes KPI · período 2023–2025"
- Implementar como SVG customizado (Recharts não tem heatmap nativo)

**Seção 4 — Tabela de alertas por produto**
- Tabela com `riscoOlaPorProduto`
- Colunas: Produto | Incidentes pendentes | Probabilidade OLA | Status
- Cor de fundo da linha baseada na probViolacao (>30%=vermelho, >15%=amarelo)
- Botão "Detalhes" em cada linha → abre DrillDownPanel lateral

---

### 4. `src/pages/TecnicoPage.jsx`

Visão analítica profunda. Público: engenheiros e analistas de dados.

**Seção 1 — 4 KPI técnicos**
- "Total incidentes KPI (2025)" → 25.600 | cor cinza
- "Taxa violação P2" → "0.81%" | cor vermelho
- "Taxa violação P3" → "0.96%" | cor laranja
- "Grupo mais crítico" → "Team07 · 8.94%" | cor vermelho

**Seção 2 — Ranking grupos (taxa de violação)**
- BarChart horizontal com `grupos` (top 10)
- Ordenado por taxaViolacao desc
- Cor da barra: vermelha se >3%, laranja se >1%, verde se <1%
- Tooltip: mostra total, violações e taxa
- Destaque no Team07 (8.94%)
- Título: "Taxa de violação de OLA por grupo de atendimento"

**Seção 3 — SHAP Feature Importance**
- BarChart horizontal com `shapFeatures`
- Ordenado por importance desc
- Cor única: vermelho com opacidade proporcional à importance
- LabelList mostrando % no final de cada barra
- Tooltip: mostra descrição da feature
- Título: "Feature importance — modelo XGBoost OLA (simulado)"
- Subtitle small: "Substituído por SHAP real após treinamento"

**Seção 4 — Clusters K-Means**
- 4 cards em grid 2×2 com os clusters
- Cada card: label do cluster, tamanho, taxa de violação (badge colorido),
  perfil resumido (hora, dias, produto, grupo), descrição
- Badge de taxa: >5%=vermelho, >2%=laranja, <2%=verde
- Cluster 3 (Team07) deve ter borda vermelha destacada
- Título: "Clusters de padrões de incidentes (K-Means simulado)"

**Seção 5 — Tabela técnica completa de grupos × categorias**
- Tabela com cruzamento: linha=grupo, coluna=categoria (top 5)
- Valor: taxa de violação da combinação
- Colormap de fundo (mais escuro = maior taxa)
- Scroll horizontal se necessário

---

### 5. `src/pages/FinancialPage.jsx` (renomear para FinanceiroPage.jsx)

Visão de impacto financeiro estimado de violações de OLA.

**Nota importante:** Os valores financeiros são ESTIMADOS com base em
penalidades de SLA, não em receita por downtime de servidor.

**Seção 1 — Header com disclaimer**
- Título: "Impacto Estimado de Violações de OLA"
- Badge amarelo: "ESTIMADO — baseado em penalidades SLA"

**Seção 2 — 3 KPI cards financeiros**
- "Violações P2 no ano" → 42 | com meta "meta: 36-39" | cor vermelho
- "Violações P3 no ano" → 196 | com meta "meta: 231-263" | cor verde
- "Excesso P2 vs meta" → "+3 violações" | cor laranja

**Seção 3 — Violações por mês (barras)**
- BarChart com `volumeMensal2025` (violP2 e violP3)
- ReferenceLine em y=3.2 para P2 (meta/mês) com label "meta mensal P2"
- ReferenceLine em y=21.9 para P3 (meta/mês) com label "meta mensal P3"

**Seção 4 — Distribuição de violações por produto**
- PieChart ou BarChart horizontal com `produtos`
- Mostrar violacoes por produto
- Tooltip com taxa de violação

**Toggle geral/técnico:**
- Botão no topo com `useState`
- Geral: visão executiva (seções 1-4 acima)
- Técnico: breakdown detalhado por produto × grupo

---

### 6. `src/components/DrillDownPanel.jsx`

Painel lateral deslizante (slide-in da direita) que abre ao clicar
em um produto/grupo na tabela do Monitoramento.

Recebe prop `item` (objeto de produto ou grupo) e `onClose`.

Mostra:
- Nome do produto/grupo
- Total de incidentes · violações · taxa de violação
- Gráfico de barras com distribuição por hora do dia (usando heatmapData
  filtrado pelo dia com mais incidentes daquele item)
- Lista dos top 3 clusters que envolvem aquele produto/grupo
- Botão fechar (X)

Animação de slide: `transform: translateX(0)` quando visível,
`translateX(40px) + opacity 0` quando fechado.

---

## Regras de implementação

1. **Nunca hardcodar hex** de cor — sempre usar `var(--red)` etc.
2. **Sempre usar** `fontFamily: 'var(--font-mono)'` ou `'var(--font-sans)'`
3. **Animação `fadeInUp`** em todos os cards (definida em index.css)
4. **Responsividade básica:** colunas colapsam em telas <768px
5. **Sem dependências novas** — apenas o que está em package.json
6. Todos os componentes exportam `default`
7. Importar dados sempre de `../data/mockData` ou `../../data/mockData`
8. **Manter** `src/context/DashboardContext.jsx` (usado pelo DashboardProvider no App.jsx)

---

## Estrutura de arquivos a entregar

```
src/
├── components/
│   ├── Topbar.jsx           ← reescrever
│   └── DrillDownPanel.jsx   ← reescrever
├── pages/
│   ├── GestaoPage.jsx       ← reescrever
│   ├── MonitoramentoPage.jsx← reescrever
│   ├── TecnicoPage.jsx      ← reescrever
│   └── FinanceiroPage.jsx   ← reescrever (era FinancialPage)
```

**Atenção:** Se renomear FinancialPage → FinanceiroPage, atualizar
o import no `App.jsx` também.

---

## Como os dados mudam quando os modelos ficarem prontos

Os JSONs de output substituem as importações do mockData assim:

| mockData atual | JSON do modelo |
|---|---|
| `previsaoVolume` | `outputs/previsoes_volume.json` (Prophet) |
| `riscoOlaPorProduto` | `outputs/risco_ola.json` (XGBoost) |
| `clusters` | `outputs/clusters.json` (K-Means) |
| `kpiAtingimento` | `outputs/kpi_atingimento.json` (Projeção) |
| `shapFeatures` | campo `shap_values` do risco_ola.json |

Os campos `produtos`, `grupos`, `categorias`, `heatmapData`,
`volumeMensal2025` e `volumeDiario30d` são dados históricos reais
que **não mudam** — vêm direto do dataset processado.

---

## Entregue os arquivos na ordem:

1. `src/components/Topbar.jsx`
2. `src/pages/GestaoPage.jsx`
3. `src/pages/MonitoramentoPage.jsx`
4. `src/pages/TecnicoPage.jsx`
5. `src/pages/FinanceiroPage.jsx`
6. `src/components/DrillDownPanel.jsx`
7. Atualização do `src/App.jsx` (apenas o import de FinancialPage → FinanceiroPage)

Para cada arquivo, entregue o código completo pronto para substituir
o arquivo atual. Não entregue trechos parciais.
