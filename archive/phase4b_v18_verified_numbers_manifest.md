# v18 Verified Numbers Manifest

Generated: 2026-06-22T11:57:53.342560+00:00 UTC

## Output files

- `v18_analysis_figures/accuracy_by_region_v18.png`
- `v18_analysis_figures/chr_by_tau_v18.png`
- `v18_analysis_figures/ece_comparison_v18.png`
- `v18_analysis_figures/h3_effect_sizes_v18.png`
- `v18_analysis_figures/reliability_curves_v18.png`
- `v18_analysis_figures/source_confound_v18.png`
- `v18_analysis_figures/wrong_conf_distributions_v18.png`
- `v18_outputs/v18_accuracy_by_model.csv`
- `v18_outputs/v18_accuracy_pooled.csv`
- `v18_outputs/v18_chr.csv`
- `v18_outputs/v18_dataset_answer_balance.csv`
- `v18_outputs/v18_dataset_difficulty_distribution.csv`
- `v18_outputs/v18_dataset_subject_distribution.csv`
- `v18_outputs/v18_ece_bootstrap_ci.csv`
- `v18_outputs/v18_ece_brier_auroc.csv`
- `v18_outputs/v18_ece_equal_mass_sensitivity.csv`
- `v18_outputs/v18_flagged_items.csv`
- `v18_outputs/v18_flagged_sensitivity_accuracy.csv`
- `v18_outputs/v18_h3_by_model.csv`
- `v18_outputs/v18_h3_pooled.csv`
- `v18_outputs/v18_item_error_examples.csv`
- `v18_outputs/v18_item_high_conf_errors.csv`
- `v18_outputs/v18_mixed_models.csv`
- `v18_outputs/v18_source_confound_across.csv`
- `v18_outputs/v18_source_confound_within.csv`

## Pooled v17 GM-only accuracy by signal

| signal | n | acc | acc_af | acc_eu | acc_diff | chi2 | chi2_p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MSP | 1260 | 0.8651 | 0.8746 | 0.8556 | 0.019 | 0.9792 | 0.3224 |
| CoCoA_0.25 | 1260 | 0.8651 | 0.8746 | 0.8556 | 0.019 | 0.9792 | 0.3224 |
| CoCoA_0.5 | 1260 | 0.8651 | 0.8746 | 0.8556 | 0.019 | 0.9792 | 0.3224 |
| CoCoA_0.75 | 1260 | 0.8651 | 0.8746 | 0.8556 | 0.019 | 0.9792 | 0.3224 |
| VCE | 1260 | 0.8651 | 0.8746 | 0.8556 | 0.019 | 0.9792 | 0.3224 |

## Pooled H3 (wrong-answer confidence) by signal

| signal | n_af | n_eu | af_mean | eu_mean | cohens_d | cliffs_delta | mannwhitney_p_one_sided | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MSP | 79 | 91 | 0.9038 | 0.9165 | -0.0589 | -0.0353 | 0.7166 | not supported |
| CoCoA_0.25 | 79 | 91 | 0.8682 | 0.8953 | -0.1612 | -0.1395 | 0.9423 | not supported |
| CoCoA_0.5 | 79 | 91 | 0.8325 | 0.8742 | -0.2738 | -0.1516 | 0.9565 | not supported |
| CoCoA_0.75 | 79 | 91 | 0.7969 | 0.853 | -0.3205 | -0.152 | 0.9569 | not supported |
| VCE | 79 | 91 | 0.7613 | 0.8319 | -0.3127 | -0.1049 | 0.8832 | not supported |

## Mixed-effects models

| signal | model_type | converged | region_coef | region_pvalue | error |
| --- | --- | --- | --- | --- | --- |
| MSP | glmm_accuracy | True | 0.1655 | 0.6458 | None |
| CoCoA_0.25 | glmm_accuracy | True | 0.1655 | 0.6458 | None |
| CoCoA_0.5 | glmm_accuracy | True | 0.1655 | 0.6458 | None |
| CoCoA_0.75 | glmm_accuracy | True | 0.1655 | 0.6458 | None |
| VCE | glmm_accuracy | True | 0.1655 | 0.6458 | None |
| MSP | lmm_confidence | True | -0.1765 | 0.4138 | None |
| CoCoA_0.25 | lmm_confidence | True | -0.2469 | 0.3746 | None |
| CoCoA_0.5 | lmm_confidence | True | -0.245 | 0.3916 | None |
| CoCoA_0.75 | lmm_confidence | True | -0.2434 | 0.4056 | None |
| VCE | lmm_confidence | True | -0.2284 | 0.5044 | None |

## ECE cluster-bootstrap 95% CI (pooled)

| signal | observed_ece | mean_boot | ci_low | ci_high |
| --- | --- | --- | --- | --- |
| MSP | 0.1198 | 0.1202 | 0.0849 | 0.1565 |
| CoCoA_0.25 | 0.0965 | 0.0979 | 0.063 | 0.132 |
| CoCoA_0.5 | 0.0735 | 0.0761 | 0.0404 | 0.1107 |
| CoCoA_0.75 | 0.0605 | 0.0616 | 0.0299 | 0.099 |
| VCE | 0.048 | 0.0561 | 0.0313 | 0.0849 |

## Notes

- ECE uses 10 equal-width bins on [0, 1].
- CHR is the fraction wrong among items with confidence ≥ τ.
- H3 uses Mann-Whitney U and one-sided p-values; Holm correction is applied per-model.
- Accuracy model: marginal logistic regression with cluster-robust SEs clustered by question id
  (a crossed logistic GLMM is computationally unstable on this design).
- Confidence model: logit-normal linear mixed model with question-id random intercept and
  model as a fixed effect.
