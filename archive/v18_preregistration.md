# v18 Pre-registration Stub

## Hypotheses

- **H1 (Accuracy disparity):** Models do not differ in Africa vs Europe accuracy on the GM-only v3 subset.
- **H2 (Calibration):** Equal-width ECE and CHR indicate comparable calibration across regions.
- **H3 (Overconfidence on wrong African answers):** Wrong-answer confidence is higher for African items than European items.

## Design

- Dataset: AfriKnow GM-only v3 (180 items, 90 Africa / 90 Europe).
- Models: 7 endpoints (claude-sonnet-4.6, gpt-4o-mini, gpt-4.1-nano, gemini-2.5-flash-lite, deepseek-v3.2, gemma-4-31b, llama-3.3-70b).
- Confidence signals: VCE (primary), MSP, CoCoA with α ∈ {0, 0.25, 0.5, 0.75, 1.0}.
- Primary α = 0.5 (fixed composite).

## Analysis plan

1. Accuracy per model and pooled; Pearson χ²; marginal logistic regression with cluster-robust SEs by qid.
2. CHR at τ ∈ {0.60, 0.70, 0.80, 0.90}.
3. H3 battery: Cohen's d, Cliff's δ, Mann-Whitney U, Holm correction.
4. ECE (10 equal-width) and Brier per model/region; equal-mass sensitivity (5/10/15 bins).
5. Cluster-bootstrap 95% CI for pooled ECE by qid.
6. AUROC for confidence as correctness discriminator.
7. Mixed models: logit-normal LMM on confidence (question-id random intercept, model fixed effect);
   marginal logistic regression with cluster-robust SEs on accuracy (crossed logistic GLMM did not converge).
8. Sensitivity analysis excluding the 21 flagged content-label mismatches.

## Stopping / exclusion rules

- Exclude API/parse failures from per-model accuracy but retain for calibration where possible.
- Exclude flagged IDs in the sensitivity arm.
- No interim peeking; this is a post-hoc reanalysis of completed Phase 4B data.

## Model roster note

The original design specified 5 models. The final evaluation expanded to 7 models to increase coverage of the closed/open model spectrum. The 7-model roster is: claude-sonnet-4.6, gpt-4o-mini, gpt-4.1-nano, gemini-2.5-flash-lite (closed); deepseek-v3.2, gemma-4-31b, llama-3.3-70b (open).

*Stub generated automatically by phase4b_v18_analysis.py.*
