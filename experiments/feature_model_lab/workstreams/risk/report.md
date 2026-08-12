# Incident-level OLA Risk Workstream

## Workstream result

PROMOTION CANDIDATE

The strongest point-in-time-safe candidate is `linear_svm_structured`. This workstream does not make the overall multi-track stopping decision; it supplies paired evidence to the parent feature-model laboratory.

## Protocol and predeclared gate

- Monthly outer folds: July through December 2025.
- Training rows opened strictly earlier and had a resolution/closure label known strictly before each fold start.
- Every model scores the same monthly P2/P3 rows; global, P2, and P3 metrics are derived from one fold fit.
- Robust PR-AUC is the median of the six monthly PR-AUC values.
- Operational workload is fixed at the top 5% within each segment/month.
- Model specifications are bounded and fixed; no outer-fold labels tune hyperparameters or ensemble weights.
- Promotion requires at least 15% robust PR-AUC improvement, at least four monthly wins, no more than 5% relative Recall@Top-5% degradation, and point-in-time-safe features.

## Champion versus strongest candidate

Champion:

| Segment | Pooled PR-AUC | Robust PR-AUC | Precision@5% | Recall@5% | Lift@5% | Alerts | Reviews/hit |
|---|---:|---:|---:|---:|---:|---:|---:|
| global | 0.01445 | 0.01637 | 2.51% | 14.02% | 2.81 | 597 | 39.8 |
| P2 | 0.01598 | 0.01597 | 2.42% | 15.00% | 3.01 | 124 | 41.3 |
| P3 | 0.01468 | 0.01825 | 2.75% | 14.94% | 2.99 | 473 | 36.4 |

Strongest candidate:

| Segment | Pooled PR-AUC | Robust PR-AUC | Precision@5% | Recall@5% | Lift@5% | Alerts | Reviews/hit |
|---|---:|---:|---:|---:|---:|---:|---:|
| global | 0.02688 | 0.03984 | 4.86% | 27.10% | 5.43 | 597 | 20.6 |
| P2 | 0.02545 | 0.03509 | 2.42% | 15.00% | 3.01 | 124 | 41.3 |
| P3 | 0.02970 | 0.04149 | 5.50% | 29.89% | 5.99 | 473 | 18.2 |

| Segment | Robust improvement | Monthly wins | Recall@5% delta | Gate |
|---|---:|---:|---:|---:|
| global | +143.4% | 6/6 | +13.1% | PASS |
| P2 | +119.7% | 4/6 | +0.0% | PASS |
| P3 | +127.3% | 4/6 | +14.9% | PASS |

## Model-family coverage

| Model | Global pooled / robust / R@5 | P2 pooled / robust / R@5 | P3 pooled / robust / R@5 |
|---|---:|---:|---:|
| elastic_structured_full | 0.01645 | 0.01916 | 14.0% | 0.01218 | 0.00687 | 0.0% | 0.01760 | 0.02009 | 17.2% |
| elastic_no_categories | 0.01454 | 0.01566 | 12.1% | 0.01025 | 0.00571 | 0.0% | 0.01577 | 0.01629 | 13.8% |
| elastic_no_history_novelty | 0.01397 | 0.01519 | 13.1% | 0.01084 | 0.00811 | 0.0% | 0.01475 | 0.01625 | 17.2% |
| elastic_no_volume_context | 0.01698 | 0.01827 | 16.8% | 0.01150 | 0.00719 | 5.0% | 0.01858 | 0.01918 | 18.4% |
| linear_svm_structured | 0.02688 | 0.03984 | 27.1% | 0.02545 | 0.03509 | 15.0% | 0.02970 | 0.04149 | 29.9% |
| extra_trees_structured | 0.01284 | 0.03117 | 14.0% | 0.01026 | 0.01042 | 0.0% | 0.01391 | 0.03869 | 17.2% |
| hist_gradient_boosting_structured | 0.00801 | 0.00885 | 1.9% | 0.00951 | 0.00662 | 0.0% | 0.00823 | 0.00964 | 2.3% |
| xgboost_safe_reconstruction | 0.01582 | 0.01343 | 6.5% | 0.01599 | 0.00734 | 10.0% | 0.01671 | 0.01504 | 6.9% |
| word_tfidf_logistic | 0.04220 | 0.06220 | 15.0% | 0.01832 | 0.01500 | 20.0% | 0.04892 | 0.07765 | 14.9% |
| word_char_tfidf_svm | 0.03931 | 0.04409 | 17.8% | 0.02063 | 0.01766 | 20.0% | 0.04478 | 0.05284 | 16.1% |
| nbsvm_word_char | 0.05063 | 0.08808 | 15.9% | 0.01712 | 0.01756 | 10.0% | 0.06021 | 0.10246 | 17.2% |
| hybrid_nbsvm_xgboost | 0.01925 | 0.02413 | 11.2% | 0.07489 | 0.02229 | 25.0% | 0.01771 | 0.02544 | 9.2% |

The 12 cycles cover 8 named model families: bagging_random_trees, gradient_boosting, leakage_safe_fixed_rank_hybrid, linear_margin, nbsvm_sparse_text, regularized_linear, sparse_text_linear, sparse_text_margin.

## Explicit feature/model ablations

Positive deltas mean the named full mechanism outperformed its ablated/reference model.

| Mechanism | Segment | Pooled PR-AUC delta | Robust PR-AUC delta | Recall@5% delta |
|---|---|---:|---:|---:|
| sparse_categories | global | +0.00191 | +0.00351 | +1.9% |
| sparse_categories | P2 | +0.00192 | +0.00117 | +0.0% |
| sparse_categories | P3 | +0.00183 | +0.00380 | +3.4% |
| historical_backoff_plus_novelty | global | +0.00249 | +0.00397 | +0.9% |
| historical_backoff_plus_novelty | P2 | +0.00133 | -0.00124 | +0.0% |
| historical_backoff_plus_novelty | P3 | +0.00285 | +0.00384 | +0.0% |
| volume_context | global | -0.00053 | +0.00089 | -2.8% |
| volume_context | P2 | +0.00068 | -0.00031 | -5.0% |
| volume_context | P3 | -0.00098 | +0.00091 | -1.1% |
| character_tfidf_and_margin | global | -0.00289 | -0.01811 | +2.8% |
| character_tfidf_and_margin | P2 | +0.00231 | +0.00267 | +0.0% |
| character_tfidf_and_margin | P3 | -0.00414 | -0.02481 | +1.1% |
| naive_bayes_log_count_ratio | global | +0.01132 | +0.04399 | -1.9% |
| naive_bayes_log_count_ratio | P2 | -0.00351 | -0.00010 | -10.0% |
| naive_bayes_log_count_ratio | P3 | +0.01542 | +0.04962 | +1.1% |
| fixed_rank_hybrid | global | -0.03138 | -0.06394 | -4.7% |
| fixed_rank_hybrid | P2 | +0.05777 | +0.00472 | +15.0% |
| fixed_rank_hybrid | P3 | -0.04250 | -0.07702 | -8.0% |

## Temporal stability of strongest candidate

| Segment | Month | Champion PR-AUC | Candidate PR-AUC | Delta | Champion hits | Candidate hits |
|---|---|---:|---:|---:|---:|---:|
| global | 2025-07 | 0.01783 | 0.04046 | +0.02263 | 3 | 5 |
| global | 2025-08 | 0.01083 | 0.03104 | +0.02021 | 2 | 5 |
| global | 2025-09 | 0.00792 | 0.03921 | +0.03129 | 2 | 2 |
| global | 2025-10 | 0.01598 | 0.02266 | +0.00668 | 3 | 3 |
| global | 2025-11 | 0.02713 | 0.08805 | +0.06093 | 4 | 7 |
| global | 2025-12 | 0.01675 | 0.06953 | +0.05278 | 1 | 7 |
| P2 | 2025-07 | 0.03002 | 0.04259 | +0.01257 | 1 | 1 |
| P2 | 2025-08 | 0.02113 | 0.02203 | +0.00090 | 0 | 0 |
| P2 | 2025-09 | 0.00716 | 0.25450 | +0.24734 | 0 | 1 |
| P2 | 2025-10 | 0.01081 | 0.07692 | +0.06611 | 0 | 1 |
| P2 | 2025-11 | 0.06135 | 0.02758 | -0.03377 | 2 | 0 |
| P2 | 2025-12 | 0.00524 | 0.00278 | -0.00246 | 0 | 0 |
| P3 | 2025-07 | 0.01697 | 0.04632 | +0.02935 | 2 | 4 |
| P3 | 2025-08 | 0.01180 | 0.03665 | +0.02484 | 2 | 5 |
| P3 | 2025-09 | 0.00979 | 0.00881 | -0.00098 | 2 | 1 |
| P3 | 2025-10 | 0.02158 | 0.01496 | -0.00662 | 3 | 2 |
| P3 | 2025-11 | 0.02208 | 0.15651 | +0.13443 | 3 | 7 |
| P3 | 2025-12 | 0.01953 | 0.09391 | +0.07438 | 1 | 7 |

Three-seed sensitivity check (`11, 42, 101`):

| Segment | Min robust PR-AUC | Max robust PR-AUC | Relative range | Min Recall@5% | Max Recall@5% |
|---|---:|---:|---:|---:|---:|
| global | 0.03984 | 0.03984 | 0.00% | 27.10% | 27.10% |
| P2 | 0.03509 | 0.03509 | 0.00% | 15.00% | 15.00% |
| P3 | 0.04149 | 0.04149 | 0.00% | 29.89% | 29.89% |

## Leakage and interpretation

The assignment group remains temporally uncertain and appears only in the reconstructed champion. Challengers use opening-time fields, strictly left-shifted volume/support features, and historical targets only after their outcome time. Category/text vocabularies are fold-local. Hybrid weights are fixed in advance. Scores are ranking signals, not calibrated probabilities.

No incident number, category value, source value, raw summary, token, or vocabulary is persisted. Post-outcome fields are never predictors; resolution and closure timestamps only establish when a prior label became observable.

## Runtime and memory

Total workstream runtime: 308.2 seconds. Observed process peak RSS: 488.3 MB, below the declared 18 GB ceiling. Per-cycle measurements are in `experiment_registry.jsonl` and `model_registry.json`.

## Reproduction

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/predictfy-locaweb/bin/python experiments/feature_model_lab/workstreams/risk/reproduce.py
```
