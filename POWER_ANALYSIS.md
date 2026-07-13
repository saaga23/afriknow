# H3 Power Analysis — Equivalence Test

## Current Situation

- **Observed effect:** Cohen's d = -0.31 (Africa wrong-answer VCE lower than Europe)
- **Sample:** n_Africa = 79 wrong answers, n_Europe = 91 wrong answers
- **90% CI:** [-0.59, -0.02]
- **Equivalence margin:** Δ = 0.20

**Conclusion:** The 90% CI does **not** fall within [-0.20, +0.20]. We cannot claim equivalence. The test is underpowered.

## Why the Original Power Analysis Was Wrong

The original analysis claimed ">99% power to detect d ≈ 1.00." This is the **contaminated effect** from mixed-source data — the very artifact the paper debunks. Using that effect size for power is circular: it proves only "if the source artifact survived into GM-only data we'd see it," which is tautological.

## Correct Power Analysis for Equivalence

For an equivalence test with:
- Minimum practically relevant effect: d = 0.30
- Alpha: 0.05 (one-sided)
- Target power: 0.80
- Equivalence margin: Δ = 0.20

**Required sample size:** n ≈ **180 per group** (total wrong answers ≈ 360)

Our current n = 79/91 is **underpowered** (~30–40% power for d = 0.30).

## Remedy: Mixed-Source Contrast Arm

To achieve n ≈ 180 wrong answers per group:
1. Run the same 7 models on **180 GM-only items** (current data)
2. Run the same 7 models on **180 matched mixed-source items** (AfriMMLU + Global-MMLU)
3. This doubles the wrong-answer sample to ~n = 160–182 per condition
4. Gives ~80% power for equivalence test at d = 0.30

## Experimental Design

See `MIXED_SOURCE_CONTRAST_DESIGN.md` for the full protocol.
