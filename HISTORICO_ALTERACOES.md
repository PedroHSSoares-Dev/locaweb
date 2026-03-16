# Histórico de Alterações — Predictfy × Locaweb

> Documento gerado em 15/03/2026.
> Registra todas as criações e modificações realizadas nas sessões de revisão com Claude Code.
> Organizado cronologicamente por sessão.

---

## SESSÃO 1 — Revisão inicial, criação do CLAUDE.md e ajustes estruturais no EDA

### 1.1 — CRIADO: `CLAUDE.md`

**Arquivo:** `/locaweb/CLAUDE.md`
**Motivo:** O projeto não tinha um documento de referência rápida para contextualizar qualquer futura conversa ou colaboração. Sem esse documento, a cada nova sessão seria necessário reexplicar todo o contexto do projeto, as regras de negócio, os prazos e as restrições técnicas.

**O que contém:**
- Identidade do projeto (nome, FIAP Challenge 2026, turma, parceiro)
- Contexto de negócio completo: OLAs (P2=4h, P3=12h), metas anuais de violações, definição do subset KPI
- Regra do target e motivo de ser `KPI Violado?` e não `Duração > OLA`
- Lista explícita de colunas que são **data leakage** (Duração, Resolvido, Encerrado, Código de fechamento, Solução)
- Tabela completa das 24 features do modelo com tipo e origem
- Arquitetura da solução (dataset → modelos → JSONs → dashboard → chatbot)
- Stack tecnológica (Prophet, XGBoost, K-Means, SHAP, React, Gemini)
- Status de cada notebook (quais existem ✅, quais estão pendentes ❌)
- Status do código Python em `src/` (tudo pendente)
- Rotas do dashboard e perfis de usuário
- Arquitetura do chatbot (Gemini Flash roteador + Gemini Pro analista)
- Prazos dos sprints (Sprint 1: 12/04/2026, Sprint 2: 17/05/2026)
- Localização de arquivos importantes
- Top 13 achados críticos da EDA

---

### 1.2 — MODIFICADO: `notebooks/01_eda.ipynb` — Rodada 1

**Arquivo:** `/locaweb/notebooks/01_eda.ipynb`
**Estado anterior:** 42 células
**Estado após:** 51 células (+9 células novas)

#### 1.2.1 — Adicionada: Seção 0 — Objetivos da EDA

**Posição:** Célula [01] (antes da Seção 1)
**Tipo:** Markdown
**Motivo:** A metodologia da Aula 03 (IADLA) exige que toda EDA comece com a definição explícita de 6 objetivos seguindo o processo KDD (Knowledge Discovery in Databases). O notebook original pulava direto para o setup sem declarar o que a análise se propunha a fazer. A ausência dessa seção compromete a nota no critério _"Clareza na definição do problema"_ (critério de avaliação da banca Locaweb, slide 11 do PDF).

**O que foi adicionado:**
```markdown
Objetivos 1 a 6:
1. Obter e organizar os dados com rastreabilidade
2. Compreender a estrutura do dataset
3. Avaliar a qualidade dos dados
4. Investigar o comportamento univariado
5. Explorar relações multivariadas
6. Consolidar achados e decisões
```

---

#### 1.2.2 — Adicionada: Seção 3.5 — Análise de Subcategoria (dataset completo)

**Posição:** Células [19] e [20] (antes da Seção 4)
**Tipo:** Markdown + Código
**Motivo:** A coluna `Subcategoria` foi **completamente omitida** no notebook original. Não havia nenhuma análise univariada dela. Dado que posteriormente o Cramér's V revelou ser a feature com maior associação com o target (0.32), a ausência dessa análise era uma lacuna grave.

**O que foi adicionado:**
- Contagem de subcategorias únicas (447 únicas)
- Percentual de nulos (63.4%)
- Gráfico de barras horizontais com Top 20 subcategorias por volume

---

#### 1.2.3 — Adicionada: Seção 6.4 — Subcategoria no subset KPI

**Posição:** Células [40] e [41]
**Tipo:** Markdown + Código
**Motivo:** Complemento da seção 3.5, mas agora focando nos incidentes que realmente entram para KPI. Necessário para avaliar a relevância da feature nos dados de treino.

**O que foi adicionado:**
- Top 15 subcategorias por volume no subset KPI
- Top 15 subcategorias por taxa de violação (mínimo 10 incidentes)
- Contagem de nulos no subset KPI (apenas 0.1%)

---

#### 1.2.4 — Adicionada: Seção 6.5 — EDA Bivariada com Cramér's V

**Posição:** Células [42] e [43]
**Tipo:** Markdown + Código
**Motivo:** O notebook original tinha apenas uma matriz de correlação com 5 variáveis numéricas. Para features categóricas, a correlação de Pearson não se aplica. A metodologia da Aula 03 demonstra análise de associação entre features e o target. O **Cramér's V** é a métrica correta para associação entre duas variáveis categóricas (ou categórica × binária).

**O que foi adicionado:**
- Função `cramers_v()` implementada com correção de viés (phi² corrigido)
- Cálculo do Cramér's V para 9 features categóricas vs `KPI Violado?`
- Gráfico de barras horizontais com ranking de associação
- Linhas de referência: > 0.3 = forte, > 0.1 = moderado

**Resultado revelado:**
```
Subcategoria:        0.3166  ← maior de todos (inesperado)
Grupo designado:     0.1139
Categoria:           0.0860
Código fechamento:   0.0760
Produto:             0.0715
Aberto por:          0.0385
dia_semana:          0.0253
Prioridade:          0.0049  ← quase zero (contraintuitivo)
hora:                0.0000  ← zero (contraintuitivo)
```

---

#### 1.2.5 — Adicionada: Seção 6.6 — Cross-análise Grupo × Produto × KPI Violado?

**Posição:** Células [44] e [45]
**Tipo:** Markdown + Código
**Motivo:** O PDF da Locaweb (slide 9) exige explicitamente _"Agrupamentos críticos (produto + categoria + prioridade)"_. A análise marginal de grupos e produtos individualmente não captura o risco das combinações. Um grupo pode ter taxa baixa individualmente mas concentrar alto risco em produto específico.

**O que foi adicionado:**
- Agrupamento Grupo × Produto com volume, violações e taxa
- Filtro: mínimo 10 incidentes para confiabilidade estatística
- Top 15 combinações por taxa de violação

**Resultado revelado:**
```
Team09 + lssl:  16.67% (18 incidentes, 3 violações)
Team03 + lvps:  14.29% (42 incidentes, 6 violações)
Team07 + lexc:   9.23% (130 incidentes, 12 violações)
Team11 + lsin:   7.31% (547 incidentes, 40 violações)
```

---

## SESSÃO 2 — Revisão pós-execução vs PDF Locaweb

Após a execução do notebook, os outputs revelaram inconsistências críticas e lacunas em relação aos requisitos do PDF da Locaweb (`Locaweb_FIAP_Apresentação_V2.pdf`).

### 2.1 — MODIFICADO: `notebooks/01_eda.ipynb` — Rodada 2

**Estado anterior:** 51 células
**Estado após:** 61 células (+10 células novas, 2 células corrigidas)

---

#### 2.1.1 — CORRIGIDA: Célula 4.4 — Validação do target

**Posição:** Célula [25]
**Tipo:** Código (modificação de conteúdo existente)
**Problema encontrado:** A célula original tinha um bloco `else` que imprimia:
```
✅ O campo KPI Violado? é 100% consistente com Duração > OLA
```
Porém, o output ao executar mostrou **3.399 divergências**, tornando essa afirmação **factualmente errada**. Deixar uma conclusão errada em um notebook de apresentação comprometeria a credibilidade do projeto perante a banca.

**O que foi corrigido:**
- Removido o `else` com a afirmação incorreta
- Adicionado print explícito alertando sobre as 3.399 divergências
- Mensagem direcionando para a nova seção 4.4b
- Conclusão correta: _"TARGET CORRETO: usar campo KPI Violado? (ground truth de negócio)"_

---

#### 2.1.2 — Adicionada: Seção 4.4b — Investigação das 3.399 divergências

**Posição:** Células [26] e [27] (logo após 4.4)
**Tipo:** Markdown + Código
**Motivo:** A simples constatação de 3.399 divergências sem explicação seria um problema em aberto na análise. A banca perguntaria: _"Por que 3.398 incidentes têm Duração > OLA mas estão marcados como KPI = NAO?"_ Essa seção investiga e explica.

**O que foi adicionado:**
- Filtro dos incidentes divergentes (KPI = NAO mas Duração > OLA)
- Análise do `Status` dos divergentes
- Análise do `Código de fechamento` dos divergentes
- Distribuição por Prioridade
- Percentis da duração dos divergentes (para mostrar que são os outliers extremos)
- Top 10 grupos com mais divergências
- Conclusão: os divergentes têm durações absurdas (P50 já acima do OLA normal), indicando incidentes com pausas de SLA ou exceções de negócio aprovadas

**Impacto na modelagem:** Confirmado que `KPI Violado?` é o target correto, não `(Duração > OLA)`.

---

#### 2.1.3 — Adicionada: Seção 5.6 — Representatividade Histórica

**Posição:** Células [34] e [35] (após 5.5)
**Tipo:** Markdown + Código
**Motivo:** O output da célula 5.5 mostrou:
```
P3 2023: 4 violações ⚠️
P3 2024: 6 violações ⚠️
P3 2025: 196 violações
```
O notebook marcava ⚠️ sem nenhuma explicação. Isso é um achado crítico: com apenas 4 e 6 violações em anos inteiros versus 196 em 2025, fica evidente que o KPI de P3 só passou a ser monitorado sistematicamente em 2025. Usar 2023/2024 para treinar o modelo de classificação contaminaria o treino com dados sem violações registradas por razão administrativa (não operacional).

**O que foi adicionado:**
- Tabela volume × violações por ano e prioridade
- Volume total do dataset por ano (comparativo)
- Dois gráficos de barra: volume KPI por ano e violações por ano
- Diagnóstico textual explicando a sub-representação
- Recomendação formal:
  - **XGBoost (classificação):** usar apenas 2025
  - **Prophet (volume):** dados 2023-2025 são válidos para sazonalidade

---

#### 2.1.4 — Adicionada: Seção 6.7 — Incidentes Recorrentes

**Posição:** Células [46] e [47]
**Tipo:** Markdown + Código
**Motivo:** O PDF da Locaweb (slide 9) lista explicitamente como requisito: _"Incidentes recorrentes"_. Sem esta análise, o projeto deixa em aberto um dos 4 eixos analíticos cobrados. Incidentes recorrentes com alta taxa de violação são candidatos a alertas proativos no dashboard.

**O que foi adicionado:**
- Normalização da `Descrição resumida` (lowercase + strip)
- Contagem de descrições únicas e distribuição de frequência
- Top 20 descrições mais frequentes (min 5 ocorrências)
- Gráfico 1: Top 15 por volume (descrições mais comuns)
- Gráfico 2: Top 15 por taxa de violação (descrições mais perigosas)
- Limpeza da coluna temporária após análise

---

#### 2.1.5 — Adicionada: Seção 6.8 — Trivariate Produto × Categoria × Prioridade

**Posição:** Células [48] e [49]
**Tipo:** Markdown + Código
**Motivo:** O PDF (slide 9) exige _"Agrupamentos críticos (produto + categoria + prioridade)"_ — três variáveis simultaneamente. A seção 6.6 fazia apenas Grupo × Produto (duas variáveis). A análise trivariate é mais rica e alinhada ao requisito do desafio.

**O que foi adicionado:**
- Agrupamento Produto × Categoria × Prioridade com volume, violações e taxa
- Top 20 combinações por taxa (mínimo 10 incidentes)
- Heatmap Produto × Categoria (top 12 produtos × top 10 categorias) com taxa de violação como cor

---

#### 2.1.6 — Adicionada: Seção 6.9 — Explicação dos Cramér's V Contraintuitivos

**Posição:** Células [50] e [51]
**Tipo:** Markdown + Código
**Motivo:** Três resultados do Cramér's V (seção 6.5) são contraintuitivos e, se não explicados, gerariam dúvidas ou questionamentos na banca:
1. **Prioridade ≈ 0**: parece estranho que a prioridade não prediga violação
2. **hora = 0**: parece estranho que a hora do dia não influencie
3. **Subcategoria = 0.32 com 63% nulos**: parece contraditório

**O que foi adicionado:**
- Bloco 1 (Prioridade): demonstra que P2 e P3 têm taxas de violação similares no subset KPI porque o OLA escala com a prioridade — logo a prioridade não discrimina, ela define o threshold
- Bloco 2 (hora): mostra taxa de violação por hora do dia (praticamente flat), explicando que a hora influencia o _volume_ de incidentes (Prophet), não a _probabilidade de violação_ (XGBoost)
- Bloco 3 (Subcategoria): compara taxa de violação entre registros com subcategoria preenchida vs "DESCONHECIDO", mostrando que a ausência em si é um sinal

---

#### 2.1.7 — REESCRITA COMPLETA: Seção 8 — Conclusões

**Posição:** Célula [59]
**Tipo:** Markdown (substituição total do conteúdo)
**Motivo:** A seção de conclusões original tinha:
1. A afirmação incorreta sobre o target (já corrigida na célula 4.4, mas a conclusão final ainda dizia "KPI Violado? é consistente com Duração > OLA")
2. A tabela de features sem o Cramér's V (que agora é a métrica mais informativa disponível)
3. Nenhuma menção à janela de treino recomendada (2025)
4. Nenhuma menção ao erro de target
5. Achados da banca desatualizados

**O que foi reescrito:**
- Tabela de features atualizada com coluna de Cramér's V e ordenada por poder discriminativo
- Nova seção: **TARGET CORRETO** — explicação da decisão de usar `KPI Violado?` (com menção às 3.399 divergências)
- Nova seção: **JANELA DE TREINAMENTO RECOMENDADA: 2025** — com distinção clara entre dados para XGBoost vs Prophet
- Seção de Data Leakage convertida para tabela (mais clara)
- Estratégia de nulos atualizada mencionando o Cramér's V da subcategoria
- Seção de outliers P3 conectada ao achado das divergências
- Seção de desbalanceamento atualizada com PR-AUC como métrica adicional
- **Top 10 achados para a banca** — lista concisa dos descobertas mais importantes com números concretos

---

## Resumo consolidado de todos os arquivos alterados

| Arquivo | Tipo de mudança | Células/Seções afetadas |
|---|---|---|
| `CLAUDE.md` | **Criado** (novo arquivo) | — |
| `notebooks/01_eda.ipynb` | **Modificado** — 19 células adicionadas/corrigidas | Seções 0, 3.5, 4.4, 4.4b, 5.6, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 8 |

### Contagem de células do notebook

| Estado | Células |
|---|---|
| Original (antes de qualquer alteração) | 42 |
| Após Sessão 1 | 51 (+9) |
| Após Sessão 2 | 61 (+10) |
| **Total de células adicionadas** | **+19** |
| **Total de células corrigidas** | **2** (4.4 e 8) |

---

## Mapa de seções do notebook (estado final)

| Seção | Células | Conteúdo | Status |
|---|---|---|---|
| 0 | [01] | Objetivos da EDA (6 itens KDD) | 🆕 Adicionado |
| 1 | [02-06] | Setup e carregamento | ✅ Original |
| 2 | [07-13] | Qualidade dos dados (nulos, duplicatas, duração) | ✅ Original |
| 3 | [14-20] | Distribuições e regras de negócio | ✅ + 3.5 adicionado |
| 4 | [21-27] | Subset KPI + target + validação + investigação divergências | ✅ + 4.4b adicionado, 4.4 corrigido |
| 5 | [28-35] | Análise temporal + representatividade histórica | ✅ + 5.6 adicionado |
| 6 | [36-51] | Produtos/grupos/categorias + Cramér's V + análises avançadas | ✅ + 6.4-6.9 adicionados |
| 7 | [52-58] | Investigações adicionais (duração, outliers, correlação) | ✅ Original |
| 8 | [59] | Conclusões e decisões de feature engineering | 🔄 Reescrito |

---

## Decisões técnicas tomadas e seus motivos

### 1. Target correto: `KPI Violado?` (não `Duração > OLA`)
**Motivo:** 3.399 incidentes têm Duração > OLA mas KPI = NAO, indicando regras de negócio (pausas de SLA, exceções). O campo original reflete o ground truth real da Locaweb.

### 2. Janela de treino XGBoost: apenas 2025
**Motivo:** P3 2023 e 2024 têm 4 e 6 violações respectivamente — subregistro administrativo, não operacional. Treinar com dados anteriores incluiria amostras "limpas" por razão incorreta (MNAR no target).

### 3. Subcategoria como feature prioritária
**Motivo:** Cramér's V = 0.32, o maior de todas as features testadas. Apesar de 63% de nulos no dataset total, no subset KPI apenas 0.1% são nulos. A ausência de subcategoria ("DESCONHECIDO") é um sinal preditivo válido.

### 4. Prioridade mantida como feature apesar de Cramér's V ≈ 0
**Motivo:** Cramér's V mede associação marginal. Prioridade tem valor interativo (combinada com outras features) e define o contexto do incidente. O XGBoost capturará interações que o Cramér's V não detecta.

### 5. Hora do dia mantida como feature para Prophet, questionada para XGBoost
**Motivo:** Cramér's V = 0 indica ausência de associação direta com violação OLA. Mas a hora influencia fortemente o volume de incidentes (sazonalidade no Prophet). Para o XGBoost, seu valor dependerá de validação no notebook 04.
