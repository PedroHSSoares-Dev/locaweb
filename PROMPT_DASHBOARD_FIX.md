# Prompt — Predictfy × Locaweb: Dashboard Fix & Completion

## Contexto do projeto

Você está trabalhando no frontend de uma dashboard AIOps chamada **Predictfy × Locaweb**, desenvolvida como projeto acadêmico FIAP Challenge 2026.

**Stack:** React + Vite + Recharts + react-router-dom + lucide-react  
**Diretório:** `frontend/src/`  
**Tema:** dark theme com tokens CSS em `index.css`  
**Dados:** mockData.js com 28 servidores simulados (dataset real da Locaweb ainda não integrado)

### Tokens CSS (index.css — não alterar)
```css
--bg: #0a0a0a | --surface1: #111111 | --surface2: #181818 | --surface3: #1f1f1f
--border: rgba(255,255,255,0.07) | --border-md: rgba(255,255,255,0.13)
--red: #E8002D | --orange: #ff6d00 | --yellow: #ffea00 | --green: #00e676
--text-pri: #f0f0f0 | --text-sec: #888888 | --text-muted: #444444
--font-mono: 'IBM Plex Mono' | --font-sans: 'IBM Plex Sans'
```

---

## Estado atual dos arquivos

### Arquivos que JÁ FUNCIONAM (não mexer na lógica, só corrigir bugs visuais se houver):
- `App.jsx` — roteamento correto com BrowserRouter + 4 rotas
- `index.css` — tokens e animações ok
- `main.jsx` — entry point ok
- `context/DashboardContext.jsx` — estado global de horizon ok
- `data/mockData.js` — 28 servidores, financialConfig, featureProfiles, helpers ok
- `components/Topbar.jsx` — navegação com NavLink, horizon selector, status badge ok
- `components/RiskHeatmap.jsx` — heatmap por produto com ServerCell, badges ok
- `components/DrillDownPanel.jsx` — panel lateral com métricas, feature importance, animação ok
- `components/KpiCards.jsx` — 4 cards com alertas, próximo incidente, críticos, total ok
- `components/TimeSeriesChart.jsx` — AreaChart (geral) e LineChart (técnico) ok
- `components/AlertsList.jsx` — lista ordenada por risco, colunas técnicas ok
- `components/FinancialImpact.jsx` — ComposedChart geral, BarChart % técnico, KPI cards ok
- `pages/GestaoPage.jsx` — health banner, KPI cards, product bar chart, gauge, timeline, trend ok
- `pages/MonitoramentoPage.jsx` — filter chip, KpiCards, TimeSeries+Heatmap, AlertsList ok
- `pages/FinancialPage.jsx` — wrapper simples para FinancialImpact ok

### Arquivo que PRECISA SER CRIADO/COMPLETADO:
- `pages/TecnicoPage.jsx` — **a página existe mas está incompleta** (veja abaixo)

---

## O que precisa ser feito

### TAREFA 1 — Completar TecnicoPage.jsx

A página atual apenas reutiliza os mesmos componentes do MonitoramentoPage com `viewMode="tecnica"`. Isso está funcionando, mas a visão técnica precisa de uma **seção extra exclusiva** que não existe em nenhuma outra página: um **painel de métricas de sistema em tempo real** dos servidores críticos.

Adicione, acima do `<AlertsList>`, um novo bloco chamado `SystemMetricsPanel` **inline na própria TecnicoPage.jsx** com as seguintes especificações:

**SystemMetricsPanel:**
- Título: "Métricas de Sistema — Servidores em Alerta"
- Filtra servidores com `failProb >= 40`, ordenados por `failProb` desc
- Exibe uma grade de cards com `gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))'`
- Cada card mostra:
  - Nome do servidor (`font-mono`, destaque vermelho se crítico)
  - Produto (font-sans, text-muted)
  - 3 mini barras horizontais: CPU, RAM, Disco (cada com label, valor % e barra colorida)
  - Latência como texto simples (ex: `142ms`)
  - Cor da barra: verde se <50%, amarelo se 50-79%, laranja se 80-89%, vermelho se ≥90%
- Background `var(--surface1)`, border `var(--border)`, borderRadius 8
- Barra tem height 3px, background `var(--surface3)`, fill com a cor de risco
- Animação `fadeInUp` com delay escalonado por índice

**TecnicoPage.jsx atualizada deve ter esta estrutura:**
```jsx
<KpiCards horizon={horizon} viewMode="tecnica" />
<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
  <TimeSeriesChart viewMode="tecnica" />
  <RiskHeatmap onSelectServer={setSelectedServer} />
</div>
<SystemMetricsPanel />   {/* NOVO */}
<AlertsList horizon={horizon} viewMode="tecnica" onSelectServer={setSelectedServer} />
```

---

### TAREFA 2 — Corrigir bug no RiskHeatmap com filtro de produto

Em `MonitoramentoPage.jsx`, o `<RiskHeatmap>` recebe a prop `filtroProduto` mas o componente `RiskHeatmap.jsx` **ignora essa prop**. Quando o usuário clica num produto na GestaoPage e é redirecionado para `/monitoramento?produto=Cloud+Server`, o heatmap deveria filtrar apenas os servidores daquele produto, mas mostra todos.

**Fix no RiskHeatmap.jsx:**
- Adicionar prop `filtroProduto` na assinatura da função
- Filtrar `getServersByProduct()` para mostrar apenas o grupo do produto selecionado quando `filtroProduto` estiver definido
- Quando filtrado, mostrar um indicador sutil no header: `"Filtrando: {filtroProduto}"` em font-mono 10px, cor var(--text-muted)
- Quando não filtrado, comportamento atual (mostrar todos os grupos)

---

### TAREFA 3 — Adicionar aba "Financeiro" alternância entre visão Geral e Técnica na FinancialPage

A `FinancialPage.jsx` atualmente passa `viewMode="geral"` fixo para o `FinancialImpact`. O componente `FinancialImpact` já tem suporte completo a `viewMode="tecnica"` (BarChart de composição %), mas não há como o usuário alternar entre as duas visões.

**Adicionar na FinancialPage.jsx:**
- Um toggle simples de 2 botões no topo da página: `VISÃO GERAL` | `VISÃO TÉCNICA`
- Estilo dos botões: idêntico ao seletor de horizonte na Topbar (background surface2, border, borderRadius 6, padding 2)
- Botão ativo: background `var(--red)`, color `#fff`
- Botão inativo: color `var(--text-sec)`, transparent background
- Estado local com `useState('geral')` → passa para `FinancialImpact`

---

### TAREFA 4 — Pequenas correções de consistência

**4a. AlertsList.jsx — filtroProduto ignorado**  
O componente recebe `filtroProduto` como prop mas não o utiliza. Adicionar filtro:
```js
const sorted = [...servers]
  .filter(s => !filtroProduto || s.product === filtroProduto)
  .sort((a, b) => b.failProb - a.failProb);
```

**4b. GestaoPage.jsx — trend line domain**  
No LineChart da tendência global (seção 6), o YAxis não tem domain definido. Adicionar `domain={['auto', 'auto']}` para não fixar em 0-100 e mostrar melhor a variação.

**4c. Topbar.jsx — badge de risco no /tecnico**  
O badge de contagem de servidores em risco (número vermelho ao lado de "Técnico") usa `atRiskCount` mas não aplica o multiplicador do horizonte selecionado. Corrigir:
```js
// antes:
const atRiskCount = servers.filter(s => s.failProb >= 40).length;
// depois:
const atRiskCount = servers.filter(s => s.failProb * mult >= 40).length;
```
(O `mult` já existe calculado logo acima no componente.)

---

## Restrições importantes

1. **NÃO alterar** `mockData.js`, `index.css`, `main.jsx`, `App.jsx`, `DashboardContext.jsx`
2. **NÃO instalar** nenhum pacote npm adicional — usar apenas o que já está em package.json (react-router-dom, recharts, lucide-react já instalados)
3. **Manter** todos os tokens CSS via variáveis (`var(--red)` etc.), nunca hardcodar hex para cores principais
4. **Manter** `fontFamily: 'var(--font-mono)'` e `'var(--font-sans)'` em todos os textos
5. **Manter** animação `fadeInUp` nos cards novos (já está em index.css)
6. **Não remover** nenhuma funcionalidade existente — apenas adicionar e corrigir

---

## Arquivos a entregar

Retornar o código completo e funcional dos seguintes arquivos, em ordem:

1. `frontend/src/pages/TecnicoPage.jsx` (com SystemMetricsPanel inline)
2. `frontend/src/components/RiskHeatmap.jsx` (com fix do filtroProduto)
3. `frontend/src/pages/FinancialPage.jsx` (com toggle geral/técnico)
4. `frontend/src/components/AlertsList.jsx` (com fix do filtroProduto)
5. `frontend/src/pages/GestaoPage.jsx` (com fix do domain no trend chart)
6. `frontend/src/components/Topbar.jsx` (com fix do atRiskCount)

Para cada arquivo, retornar o código completo (não trechos) pronto para substituir o arquivo atual.
