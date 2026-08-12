# Daily-volume forecasting workstream

## Status

PROMOTION GATE PASSED: CALENDAR-ADJUSTED SEASONAL

## Executive conclusion

The deterministic calendar-adjusted seasonal challenger passed the predefined volume gate on the exact active Q4 rolling-origin rows. Aggregate D+1..D+7 MAE fell from 12.4605 to 10.1848 (18.26%); it won 7/7 horizons and WAPE improved from 0.2242 to 0.1833. The candidate remains a narrow, calendar-event mechanism rather than a general replacement for ordinary-day forecasting, so production should start as a shadow/canary overlay.

## Exact gate

- At least 10% average-horizon MAE reduction: **True**.
- Win at least 5 of 7 horizons: **7/7**.
- No WAPE regression over 5%: **True** (-18.25% relative change).
- All evaluation outcomes are real 2025 rows and every feature is available at its rolling origin.
- Candidate is deterministic; three clean repeated seed labels produce exactly the same metrics.

## Horizon results

| Horizon | Active baseline MAE | Candidate MAE | Reduction |
|---|---:|---:|---:|
| D1 | 12.6957 | 10.4892 | 17.38% |
| D2 | 12.5934 | 10.3402 | 17.89% |
| D3 | 12.5111 | 10.2329 | 18.21% |
| D4 | 12.4607 | 10.1568 | 18.49% |
| D5 | 12.4091 | 10.1112 | 18.52% |
| D6 | 12.3678 | 10.0723 | 18.56% |
| D7 | 12.1860 | 9.8906 | 18.84% |

## Synthetic audit

The supplied file has **1097 rows over 1096 unique dates**; the correct calendar has 1096 days. The extra row is a duplicated 2023 target date caused by an eight-row ISO-week-1 source block combined with a fixed seven-day pointer increment. Synthetic dates end 2024-12-31; all 365 dates in 2025 are flagged real and exactly match the raw KPI daily aggregation.

The original notebook generated 2023-2024 from **all of real 2025**, including the Q4 test period. Its supplied synthetic rows are therefore excluded from promotion-eligible training. It also assigns Monday-sorted source blocks to target blocks that need not start Monday, distorting weekday alignment (especially 2023). Near-matching marginal moments are generator inheritance, not independent validation.

Fold-safe comparisons use seed means, with individual seeds retained in `metrics.json`. Versus real-only Ridge MAE 39.3095: equal augmentation was 20.6407 (std 3.5500; delta -18.6688), 0.25-weight augmentation 21.5565 (std 2.8651; delta -17.7530), pretrain/fine-tune 52.6183 (std 0.1820; delta +13.3087), and lag-only initialization 38.7177 (std 0.5900; delta -0.5918). The supplied-file equal-weight diagnostic scored 11.0498, but F10 is explicitly ineligible because the generator used Q4 actuals. None displaced the real-only calendar challenger.

## Experiment registry

| ID | Experiment | Family | Q4 MAE (seed mean) | Q4 WAPE (seed mean) | Decision |
|---|---|---|---:|---:|---|
| F01 | active_seasonal_median3 | seasonal baseline | 12.4605 | 0.2242 | RETAIN |
| F02 | seasonal_ewma13 | statistical seasonal smoothing | 12.1860 | 0.2193 | RETAIN |
| F03 | ridge_ar_full_real | linear autoregression | 39.3095 | 0.7072 | REJECT |
| F04 | extra_trees_full_real | random/bagging trees | 21.1725 | 0.3809 | REJECT |
| F05 | hist_gradient_full_real | gradient boosting | 19.0658 | 0.3430 | REJECT |
| F06 | ridge_safe_synthetic_equal | linear autoregression | 20.6407 | 0.3713 | REJECT |
| F07 | ridge_safe_synthetic_reduced | linear autoregression | 21.5565 | 0.3878 | REJECT |
| F08 | sgd_safe_synthetic_pretrain_finetune | linear online fine-tuning | 52.6183 | 0.9468 | REJECT |
| F09 | ridge_safe_synthetic_lag_init | linear autoregression | 38.7177 | 0.6965 | REJECT |
| F10 | ridge_provided_synthetic_diagnostic | linear autoregression | 11.0498 | 0.1988 | INELIGIBLE DIAGNOSTIC |
| F11 | ridge_ablate_calendar | linear autoregression ablation | 14.6281 | 0.2633 | REJECT |
| F12 | ridge_ablate_rolling | linear autoregression ablation | 25.0649 | 0.4508 | REJECT |
| F13 | ridge_ablate_trend_residual | linear autoregression ablation | 38.5450 | 0.6934 | REJECT |
| F14 | ridge_ablate_weekly_lags | linear autoregression ablation | 39.2795 | 0.7067 | REJECT |
| F15 | calendar_adjusted_seasonal | hybrid statistical/operational rule | 10.1848 | 0.1833 | PROMOTION CANDIDATE |

## Feature ablations

Four explicit drop-family Ridge ablations were paired on the same Q4 rows. Full Ridge MAE was 39.3095; dropping calendar/Fourier (F11) yielded 14.6281 (-24.6814), dropping rolling distribution (F12) 25.0649 (-14.2446), dropping trend/residual (F13) 38.5450 (-0.7645), and dropping aligned/state lags (F14) 39.2795 (-0.0300). The broad linear model was rejected: several families reduced its extrapolation error when removed, yet every ablation still lost to the active seasonal baseline. The promoted hybrid retains only same-weekday median lags, calendar-known event windows, and a causally estimated prior-holiday factor.

## Temporal stability and interpretation

The rule is neutral outside its declared event window, so October is exactly unchanged. It improves both affected months: November through its known weekday holiday and December through Christmas/year-end activity.

| Target month | Baseline MAE | Candidate MAE | MAE reduction | Baseline WAPE | Candidate WAPE |
|---|---:|---:|---:|---:|---:|
| 2025-10 | 9.9745 | 9.9745 | 0.00% | 0.1478 | 0.1478 |
| 2025-11 | 11.5667 | 10.1820 | 11.97% | 0.2124 | 0.1869 |
| 2025-12 | 15.5806 | 10.3886 | 33.32% | 0.3394 | 0.2263 |

The effect is stable by mechanism (neutral when inactive; lower error in both active months), but only one real Christmas/year-end period exists. A future-year canary is therefore required before unconditional rollout. Aggregate bias changed from 7.093 to 4.312 incidents per forecast.

## Leakage and reproducibility

- Target dates are always real 2025; synthetic validation/test rows are forbidden by code.
- Weekly lags and adjustment-factor outcomes are timestamp-checked at or before the forecast origin.
- Supplied synthetic history is evaluated only in F10, explicitly marked ineligible.
- Fold-safe synthetic data is regenerated separately from the real prefix ending before each evaluation period.
- Clean-process reproduction compares every aggregate and horizon metric at tolerance `1e-12` and validates source hashes.

## Hardware/runtime

All cycles ran single-process on arm64 with bounded trees (`n_jobs=1`). Total measured runtime was 335.77s; maximum reported process RSS was 322.8 MB, below the 18 GB ceiling. No package was installed and no production artifact was modified.

## Production decision

Promote only to a shadow/canary **calendar overlay** on the existing seasonal median baseline. Preserve the ordinary-day baseline unchanged, log event-day errors, and require a second year of real Christmas/year-end evidence before full automatic replacement. Do not use the supplied synthetic CSV for any Q4-backed promotion claim.


## Total/P2/P3 reconciliation

Raw 2025 KPI totals reconcile exactly on every calendar day: **25,156 Total = 5,159 P2 + 19,997 P3**, with 0 mismatched days and maximum absolute daily gap 0. The exact raw labels are `2 - Alta` and `3 - Média`.

| Series | Active baseline MAE | Calendar candidate MAE | Reduction | Horizon wins |
|---|---:|---:|---:|---:|
| TOTAL | 12.4605 | 10.1848 | 18.26% | 7/7 |
| P2 | 4.2832 | 4.3554 | -1.68% | 0/7 |
| P3 | 11.3729 | 9.4230 | 17.15% | 7/7 |

The promotion claim applies to **Total only**. Total is forecast directly; P2/P3 diagnostics are neither summed into the candidate nor used to select its adjustment. This avoids concealing segment-specific error behind reconciliation.
