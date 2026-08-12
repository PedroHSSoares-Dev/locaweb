# Avaliação independente — Predictfy × Locaweb AIOps

**Overall verdict:** Predictfy é um MVP AIOps forte, coeso e excepcionalmente transparente para um projeto acadêmico; está pronto para uma apresentação FIAP em desktop, mas a falha móvel, inconsistências entre números/modelos e a ausência de um ciclo operacional fechado bloqueiam um piloto real na Locaweb.

- Pontuação ponderada: **7,21/10**
- Prontidão para hackathon: **8,3/10**
- Prontidão para piloto corporativo: **5,4/10**
- Confiança da avaliação: **alta — 92%**
- Escopo efetivo: todas as rotas visíveis, autenticação, 11 perguntas ao assistente e viewports de 1440×900, 1280×720 e 390×844.
- A avaliação foi estritamente visual pelo navegador; nenhum código, repositório, DOM oculto ou payload de rede foi inspecionado.

## Primeira impressão

Antes da autenticação, um visitante entende em 15 segundos que se trata de uma plataforma operacional protegida por Microsoft Entra ID com um assistente AIOps. Ele ainda não entende exatamente qual problema de negócio será resolvido.

Após o login, a mensagem fica imediatamente clara: **P2 está fora da faixa e requer prioridade; P3 está controlado**. O alerta vermelho, as 42 violações e as ações “Priorizar P2”, “Revisão semanal” e “Escalar” dominam corretamente a atenção.

O produto parece uma solução AIOps coerente, não uma coleção aleatória de dashboards. A progressão Gestão → Monitoramento → Técnico → Modelos → Administração é lógica e o chatbot preserva essa narrativa.

## Scorecard ponderado

A contribuição é calculada como `peso × nota ÷ 10`. A soma matemática é **7,214**, arredondada para **7,21/10**.

| Critério | Peso | Nota | Contrib. | Evidência observada | Principal fraqueza | Melhoria recomendada | Pri. | Esforço |
|---|---:|---:|---:|---|---|---|---|---|
| Valor executivo e história de negócio | 10% | 8,0 | 0,800 | Gestão abre com P2 fora da faixa, P3 controlado e ações claras. | Não há impacto financeiro ou custo operacional visível. | Relacionar violações a risco/capacidade, sem inventar ROI. | P1 | Médio |
| Arquitetura de informação e navegação | 7% | 7,5 | 0,525 | Cinco rotas com públicos e perguntas distintos; contexto do chat acompanha a rota. | Alguns indicadores reaparecem em várias telas sem ligação explícita. | Manter resumos e adicionar “ver investigação completa”. | P2 | Pequeno |
| Hierarquia visual e escaneabilidade | 7% | 7,5 | 0,525 | Alertas, módulos numerados e cards são rapidamente escaneáveis. | Telas Técnico e Modelos ficam densas abaixo da primeira dobra. | Destacar decisão principal e recolher detalhes metodológicos. | P2 | Pequeno |
| Tipografia e legibilidade | 6% | 6,8 | 0,408 | Títulos e números principais são legíveis. | Legendas, timestamps e textos cinza são pequenos e de baixo contraste. | Aumentar contraste e tamanho mínimo das informações secundárias. | P2 | Pequeno |
| Consistência visual e acabamento | 6% | 7,5 | 0,450 | Identidade dark, cores funcionais e componentes consistentes. | Estados técnicos transitórios e mensagens internas quebram o acabamento. | Substituir mensagens de artefato por estados de carregamento seguros. | P1 | Pequeno |
| Clareza de KPI e interpretação | 7% | 8,2 | 0,574 | Faixas 36–39 e 231–263, consumo e status estão explicados. | Total previsto não fecha com P2+P3: 66 vs. 67 e 62 vs. 58. | Explicar ao lado dos cards que as séries são independentes ou reconciliá-las. | P0 | Médio |
| Comunicação de previsão e risco | 8% | 6,7 | 0,536 | D+1/D+7, MAE, histórico e separação entre score e probabilidade são visíveis. | Gestão não exibe intervalo de incerteza ou faixa operacional. | Mostrar intervalo/tolerância e data da última atualização. | P1 | Médio |
| Ação operacional e drill-down | 8% | 6,5 | 0,520 | Monitoramento traz ações antes do turno, durante o pico e gatilho; Técnico aponta Team07 e Cluster 4. | Não há incidente, dono, reconhecimento, runbook ou encerramento. | Criar fila de investigação com responsável e resultado observado. | P1 | Grande |
| Transparência de modelos e confiança | 7% | 7,3 | 0,511 | Desbalanceamento, PR-AUC, recall, precision, matriz de confusão e limitações são muito bem explicados. | K-Means mostra 0,1994 no resumo e 0,1965 na tabela; chatbot recomenda Prophet enquanto a tela marca LSTM como ativo. | Usar uma fonte única para métricas, status e respostas do agente. | P0 | Médio |
| UX e qualidade do chatbot | 10% | 7,0 | 0,700 | Respostas estruturadas, fontes, limitações, ações, modos Rápido/Profundo e Markdown correto. | Uma resposta sobre modelos contradisse a governança; houve estado transitório “LLM OFFLINE”. | Validar respostas críticas contra o registro de modelos e oferecer fallback explicativo. | P0 | Médio |
| Integração dashboard–chatbot | 6% | 8,0 | 0,480 | Ao trocar de rota, o chat oferece “usar nova rota” ou “manter contexto”; resposta técnica usou corretamente o Cluster 4. | Duplo clique não restaurou a largura padrão durante o teste. | Corrigir restauração e indicar visualmente o contexto usado em cada resposta. | P2 | Pequeno |
| Performance e estados do sistema | 5% | 6,7 | 0,335 | Rotas responderam bem; 11 respostas tiveram mediana de 6,55 s. | Monitoramento mostrou momentaneamente “modelo não treinado / executar notebook”; chat variou até 10,87 s e exibiu “offline”. | Usar skeleton, timeout claro, retry e fallback. | P1 | Médio |
| Responsividade e acessibilidade | 5% | 4,2 | 0,210 | Técnico e chat móvel funcionaram bem; tabela e código têm overflow local; não houve scroll horizontal da página. | Gestão/Monitoramento ficaram comprimidos a ~76 px após navegação móvel; hamburger mede 38×38 px. | Corrigir reserva de largura do chat nas trocas de rota e adotar alvos mínimos de 44 px. | P0 | Médio |
| Autenticação e confiança de sessão | 4% | 8,0 | 0,320 | Login explica Microsoft, Entra ID e acesso protegido; autenticação foi fluida e RBAC é visível. | Não há política, escopos ou trilha de alterações apresentados ao usuário. | Exibir resumo de dados acessados e auditoria administrativa. | P1 | Médio |
| Narrativa de demo e diferenciação | 4% | 8,0 | 0,320 | Une KPI, previsão, investigação, governança e agente contextual. | Mobile, inconsistências e estados transitórios podem quebrar confiança ao vivo. | Roteiro desktop ensaiado e preflight de dados/modelos/LLM. | P0 | Pequeno |

## Avaliação por perfil

| Perspectiva | Nota | Ponto mais forte | Principal preocupação | Necessário para aprovação |
|---|---:|---|---|---|
| Diretor executivo Locaweb | 7,8 | P2/P3 e prioridade executiva são compreendidos sem conhecimento de ML. | Falta impacto financeiro e confiança nos números não reconciliados. | Faixas de incerteza, consistência e prova de ganho operacional. |
| Operações/SRE | 6,2 | Briefing D+1, equipe crítica, gatilho e Cluster 4 indicam onde começar. | Não há ciclo alerta → responsável → runbook → resultado. | Fila operacional, ownership, integração ITSM e piloto sombra. |
| Dados/ML | 7,0 | Transparência sobre desbalanceamento, validação e limites é acima da média. | Precision de 3,1%, métricas inconsistentes e recomendação conflitante do chatbot. | Registro único de modelos e comparação temporal reconciliada. |
| Segurança/governança | 7,1 | Microsoft Entra, RBAC, diretório e consumo do agente são visíveis. | Cinco das nove identidades são administradoras e não há auditoria visível. | Least privilege, log de alterações, retenção e política de dados. |
| Juiz FIAP | 8,8 | Produto completo, visualmente maduro e com comunicação responsável de IA. | Uma falha móvel ou contradição ao vivo prejudicaria fortemente a apresentação. | Desktop estável, narrativa curta e correções P0. |

As revisões independentes por screenshots convergiram: nota alta para banca/executivo, intermediária para SRE e forte penalização da responsividade móvel.

## Cinco maiores forças

1. **Norte executivo imediato:** P2 exige ação; P3 está controlado.
2. **Governança de ML excepcional para um hackathon:** a aplicação explica por que 99% de acurácia seria inútil.
3. **Separação responsável entre fato, previsão, cenário e hipótese:** score não é probabilidade; cluster não é causa.
4. **Monitoramento orientado a ação:** escala, acompanhamento e gatilho aparecem junto dos números.
5. **Chat contextual de verdade:** sintetiza rotas, apresenta fontes, limitações e ações, em vez de apenas repetir cards.

## Cinco maiores fraquezas

1. **Falha móvel crítica:** Gestão e Monitoramento ficaram comprimidos e ilegíveis após a sequência chat → recolher → trocar rota; reload não recuperou.
2. **Inconsistências de confiança:** silhouette 0,1994 vs. 0,1965; Prophet recomendado pelo chat vs. LSTM marcado como ativo; previsões agregadas não reconciliadas.
3. **Ausência de circuito operacional fechado:** não há incidentes, donos, runbooks, reconhecimento ou medição da ação tomada.
4. **Viabilidade limitada do XGBoost no corte atual:** 70,7% de recall, mas apenas 3,1% de precision e 1.281 falsos alertas para 41 acertos.
5. **Dados e estados de demo:** base observada termina em 31/12/2025; apareceram “LLM OFFLINE”, “modelo não treinado” e instrução para executar notebook.

## Respostas às perguntas centrais

| Pergunta | Resposta |
|---|---|
| Um visitante entende o produto em 15 segundos? | Parcialmente antes do login; claramente após entrar na Gestão. |
| Um diretor entende o risco sem conhecer ML? | Sim. P2/P3, faixas e ações são claros. |
| Um SRE sabe o que investigar? | Parcialmente: Team07 e Cluster 4 são bons pontos de partida, mas faltam incidentes e responsáveis. |
| Fatos, previsões, cenários e hipóteses são diferenciados? | Em geral, sim e melhor que a média; a Gestão ainda precisa de incerteza mais visível. |
| Limitações evitam mau uso? | Sim para XGBoost/K-Means; menos consistentemente para forecasts e respostas do chatbot. |
| O dashboard comunica ação? | Sim, mas não permite registrar ou acompanhar a ação. |
| O chatbot melhora o dashboard? | Sim: sintetiza, contextualiza e explicita limites. Uma resposta crítica, porém, contradisse a tela de Modelos. |
| Vale o espaço de tela? | Sim no desktop, pois é recolhível e redimensionável; no mobile funciona como tela cheia. |
| A identidade visual é coerente? | Sim, com aparência AIOps corporativa; é mais “Predictfy tech” do que identidade oficial Locaweb. |
| Os módulos estão nas rotas corretas? | Quase todos; apenas mensagens de regeneração e detalhes de artefato estão na rota errada. |
| Há módulo desnecessário? | Não. Há repetições úteis, desde que sejam tratadas como resumo e drill-down. |
| Qual capacidade visível falta? | Fila de incidentes priorizada com responsável, runbook, reconhecimento e feedback. |
| O que mais impressiona a banca? | A combinação de história executiva, governança honesta e chatbot contextual. |
| O que mais prejudica a demo? | Layout móvel quebrado; depois, inconsistências e estados “offline/não treinado”. |
| Aprovaria? | FIAP: sim em desktop. Final de hackathon: condicional. Piloto Locaweb: não ainda. |

## Backlog recomendado

### P0 — antes da próxima apresentação

| Tipo | Recomendação | Problema resolvido | Esforço |
|---|---|---|---|
| Estrutural | Corrigir a largura reservada pelo chat no breakpoint móvel e nas trocas de rota. | Gestão/Monitoramento ficam praticamente ilegíveis. | Médio |
| Quick win | Unificar métricas e status usados por dashboard e chatbot. | Silhouette e recomendação Prophet/LSTM entram em conflito. | Médio |
| Quick win | Explicar ou reconciliar Total, P2 e P3 junto dos cards. | 66 ≠ 13+54 e 62 ≠ 14+44 parecem erro. | Pequeno |
| Quick win | Remover “executar notebook/regenere o XGBoost” da experiência de apresentação. | Linguagem interna quebra a percepção de produto acabado. | Pequeno |
| Quick win | Criar estados seguros para LLM offline e carregamento da sazonalidade. | Estado transitório pode parecer falha completa. | Médio |

### P1 — melhorias de alto valor

| Tipo | Recomendação | Problema resolvido | Esforço |
|---|---|---|---|
| Estrutural | Criar fila de investigação com incidente, prioridade, score, responsável e status. | SRE sabe o perfil, mas não o caso a investigar. | Grande |
| Estrutural | Mostrar faixa de incerteza e data de atualização dos forecasts. | Números pontuais podem ser tratados como promessa. | Médio |
| Estrutural | Apresentar orçamento de alertas e carga estimada de triagem. | Precision de 3,1% pode inviabilizar a operação. | Médio |
| Quick win | Transformar Team07 e Cluster 4 em links para investigação detalhada. | Hoje são indicações sem próximo passo clicável. | Pequeno |
| Estrutural | Adicionar trilha administrativa visível. | Não há evidência de quem alterou acesso ou privilégio. | Grande |

### P2 — acabamento

- Aumentar contraste de legendas, timestamps e fontes.
- Aumentar o hamburger móvel de 38×38 para pelo menos 44×44 px.
- Tornar mais evidente que tabelas e blocos de código podem ser rolados horizontalmente.
- Corrigir o duplo clique para restaurar a largura do chat.
- Reduzir sobreposição do botão flutuante sobre cards móveis.

### Recursos corporativos que não precisam ser construídos apenas para o hackathon

Para um piloto, mas não para ganhar a apresentação, seriam necessários:

- integração de leitura/escrita com o ITSM;
- auditoria e retenção corporativa;
- monitoramento de drift e qualidade dos modelos;
- SLO do agente e fallback;
- piloto sombra com comparação contra baseline;
- métricas de alertas aceitos, falsos positivos, tempo de triagem e OLAs potencialmente evitadas.

## Decisão sobre módulos

### Devem permanecer

- Norte executivo, metas OLA e histórico em Gestão.
- Briefing D+1, série temporal e fila de atenção em Monitoramento.
- Risco por equipe, XGBoost e perfis de clusters em Técnico.
- Registro, métricas, matriz de confusão e limitações em Modelos.
- RBAC e consumo do agente em Administração.
- Chatbot lateral contextual.

### Devem mover ou ser resumidos

- “Regenere o XGBoost” deve sair de Técnico e virar estado operacional em Modelos/Administração.
- Monitoramento deve manter apenas resumo do orçamento OLA; a explicação completa pertence à Gestão.
- Monitoramento deve manter o top 1 de equipes; o ranking completo pertence ao Técnico.
- Métricas de qualidade do K-Means ficam em Modelos; perfis e implicações ficam em Técnico.
- Administração não deve fazer parte da demonstração de três minutos.

## Veredictos específicos

### Chatbot

**Vale o espaço e melhora o produto.** O assistente foi descoberto facilmente, funcionou recolhido, expandido, redimensionado e em tela cheia móvel. A mudança de Gestão para Técnico apresentou explicitamente “usar Técnico” ou “manter Gestão”; após selecionar Técnico, a resposta indicou corretamente o Cluster 4.

Nas 11 perguntas:

- tempo mínimo: **4,87 s**;
- mediana: **6,55 s**;
- média: **7,14 s**;
- máximo: **10,87 s**.

As respostas foram fortes em limitações, ações e fontes. Tabelas e código usam overflow local (`auto`) e não causaram scroll horizontal da página. A principal falha de conteúdo foi recomendar Prophet como referência provisória quando a tela de Modelos identifica LSTM como ativo e mostra vantagem no mesmo holdout.

### Autenticação e sessão

A autenticação foi clara e confiável:

- login branded e explicação do motivo do acesso;
- seleção da conta Microsoft já autenticada;
- retorno fluido ao dashboard;
- nenhuma senha ou MFA foi solicitada;
- nenhuma informação extra foi exibida antes do login.

A Administração mostra RBAC, diretório, status e consumo do agente. Para um piloto, faltam trilha de auditoria, política de retenção, scopes em linguagem simples e demonstração de least privilege. Não foi feito logout global da Microsoft.

### Responsividade e acessibilidade

O resultado foi misto:

- 1440×900 e 1280×720: sem scroll horizontal da página e com bom split dashboard/chat.
- Técnico em 390×844: cards e gráfico adaptados corretamente.
- Chat móvel: tela cheia, composer fixo e controles de 44×44 px.
- Tabela móvel: área local 309 px para conteúdo de 1.421 px.
- Código móvel: área local 309 px para conteúdo de 2.637 px.
- Navegação móvel: linhas de 44 px; hamburger de apenas 38 px.
- Gestão/Monitoramento móvel após troca de rota: **falha P0, persistente mesmo após reload**.

## Demonstração ideal de três minutos

### 0:00–0:20 — Gestão

Abra `/gestao`.

Diga:

> “Predictfy transforma três anos de incidentes em decisões operacionais. O norte hoje é simples: P2 ultrapassou a faixa de negócio; P3 permanece controlado. A plataforma separa o que sabemos, o que prevemos e o que ainda precisa ser investigado.”

### 0:20–0:55 — KPI principal

Mostre:

- P2: 42 violações, faixa 36–39;
- P3: 196, dentro da faixa 231–263;
- ações: priorizar P2 e revisar semanalmente.

### 0:55–1:30 — Monitoramento

Mostre o briefing D+1:

- 66 incidentes;
- P2 13;
- P3 54;
- ações antes do turno, durante o pico e gatilho.

Explique imediatamente que as séries são independentes e não precisam somar exatamente ao total.

### 1:30–1:55 — Modelos

Mostre o XGBoost:

- recall 70,7%;
- precision 3,1%;
- uso permitido: ordenar triagem humana, não automatizar resposta.

Isso demonstra maturidade, não fraqueza.

### 1:55–2:35 — Chatbot

Pergunte:

> “O que os dados não permitem concluir?”

A resposta observada distinguiu causalidade, previsão, score, limitações e ausência de tempo real.

### 2:35–3:00 — Fechamento

> “O valor do Predictfy não é adivinhar incidentes nem automatizar decisões frágeis. É antecipar pressão, concentrar a atenção humana onde o risco é maior e tornar cada recomendação explicável e auditável.”

Não mostre **Administração** na demo de três minutos: é útil para governança, mas consome tempo e pode expor identidades.

Pergunta provável da banca:

> “Com apenas 3,1% de precision, o XGBoost é realmente útil?”

Melhor resposta:

> “Não como alarme automático. No teste, capturou 41 de 58 violações, mas produziu 1.281 falsos positivos. Por isso o produto o apresenta como score de ordenação para revisão humana. A próxima validação é um piloto sombra com orçamento de alertas e medição da carga de triagem.”

## Aprovação final

| Decisão | Veredicto | Condições |
|---|---|---|
| Pronto para apresentação FIAP | **Sim** | Usar desktop, executar preflight e explicar reconciliação e baixa precision. |
| Pronto para final de hackathon | **Condicional** | Corrigir os P0 de responsividade, consistência e estados transitórios. |
| Pronto para piloto controlado Locaweb | **Não** | Exige dados atuais, fila operacional, auditoria, alert budget e piloto sombra. |

## Rotas e estados avaliados

| Rota/estado | O que foi efetivamente testado |
|---|---|
| `/gestao` não autenticada | Login, mensagem de acesso protegido e botão Microsoft. |
| Autenticação Microsoft | Seletor de conta autorizado e retorno ao app; sem senha/MFA. |
| `/gestao` autenticada | Alertas, metas, capacidade D+1/D+7, histórico; 1440×900 e mobile. |
| `/monitoramento` | Briefing, série temporal, sazonalidade, fila operacional; desktop e mobile. |
| `/tecnico` | Equipes, score XGBoost, SHAP, clusters; 1440×900, 1280×720 e 390×844. |
| `/modelos` | Abas XGBoost, Prophet & LSTM e K-Means. |
| `/admin` | Resumo RBAC, criação de acesso, diretório e consumo; somente leitura. |
| Chatbot | Recolhido, expandido, redimensionado, mobile, nova conversa, Rápido/Profundo, 11 perguntas, tabela, código e troca de contexto. |
| Layout | 1440×900, 1280×720 e 390×844; overflow local e largura da página. |

Não foram avaliados: logout global, senha/MFA, erros de autenticação, conta não administradora, alterações administrativas, concorrência/carga, mutações ITSM, histórico completo de conversas ou links externos das fontes.

## Evidência visual selecionada

### Login

![Login protegido](/Users/pedro/.codex/visualizations/2026/08/11/019fee56-a5c4-7970-b580-e94fcdcae80d/predictfy-evaluation/01-gestao-first-view.png)

### Gestão

![Centro de Gestão](/Users/pedro/.codex/visualizations/2026/08/11/019fee56-a5c4-7970-b580-e94fcdcae80d/predictfy-evaluation/03-gestao-1440x900-collapsed.png)

### Monitoramento

![Monitoramento preditivo](/Users/pedro/.codex/visualizations/2026/08/11/019fee56-a5c4-7970-b580-e94fcdcae80d/predictfy-evaluation/06-monitoramento-final-1440x900.png)

### Modelos e governança

![Modelos e governança](/Users/pedro/.codex/visualizations/2026/08/11/019fee56-a5c4-7970-b580-e94fcdcae80d/predictfy-evaluation/08-modelos-1440x900.png)

### Administração sem identidades expostas

![Resumo administrativo seguro](/Users/pedro/.codex/visualizations/2026/08/11/019fee56-a5c4-7970-b580-e94fcdcae80d/predictfy-evaluation/09-admin-safe-summary.png)

### Chatbot, tabela larga e overflow local

![Tabela larga no chatbot](/Users/pedro/.codex/visualizations/2026/08/11/019fee56-a5c4-7970-b580-e94fcdcae80d/predictfy-evaluation/11-chat-wide-table-1440x900.png)

### Integração Técnico–chatbot

![Resposta técnica contextual](/Users/pedro/.codex/visualizations/2026/08/11/019fee56-a5c4-7970-b580-e94fcdcae80d/predictfy-evaluation/12-chat-complex-response.png)

### Técnico móvel funcional

![Técnico móvel](/Users/pedro/.codex/visualizations/2026/08/11/019fee56-a5c4-7970-b580-e94fcdcae80d/predictfy-evaluation/17-tecnico-mobile-390x844.png)

### Falha móvel da Gestão

![Gestão móvel comprimida](/Users/pedro/.codex/visualizations/2026/08/11/019fee56-a5c4-7970-b580-e94fcdcae80d/predictfy-evaluation/23-gestao-mobile-after-wait.png)
