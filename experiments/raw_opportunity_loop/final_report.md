# Raw Opportunity Loop — Final Report

## Status

NO-GO: RAW-ONLY CEILING

## Executive conclusion

Twelve materially different, point-in-time-safe raw-data families were tested; none produced a candidate that passed all P2 promotion gates. Q4 and all 2025 outer months were already inspected; this is not described as a fresh holdout.

## Exact stopping criterion

NO-GO condition: 12 materially different cycles completed, safe raw columns exhausted, strongest candidate rechecked, and failure established on paired monthly folds.

## Champion versus final candidate

| Metric | Locked generalist, fold-safe reimplementation | Final candidate |
|---|---:|---:|
| Aggregate P2 PR-AUC | 0.01598 | 0.02720 |
| Precision@Top-5% | 2.42% | 3.23% |
| Recall@Top-5% | 15.00% | 20.00% |
| Lift@Top-5% | 3.01 | 4.02 |
| Alerts/day | 0.674 | 0.674 |
| Reviewed per true violation | 41.333333333333336 | 31.0 |

Required candidate PR-AUC: `0.05000`. Monthly PR-AUC wins: `5/6`.

The previously opened `xgboost_specialists.json` reports P2 Q4 PR-AUC 0.02759 (global 0.21321; P3 0.26335). That artifact fits once through June and evaluates a fixed Q4 block, whereas this research retrains monthly and excludes labels not known at each month start; the numbers are therefore context, not interchangeable baselines.

## Monthly P2 results

| Month | Champion PR-AUC | Candidate PR-AUC | Delta | Candidate Top-5% hits/alerts |
|---|---:|---:|---:|---:|
| 2025-07 | 0.0300 | 0.0441 | +0.0140 | 1/19 |
| 2025-08 | 0.0211 | 0.0128 | -0.0084 | 0/21 |
| 2025-09 | 0.0072 | 0.0098 | +0.0026 | 0/22 |
| 2025-10 | 0.0108 | 0.0127 | +0.0019 | 0/22 |
| 2025-11 | 0.0613 | 0.2328 | +0.1714 | 3/22 |
| 2025-12 | 0.0052 | 0.0095 | +0.0043 | 0/18 |

## Feature-family evidence

Retained single-family hypotheses: text_tfidf, novelty_support.

Rejected single-family hypotheses: historical_outcomes, arrival_burst, recurrence, segmented_bursts, description_history, config_identity, active_workload, queue_growth, interactions, calendar_context.

| Family | P2 PR-AUC | Delta vs safe base | P2 Recall@Top-5% | P3 PR-AUC diagnostic | Decision |
|---|---:|---:|---:|---:|---|
| historical_outcomes | 0.01691 | +0.00092 | 20.0% | 0.01255 | REJECT |
| arrival_burst | 0.01641 | +0.00042 | 20.0% | 0.01296 | REJECT |
| recurrence | 0.01339 | -0.00260 | 20.0% | 0.01978 | REJECT |
| segmented_bursts | 0.01196 | -0.00403 | 15.0% | 0.01234 | REJECT |
| description_history | 0.01496 | -0.00103 | 15.0% | 0.01458 | REJECT |
| config_identity | 0.01621 | +0.00022 | 20.0% | 0.01140 | REJECT |
| text_tfidf | 0.02720 | +0.01121 | 20.0% | 0.01879 | RETAIN |
| novelty_support | 0.01783 | +0.00184 | 15.0% | 0.01745 | RETAIN |
| active_workload | 0.01430 | -0.00168 | 20.0% | 0.01176 | REJECT |
| queue_growth | 0.01662 | +0.00063 | 15.0% | 0.01309 | REJECT |
| interactions | 0.01395 | -0.00204 | 5.0% | 0.01043 | REJECT |
| calendar_context | 0.01582 | -0.00017 | 15.0% | 0.01304 | REJECT |

The final text family is an explicit single-family ablation against the safe base: PR-AUC rose from 0.01599 to 0.02720, while Top-5% recall rose from 10.0% to 20.0%. It still failed the absolute promotion thresholds. The exact per-cycle paired deltas are in `experiment_log.jsonl`; multi-family drop-one evidence, when applicable, is in `final_metrics.json`.

## Why the strongest candidate improved

Observed: the fold-fitted TF-IDF/logistic rank blend beat the champion PR-AUC in five of six months. The gain was highly concentrated in November, where it found three violations in 22 reviews; it found no Top-5% violations in four months. Supported inference: lexical structure in templated opening summaries adds a limited recurrence signal beyond exact category encodings. Hypothesis, not established fact: repeated machine-generated alert wording identifies operational episodes. Unsupported conclusion: the experiment does not show that any word or incident cause is causal, and no vocabulary or raw text was persisted.

## P3 diagnostic (not used to select P2)

Across the same July-December walk-forward protocol, champion P3 PR-AUC was 0.01468 and the strongest P2 candidate's P3 PR-AUC was 0.01879. P3 metrics were logged in every experiment cycle but did not influence the P2 promotion decision.

## Leakage and point-in-time audit

- All 19 raw columns were classified in `column_audit.csv`.
- Forbidden post-outcome/direct-target fields were excluded from predictive matrices.
- `Grupo designado` remains temporally uncertain because the local snapshot has no assignment history and the referenced data dictionary was absent. It is included only in the champion reimplementation, not in the safe challenger.
- Training rows require both opening before the fold and outcome known before the fold.
- Arrival/recurrence features use left-open searches, so the current and simultaneous incidents are excluded.
- Historical outcome rates use only prior known resolution/closure events.
- All category maps, target encodings, imputers and text vocabularies are fitted inside each outer training fold.

## Facts, inferences, hypotheses, unsupported conclusions

- Observed fact: P2 KPI coverage begins in 2025; there are only 42 P2 violations total and 20 in July-December.
- Observed fact: closure/resolution coverage changes sharply by opening year.
- Supported inference: P2 evidence is dominated by a single collection regime and has high monthly variance.
- Tested hypothesis: workload, recurrence, novelty, prior outcomes, configuration identity, description history, interactions, calendar, segmented bursts, queue growth and text can improve ranking.
- Unsupported conclusion: the raw snapshot cannot establish the organizational cause of P2 violations or prove causal effects.

## Operational interpretation

Scores are ranking signals, not calibrated probabilities. A model passing the gate may prioritize only the top 5% of monthly P2 arrivals for human review; it must not auto-close, auto-escalate, deny service, or replace OLA rules. A NO-GO result means the raw snapshot should not be promoted for P2 prioritization.

## Limitations and confidence

Only 20 P2 violations occur across the six evaluation folds. All months have already been inspected, so confidence is exploratory and low for promotion even with paired folds and seed checks. The single-snapshot dataset cannot verify reassignment history or the cause of the 2025 regime change.

## Minimum additional data if NO-GO

Live queue depth and concurrent open P2/P3 at scoring time; group workload and staffing/on-call coverage; time to acknowledgement; product health telemetry; deployment/change events; alert correlation/recurrence identifiers; and escalation/assignment history. These distinguish “not predictive” from “not measured.”

## Reproduction

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/predictfy-locaweb/bin/python experiments/raw_opportunity_loop/reproduce.py
```
