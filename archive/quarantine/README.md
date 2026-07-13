# Quarantine: Invalid Per-Model Statistics

## Why These Files Are Quarantined

The following output files contain **per-model statistics based on cell sizes of 2–4 wrong answers**. Effect sizes and p-values computed on such small samples are statistically meaningless and must not be reported in a scientific paper.

| Quarantined File | Issue |
|---|---|
| `v18_h3_by_model.csv` | Per-model H3 effect sizes on n=2–4 wrong answers |
| `v18_source_confound_within.csv` | Cross-cohort comparison with n=20/cell, different model rosters |

## What to Report Instead

- **H3 (wrong-answer confidence):** Report only the **pooled** test from `v18_h3_pooled.csv` (n_Africa=79, n_Europe=91).
- **Source confounding:** Do not report per-model cross-cohort comparisons. Use an internal within-study contrast instead (see `REMEDIATION.md`).

## Date Quarantined

2026-07-13 — Pre-submission audit for COLING 2027.
