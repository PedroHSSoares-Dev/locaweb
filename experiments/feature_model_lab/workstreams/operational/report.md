# Alternative Operational Track — Next-day High-workload Advisory

## Status

NO-GO: OPERATIONAL TRACK GATE NOT PASSED

## Executive conclusion

The strongest candidate was `extra_trees_no_rolling`. It raised pooled real-2025 PR-AUC from 0.6733 to 0.7207 (+7.0%), won 5/6 monthly folds, and improved Top-20% precision from 42.5% to 67.5%. It did **not** pass the predeclared 15% paired-improvement gate and was slightly below the baseline in pooled Oct-Dec PR-AUC (0.5301 versus 0.5383). Promotion decision: **DO NOT PROMOTE**.

This is a track-level no-go, not a claim that the overall multi-track research has reached its terminal condition.

## Preregistration and target-validity amendment

The baseline, metric, 15% gate, folds, workload, and operational action were written before any candidate ran. The original fixed threshold was invalidated before candidate execution: the all-incident daily mean changes from 0.30 (2023) and 1.70 (2024) to 333.73 (2025), and its frozen q80=33 labeled 181/184 evaluation days positive. `preregistration_amendment.json`, also written before candidate execution, therefore defines the observable proxy as:

> A high-workload day has a real opening count at or above the 80th percentile of the eight strictly prior same-weekday counts.

This threshold is known by the end of d-1. July-December contains 83/184 positives. The score supports a D+1 flex-staffing/on-call-readiness advisory only; it does not automate incident handling.

## Exact track stopping criterion

Nine materially distinct cycles covered robust seasonal residual/MAD, regularized logistic, Isolation Forest hybrid, Extra Trees, histogram gradient boosting, and a fixed rank ensemble. Five seeds were checked for the strongest stochastic candidate. No candidate passed all predeclared gates, so this isolated operational track stops as no-go.

## Baseline versus strongest candidate

| Metric | Seasonal lag-7 margin | `extra_trees_no_rolling` |
|---|---:|---:|
| Pooled PR-AUC | 0.6733 | 0.7207 |
| Relative PR-AUC gain | — | +7.0% |
| Monthly wins | — | 5/6 |
| Jul-Sep PR-AUC | 0.7689 | 0.8916 |
| Oct-Dec PR-AUC | 0.5383 | 0.5301 |
| Top-20% alerts | 40 | 40 |
| Top-20% hits | 17 | 27 |
| Top-20% precision | 42.5% | 67.5% |
| Top-20% recall | 20.5% | 32.5% |
| Days reviewed per hit | 2.35 | 1.48 |

Top-20% is a capacity-matched ranking diagnostic (40 advisory-days across 184 days), not a threshold selected on the evaluation folds.

## Temporal results

| Month | Positives | Baseline PR-AUC | Candidate PR-AUC | Candidate Top-20% hits/alerts |
|---|---:|---:|---:|---:|
| 2025-07 | 5/31 | 0.1380 | 0.3697 | 2/7 |
| 2025-08 | 18/31 | 0.5582 | 0.7351 | 6/7 |
| 2025-09 | 27/30 | 0.9199 | 0.9912 | 6/6 |
| 2025-10 | 10/31 | 0.5730 | 0.6018 | 5/7 |
| 2025-11 | 8/30 | 0.6020 | 0.3772 | 2/6 |
| 2025-12 | 15/31 | 0.5388 | 0.7007 | 6/7 |

The candidate wins July, August, September, October, and December, but loses November. The first-half gain is strong; the second-half aggregate is marginally worse, which independently fails the stability gate.

## Experiment coverage

| Cycle | Candidate | Family | PR-AUC | Gain vs baseline | Monthly wins | Top-20% precision | Top-20% recall | Decision |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 1 | robust_residual_rule | robust seasonal residual/MAD-style rule | 0.7052 | +4.7% | 4/6 | 47.5% | 22.9% | RETAIN |
| 2 | logistic_calendar | regularized generalized linear | 0.4325 | -35.8% | 3/6 | 42.5% | 20.5% | REJECT |
| 3 | logistic_calendar_lags | regularized generalized linear | 0.6956 | +3.3% | 6/6 | 67.5% | 32.5% | RETAIN |
| 4 | logistic_full | regularized generalized linear | 0.5539 | -17.7% | 4/6 | 50.0% | 24.1% | REJECT |
| 5 | isolation_regime_hybrid | unsupervised density plus directional rule | 0.7081 | +5.2% | 4/6 | 45.0% | 21.7% | RETAIN |
| 6 | extra_trees_no_rolling | random-tree bagging | 0.7207 | +7.0% | 5/6 | 67.5% | 32.5% | RETAIN_EXPLORATORY |
| 7 | extra_trees_full | random-tree bagging | 0.6180 | -8.2% | 5/6 | 62.5% | 30.1% | REJECT |
| 8 | hist_gradient_boosting | gradient boosting | 0.6138 | -8.8% | 6/6 | 65.0% | 31.3% | REJECT |
| 9 | hybrid_rank_blend | ensemble/hybrid | 0.6088 | -9.6% | 5/6 | 60.0% | 28.9% | REJECT |

## Explicit feature ablations

| Feature family | Measured ablation |
|---|---|
| calendar | `{"candidate": "logistic_calendar", "pr_auc": 0.4324969337319647}` |
| lag_levels | `{"from": "logistic_calendar", "to": "logistic_calendar_lags", "pr_auc_delta": 0.2630834098706389}` |
| rolling_distribution | `{"from": "extra_trees_no_rolling", "to": "extra_trees_full", "pr_auc_delta": -0.10273941764358652}` |
| seasonal_residual | `{"from": "seasonal_naive_lag7_margin", "to": "robust_residual_rule", "relative_gain": 0.0473742395221175}` |
| trend_regime | `{"from": "robust_residual_rule", "to": "isolation_regime_hybrid", "pr_auc_delta": 0.002895854968192557}` |

Lag levels are retained: adding them to calendar-only logistic contributes the largest positive ablation. The full rolling-distribution family is rejected for Extra Trees because it lowers PR-AUC materially. Seasonal residual and directional Isolation Forest additions are only marginally positive. Calendar-only is insufficient.

## Seed stability

Across seeds 11, 29, 47, 71, 101, candidate PR-AUC is 0.7176 ± 0.0062, relative spread 2.33%, and mean gain 6.6%. Randomness is controlled, but every seed remains below the 15% gate; stability cannot rescue an insufficient effect.

## Synthetic evidence separation

No synthetic row was used for training or evaluation in this track. The available synthetic series was generated from 2025 P2/P3 observations, including the evaluation period, and does not represent all-incident workload. Mixing it here would create both target mismatch and future-information risk. Synthetic contribution for this track is therefore not estimable and is not claimed.

## Leakage and reproducibility

- Daily aggregates contain no persisted incident identifiers, people, categories, or descriptions.
- Target thresholds use eight strictly prior same-weekday observations.
- Every lag/rolling feature ends by d-1; no centered windows are used.
- Each monthly model trains only on 2025 target dates before the fold.
- All evaluation rows are real July-December 2025 observations and are identical across methods.
- Preprocessing is fit inside each training fold.
- Strongest-candidate seed spread is recorded above; `reproduce.py` performs a fresh-process exact-metric check.

## Hardware and runtime

Apple arm64, 10 logical CPUs; Python 3.11.11; scikit-learn 1.8.0. The research run took 79.8s with observed process peak RSS about 309.5 MB. Tree jobs were bounded to two workers; CUDA/MPS was not used.

## Production decision

Do not promote this challenger. If a safe rule must ship today, retain the transparent lag-7 margin as an exploratory staffing signal with human review and no automated action. The Extra Trees candidate is useful evidence—especially its 67.5% precision versus 42.5% at the same workload—but remains exploratory until it passes the locked effect-size and second-half stability gates on later real data.
