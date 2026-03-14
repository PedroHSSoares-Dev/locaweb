# Avaliação de Visualizações — Dashboard Locaweb InfraPredict

> **Contexto:** MVP acadêmico FIAP. Dados 100% simulados. Stack: React + Recharts. Público misto: DevOps/SRE (precisão e densidade) + gestores (clareza e acionabilidade). Horizonte padrão observado: 6h. Avaliação realizada com navegação ao vivo em `localhost:5173`.

---

## [GRÁFICO 1] Mapa de Risco por Servidor (Heatmap de Cards) — Monitoramento / Ambas as Visões

**O que está mostrando:** A probabilidade de falha de cada um dos 14 servidores, agrupada por produto (Hospedagem Compartilhada, E-mail Pro, Cloud Server, DNS), com codificação de cor por nível de risco (Crítico/Alto/Médio/Baixo) e barra de progresso proporcional à probabilidade.

**Importância:** Acionável

→ Justificativa: O usuário identifica de imediato qual servidor exige atenção (cards vermelhos saltam no tema escuro), qual produto está mais comprometido e pode acionar o DrillDown com um clique. É o elemento com maior densidade de informação acionável por centímetro quadrado do dashboard.

**Veredicto:** Está bom, com ressalvas pontuais

→ O tipo de card-grid é a escolha certa para este contexto: combina identidade (nome do servidor), valor numérico (%), nível semântico (Crítico/Alto), indicador visual (barra + cor de borda) e interatividade (clique para DrillDown) em um espaço compacto. Um treemap comunicaria o risco relativo de forma mais intuitiva para gestores mas perderia o nome do servidor e o nível textual — troca desvantajosa para o público SRE. Uma lista ranqueada eliminaria o agrupamento por produto, que é contextualmente relevante para equipes de operações.

**Problemas identificados:**

1. **Ordenação cross-produto inconsistente:** dentro de cada grupo os cards estão ordenados por probabilidade decrescente (correto), mas a leitura natural top-to-bottom coloca BRZ-HOST-04 (58%, Médio) visualmente antes de BRZ-MAIL-07 (83%, Crítico). Um gestor varrendo a tela de cima para baixo pode perder um servidor crítico.

2. **Ausência de tendência:** nenhum indicador de se a probabilidade está subindo ou descendo. Um ícone `↑` vermelho ou `↓` verde ao lado do percentual custaria 2px e triplicaria a acionabilidade do card — o SRE saberia se precisa agir agora ou se a situação está se resolvendo sozinha.

3. **Agrupamento por produto vs. por risco:** o agrupamento por produto faz sentido estrutural para times separados por produto, mas dificulta a leitura de risco global. Sugestão: manter o agrupamento por produto, mas adicionar um badge de contagem de críticos no cabeçalho de cada grupo (ex: `HOSPEDAGEM COMPARTILHADA — 1 CRÍTICO`).

4. **Tamanho de cards não é proporcional ao risco:** todos os cards têm o mesmo tamanho. Um servidor com 94% e um com 8% ocupam a mesma área. Alternativa viável: usar `opacity` reduzida nos cards de baixo risco para criar hierarquia visual sem mudar o layout.

**Nota: 7.5/10**

---

## [GRÁFICO 2] Time Series Chart (AreaChart 24h) — Monitoramento / Visão Geral e Visão Técnica

**O que está mostrando (Visão Geral):** A evolução da probabilidade de falha do servidor mais crítico (BRZ-HOST-01, 94%) ao longo das últimas 24h, com linhas de referência em 75% (crítico) e ~40% (alerta).

**O que está mostrando (Visão Técnica):** O mesmo gráfico, mas com 3 séries sobrepostas (top 3 servidores: BRZ-HOST-01 vermelho, BRZ-MAIL-07 laranja, BRZ-CLOUD-03 amarelo).

**Importância:** Contexto útil (Visão Geral) | Decorativa com potencial (Visão Técnica)

→ Justificativa Visão Geral: A série única é clara e legível. As reference lines bem posicionadas dão contexto imediato. O usuário consegue identificar padrões de degradação. Classifico como "contexto útil" porque a informação passada não gera ação direta — o que aciona é o valor atual, já exibido nos KPI cards e no heatmap.

→ Justificativa Visão Técnica: Com 3 áreas preenchidas sobrepostas e todas concentradas entre 60% e 100%, as curvas se fundem numa mancha escura avermelhada. O gráfico falha em comunicar *diferença entre os três servidores*, que era seu objetivo ao passar de 1 para 3 séries.

**Veredicto:** Visão Geral está bom | Visão Técnica precisa mudar

**Proposta para Visão Técnica:** Substituir `<AreaChart>` por `<LineChart>` com 3 `<Line>` sem área preenchida e `strokeWidth={2}`. As curvas ganham separação visual imediata. As reference lines continuam funcionando. Custo de implementação: trocar a tag e remover as props de `fill`. Ganho: as 3 linhas se tornam distinguíveis mesmo com cores similares.

```jsx
// Antes
<AreaChart data={data}>
  <Area dataKey="host01" fill="#ff2020" stroke="#ff2020" />
  <Area dataKey="mail07" fill="#ff8800" stroke="#ff8800" />
  <Area dataKey="cloud03" fill="#ffcc00" stroke="#ffcc00" />
</AreaChart>

// Depois
<LineChart data={data}>
  <YAxis domain={[40, 100]} tickFormatter={(v) => `${v}%`} />
  <Line dataKey="host01" stroke="#ff2020" strokeWidth={2} dot={false} />
  <Line dataKey="mail07" stroke="#ff8800" strokeWidth={2} dot={false} />
  <Line dataKey="cloud03" stroke="#ffcc00" strokeWidth={2} dot={false} />
</LineChart>
```

**Problemas adicionais em ambas as visões:**

1. **Eixo Y mal aproveitado (0-100%):** os dados se concentram entre 60% e 100%, usando apenas o terço superior do espaço vertical. Adicionar `domain={[40, 100]}` no `YAxis` ampliaria 60% da área de plotagem e tornaria variações de 5-10pp visíveis — atualmente imperceptíveis.

2. **Sem projeção futura:** o horizonte selecionado é 6h, mas o gráfico mostra apenas as últimas 24h. Um modelo preditivo que projeta 6h à frente mas não visualiza essa projeção perde metade da proposta de valor. Sugestão: adicionar `<ReferenceLine>` vertical no "agora" e uma área sombreada com a projeção à direita.

3. **Sem anotação de alertas:** não há marcação de quando os alertas foram gerados. Um `<ReferenceDot>` no ponto exato em que a probabilidade cruzou 40% daria contexto imediato ("o alerta existe há 3h").

4. **Área preenchida é decorativa na Visão Geral:** não carrega informação adicional além da linha em si. Um `<LineChart>` com `strokeWidth={3}` seria mais limpo.

**Nota: 5.5/10** (Visão Geral: 7/10 | Visão Técnica: 4/10)

---

## [GRÁFICO 3] Feature Importance (Barras Horizontais) — DrillDown de Servidor Crítico

**O que está mostrando:** A contribuição relativa de cada métrica (CPU Load, RAM Usage, Disk I/O, Latência, Erros HTTP) para a predição de falha do modelo ML do servidor selecionado (BRZ-HOST-01).

**Importância:** Contexto útil (para SRE) | Decorativa (para gestor)

→ Justificativa: Um SRE consegue usar essa informação para priorizar onde intervir primeiro ("CPU Load é o principal driver — vou verificar processos em fuga"). Para um gestor, o gráfico não gera ação direta, e o DrillDown é majoritariamente acionado por gestores que clicaram em "Investigar".

**Veredicto:** Precisa mudar

**Proposta 1 — Para audiência mista (recomendada):** Manter o gráfico de barras horizontais mas adicionar: (a) valor percentual ao final de cada barra com `<LabelList position="right" />`, (b) garantir ordenação decrescente por importância via sort nos dados, (c) usar cor única (vermelho) com `fillOpacity` variando de `1.0` a `0.2` conforme importância — elimina a necessidade de legenda de cores.

**Proposta 2 — Para gestor puro:** Substituir o gráfico por texto estruturado:
```
Principais causas desta predição:
1. Sobrecarga de CPU — 48% de influência
2. Uso elevado de RAM — 32% de influência
3. I/O de disco saturado — 14% de influência
```

**Problemas identificados:**

1. **5 cores distintas sem função semântica:** cada barra tem uma cor diferente (vermelho, laranja, amarelo, verde, cinza) sem motivo funcional. A cor já está codificando severidade nos cards do heatmap — aqui ela apenas cria ruído. Uma cor única com intensidade decrescente seria semanticamente correta.

2. **Sem valores numéricos nas barras:** as barras são proporcionais mas não têm rótulos. O usuário não sabe se CPU Load é 45% ou 80% de influência — apenas que é a maior. `<LabelList dataKey="value" formatter={(v) => \`${v}%\`} />` resolve.

3. **"Erros HTTP" quase invisível:** barra tão pequena que desaparece. Se contribuição < 5%, agrupar em "Outros".

4. **Proporção no painel:** Feature Importance ocupa menos de 30% do DrillDown mas é a informação mais única do painel — as métricas de CPU/RAM estão duplicadas na tabela da Visão Técnica. Sugere-se inverter a proporção.

**Nota: 6/10**

---

## [GRÁFICO 4A] Financial ComposedChart — Visão Geral (barras simples + linha de probabilidade)

**O que está mostrando:** A exposição financeira total de cada servidor em risco (barras vermelhas, eixo R$ à esquerda), sobreposta à linha de probabilidade de falha (linha branca pontilhada, eixo % à direita), com ReferenceLine "Limite de atenção".

**Importância:** Acionável

→ Justificativa: Um gestor pode tomar decisão direta — "BRZ-HOST-01 tem a maior exposição E a maior probabilidade, é a prioridade máxima." O dual-axis é justificado porque as duas grandezas (R$ e %) têm relação direta com a decisão de priorização.

**Veredicto:** Está bom para Visão Geral, com ajustes pontuais

**Problemas identificados:**

1. **Dual-axis sem rótulos de eixo:** sem `"Exposição (R$)"` e `"Probabilidade (%)"` explícitos, um usuário pode confundir as escalas.

2. **Linha de probabilidade não monotônica:** as barras estão ordenadas por exposição decrescente, mas a linha de probabilidade sobe e desce de forma sinuosa (BRZ-HOST-04 tem exposição maior que BRZ-DNS-01 mas probabilidade menor). Parece série temporal em vez de ranking com segunda dimensão. Alternativa mais expressiva: `<ScatterChart>` com X = probabilidade, Y = exposição, comunicando diretamente a relação entre as duas variáveis.

3. **ReferenceLine sem valor:** label "Limite de atenção" não inclui o valor (R$600k). Adicionar `label={{ value: "R$600k — Limite de atenção" }}` tornaria a linha autoexplicativa.

4. **Todos acima do limite:** a ReferenceLine perde impacto quando todos os elementos a ultrapassam. Seria mais útil se marcasse o ponto de intervenção automática.

**Nota: 7/10**

---

## [GRÁFICO 4B] Financial ComposedChart — Visão Técnica (barras empilhadas + linha de probabilidade)

**O que está mostrando:** A decomposição da exposição financeira de cada servidor em três componentes empilhados (Churn laranja, Downtime vermelho, Ops Cost amarelo) mais a linha de probabilidade (branca pontilhada).

**Importância:** Contexto útil

→ Justificativa: A decomposição Churn/Downtime/Ops Cost é informação valiosa para entender a natureza do risco. Porém, como Churn domina ~90% de cada barra, os outros componentes quase desaparecem — a composição está tecnicamente presente mas praticamente ilegível.

**Veredicto:** Precisa mudar

**Proposta:** Usar `stackOffset="expand"` no `<BarChart>` para normalizar para 100% e remover o eixo R$, mostrando apenas a proporção de cada componente. O valor absoluto total vai como rótulo no topo de cada barra. Isso comunica "onde está o risco de cada servidor" em vez de "qual é o total" (já existente na Visão Geral).

**Problemas adicionais:**

1. **Downtime e Ops Cost invisíveis:** as fatias são tão pequenas que precisam de zoom para serem vistas. A legenda indica 4 itens mas o olho vê 2.

2. **Linha branca sobre barras laranjas:** contraste existe mas a linha pontilhada se perde visualmente. Considerar `stroke="#00FFFF"` (ciano) ou `strokeWidth={2}`.

3. **Ordem de empilhamento:** Churn (maior, mais variável) deveria estar no topo para facilitar comparação entre servidores. Reordenar: Ops Cost (base) > Downtime > Churn (topo).

**Nota: 5/10**

---

## [GRÁFICO 5] KPI Cards — Monitoramento (Visão Geral e Visão Técnica)

**O que está mostrando:** Quatro métricas-chave: Servidores Monitorados (14), Alertas Ativos (6), Probabilidade Média (40.1%) e Próximo Incidente (~0.4h).

**Importância:** Misto — 2 acionáveis, 1 contexto útil, 1 problemático

→ **Servidores Monitorados (14):** Contexto útil. Não muda a cada refresh e não gera ação.

→ **Alertas Ativos (6):** Acionável ✓. Número mais importante da tela. Sub-label `failProb ≥40% — 6h` é excelente contextualização.

→ **Probabilidade Média (40.1%):** Contexto útil com ressalva. A média de 14 servidores esconde a distribuição bimodal real (2 críticos >80%, 8 seguros <35%). Uma média de 40% é enganosamente tranquilizadora. O delta `+0.4%` na Visão Técnica é boa adição. Sugestão: substituir por "Críticos Agora: 2 / 14".

→ **Próximo Incidente (~0.4h):** Problemático. `~0.4h` (≈24 minutos) é específico demais para dados simulados. Alternativa: "< 1h" ou range "0.4h – 1.2h" com intervalo de confiança.

**Veredicto:** Ajuste parcial necessário

→ Reordenar: (1) Alertas Ativos, (2) Próximo Incidente, (3) Probabilidade Média, (4) Servidores Monitorados.

**Métricas ausentes para SRE:** MTTR estimado, horas acima do threshold crítico nas últimas 24h, SLA breach probability.

**Métricas ausentes para gestor:** % da frota crítica, tendência global (melhorando/piorando).

**Nota: 6.5/10**

---

## [GRÁFICO 6] KPI Cards — Impacto Financeiro (Visão Geral e Visão Técnica)

**O que está mostrando:** Três métricas financeiras: Receita em Risco (R$ 419.640), Perda por Churn Estimada (R$ 6.071.868) e Exposição Total (R$ 15.683.299).

**Importância:** Acionável

→ Justificativa: As três métricas têm semânticas distintas e complementares — impacto imediato, impacto de longo prazo em churn, e exposição total consolidada. Um gestor pode usar qualquer uma em uma reunião de priorização.

**Veredicto:** Ajuste de hierarquia necessário

**Problemas identificados:**

1. **Hierarquia invertida:** Exposição Total (R$15.6M — maior e mais impactante) é o terceiro card. Receita em Risco (R$419k — menor número) é o primeiro. A leitura da esquerda para a direita cria falsa impressão de problema pequeno. Reordenar: (1) Exposição Total, (2) Perda por Churn, (3) Receita em Risco.

2. **Diferença semântica entre os KPIs não está clara:** R$419k vs R$15.6M (37x de diferença) sem subtítulo explicativo confunde. Adicionar "impacto nas próximas 6h" vs "custo total de recuperação + churn" como subtítulo.

3. **Sem referência relativa:** R$15.6M é muito ou pouco? Adicionar "≈ X% da receita mensal" daria escala para o gestor.

4. **Ausência de clientes afetados:** "847 clientes em risco de churn" seria mais impactante que "R$6M" para gestores orientados a NPS e retenção.

5. **Sem delta histórico:** os cards financeiros não têm `+/-` comparativo (ao contrário do card de Probabilidade Média no Monitoramento). "`↑ R$2.1M vs. 24h atrás`" seria imediatamente acionável.

**Nota: 6.5/10**

---

## Resumo Geral

| Gráfico | Importância | Veredicto | Nota |
|---|---|---|---|
| Risk Heatmap (Cards) | Acionável | Está bom (com ressalvas) | 7.5/10 |
| Time Series — Visão Geral | Contexto útil | Está bom (com ajustes) | 7.0/10 |
| Time Series — Visão Técnica | Decorativa | **Precisa mudar** | 4.0/10 |
| Feature Importance (DrillDown) | Contexto útil / Decorativa | **Precisa mudar** | 6.0/10 |
| Financial ComposedChart — Geral | Acionável | Está bom (com ajustes) | 7.0/10 |
| Financial ComposedChart — Técnica | Contexto útil | **Precisa mudar** | 5.0/10 |
| KPI Cards — Monitoramento | Misto | Ajuste parcial | 6.5/10 |
| KPI Cards — Financeiro | Acionável | Ajuste de hierarquia | 6.5/10 |

**Média geral: 6.2/10**

---

## Top 3 Mudanças de Maior Impacto

### 1. Substituir AreaChart com 3 séries por LineChart na Visão Técnica + ajustar domain do YAxis

**Impacto:** Alto | **Custo de implementação:** Baixíssimo (troca de tag + 1 prop)

Trocar `<AreaChart>` por `<LineChart>`, remover as props `fill` de cada série, e adicionar `domain={[40, 100]}` no `<YAxis>`. Resultado imediato: as 3 curvas tornam-se distinguíveis (hoje são uma mancha avermelhada indistinta), e variações de 5-10pp — atualmente invisíveis na escala 0-100% — ficam visíveis e comparáveis. É a mudança com maior ganho de legibilidade pelo menor custo de desenvolvimento.

### 2. Adicionar `<LabelList>` no Feature Importance + usar cor única com opacidade variável

**Impacto:** Médio-alto | **Custo de implementação:** Baixo (2 props do Recharts)

O Feature Importance é o único elemento exclusivo do DrillDown — toda a outra informação existe na tabela da Visão Técnica. Portanto, é o elemento que mais justifica o DrillDown existir. Adicionar `<LabelList dataKey="importance" position="right" formatter={(v) => \`${(v*100).toFixed(0)}%\`} />` e unificar as cores para vermelho com `fillOpacity` decrescente de `1.0` a `0.15` elimina a legenda desnecessária e torna a magnitude de cada feature imediatamente legível.

### 3. Normalizar barras empilhadas para 100% no Financial Técnico + reordenar KPI cards financeiros

**Impacto:** Médio-alto | **Custo de implementação:** Baixo-médio

Usar `stackOffset="expand"` no `<BarChart>` normaliza automaticamente para 100%, transformando o gráfico de "repetição da Visão Geral" para "composição do risco por servidor" — informação genuinamente nova. Em paralelo, reordenar os KPI cards para (1) Exposição Total → (2) Perda por Churn → (3) Receita em Risco corrige a hierarquia e evita que o gestor leia R$419k como o número principal de uma exposição de R$15.6M.

---

## Observações Finais

**O que a dashboard acerta bem:**
- Identidade visual coesa (tema escuro, paleta de risco bem definida)
- Interatividade (DrillDown por clique no heatmap e no botão Investigar)
- Separação de audiência (Visão Geral/Técnica)
- Uso de reference lines para contextualizar thresholds
- Badge "SIMULADO" visível — excelente transparência para contexto acadêmico
- Delta `+0.4%` na Probabilidade Média da Visão Técnica

**O que ainda precisa:**
- Projeção futura visível (o modelo prediz 6h, o gráfico mostra apenas histórico)
- Indicadores de tendência (↑↓) nos cards de risco
- Anotações temporais de eventos (quando o alerta foi gerado)
- Valores absolutos nos gráficos que não os exibem
- Revisão da hierarquia dos KPI cards financeiros
- Intervalo de confiança no "Próximo Incidente"

---

*Avaliação realizada em 13/03/2026 | Dashboard localhost:5173 | MVP FIAP InfraPredict*
