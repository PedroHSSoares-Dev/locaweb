# Relatório — validação isolada dos modelos

Data do experimento: 05/08/2026.

## Resumo executivo

- **XGBoost: melhorou de forma relevante** no novo protocolo cronológico. No
  teste futuro intocado (novembro e dezembro de 2025), obteve PR-AUC 0,2434 e
  ROC-AUC 0,8885. O ganho, porém, ficou concentrado em P3; P2 continua fraco e
  tem somente sete violações no teste.
- **LSTM: não há melhoria robusta suficiente para promoção.** Algumas execuções
  melhoraram o MAE publicado, mas o resultado variou muito entre seeds. Na média
  de três seeds, os modelos perderam para baselines simples no horizonte
  recursivo D+1..D+7.
- O protocolo `one-step-ahead` atual do LSTM é válido para a pergunta operacional
  “amanhã, atualizando o histórico todos os dias”. Ele deve ser mantido com esse
  nome e acompanhado de uma avaliação recursiva separada para D+1..D+7.
- Databricks não participou deste teste e não seria a causa de ganho de métrica.
  Seu valor seria operacional: MLflow, Jobs e rastreabilidade, como camada
  opcional e não como dependência do núcleo cloud-agnostic.

## Isolamento

Os experimentos leem `data/raw/LW-DATASET.xlsx` e gravam somente nesta pasta.
Não alteram `src/`, `outputs/`, `models_saved/`, API ou frontend.

## LSTM

Protocolo:

- treino real limitado a 01/01/2025..30/09/2025;
- holdout real de 01/10/2025..31/12/2025 (92 dias);
- scaler ajustado somente no treino;
- anos sintéticos gerados somente a partir de Jan-Set/2025;
- blocos semanais preservam o alinhamento do dia da semana;
- avaliação `one-step-ahead` com observação real incorporada a cada novo dia;
- avaliação recursiva em 86 origens, com horizontes D+1..D+7;
- três seeds: 42, 123 e 2026.

### One-step-ahead (MAE; menor é melhor)

| Série | Produção publicada* | Melhor candidato, média ± desvio | Baseline simples | Veredito |
|---|---:|---:|---:|---|
| Total | 14,67 | Calendar LSTM: 14,19 ± 1,21 | Lag-7: 13,33 | ganho médio de 3,3% vs publicado, mas perde do baseline |
| P2 | 4,15 | Calendar LSTM: 4,25 ± 0,39 | mediana por dia da semana: 3,60 | piorou 2,4% e perde do baseline |
| P3 | 13,32 | LSTM univariado: 12,84 ± 0,80 | Lag-7: 11,72 | ganho médio de 3,6% vs publicado, mas perde do baseline |

\* A referência publicada não é uma comparação limpa: o scaler foi ajustado na
série completa e os anos sintéticos foram gerados com todo 2025, incluindo o
holdout. Ela aparece somente como referência histórica.

Na seed 42, os MAEs foram 13,04 (total univariado), 3,95 (P2 com calendário) e
12,06 (P3 com calendário). Repetir o treino revelou valores bem piores em outras
seeds, chegando a 17,59 no total. Portanto, usar apenas a seed 42 superestima a
melhoria.

### Rolling-origin recursivo D+1..D+7

| Série | Melhor LSTM, média de 3 seeds | Melhor baseline | Diferença do LSTM |
|---|---:|---:|---:|
| Total | Calendar LSTM: 13,53 | Lag-7: 12,50 | 8,3% pior |
| P2 | Calendar LSTM: 4,14 | mediana por dia da semana: 3,49 | 18,8% pior |
| P3 | LSTM univariado: 11,93 | Lag-7: 11,03 | 8,1% pior |

Conclusão do LSTM: manter a avaliação one-step porque ela responde corretamente
ao cenário D+1 com atualização diária, mas não usar esse número como prova de
qualidade D+7. Antes de qualquer promoção, testar ensemble de seeds, previsão
direta multi-horizonte e comparar todos os modelos no mesmo conjunto temporal.

O campo `mae_prophet_92_dias = 23.80` no resultado atual do LSTM também não deve
sustentar a alegação de “38,3% melhor”: ele é hardcoded e não corresponde ao
mesmo protocolo reproduzido neste experimento.

## XGBoost

Protocolo:

- somente 2025, período no qual P2 passa a ter volume útil;
- treino Jan-Ago: 17.649 incidentes / 177 violações;
- validação Set-Out: 4.450 / 22;
- teste intocado Nov-Dez: 3.057 / 39;
- categóricas e frequências ajustadas apenas no treino;
- one-hot com categorias desconhecidas aceitas;
- médias móveis terminam em D-1, sem incluir volume do próprio dia;
- seis configurações fixas comparadas somente na validação;
- modelo selecionado: profundidade 3, `scale_pos_weight=20`;
- modelo e thresholds definidos antes de acessar o teste.

### Resultado no teste futuro

| Métrica | Referência publicada* | Experimento temporal |
|---|---:|---:|
| PR-AUC | 0,0694 | **0,2434** |
| ROC-AUC | 0,7767 | **0,8885** |
| Lift PR-AUC sobre aleatório | — | **19,08×** |
| IC bootstrap 95% do PR-AUC | — | 0,1098..0,3996 |

\* A referência publicada usa um split posicional num dataset em ordem reversa
(futuro no treino, passado no teste) e escolhe modelo e threshold no próprio
teste. Por isso, a variação percentual não é uma comparação controlada, embora o
novo valor seja claramente promissor.

### Thresholds escolhidos na validação e aplicados no teste

| Política | Recall | Precision | F1 | TP / FP / FN | Alertas |
|---|---:|---:|---:|---:|---:|
| Priorizar recall ≥70% | 82,05% | 3,97% | 0,0757 | 32 / 775 / 7 | 807 |
| Maximizar F1 | 28,21% | 27,50% | 0,2785 | 11 / 29 / 28 | 40 |

O primeiro threshold é útil como triagem ampla, mas gera muitos alertas. O
segundo é operacionalmente mais barato, porém deixa 28 violações passarem. A
decisão precisa ser baseada no custo real de um falso negativo e na capacidade
da equipe de analisar alertas.

### Limitação por prioridade

| Prioridade | Positivos no teste | PR-AUC | ROC-AUC | Observação |
|---|---:|---:|---:|---|
| P2 | 7 | 0,0264 | 0,8259 | ranking fraco e amostra muito pequena |
| P3 | 32 | 0,3205 | 0,8955 | concentra a melhoria geral |

P2 é justamente o problema de negócio fora da meta. Portanto, o XGBoost está
promissor, mas ainda não deve ser apresentado como resolvido para P2. O próximo
teste correto é backtesting temporal com várias janelas e uma estratégia
específica para P2, sem reutilizar Nov-Dez para novas escolhas.

## Recomendação

1. Não promover o LSTM experimental. Manter as duas métricas separadas e usar os
   baselines como requisito mínimo.
2. Levar o protocolo cronológico do XGBoost para uma branch própria e validar em
   múltiplas janelas antes de substituir produção.
3. Expor duas políticas de threshold no dashboard: “cobertura” e “capacidade da
   operação”, com quantidade esperada de alertas.
4. Tratar P2 separadamente e comunicar a incerteza causada por poucos positivos.
5. Se Databricks for adotado, usá-lo para registrar esses runs e comparar
   artefatos via MLflow; manter os scripts executáveis localmente e em qualquer
   cloud.

## Artefatos reproduzíveis

- `run_lstm_validation.py` → `lstm_results.json`
- `run_xgb_validation.py` → `xgb_results.json`
