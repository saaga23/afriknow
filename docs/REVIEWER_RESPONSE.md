# AfriKnow COLING 2027 — Pre-emptive Reviewer Response

**Target venue:** COLING 2027  
**Deadline:** October 12, 2026  
**Prepared:** 2026-07-10

---

## Objection 1: "Source confound is the only real finding; the rest is noise."

**Reviewer concern:** The source-confound finding is the central contribution. The null regional effects under source control are not "noise"; they are the evidence that source control changes the conclusion. The mixed-effects and sensitivity analyses strengthen this claim.

**Our response:** We agree that source control is the central contribution. The null regional effects are not noise; they are the primary result. When region is confounded with benchmark source (AfriMMLU vs. Global-MMLU), accuracy and confidence appear to differ. When source is held constant (Global-MMLU only), those differences vanish. This is direct evidence that the earlier Africa-overconfidence headline was a source artifact. The mixed-effects models (Section 4.3) and sensitivity analyses (Section 4.5) are not decorative; they test whether the null holds under alternative specifications. All five confidence signals (VCE, MSP, CoCoA at three alpha levels) point in the same direction, which strengthens the claim that the absence of a regional effect is robust to signal choice.

**Manuscript support:**
- Abstract: "no evidence of higher wrong-answer confidence for Africa under VCE"
- Section 4.2 (Accuracy): "no evidence of a systematic Africa-versus-Europe accuracy gap"
- Section 4.3 (Mixed-effects): "region effect is not significant; point estimate indicates slightly lower confidence on African items"
- Section 4.5 (Sensitivity): "Excluding 21 flagged content-label mismatches leaves the conclusions unchanged"
- Section 5 (Discussion): "apparent regional overconfidence can be absorbed by source confounding"

---

## Objection 2: "180 items is too small; results are underpowered."

**Reviewer concern:** Power analysis shows >99% power to detect the original effect (d≈1.00). The null is not due to underpowering. The 180-item design is a deliberate trade-off: source control requires source uniformity, which limits item availability.

**Our response:** The 180-item design is adequately powered. The original mixed-source run detected d≈1.00 with 474 wrong answers. The source-controlled run has 170 wrong answers (79 Africa, 91 Europe), which still provides >99% power to detect d≈1.00 at α=.05. The absence of a significant regional effect is therefore not attributable to underpowering. If the original effect were robust to source control, it would be clearly detectable in this design. The smaller per-model samples (range 15–39 wrong answers) explain why no single model reaches significance after Holm correction, but the pooled test is adequately powered.

**Manuscript support:**
- Section 3.4 (Analysis plan and power): "adequate power to detect the original effect size (Cohen's d ≈ 1.00) with power > .99"
- Section 4.3 (Mixed-effects): "question-id random variance is substantial, highlighting the need for item-level random effects"
- Section 5 (Discussion): "underpowering cannot explain the absence of a significant regional effect"

---

## Objection 3: "Post-hoc analysis is unreliable; you cherry-picked the null."

**Reviewer concern:** H3 was pre-specified. All five signals are reported without selection. Sensitivity analyses were not contingent on observed results. The Analysis Plan appendix documents this explicitly.

**Our response:** H3 was pre-specified before the v17 GM-only evaluation was executed on 2026-06-19. The directional hypothesis (Africa > Europe for wrong-answer confidence) was stated a priori. H1 (accuracy) and H2 (CHR) were added during initial data inspection as complementary signals, but they are reported as descriptive checks, not as primary hypotheses. The v18 post-hoc analysis expands the signal grid to include all five confidence signals, adds mixed-effects models, adds the source-confound comparison, and adds sensitivity analyses. All hypotheses, models, and sensitivity checks are reported without selection. No analysis was conditioned on the observed regional effect sizes.

**Manuscript support:**
- Appendix (Analysis Plan and Pre-registration): "H3 was pre-specified... all five signals reported without selection"
- Section 3.4: "The directional hypothesis... was specified before the v17 GM-only evaluation was executed"
- Section 4.4 (Sensitivity): "all five confidence signals point in the same direction"

---

## Objection 4: "Why should we trust Global-MMLU's geographic labels?"

**Reviewer concern:** 21 items (11.7%) were flagged for content-label review. Sensitivity analysis excluding them leaves conclusions unchanged. The labels are used as a starting point for matched-pair construction, not as ground truth.

**Our response:** We do not treat Global-MMLU's geographic labels as ground truth. They are used as a starting point for matched-pair construction. During dataset construction, 21 items (11.7%) were flagged for content-label review because the geographic content appeared misaligned with the assigned region tag. These items were reviewed and excluded from the matched pairs. The sensitivity analysis in Section 4.5 shows that excluding these 21 flagged items leaves the conclusions unchanged. This demonstrates that the results are not driven by mislabeled items.

**Manuscript support:**
- Section 2.1 (Dataset): "21 items (11.7%) were flagged for content-label review"
- Section 3.3 (Dataset): "geographic content mismatch review during dataset construction"
- Section 4.5 (Sensitivity): "Excluding 21 flagged content-label mismatches leaves the conclusions unchanged"

---

## Objection 5: "No human validation; how do you know the answer key is correct?"

**Reviewer concern:** This is a calibration audit, not a correctness validation. The contribution is about confidence-accuracy alignment, not about disputing the benchmark. Human annotation would not address the source-confound question.

**Our response:** This is a calibration audit, not a correctness validation. The contribution is about whether model confidence matches model accuracy, not about whether the benchmark answer keys are correct. Even if some answer keys were wrong, that would affect both regions equally in a source-controlled design, and the calibration metrics (ECE, Brier, AUROC) would still be valid measures of confidence-accuracy alignment. Human annotation is not relevant to the source-confound question, which is about whether regional effects persist when benchmark source is held constant.

**Manuscript support:**
- Section 1 (Introduction): "The contribution is about confidence-accuracy alignment, not about disputing the benchmark"
- Section 3.2 (Models): "All questions have a known correct answer"
- Section 5 (Discussion): "source-aware calibration audits are a useful diagnostic for fairness evaluation"

---

## Supplementary Materials

- **Kaggle dataset:** `abrahamsunday123/afriknow-v18-inputs` (public)
- **Kaggle notebook:** `abrahamsunday123/afriknow-phase-4b-v18-post-hoc-analysis` (public)
- **Code repository:** To be made public before submission
- **Reproducibility appendix:** Section 6.2 documents seeds, model identifiers, temperature settings, and cost logs

---

*This document will be expanded with specific line-number references after the final manuscript revision.*
