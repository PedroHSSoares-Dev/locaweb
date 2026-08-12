# Feature Model Lab — Final Report

## 1. Executive conclusion

**SUCCESS: TARGET X ACHIEVED.** Two promotion gates passed on real, paired temporal evidence: the point-in-time structured LinearSVC for OLA-risk ranking and the Total-volume calendar-adjusted seasonal overlay. The alternative workload track improved operational triage but failed its locked 15%/second-half gate. No production artifact was changed.

The risk result is the stronger basis for Target X because global PR-AUC improved in all six July–December folds. The forecasting gain is concentrated in known holiday/year-end dates and should remain a shadow overlay until another real year confirms it.

## 2. Exact stopping criterion

- Minimum coverage passed: 36 cycles, 3 tracks, 11 named model families, 17 named feature families, and 10 explicit drop/mechanism ablations.
- OLA gate: passed for global, P2, and P3; global is the most stable operational claim.
- Forecast gate: Total MAE improved 18.26%, with 7/7 horizon wins and WAPE change -18.25%.
- Clean reproductions: all three workstreams passed with zero maximum numeric difference.

## 3. Experiment coverage

| Track | Cycles | Distinct focus | Track result |
|---|---:|---|---|
| OLA risk | 12 | structured, sparse text, trees, boosting, hybrids | promotion candidate |
| Daily volume | 15 | statistical, AR, trees, boosting, synthetic strategies, calendar rule | promotion candidate on Total |
| Operational workload | 9 | transparent rules, GLM, density, trees, boosting, ensemble | no-go at locked gate |

The portfolio includes transparent linear/generalized models, maximum-margin models, bagging trees, gradient boosting, statistical time series, sparse text/NB-SVM, anomaly/density models, and fixed hybrids.

## 4. Champion versus final candidate for every track

### OLA risk

| Segment | Pooled PR-AUC champion → candidate | Robust PR-AUC champion → candidate | Wins | Recall@5% champion → candidate |
|---|---:|---:|---:|---:|
| Global | 0.01445 → 0.02688 | 0.01637 → 0.03984 | 6/6 | 14.0% → 27.1% |
| P2 | 0.01598 → 0.02545 | 0.01597 → 0.03509 | 4/6 | 15.0% → 15.0% |
| P3 | 0.01468 → 0.02970 | 0.01825 → 0.04149 | 4/6 | 14.9% → 29.9% |

P2 has only 20 evaluation violations; its ranking gate passes, but Recall@5% is unchanged. No standalone P2 production claim is warranted.

### Daily volume

| Series | Baseline MAE | Candidate MAE | Change | Horizon wins | Scope |
|---|---:|---:|---:|---:|---|
| Total | 12.4605 | 10.1848 | -18.26% | 7/7 | promotion gate |
| P2 | 4.2832 | 4.3554 | +1.68% error | 0/7 | diagnostic only |
| P3 | 11.3729 | 9.4230 | -17.15% error | 7/7 | diagnostic only |

Raw real 2025 reconciles daily and annually: 25,156 Total = 5,159 P2 + 19,997 P3, with zero mismatched days. Total is modeled directly, not silently reconstructed from the segments.

### Operational workload

The seasonal lag-7-margin baseline PR-AUC was 0.67327; `extra_trees_no_rolling` reached 0.72069 (+7.04%) and won 5/6 months. It remains no-go because gain was below 15% and Oct–Dec regressed (0.53013 versus 0.53826).

## 5. Synthetic-data audit and measured contribution

The supplied CSV has 1,097 rows but 1,096 unique dates: one 2023 date is duplicated. Its notebook generated 2023–2024 from all real 2025, including Q4, and misaligned some weekday blocks. The file is therefore ineligible for Q4-backed promotion training.

Against real-only Ridge MAE 39.3095, fold-safe seed-mean MAE was 20.6407 for equal weighting, 21.5565 for 0.25 weighting, 52.6183 for pretrain/fine-tune, and 38.7177 for lag initialization. Synthetic data helped the weak Ridge under equal/reduced weighting but still failed to beat the active baseline. The supplied contaminated file scored 11.0498; that attractive result is explicitly ineligible and is evidence of generator-artifact risk.

## 6. Feature ablation results

- OLA sparse categories added +0.00351 global robust PR-AUC; historical backoff/novelty added +0.00397.
- OLA volume context added only +0.00089 robust PR-AUC while reducing Recall@5% by -2.8%; it is not a core retained mechanism.
- NB log-count ratios improved global text robust PR-AUC by +0.04399, but hurt P2 recall by -10.0%; the simpler structured margin model was selected.
- Forecast Ridge full MAE was 39.3095; dropping calendar/Fourier reduced it to 14.6281, showing the short real history cannot support that broad linear calendar basis. Rolling, trend, and weekly-lag drop tests are recorded in F12–F14.
- Operational Extra Trees without rolling distributions (0.72069) beat the full rolling variant, so the rolling family was rejected for that target.

## 7. Temporal stability

- OLA global won 6/6 months; P2 and P3 each won 4/6. Seeds 11, 42, and 101 were numerically identical for the selected LinearSVC.
- Forecast Total won all seven horizons. October was unchanged; November and December improved through predeclared calendar-known event handling. This is mechanism-consistent but still only one real year-end period.
- Operational workload won 5/6 months but failed the half-year guardrail: Jul–Sep improved, Oct–Dec regressed.

## 8. Operational workload and interpretation

At a fixed top-5% OLA review budget, the global candidate emits 597 alerts over six months (3.24/day), captures 29 violations, and requires 20.6 reviews per hit. P2 requires 41.3 reviews/hit; P3 requires 18.2.

The operational workload candidate reviews 40 high-risk days, finds 27, and moves precision/recall from 42.5%/20.5% to 67.5%/32.5%; useful evidence, but not sufficient for promotion.

## 9. Models and features rejected

- OLA: HistGradientBoosting, safe XGBoost reconstruction, global fixed-rank hybrid, and unstable text-only operational trade-offs were not selected.
- Forecast: real-only Ridge, Extra Trees, HistGradientBoosting, synthetic pretrain/fine-tune, and all synthetic-augmented variants failed the active-baseline gate. F10 must never be revisited as eligible evidence without regeneration.
- Operational: calendar-only GLM, full rolling Extra Trees, boosting, isolation hybrid, and fixed blend failed the complete gate.
- Do not reintroduce assignment group into challengers until its opening-time availability is proven.

## 10. Leakage and reproducibility checks

All evaluation rows are real. OLA training openings and known labels precede every monthly fold; vocabularies/encoders are fold-local; left-shifted arrival and historical-outcome features exclude the current row. Forecast lags and holiday factors use data observable at each origin. Synthetic rows are training-only and the supplied leaky file is diagnostic-only. All three clean-process checks matched with zero numeric difference and source hashes were verified.

No incident identifier, personal value, category value, raw summary, token, or vocabulary is persisted in these reports or configs.

## 11. Hardware/runtime summary

| Track | Runtime | Peak RSS |
|---|---:|---:|
| OLA risk | 308.2s | 488.3 MB |
| Forecast | 335.8s | 322.8 MB |
| Operational | 79.8s | 309.5 MB |

All runs stayed far below 18 GB, used bounded CPU parallelism, did not assume CUDA, and installed no package.

## 12. Exact files created

Authoritative root artifacts: `STATE.md`, `experiment_registry.jsonl`, `feature_catalog.json`, `model_registry.json`, `synthetic_data_audit.json`, `champion_table.json`, `final_metrics.json`, `final_report.md`, `reproduce.py`, `reproduction_check.json`, and `consolidate.py` under `experiments/feature_model_lab/`. Detailed evidence lives in the three `workstreams/` directories. Regenerable configs live under `models_saved/experiments/feature_model_lab/`.

## 13. Reproduction command

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/predictfy-locaweb/bin/python experiments/feature_model_lab/reproduce.py
```

Then regenerate the authoritative summary with:

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/predictfy-locaweb/bin/python experiments/feature_model_lab/consolidate.py
```

## 14. Recommended production decision

Do not overwrite the current production models yet. Run `linear_svm_structured` as a prospective shadow ranker at a fixed top-5% queue, using global/P3 as the primary evidence and treating P2 as exploratory. Run the volume calendar rule only as a shadow/canary overlay on Total event dates; preserve the ordinary seasonal baseline and do not apply the overlay separately to P2. Keep the operational workload candidate exploratory. Require prospective 2026 evidence, calibration before any probability wording, and an explicit review-capacity sign-off before promotion.
