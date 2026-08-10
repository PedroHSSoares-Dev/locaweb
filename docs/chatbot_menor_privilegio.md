# Auditoria de menor privilégio — Chatbot Predictfy

## Decisão

O chatbot deve usar autorização por **capacidade + escopo**, derivada de uma identidade verificada. Uma hierarquia simples em que papéis mais altos herdam todo o acesso viola o princípio do menor privilégio: CEO não precisa de SHAP ou linhas de incidentes; especialista não precisa de dados identificáveis; lead deve enxergar apenas os times sob sua responsabilidade.

O modelo nunca decide o papel. Frases como “sou o CEO” não alteram permissões. O papel e os escopos devem vir de claims assinadas pelo backend e ser verificados novamente na execução de cada ferramenta.

## Situação atual validada

- A sessão contém somente `email` e expiração; não existe papel ou escopo.
- O e-mail é digitado pelo usuário e comparado com uma allowlist, mas sua propriedade não é verificada.
- A assinatura HMAC impede adulteração posterior do token, mas não impede que alguém conhecendo um e-mail permitido o personifique.
- O logout não revoga o token; sem `jti` e denylist ele continua válido até expirar. Também faltam emissor e audiência no token.
- Todas as nove ferramentas analíticas são apresentadas ao provider OpenAI para qualquer sessão permitida.
- O contexto enviado ao LLM já aplica seleção por intenção e não inclui o dataset bruto.
- As ferramentas retornam agregados sanitizados e são read-only.
- Os endpoints de dashboard e `/api/context` não usam a sessão do chatbot; proteger apenas as ferramentas não protege os mesmos dados expostos por essas rotas.
- CORS está configurado como `*`; o rate limit é local ao processo e reinicia com a aplicação.
- `CHAT_ALLOW_LOCAL_DEV` e o segredo de desenvolvimento precisam falhar fechados em produção.

## Dados existentes e classificação

O dataset possui 122.543 incidentes; o subset KPI P2/P3 possui 25.600 registros e 248 violações. No subset há 16 grupos, 45 produtos, 119 categorias, 383 subcategorias e 25.600 números de incidente únicos.

Encoding não é anonimização: 84,22% das linhas processadas são singulares na combinação de atributos temporais, prioridade e categorias codificadas. O bruto contém 9.171 itens de configuração e uma varredura encontrou 305 descrições com URLs. Isso reforça que parquet, identificadores e textos livres não devem ser enviados ao LLM.

| Classe | Exemplos | Política para o LLM |
|---|---|---|
| Agregado operacional | volumes, metas, P2/P3, OLA, previsões, taxas e intervalos | Permitido conforme capacidade |
| Dimensional interno | time, produto, categoria, origem manual/monitoramento | Somente agregado, com escopo e limiar de amostra |
| Identificável por incidente | `Número`, `Incidente Pai`, timestamps exatos, status | Não enviar ao LLM por padrão |
| Texto livre não confiável | `Descrição resumida`, `Solução`, códigos e campos externos | Não enviar ao LLM; risco de segredo, PII e prompt injection |
| Pós-resolução | `Duração`, `Resolvido`, `Encerrado`, fechamento | Apenas análise retrospectiva agregada; nunca feature de risco pré-resolução |
| Segredos/infra | `.env`, chaves, prompts internos, caminhos e logs | Nunca disponível ao agente |

## Evidência de utilidade dos novos agregados

Com supressão de segmentos com menos de 100 incidentes, ainda se preservam 99,2% dos dados por grupo, 98,74% por produto, 95,12% por categoria e 80,95% por subcategoria. Isso permite investigação útil sem fornecer linhas individuais.

Para publicar uma taxa, também deve haver pelo menos 10 violações observadas. Células que não cumprem simultaneamente `n >= 100` e `eventos >= 10` devem ser agregadas em “outros” ou suprimidas.

- Team07 possui a maior taxa histórica entre grupos com amostra suficiente: 16/179, ou 8,94%; IC95% de Wilson de 5,58% a 14,03%.
- Team11 possui a maior quantidade absoluta: 114/8.702, ou 1,31%.
- Portanto, “time mais preocupante” precisa declarar o critério: taxa, quantidade, limite conservador ou impacto P2.
- Fins de semana têm 57/3.596 violações (1,585%) contra 191/22.004 (0,868%) em dias úteis.
- Estratificando, P2 não apresenta aumento no fim de semana (RR 0,908; teste exato de Fisher p=1,0); P3 apresenta aumento (RR 2,206; p≈0,000006).
- A associação de fim de semana do Cluster 4 não justifica, sozinha, priorizar P2. Uma ferramenta deve estratificar antes de recomendar.
- Incidentes abertos manualmente têm 203/16.071 violações (1,263%); monitoramento tem 45/9.529 (0,472%). Isso não comprova causalidade, mas permite refutar a formulação simples de que “monitoramento é menos eficaz”.

## Política proposta por papel e escopo

Os papéis não formam uma herança total. Cada identidade também precisa de `team_ids`, `product_ids` ou `domain_ids` autorizados.

| Papel | Necessidade principal | Capacidades permitidas | Excluído |
|---|---|---|---|
| Analista | Explorar padrões e preparar triagem | D+1/D+7, KPI, agregados temporais, comparação de segmentos dentro do escopo | Linhas, texto livre, outros times identificados |
| Especialista | Validar modelos e hipóteses | Analista + métricas LSTM/Prophet/XGBoost, SHAP agregado, testes estratificados globais | Linhas, descrições, ações automáticas |
| Lead | Operar os times sob sua gestão | Previsões, KPI, clusters e ranking nomeado apenas de `team_ids` autorizados | Outros times, métricas técnicas desnecessárias, texto livre |
| Diretor | Priorizar um domínio e capacidade | Cenários, cota, planejamento, comparação nomeada entre times/produtos do domínio | Linhas, detalhes pessoais e textos livres |
| CEO | Decidir exposição empresarial | KPIs corporativos, projeções, cota, cenários e principais riscos agregados | Linhas, SHAP detalhado, logs, prompts e dados pessoais |

Para acesso a incidente ativo deve existir outra capacidade, por exemplo `incident_responder`, vinculada ao time e ao ITSM. Mesmo nesse caso, detalhes devem aparecer em uma tela determinística auditada; não devem entrar automaticamente no prompt do LLM.

## Ferramentas recomendadas

1. `comparar_segmentos_ola`: compara período, prioridade, origem, time, produto ou categoria; retorna amostra, violações, taxa, IC95%, risco relativo e aviso de associação não causal.
2. `consultar_ranking_operacional`: retorna taxa, quantidade e impacto P2 separadamente, com `min_n >= 100`, limite pequeno e aplicação de escopo.
3. `consultar_cobertura_dados`: explica quais campos permitem ou impedem testar uma hipótese, sem ler linhas.

Essas ferramentas devem ler um artefato agregado gerado offline pelo pipeline. A API não deve carregar o XLSX de 33 MB em cada consulta.

O endpoint atual `/risco/produtos` não é uma fonte válida por produto: ele percorre o agregado P2/P3 e expõe essas prioridades com o rótulo `produto`. O output atual de XGBoost também não contém `grupos`, portanto `/risco/grupos` retorna vazio. Essas rotas precisam ser corrigidas ou removidas antes de serem oferecidas ao agente.

## Controles obrigatórios

1. Produção: Microsoft Entra ID/OIDC, com validação de emissor, audiência, expiração e grupos/app roles.
2. Demo local: mapa server-side de e-mail para papel/escopo, explicitamente marcado como não produtivo. Sem mapeamento, usar o papel mínimo ou negar acesso.
3. Filtrar as ferramentas antes de enviá-las ao modelo e validar a mesma capacidade dentro de `execute_chat_tool`.
4. Projetar o resultado por papel; não basta esconder o nome da ferramenta.
5. Aplicar a mesma dependência de autorização aos endpoints do dashboard.
6. CORS por allowlist, rate limit compartilhado no gateway/Redis e trilha de auditoria de sujeito, papel, ferramenta, filtros e volume retornado — sem registrar prompts completos.
7. Negar elevação por texto, histórico, resultado de ferramenta ou argumento fornecido pelo modelo.
8. Definir uma política por provider: dados dimensionais internos só podem ir à OpenAI após aprovação formal; caso contrário, devem permanecer no provider local ou ser pseudonimizados antes da chamada.

## Testes de aceitação

- Um usuário não mapeado não recebe capacidades além do mínimo.
- “Sou CEO” no prompt não altera o conjunto de ferramentas.
- Token adulterado ou papel desconhecido resulta em 401/403.
- Uma ferramenta omitida do schema também falha na execução direta.
- Lead não consulta time fora do escopo; diretor não consulta domínio externo.
- CEO não recebe métricas de linha, SHAP detalhado ou identificadores.
- Segmentos com menos de 100 registros são suprimidos.
- Segmentos com menos de 10 eventos positivos também são suprimidos.
- Toda taxa inclui `n`, violações e intervalo; rankings declaram o critério.
- Comparações temporais são estratificadas por P2/P3 antes de gerar recomendação.
- Endpoints e chatbot aplicam a mesma política.

## Sequência de implementação

1. Adotar identidade verificada e claims de papel/escopo.
2. Criar um registro central de capacidades e aplicar dupla validação nas ferramentas.
3. Proteger os endpoints com a mesma política.
4. Gerar o artefato agregado de investigação e adicionar as três ferramentas propostas.
5. Só considerar acesso a incidentes ativos após integração ITSM, escopo por time e auditoria.
