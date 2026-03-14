# Avaliação de Visualizações v2 — Dashboard Locaweb InfraPredict
### Avaliação pós-atualização · 13/03/2026

> **O que mudou:** Esta é a segunda rodada de avaliação, realizada após o Pedro implementar melhorias com base no relatório v1. Cada seção registra explicitamente o que foi corrigido ✅, o que ainda persiste ⚠️ e o que regrediu ❌. A nota final reflete o estado atual, não o delta de melhoria.

---

## Resumo das mudanças implementadas

| # | Mudança | Status |
|---|---|---|
| 1 | KPI cards Monitoramento reordenados (Alertas Ativos primeiro) | ✅ Implementado |
| 2 | "Próximo Incidente" de `~0.4h` → `menos de 1h` | ✅ Implementado |
| 3 | Badges de contagem por grupo no Heatmap (`1 CRÍTICO`, `1 ALERTA`) | ✅ Implementado |
| 4 | Indicadores de tendência nos cards (`↑+12pp`, `↓-5pp`) | ✅ Implementado |
| 5 | Time Series Técnico: `<AreaChart>` → `<LineChart>` | ✅ Implementado |
| 6 | Time Series Técnico: `domain={[40, 100]}` no eixo Y | ✅ Implementado |
| 7 | Feature Importance: cor única vermelha com opacidade variável | ✅ Implementado |
| 8 | Feature Importance: percentuais numéricos nas barras (32%, 23%…) | ✅ Implementado |
| 9 | KPI cards Financeiro reordenados (Exposição Total primeiro) | ✅ Implementado |
| 10 | Subtítulos semânticos nos KPIs financeiros | ✅ Implementado |
| 11 | `stackOffset="expand"` nas barras empilhadas (Técnico Financeiro) | ❌ Regressão — barras sumiram |
| 12 | `ReferenceLine` com valor R$ no label ("Limite de atenção") | ⚠️ Não implementado |
| 13 | Projeção futura no time series | ⚠️ Não implementado |
| 14 | KPI "Probabilidade Média" → "Críticos Agora" | ⚠️ Não implementado |

**Taxa de implementação: 10/14 sugestões — 71%**

---

## [GRÁFICO 1] Mapa de Risco por Servidor — Monitoramento / Ambas as Visões

**O que está mostrando:** A probabilidade de falha dos 14 servidores, agrupada por produto, com codificação de cor por nível de risco, barra de progresso, **indicadores de tendência** e **badges de alerta por grupo**.

**Importância:** Acionável

**Veredicto:** ✅ Melhorou significativamente — está bom

**O que mudou desde v1:**

✅ **Indicadores de tendência implementados:** cada card agora exibe `↑+12pp` (vermelho) ou `↓-5pp` (verde) abaixo do percentual. Esta é a melhoria de maior impacto prático do heatmap — o SRE sabe instantaneamente se o servidor está piorando (agir agora) ou melhorando (monitorar). A escolha de `pp` (pontos percentuais) é tecnicamente correta e precisa.

✅ **Badges por grupo implementados:** cada linha de produto agora exibe `1 CRÍTICO` e/ou `1 ALERTA` em badges coloridos no cabeçalho do grupo. O SRE pode varrer os grupos verticalmente e saber onde há fogo sem precisar ler todos os cards.

**Problemas remanescentes:**

⚠️ **Ordenação cross-produto ainda inconsistente:** BRZ-MAIL-07 (83%, Crítico, E-mail Pro) continua abaixo de BRZ-HOST-04 (58%, Médio, Hospedagem) na leitura top-to-bottom. Os badges amenizam isso ("E-MAIL PRO — 1 CRÍTICO"), mas um gestor que lê linearmente ainda pode perder o segundo servidor crítico.

⚠️ **Área fill no Visão Geral do time series** (não afeta o heatmap, mas é o gráfico adjacente).

**Nota: 8.5/10** *(era 7.5 — ganho de +1.0)*

---

## [GRÁFICO 2] Time Series Chart — Monitoramento / Visão Geral

**O que está mostrando:** A evolução da probabilidade de falha do servidor mais crítico (BRZ-HOST-01) nas últimas 24h, com reference lines em 75% (crítico) e 40% (alerta).

**Importância:** Contexto útil

**Veredicto:** Está bom — sem mudanças nesta visão

**Problemas remanescentes (inalterados da v1):**

⚠️ **Área preenchida ainda presente:** o fill abaixo da curva não carrega informação adicional. O gráfico inteiro se passa entre 75% e 100% mas o eixo Y vai de 0% a 100%, desperdiçando 75% do espaço vertical disponível. O `domain` ajustado existe apenas na Visão Técnica — seria benéfico aplicar também aqui com `domain={[70, 100]}`.

⚠️ **Sem projeção futura:** o horizonte de 6h foi selecionado, mas o gráfico mostra apenas o histórico de 24h. A área à direita do "agora" permanece vazia — nenhuma visualização da predição que o modelo gerou.

⚠️ **Sem `<ReferenceDot>` de onset do alerta:** não há marcação de quando a probabilidade cruzou 40% pela primeira vez, o que deixaria o SRE sem contexto de quanto tempo o servidor já está em estado de alerta.

**Nota: 7.0/10** *(inalterado)*

---

## [GRÁFICO 3] Time Series Chart — Monitoramento / Visão Técnica

**O que está mostrando:** A evolução da probabilidade de falha dos top 3 servidores em risco (BRZ-HOST-01 vermelho, BRZ-MAIL-07 laranja, BRZ-CLOUD-03 amarelo) nas últimas 24h.

**Importância:** Contexto útil → subiu para **Acionável**

**Veredicto:** ✅ Transformação completa — excelente resultado

**O que mudou desde v1:**

✅ **`<AreaChart>` → `<LineChart>`:** as 3 linhas estão completamente distinguíveis. O que antes era uma mancha avermelhada indistinta é agora 3 curvas separadas onde cada uma conta uma história diferente. BRZ-CLOUD-03 (amarelo) cai dramaticamente para ~57% ao meio-dia antes de subir para ~100% ao final do dia — informação que era impossível de ler na versão anterior.

✅ **`domain={[40, 100]}` no eixo Y:** a área de plotagem agora usa 100% do espaço disponível. Variações de 10pp (que eram imperceptíveis antes) são agora visíveis como movimentos significativos no gráfico. O threshold de 75% ("crítico") ocupa agora o centro visual do gráfico, dando peso correto à linha de alerta.

✅ **Reference line de alerta (~40%) ainda presente:** posicionada no fundo do gráfico, serve como limite inferior visual, bem contextualizado.

**Problemas remanescentes:**

⚠️ **Sem projeção futura:** mesmo problema do Visão Geral — o gráfico é puramente retrospectivo.

⚠️ **Sem anotação de onset de alerta:** não há `<ReferenceDot>` marcando quando cada linha cruzou o threshold.

⚠️ **Linhas muito próximas no topo:** entre 20:00 e o final do eixo, as 3 linhas convergem para ~100% e se sobrepõem novamente. Não é causado pelo tipo de gráfico (correto agora) mas sim pelos dados simulados. Em produção, dados reais provavelmente teriam mais dispersão.

**Nota: 8.5/10** *(era 4.0 — ganho de +4.5 — maior melhoria da dashboard)*

---

## [GRÁFICO 4] Feature Importance (Barras Horizontais) — DrillDown

**O que está mostrando:** A contribuição percentual de cada métrica (CPU Load 32%, RAM Usage 23%, Disk I/O 18%, Latência 17%, Erros HTTP 10%) para a predição de falha do modelo ML.

**Importância:** Contexto útil (SRE) / Acionável (com as melhorias aplicadas)

**Veredicto:** ✅ Melhorou significativamente — está bom

**O que mudou desde v1:**

✅ **Valores percentuais nas barras:** 32%, 23%, 18%, 17%, 10% aparecem à direita de cada barra. O usuário não precisa mais inferir a magnitude pela comprimento visual — lê diretamente. Esta mudança eleva o gráfico de "interpretável por SRE" para "interpretável por gestor".

✅ **Cor única vermelha com opacidade decrescente:** as 5 cores diferentes (vermelho, laranja, amarelo, verde, cinza) foram substituídas por vermelho com intensidade proporcional à importância. A semântica ficou correta: mais vermelho = mais perigoso/influente. A legenda de cores foi eliminada — não é mais necessária.

✅ **Ordenação decrescente confirmada:** CPU Load (32%) > RAM Usage (23%) > Disk I/O (18%) > Latência (17%) > Erros HTTP (10%). A hierarquia visual é agora imediata e correta.

**Problemas remanescentes:**

⚠️ **"Erros HTTP" ainda presente com apenas 10%:** a barra é a menor e quase se confunde com a anterior. Considerar threshold de visibilidade (<12%) para agrupar em "Outros". Neste caso específico a diferença de 17% para 10% entre Latência e Erros HTTP é pequena o suficiente para justificar a exibição, então é aceitável.

⚠️ **Os valores somam 100% (32+23+18+17+10=100):** isso pode ser uma coincidência dos dados simulados, mas se for sempre o caso em produção é correto. Se não for, a percepção de que "tudo some 100%" pode criar expectativa errada. Detalhe menor.

⚠️ **Métricas Atuais têm barras de progresso, mas sem threshold:** CPU 80%, RAM 79%, Disco 69% têm barras, mas nenhuma linha de "normal esperado" (ex: abaixo de 70% é ok). O usuário não sabe se 79% de RAM é crítico ou normal para este servidor.

**Nota: 8.0/10** *(era 6.0 — ganho de +2.0)*

---

## [GRÁFICO 5A] Financial ComposedChart — Visão Geral

**O que está mostrando:** A exposição financeira total de cada servidor (barras vermelhas, R$ eixo esquerdo) mais a linha de probabilidade (linha branca pontilhada, % eixo direito) e ReferenceLine "Limite de atenção".

**Importância:** Acionável

**Veredicto:** Sem mudanças — mantém os mesmos pontos da v1

**Problemas remanescentes (inalterados):**

⚠️ **`ReferenceLine` sem valor monetário:** o label "Limite de atenção" existe mas não informa qual é o limite (R$ ~600k). Um usuário novo na dashboard não consegue interpretar a linha sem contexto adicional. Fix de 1 linha: `label={{ value: "Limite R$600k", position: "insideTopLeft" }}`.

⚠️ **Linha de probabilidade não ordenada pela mesma chave das barras:** barras ordenadas por exposição total; linha de probabilidade cria curva sinuosa que não segue a mesma ordem. Visualmente parece série temporal, não ranking bidimensional.

⚠️ **Dual-axis sem rótulos de eixo:** os eixos Y esquerdo (R$) e direito (%) não têm `label` prop.

**Nota: 7.0/10** *(inalterado)*

---

## [GRÁFICO 5B] Financial ComposedChart — Visão Técnica

**O que está mostrando:** Deveria mostrar decomposição Churn + Downtime + Ops Cost em barras empilhadas normalizadas, mas atualmente **as barras não estão renderizando** — apenas a linha de probabilidade é visível.

**Importância:** Contexto útil (quando funcionando)

**Veredicto:** ❌ Regressão — o gráfico quebrou

**O que aconteceu:**

A implementação de `stackOffset="expand"` em um `<ComposedChart>` com dual Y-axis (`yAxisId` separados para barras R$ e linha %) causou um conflito interno no Recharts. Com `stackOffset="expand"`, o Recharts normaliza os valores de stack para o intervalo 0-1. No entanto, como as barras estão vinculadas ao `yAxisId` do eixo R$ (que ainda espera valores monetários absolutos), o domínio do eixo e os valores normalizados entram em conflito e as barras são renderizadas com altura 0 ou fora da área de plotagem.

O sintoma observado: o eixo Y direito exibe "1%, 0.75%, 0.5%, 0.25%, 0%" (os valores 0-1 formatados como percentuais) enquanto o eixo Y esquerdo mostra "0%-100%", e as barras simplesmente não aparecem.

**Correção recomendada — 2 opções:**

**Opção A (mais simples — sem `stackOffset`):** Pré-calcular os percentuais nos dados antes de passar ao Recharts e usar valores absolutos 0-100 em vez de `stackOffset="expand"`:
```js
// No processamento dos dados:
const dataWithPct = servers.map(s => {
  const total = s.churn + s.downtime + s.opsCost;
  return {
    ...s,
    churnPct:    (s.churn    / total) * 100,
    downtimePct: (s.downtime / total) * 100,
    opsCostPct:  (s.opsCost  / total) * 100,
    totalLabel:  formatCurrency(total),
  };
});
// No JSX, usar dataKey="churnPct" etc. com um único YAxis 0-100
// Remover o dual-axis e a linha de probabilidade desta visão (ou colocar em gráfico separado)
```

**Opção B (manter dual-axis, abandonar expand):** Manter as barras absolutas em R$ como antes, mas ajustar a **ordem do stack** (Ops Cost base → Downtime → Churn topo) para que Churn, a variável mais interessante, seja comparável entre servidores pela altura do topo.

**Nota: 2.0/10** *(era 5.0 — regressão de -3.0)*

---

## [GRÁFICO 6] KPI Cards — Monitoramento

**O que está mostrando:** Alertas Ativos (6), Próximo Incidente (menos de 1h), Probabilidade Média (40.1%), Servidores Monitorados (14).

**Importância:** Misto

**Veredicto:** ✅ Melhorou — ajustes pontuais remanescentes

**O que mudou desde v1:**

✅ **Ordem corrigida:** Alertas Ativos agora é o primeiro card — o usuário vê imediatamente o número mais operacional. Servidores Monitorados foi para o último lugar corretamente.

✅ **Falsa precisão eliminada:** `~0.4h` → `menos de 1h`. A informação de urgência é preservada (algo vai acontecer logo) sem comprometer credibilidade com precisão de minutos. Excelente.

**Problemas remanescentes:**

⚠️ **"Probabilidade Média" ainda presente:** a média de 40.1% dos 14 servidores continua sendo o terceiro KPI. Com BRZ-HOST-01 a 94% e a maioria dos servidores abaixo de 35%, esta média é enganosa. A sugestão de "Críticos Agora: 2/14" não foi implementada. Para o público gestor, saber que "2 servidores estão em estado crítico" é muito mais acionável que "a média é 40%".

⚠️ **Delta `+0.4%` na Probabilidade Média (Visão Técnica):** este delta continua presente e correto — bom detalhe técnico. Mas confirma que o card está voltado para o SRE (quem lê deltas de probabilidade), não para o gestor.

**Nota: 7.5/10** *(era 6.5 — ganho de +1.0)*

---

## [GRÁFICO 7] KPI Cards — Impacto Financeiro

**O que está mostrando:** Exposição Total (R$15.683.299), Perda por Churn Estimada (R$6.071.868), Receita em Risco (R$419.640).

**Importância:** Acionável

**Veredicto:** ✅ Melhorou significativamente — está bom

**O que mudou desde v1:**

✅ **Hierarquia corrigida:** Exposição Total (R$15.6M) agora é o primeiro card — o maior e mais impactante número aparece primeiro. A progressão agora faz sentido narrativo: visão total → impacto em clientes → impacto imediato.

✅ **Subtítulos semânticos adicionados:**
- "Total consolidado c/ multa SLA" — explica de onde vem o R$15.6M
- "Impacto de longo prazo (LTV)" — contextualiza o churn como consequência futura
- "Downtime nas próximas 6h" — ancora o R$419k no horizonte selecionado

Estes subtítulos resolvem a ambiguidade semântica que existia antes — o gestor agora entende a diferença entre os três números sem precisar perguntar.

**Problemas remanescentes:**

⚠️ **Sem referência relativa ao MRR:** R$15.6M ainda é um número absoluto sem escala. "≈ X% da receita mensal" ou "impacto de Y dias de receita" tornaria o número imediatamente interpretável para gestores que não conhecem de cor o faturamento da Locaweb.

⚠️ **Sem delta histórico:** nenhum dos três cards tem `↑/↓` comparativo com 24h atrás. O card de Probabilidade Média em Monitoramento tem o delta implementado — seria consistente aplicar o mesmo padrão aqui.

⚠️ **Receita em Risco (R$419k) está em branco/branco:** diferente dos outros dois cards (laranja e vermelho), o terceiro card não tem cor de destaque no valor — fica em branco. Visualmente parece menos urgente, o que pode ser intencional (R$419k é de fato o menor impacto), mas cria inconsistência de hierarquia visual.

**Nota: 8.0/10** *(era 6.5 — ganho de +1.5)*

---

## Resumo Geral — Comparativo v1 → v2

| Gráfico | Nota v1 | Nota v2 | Delta | Status |
|---|---|---|---|---|
| Risk Heatmap (Cards) | 7.5 | **8.5** | +1.0 | ✅ Melhorou |
| Time Series — Visão Geral | 7.0 | **7.0** | 0 | ⚠️ Inalterado |
| Time Series — Visão Técnica | 4.0 | **8.5** | **+4.5** | ✅ Maior melhoria |
| Feature Importance (DrillDown) | 6.0 | **8.0** | +2.0 | ✅ Melhorou |
| Financial ComposedChart — Geral | 7.0 | **7.0** | 0 | ⚠️ Inalterado |
| Financial ComposedChart — Técnica | 5.0 | **2.0** | **-3.0** | ❌ Regressão |
| KPI Cards — Monitoramento | 6.5 | **7.5** | +1.0 | ✅ Melhorou |
| KPI Cards — Financeiro | 6.5 | **8.0** | +1.5 | ✅ Melhorou |
| **Média geral** | **6.2** | **7.1** | **+0.9** | |

---

## Top 3 prioridades para v3

### 🚨 URGENTE — Corrigir regressão: barras sumindo no Financial Técnico

O `stackOffset="expand"` em ComposedChart com dual Y-axis é incompatível no Recharts. Pré-calcular os percentuais nos dados (`churnPct`, `downtimePct`, `opsCostPct`) e usar um único `<YAxis domain={[0,100]}>` resolve o problema sem perda de funcionalidade. Remover o eixo secundário nesta visão ou mover a linha de probabilidade para um segundo gráfico menor abaixo do principal.

### 2. Corrigir o Financial Geral: adicionar valor na ReferenceLine + rótulos dos eixos

É literalmente 1 prop: `label={{ value: "Limite R$600k", position: "insideTopLeft", fill: "#ffcc00" }}` na `<ReferenceLine>`. Adicionalmente, `<YAxis label={{ value: "Exposição (R$)", angle: -90 }} />` e `<YAxis yAxisId="right" label={{ value: "Probabilidade (%)", angle: 90 }} />`. Custo: ~10 linhas. Ganho: o gráfico se torna autoexplicativo.

### 3. Substituir KPI "Probabilidade Média" por "Servidores Críticos: 2/14"

Trocar o texto e o valor calculado de `mean(failProb)` por `count(failProb >= 75)` com denominador total. O valor "2/14" é imediatamente acionável para ambos os perfis: o SRE sabe quantos runbooks precisar executar, o gestor sabe a escala do problema. O delta `+0.4%` da Visão Técnica pode ser mantido como subtítulo do card.

---

## Considerações finais sobre a evolução

A dashboard evoluiu de **6.2 → 7.1** em média — uma melhoria real e perceptível. As duas mudanças de maior impacto visual (LineChart técnico + tendências no heatmap) foram executadas corretamente e transformaram a experiência de uso. O Feature Importance passou de "decorativo" para "genuinamente útil" com apenas 2 mudanças de prop.

O único ponto de atenção sério é a regressão no Financial Técnico — o gráfico simplesmente não renderiza as barras. Em um protótipo de alta fidelidade apresentado para uma banca FIAP, ter uma tela em branco é mais prejudicial do que ter o gráfico imperfeito que existia antes. **A correção deve ser a prioridade zero antes da apresentação.**

---

*Avaliação v2 realizada em 13/03/2026 | Dashboard localhost:5173 | MVP FIAP InfraPredict*
