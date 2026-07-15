# H3 Power Analysis — Equivalence Test

## Current Situation (7-Model Run, 2026-07-15)

- **Observed effect:** Cohen's d = -0.29 (Africa wrong-answer VCE lower than Europe)
- **Sample:** n_Africa = 69 wrong answers, n_Europe = 78 wrong answers
- **Pooled wrong-answer VCE:** Africa 0.794, Europe 0.849
- **Mann-Whitney U (two-sided):** p = 0.286
- **90% CI:** does not fall within [-0.20, +0.20]

**Conclusion:** The observed 90% CI does **not** fall within the equivalence margin [-0.20, +0.20]. We cannot claim equivalence. The test is underpowered for the observed effect size.

## Why the Original Power Analysis Was Wrong

The original analysis claimed ">99% power to detect d ≈ 1.00." This is the **contaminated effect** from mixed-source data — the very artifact the paper debunks. Using that effect size for power is circular: it proves only "if the source artifact survived into GM-only data we'd see it," which is tautological.

## Correct Power Analysis for Equivalence

For an equivalence test with:
- Minimum practically relevant effect: d = 0.30
- Alpha: 0.05 (one-sided)
- Target power: 0.80
- Equivalence margin: Δ = 0.20

**Required sample size:** n ≈ **180 per group** (total wrong answers ≈ 360)

Our current n = 69/78 is **underpowered** (~30–40% power for d = 0.30).

## Actual 7-Model Results

| Metric | Value |
|--------|-------|
| Models executed | 7 |
| Items | 180 (90 Africa / 90 Europe) |
| Total rows | 2,520 |
| Total API cost | $0.1045 |
| Pooled accuracy (Africa) | 89.0% (561/630) |
| Pooled accuracy (Europe) | 87.6% (552/630) |
| Accuracy chi-square | 0.49, p = 0.483 |
| Pooled wrong-answer VCE (Africa) | 0.794 (n=69) |
| Pooled wrong-answer VCE (Europe) | 0.849 (n=78) |
| Cohen's d (Africa - Europe) | -0.29 |
| Mann-Whitney U p (two-sided) | 0.286 |
| Pooled CHR at τ=0.70 (Africa) | 9.6% (n=613) |
| Pooled CHR at τ=0.70 (Europe) | 11.8% (n=625) |
| CHR ratio (Africa/Europe) | 0.81 |

### Per-Model Wrong-Answer VCE

| Model | N Africa | Mean Af | N Europe | Mean Eu | Cohen's d | MWU p |
|-------|----------|---------|----------|---------|-----------|-------|
| claude-3-haiku | 13 | 0.869 | 11 | 0.882 | -0.28 | 0.512 |
| deepseek-v3.2 | 8 | 0.863 | 7 | 0.879 | -0.26 | 0.589 |
| gemini-2.5-flash-lite | 11 | 0.659 | 12 | 0.829 | -0.55 | 0.267 |
| gpt-4.1-nano | 16 | 0.812 | 17 | 0.871 | -0.53 | 0.138 |
| gpt-4o-mini | 9 | 0.861 | 14 | 0.836 | +0.40 | 0.718 |
| llama-3.3-70b | 6 | 0.817 | 11 | 0.809 | +0.02 | 0.208 |
| qwen3-235b | 6 | 0.617 | 6 | 0.833 | -1.11 | 0.122 |

### Per-Model Accuracy

| Model | Africa Acc | 95% CI | Europe Acc | 95% CI |
|-------|------------|--------|------------|--------|
| claude-3-haiku | 0.856 | [0.768, 0.914] | 0.878 | [0.794, 0.930] |
| deepseek-v3.2 | 0.911 | [0.834, 0.954] | 0.922 | [0.848, 0.962] |
| gemini-2.5-flash-lite | 0.878 | [0.794, 0.930] | 0.867 | [0.781, 0.922] |
| gpt-4.1-nano | 0.822 | [0.731, 0.888] | 0.811 | [0.718, 0.879] |
| gpt-4o-mini | 0.900 | [0.821, 0.946] | 0.844 | [0.756, 0.905] |
| llama-3.3-70b | 0.933 | [0.862, 0.969] | 0.878 | [0.794, 0.930] |
| qwen3-235b | 0.933 | [0.862, 0.969] | 0.933 | [0.862, 0.969] |

## Remedy: Mixed-Source Contrast Arm

To achieve n ≈ 180 wrong answers per group:
1. Run the same 7 models on **180 GM-only items** (completed: `kaggle_8model_outputs.csv`)
2. Run the same 7 models on **180 matched mixed-source items** (AfriMMLU + Global-MMLU)
3. This doubles the wrong-answer sample to ~n = 160–182 per condition
4. Gives ~80% power for equivalence test at d = 0.30

## Experimental Design

See `MIXED_SOURCE_CONTRAST_DESIGN.md` for the full protocol.
